# WallVision

> A complete FMCW radar signal processing pipeline — from raw chirp simulation to through-wall human detection and contactless breathing/heart rate extraction — built entirely in software, with zero RF hardware required.

---

## Table of Contents

1. [What This Project Is](#what-this-project-is)
2. [Why This Project Exists](#why-this-project-exists)
3. [How FMCW Radar Works — The Physics](#how-fmcw-radar-works--the-physics)
4. [The Full Signal Processing Pipeline](#the-full-signal-processing-pipeline)
5. [Tech Stack](#tech-stack)
6. [Project Structure](#project-structure)
7. [Backend — Module by Module](#backend--module-by-module)
8. [Frontend — Component by Component](#frontend--component-by-component)
9. [API Reference](#api-reference)
10. [WebSocket Protocol](#websocket-protocol)
11. [Getting Started](#getting-started)
12. [Using the App](#using-the-app)
13. [Working With Real Radar Hardware Data](#working-with-real-radar-hardware-data)
14. [Design Decisions & Known Limitations](#design-decisions--known-limitations)
15. [Phase Build History](#phase-build-history)
16. [Troubleshooting](#troubleshooting)
17. [Roadmap Ideas](#roadmap-ideas)
18. [License](#license)

---

## What This Project Is

WallVision is a full-stack simulation and processing platform for **FMCW (Frequency-Modulated Continuous Wave) radar** — the same class of radar technology used in automotive collision-avoidance systems, military through-wall surveillance, contactless patient monitoring, and gesture-recognition sensors.

The project does three things end to end:

1. **Generates physically accurate synthetic radar data** — simulating what a real 77 GHz mmWave radar chip would measure when pointed at a stationary or moving human target, including the microscopic chest motion caused by breathing and heartbeat.
2. **Processes that data through a complete DSP pipeline** — the exact sequence of mathematical operations a real radar system performs: range resolution via FFT, velocity resolution via a second FFT, adaptive noise-floor thresholding to separate real targets from clutter, and time-frequency analysis to extract vital signs from sub-millimetre body motion.
3. **Visualizes every stage live** — either as a single "run and see the result" simulation, or as an animated step-by-step stream over WebSocket showing each DSP stage completing in real time, exactly as a radar engineer would watch a live console.

It also accepts **real raw data** captured from Texas Instruments mmWave radar evaluation kits (the IWR1443 and similar DCA1000-based capture hardware), so the same pipeline that processes simulated data can process an actual physical radar recording.

## Why This Project Exists

Radar digital signal processing is a field with disproportionately high real-world impact and disproportionately low public/educational tooling. It underlies:

- **Search-and-rescue**: locating survivors trapped behind rubble or walls by detecting their breathing
- **Automotive safety**: every modern car with adaptive cruise control or blind-spot detection uses an FMCW radar chip running this exact Range-Doppler-CFAR pipeline
- **Contactless health monitoring**: hospitals and elder-care facilities use phase-based vital sign radar to monitor patients without wires or wearables
- **Defense and security**: through-wall surveillance for law enforcement and military applications

Despite this, almost no public, accessible, from-scratch implementations of the *full* pipeline exist for students or engineers to learn from. Most public radar projects either wrap a vendor's closed SDK or only demonstrate a single isolated stage (e.g. just an FFT, without CFAR or micro-Doppler). WallVision implements every stage from first principles — the actual chirp physics, the actual CFAR statistics, the actual wavelet mathematics — so the full chain from raw signal to a clinical-grade "17 breaths per minute" readout is visible, inspectable, and modifiable.

## How FMCW Radar Works — The Physics

This section explains the core physics that every module in this repository implements, since understanding it is the entire point of the project.

### The Chirp

An FMCW radar doesn't transmit a single frequency — it transmits a **chirp**: a signal whose frequency sweeps linearly upward over a short time window (tens of microseconds), then resets and repeats. If you wrote it as a complex exponential:

```
s_tx(t) = exp( j · 2π · ( fc·t + (BW / 2Tc)·t² ) )
```

where `fc` is the centre frequency (77 GHz in this project — the standard automotive/industrial mmWave band), `BW` is the swept bandwidth, and `Tc` is the chirp duration.

### The Beat Signal

When this chirp reflects off a target at distance `r` and returns to the receiver, it arrives delayed by the round-trip travel time `τ = 2r/c`. The receiver mixes the transmitted and received signals together (a process called *dechirping*), which produces a much simpler signal: a single tone whose frequency is directly proportional to the target's distance.

```
s_beat(t) = s_tx(t) · conj(s_rx(t)) = exp( j·2π·f_beat·t − j·φ₀ )

f_beat = (BW / Tc) · τ = 2·BW·r / (c·Tc)     ← this is why beat frequency encodes range
φ₀     = 2π·fc·τ                              ← this carrier phase term encodes vital signs
```

This is the elegant trick at the heart of all FMCW radar: instead of needing to time a return pulse with picosecond precision (as pulsed radar does), you just need to measure a low-frequency tone with an ordinary ADC — and that tone's frequency tells you the range.

### Range Resolution

Taking an FFT of the beat signal across "fast time" (samples within one chirp) converts that beat frequency into a range bin. The achievable resolution is purely a function of bandwidth:

```
range_resolution = c / (2 · BW)
```

This project defaults to 1 GHz of bandwidth, giving a 15 cm range resolution — meaning two targets closer together than 15 cm cannot be distinguished as separate range bins.

### Doppler / Velocity Resolution

A single chirp tells you range. To get *velocity*, the radar transmits many chirps back-to-back (this project defaults to 128) and looks at how the *phase* of the beat signal at a given range bin changes from chirp to chirp ("slow time"). A moving target shifts that phase by a tiny, consistent amount each chirp — a second FFT across the chirp axis (rather than the sample axis) turns that phase progression into a velocity measurement, exactly the same way a Doppler shift works for sound or light.

```
velocity_resolution = λ / (2 · N · Tc)
```

where `N` is the number of chirps per frame and `λ` is the radar wavelength (≈3.9 mm at 77 GHz).

### Why This Same Mechanism Detects a Heartbeat

This is the part that makes through-wall vital sign sensing possible, and it's worth dwelling on because it's genuinely counter-intuitive: the radar's *range resolution* is 15 cm, but it can detect chest motion of **2 millimetres** (breathing) and **0.4 millimetres** (heartbeat) — motion three orders of magnitude smaller than a single range bin.

The reason is that range resolution and phase sensitivity are two completely different things. While the FFT can only tell you *which 15 cm bin* a target is in, the **carrier phase term** `φ₀ = 2π·fc·τ` inside that bin is exquisitely sensitive to sub-wavelength displacement:

```
Δφ = 4π · Δr / λ
```

At λ ≈ 3.9 mm, a 2 mm chest displacement produces a phase shift of roughly 6.4 radians — easily measurable, even though the underlying range bin itself never changes. This is the same principle used in InSAR satellite imaging to detect millimetre-scale ground subsidence, and the same principle medical-grade contactless vital sign monitors use. Tracking this phase value across many consecutive *frames* (not chirps — a slower timescale, ~10-20 Hz) and running a bandpass filter and FFT on that phase sequence is exactly how WallVision extracts a breathing rate in BPM and a heart rate in BPM.

### CFAR — Separating Real Targets From Noise

A raw Range-Doppler map is noisy: thermal noise, clutter, and multipath reflections all produce energy across the map, and a fixed power threshold either misses weak real targets or floods you with false detections depending on the (constantly-changing) noise floor. **CFAR (Constant False Alarm Rate)** detection solves this by computing an *adaptive* threshold around every cell, based on the actual local noise level around it — guard cells immediately next to the cell under test are excluded (so the target's own energy doesn't pollute the noise estimate), and a ring of training cells further out estimates the local noise floor. This project uses **OS-CFAR (Ordered Statistics CFAR)**, which picks a specific rank-ordered value (rather than a simple average) from the training cells, making it robust even when multiple targets sit close together in the same window.

### Why CWT Instead of a Standard FFT for Vital Signs

Breathing rate naturally varies in depth and timing — it's not a perfectly periodic signal. A standard FFT/STFT has a fixed time-frequency resolution tradeoff across the whole signal. A **Continuous Wavelet Transform (CWT)** with a complex Morlet wavelet instead scales its analysis window with frequency: tight time resolution at high frequencies (good for catching the faster, more transient heartbeat), wide time resolution at low frequencies (good for averaging out breath-to-breath variability). This is the standard tool used in published vital-sign radar research, and it's what produces the spectrogram visualization in this project's dashboard — you can visually see the breathing band and heartbeat band as two separate horizontal stripes of energy across time.

## The Full Signal Processing Pipeline

Putting all of the above together, here is the exact sequence WallVision executes on every run, matching the six animated stages shown in the Live Pipeline view:

```
 [0] CHIRP GENERATION
     Simulate (or load from a real .bin capture) the complex FMCW
     beat signal for every chirp in the frame, with realistic AWGN
     noise added at the configured SNR.
        │
        ▼
 [1] RANGE FFT
     Window the fast-time axis (Hann/Blackman/rectangular), FFT
     each chirp individually. Produces a range profile per chirp —
     this is "where are things, roughly."
        │
        ▼
 [2] DOPPLER FFT
     Window the slow-time axis, FFT across chirps at each range
     bin. Produces the full 2D Range-Doppler magnitude map —
     "where are things, AND how fast are they moving."
        │
        ▼
 [3] OS-CFAR DETECTION
     Slide an adaptive noise-floor estimator across the map.
     Anything exceeding its local adaptive threshold is flagged as
     a detection. Non-maximum suppression collapses clustered
     detections from the same physical target into one.
        │
        ▼
 [4] MICRO-DOPPLER CWT  (only runs if a target was detected)
     Extract the slow, frame-rate phase sequence at the detected
     target's range bin over a multi-second window. Run a complex
     Morlet CWT across it to produce a time-frequency spectrogram
     showing breathing and heartbeat oscillation bands.
        │
        ▼
 [5] VITAL SIGN EXTRACTION
     Bandpass-filter the phase sequence into the breathing band
     (0.1–0.6 Hz) and heartbeat band (0.8–2.2 Hz) separately, then
     zero-padded FFT each band to pull out a precise BPM estimate
     for both.
```

Every one of these six stages is independently inspectable in the Live Pipeline dashboard view, lighting up as it completes when streamed over WebSocket.

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| DSP Engine | Python 3.11, NumPy, SciPy | Native, fast array operations for FFTs, filtering, and windowing |
| Wavelet Transform | PyWavelets | Reference-quality complex Morlet CWT implementation |
| Backend API | FastAPI, Uvicorn | Async REST + native WebSocket support, automatic OpenAPI docs |
| Data Validation | Pydantic | Type-safe request/response schemas shared between REST and WebSocket |
| Frontend Framework | Next.js 14 (App Router) | Fast iteration, file-based routing, easy client/server component split |
| Visualization | Plotly.js (react-plotly.js) | The only JS charting library that handles dense 2D heatmaps (Range-Doppler maps, spectrograms) well |
| Styling | Tailwind CSS + CSS custom properties | Utility-first styling with a custom light/dark theme token system |
| State Management | React hooks (no external state library) | App is small enough that custom hooks (`usePipeline`, `useWebSocket`, `useTheme`) are sufficient |

## Project Structure

```
wallvision/
├── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── chirp_simulator.py       ← FMCW beat signal generation + target model + vital-sign phase sequence simulator
│   │   ├── range_doppler.py         ← 2D FFT: range FFT + Doppler FFT, axis computation
│   │   ├── cfar.py                  ← OS-CFAR 2D/1D detector + non-maximum suppression
│   │   ├── micro_doppler.py         ← Complex Morlet CWT spectrogram + dominant frequency extraction
│   │   ├── vital_signs.py           ← Bandpass filtering + FFT-based BPM extraction
│   │   └── dataset_loader.py        ← TI DCA1000 / IWR1443 raw .bin capture parser
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                ← REST endpoints: /api/simulate, /api/upload-dataset, /api/pipeline-steps
│   │   └── websocket.py             ← /ws/radar-stream — live, stage-by-stage pipeline streamer
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py               ← Pydantic request/response models shared by REST and WS
│   ├── main.py                      ← FastAPI app instance, CORS config, router mounting
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.jsx           ← Root HTML shell, metadata
│   │   │   ├── page.jsx             ← Main dashboard — nav routing, wires every panel together
│   │   │   └── globals.css          ← Light/dark theme CSS variables, base component classes
│   │   ├── components/
│   │   │   ├── Sidebar.jsx          ← Left navigation (Dashboard / Live Pipeline / Dataset Upload)
│   │   │   ├── ThemeToggle.jsx      ← Sun/moon icon button, toggles light/dark theme
│   │   │   ├── ChirpConfig.jsx      ← All scene/radar configuration sliders
│   │   │   ├── RangeDopplerMap.jsx  ← Plotly heatmap of the Range-Doppler magnitude map + CFAR markers
│   │   │   ├── TargetPanel.jsx      ← Detection list + breathing/heart rate readout cards
│   │   │   ├── PipelineSteps.jsx    ← Animated six-stage live pipeline tracker
│   │   │   ├── MicroDopplerPlot.jsx ← Plotly CWT spectrogram with breathing/heartbeat band overlays
│   │   │   ├── VitalSignsPanel.jsx  ← Raw vs. bandpass-filtered phase signal chart
│   │   │   └── DatasetUploader.jsx  ← Drag-drop .bin file uploader with capture shape inputs
│   │   ├── hooks/
│   │   │   ├── usePipeline.js       ← REST-based simulate/upload state management
│   │   │   ├── useWebSocket.js      ← WebSocket connection + live per-stage state updates
│   │   │   └── useTheme.js          ← Light/dark theme persistence (localStorage + OS preference)
│   │   └── lib/
│   │       └── api.js               ← Axios client, endpoint wrappers, default config object
│   ├── next.config.mjs              ← Excludes Plotly from the SSR server bundle
│   ├── tailwind.config.ts           ← Theme token mapping (class-based dark mode)
│   └── package.json
├── .gitignore
└── README.md
```

## Backend — Module by Module

### `core/chirp_simulator.py`
Defines `ChirpConfig` (radar hardware parameters: bandwidth, centre frequency, chirp duration, sample rate, chirp/sample counts) as a dataclass with computed properties for range resolution, velocity resolution, max range, and max velocity — these formulas are derived directly in the docstrings. `TargetConfig` defines a simulated human target: range, bulk velocity, breathing rate/amplitude, heartbeat rate/amplitude. `simulate_frame()` generates the full complex beat-signal array for one radar frame, including realistic AWGN noise scaled to a target SNR. `simulate_vital_sign_phase_sequence()` is a separate, slower-timescale simulator specifically for vital signs — it operates at frame-rate (e.g. 20 Hz across several seconds) rather than chirp-rate (kHz, across milliseconds), because breathing and heartbeat periods (multiple seconds) cannot be resolved within the duration of a single radar frame.

### `core/range_doppler.py`
Implements the two-stage 2D FFT pipeline: windows and FFTs the fast-time axis to get per-chirp range profiles, then windows and FFTs the slow-time axis to get the full Range-Doppler magnitude map, with `fftshift` applied so zero-velocity sits at the centre of the map. Also computes the physical range and velocity axis arrays so every bin in the output maps to real-world metres and metres/second.

### `core/cfar.py`
Implements 2D and 1D OS-CFAR detection. For every cell under test, it gathers a ring of training cells (excluding adjacent guard cells), sorts them, and picks a rank-ordered value as the local noise estimate. The detection threshold is derived from a closed-form approximation of the desired probability-of-false-alarm (PFA). Detected cells are passed through non-maximum suppression to collapse multiple adjacent detections of the same physical target into a single reported detection.

### `core/micro_doppler.py`
Extracts the unwrapped slow-time phase signal at a target's range bin, then computes a complex Morlet continuous wavelet transform across a log-spaced bank of frequency scales (0.1–3.0 Hz, covering both breathing and heartbeat bands). Also includes a helper to find the dominant frequency within a specified band, time-averaged across the whole spectrogram for a more robust single-number estimate than picking a single FFT bin.

### `core/vital_signs.py`
Runs zero-phase Butterworth bandpass filters on the phase signal — one passband for breathing (0.1–0.6 Hz), one for heartbeat (0.8–2.2 Hz) — then estimates the dominant frequency in each band via a heavily zero-padded FFT for sub-BPM precision. Includes a detection-confidence check (the breathing peak must exceed a minimum power threshold relative to the noise floor) before reporting a result, so the UI correctly shows "no vitals detected" rather than a meaningless number when the signal is too weak.

### `core/dataset_loader.py`
Parses raw `.bin` captures from a TI DCA1000 capture card (the standard data-acquisition hardware paired with TI's IWR-series mmWave evaluation boards). These files store interleaved 16-bit signed I/Q sample pairs with no header describing their own shape, so the loader requires the user to specify `num_chirps` and `num_samples` matching their capture configuration, with a pre-flight byte-count validation that gives a clear error message if the declared shape doesn't match the actual file size.

### `api/routes.py`
Three REST endpoints: `GET /api/pipeline-steps` returns static metadata describing each of the six DSP stages (used to drive UI step descriptions and formulas); `POST /api/simulate` runs the full pipeline on a synthetically generated scene from a `ChirpConfigRequest` payload; `POST /api/upload-dataset` runs the same pipeline on an uploaded `.bin` file. Both POST endpoints share a single `_run_full_pipeline()` function so the simulate and upload paths can never silently diverge in behaviour.

### `api/websocket.py`
A single `/ws/radar-stream` WebSocket endpoint that, on receiving a JSON config message, runs the pipeline stage by stage, sending one JSON message per completed stage (with a small artificial delay so the frontend's stage-by-stage animation is visible rather than instantaneous) followed by a final summary message.

### `models/schemas.py`
Every Pydantic model used across the REST and WebSocket APIs: `ChirpConfigRequest` (the full set of user-tunable parameters, all with realistic min/max bounds), `DetectionResult`, `PipelineStep`, and `RadarFrameResponse` (the complete pipeline output, including optional fields for vital signs and micro-Doppler data that are only populated when a target is actually detected).

## Frontend — Component by Component

### `hooks/usePipeline.js`
Owns the radar configuration state object and exposes `runSimulation()` and `runUpload()`, both of which call the REST API and store the resulting `RadarFrameResponse` in state, along with loading and error state.

### `hooks/useWebSocket.js`
Opens a persistent WebSocket connection to `/ws/radar-stream` on mount, accumulates incoming `step` messages into a `steps` object keyed by stage index, and exposes a `runPipeline(config)` function to kick off a live run. Includes a guard against a React Strict Mode dev-only quirk where the first (throwaway) WebSocket connection's `onerror` can fire a misleading "connection failed" message before the real, persistent connection takes over.

### `hooks/useTheme.js`
Reads the user's previously saved theme preference from `localStorage`, falling back to the OS-level `prefers-color-scheme` media query on first load. Toggling flips a `dark` class on the `<html>` element (Tailwind's class-based dark mode strategy) and persists the choice.

### `components/ChirpConfig.jsx`
Every user-tunable radar and scene parameter as a labeled slider: bandwidth, centre frequency, target range, target velocity, SNR, breathing rate, chest displacement amplitude, plus a checkbox to enable/disable heartbeat micro-Doppler. Two action buttons trigger either a single REST simulation or a live WebSocket-streamed run.

### `components/RangeDopplerMap.jsx`
A Plotly heatmap of the Range-Doppler magnitude map, with detected targets overlaid as circular markers annotated with their SNR in dB. The colorscale and grid colors adapt to the active light/dark theme.

### `components/TargetPanel.jsx`
Lists every CFAR detection (range, velocity, SNR) as a card, and — when vital signs were successfully extracted — shows large breathing-rate and heart-rate readouts.

### `components/PipelineSteps.jsx`
The six-stage live pipeline tracker. Each stage card's status dot and styling updates in real time as WebSocket messages arrive, visually distinguishing "not started," "currently processing," and "complete."

### `components/MicroDopplerPlot.jsx`
A Plotly heatmap of the CWT spectrogram (time vs. frequency-in-BPM, log-scaled y-axis), with shaded reference bands marking the typical breathing (12–30 BPM) and heartbeat (48–120 BPM) frequency ranges so the extracted oscillations are visually easy to locate.

### `components/VitalSignsPanel.jsx`
A line chart overlaying the raw, noisy unwrapped phase signal against the same signal after breathing-band bandpass filtering — visually demonstrating what the filter actually does to the data.

### `components/DatasetUploader.jsx`
A drag-and-drop zone for `.bin` files, plus numeric inputs for the capture's chirp/sample dimensions (required because raw DCA1000 captures carry no self-describing header).

### `components/Sidebar.jsx` / `components/ThemeToggle.jsx`
Navigation and theme controls — three views (Dashboard, Live Pipeline, Dataset Upload) and a single icon button that swaps the entire color scheme.

## API Reference

### `GET /api/pipeline-steps`
Returns static metadata for all six pipeline stages (name, description, output, formula). Used to drive any UI element that explains what each stage does.

### `POST /api/simulate`
Runs the full DSP pipeline on a synthetically generated scene.

**Request body** (`ChirpConfigRequest`):
```json
{
  "bandwidth_ghz": 1.0,
  "center_freq_ghz": 77.0,
  "chirp_duration_us": 64.0,
  "num_chirps": 128,
  "num_samples": 256,
  "sample_rate_mhz": 4.0,
  "snr_db": 20.0,
  "target_range_m": 4.0,
  "target_velocity_mps": 0.0,
  "breathing_rate_bpm": 15.0,
  "breathing_amplitude_mm": 2.0,
  "enable_heartbeat": true,
  "window_type": "hann",
  "cfar_guard_cells": 2,
  "cfar_training_cells": 8,
  "cfar_pfa": 0.0001
}
```

**Response** (`RadarFrameResponse`): full Range-Doppler map, range/velocity axes, range profile, list of CFAR detections, and — if a target was detected — breathing rate, heart rate, raw and filtered phase signals, phase FFT spectrum, and the full micro-Doppler CWT spectrogram.

### `POST /api/upload-dataset`
Same response shape as `/api/simulate`, but `multipart/form-data` with a `.bin` file plus the same configuration fields (sent as form fields rather than JSON).

Interactive documentation for both endpoints — with a "Try it out" button to test requests directly from the browser — is auto-generated by FastAPI at `http://localhost:8000/docs` whenever the backend is running.

## WebSocket Protocol

Connect to `ws://localhost:8000/ws/radar-stream` and send a JSON-encoded `ChirpConfigRequest` (same shape as the REST `/api/simulate` body) as a text message. The server responds with a sequence of messages:

```json
{ "type": "step", "index": 0, "name": "Chirp Generation", "data": { ... } }
{ "type": "step", "index": 1, "name": "Range FFT", "data": { ... } }
{ "type": "step", "index": 2, "name": "Doppler FFT", "data": { ... } }
{ "type": "step", "index": 3, "name": "OS-CFAR Detection", "data": { "detections": [...] } }
{ "type": "step", "index": 4, "name": "Micro-Doppler CWT", "data": { ... } }   // only if a target was detected
{ "type": "step", "index": 5, "name": "Vital Sign Extraction", "data": { ... } } // only if a target was detected
{ "type": "complete", "summary": { "target_detected": true, "num_detections": 1, "vitals": { ... } } }
```

If a config message fails Pydantic validation, an `{ "type": "error", "message": "..." }` message is sent instead. The connection stays open for multiple sequential runs — send a new config message at any time to start another pipeline run on the same socket.

## Getting Started

### Prerequisites

- Python 3.11 or later
- Node.js 18+ — on Windows, confirm a 64-bit install with `node -p "process.arch"` (should print `x64`)
- npm

### Clone the Repository

```bash
git clone https://github.com/MuaazTasawar/wallvision.git
cd wallvision
```

### Backend Setup

```bash
cd backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running Both Servers

In one terminal, from `backend/` with the venv active:
```bash
uvicorn main:app --reload --port 8000
```

In a second terminal, from `frontend/`:
```bash
npm run dev
```

Open `http://localhost:3000`. The backend must already be running for the frontend's "Connected" status indicator (top right) to go live and for any simulation or upload action to succeed. Interactive API docs are available separately at `http://localhost:8000/docs`.

## Using the App

The sidebar has three views:

- **Dashboard** — the full radar console: configure a scene with the sliders, click "Run Simulation" for a single REST-based pipeline pass, and see the Range-Doppler heatmap, detection list, breathing/heart rate readouts, micro-Doppler spectrogram, and raw/filtered phase chart all populate at once.
- **Live Pipeline** — click "Run Live Pipeline" to stream the same six DSP stages over WebSocket, watching each stage card light up sequentially as it completes — this is the "watch the radar think" view.
- **Dataset Upload** — drag and drop a real TI DCA1000 `.bin` capture, specify its chirp/sample dimensions, and run it through the identical pipeline used for simulated data.

The theme toggle (sun/moon icon, top right) switches between light and dark color schemes instantly, with the choice persisted across sessions.

## Working With Real Radar Hardware Data

If you have access to a TI mmWave evaluation kit (e.g. IWR1443BOOST) paired with a DCA1000EVM capture card, raw `.bin` captures from that hardware can be processed directly through this pipeline via the Dataset Upload view. Note the current loader supports the common single-RX complex (I/Q) capture layout; multi-RX/multi-TX MIMO captures would require channel de-interleaving not currently implemented (the loader's pre-flight size check will report a clear file-size mismatch error if your capture doesn't match the declared single-RX shape — this is intentional, not a bug, and is documented directly in `dataset_loader.py`).

## Design Decisions & Known Limitations

- **Vital signs use a separate timescale from Range-Doppler processing.** A single radar frame (e.g. 128 chirps × 64 µs) only spans about 16 milliseconds — far too short to observe a 4-second breathing cycle. Vital sign extraction therefore simulates/requires a separate, much slower frame-rate phase sequence (multiple seconds, sampled at ~10–20 Hz), which is the same architecture real mmWave vital-sign radar systems use. This is a deliberate physical constraint, not a simplification.
- **CFAR is range-only (1D sliding window along range, per Doppler row), not full 2D.** This is appropriate because simulated targets have near-zero bulk velocity and most of their energy sits in a single Doppler bin — a full 2D CFAR window would be a straightforward extension for scenes with multiple moving targets at different velocities.
- **The frontend's Plotly components are dynamically imported with SSR disabled**, since Plotly references `window` and cannot run during Next.js server-side rendering.
- **No authentication or persistence layer.** This is a single-session DSP demonstration tool, not a multi-user production radar system — there is no database, no user accounts, and no saved run history.

## Phase Build History

| Phase | Name | What Was Built |
|---|---|---|
| 0 | Project Init & Config | Repository scaffold, `.gitignore`, base FastAPI app, initial theme tokens |
| 1 | DSP Core — Chirp Simulator | FMCW beat signal physics, target model, full Pydantic schema set |
| 2 | Range-Doppler + CFAR | 2D FFT range-Doppler processing, OS-CFAR detector with non-maximum suppression |
| 3 | Micro-Doppler & Vital Signs | Complex Morlet CWT spectrogram, frame-rate phase sequence simulator, bandpass-filtered BPM extraction |
| 4 | Dataset Loader + Full API | TI DCA1000 `.bin` parser, complete REST routes, WebSocket live pipeline streamer |
| 5 | Frontend Foundation | Next.js app shell, Axios API client, pipeline/WebSocket React hooks |
| 6 | Radar Visualization | Plotly Range-Doppler heatmap with CFAR markers, detection panel, animated pipeline stage tracker |
| 7 | Vitals, Dataset & Polish | Micro-Doppler spectrogram view, raw/filtered phase signal chart, dataset uploader UI, WebSocket error-flash fix |
| 8 | UI Redesign | Full visual rework — light/dark theme system with persisted preference, sidebar navigation, working view routing |

## Troubleshooting

**`ModuleNotFoundError: No module named 'core'` when running a backend script** — you're not in the `backend/` directory, or the venv isn't active. Run `cd backend` and `.\venv\Scripts\Activate.ps1` (Windows) or `source venv/bin/activate` (macOS/Linux) first.

**`Failed to load SWC binary for win32/x64`** — a corrupted native binary on Windows, usually from antivirus interference during install. Delete `node_modules` and `package-lock.json`, run `npm cache clean --force`, then `npm install` again.

**PowerShell `curl.exe -d "{\"key\": ...}"` returns a JSON decode error** — PowerShell mangles escaped quotes in command-line strings. Use `Invoke-RestMethod -Body '...'` with single-quoted JSON instead, or test via the `/docs` interactive UI.

**Brief "Connection to radar backend failed" message flashes on page load in dev mode** — this is a known React Strict Mode artifact (the dev-only double-effect-invocation behavior) and is suppressed by a guard in `useWebSocket.js`; it does not occur in production builds (`npm run build && npm start`).

## Roadmap Ideas

- Multi-target tracking across frames (currently each run is a single independent frame)
- Full 2D CFAR for scenes with multiple targets at different velocities
- Multi-RX channel support in the dataset loader for real MIMO captures
- Exportable PDF/CSV reports of a given pipeline run
- WebGL-accelerated rendering for larger Range-Doppler maps

## License

MIT