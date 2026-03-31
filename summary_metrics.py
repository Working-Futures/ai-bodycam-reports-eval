import json
import statistics

input_file = "video_metrics.json"
output_file = "overall_metrics.json"


with open(input_file) as f:
    data = json.load(f)


accuracy = []
hallucination = []
inaccuracy = []
narrative_quality = []


for video, metrics in data.items():

    if metrics["accuracy_rate"] is not None:
        accuracy.append(metrics["accuracy_rate"])

    if metrics["hallucination_rate"] is not None:
        hallucination.append(metrics["hallucination_rate"])

    if metrics["inaccuracy_rate"] is not None:
        inaccuracy.append(metrics["inaccuracy_rate"])

    if metrics["narrative_quality"] is not None:
        narrative_quality.append(metrics["narrative_quality"])


def summarize(values):
    if not values:
        return None

    return {
        "mean": statistics.mean(values),
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
        "min": min(values),
        "max": max(values)
    }


results = {
    "accuracy_rate": summarize(accuracy),
    "hallucination_rate": summarize(hallucination),
    "inaccuracy_rate": summarize(inaccuracy),
    "narrative_quality": summarize(narrative_quality)
}



with open(output_file, "w") as f:
    json.dump(results, f, indent=2)


