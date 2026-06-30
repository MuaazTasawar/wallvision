"""
WebSocket Live Pipeline Streamer
===================================
  WS /ws/radar-stream

Streams the DSP pipeline stage-by-stage so the frontend can animate
"Chirp generated -> Range FFT -> Doppler FFT -> CFAR -> Micro-Doppler ->
Vitals" exactly as described in the WallVision wow moment.

Client sends a JSON ChirpConfigRequest-shaped message to start a run.
Server pushes one JSON message per pipeline stage, then a final
"complete" message with the full RadarFrameResponse-equivalent payload.
"""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.chirp_simulator import (
    ChirpConfig, TargetConfig, simulate_frame, simulate_vital_sign_phase_sequence,
)
from core.range_doppler import compute_range_doppler
from core.cfar import os_cfar_2d
from core.micro_doppler import compute_cwt_spectrogram
from core.vital_signs import extract_vital_signs
from models.schemas import ChirpConfigRequest

router = APIRouter()


async def _send_step(ws: WebSocket, step_index: int, name: str, payload: dict):
    await ws.send_json({
        "type":  "step",
        "index": step_index,
        "name":  name,
        "data":  payload,
    })
    await asyncio.sleep(0.15)  # small delay so the frontend can visibly animate each stage


@router.websocket("/ws/radar-stream")
async def radar_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                req = ChirpConfigRequest(**payload)
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"Invalid config: {e}"})
                continue

            config = ChirpConfig(
                bandwidth=req.bandwidth_ghz * 1e9,
                center_freq=req.center_freq_ghz * 1e9,
                chirp_duration=req.chirp_duration_us * 1e-6,
                num_chirps=req.num_chirps,
                num_samples=req.num_samples,
                sample_rate=req.sample_rate_mhz * 1e6,
            )
            target = TargetConfig(
                range_m=req.target_range_m,
                velocity_mps=req.target_velocity_mps,
                breathing_rate_hz=req.breathing_rate_bpm / 60.0,
                breathing_amplitude_m=req.breathing_amplitude_mm / 1000.0,
                enable_heartbeat=req.enable_heartbeat,
            )

            # ── Step 0: Chirp generation ────────────────────────────────────────
            frame = simulate_frame(config, target, snr_db=req.snr_db, rng_seed=None)
            await _send_step(websocket, 0, "Chirp Generation", {
                "status": f"Generated {config.num_chirps} chirps x {config.num_samples} samples",
            })

            # ── Step 1+2: Range FFT + Doppler FFT (combined internally) ─────────
            rd = compute_range_doppler(frame, config, window_type=req.window_type)
            await _send_step(websocket, 1, "Range FFT", {
                "range_profile_db": rd["range_profile_db"],
                "range_axis":       rd["range_axis"],
            })
            await _send_step(websocket, 2, "Doppler FFT", {
                "range_doppler_db": rd["range_doppler_db"],
                "range_axis":       rd["range_axis"],
                "velocity_axis":    rd["velocity_axis"],
            })

            # ── Step 3: CFAR ──────────────────────────────────────────────────────
            detections_raw = os_cfar_2d(
                rd["rd_linear"], guard_cells=req.cfar_guard_cells,
                training_cells=req.cfar_training_cells, pfa=req.cfar_pfa,
            )
            detections = [{
                "range_bin": d["range_bin"], "doppler_bin": d["doppler_bin"],
                "snr_db": d["snr_db"],
                "range_m": rd["range_axis"][d["range_bin"]] if d["range_bin"] < len(rd["range_axis"]) else 0.0,
                "velocity_mps": rd["velocity_axis"][d["doppler_bin"]] if d["doppler_bin"] < len(rd["velocity_axis"]) else 0.0,
            } for d in detections_raw]

            await _send_step(websocket, 3, "OS-CFAR Detection", {"detections": detections})

            # ── Step 4+5: Micro-Doppler + Vitals (only if a target was found) ──────
            vitals_payload = None
            cwt_payload = None
            if detections:
                top = max(detections, key=lambda d: d["snr_db"])
                target_for_vitals = TargetConfig(
                    range_m=top["range_m"],
                    breathing_rate_hz=req.breathing_rate_bpm / 60.0,
                    breathing_amplitude_m=req.breathing_amplitude_mm / 1000.0,
                    enable_heartbeat=req.enable_heartbeat,
                )
                seq = simulate_vital_sign_phase_sequence(
                    target_for_vitals, duration_s=10.0, frame_rate_hz=20.0, rng_seed=None,
                )
                cwt = compute_cwt_spectrogram(seq["phase_signal"], seq["fs"])
                vitals = extract_vital_signs(seq["phase_signal"], seq["fs"])

                cwt_payload = {
                    "cwt_power_db":   cwt["cwt_power_db"],
                    "time_axis":      cwt["time_axis"],
                    "frequency_axis_bpm": cwt["frequency_axis_bpm"],
                }
                vitals_payload = {
                    "breathing_rate_bpm":  vitals["breathing_rate_bpm"],
                    "heart_rate_bpm":      vitals["heart_rate_bpm"],
                    "vital_signs_detected": vitals["vital_signs_detected"],
                    "phase_signal":        vitals["phase_signal"],
                    "breathing_signal":    vitals["breathing_signal"],
                }

                await _send_step(websocket, 4, "Micro-Doppler CWT", cwt_payload)
                await _send_step(websocket, 5, "Vital Sign Extraction", vitals_payload)

            # ── Final: complete ───────────────────────────────────────────────────
            await websocket.send_json({
                "type": "complete",
                "summary": {
                    "target_detected": len(detections) > 0,
                    "num_detections":  len(detections),
                    "vitals":          vitals_payload,
                },
            })

    except WebSocketDisconnect:
        pass