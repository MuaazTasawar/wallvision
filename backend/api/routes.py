"""
REST API Routes
================
  GET  /api/pipeline-steps     — static metadata describing each DSP stage
  POST /api/simulate           — run full pipeline on a SIMULATED scene
  POST /api/upload-dataset     — run full pipeline on an UPLOADED TI .bin capture
"""

import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from core.chirp_simulator import (
    ChirpConfig, TargetConfig, simulate_frame, simulate_vital_sign_phase_sequence,
)
from core.range_doppler import compute_range_doppler
from core.cfar import os_cfar_2d
from core.micro_doppler import compute_cwt_spectrogram
from core.vital_signs import extract_vital_signs
from core.dataset_loader import load_ti_mmwave_bin, validate_capture_size, DatasetLoadError

from models.schemas import (
    ChirpConfigRequest, RadarFrameResponse, DetectionResult,
    PipelineStepsResponse, PipelineStep,
)

router = APIRouter(prefix="/api")


# ── Pipeline step metadata (static, drives the frontend PipelineSteps panel) ──

PIPELINE_STEPS = [
    PipelineStep(
        index=0, name="Chirp Generation",
        description="Simulate FMCW beat signals for the configured scene.",
        output="Complex frame (num_chirps x num_samples)",
        formula="s_b(t) = exp(j*2*pi*f_beat*t - j*phi_carrier),  f_beat = 2*BW*r/(c*Tc)",
    ),
    PipelineStep(
        index=1, name="Range FFT",
        description="1D FFT along fast-time resolves target range.",
        output="Range spectrum per chirp",
        formula="r = bin_idx * c / (2*BW)",
    ),
    PipelineStep(
        index=2, name="Doppler FFT",
        description="2D FFT along slow-time resolves target velocity.",
        output="Range-Doppler map (dB)",
        formula="v = doppler_freq * lambda / 2",
    ),
    PipelineStep(
        index=3, name="OS-CFAR Detection",
        description="Adaptive thresholding isolates targets from noise floor.",
        output="List of (range, velocity, SNR) detections",
        formula="threshold = alpha * z_K,  alpha = K*(Pfa^(-1/K) - 1)",
    ),
    PipelineStep(
        index=4, name="Micro-Doppler CWT",
        description="Wavelet transform of phase reveals breathing/heartbeat oscillation.",
        output="Time-frequency spectrogram (dB)",
        formula="CWT(a,b) = (1/sqrt(a)) * integral[ x(t) * psi*((t-b)/a) dt ]",
    ),
    PipelineStep(
        index=5, name="Vital Sign Extraction",
        description="Bandpass filter + FFT on phase signal extracts BPM rates.",
        output="Breathing rate (BPM), Heart rate (BPM)",
        formula="delta_phi = 4*pi*delta_r / lambda",
    ),
]


@router.get("/pipeline-steps", response_model=PipelineStepsResponse)
async def get_pipeline_steps():
    return PipelineStepsResponse(steps=PIPELINE_STEPS)


# ── Core pipeline runner (shared by /simulate and /upload-dataset) ────────────

def _run_full_pipeline(frame: np.ndarray, config: ChirpConfig, req: ChirpConfigRequest) -> RadarFrameResponse:
    """
    Runs Range-Doppler -> CFAR -> (if target detected) micro-Doppler + vitals
    on an already-generated complex frame, and assembles the API response.
    """
    rd = compute_range_doppler(frame, config, window_type=req.window_type)
    detections_raw = os_cfar_2d(
        rd["rd_linear"],
        guard_cells=req.cfar_guard_cells,
        training_cells=req.cfar_training_cells,
        pfa=req.cfar_pfa,
    )

    detections = []
    for d in detections_raw:
        range_m = rd["range_axis"][d["range_bin"]] if d["range_bin"] < len(rd["range_axis"]) else 0.0
        vel_mps = rd["velocity_axis"][d["doppler_bin"]] if d["doppler_bin"] < len(rd["velocity_axis"]) else 0.0
        detections.append(DetectionResult(
            range_bin=d["range_bin"], doppler_bin=d["doppler_bin"],
            snr_db=d["snr_db"], range_m=range_m, velocity_mps=vel_mps, power=d["power"],
        ))

    response_kwargs = dict(
        range_doppler_db=rd["range_doppler_db"],
        range_axis=rd["range_axis"],
        velocity_axis=rd["velocity_axis"],
        range_profile_db=rd["range_profile_db"],
        detections=detections,
        range_resolution_m=config.range_resolution,
        velocity_resolution_mps=config.velocity_resolution,
        max_range_m=config.max_range,
        max_velocity_mps=config.max_velocity,
    )

    # ── Vital signs: only meaningful for a SIMULATED scene with a stationary-ish
    #    target, since they need a separate frame-rate phase sequence that the
    #    chirp-level frame alone cannot provide (see Phase 3 design note).
    if detections:
        top = max(detections, key=lambda d: d.snr_db)
        target_for_vitals = TargetConfig(
            range_m=top.range_m,
            breathing_rate_hz=req.breathing_rate_bpm / 60.0,
            breathing_amplitude_m=req.breathing_amplitude_mm / 1000.0,
            enable_heartbeat=req.enable_heartbeat,
        )
        seq = simulate_vital_sign_phase_sequence(
            target_for_vitals, duration_s=10.0, frame_rate_hz=20.0, rng_seed=None,
        )
        vitals = extract_vital_signs(seq["phase_signal"], seq["fs"])
        cwt = compute_cwt_spectrogram(seq["phase_signal"], seq["fs"])

        response_kwargs.update(
            breathing_rate_bpm=vitals["breathing_rate_bpm"],
            heart_rate_bpm=vitals["heart_rate_bpm"],
            vital_signs_detected=vitals["vital_signs_detected"],
            phase_signal=vitals["phase_signal"],
            breathing_signal=vitals["breathing_signal"],
            phase_fft_db=vitals["phase_fft_db"],
            phase_fft_freqs_bpm=vitals["phase_fft_freqs_bpm"],
            cwt_power_db=cwt["cwt_power_db"],
            cwt_time_axis=cwt["time_axis"],
            cwt_frequency_axis=cwt["frequency_axis_bpm"],
        )

    return RadarFrameResponse(**response_kwargs)


# ── /api/simulate ──────────────────────────────────────────────────────────────

@router.post("/simulate", response_model=RadarFrameResponse)
async def simulate(req: ChirpConfigRequest):
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

    frame = simulate_frame(config, target, snr_db=req.snr_db, rng_seed=None)

    return _run_full_pipeline(frame, config, req)


# ── /api/upload-dataset ─────────────────────────────────────────────────────────

@router.post("/upload-dataset", response_model=RadarFrameResponse)
async def upload_dataset(
    file:         UploadFile = File(...),
    num_chirps:   int        = Form(128),
    num_samples:  int        = Form(256),
    bandwidth_ghz:    float  = Form(1.0),
    center_freq_ghz:  float  = Form(77.0),
    chirp_duration_us: float = Form(64.0),
    sample_rate_mhz:  float  = Form(4.0),
    snr_db:           float  = Form(20.0),
    window_type:      str    = Form("hann"),
    cfar_guard_cells: int    = Form(2),
    cfar_training_cells: int = Form(8),
    cfar_pfa:         float  = Form(1e-4),
):
    file_bytes = await file.read()

    validation = validate_capture_size(len(file_bytes), num_chirps, num_samples)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])

    try:
        frame = load_ti_mmwave_bin(file_bytes, num_chirps, num_samples)
    except DatasetLoadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    config = ChirpConfig(
        bandwidth=bandwidth_ghz * 1e9,
        center_freq=center_freq_ghz * 1e9,
        chirp_duration=chirp_duration_us * 1e-6,
        num_chirps=num_chirps,
        num_samples=num_samples,
        sample_rate=sample_rate_mhz * 1e6,
    )

    # Build a minimal request object for shared pipeline logic
    req = ChirpConfigRequest(
        bandwidth_ghz=bandwidth_ghz, center_freq_ghz=center_freq_ghz,
        chirp_duration_us=chirp_duration_us, num_chirps=num_chirps,
        num_samples=num_samples, sample_rate_mhz=sample_rate_mhz,
        snr_db=snr_db, window_type=window_type,
        cfar_guard_cells=cfar_guard_cells, cfar_training_cells=cfar_training_cells,
        cfar_pfa=cfar_pfa,
    )

    return _run_full_pipeline(frame, config, req)