"""
Phase-Based Vital Sign Extraction
====================================
Extracts breathing rate and heart rate from the slow-time phase signal
at a target's range bin, using the principle that sub-millimetre chest
wall displacement produces a measurable phase shift at mmWave
wavelengths:

    Δφ = 4π · Δr / λ

At λ ≈ 3.9 mm (77 GHz), a 2 mm breathing displacement produces
Δφ ≈ 4π × 0.002 / 0.0039 ≈ 6.4 rad — easily resolvable, which is why
phase-based vital sign sensing works even though Δr is far smaller
than the radar's range resolution (~15 cm).

Pipeline
────────
  unwrapped phase φ(t)
        │
        ▼  remove DC trend (np.unwrap already done upstream)
        │
        ▼  bandpass filter → isolate breathing band (0.1–0.5 Hz)
        │   Butterworth IIR, zero-phase (filtfilt)
        │
        ▼  FFT of filtered signal → peak frequency = breathing rate
        │
        ▼  (optional) bandpass filter → heartbeat band (0.8–2.0 Hz)
        │   Heartbeat signal is much weaker — harmonic cancellation
        │   technique removes breathing harmonics before FFT.
        │
        ▼  breathing_rate_bpm, heart_rate_bpm
"""

import numpy as np
from scipy.signal import butter, filtfilt
from .chirp_simulator import ChirpConfig


# ── Bandpass filter ────────────────────────────────────────────────────────────

def _bandpass_filter(
    signal:    np.ndarray,
    fs:        float,
    low_hz:    float,
    high_hz:   float,
    order:     int = 4,
) -> np.ndarray:
    """
    Zero-phase Butterworth bandpass filter.

    Parameters
    ----------
    signal  : 1D float ndarray
    fs      : sampling frequency [Hz] (= 1 / chirp_duration, the slow-time rate)
    low_hz, high_hz : passband edges
    order   : filter order

    Returns
    -------
    filtered : 1D float ndarray, same length as input
    """
    nyquist = fs / 2.0
    low  = max(low_hz / nyquist, 1e-6)
    high = min(high_hz / nyquist, 0.999)

    if high <= low:
        return np.zeros_like(signal)

    # filtfilt requires signal length > 3 * max(len(a), len(b))
    padlen_needed = 3 * (2 * order + 1)
    if len(signal) <= padlen_needed:
        return np.zeros_like(signal)

    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, signal)


# ── FFT-based rate estimation ──────────────────────────────────────────────────

def _estimate_rate_from_fft(
    signal:      np.ndarray,
    fs:          float,
    band_min_hz: float,
    band_max_hz: float,
) -> dict:
    """
    Estimate dominant frequency within a band via zero-padded FFT
    for sub-bin frequency resolution.

    Returns
    -------
    dict: {rate_hz, rate_bpm, spectrum_db, freq_axis_hz, freq_axis_bpm, peak_power_db}
    """
    n = len(signal)
    if n == 0 or np.allclose(signal, 0.0):
        return {
            "rate_hz": 0.0, "rate_bpm": 0.0,
            "spectrum_db": [], "freq_axis_hz": [], "freq_axis_bpm": [],
            "peak_power_db": -100.0,
        }

    # Zero-pad 8x for finer frequency resolution (BPM-level precision)
    n_fft = max(2048, n * 8)
    window = np.hanning(n)
    windowed = signal * window

    spectrum = np.fft.rfft(windowed, n=n_fft)
    freqs    = np.fft.rfftfreq(n_fft, d=1.0 / fs)

    power = np.abs(spectrum) ** 2
    power_db = 10.0 * np.log10(np.maximum(power, 1e-15))
    power_db -= power_db.max() if power_db.max() > -np.inf else 0.0

    band_mask = (freqs >= band_min_hz) & (freqs <= band_max_hz)
    if not np.any(band_mask):
        return {
            "rate_hz": 0.0, "rate_bpm": 0.0,
            "spectrum_db": power_db.tolist(), "freq_axis_hz": freqs.tolist(),
            "freq_axis_bpm": (freqs * 60.0).tolist(), "peak_power_db": -100.0,
        }

    band_freqs = freqs[band_mask]
    band_power = power[band_mask]
    peak_idx   = np.argmax(band_power)

    rate_hz = float(band_freqs[peak_idx])
    peak_power_db = float(10.0 * np.log10(band_power[peak_idx] + 1e-15) - power_db.max())

    return {
        "rate_hz":       rate_hz,
        "rate_bpm":      rate_hz * 60.0,
        "spectrum_db":   power_db.tolist(),
        "freq_axis_hz":  freqs.tolist(),
        "freq_axis_bpm": (freqs * 60.0).tolist(),
        "peak_power_db": peak_power_db,
    }


# ── Main vital sign extraction ─────────────────────────────────────────────────

def extract_vital_signs(
    phase_signal: np.ndarray,
    fs_hz:        float,
    breathing_band_hz: tuple = (0.1, 0.6),
    heartbeat_band_hz: tuple = (0.8, 2.2),
) -> dict:
    """
    Full vital sign extraction pipeline from an unwrapped slow-time
    phase signal.

    Parameters
    ----------
    phase_signal : 1D float ndarray (radians, DC-removed)
    fs_hz        : sample rate of phase_signal [Hz].
                   For frame-rate vital sequences this is frame_rate_hz
                   (typically 10-20 Hz) — NOT 1/chirp_duration.
    breathing_band_hz, heartbeat_band_hz : passband tuples (Hz)
    """
    fs = fs_hz

    breathing_signal = _bandpass_filter(
        phase_signal, fs, breathing_band_hz[0], breathing_band_hz[1]
    )
    breathing_result = _estimate_rate_from_fft(
        breathing_signal, fs, breathing_band_hz[0], breathing_band_hz[1]
    )

    vital_signs_detected = breathing_result["peak_power_db"] > -25.0 and len(phase_signal) >= 16

    heartbeat_signal = _bandpass_filter(
        phase_signal, fs, heartbeat_band_hz[0], heartbeat_band_hz[1]
    )
    heartbeat_result = _estimate_rate_from_fft(
        heartbeat_signal, fs, heartbeat_band_hz[0], heartbeat_band_hz[1]
    )

    full_band_result = _estimate_rate_from_fft(
        phase_signal - np.mean(phase_signal), fs, 0.05, 2.5
    )

    return {
        "breathing_rate_bpm":   round(breathing_result["rate_bpm"], 1) if vital_signs_detected else None,
        "heart_rate_bpm":       round(heartbeat_result["rate_bpm"], 1) if vital_signs_detected else None,
        "vital_signs_detected": vital_signs_detected,
        "phase_signal":         phase_signal.tolist(),
        "breathing_signal":     breathing_signal.tolist(),
        "phase_fft_db":         full_band_result["spectrum_db"],
        "phase_fft_freqs_bpm":  full_band_result["freq_axis_bpm"],
    }