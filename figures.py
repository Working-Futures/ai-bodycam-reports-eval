import json
import os
import matplotlib.pyplot as plt

input_file = "video_metrics.json"
output_dir = "figures"

os.makedirs(output_dir, exist_ok=True)

with open(input_file, "r") as f:
    data = json.load(f)

accuracy_rates = []
hallucination_rates = []
narrative_quality_scores = []

for video, metrics in data.items():
    acc = metrics.get("accuracy_rate")
    hall = metrics.get("hallucination_rate")
    nq = metrics.get("narrative_quality")

    if acc is not None:
        accuracy_rates.append(acc)
    if hall is not None:
        hallucination_rates.append(hall)
    if nq is not None:
        narrative_quality_scores.append(nq)

# -------- FIGURE 1: ACCURACY DISTRIBUTION --------
plt.figure(figsize=(8, 5))
plt.hist(accuracy_rates, bins=10, edgecolor="black")
plt.title("Distribution of Factual Accuracy Rates Across Reports")
plt.xlabel("Accuracy Rate")
plt.ylabel("Number of Reports")
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "figure1_accuracy_distribution.png"), dpi=300)
plt.close()

# -------- FIGURE 2: HALLUCINATION DISTRIBUTION --------
plt.figure(figsize=(8, 5))
plt.hist(hallucination_rates, bins=10, edgecolor="black")
plt.title("Distribution of Hallucination Rates Across Reports")
plt.xlabel("Hallucination Rate")
plt.ylabel("Number of Reports")
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "figure2_hallucination_distribution.png"), dpi=300)
plt.close()

# -------- FIGURE 3: NARRATIVE QUALITY DISTRIBUTION --------
plt.figure(figsize=(8, 5))
plt.hist(narrative_quality_scores, bins=10, edgecolor="black")
plt.title("Distribution of Narrative Quality Scores Across Reports")
plt.xlabel("Narrative Quality Score")
plt.ylabel("Number of Reports")
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "figure3_narrative_quality_distribution.png"), dpi=300)
plt.close()
# -------- FIGURE 4: ACCURACY VS NARRATIVE QUALITY --------
plt.figure(figsize=(8, 5))

plt.scatter(
    accuracy_rates,
    narrative_quality_scores
)

plt.title("Accuracy Rate vs Narrative Quality")
plt.xlabel("Accuracy Rate")
plt.ylabel("Narrative Quality Score")

plt.tight_layout()

plt.savefig(
    os.path.join(output_dir, "figure4_accuracy_vs_narrative_quality.png"),
    dpi=300
)

plt.close()
