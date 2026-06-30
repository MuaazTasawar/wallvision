"""
TI mmWave (IWR1443 / xWR series) Raw ADC Dataset Loader
=========================================================
Parses raw binary captures from Texas Instruments mmWave radar
evaluation kits (DCA1000 capture card format) into a complex
(num_chirps, num_samples) frame compatible with the rest of the
WallVision DSP pipeline.

DCA1000 raw capture format
───────────────────────────
  Each ADC sample is stored as interleaved 16-bit signed integers:
    [I0, Q0, I1, Q1, I2, Q2, ...]   (for complex/IQ mode, 2 RX example)

  For a single-RX, complex (IQ) capture, the file is a flat sequence:
    I, Q, I, Q, ...  repeated for (num_chirps × num_samples) pairs.

  WallVision supports the common single-RX complex capture layout.
  Real multi-RX/multi-TX captures (e.g. full 4RX MIMO) would need
  channel de-interleaving — out of scope for this educational pipeline,
  noted clearly to the user if their file doesn't match expected size.

Reference: TI DCA1000EVM Data Capture Card User's Guide.
"""

import numpy as np
from typing import Optional


class DatasetLoadError(Exception):
    """Raised when a .bin file cannot be parsed into the expected shape."""
    pass


def load_ti_mmwave_bin(
    file_bytes:   bytes,
    num_chirps:   int,
    num_samples:  int,
) -> np.ndarray:
    """
    Parse a raw TI DCA1000 .bin capture into a complex radar frame.

    Parameters
    ----------
    file_bytes  : raw bytes read from the uploaded .bin file
    num_chirps  : expected number of chirps in the capture
    num_samples : expected ADC samples per chirp

    Returns
    -------
    frame : complex ndarray, shape (num_chirps, num_samples)

    Raises
    ------
    DatasetLoadError if the byte count doesn't match the expected
    (num_chirps × num_samples × 2 int16 values × 2 bytes) size.
    """
    # Each complex sample = 2 int16 values (I, Q) = 4 bytes
    expected_samples_total = num_chirps * num_samples
    expected_bytes = expected_samples_total * 4

    if len(file_bytes) < expected_bytes:
        raise DatasetLoadError(
            f"File too small for declared shape ({num_chirps} chirps x {num_samples} samples). "
            f"Expected at least {expected_bytes} bytes, got {len(file_bytes)}. "
            f"Try adjusting num_chirps/num_samples to match your capture configuration, "
            f"or this file may use a multi-RX interleaved layout not yet supported."
        )

    # Read as int16, little-endian (TI DCA1000 default)
    raw = np.frombuffer(file_bytes[:expected_bytes], dtype="<i2")

    # Reshape into I/Q pairs
    iq_pairs = raw.reshape(-1, 2).astype(np.float64)
    complex_samples = iq_pairs[:, 0] + 1j * iq_pairs[:, 1]

    # Reshape into (num_chirps, num_samples)
    frame = complex_samples[:expected_samples_total].reshape(num_chirps, num_samples)

    return frame


def validate_capture_size(
    file_size_bytes: int,
    num_chirps:      int,
    num_samples:     int,
) -> dict:
    """
    Pre-flight check before attempting a full parse — used by the API
    to give the user a clear error before processing.

    Returns
    -------
    dict: {valid, expected_bytes, actual_bytes, message}
    """
    expected_bytes = num_chirps * num_samples * 4
    valid = file_size_bytes >= expected_bytes

    if valid:
        message = "File size matches expected capture dimensions."
    else:
        message = (
            f"File size mismatch: expected >= {expected_bytes} bytes "
            f"for {num_chirps} chirps x {num_samples} samples, got {file_size_bytes}."
        )

    return {
        "valid":          valid,
        "expected_bytes": expected_bytes,
        "actual_bytes":   file_size_bytes,
        "message":        message,
    }


def estimate_frame_dims_from_filesize(
    file_size_bytes: int,
    num_samples:     int = 256,
) -> Optional[int]:
    """
    Best-effort guess at num_chirps if the user doesn't know their
    capture configuration — assumes a fixed num_samples (ADC samples/chirp)
    and solves for whole-number num_chirps from total file size.

    Returns
    -------
    num_chirps : int, or None if file size doesn't divide evenly
    """
    bytes_per_chirp = num_samples * 4
    if file_size_bytes % bytes_per_chirp != 0:
        return None
    return file_size_bytes // bytes_per_chirp