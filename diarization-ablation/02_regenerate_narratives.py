#!/usr/bin/env python3
"""
Step 2: Re-generate police report narratives using Gemini with the new transcripts.

Uses the SAME prompt as Maya's original pipeline to ensure a fair comparison.
Only the transcript input changes (because of different diarization).

Usage:
    python 02_regenerate_narratives.py [--models pyannote-community-1] [--videos 1 2 5]
"""

import argparse
import json
import time
from pathlib import Path

import google.generativeai as genai
from tqdm import tqdm

from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    NEW_TRANSCRIPTS_DIR, NEW_NARRATIVES_DIR, NEW_FACTS_DIR,
    DIARIZATION_MODELS, VIDEO_SUBSET, AUDIO_DIR
)

# ============================================================
# PROMPTS — These must match Maya's original pipeline exactly.
# If you have a different prompt, replace these.
# ============================================================

NARRATIVE_PROMPT = """You are a police officer writing an incident report based on body-worn camera footage.
Based on the following transcript from body-worn camera footage, write a first-person police narrative report.
The report should:
1. Be written from the perspective of the officer wearing the camera
2. Include all key events, actions, and dialogue in chronological order
3. Use formal police report language
4. Include specific details from the transcript (names, locations, times mentioned)
5. Note any use of force, Miranda warnings, or searches
6. Where information is unclear or missing from the transcript, indicate with [INSERT: description of missing info]

Transcript:
{transcript}

Write the police narrative report:"""

ATOMIC_FACTS_PROMPT = """Break down the following police narrative into atomic facts.
Each atomic fact should be a single, verifiable claim that can be independently checked against the source transcript.

Rules:
1. Each fact should be on its own line
2. Each fact should contain exactly one claim
3. Facts should be specific and verifiable
4. Include all claims from the narrative, even minor ones

Narrative:
{narrative}

List each atomic fact on its own line:"""


def format_transcript_for_prompt(transcript):
    """Format a transcript JSON into readable text for the LLM prompt."""
    lines = []
    for entry in transcript:
        speaker = entry.get('speaker', 'UNKNOWN')
        text = entry.get('text', '').strip()
        if text:
            lines.append(f"[{speaker}]: {text}")
    return "\n".join(lines)


def generate_with_retry(model, prompt, max_retries=3, base_delay=5):
    """Call Gemini with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"    Retry {attempt+1}/{max_retries} after {delay}s: {e}")
            time.sleep(delay)


def get_video_ids():
    all_ids = sorted([
        int(f.stem.replace("audio_", ""))
        for f in AUDIO_DIR.glob("audio_*.mp3")
    ])
    if VIDEO_SUBSET is not None:
        all_ids = [v for v in all_ids if v in VIDEO_SUBSET]
    return all_ids


def main():
    parser = argparse.ArgumentParser(description="Re-generate narratives with Gemini")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--videos", nargs="+", type=int, default=None)
    parser.add_argument("--skip-narratives", action="store_true",
                        help="Skip narrative generation, only extract atomic facts")
    args = parser.parse_args()

    # Setup Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    models_to_run = DIARIZATION_MODELS
    if args.models:
        models_to_run = [(l, p) for l, p in DIARIZATION_MODELS if l in args.models]

    video_ids = args.videos if args.videos else get_video_ids()

    for model_label, _ in models_to_run:
        trans_dir = NEW_TRANSCRIPTS_DIR / model_label
        narr_dir = NEW_NARRATIVES_DIR / model_label
        facts_dir = NEW_FACTS_DIR / model_label
        narr_dir.mkdir(parents=True, exist_ok=True)
        facts_dir.mkdir(parents=True, exist_ok=True)

        if not trans_dir.exists():
            print(f"No transcripts found for {model_label} — run 01_rediarize.py first")
            continue

        print(f"\n{'='*60}")
        print(f"GENERATING NARRATIVES: {model_label}")
        print(f"{'='*60}")

        for vid in tqdm(video_ids, desc=f"[{model_label}]"):
            trans_path = trans_dir / f"transcript_{vid:02d}.json"
            narr_path = narr_dir / f"narrative_{vid:02d}.txt"
            facts_path = facts_dir / f"atomic_facts_{vid:02d}.txt"

            if not trans_path.exists():
                continue

            # Load transcript
            with open(trans_path) as f:
                transcript = json.load(f)

            transcript_text = format_transcript_for_prompt(transcript)

            # Generate narrative
            if not narr_path.exists() and not args.skip_narratives:
                try:
                    prompt = NARRATIVE_PROMPT.format(transcript=transcript_text)
                    narrative = generate_with_retry(model, prompt)

                    # Clean up: remove "Narrative:" prefix if present
                    if narrative.startswith("Narrative:"):
                        narrative = narrative[len("Narrative:"):].strip()

                    with open(narr_path, 'w') as f:
                        f.write(narrative)

                    # Rate limiting
                    time.sleep(1)

                except Exception as e:
                    print(f"  ERROR generating narrative for video_{vid:02d}: {e}")
                    continue

            # Extract atomic facts
            if not facts_path.exists() and narr_path.exists():
                try:
                    with open(narr_path) as f:
                        narrative = f.read()

                    prompt = ATOMIC_FACTS_PROMPT.format(narrative=narrative)
                    facts_text = generate_with_retry(model, prompt)

                    # Clean: one fact per line, remove numbering/bullets
                    facts = []
                    for line in facts_text.strip().split('\n'):
                        line = line.strip()
                        # Remove numbering like "1.", "- ", "* "
                        if line and line[0].isdigit():
                            line = line.lstrip('0123456789.').strip()
                        line = line.lstrip('-*• ').strip()
                        if line:
                            facts.append(line)

                    with open(facts_path, 'w') as f:
                        f.write('\n'.join(facts))

                    time.sleep(1)

                except Exception as e:
                    print(f"  ERROR extracting facts for video_{vid:02d}: {e}")
                    continue

        print(f"  Narratives: {narr_dir}")
        print(f"  Atomic facts: {facts_dir}")

    print("\nDone!")


if __name__ == "__main__":
    main()
