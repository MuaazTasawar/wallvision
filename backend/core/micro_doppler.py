"""
Micro-Doppler Spectrogram via Continuous Wavelet Transform (CWT)
==================================================================
Human chest motion (breathing + heartbeat) produces a slow-time phase
signal that is non-stationary — its frequency content changes over
the observation window as breathing depth/rate naturally varies.

The STFT trades time and frequency resolution at a fixed ratio.
The CWT instead uses a Morlet wavelet whose width scales with the
analysis frequency, giving better time resolution at high frequencies
(heartbeat, ~1 Hz) and better frequency resolution at low frequencies
(breathing, ~0.2-0.5 Hz) — the right tradeoff for vital-sign micro-
Doppler, which is why it's the standard tool in this domain.

Pipeline
────────
  slow-time phase signal φ(t)  [from peak range bin across all chirps]
        │
        ▼  remove DC / detrend
        │
        ▼  complex Morlet CWT across a bank of scales
        │   scale ↔ frequency:  f = fc / (scale × dt)
        │   (fc = wavelet centre frequency, dt = chirp period)
        │
        ▼  |CWT|²  →  power, convert to dB
        │
        ▼  spectrogram (scale/frequency × slow-time)

Output frequency axis is in Hz; the frontend overlays BPM gridlines
(BPM = Hz × 60) so breathing (~0.2-0.5 Hz / 12-30 BPM) and heartbeat
(~0.8-2.0 Hz / 48-120 BPM) bands are visually distinguishable.
"""

import numpy as np
import pywt
from .chirp_simulator import ChirpConfig


# ── Phase extraction ────────────────────────────────────────────────────────────

def extract_slow_time_phase(rd_complex_at_range: np.ndarray) -> np.ndarray:
    """
    Extract and unwrap the slow-time phase signal at a fixed range bin.

    Parameters
    ----------
    rd_complex_at_range : complex 1D ndarray, length = num_chirps
                           (the Doppler-FFT complex column at the target's range bin,
                            taken BEFORE fftshift/magnitude — i.e. the raw per-chirp
                            complex sample at that range, one value per chirp)

    Returns
    -------
    phase_unwrapped : float ndarray, length = num_chirps
                       Unwrapped phase in radians, DC-removed.
    """
    phase = np.angle(rd_complex_at_range)
    phase_unwrapped = np.unwrap(phase)
    phase_unwrapped = phase_unwrapped - np.mean(phase_unwrapped)
    return phase_unwrapped


# ── CWT spectrogram ──────────────────────────────────────────────────────────────

def compute_cwt_spectrogram(
    phase_signal:    np.ndarray,
    fs_hz:           float,
    num_scales:      int   = 64,
    freq_min_hz:     float = 0.1,
    freq_max_hz:     float = 3.0,
    wavelet:         str   = "cmor1.5-1.0",
) -> dict:
    """
    Complex Morlet CWT of the slow-time (frame-rate) phase signal.

    Parameters
    ----------
    phase_signal : 1D float ndarray (unwrapped phase)
    fs_hz        : sample rate of phase_signal [Hz] — frame_rate_hz,
                   NOT 1/chirp_duration.
    """
    dt = 1.0 / fs_hz
    n  = len(phase_signal)

    freqs_hz = np.geomspace(freq_min_hz, freq_max_hz, num_scales)
    central_freq = pywt.central_frequency(wavelet)
    scales = central_freq / (freqs_hz * dt)

    coeffs, actual_freqs = pywt.cwt(
        phase_signal, scales, wavelet, sampling_period=dt
    )

    power = np.abs(coeffs) ** 2
    power_db = 10.0 * np.log10(np.maximum(power, 1e-12))
    power_db -= power_db.max()

    time_axis = np.arange(n) * dt

    return {
        "cwt_power_db":       power_db.tolist(),
        "time_axis":          time_axis.tolist(),
        "frequency_axis":     actual_freqs.tolist(),
        "frequency_axis_bpm": (actual_freqs * 60.0).tolist(),
    }


# ── Dominant frequency extraction (used to cross-check FFT-based vitals) ────────

def find_dominant_frequency_band(
    cwt_power_db:    np.ndarray,
    frequency_axis:  np.ndarray,
    band_min_hz:     float,
    band_max_hz:     float,
) -> dict:
    """
    Find the time-averaged dominant frequency within a band of the CWT
    spectrogram. Used to extract a robust breathing-rate or heart-rate
    estimate from the 2D map (averaging across slow-time reduces noise
    sensitivity compared to a single 1D FFT bin pick).

    Parameters
    ----------
    cwt_power_db    : 2D ndarray (num_scales, num_chirps), in dB
    frequency_axis  : 1D ndarray (num_scales,), Hz — same order as cwt rows
    band_min_hz, band_max_hz : frequency band to search within

    Returns
    -------
    dict: {dominant_freq_hz, dominant_freq_bpm, confidence_db}
    """
    band_mask = (frequency_axis >= band_min_hz) & (frequency_axis <= band_max_hz)
    if not np.any(band_mask):
        return {"dominant_freq_hz": 0.0, "dominant_freq_bpm": 0.0, "confidence_db": -100.0}

    # Average power across time for each frequency row within the band
    power_linear = 10.0 ** (cwt_power_db / 10.0)
    band_power_time_avg = np.mean(power_linear[band_mask], axis=1)
    band_freqs = frequency_axis[band_mask]

    peak_idx = np.argmax(band_power_time_avg)
    dominant_freq = float(band_freqs[peak_idx])
    confidence_db = float(10.0 * np.log10(band_power_time_avg[peak_idx] + 1e-12))

    return {
        "dominant_freq_hz":  dominant_freq,
        "dominant_freq_bpm": dominant_freq * 60.0,
        "confidence_db":     confidence_db,
    }