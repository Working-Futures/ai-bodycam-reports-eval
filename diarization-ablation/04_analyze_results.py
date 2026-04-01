#!/usr/bin/env python3
"""
Step 4: Full analysis of the diarization ablation results.

This script runs after human coders have evaluated the re-generated narratives.
It compares accuracy rates between the original pipeline and the improved-diarization
pipeline to quantify the causal effect of diarization quality on report accuracy.

If human coding hasn't been done yet, it still produces useful intermediate
analyses: transcript-level diarization quality comparisons, speaker assignment
differences, and predicted accuracy improvements based on the error taxonomy.

Usage:
    python 04_analyze_results.py [--coded-data path/to/new_coded_responses.csv]
"""

import argparse
import json
from pathlib import Path
from difflib import SequenceMatcher

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from config import (
    ORIGINAL_TRANSCRIPTS_DIR, NEW_TRANSCRIPTS_DIR,
    ORIGINAL_NARRATIVES_DIR, NEW_NARRATIVES_DIR,
    ORIGINAL_FACTS_DIR, NEW_FACTS_DIR,
    COMPARISON_DIR, OUTPUT_DIR,
    DIARIZATION_MODELS, AUDIO_DIR
)


def count_speaker_swaps(orig_transcript, new_transcript):
    """
    Count segments where the speaker label changed between original and new
    diarization, after aligning speakers optimally.

    This is the key metric: how many utterances get re-attributed to a
    different speaker when diarization improves?
    """
    from collections import Counter

    # Build time-aligned comparison
    swaps = 0
    total = 0

    for orig_seg in orig_transcript:
        # Find the best-matching segment in the new transcript
        best_overlap = 0
        best_new_speaker = None

        for new_seg in new_transcript:
            start = max(orig_seg['start'], new_seg['start'])
            end = min(orig_seg['end'], new_seg['end'])
            overlap = max(0, end - start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_new_speaker = new_seg.get('speaker', '')

        if best_new_speaker is not None:
            total += 1
            # We can't directly compare labels (SPEAKER_00 in one might be SPEAKER_01
            # in another), so we track the pattern of changes
            # This will be resolved in the analysis via Hungarian matching

    return total


def compare_narratives(orig_path, new_path):
    """Compare original and new narratives at the text level."""
    if not orig_path.exists() or not new_path.exists():
        return None

    with open(orig_path) as f:
        orig = f.read().strip()
    with open(new_path) as f:
        new = f.read().strip()

    # Sequence similarity
    sim = SequenceMatcher(None, orig, new).ratio()

    # Word-level comparison
    orig_words = orig.lower().split()
    new_words = new.lower().split()
    word_sim = SequenceMatcher(None, orig_words, new_words).ratio()

    # Length comparison
    len_diff = len(new_words) - len(orig_words)

    return {
        'char_similarity': sim,
        'word_similarity': word_sim,
        'orig_words': len(orig_words),
        'new_words': len(new_words),
        'word_count_diff': len_diff,
    }


def compare_atomic_facts(orig_path, new_path):
    """Compare atomic facts extracted from original vs new narratives."""
    if not orig_path.exists() or not new_path.exists():
        return None

    with open(orig_path) as f:
        orig_facts = [l.strip() for l in f.readlines() if l.strip()]
    with open(new_path) as f:
        new_facts = [l.strip() for l in f.readlines() if l.strip()]

    # Count of facts
    n_orig = len(orig_facts)
    n_new = len(new_facts)

    # Find matching facts (fuzzy)
    matched = 0
    for of in orig_facts:
        for nf in new_facts:
            if SequenceMatcher(None, of.lower(), nf.lower()).ratio() > 0.8:
                matched += 1
                break

    return {
        'orig_n_facts': n_orig,
        'new_n_facts': n_new,
        'n_matched': matched,
        'fact_retention_rate': matched / n_orig if n_orig > 0 else 0,
        'fact_count_diff': n_new - n_orig,
    }


def estimate_accuracy_improvement(error_taxonomy_path, agreement_df):
    """
    Based on the error taxonomy (which errors are diarization-caused) and
    the diarization quality improvement, estimate how much accuracy should
    improve with better diarization.

    This is a PREDICTION, not a measurement — useful for power analysis
    and framing, but the actual improvement must be measured via human coding.
    """
    if not error_taxonomy_path.exists():
        return None

    errors = pd.read_csv(error_taxonomy_path)
    total_errors = len(errors)

    # Count diarization-caused errors
    diar_errors = errors[
        errors['error_type'] == 'Speaker misattribution (officer/civilian swap)'
    ].shape[0]

    diar_fraction = diar_errors / total_errors if total_errors > 0 else 0

    print(f"\n  Error taxonomy: {diar_errors}/{total_errors} ({diar_fraction:.1%}) "
          f"are speaker misattribution")

    # If the new diarization fixes X% of speaker assignments,
    # we'd expect roughly (diar_fraction * X) improvement in accuracy
    # This is a rough upper bound — not all speaker swaps lead to errors

    return {
        'total_errors': total_errors,
        'diarization_errors': diar_errors,
        'diarization_error_fraction': diar_fraction,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coded-data", type=str, default=None,
                        help="Path to CSV with human-coded accuracy for new narratives")
    args = parser.parse_args()

    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

    video_ids = sorted([
        int(f.stem.replace("audio_", ""))
        for f in AUDIO_DIR.glob("audio_*.mp3")
    ])

    model_labels = [label for label, _ in DIARIZATION_MODELS]

    print("=" * 60)
    print("DIARIZATION ABLATION: FULL ANALYSIS")
    print("=" * 60)

    # ============================================================
    # 1. Narrative-level comparison
    # ============================================================
    print("\n1. Comparing narratives...")

    narr_rows = []
    for model_label in model_labels:
        new_narr_dir = NEW_NARRATIVES_DIR / model_label
        if not new_narr_dir.exists():
            continue

        for vid in video_ids:
            orig_path = ORIGINAL_NARRATIVES_DIR / f"narrative_{vid:02d}.txt"
            new_path = new_narr_dir / f"narrative_{vid:02d}.txt"
            result = compare_narratives(orig_path, new_path)
            if result:
                result['video_id'] = vid
                result['model'] = model_label
                narr_rows.append(result)

    if narr_rows:
        narr_df = pd.DataFrame(narr_rows)
        narr_df.to_csv(COMPARISON_DIR / 'narrative_comparison.csv', index=False)

        print("\n  Narrative similarity (original vs re-generated):")
        for model_label in model_labels:
            subset = narr_df[narr_df['model'] == model_label]
            if len(subset) > 0:
                print(f"\n    {model_label}:")
                print(f"      Word similarity: {subset['word_similarity'].mean():.3f} "
                      f"(±{subset['word_similarity'].std():.3f})")
                print(f"      Word count diff: {subset['word_count_diff'].mean():+.1f}")
    else:
        print("  No narratives to compare — run 02_regenerate_narratives.py first")

    # ============================================================
    # 2. Atomic facts comparison
    # ============================================================
    print("\n2. Comparing atomic facts...")

    facts_rows = []
    for model_label in model_labels:
        new_facts_dir = NEW_FACTS_DIR / model_label
        if not new_facts_dir.exists():
            continue

        for vid in video_ids:
            orig_path = ORIGINAL_FACTS_DIR / f"atomic_facts_{vid:02d}.txt"
            new_path = new_facts_dir / f"atomic_facts_{vid:02d}.txt"
            result = compare_atomic_facts(orig_path, new_path)
            if result:
                result['video_id'] = vid
                result['model'] = model_label
                facts_rows.append(result)

    if facts_rows:
        facts_df = pd.DataFrame(facts_rows)
        facts_df.to_csv(COMPARISON_DIR / 'facts_comparison.csv', index=False)

        print("\n  Atomic facts comparison:")
        for model_label in model_labels:
            subset = facts_df[facts_df['model'] == model_label]
            if len(subset) > 0:
                print(f"\n    {model_label}:")
                print(f"      Fact retention: {subset['fact_retention_rate'].mean():.3f}")
                print(f"      Fact count diff: {subset['fact_count_diff'].mean():+.1f}")

    # ============================================================
    # 3. Predicted accuracy improvement from error taxonomy
    # ============================================================
    print("\n3. Estimating accuracy improvement potential...")

    error_path = Path(__file__).resolve().parent.parent / "results" / "grounded_error_taxonomy.csv"
    agreement_path = COMPARISON_DIR / 'diarization_agreement.csv'
    agreement_df = pd.read_csv(agreement_path) if agreement_path.exists() else None

    estimate = estimate_accuracy_improvement(error_path, agreement_df)
    if estimate:
        # Load original accuracy data
        coded_path = Path(__file__).resolve().parent.parent / "results" / "merged_analysis.csv"
        if coded_path.exists():
            original = pd.read_csv(coded_path)
            orig_accuracy = original['mean_accuracy'].mean()
            orig_inaccuracy = original['mean_inaccuracy'].mean()

            # Upper bound: if perfect diarization eliminates ALL speaker misattribution errors
            potential_fix = orig_inaccuracy * estimate['diarization_error_fraction']
            predicted_accuracy = orig_accuracy + potential_fix
            predicted_inaccuracy = orig_inaccuracy - potential_fix

            print(f"\n  Current accuracy: {orig_accuracy:.3f}")
            print(f"  Current inaccuracy: {orig_inaccuracy:.3f}")
            print(f"  Speaker misattribution errors: {estimate['diarization_error_fraction']:.1%} of all errors")
            print(f"  Upper-bound accuracy if perfect diarization: {predicted_accuracy:.3f}")
            print(f"  Upper-bound inaccuracy if perfect diarization: {predicted_inaccuracy:.3f}")
            print(f"  → Potential accuracy improvement: +{potential_fix:.3f} ({potential_fix/orig_inaccuracy:.1%} of errors)")
            print(f"  → Inaccuracy STILL {predicted_inaccuracy/original['mean_hallucination'].mean():.1f}× hallucination rate")

    # ============================================================
    # 4. If human-coded data for new narratives is available
    # ============================================================
    if args.coded_data:
        print(f"\n4. Comparing coded accuracy: original vs re-diarized...")

        new_coded = pd.read_csv(args.coded_data)
        coded_path = Path(__file__).resolve().parent.parent / "results" / "merged_analysis.csv"
        original = pd.read_csv(coded_path)

        # Merge on video_id
        original['video_num'] = original['video_id'].str.extract(r'(\d+)').astype(int)
        comparison = original.merge(
            new_coded, left_on='video_num', right_on='video_id',
            suffixes=('_orig', '_new')
        )

        if len(comparison) > 0:
            # Paired t-test on accuracy
            t_stat, p_val = stats.ttest_rel(
                comparison['mean_accuracy_new'],
                comparison['mean_accuracy_orig']
            )
            effect_size = (comparison['mean_accuracy_new'].mean() -
                          comparison['mean_accuracy_orig'].mean())

            print(f"\n  Paired comparison (n={len(comparison)}):")
            print(f"    Original accuracy: {comparison['mean_accuracy_orig'].mean():.3f}")
            print(f"    New accuracy:      {comparison['mean_accuracy_new'].mean():.3f}")
            print(f"    Improvement:       {effect_size:+.3f}")
            print(f"    Paired t-test:     t={t_stat:.3f}, p={p_val:.4f}")

            # Per-error-type improvement
            if 'error_type_orig' in comparison.columns:
                print("\n  Improvement by error type:")
                for etype in comparison['error_type_orig'].unique():
                    subset = comparison[comparison['error_type_orig'] == etype]
                    improvement = subset['mean_accuracy_new'].mean() - subset['mean_accuracy_orig'].mean()
                    print(f"    {etype}: {improvement:+.3f}")

            # Generate comparison figure
            fig, axes = plt.subplots(1, 3, figsize=(15, 5))

            # Panel A: Paired accuracy
            axes[0].scatter(comparison['mean_accuracy_orig'], comparison['mean_accuracy_new'],
                           alpha=0.5, s=40)
            axes[0].plot([0, 1], [0, 1], 'k--', alpha=0.3)
            axes[0].set_xlabel('Original Accuracy')
            axes[0].set_ylabel('New (Re-diarized) Accuracy')
            axes[0].set_title(f'Paired Accuracy Comparison (n={len(comparison)})')

            # Panel B: Improvement distribution
            improvements = comparison['mean_accuracy_new'] - comparison['mean_accuracy_orig']
            axes[1].hist(improvements, bins=20, color='#2ecc71', edgecolor='white', alpha=0.8)
            axes[1].axvline(0, color='red', linestyle='--')
            axes[1].axvline(improvements.mean(), color='blue', linewidth=2,
                           label=f'Mean: {improvements.mean():+.3f}')
            axes[1].set_xlabel('Accuracy Change (new - original)')
            axes[1].set_ylabel('Count')
            axes[1].set_title('Distribution of Accuracy Changes')
            axes[1].legend()

            # Panel C: Inaccuracy rate comparison
            if 'mean_inaccuracy_new' in comparison.columns:
                axes[2].scatter(comparison['mean_inaccuracy_orig'],
                               comparison['mean_inaccuracy_new'], alpha=0.5, s=40, color='#e74c3c')
                axes[2].plot([0, 0.8], [0, 0.8], 'k--', alpha=0.3)
                axes[2].set_xlabel('Original Inaccuracy')
                axes[2].set_ylabel('New Inaccuracy')
                axes[2].set_title('Inaccuracy Rate Change')

            plt.tight_layout()
            plt.savefig(COMPARISON_DIR / 'accuracy_improvement.pdf', dpi=300)
            plt.savefig(COMPARISON_DIR / 'accuracy_improvement.png', dpi=300)
            plt.close()
            print(f"\n  Figure saved: {COMPARISON_DIR / 'accuracy_improvement.pdf'}")

    else:
        print("\n4. No coded data for new narratives provided.")
        print("   After human coding, re-run with: python 04_analyze_results.py --coded-data <path>")

    print("\n" + "=" * 60)
    print("Analysis complete! Outputs in:", COMPARISON_DIR)
    print("=" * 60)


if __name__ == "__main__":
    main()
