"""
FMCW Chirp Simulator
====================
Generates synthetic FMCW radar beat signals for a scene containing
one human target with breathing and heartbeat micro-Doppler modulation.

Physics recap
─────────────
TX chirp:   s_tx(t) = exp(j·2π·(fc·t + (BW/2Tc)·t²))
RX delayed: s_rx(t) = s_tx(t − τ),   τ = 2r/c
Beat signal: s_b(t) = s_tx · conj(s_rx)
           = exp(j·2π·f_beat·t − j·φ₀)

  f_beat = (BW/Tc) · τ = 2·BW·r / (c·Tc)   [range-proportional frequency]
  φ₀     = 2π·fc·τ                           [carrier phase, used for vitals]

Across N chirps (slow-time axis), a moving target at velocity v adds
a phase increment Δφ = 4π·fc·v·Tc / c per chirp (Doppler).

Vital signs modulate r(t) sinusoidally, producing micro-Doppler
sidebands visible in the slow-time CWT spectrogram.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ── Radar Configuration ────────────────────────────────────────────────────────

@dataclass
class ChirpConfig:
    """
    FMCW radar hardware and waveform parameters.
    All values in SI units unless the field name says otherwise.
    """
    bandwidth:       float = 1e9      # Hz   — range resolution = c/(2·BW) ≈ 15 cm
    center_freq:     float = 77e9     # Hz   — 77 GHz mmWave band
    chirp_duration:  float = 64e-6    # s    — time per chirp (Tc)
    num_chirps:      int   = 128      # —     slow-time samples per frame
    num_samples:     int   = 256      # —     fast-time ADC samples per chirp
    sample_rate:     float = 4e6      # Hz   — ADC sample rate (fs)

    # ── Derived quantities ─────────────────────────────────────────────────────

    @property
    def range_resolution(self) -> float:
        """δr = c / (2·BW)  [meters per range bin]"""
        return 3e8 / (2.0 * self.bandwidth)

    @property
    def slope(self) -> float:
        """Chirp slope k = BW / Tc  [Hz/s]"""
        return self.bandwidth / self.chirp_duration

    @property
    def max_beat_freq(self) -> float:
        """Maximum detectable beat frequency = fs/2  [Hz]"""
        return self.sample_rate / 2.0

    @property
    def max_range(self) -> float:
        """Rmax = fs·c / (2·k)  [meters]"""
        return (self.sample_rate * 3e8) / (2.0 * self.slope)

    @property
    def range_bin_size(self) -> float:
        """Physical size of each range FFT bin [meters]"""
        # After N-point FFT on fs-sampled signal: df = fs/N
        # Range per bin: dr = c·df / (2·k)
        df = self.sample_rate / self.num_samples
        return (3e8 * df) / (2.0 * self.slope)

    @property
    def velocity_resolution(self) -> float:
        """δv = λ / (2·N·Tc)  [m/s per Doppler bin]"""
        wavelength = 3e8 / self.center_freq
        return wavelength / (2.0 * self.num_chirps * self.chirp_duration)

    @property
    def max_velocity(self) -> float:
        """vmax = λ / (4·Tc)  [m/s] — unambiguous velocity range ±vmax"""
        wavelength = 3e8 / self.center_freq
        return wavelength / (4.0 * self.chirp_duration)

    @property
    def wavelength(self) -> float:
        """λ = c / fc  [meters]"""
        return 3e8 / self.center_freq


# ── Target Model ───────────────────────────────────────────────────────────────

@dataclass
class TargetConfig:
    """
    Simulated human target.

    The chest displacement due to breathing and heartbeat produces
    a time-varying range r(t) = r0 + Δr_breath(t) + Δr_heart(t),
    which modulates the beat signal phase across slow-time —
    this is the micro-Doppler signature we extract.
    """
    range_m:                 float = 4.0     # m    — distance from radar
    velocity_mps:            float = 0.0     # m/s  — bulk radial velocity (0 = stationary)
    rcs_dbsm:                float = 0.0     # dBsm — radar cross section

    # Breathing
    breathing_rate_hz:       float = 0.25    # Hz   — 15 breaths/min
    breathing_amplitude_m:   float = 0.002   # m    — 2 mm chest displacement

    # Heartbeat (superimposed on breathing)
    heartbeat_rate_hz:       float = 1.1     # Hz   — 66 BPM
    heartbeat_amplitude_m:   float = 0.0004  # m    — 0.4 mm

    # Enable flags
    enable_heartbeat:        bool  = True


# ── Core Simulation ────────────────────────────────────────────────────────────

def simulate_frame(
    config:   ChirpConfig,
    target:   Optional[TargetConfig] = None,
    snr_db:   float = 20.0,
    rng_seed: Optional[int] = None,
) -> np.ndarray:
    """
    Simulate one radar frame of FMCW beat signals.

    Each row is one chirp's complex beat signal (fast-time axis).
    Across rows (slow-time axis), the target's breathing and heartbeat
    micro-Doppler produce slow phase modulations.

    Parameters
    ----------
    config   : ChirpConfig
    target   : TargetConfig — None produces a pure-noise frame
    snr_db   : signal-to-noise ratio in dB (per-element)
    rng_seed : reproducible noise if set

    Returns
    -------
    frame : complex ndarray, shape (num_chirps, num_samples)
    """
    c   = 3e8
    rng = np.random.default_rng(rng_seed)

    num_chirps  = config.num_chirps
    num_samples = config.num_samples

    # Fast-time axis: sample indices within one chirp
    dt_fast = 1.0 / config.sample_rate
    t_fast  = np.arange(num_samples) * dt_fast          # shape (num_samples,)

    # Slow-time axis: start time of each chirp
    t_slow = np.arange(num_chirps) * config.chirp_duration  # shape (num_chirps,)

    frame = np.zeros((num_chirps, num_samples), dtype=complex)

    if target is not None:
        rcs_linear = 10.0 ** (target.rcs_dbsm / 10.0)
        amplitude  = np.sqrt(rcs_linear)

        for chirp_idx, t_s in enumerate(t_slow):
            # ── Time-varying range ─────────────────────────────────────────────
            # Bulk motion (constant velocity)
            r_bulk = target.velocity_mps * t_s

            # Breathing displacement
            r_breath = target.breathing_amplitude_m * np.sin(
                2.0 * np.pi * target.breathing_rate_hz * t_s
            )

            # Heartbeat displacement (superimposed)
            r_heart = 0.0
            if target.enable_heartbeat:
                r_heart = target.heartbeat_amplitude_m * np.sin(
                    2.0 * np.pi * target.heartbeat_rate_hz * t_s
                )

            r_total = target.range_m + r_bulk + r_breath + r_heart

            # ── Beat signal ────────────────────────────────────────────────────
            # Round-trip delay
            tau = 2.0 * r_total / c

            # Beat frequency (range-proportional)
            f_beat = config.slope * tau

            # Carrier phase at this chirp (used for phase-based vitals extraction)
            phi_carrier = 2.0 * np.pi * config.center_freq * tau

            # Complex beat signal for this chirp
            beat = amplitude * np.exp(
                1j * (2.0 * np.pi * f_beat * t_fast - phi_carrier)
            )
            frame[chirp_idx] += beat

    # ── AWGN noise ─────────────────────────────────────────────────────────────
    if target is not None and np.max(np.abs(frame)) > 0:
        signal_power = np.mean(np.abs(frame) ** 2)
    else:
        signal_power = 1.0

    noise_power  = signal_power / (10.0 ** (snr_db / 10.0))
    noise_std    = np.sqrt(noise_power / 2.0)
    noise        = noise_std * (
        rng.standard_normal((num_chirps, num_samples))
        + 1j * rng.standard_normal((num_chirps, num_samples))
    )
    frame += noise

    return frame


# ── Chirp metadata helper ──────────────────────────────────────────────────────

def get_axes(config: ChirpConfig) -> dict:
    """
    Pre-compute the physical axis arrays for a radar frame processed with
    range-FFT (num_samples/2 bins) and Doppler-FFT (num_chirps bins).

    Returns
    -------
    dict with:
        range_axis    : np.ndarray [m]  — one entry per range bin
        velocity_axis : np.ndarray [m/s] — one entry per Doppler bin (fftshift order)
        range_res     : float [m]
        velocity_res  : float [m/s]
        max_range     : float [m]
        max_velocity  : float [m/s]
    """
    n_range   = config.num_samples // 2
    n_doppler = config.num_chirps

    # Range axis: df = fs/N → range = c·df / (2·k) per bin
    df_fast    = config.sample_rate / config.num_samples
    range_per_bin = (3e8 / 2.0) * df_fast / config.slope
    range_axis = np.arange(n_range) * range_per_bin

    # Doppler axis: fftshift so 0 velocity is in the centre
    prf         = 1.0 / config.chirp_duration          # pulse repetition frequency
    doppler_freqs = np.fft.fftshift(np.fft.fftfreq(n_doppler, d=1.0 / prf))
    velocity_axis = doppler_freqs * config.wavelength / 2.0

    return {
        "range_axis":    range_axis,
        "velocity_axis": velocity_axis,
        "range_res":     config.range_resolution,
        "velocity_res":  config.velocity_resolution,
        "max_range":     config.max_range,
        "max_velocity":  config.max_velocity,
    }
def simulate_vital_sign_phase_sequence(
    target:         TargetConfig,
    center_freq:    float = 77e9,
    duration_s:     float = 10.0,
    frame_rate_hz:  float = 20.0,
    phase_noise_std: float = 0.05,
    rng_seed:       int = None,
) -> dict:
    """
    Simulate the slow-time (frame-rate) phase signal used for vital sign
    extraction. This is a SEPARATE timescale from the chirp-to-chirp axis
    used for Range-Doppler processing.

    Each "sample" here represents one full radar FRAME (not one chirp) —
    e.g. the phase of the target's range bin extracted once per frame.
    Frame rate is typically 10-20 Hz, giving enough samples over several
    seconds to resolve breathing (~0.2-0.5 Hz) and heartbeat (~0.8-2 Hz).

    Returns
    -------
    dict with:
        phase_signal : ndarray, unwrapped phase, DC-removed
        time_axis    : ndarray, seconds
        fs           : float, sample rate = frame_rate_hz
    """
    c = 3e8
    rng = np.random.default_rng(rng_seed)

    n_samples = int(duration_s * frame_rate_hz)
    t = np.arange(n_samples) / frame_rate_hz

    r_breath = target.breathing_amplitude_m * np.sin(
        2.0 * np.pi * target.breathing_rate_hz * t
    )
    r_heart = np.zeros_like(t)
    if target.enable_heartbeat:
        r_heart = target.heartbeat_amplitude_m * np.sin(
            2.0 * np.pi * target.heartbeat_rate_hz * t
        )

    r_total = target.range_m + target.velocity_mps * t + r_breath + r_heart
    tau = 2.0 * r_total / c

    # Carrier phase — this is the sensitive term: Δφ = 4π·Δr/λ
    phase = 2.0 * np.pi * center_freq * tau
    phase += rng.normal(0.0, phase_noise_std, size=n_samples)  # phase noise

    phase_unwrapped = np.unwrap(phase)
    phase_unwrapped -= np.mean(phase_unwrapped)

    return {
        "phase_signal": phase_unwrapped,
        "time_axis":    t,
        "fs":           frame_rate_hz,
    }