"""
OS-CFAR Detector (Ordered Statistics CFAR)
==========================================
Detects targets in a 2D Range-Doppler map by adaptively estimating
the noise floor around each cell under test (CUT) using its neighbours.

Algorithm (1D per row, applied across the full 2D map)
───────────────────────────────────────────────────────
For each CUT at (d, r):

  1.  Collect training cells in a window around CUT,
      excluding guard cells immediately adjacent to CUT.

        [TC TC TC | GC GC | CUT | GC GC | TC TC TC]
         ◄──TC──►  ◄─GC─►         ◄─GC─►  ◄──TC──►

  2.  Sort the M training-cell magnitudes.

  3.  OS estimate: use the K-th largest (K = ceil(k_rank × M)).
      OS-CFAR is robust to multiple targets in the training window
      (unlike CA-CFAR which averages all training cells).

  4.  Threshold = α × z_K
      where α is derived from the desired PFA:
          PFA ≈ C(M,K) × (1 + α)^(−(M−K+1)) × product term
      In practice we use the simplified scalar:
          α = K × (PFA^(−1/K) − 1)      [common approximation]

  5.  Detection: CUT > threshold

Post-processing
───────────────
  Non-Maximum Suppression (NMS): among overlapping detections within
  radius r, keep only the local maximum to avoid clustered duplicates.

References
──────────
  Richards, M.A. (2014). Fundamentals of Radar Signal Processing, 2nd ed.
  Rohling, H. (1983). Radar CFAR Thresholding in Clutter and Multiple
    Target Situations. IEEE Trans. AES-19(4).
"""

import numpy as np
from typing import List


# ── Threshold factor ───────────────────────────────────────────────────────────

def _cfar_alpha(k: int, pfa: float) -> float:
    """
    Compute OS-CFAR threshold multiplier α.

    Simplified closed-form approximation (Rohling 1983):
        α = K · (PFA^(−1/K) − 1)

    Parameters
    ----------
    k   : rank index (number of training cells used as noise estimate)
    pfa : desired probability of false alarm

    Returns
    -------
    alpha : float  (multiply by noise estimate to get detection threshold)
    """
    if k <= 0:
        return 1.0
    return float(k) * (pfa ** (-1.0 / k) - 1.0)


# ── 2D OS-CFAR ────────────────────────────────────────────────────────────────

def os_cfar_2d(
    rd_map:         np.ndarray,
    guard_cells:    int   = 2,
    training_cells: int   = 8,
    k_rank:         float = 0.75,
    pfa:            float = 1e-4,
) -> List[dict]:
    """
    2D Ordered Statistics CFAR on the Range-Doppler magnitude map.

    The sliding window moves across every (doppler, range) cell.
    Training cells are taken from a 1D strip along the range axis
    (constant Doppler row) — this is range-only CFAR, which is
    appropriate here because target velocities are small (≈ 0 m/s)
    and most energy is concentrated in a single Doppler bin.

    Parameters
    ----------
    rd_map         : 2D float ndarray (num_doppler, num_range) — LINEAR magnitude
    guard_cells    : guard cells each side of CUT (exclude from training)
    training_cells : training cells each side of guard region
    k_rank         : fraction of training cells to use as OS estimate (0–1)
    pfa            : desired probability of false alarm

    Returns
    -------
    detections : list of dicts, each containing:
        range_bin   : int
        doppler_bin : int
        snr_db      : float
        power       : float   (raw linear magnitude of CUT)
        threshold   : float   (detection threshold applied)
    """
    n_doppler, n_range = rd_map.shape

    gc     = guard_cells
    tc     = training_cells
    margin = gc + tc          # total one-sided window extent

    # Number of training cells per side × 2 sides
    m = training_cells * 2
    k = max(1, int(np.ceil(k_rank * m)))
    alpha = _cfar_alpha(k, pfa)

    detections: List[dict] = []

    # Iterate over valid cells (skip border where window would exceed map)
    for d_idx in range(n_doppler):
        for r_idx in range(margin, n_range - margin):

            cut = rd_map[d_idx, r_idx]

            # ── Collect training cells (range axis, same Doppler row) ──────────
            # Left training window: [r_idx - margin : r_idx - gc]
            left_cells  = rd_map[d_idx, r_idx - margin : r_idx - gc]
            # Right training window: [r_idx + gc + 1 : r_idx + margin + 1]
            right_cells = rd_map[d_idx, r_idx + gc + 1 : r_idx + margin + 1]

            training = np.concatenate([left_cells, right_cells])
            if training.size == 0:
                continue

            # ── OS estimate: K-th order statistic ─────────────────────────────
            sorted_training = np.sort(training)
            k_idx           = min(k - 1, len(sorted_training) - 1)
            noise_estimate  = sorted_training[k_idx]

            if noise_estimate < 1e-15:
                continue

            threshold = alpha * noise_estimate

            if cut > threshold:
                snr_db = 20.0 * np.log10(cut / noise_estimate)
                detections.append({
                    "range_bin":   int(r_idx),
                    "doppler_bin": int(d_idx),
                    "snr_db":      float(snr_db),
                    "power":       float(cut),
                    "threshold":   float(threshold),
                })

    # ── Non-Maximum Suppression ────────────────────────────────────────────────
    return _nms(detections, nms_range_radius=3, nms_doppler_radius=2)


# ── Non-Maximum Suppression ────────────────────────────────────────────────────

def _nms(
    detections:         List[dict],
    nms_range_radius:   int = 3,
    nms_doppler_radius: int = 2,
) -> List[dict]:
    """
    Suppress duplicate detections within a neighbourhood.

    Sort detections by descending power.  For the strongest detection,
    mark all weaker candidates within (nms_range_radius, nms_doppler_radius)
    as suppressed.  Repeat for the next unsuppressed candidate.

    Returns only unsuppressed detections, still sorted by descending power.
    """
    if not detections:
        return []

    # Sort by power descending so we always keep the strongest in a cluster
    sorted_dets = sorted(detections, key=lambda x: x["power"], reverse=True)

    suppressed = [False] * len(sorted_dets)
    kept: List[dict] = []

    for i, det_i in enumerate(sorted_dets):
        if suppressed[i]:
            continue
        kept.append(det_i)
        # Suppress weaker neighbours
        for j in range(i + 1, len(sorted_dets)):
            if suppressed[j]:
                continue
            det_j = sorted_dets[j]
            dr = abs(det_i["range_bin"]   - det_j["range_bin"])
            dd = abs(det_i["doppler_bin"] - det_j["doppler_bin"])
            if dr <= nms_range_radius and dd <= nms_doppler_radius:
                suppressed[j] = True

    return kept


# ── Threshold map (for visualisation) ─────────────────────────────────────────

def compute_threshold_map(
    rd_map:         np.ndarray,
    guard_cells:    int   = 2,
    training_cells: int   = 8,
    k_rank:         float = 0.75,
    pfa:            float = 1e-4,
) -> np.ndarray:
    """
    Return a 2D array of the CFAR threshold value at every range cell
    (same Doppler rows as rd_map).  Used to visualise the adaptive noise floor.

    Returns
    -------
    threshold_map : float ndarray, same shape as rd_map
                    Values outside the valid margin are set to NaN.
    """
    n_doppler, n_range = rd_map.shape
    gc     = guard_cells
    tc     = training_cells
    margin = gc + tc
    m      = training_cells * 2
    k      = max(1, int(np.ceil(k_rank * m)))
    alpha  = _cfar_alpha(k, pfa)

    threshold_map = np.full_like(rd_map, np.nan, dtype=float)

    for d_idx in range(n_doppler):
        for r_idx in range(margin, n_range - margin):
            left_cells  = rd_map[d_idx, r_idx - margin : r_idx - gc]
            right_cells = rd_map[d_idx, r_idx + gc + 1 : r_idx + margin + 1]
            training    = np.concatenate([left_cells, right_cells])
            if training.size == 0:
                continue
            sorted_t    = np.sort(training)
            k_idx       = min(k - 1, len(sorted_t) - 1)
            noise_est   = sorted_t[k_idx]
            threshold_map[d_idx, r_idx] = alpha * noise_est

    return threshold_map


# ── Single-row 1D CFAR (used by WebSocket streamer for step card) ─────────────

def os_cfar_1d(
    range_profile:  np.ndarray,
    guard_cells:    int   = 2,
    training_cells: int   = 8,
    k_rank:         float = 0.75,
    pfa:            float = 1e-4,
) -> List[dict]:
    """
    1D OS-CFAR on a range profile vector.
    Lightweight version for real-time WebSocket step streaming.

    Parameters
    ----------
    range_profile : 1D float ndarray (linear magnitude)

    Returns
    -------
    list of dicts: {range_bin, snr_db, power}
    """
    n_range = len(range_profile)
    gc      = guard_cells
    tc      = training_cells
    margin  = gc + tc
    m       = tc * 2
    k       = max(1, int(np.ceil(k_rank * m)))
    alpha   = _cfar_alpha(k, pfa)

    detections: List[dict] = []

    for r_idx in range(margin, n_range - margin):
        cut         = range_profile[r_idx]
        left_cells  = range_profile[r_idx - margin : r_idx - gc]
        right_cells = range_profile[r_idx + gc + 1 : r_idx + margin + 1]
        training    = np.concatenate([left_cells, right_cells])
        if training.size == 0:
            continue
        sorted_t    = np.sort(training)
        k_idx       = min(k - 1, len(sorted_t) - 1)
        noise_est   = sorted_t[k_idx]
        if noise_est < 1e-15:
            continue
        threshold = alpha * noise_est
        if cut > threshold:
            snr_db = 20.0 * np.log10(cut / noise_est)
            detections.append({
                "range_bin": int(r_idx),
                "snr_db":    float(snr_db),
                "power":     float(cut),
            })

    return _nms_1d(detections, radius=3)


def _nms_1d(detections: List[dict], radius: int = 3) -> List[dict]:
    """1D NMS for range-profile detections."""
    if not detections:
        return []
    sorted_dets = sorted(detections, key=lambda x: x["power"], reverse=True)
    suppressed  = [False] * len(sorted_dets)
    kept: List[dict] = []
    for i, det_i in enumerate(sorted_dets):
        if suppressed[i]:
            continue
        kept.append(det_i)
        for j in range(i + 1, len(sorted_dets)):
            if suppressed[j]:
                continue
            if abs(det_i["range_bin"] - sorted_dets[j]["range_bin"]) <= radius:
                suppressed[j] = True
    return kept