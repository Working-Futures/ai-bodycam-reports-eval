#!/usr/bin/env python3
"""
Generate all figures and tables for the AI-generated police report accuracy paper.

This script reproduces every figure and LaTeX table used in the paper from
the coded data CSVs. It does NOT require running the diarization ablation
pipeline or any API calls — just the data files in results/.

Requirements:
    pip install pandas numpy scipy matplotlib seaborn scikit-learn statsmodels

Usage:
    python generate_paper_figures.py

    # Or from a different directory:
    python generate_paper_figures.py --data-dir /path/to/results --output-dir /path/to/output

Outputs:
    figures/    — PDF + PNG for each figure
    tables/     — .tex file for each table
"""

import argparse
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from scipy.optimize import linear_sum_assignment

# ---------------------------------------------------------------------------
# Styling defaults — publication-quality, serif font, no chartjunk
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.size": 10,
    "font.family": "serif",
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# Consistent color palette across all figures
C_ACCURATE  = "#2ecc71"
C_INACCURATE = "#e74c3c"
C_HALLUCINATION = "#9b59b6"


# ===================================================================
# DATA LOADING
# ===================================================================

def load_all_data(data_dir: Path) -> dict:
    """Load every CSV produced by the analysis pipeline."""
    d = {}
    files = {
        "facts":           "all_fact_labels.csv",
        "likert":          "all_likert_labels.csv",
        "consensus":       "consensus_labels.csv",
        "per_video":       "per_video_scores.csv",
        "merged":          "merged_analysis.csv",
        "errors_consensus":"grounded_error_taxonomy.csv",
        "errors_broad":    "grounded_error_taxonomy_broad.csv",
        "agreement":       "per_video_agreement.csv",
    }
    for key, fname in files.items():
        path = data_dir / fname
        if path.exists():
            d[key] = pd.read_csv(path)
            print(f"  Loaded {fname}: {len(d[key])} rows")
        else:
            print(f"  WARNING: {fname} not found — some outputs will be skipped")
            d[key] = None
    return d


# ===================================================================
# FIGURE 1: Per-video inaccuracy vs. hallucination (paired dot plot)
# ===================================================================

def fig_inaccuracy_vs_hallucination(data, fig_dir):
    """
    Paired lollipop plot. Each row is one video, sorted by the gap between
    inaccuracy and hallucination. Red dot = inaccuracy rate, purple dot =
    hallucination rate, gray line connects them. The visual argument: in
    virtually every video, red is to the right of purple.
    """
    merged = data["merged"]
    if merged is None:
        return

    df = merged.copy()
    df["gap"] = df["mean_inaccuracy"] - df["mean_hallucination"]
    df = df.sort_values("gap", ascending=True).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(7, 10))
    y = np.arange(len(df))

    # Connecting lines
    for i, row in df.iterrows():
        ax.plot(
            [row["mean_hallucination"], row["mean_inaccuracy"]], [i, i],
            color="#bdc3c7", linewidth=1, zorder=1,
        )

    # Dots
    ax.scatter(df["mean_inaccuracy"], y, color=C_INACCURATE, s=28, zorder=2,
               label="Inaccuracy rate", edgecolors="#c0392b", linewidth=0.5)
    ax.scatter(df["mean_hallucination"], y, color=C_HALLUCINATION, s=28, zorder=2,
               label="Hallucination rate", edgecolors="#8e44ad", linewidth=0.5)

    ax.set_yticks([])
    ax.set_xlabel("Rate")
    ax.set_title(
        f"Per-Video Inaccuracy vs. Hallucination Rate\n"
        f"(n = {len(df)} reports, sorted by gap)",
        fontweight="bold",
    )
    ax.set_xlim(-0.02, 0.75)

    n_dom = (df["gap"] > 0).sum()
    ax.text(
        0.97, 0.03,
        f"Inaccuracy > hallucination\nin {n_dom}/{len(df)} videos "
        f"({n_dom/len(df)*100:.0f}%)\n"
        f"Median gap: {df['gap'].median():.3f}\nMean gap: {df['gap'].mean():.3f}",
        transform=ax.transAxes, fontsize=9, va="bottom", ha="right",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#fef9e7",
                  edgecolor="#f0e68c", alpha=0.9),
    )

    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)

    _save(fig, fig_dir, "fig1_inaccuracy_vs_hallucination")


# ===================================================================
# FIGURE 2: Ranked accuracy waterfall with tail risk
# ===================================================================

def fig_ranked_accuracy(data, fig_dir):
    """
    Bar chart of every video's accuracy, sorted worst-to-best, color-coded
    red→orange→yellow→green. Shaded region on the left highlights the
    bottom 10% ("tail risk"). Mean line across the middle.
    """
    merged = data["merged"]
    if merged is None:
        return

    sorted_acc = merged["mean_accuracy"].sort_values().reset_index(drop=True)
    n = len(sorted_acc)
    n_tail = max(1, int(n * 0.10))

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(n)

    # Tail shading
    ax.axvspan(-0.5, n_tail - 0.5, alpha=0.15, color=C_INACCURATE, zorder=0)
    ax.axvline(n_tail - 0.5, color=C_INACCURATE, linewidth=1,
               linestyle="--", alpha=0.7)

    # Color each bar by accuracy level
    colors = []
    for v in sorted_acc:
        if v < 0.5:
            colors.append("#e74c3c")
        elif v < 0.7:
            colors.append("#e67e22")
        elif v < 0.85:
            colors.append("#f1c40f")
        else:
            colors.append("#2ecc71")

    ax.bar(x, sorted_acc, color=colors, width=1.0, edgecolor="none", alpha=0.85)

    # Mean line
    mean_acc = sorted_acc.mean()
    ax.axhline(mean_acc, color="#2c3e50", linewidth=1.5, linestyle="-", zorder=3)
    ax.text(n * 0.65, mean_acc + 0.015, f"Mean = {mean_acc:.1%}",
            fontsize=10, color="#2c3e50", fontweight="bold")

    # 50% threshold
    ax.axhline(0.5, color=C_INACCURATE, linewidth=1, linestyle=":", alpha=0.6)
    ax.text(n * 0.02, 0.51, "50% accuracy threshold",
            fontsize=8, color=C_INACCURATE, alpha=0.8)

    # Tail annotation
    tail_mean = sorted_acc.head(n_tail).mean()
    ax.annotate(
        f"Bottom 10%\n(n={n_tail})\nMean acc: {tail_mean:.1%}",
        xy=(n_tail / 2, tail_mean), xytext=(n_tail + 8, 0.35),
        fontsize=9, color="#c0392b",
        arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fadbd8",
                  edgecolor=C_INACCURATE, alpha=0.9),
    )

    # Top 10% annotation
    top_mean = sorted_acc.tail(n_tail).mean()
    ax.annotate(
        f"Top 10%\nMean acc: {top_mean:.1%}",
        xy=(n - n_tail / 2, top_mean), xytext=(n - n_tail - 15, 0.98),
        fontsize=9, color="#27ae60",
        arrowprops=dict(arrowstyle="->", color="#27ae60", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#d5f5e3",
                  edgecolor="#27ae60", alpha=0.9),
    )

    ax.set_xlabel("Reports (ranked worst → best)")
    ax.set_ylabel("Factual Accuracy Rate")
    ax.set_title(
        f"Report-Level Accuracy: Variance and Tail Risk\n"
        f"(n = {n} AI-generated police reports)",
        fontweight="bold",
    )
    ax.set_ylim(0, 1.05)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_xticks([])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _save(fig, fig_dir, "fig2_ranked_accuracy")


# ===================================================================
# FIGURE 3: Error taxonomy with pipeline attribution
# ===================================================================

def fig_pipeline_error_attribution(data, fig_dir):
    """
    Two-part figure. Top: pipeline flow diagram (BWC Audio → WhisperX ASR +
    Diarization → Transcript → Gemini LLM) with error counts attributed to
    each stage. Bottom: horizontal bar chart of all error types, color-coded
    by originating pipeline stage.
    """
    errors = data["errors_consensus"]
    if errors is None:
        return

    error_counts = errors["error_type"].value_counts()
    total = len(errors)

    # Map each error type to a pipeline stage
    STAGE_MAP = {
        "Speaker misattribution (officer/civilian swap)": "ASR / Diarization",
        "Statement/dialogue distortion":    "LLM Generation",
        "Action/event distortion":          "LLM Generation",
        "Temporal/causal error":            "LLM Generation",
        "Identification/description error": "LLM Generation",
        "Object/evidence detail error":     "LLM Generation",
        "Legal/procedural distortion":      "LLM Generation",
        "Severity/tone distortion":         "LLM Generation",
        "Other distortion":                 "Ambiguous",
    }
    STAGE_COLOR = {
        "ASR / Diarization": "#e74c3c",
        "LLM Generation":    "#e67e22",
        "Ambiguous":          "#95a5a6",
    }

    # Aggregate counts by stage
    stage_counts = {}
    for etype, count in error_counts.items():
        stage = STAGE_MAP.get(etype, "Ambiguous")
        stage_counts[stage] = stage_counts.get(stage, 0) + count

    fig = plt.figure(figsize=(10, 7))

    # ---------- Top half: pipeline diagram ----------
    ax_pipe = fig.add_axes([0.05, 0.55, 0.9, 0.4])
    ax_pipe.set_xlim(0, 10)
    ax_pipe.set_ylim(0, 3)
    ax_pipe.axis("off")

    from matplotlib.patches import FancyBboxPatch

    boxes = [
        (0.3,  1.2, 1.8, 0.9, "BWC\nAudio",               "#ecf0f1", "#bdc3c7"),
        (2.8,  1.2, 2.0, 0.9, "WhisperX\nASR + Diarization", "#fadbd8", "#e74c3c"),
        (5.5,  1.2, 1.5, 0.9, "Transcript",                "#ecf0f1", "#bdc3c7"),
        (7.7,  1.2, 1.8, 0.9, "Gemini\nLLM",              "#fdebd0", "#e67e22"),
    ]
    for bx, by, bw, bh, label, fc, ec in boxes:
        box = FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.1",
                              facecolor=fc, edgecolor=ec, linewidth=2)
        ax_pipe.add_patch(box)
        ax_pipe.text(bx + bw / 2, by + bh / 2, label,
                     ha="center", va="center", fontsize=9, fontweight="bold")

    arrow_kw = dict(arrowstyle="->", color="#7f8c8d", lw=2, mutation_scale=15)
    for x_from, x_to in [(2.15, 2.75), (4.85, 5.45), (7.05, 7.65)]:
        ax_pipe.annotate("", xy=(x_to, 1.65), xytext=(x_from, 1.65),
                         arrowprops=arrow_kw)

    # Error-count annotations pointing down from stages
    asr_count = stage_counts.get("ASR / Diarization", 0)
    llm_count = stage_counts.get("LLM Generation", 0)
    amb_count = stage_counts.get("Ambiguous", 0)

    ax_pipe.annotate(
        f"{asr_count} errors\n({asr_count/total*100:.0f}%)",
        xy=(3.8, 1.2), xytext=(3.8, 0.3),
        fontsize=10, fontweight="bold", color="#c0392b", ha="center",
        arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=1.5),
    )
    ax_pipe.annotate(
        f"{llm_count} errors\n({llm_count/total*100:.0f}%)",
        xy=(8.6, 1.2), xytext=(8.6, 0.3),
        fontsize=10, fontweight="bold", color="#d35400", ha="center",
        arrowprops=dict(arrowstyle="->", color="#e67e22", lw=1.5),
    )
    ax_pipe.text(5.0, 0.15,
                 f"{amb_count} errors ({amb_count/total*100:.0f}%) — ambiguous origin",
                 fontsize=8, color="#7f8c8d", ha="center", style="italic")

    ax_pipe.set_title("Error Attribution Across Pipeline Stages",
                      fontsize=13, fontweight="bold", pad=10)

    # ---------- Bottom half: detailed bar chart ----------
    ax_bar = fig.add_axes([0.12, 0.06, 0.82, 0.42])

    short_names = {
        "Speaker misattribution (officer/civilian swap)": "Speaker misattribution\n(officer ↔ civilian)",
        "Other distortion": "Other distortion",
        "Statement/dialogue distortion": "Statement/dialogue\ndistortion",
        "Identification/description error": "Identification/\ndescription error",
        "Object/evidence detail error": "Object/evidence\ndetail error",
        "Action/event distortion": "Action/event\ndistortion",
        "Legal/procedural distortion": "Legal/procedural\ndistortion",
        "Temporal/causal error": "Temporal/causal\nerror",
        "Severity/tone distortion": "Severity/tone\ndistortion",
    }

    labels = [short_names.get(e, e) for e in error_counts.index]
    colors = [STAGE_COLOR.get(STAGE_MAP.get(e, "Ambiguous"), "#95a5a6")
              for e in error_counts.index]
    counts = error_counts.values
    pcts = counts / total * 100

    ax_bar.barh(range(len(counts)), counts, color=colors,
                edgecolor="white", linewidth=0.5, height=0.7)
    ax_bar.set_yticks(range(len(counts)))
    ax_bar.set_yticklabels(labels, fontsize=9)
    ax_bar.invert_yaxis()

    for i, (c, p) in enumerate(zip(counts, pcts)):
        ax_bar.text(c + 2, i, f"{c} ({p:.1f}%)", va="center", fontsize=9)

    ax_bar.set_xlabel("Number of Consensus-Inaccurate Facts")
    ax_bar.set_xlim(0, max(counts) * 1.25)
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)

    import matplotlib.patches as mpatches
    legend_elements = [
        mpatches.Patch(facecolor="#e74c3c", label="ASR / Diarization stage"),
        mpatches.Patch(facecolor="#e67e22", label="LLM generation stage"),
        mpatches.Patch(facecolor="#95a5a6", label="Ambiguous origin"),
    ]
    ax_bar.legend(handles=legend_elements, loc="lower right",
                  fontsize=8, framealpha=0.9)

    _save(fig, fig_dir, "fig3_pipeline_error_attribution")


# ===================================================================
# FIGURE 4: Inter-rater agreement (confusion matrix + scatter)
# ===================================================================

def fig_inter_rater_agreement(data, fig_dir):
    """
    Left panel: 3×3 confusion matrix heatmap (Maya rows × Nasser columns).
    Right panel: per-video accuracy scatter (Maya x-axis, Nasser y-axis).
    """
    consensus = data["consensus"]
    per_video = data["per_video"]
    if consensus is None or per_video is None:
        return

    # -- Build confusion matrix --
    labels_order = ["accurate", "inaccurate", "unsupported"]
    label_display = ["Accurate", "Inaccurate", "Unsupported"]
    cm = np.zeros((3, 3), dtype=int)
    for _, row in consensus.iterrows():
        ml = row["maya_label"]
        nl = row["nasser_label"]
        if ml in labels_order and nl in labels_order:
            cm[labels_order.index(ml), labels_order.index(nl)] += 1

    n_total = cm.sum()
    raw_agreement = np.trace(cm) / n_total

    # Cohen's kappa
    p_o = raw_agreement
    row_sums = cm.sum(axis=1) / n_total
    col_sums = cm.sum(axis=0) / n_total
    p_e = np.sum(row_sums * col_sums)
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) != 0 else 0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # -- Left: heatmap --
    im = ax1.imshow(cm, cmap="Blues", aspect="auto")
    ax1.set_xticks(range(3))
    ax1.set_yticks(range(3))
    ax1.set_xticklabels(label_display, fontsize=9)
    ax1.set_yticklabels(label_display, fontsize=9)
    ax1.set_xlabel("Nasser")
    ax1.set_ylabel("Maya")

    # Annotate cells with counts
    for i in range(3):
        for j in range(3):
            color = "white" if cm[i, j] > cm.max() * 0.5 else "black"
            ax1.text(j, i, str(cm[i, j]), ha="center", va="center",
                     fontsize=12, fontweight="bold", color=color)

    ax1.set_title(f"Confusion Matrix (N={n_total:,} facts)\n"
                  f"Cohen's κ={kappa:.3f}")

    # -- Right: per-video scatter --
    r_val, p_val = stats.pearsonr(per_video["maya_accuracy"],
                                   per_video["nasser_accuracy"])

    ax2.scatter(per_video["maya_accuracy"], per_video["nasser_accuracy"],
                alpha=0.5, s=40, color="#3498db", edgecolors="#2980b9",
                linewidth=0.5)
    ax2.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)

    # Regression line
    m, b = np.polyfit(per_video["maya_accuracy"], per_video["nasser_accuracy"], 1)
    x_line = np.linspace(0, 1, 100)
    ax2.plot(x_line, m * x_line + b, color="#e74c3c", linewidth=1.5, alpha=0.7)

    ax2.set_xlabel("Maya Accuracy Rate")
    ax2.set_ylabel("Nasser Accuracy Rate")
    ax2.set_title(f"Per-Video Accuracy by Coder (r={r_val:.3f})")
    ax2.set_xlim(-0.05, 1.05)
    ax2.set_ylim(-0.05, 1.05)

    plt.tight_layout()
    _save(fig, fig_dir, "inter_rater_agreement")


# ===================================================================
# FIGURE 5: Accuracy distributions (triple histogram)
# ===================================================================

def fig_accuracy_distributions(data, fig_dir):
    """Three overlaid histograms: accuracy, inaccuracy, hallucination rates."""
    merged = data["merged"]
    if merged is None:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    bins = np.linspace(0, 1, 25)

    ax.hist(merged["mean_accuracy"], bins=bins, alpha=0.6,
            color=C_ACCURATE, label="Accuracy", edgecolor="white")
    ax.hist(merged["mean_inaccuracy"], bins=bins, alpha=0.6,
            color=C_INACCURATE, label="Inaccuracy", edgecolor="white")
    ax.hist(merged["mean_hallucination"], bins=bins, alpha=0.6,
            color=C_HALLUCINATION, label="Hallucination", edgecolor="white")

    ax.set_xlabel("Rate")
    ax.set_ylabel("Number of Videos")
    ax.set_title("Distribution of Accuracy, Inaccuracy, and Hallucination Rates")
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _save(fig, fig_dir, "accuracy_distributions_actual")


# ===================================================================
# FIGURE 6: Accuracy vs. narrative quality scatter
# ===================================================================

def fig_accuracy_vs_quality(data, fig_dir):
    """Scatter of mean accuracy vs. narrative quality with regression line."""
    merged = data["merged"]
    if merged is None or "narrative_quality" not in merged.columns:
        return

    valid = merged.dropna(subset=["mean_accuracy", "narrative_quality"])
    r_val, p_val = stats.pearsonr(valid["mean_accuracy"],
                                   valid["narrative_quality"])
    rho, rho_p = stats.spearmanr(valid["mean_accuracy"],
                                  valid["narrative_quality"])

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(valid["mean_accuracy"], valid["narrative_quality"],
               alpha=0.5, s=40, color="#3498db", edgecolors="#2980b9",
               linewidth=0.5)

    m, b = np.polyfit(valid["mean_accuracy"], valid["narrative_quality"], 1)
    x_line = np.linspace(valid["mean_accuracy"].min(),
                          valid["mean_accuracy"].max(), 100)
    ax.plot(x_line, m * x_line + b, color=C_INACCURATE, linewidth=1.5)

    ax.set_xlabel("Mean Factual Accuracy Rate")
    ax.set_ylabel("Narrative Quality (mean Likert)")
    ax.set_title(f"Accuracy vs. Narrative Quality\n"
                 f"Pearson r={r_val:.3f} (p<0.001), Spearman ρ={rho:.3f}")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _save(fig, fig_dir, "accuracy_vs_quality_actual")


# ===================================================================
# FIGURE 7: Sensitivity analysis (grouped bars)
# ===================================================================

def fig_sensitivity(data, fig_dir):
    """
    Grouped bar chart: 4 approaches to resolving coder disagreements,
    each showing accuracy / inaccuracy / hallucination rates.
    """
    facts = data["facts"]
    merged = data["merged"]
    if facts is None or merged is None:
        return

    both = facts.dropna(subset=["maya_label", "nasser_label"])
    n = len(both)

    # Strict
    s_acc = ((both["maya_label"] == "accurate") &
             (both["nasser_label"] == "accurate")).sum() / n
    s_ina = ((both["maya_label"] == "inaccurate") &
             (both["nasser_label"] == "inaccurate")).sum() / n
    s_hal = ((both["maya_label"] == "unsupported") &
             (both["nasser_label"] == "unsupported")).sum() / n

    # Mean of coders
    m_acc = merged["mean_accuracy"].mean()
    m_ina = merged["mean_inaccuracy"].mean()
    m_hal = merged["mean_hallucination"].mean()

    # Lenient (either says accurate → accurate)
    def _lenient(r):
        if r["maya_label"] == "accurate" or r["nasser_label"] == "accurate":
            return "accurate"
        if r["maya_label"] == "unsupported" or r["nasser_label"] == "unsupported":
            return "unsupported"
        return "inaccurate"

    lenient = both.apply(_lenient, axis=1)
    l_acc = (lenient == "accurate").sum() / n
    l_ina = (lenient == "inaccurate").sum() / n
    l_hal = (lenient == "unsupported").sum() / n

    # Generous (all disagreements → accurate)
    def _generous(r):
        if r["maya_label"] == r["nasser_label"]:
            return r["maya_label"]
        return "accurate"

    generous = both.apply(_generous, axis=1)
    g_acc = (generous == "accurate").sum() / n
    g_ina = (generous == "inaccurate").sum() / n
    g_hal = (generous == "unsupported").sum() / n

    approaches = ["Strict\n(both agree)", "Mean of\ncoders",
                  "Lenient\n(either acc.)", "Generous\n(disagree→acc.)"]
    acc_vals = [s_acc, m_acc, l_acc, g_acc]
    ina_vals = [s_ina, m_ina, l_ina, g_ina]
    hal_vals = [s_hal, m_hal, l_hal, g_hal]

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(4)
    w = 0.25
    ax.bar(x - w, acc_vals, w, label="Accuracy", color=C_ACCURATE)
    ax.bar(x, ina_vals, w, label="Inaccuracy", color=C_INACCURATE)
    ax.bar(x + w, hal_vals, w, label="Hallucination", color=C_HALLUCINATION)
    ax.set_xticks(x)
    ax.set_xticklabels(approaches, fontsize=9)
    ax.set_ylabel("Rate")
    ax.set_title("Core Finding Robustness: Inaccuracy >> Hallucination "
                 "Under All Approaches")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 1.05)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _save(fig, fig_dir, "sensitivity_analysis")


# ===================================================================
# FIGURE 8: Coder comparison (side-by-side per-video accuracy bars)
# ===================================================================

def fig_coder_comparison(data, fig_dir):
    """Side-by-side bars showing Maya vs Nasser accuracy for each video."""
    pv = data["per_video"]
    if pv is None:
        return

    pv_sorted = pv.sort_values("mean_accuracy").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(pv_sorted))
    w = 0.4

    ax.bar(x - w / 2, pv_sorted["maya_accuracy"], w, label="Maya",
           color="#3498db", alpha=0.8)
    ax.bar(x + w / 2, pv_sorted["nasser_accuracy"], w, label="Nasser",
           color="#e67e22", alpha=0.8)

    ax.set_ylabel("Accuracy Rate")
    ax.set_xlabel("Videos (sorted by mean accuracy)")
    ax.set_title("Per-Video Accuracy by Coder")
    ax.set_xticks([])
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    _save(fig, fig_dir, "coder_comparison")


# ===================================================================
# FIGURE 9: Feature correlations
# ===================================================================

def fig_feature_correlations(data, fig_dir):
    """Scatter matrix of transcript features vs accuracy."""
    merged = data["merged"]
    if merged is None:
        return

    feats = ["total_transcript_words", "n_speakers", "transcript_duration_sec",
             "n_atomic_facts"]
    available = [f for f in feats if f in merged.columns]

    if len(available) < 2:
        return

    fig, axes = plt.subplots(1, len(available), figsize=(4 * len(available), 4))
    if len(available) == 1:
        axes = [axes]

    for ax, feat in zip(axes, available):
        valid = merged.dropna(subset=[feat, "mean_accuracy"])
        ax.scatter(valid[feat], valid["mean_accuracy"], alpha=0.4, s=30,
                   color="#3498db")
        r, p = stats.pearsonr(valid[feat], valid["mean_accuracy"])
        ax.set_xlabel(feat.replace("_", " ").title())
        ax.set_ylabel("Accuracy")
        ax.set_title(f"r={r:.3f}" + (" *" if p < 0.05 else ""))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    plt.suptitle("Transcript Features vs. Factual Accuracy", fontweight="bold")
    plt.tight_layout()
    _save(fig, fig_dir, "feature_correlations")


# ===================================================================
# TABLES
# ===================================================================

def tab_irr(data, tab_dir):
    """Inter-rater reliability table."""
    consensus = data["consensus"]
    if consensus is None:
        return

    labels_order = ["accurate", "inaccurate", "unsupported"]
    cm = np.zeros((3, 3), dtype=int)
    for _, row in consensus.iterrows():
        ml, nl = row["maya_label"], row["nasser_label"]
        if ml in labels_order and nl in labels_order:
            cm[labels_order.index(ml), labels_order.index(nl)] += 1

    n_total = cm.sum()
    p_o = np.trace(cm) / n_total
    row_sums = cm.sum(axis=1) / n_total
    col_sums = cm.sum(axis=0) / n_total
    p_e = np.sum(row_sums * col_sums)
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) != 0 else 0

    # Krippendorff's alpha (nominal) — simplified computation
    # Using the observed disagreement / expected disagreement approach
    labels = {"accurate": 0, "inaccurate": 1, "unsupported": 2}
    vals = []
    for _, row in consensus.iterrows():
        if row["maya_label"] in labels and row["nasser_label"] in labels:
            vals.append((labels[row["maya_label"]], labels[row["nasser_label"]]))
    n_items = len(vals)
    D_o = sum(1 for a, b in vals if a != b) / n_items
    cats = [0, 1, 2]
    freqs = {c: sum(1 for a, b in vals for v in (a, b) if v == c) for c in cats}
    total_annotations = 2 * n_items
    D_e = 1 - sum(freqs[c] * (freqs[c] - 1) for c in cats) / (
        total_annotations * (total_annotations - 1))
    alpha = 1 - D_o / D_e if D_e != 0 else 0

    with open(tab_dir / "irr.tex", "w") as f:
        f.write(r"""\begin{table}[t]
\caption{Inter-Rater Reliability}
\label{tab:irr}
\small
\begin{tabular}{lr}
\toprule
\textbf{Metric} & \textbf{Value} \\
\midrule
""")
        f.write(f"N (jointly coded facts) & {n_total:,} \\\\\n")
        f.write(f"Raw agreement & {p_o:.3f} \\\\\n")
        f.write(f"Cohen's $\\kappa$ (unweighted) & {kappa:.3f} \\\\\n")
        f.write(f"Krippendorff's $\\alpha$ (nominal) & {alpha:.3f} \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
    print(f"  table: irr.tex  (κ={kappa:.3f}, α={alpha:.3f})")


def tab_summary_stats(data, tab_dir):
    """Summary statistics with 95% CIs."""
    merged = data["merged"]
    if merged is None:
        return

    def _ci(col):
        m = col.mean()
        se = col.std() / np.sqrt(len(col))
        return m, m - 1.96 * se, m + 1.96 * se, col.std(), col.min(), col.max()

    metrics = [
        ("Accuracy Rate",    merged["mean_accuracy"]),
        ("Inaccuracy Rate",  merged["mean_inaccuracy"]),
        ("Hallucination Rate", merged["mean_hallucination"]),
    ]
    if "narrative_quality" in merged.columns:
        metrics.append(("Narrative Quality", merged["narrative_quality"]))

    with open(tab_dir / "summary_stats_actual.tex", "w") as f:
        f.write(r"""\begin{table}[t]
\caption{Summary Statistics (Mean-of-Coders)}
\label{tab:summary}
\small
\begin{tabular}{lcccc}
\toprule
\textbf{Metric} & \textbf{Mean} & \textbf{95\% CI} & \textbf{SD} & \textbf{Range} \\
\midrule
""")
        for label, col in metrics:
            m, lo, hi, sd, mn, mx = _ci(col.dropna())
            f.write(f"{label} & {m:.3f} & [{lo:.3f}, {hi:.3f}] "
                    f"& {sd:.3f} & [{mn:.3f}, {mx:.3f}] \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
    print(f"  table: summary_stats_actual.tex")


def tab_sensitivity(data, tab_dir):
    """Sensitivity analysis table (4 approaches)."""
    facts = data["facts"]
    merged = data["merged"]
    if facts is None or merged is None:
        return

    both = facts.dropna(subset=["maya_label", "nasser_label"])
    n = len(both)

    rows = []

    # Strict
    rows.append(("Strict (both agree)",
                 ((both["maya_label"] == "accurate") & (both["nasser_label"] == "accurate")).sum() / n,
                 ((both["maya_label"] == "inaccurate") & (both["nasser_label"] == "inaccurate")).sum() / n,
                 ((both["maya_label"] == "unsupported") & (both["nasser_label"] == "unsupported")).sum() / n))

    # Mean of coders
    rows.append(("Mean-of-coders",
                 merged["mean_accuracy"].mean(),
                 merged["mean_inaccuracy"].mean(),
                 merged["mean_hallucination"].mean()))

    # Lenient
    def _len(r):
        if r["maya_label"] == "accurate" or r["nasser_label"] == "accurate":
            return "accurate"
        if r["maya_label"] == "unsupported" or r["nasser_label"] == "unsupported":
            return "unsupported"
        return "inaccurate"
    lenient = both.apply(_len, axis=1)
    rows.append(("Lenient (either accurate)",
                 (lenient == "accurate").sum() / n,
                 (lenient == "inaccurate").sum() / n,
                 (lenient == "unsupported").sum() / n))

    # Generous
    def _gen(r):
        return r["maya_label"] if r["maya_label"] == r["nasser_label"] else "accurate"
    generous = both.apply(_gen, axis=1)
    rows.append(("Generous (disagree$\\rightarrow$accurate)",
                 (generous == "accurate").sum() / n,
                 (generous == "inaccurate").sum() / n,
                 (generous == "unsupported").sum() / n))

    with open(tab_dir / "sensitivity.tex", "w") as f:
        f.write(r"""\begin{table}[t]
\caption{Sensitivity Analysis: Core Findings Under Different Coding Approaches}
\label{tab:sensitivity}
\small
\begin{tabular}{lcccr}
\toprule
\textbf{Approach} & \textbf{Accuracy} & \textbf{Inaccuracy} & \textbf{Hallucination} & \textbf{Ratio} \\
\midrule
""")
        for label, acc, ina, hal in rows:
            ratio = f"{ina/hal:.1f}$\\times$" if hal > 0 else "---"
            f.write(f"{label} & {acc:.3f} & {ina:.3f} & {hal:.3f} & {ratio} \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
    print(f"  table: sensitivity.tex")


def tab_error_taxonomy(data, tab_dir):
    """Grounded error taxonomy table."""
    errors = data["errors_consensus"]
    if errors is None:
        return

    counts = errors["error_type"].value_counts()
    total = len(errors)

    with open(tab_dir / "grounded_error_taxonomy.tex", "w") as f:
        f.write(r"""\begin{table}[t]
\caption{Transcript-Grounded Error Taxonomy for Consensus-Inaccurate Facts}
\label{tab:error-taxonomy}
\small
\begin{tabular}{lrr}
\toprule
\textbf{Error Type} & \textbf{Count} & \textbf{\%} \\
\midrule
""")
        for etype, count in counts.items():
            clean = etype.replace("&", r"\&")
            f.write(f"{clean} & {count} & {count/total*100:.1f}\\% \\\\\n")
        f.write(f"\\midrule\n\\textbf{{Total}} & "
                f"\\textbf{{{total}}} & \\textbf{{100.0\\%}} \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
    print(f"  table: grounded_error_taxonomy.tex")


def tab_tail_analysis(data, tab_dir):
    """Tail analysis: bottom 10% vs rest."""
    merged = data["merged"]
    if merged is None:
        return

    n_tail = max(1, int(len(merged) * 0.10))
    sorted_df = merged.sort_values("mean_accuracy")
    tail = sorted_df.head(n_tail)
    rest = sorted_df.tail(len(sorted_df) - n_tail)

    rows = []
    for col, label in [("mean_accuracy", "Accuracy"),
                        ("mean_inaccuracy", "Inaccuracy"),
                        ("mean_hallucination", "Hallucination"),
                        ("narrative_quality", "Narrative Quality"),
                        ("n_speakers", "N Speakers"),
                        ("total_transcript_words", "Transcript Words"),
                        ("transcript_duration_sec", "Duration (sec)")]:
        if col not in merged.columns:
            continue
        t_mean = tail[col].mean()
        r_mean = rest[col].mean()
        try:
            _, pval = stats.mannwhitneyu(tail[col].dropna(),
                                          rest[col].dropna(),
                                          alternative="two-sided")
        except Exception:
            pval = np.nan
        rows.append((label, t_mean, r_mean, pval))

    with open(tab_dir / "tail_analysis.tex", "w") as f:
        f.write(r"""\begin{table}[t]
\caption{Tail Analysis: Characteristics of Worst-Performing Reports (Bottom 10\%)}
\label{tab:tail}
\small
\begin{tabular}{lccr}
\toprule
\textbf{Feature} & \textbf{Bottom 10\%} & \textbf{Rest} & \textbf{$p$} \\
\midrule
""")
        for label, t_m, r_m, p in rows:
            pstr = ("$<$0.001" if p < 0.001
                    else f"{p:.3f}" if not np.isnan(p) else "---")
            if not np.isnan(p) and p < 0.05:
                pstr = r"\textbf{" + pstr + "}"
            f.write(f"{label} & {t_m:.2f} & {r_m:.2f} & {pstr} \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
    print(f"  table: tail_analysis.tex")


def tab_likert_items(data, tab_dir):
    """Per-item Likert statistics + Cronbach's alpha."""
    likert = data["likert"]
    if likert is None:
        return

    # Map text values to numeric
    val_map = {"strongly_disagree": 1, "disagree": 2, "agree": 3,
               "strongly_agree": 4, "not_applicable": np.nan}

    likert["maya_num"] = likert["maya_value"].map(val_map)
    likert["nasser_num"] = likert["nasser_value"].map(val_map)
    likert["mean_num"] = likert[["maya_num", "nasser_num"]].mean(axis=1)

    item_stats = likert.groupby("question").agg(
        mean=("mean_num", "mean"),
        sd=("mean_num", "std"),
        n=("mean_num", "count"),
    ).sort_values("mean", ascending=False)

    # Cronbach's alpha
    merged = data["merged"]
    if merged is not None and "narrative_quality" in merged.columns:
        # Build item-by-video matrix
        pivot = likert.pivot_table(values="mean_num", index="video_id",
                                    columns="question_id")
        pivot = pivot.dropna()
        if len(pivot) > 0 and pivot.shape[1] > 1:
            k = pivot.shape[1]
            item_vars = pivot.var(axis=0, ddof=1)
            total_var = pivot.sum(axis=1).var(ddof=1)
            alpha = (k / (k - 1)) * (1 - item_vars.sum() / total_var)
        else:
            alpha = np.nan
    else:
        alpha = np.nan

    with open(tab_dir / "likert_items.tex", "w") as f:
        f.write(r"""\begin{table}[t]
\caption{Narrative Quality: Per-Item Statistics}
\label{tab:likert}
\small
\begin{tabular}{p{7cm}ccr}
\toprule
\textbf{Item} & \textbf{Mean} & \textbf{SD} & \textbf{$n$} \\
\midrule
""")
        for q, row in item_stats.iterrows():
            q_clean = q[:70].replace("&", r"\&").replace("%", r"\%")
            f.write(f"{q_clean} & {row['mean']:.2f} & {row['sd']:.2f} "
                    f"& {int(row['n'])} \\\\\n")

        if not np.isnan(alpha):
            f.write(f"\\midrule\n\\multicolumn{{4}}{{l}}"
                    f"{{Cronbach's $\\alpha$ = {alpha:.3f}}} \\\\\n")

        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
    print(f"  table: likert_items.tex  (α={alpha:.3f})")


def tab_regression(data, tab_dir):
    """Multiple regression: predictors of accuracy."""
    merged = data["merged"]
    if merged is None:
        return

    predictors = ["n_speakers", "total_transcript_words", "transcript_duration_sec"]
    available = [p for p in predictors if p in merged.columns]
    if not available:
        return

    valid = merged.dropna(subset=["mean_accuracy"] + available)
    X = valid[available]
    y = valid["mean_accuracy"]

    try:
        import statsmodels.api as sm
        X_const = sm.add_constant(X)
        model = sm.OLS(y, X_const).fit()

        with open(tab_dir / "regression.tex", "w") as f:
            f.write(r"""\begin{table}[t]
\caption{Multiple Regression: Predictors of Factual Accuracy}
\label{tab:regression}
\small
\begin{tabular}{lcccc}
\toprule
\textbf{Predictor} & \textbf{$\beta$} & \textbf{SE} & \textbf{$t$} & \textbf{$p$} \\
\midrule
""")
            f.write(f"(Intercept) & {model.params['const']:.4f} & "
                    f"{model.bse['const']:.4f} & {model.tvalues['const']:.2f} & "
                    f"{model.pvalues['const']:.3f} \\\\\n")
            for pred in available:
                label = pred.replace("_", " ").title()
                f.write(f"{label} & {model.params[pred]:.4f} & "
                        f"{model.bse[pred]:.4f} & {model.tvalues[pred]:.2f} & "
                        f"{model.pvalues[pred]:.3f} \\\\\n")
            f.write(f"\\midrule\n\\multicolumn{{5}}{{l}}"
                    f"{{$R^2$ = {model.rsquared:.3f}, "
                    f"Adj. $R^2$ = {model.rsquared_adj:.3f}, "
                    f"F({model.df_model:.0f},{model.df_resid:.0f}) = "
                    f"{model.fvalue:.2f}, p = {model.f_pvalue:.4f}}} \\\\\n")
            f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
        print(f"  table: regression.tex  (R²={model.rsquared:.3f})")

    except ImportError:
        print("  WARNING: statsmodels not installed, skipping regression table")


def tab_error_examples(data, tab_dir):
    """Representative error examples with source transcript."""
    errors = data["errors_consensus"]
    if errors is None:
        return

    target_types = [
        "Speaker misattribution (officer/civilian swap)",
        "Statement/dialogue distortion",
        "Identification/description error",
        "Action/event distortion",
        "Temporal/causal error",
    ]

    examples = []
    for etype in target_types:
        subset = errors[errors["error_type"] == etype].sort_values(
            "match_score", ascending=False)
        if len(subset) > 0:
            row = subset.iloc[0]
            examples.append({
                "type": etype.split("(")[0].strip(),
                "claim": str(row["fact_text"])[:80],
                "transcript": str(row["match_text"])[:60],
                "speaker": str(row.get("match_speaker", "")),
            })

    with open(tab_dir / "error_examples.tex", "w") as f:
        f.write(r"""\begin{table*}[t]
\caption{Representative Error Examples: Generated Claims vs.\ Source Transcript}
\label{tab:error-examples}
\small
\begin{tabular}{p{2.2cm}p{5.5cm}p{4.5cm}p{1.5cm}}
\toprule
\textbf{Error Type} & \textbf{Generated Claim} & \textbf{Source Transcript} & \textbf{Speaker} \\
\midrule
""")
        for ex in examples:
            claim = _tex_escape(ex["claim"])
            trans = _tex_escape(ex["transcript"])
            f.write(f"{ex['type']} & {claim} & {trans} & {ex['speaker']} \\\\\n"
                    f"\\addlinespace\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table*}
""")
    print(f"  table: error_examples.tex  ({len(examples)} examples)")


def tab_disagreement_patterns(data, tab_dir):
    """How the coders disagree: which label swaps dominate."""
    consensus = data["consensus"]
    if consensus is None:
        return

    disagree = consensus[consensus["maya_label"] != consensus["nasser_label"]]
    n_disagree = len(disagree)

    patterns = disagree.groupby(["maya_label", "nasser_label"]).size().sort_values(
        ascending=False)

    with open(tab_dir / "disagreement_patterns.tex", "w") as f:
        f.write(r"""\begin{table}[t]
\caption{Disagreement Patterns Between Coders}
\label{tab:disagreements}
\small
\begin{tabular}{llrr}
\toprule
\textbf{Maya} & \textbf{Nasser} & \textbf{Count} & \textbf{\%} \\
\midrule
""")
        for (ml, nl), count in patterns.items():
            f.write(f"{ml} & {nl} & {count} & "
                    f"{count/n_disagree*100:.1f}\\% \\\\\n")
        f.write(f"\\midrule\n\\textbf{{Total}} & & "
                f"\\textbf{{{n_disagree}}} & \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")
    print(f"  table: disagreement_patterns.tex  ({n_disagree} disagreements)")


# ===================================================================
# UTILITIES
# ===================================================================

def _save(fig, fig_dir, name):
    """Save figure as PDF and PNG."""
    fig.savefig(fig_dir / f"{name}.pdf")
    fig.savefig(fig_dir / f"{name}.png")
    plt.close(fig)
    print(f"  figure: {name}.pdf")


def _tex_escape(s):
    """Escape LaTeX special characters."""
    for ch, repl in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"),
                      ("_", r"\_"), ('"', "''")]:
        s = s.replace(ch, repl)
    return s


# ===================================================================
# MAIN
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate all figures and tables for the paper."
    )
    parser.add_argument(
        "--data-dir", type=str, default=None,
        help="Path to results/ directory with CSVs "
             "(default: ../results/ relative to this script)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Path to write figures/ and tables/ "
             "(default: same directory as this script)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    data_dir = Path(args.data_dir) if args.data_dir else (script_dir.parent / "results")
    output_dir = Path(args.output_dir) if args.output_dir else script_dir

    fig_dir = output_dir / "figures"
    tab_dir = output_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("GENERATING PAPER FIGURES AND TABLES")
    print(f"  Data:    {data_dir}")
    print(f"  Figures: {fig_dir}")
    print(f"  Tables:  {tab_dir}")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    data = load_all_data(data_dir)

    # Generate figures
    print("\nGenerating figures...")
    fig_inaccuracy_vs_hallucination(data, fig_dir)
    fig_ranked_accuracy(data, fig_dir)
    fig_pipeline_error_attribution(data, fig_dir)
    fig_inter_rater_agreement(data, fig_dir)
    fig_accuracy_distributions(data, fig_dir)
    fig_accuracy_vs_quality(data, fig_dir)
    fig_sensitivity(data, fig_dir)
    fig_coder_comparison(data, fig_dir)
    fig_feature_correlations(data, fig_dir)

    # Generate tables
    print("\nGenerating tables...")
    tab_irr(data, tab_dir)
    tab_summary_stats(data, tab_dir)
    tab_sensitivity(data, tab_dir)
    tab_error_taxonomy(data, tab_dir)
    tab_tail_analysis(data, tab_dir)
    tab_likert_items(data, tab_dir)
    tab_regression(data, tab_dir)
    tab_error_examples(data, tab_dir)
    tab_disagreement_patterns(data, tab_dir)

    print("\n" + "=" * 60)
    print("Done! All outputs in:", output_dir)
    print("=" * 60)


if __name__ == "__main__":
    main()
