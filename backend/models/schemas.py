"""
Pydantic schemas for WallVision API.

Request  → ChirpConfigRequest   (from frontend sliders)
Response → RadarFrameResponse   (full pipeline output)
           PipelineStepsResponse (static step metadata)
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# ── Request ────────────────────────────────────────────────────────────────────

class ChirpConfigRequest(BaseModel):
    """
    Frontend sends these values (all in human-friendly units).
    Backend converts to SI before passing to DSP core.
    """

    # Waveform
    bandwidth_ghz:       float = Field(default=1.0,  ge=0.1,  le=4.0,
                                       description="Bandwidth [GHz] — range resolution = 15/BW cm")
    center_freq_ghz:     float = Field(default=77.0, ge=24.0, le=81.0,
                                       description="Centre frequency [GHz]")
    chirp_duration_us:   float = Field(default=64.0, ge=10.0, le=500.0,
                                       description="Chirp duration [µs]")
    num_chirps:          int   = Field(default=128,  ge=16,   le=512,
                                       description="Chirps per frame (slow-time length)")
    num_samples:         int   = Field(default=256,  ge=64,   le=1024,
                                       description="ADC samples per chirp (fast-time length)")
    sample_rate_mhz:     float = Field(default=4.0,  ge=1.0,  le=20.0,
                                       description="ADC sample rate [MHz]")

    # Scene
    snr_db:              float = Field(default=20.0, ge=0.0,  le=50.0,
                                       description="Target SNR [dB]")
    target_range_m:      float = Field(default=4.0,  ge=0.5,  le=20.0,
                                       description="Target distance [m]")
    target_velocity_mps: float = Field(default=0.0,  ge=-5.0, le=5.0,
                                       description="Bulk radial velocity [m/s]")

    # Vital signs
    breathing_rate_bpm:     float = Field(default=15.0, ge=5.0,  le=40.0,
                                          description="Simulated breathing rate [BPM]")
    breathing_amplitude_mm: float = Field(default=2.0,  ge=0.1,  le=10.0,
                                          description="Chest displacement amplitude [mm]")
    enable_heartbeat:       bool  = Field(default=True,
                                          description="Include heartbeat micro-Doppler")

    # Processing
    window_type:         str   = Field(default="hann",
                                       pattern="^(hann|blackman|rectangular)$",
                                       description="FFT window function")
    cfar_guard_cells:    int   = Field(default=2,    ge=1, le=5)
    cfar_training_cells: int   = Field(default=8,    ge=4, le=16)
    cfar_pfa:            float = Field(default=1e-4, ge=1e-6, le=0.1,
                                       description="CFAR probability of false alarm")


# ── Sub-models ─────────────────────────────────────────────────────────────────

class DetectionResult(BaseModel):
    """One CFAR detection, converted to physical units."""
    range_bin:    int
    doppler_bin:  int
    snr_db:       float
    range_m:      float
    velocity_mps: float
    power:        float


class PipelineStep(BaseModel):
    """Metadata for one DSP stage (used by frontend PipelineSteps panel)."""
    index:       int
    name:        str
    description: str
    output:      str
    formula:     str


# ── Response ───────────────────────────────────────────────────────────────────

class RadarFrameResponse(BaseModel):
    """
    Full pipeline output for one radar frame.
    Every list here maps directly to a Plotly trace in the frontend.
    """

    # ── Range-Doppler map ──────────────────────────────────────────────────────
    range_doppler_db:  List[List[float]]   # shape [num_chirps, num_samples//2], dB, normalised
    range_axis:        List[float]         # metres, length = num_samples//2
    velocity_axis:     List[float]         # m/s,    length = num_chirps

    # ── Range profile (integrated across Doppler) ──────────────────────────────
    range_profile_db:  List[float]         # length = num_samples//2

    # ── CFAR detections ────────────────────────────────────────────────────────
    detections:        List[DetectionResult]

    # ── Vital signs (for primary detected target) ──────────────────────────────
    breathing_rate_bpm:  Optional[float]       = None
    heart_rate_bpm:      Optional[float]       = None
    vital_signs_detected: bool                 = False
    phase_signal:        Optional[List[float]] = None   # unwrapped phase (slow-time)
    breathing_signal:    Optional[List[float]] = None   # bandpass-filtered phase
    phase_fft_db:        Optional[List[float]] = None   # spectrum of phase signal
    phase_fft_freqs_bpm: Optional[List[float]] = None   # frequency axis in BPM

    # ── Micro-Doppler CWT spectrogram ──────────────────────────────────────────
    cwt_power_db:        Optional[List[List[float]]] = None   # [scales, num_chirps]
    cwt_time_axis:       Optional[List[float]]       = None
    cwt_frequency_axis:  Optional[List[float]]       = None   # normalised scale freq

    # ── Frame metadata ─────────────────────────────────────────────────────────
    range_resolution_m:    float
    velocity_resolution_mps: float
    max_range_m:           float
    max_velocity_mps:      float


class PipelineStepsResponse(BaseModel):
    steps: List[PipelineStep]


class HealthResponse(BaseModel):
    status:  str
    version: str