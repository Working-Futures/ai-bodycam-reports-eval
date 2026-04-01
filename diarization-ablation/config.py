"""
Configuration for the diarization ablation study.
Edit these paths and keys before running.
"""
from pathlib import Path

# ============================================================
# PATHS — edit these to match your setup
# ============================================================

# Root of the project (parent of this script's directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Original data from Maya's pipeline
AUDIO_DIR = PROJECT_ROOT / "files-from-maya" / "Audio Clips"
ORIGINAL_TRANSCRIPTS_DIR = PROJECT_ROOT / "files-from-maya" / "Cleaned Transcripts"
ORIGINAL_NARRATIVES_DIR = PROJECT_ROOT / "files-from-maya" / "Narratives"
ORIGINAL_FACTS_DIR = PROJECT_ROOT / "files-from-maya" / "Atomic Facts"

# Output directories (created automatically)
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
NEW_DIARIZATION_DIR = OUTPUT_DIR / "diarization"
NEW_TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"
NEW_NARRATIVES_DIR = OUTPUT_DIR / "narratives"
NEW_FACTS_DIR = OUTPUT_DIR / "atomic_facts"
COMPARISON_DIR = OUTPUT_DIR / "comparison"

# ============================================================
# API KEYS
# ============================================================

# HuggingFace token (required for pyannote models)
# Get yours at: https://huggingface.co/settings/tokens
# You must accept the terms for:
#   - pyannote/speaker-diarization-3.1
#   - pyannote/speaker-diarization-community-1
#   - pyannote/segmentation-3.0
HF_TOKEN = "YOUR_HF_TOKEN_HERE"

# Google Gemini API key (for narrative re-generation)
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

# ============================================================
# DIARIZATION MODELS TO COMPARE
# ============================================================

# Each entry is (label, model_name_or_path)
DIARIZATION_MODELS = [
    ("pyannote-3.1", "pyannote/speaker-diarization-3.1"),        # WhisperX default
    ("pyannote-community-1", "pyannote/speaker-diarization-community-1"),  # Improved
]

# ============================================================
# EXPERIMENT SETTINGS
# ============================================================

# Which videos to process. Set to None for all 112.
# For a quick test, try a small subset first:
# VIDEO_SUBSET = [1, 2, 5, 8, 10, 15, 20, 30, 50, 70]
VIDEO_SUBSET = None  # None = all videos

# Whisper model for ASR (same as original pipeline for fair comparison)
WHISPER_MODEL = "large-v2"

# Gemini model for narrative generation
GEMINI_MODEL = "gemini-1.5-pro"

# Number of concurrent Gemini requests
GEMINI_CONCURRENCY = 5

# Device for PyTorch models
DEVICE = "cuda"  # or "cpu" if no GPU

# Batch size for Whisper
WHISPER_BATCH_SIZE = 16
