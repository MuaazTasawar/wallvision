"""
Range-Doppler Processing
========================
Implements the 2D FFT pipeline that converts a raw FMCW beat-signal
frame into a Range-Doppler map (RD map).

Pipeline
────────
  frame (num_chirps × num_samples, complex)
        │
        ▼  apply Hann/Blackman window along fast-time axis
        │
        ▼  1st FFT along axis=1  →  Range FFT
        │   Each column is now a range bin.
        │   Discard upper half (mirror — real beat signal).
        │
        ▼  apply Hann window along slow-time axis
        │
        ▼  2nd FFT along axis=0  →  Doppler FFT
        │   Each row is now a velocity bin.
        │   fftshift centres zero-velocity.
        │
        ▼  |·|² → magnitude in dB, normalise to 0 dB peak
        │
        ▼  RD map  (num_chirps × num_samples//2, dB)

Physical units
──────────────
  Range    r = bin_idx × (c × fs) / (2 × BW × N)
  Velocity v = doppler_freq × λ / 2
           doppler_freq from fftfreq(N, d=1/PRF)
"""

import numpy as np
from scipy.signal import windows as sig_windows
from .chirp_simulator import ChirpConfig


# ── Window factory ─────────────────────────────────────────────────────────────

def _make_window(name: str, length: int) -> np.ndarray:
    """Return a normalised 1-D window array of the given type and length."""
    name = name.lower()
    if name == "hann":
        return sig_windows.hann(length)
    elif name == "blackman":
        return sig_windows.blackman(length)
    elif name == "rectangular":
        return np.ones(length)
    else:
        raise ValueError(f"Unknown window type '{name}'. Choose hann | blackman | rectangular.")


# ── Main processing function ───────────────────────────────────────────────────

def compute_range_doppler(
    frame:       np.ndarray,
    config:      ChirpConfig,
    window_type: str = "hann",
) -> dict:
    """
    Full 2D Range-Doppler processing of one radar frame.

    Parameters
    ----------
    frame       : complex ndarray (num_chirps, num_samples)
    config      : ChirpConfig  — needed to compute physical axis values
    window_type : 'hann' | 'blackman' | 'rectangular'

    Returns
    -------
    dict with keys:
        range_doppler_db   : list[list[float]]  shape [num_chirps, num_samples//2]
        range_axis         : list[float]        metres
        velocity_axis      : list[float]        m/s  (fftshifted, centred on 0)
        range_profile_db   : list[float]        1-D range profile (Doppler-integrated)
        rd_linear          : np.ndarray         linear magnitude (for CFAR input)
        peak_range_bin     : int                range bin of overall RD peak
        peak_range_m       : float              physical range of RD peak
        peak_velocity_mps  : float              velocity at RD peak
    """
    num_chirps, num_samples = frame.shape
    n_range   = num_samples // 2          # keep positive-frequency half only
    n_doppler = num_chirps
    c         = 3e8

    # ── Step 1: Window along fast-time (range axis) ────────────────────────────
    win_fast = _make_window(window_type, num_samples)             # (num_samples,)
    frame_win = frame * win_fast[np.newaxis, :]                   # broadcast over chirps

    # ── Step 2: 1st FFT — Range FFT ───────────────────────────────────────────
    range_fft = np.fft.fft(frame_win, n=num_samples, axis=1)     # (num_chirps, num_samples)
    range_fft = range_fft[:, :n_range]                           # keep positive half

    # ── Step 3: Window along slow-time (Doppler axis) ─────────────────────────
    win_slow = _make_window("hann", n_doppler)                    # (num_chirps,)
    range_fft_win = range_fft * win_slow[:, np.newaxis]           # broadcast over range bins

    # ── Step 4: 2nd FFT — Doppler FFT ─────────────────────────────────────────
    rd_complex = np.fft.fft(range_fft_win, n=n_doppler, axis=0)  # (num_chirps, n_range)
    rd_complex = np.fft.fftshift(rd_complex, axes=0)              # centre zero-velocity

    # ── Step 5: Magnitude ──────────────────────────────────────────────────────
    rd_linear = np.abs(rd_complex)                                # (num_chirps, n_range)

    # ── Step 6: Convert to dB, normalise ──────────────────────────────────────
    rd_mag    = np.maximum(rd_linear, 1e-12)
    rd_db     = 20.0 * np.log10(rd_mag)
    rd_db    -= rd_db.max()                                       # peak → 0 dB

    # ── Range axis ─────────────────────────────────────────────────────────────
    # df_fast = fs / N  [Hz per bin]
    # range per bin: dr = c · df_fast / (2 · slope)
    df_fast   = config.sample_rate / num_samples
    dr        = (c / 2.0) * df_fast / config.slope
    range_axis = np.arange(n_range) * dr                         # metres

    # ── Doppler / velocity axis ────────────────────────────────────────────────
    # PRF = 1 / chirp_duration
    # fftfreq gives [-PRF/2 … +PRF/2] after fftshift
    prf           = 1.0 / config.chirp_duration
    doppler_freqs = np.fft.fftshift(np.fft.fftfreq(n_doppler, d=1.0 / prf))
    velocity_axis = doppler_freqs * config.wavelength / 2.0      # m/s

    # ── Range profile (incoherent integration across Doppler) ─────────────────
    range_profile     = np.mean(rd_linear, axis=0)               # (n_range,)
    range_profile_db  = 20.0 * np.log10(np.maximum(range_profile, 1e-12))
    range_profile_db -= range_profile_db.max()

    # ── Peak detection (for debug / status) ───────────────────────────────────
    peak_flat      = np.argmax(rd_linear)
    peak_d, peak_r = np.unravel_index(peak_flat, rd_linear.shape)
    peak_range_m   = float(range_axis[peak_r]) if peak_r < len(range_axis) else 0.0
    peak_vel_mps   = float(velocity_axis[peak_d]) if peak_d < len(velocity_axis) else 0.0

    return {
        "range_doppler_db":  rd_db.tolist(),
        "range_axis":        range_axis.tolist(),
        "velocity_axis":     velocity_axis.tolist(),
        "range_profile_db":  range_profile_db.tolist(),
        "rd_linear":         rd_linear,           # kept as ndarray for CFAR
        "peak_range_bin":    int(peak_r),
        "peak_range_m":      peak_range_m,
        "peak_velocity_mps": peak_vel_mps,
    }


# ── Convenience: range-only profile (no Doppler) ──────────────────────────────

def compute_range_profile(
    frame:       np.ndarray,
    config:      ChirpConfig,
    window_type: str = "hann",
) -> dict:
    """
    1D range profile only — faster than the full 2D pipeline.
    Used by the WebSocket streamer for the 'Range FFT' step card.

    Returns
    -------
    dict with:
        range_profile_db : list[float]
        range_axis       : list[float]  metres
    """
    num_chirps, num_samples = frame.shape
    n_range = num_samples // 2
    c       = 3e8

    win_fast  = _make_window(window_type, num_samples)
    frame_win = frame * win_fast[np.newaxis, :]

    # Average across chirps before FFT → reduces noise
    mean_chirp = np.mean(frame_win, axis=0)                      # (num_samples,)
    range_fft  = np.fft.fft(mean_chirp, n=num_samples)[:n_range]

    profile    = np.abs(range_fft)
    profile_db = 20.0 * np.log10(np.maximum(profile, 1e-12))
    profile_db -= profile_db.max()

    df_fast    = config.sample_rate / num_samples
    dr         = (c / 2.0) * df_fast / config.slope
    range_axis = np.arange(n_range) * dr

    return {
        "range_profile_db": profile_db.tolist(),
        "range_axis":       range_axis.tolist(),
    }