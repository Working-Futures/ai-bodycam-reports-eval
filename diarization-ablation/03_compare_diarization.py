#!/usr/bin/env python3
"""
Step 3: Compare diarization quality across models.

This script does NOT require Gemini or human coding — it works purely from
the transcripts and diarization outputs. It measures:

1. Speaker count accuracy (do we detect the right number of speakers?)
2. Diarization agreement between models (how much do speaker assignments differ?)
3. Speaker entropy / dominance (are speaker proportions reasonable?)
4. Transcript-level differences (how much does the text change with new diarization?)

For a subset of videos where we have human-coded accuracy labels, it also
correlates diarization quality metrics with factual accuracy.

Usage:
    python 03_compare_diarization.py
"""

import json
import os
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linear_sum_assignment

from config import (
    ORIGINAL_TRANSCRIPTS_DIR, NEW_TRANSCRIPTS_DIR,
    NEW_DIARIZATION_DIR, OUTPUT_DIR, COMPARISON_DIR,
    DIARIZATION_MODELS, AUDIO_DIR
)


def load_transcript(path):
    """Load a transcript JSON file."""
    with open(path) as f:
        return json.load(f)


def get_speaker_stats(transcript):
    """Compute speaker statistics from a transcript."""
    speakers = [seg.get('speaker', 'UNKNOWN') for seg in transcript]
    speaker_counts = Counter(speakers)
    n_speakers = len([s for s in speaker_counts if s != 'UNKNOWN'])

    # Speaker time proportions (approximate from segment count)
    total = sum(speaker_counts.values())
    proportions = {s: c/total for s, c in speaker_counts.items()}

    # Shannon entropy of speaker distribution
    probs = np.array([c/total for c in speaker_counts.values()])
    entropy = -np.sum(probs * np.log2(probs + 1e-10))

    # Dominance: proportion of speech from the most-speaking speaker
    dominance = max(speaker_counts.values()) / total if total > 0 else 0

    return {
        'n_speakers': n_speakers,
        'n_segments': len(transcript),
        'speaker_counts': dict(speaker_counts),
        'entropy': entropy,
        'dominance': dominance,
    }


def compute_speaker_mapping(trans_a, trans_b):
    """
    Find the best speaker-to-speaker mapping between two transcripts
    using the Hungarian algorithm on temporal overlap.

    Returns a dict mapping speaker labels in B to their best match in A.
    """
    speakers_a = set(seg.get('speaker', '') for seg in trans_a) - {'UNKNOWN', ''}
    speakers_b = set(seg.get('speaker', '') for seg in trans_b) - {'UNKNOWN', ''}

    if not speakers_a or not speakers_b:
        return {}

    speakers_a = sorted(speakers_a)
    speakers_b = sorted(speakers_b)

    # Build overlap matrix: for each pair (sa, sb), count how many segments
    # overlap temporally AND have those speaker assignments
    overlap = np.zeros((len(speakers_a), len(speakers_b)))

    for seg_a in trans_a:
        for seg_b in trans_b:
            # Check temporal overlap
            start = max(seg_a['start'], seg_b['start'])
            end = min(seg_a['end'], seg_b['end'])
            if end > start:
                sa_idx = speakers_a.index(seg_a.get('speaker', '')) if seg_a.get('speaker', '') in speakers_a else -1
                sb_idx = speakers_b.index(seg_b.get('speaker', '')) if seg_b.get('speaker', '') in speakers_b else -1
                if sa_idx >= 0 and sb_idx >= 0:
                    overlap[sa_idx, sb_idx] += (end - start)

    # Pad to square if needed
    n = max(len(speakers_a), len(speakers_b))
    padded = np.zeros((n, n))
    padded[:len(speakers_a), :len(speakers_b)] = overlap

    # Hungarian algorithm (maximize overlap = minimize negative)
    row_ind, col_ind = linear_sum_assignment(-padded)

    mapping = {}
    for r, c in zip(row_ind, col_ind):
        if c < len(speakers_b) and r < len(speakers_a):
            mapping[speakers_b[c]] = speakers_a[r]

    return mapping


def compute_speaker_agreement(trans_a, trans_b, mapping):
    """
    After aligning speakers via mapping, compute what fraction of
    speech time has matching speaker labels.
    """
    total_overlap = 0
    matching_overlap = 0

    for seg_a in trans_a:
        for seg_b in trans_b:
            start = max(seg_a['start'], seg_b['start'])
            end = min(seg_a['end'], seg_b['end'])
            if end > start:
                duration = end - start
                total_overlap += duration
                sp_a = seg_a.get('speaker', '')
                sp_b = mapping.get(seg_b.get('speaker', ''), '')
                if sp_a == sp_b:
                    matching_overlap += duration

    return matching_overlap / total_overlap if total_overlap > 0 else 0


def text_similarity(trans_a, trans_b):
    """
    Compare the actual text content of two transcripts.
    Since ASR is the same, differences come from segmentation/alignment changes.
    """
    text_a = ' '.join(seg['text'].strip() for seg in trans_a)
    text_b = ' '.join(seg['text'].strip() for seg in trans_b)

    # Simple word-level overlap
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())

    if not words_a and not words_b:
        return 1.0
    jaccard = len(words_a & words_b) / len(words_a | words_b)
    return jaccard


def main():
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    # Get all video IDs
    video_ids = sorted([
        int(f.stem.replace("audio_", ""))
        for f in AUDIO_DIR.glob("audio_*.mp3")
    ])

    model_labels = [label for label, _ in DIARIZATION_MODELS]

    print(f"Comparing diarization across: {model_labels}")
    print(f"Videos: {len(video_ids)}")

    # ============================================================
    # 1. Per-video speaker statistics for each model
    # ============================================================
    all_stats = []

    for model_label in model_labels:
        trans_dir = NEW_TRANSCRIPTS_DIR / model_label
        if not trans_dir.exists():
            print(f"  No transcripts for {model_label}, skipping")
            continue

        for vid in video_ids:
            trans_path = trans_dir / f"transcript_{vid:02d}.json"
            if not trans_path.exists():
                continue

            transcript = load_transcript(trans_path)
            stats_dict = get_speaker_stats(transcript)
            stats_dict['video_id'] = vid
            stats_dict['model'] = model_label
            all_stats.append(stats_dict)

    stats_df = pd.DataFrame(all_stats)

    # Also load original transcripts for comparison
    orig_stats = []
    for vid in video_ids:
        orig_path = ORIGINAL_TRANSCRIPTS_DIR / f"transcript_{vid:02d}.json"
        if not orig_path.exists():
            continue
        transcript = load_transcript(orig_path)
        s = get_speaker_stats(transcript)
        s['video_id'] = vid
        s['model'] = 'original-whisperx'
        orig_stats.append(s)

    orig_df = pd.DataFrame(orig_stats)
    stats_df = pd.concat([orig_df, stats_df], ignore_index=True)

    # Save
    stats_df.drop(columns=['speaker_counts'], errors='ignore').to_csv(
        COMPARISON_DIR / 'speaker_stats_by_model.csv', index=False
    )
    print(f"\nSpeaker stats saved ({len(stats_df)} rows)")

    # ============================================================
    # 2. Cross-model diarization agreement
    # ============================================================
    print("\nComputing cross-model speaker agreement...")

    agreement_rows = []
    # Compare each new model against the original
    for model_label in model_labels:
        trans_dir = NEW_TRANSCRIPTS_DIR / model_label

        for vid in video_ids:
            orig_path = ORIGINAL_TRANSCRIPTS_DIR / f"transcript_{vid:02d}.json"
            new_path = trans_dir / f"transcript_{vid:02d}.json"

            if not orig_path.exists() or not new_path.exists():
                continue

            trans_orig = load_transcript(orig_path)
            trans_new = load_transcript(new_path)

            # Align speakers and compute agreement
            mapping = compute_speaker_mapping(trans_orig, trans_new)
            agreement = compute_speaker_agreement(trans_orig, trans_new, mapping)
            text_sim = text_similarity(trans_orig, trans_new)

            orig_stats = get_speaker_stats(trans_orig)
            new_stats = get_speaker_stats(trans_new)

            agreement_rows.append({
                'video_id': vid,
                'model': model_label,
                'speaker_agreement': agreement,
                'text_similarity': text_sim,
                'orig_n_speakers': orig_stats['n_speakers'],
                'new_n_speakers': new_stats['n_speakers'],
                'speaker_count_diff': new_stats['n_speakers'] - orig_stats['n_speakers'],
                'orig_dominance': orig_stats['dominance'],
                'new_dominance': new_stats['dominance'],
            })

    agreement_df = pd.DataFrame(agreement_rows)
    agreement_df.to_csv(COMPARISON_DIR / 'diarization_agreement.csv', index=False)

    # Print summary
    if len(agreement_df) > 0:
        print("\nDiarization agreement vs. original WhisperX:")
        for model_label in model_labels:
            subset = agreement_df[agreement_df['model'] == model_label]
            if len(subset) == 0:
                continue
            print(f"\n  {model_label}:")
            print(f"    Speaker agreement: {subset['speaker_agreement'].mean():.3f} "
                  f"(±{subset['speaker_agreement'].std():.3f})")
            print(f"    Text similarity:   {subset['text_similarity'].mean():.3f}")
            print(f"    Speaker count diff: {subset['speaker_count_diff'].mean():+.2f} "
                  f"(orig avg: {subset['orig_n_speakers'].mean():.1f}, "
                  f"new avg: {subset['new_n_speakers'].mean():.1f})")

    # ============================================================
    # 3. Correlation with accuracy (if we have coded data)
    # ============================================================
    coded_data_path = Path(__file__).resolve().parent.parent / "results" / "merged_analysis.csv"

    if coded_data_path.exists():
        print("\nCorrelating with human-coded accuracy data...")
        coded = pd.read_csv(coded_data_path)

        # Extract video number from video_id
        coded['video_num'] = coded['video_id'].str.extract(r'(\d+)').astype(int)

        for model_label in model_labels:
            subset = agreement_df[agreement_df['model'] == model_label].copy()
            merged = subset.merge(coded[['video_num', 'mean_accuracy', 'mean_inaccuracy']],
                                  left_on='video_id', right_on='video_num', how='inner')

            if len(merged) > 5:
                r_agree, p_agree = stats.pearsonr(merged['speaker_agreement'],
                                                   merged['mean_accuracy'])
                r_count, p_count = stats.pearsonr(merged['speaker_count_diff'].abs(),
                                                    merged['mean_accuracy'])
                print(f"\n  {model_label} correlations with accuracy:")
                print(f"    Speaker agreement ↔ accuracy: r={r_agree:.3f}, p={p_agree:.3f}")
                print(f"    |Speaker count diff| ↔ accuracy: r={r_count:.3f}, p={p_count:.3f}")

    # ============================================================
    # 4. Generate figures
    # ============================================================
    print("\nGenerating figures...")

    if len(agreement_df) > 0:
        # Figure: Speaker agreement distribution
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        for model_label in model_labels:
            subset = agreement_df[agreement_df['model'] == model_label]
            if len(subset) > 0:
                axes[0].hist(subset['speaker_agreement'], bins=20, alpha=0.6,
                            label=model_label, edgecolor='white')
                axes[1].scatter(subset['speaker_count_diff'], subset['speaker_agreement'],
                               alpha=0.5, label=model_label)

        axes[0].set_xlabel('Speaker Assignment Agreement with Original')
        axes[0].set_ylabel('Count')
        axes[0].set_title('Diarization Agreement Distribution')
        axes[0].legend()

        axes[1].set_xlabel('Speaker Count Difference (new - original)')
        axes[1].set_ylabel('Speaker Assignment Agreement')
        axes[1].set_title('Speaker Count Change vs. Agreement')
        axes[1].legend()
        axes[1].axvline(0, color='gray', linestyle='--', alpha=0.5)

        plt.tight_layout()
        plt.savefig(COMPARISON_DIR / 'diarization_comparison.pdf', dpi=300)
        plt.savefig(COMPARISON_DIR / 'diarization_comparison.png', dpi=300)
        plt.close()

    # Figure: Speaker count comparison across models
    if len(stats_df) > 0:
        pivot = stats_df.pivot_table(values='n_speakers', index='video_id', columns='model')
        if pivot.shape[1] >= 2:
            fig, ax = plt.subplots(figsize=(8, 6))
            cols = pivot.columns.tolist()
            for i in range(1, len(cols)):
                ax.scatter(pivot[cols[0]], pivot[cols[i]], alpha=0.5, label=f'{cols[0]} vs {cols[i]}')
            ax.plot([0, pivot.max().max()], [0, pivot.max().max()], 'k--', alpha=0.3)
            ax.set_xlabel(f'Speaker Count ({cols[0]})')
            ax.set_ylabel('Speaker Count (other models)')
            ax.set_title('Speaker Count Agreement Across Models')
            ax.legend()
            plt.tight_layout()
            plt.savefig(COMPARISON_DIR / 'speaker_count_comparison.pdf', dpi=300)
            plt.savefig(COMPARISON_DIR / 'speaker_count_comparison.png', dpi=300)
            plt.close()

    print(f"\nAll comparison outputs saved to: {COMPARISON_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()
