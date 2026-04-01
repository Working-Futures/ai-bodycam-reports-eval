#!/usr/bin/env python3
"""
Step 1: Re-diarize audio files with multiple pyannote models.

For each audio file and each diarization model, produces:
  - RTTM file (standard diarization format)
  - JSON transcript (same format as Maya's original: [{start, end, text, speaker}, ...])

This script re-runs the FULL WhisperX pipeline (ASR + diarization) rather than
trying to retroactively reassign speakers, because WhisperX's speaker assignment
depends on segment-level alignment that can't be cleanly separated from diarization.

Usage:
    python 01_rediarize.py [--models pyannote-3.1 pyannote-community-1] [--videos 1 2 5]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch
import whisperx
from pyannote.audio import Pipeline as DiarizationPipeline
from tqdm import tqdm

from config import (
    AUDIO_DIR, ORIGINAL_TRANSCRIPTS_DIR, OUTPUT_DIR,
    NEW_DIARIZATION_DIR, NEW_TRANSCRIPTS_DIR,
    DIARIZATION_MODELS, VIDEO_SUBSET, HF_TOKEN,
    WHISPER_MODEL, WHISPER_BATCH_SIZE, DEVICE
)


def get_video_ids():
    """Get list of video IDs to process."""
    all_ids = sorted([
        int(f.stem.replace("audio_", ""))
        for f in AUDIO_DIR.glob("audio_*.mp3")
    ])
    if VIDEO_SUBSET is not None:
        all_ids = [v for v in all_ids if v in VIDEO_SUBSET]
    return all_ids


def load_whisper_model():
    """Load WhisperX ASR model (same for all diarization comparisons)."""
    print(f"Loading Whisper model: {WHISPER_MODEL} on {DEVICE}")
    compute_type = "float16" if DEVICE == "cuda" else "int8"
    model = whisperx.load_model(
        WHISPER_MODEL, DEVICE,
        compute_type=compute_type,
        language="en"
    )
    return model


def transcribe_and_diarize(audio_path, whisper_model, diar_pipeline, model_label):
    """
    Run full WhisperX pipeline on one audio file with a given diarization model.

    Returns:
        transcript: list of dicts [{start, end, text, speaker}, ...]
        diar_result: pyannote diarization Annotation object
        timing: dict with processing times
    """
    timing = {}
    audio_file = str(audio_path)

    # Step 1: Load audio
    t0 = time.time()
    audio = whisperx.load_audio(audio_file)
    timing['load_audio'] = time.time() - t0

    # Step 2: Transcribe (ASR only, no speaker labels yet)
    t0 = time.time()
    result = whisper_model.transcribe(audio, batch_size=WHISPER_BATCH_SIZE)
    timing['asr'] = time.time() - t0

    # Step 3: Align word-level timestamps
    t0 = time.time()
    align_model, metadata = whisperx.load_align_model(
        language_code="en", device=DEVICE
    )
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, DEVICE,
        return_char_alignments=False
    )
    timing['align'] = time.time() - t0

    # Step 4: Diarize and assign speakers
    t0 = time.time()
    diar_result = diar_pipeline(audio_file)
    timing['diarization'] = time.time() - t0

    t0 = time.time()
    result = whisperx.assign_word_speakers(diar_result, result)
    timing['assign_speakers'] = time.time() - t0

    # Convert to our standard transcript format
    transcript = []
    for seg in result["segments"]:
        transcript.append({
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip(),
            "speaker": seg.get("speaker", "UNKNOWN"),
        })

    return transcript, diar_result, timing


def save_rttm(diar_result, output_path, file_id):
    """Save diarization result in RTTM format (standard for evaluation)."""
    with open(output_path, 'w') as f:
        for turn, _, speaker in diar_result.itertracks(yield_label=True):
            f.write(
                f"SPEAKER {file_id} 1 {turn.start:.3f} {turn.duration:.3f} "
                f"<NA> <NA> {speaker} <NA> <NA>\n"
            )


def main():
    parser = argparse.ArgumentParser(description="Re-diarize audio with multiple models")
    parser.add_argument("--models", nargs="+", default=None,
                        help="Model labels to run (default: all in config)")
    parser.add_argument("--videos", nargs="+", type=int, default=None,
                        help="Video IDs to process (default: from config)")
    args = parser.parse_args()

    # Resolve which models and videos to run
    models_to_run = DIARIZATION_MODELS
    if args.models:
        models_to_run = [(l, p) for l, p in DIARIZATION_MODELS if l in args.models]

    video_ids = args.videos if args.videos else get_video_ids()

    print(f"=" * 60)
    print(f"DIARIZATION ABLATION STUDY")
    print(f"Models: {[m[0] for m in models_to_run]}")
    print(f"Videos: {len(video_ids)} files")
    print(f"Device: {DEVICE}")
    print(f"=" * 60)

    # Load Whisper (shared across all diarization models)
    whisper_model = load_whisper_model()

    # Process each diarization model
    all_timings = []

    for model_label, model_path in models_to_run:
        print(f"\n{'='*60}")
        print(f"DIARIZATION MODEL: {model_label} ({model_path})")
        print(f"{'='*60}")

        # Create output dirs
        model_diar_dir = NEW_DIARIZATION_DIR / model_label
        model_trans_dir = NEW_TRANSCRIPTS_DIR / model_label
        model_diar_dir.mkdir(parents=True, exist_ok=True)
        model_trans_dir.mkdir(parents=True, exist_ok=True)

        # Load diarization pipeline
        print(f"Loading diarization pipeline: {model_path}")
        diar_pipeline = DiarizationPipeline.from_pretrained(
            model_path, use_auth_token=HF_TOKEN
        )
        if DEVICE == "cuda":
            diar_pipeline.to(torch.device("cuda"))

        # Process each video
        for vid in tqdm(video_ids, desc=f"[{model_label}] Processing"):
            audio_path = AUDIO_DIR / f"audio_{vid:02d}.mp3"
            if not audio_path.exists():
                audio_path = AUDIO_DIR / f"audio_{vid}.mp3"
            if not audio_path.exists():
                print(f"  WARNING: {audio_path} not found, skipping")
                continue

            # Skip if already processed
            out_transcript = model_trans_dir / f"transcript_{vid:02d}.json"
            if out_transcript.exists():
                print(f"  Skipping video_{vid:02d} (already processed)")
                continue

            try:
                transcript, diar_result, timing = transcribe_and_diarize(
                    audio_path, whisper_model, diar_pipeline, model_label
                )

                # Save transcript
                with open(out_transcript, 'w') as f:
                    json.dump(transcript, f, indent=2)

                # Save RTTM
                rttm_path = model_diar_dir / f"video_{vid:02d}.rttm"
                save_rttm(diar_result, rttm_path, f"video_{vid:02d}")

                # Log timing
                timing['video_id'] = vid
                timing['model'] = model_label
                timing['n_segments'] = len(transcript)
                timing['n_speakers'] = len(set(s.get('speaker', '') for s in transcript))
                all_timings.append(timing)

                print(f"  video_{vid:02d}: {len(transcript)} segments, "
                      f"{timing['n_speakers']} speakers, "
                      f"diarization={timing['diarization']:.1f}s")

            except Exception as e:
                print(f"  ERROR on video_{vid:02d}: {e}")
                continue

    # Save timing data
    if all_timings:
        import pandas as pd
        timing_df = pd.DataFrame(all_timings)
        timing_path = OUTPUT_DIR / "processing_times.csv"
        timing_df.to_csv(timing_path, index=False)
        print(f"\nTiming data saved to {timing_path}")
        print(timing_df.groupby('model')[['asr', 'diarization', 'align']].mean())

    print("\nDone! Transcripts saved to:", NEW_TRANSCRIPTS_DIR)


if __name__ == "__main__":
    main()
