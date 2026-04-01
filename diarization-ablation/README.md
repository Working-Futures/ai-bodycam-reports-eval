# Diarization Ablation Study

**Research question**: How much of the factual inaccuracy in AI-generated police reports is caused by speaker diarization errors, and does upgrading the diarization model reduce these errors?

## Overview

This pipeline re-runs the AI police report generation pipeline with improved speaker diarization models, holding everything else constant (same ASR model, same Gemini prompt, same audio). By comparing the accuracy of reports generated with different diarization backends, we can establish a **causal link** between diarization quality and report accuracy.

## Pipeline Steps

```
01_rediarize.py          → Re-run ASR+diarization on all audio files
02_regenerate_narratives.py → Feed new transcripts to Gemini to get new reports
03_compare_diarization.py   → Compare diarization quality metrics across models
04_analyze_results.py       → Full analysis (after human coding of new reports)
```

## Setup

### 1. Environment

```bash
# Requires Python 3.10+ and a CUDA GPU
conda create -n diar-ablation python=3.10
conda activate diar-ablation
pip install -r requirements.txt
```

### 2. API Keys

Edit `config.py` and add:

- **HuggingFace token**: Get from https://huggingface.co/settings/tokens
  - Accept terms for `pyannote/speaker-diarization-3.1` and `pyannote/speaker-diarization-community-1`
- **Gemini API key**: From Google AI Studio

### 3. Configuration

In `config.py`, you can:

- Set `VIDEO_SUBSET = [1, 2, 5, 8, ...]` to test on a small subset first
- Change `DEVICE = "cpu"` if no GPU (will be very slow)
- Add or remove diarization models in `DIARIZATION_MODELS`

## Running the Pipeline

### Quick test (5 videos)

```bash
# Step 1: Re-diarize with both models (takes ~10 min per video on GPU)
python 01_rediarize.py --videos 2 5 8 15 30

# Step 2: Regenerate narratives via Gemini
python 02_regenerate_narratives.py --videos 2 5 8 15 30

# Step 3: Compare diarization quality (no API needed)
python 03_compare_diarization.py
```

### Full run (all 112 videos)

```bash
# Set VIDEO_SUBSET = None in config.py, then:
python 01_rediarize.py
python 02_regenerate_narratives.py
python 03_compare_diarization.py
```

### After human coding

Once coders have evaluated the new narratives using the same coding instrument:

```bash
python 04_analyze_results.py --coded-data path/to/new_coded_responses.csv
```

The coded CSV should have columns: `video_id`, `mean_accuracy`, `mean_inaccuracy`, `mean_hallucination`

## What Each Script Produces

| Script | Outputs | Requires API? |
|--------|---------|--------------|
| `01_rediarize.py` | New transcripts + RTTM files per model | HuggingFace |
| `02_regenerate_narratives.py` | New narratives + atomic facts | Gemini |
| `03_compare_diarization.py` | Speaker agreement stats, figures | None |
| `04_analyze_results.py` | Accuracy comparison, effect size | None |

## Expected Results

Based on the error taxonomy from the original study:

- **39.3%** of consensus-inaccurate facts are speaker misattribution (diarization errors)
- **Original accuracy**: 74.2% (mean across 80 coded videos)
- **Upper-bound prediction**: If perfect diarization eliminates all speaker errors, accuracy could reach ~83%
- The inaccuracy rate would STILL be ~5× the hallucination rate, supporting the paper's core argument

## Diarization Models

| Model | Source | Notes |
|-------|--------|-------|
| `pyannote/speaker-diarization-3.1` | WhisperX default | Baseline (what Maya used) |
| `pyannote/speaker-diarization-community-1` | pyannote community | Significant improvement over 3.1 |

## Directory Structure

```
diarization-ablation/
├── config.py                      # Paths, API keys, settings
├── requirements.txt
├── 01_rediarize.py               # Step 1: Re-diarize audio
├── 02_regenerate_narratives.py   # Step 2: Re-generate reports
├── 03_compare_diarization.py     # Step 3: Compare diarization quality
├── 04_analyze_results.py         # Step 4: Accuracy analysis
├── README.md
└── output/                       # Generated outputs
    ├── diarization/              # RTTM files per model
    ├── transcripts/              # New transcripts per model
    ├── narratives/               # New narratives per model
    ├── atomic_facts/             # New atomic facts per model
    ├── comparison/               # Analysis outputs and figures
    └── processing_times.csv
```
