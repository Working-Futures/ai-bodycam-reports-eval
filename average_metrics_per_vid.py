import json
from statistics import mean

# -------- CONFIG --------
coder1_file = "maya_filtered.json"
coder2_file = "nasser_filtered.json"
output_file = "video_metrics.json"

LIKERT_MAP = {
    "strongly_disagree": 1,
    "disagree": 2,
    "agree": 3,
    "strongly_agree": 4
}

VALID_FACT_LABELS = {"accurate", "inaccurate", "unsupported"}


# -------- HELPERS --------
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def safe_mean(values):
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def average_likert_per_question(video1, video2):
    result = {}

    q1_list = video1.get("likertQuestions", [])
    q2_list = video2.get("likertQuestions", [])

    max_len = max(len(q1_list), len(q2_list))

    for i in range(max_len):
        q1 = q1_list[i] if i < len(q1_list) else None
        q2 = q2_list[i] if i < len(q2_list) else None

        scores = []

        if q1 and q1.get("value") in LIKERT_MAP:
            scores.append(LIKERT_MAP[q1["value"]])

        if q2 and q2.get("value") in LIKERT_MAP:
            scores.append(LIKERT_MAP[q2["value"]])

        if scores:
            qid = q1.get("id") if q1 else q2.get("id")
            result[f"question_{qid}"] = mean(scores)

    return result


def compute_atomic_rates(video1, video2):
    facts1 = video1.get("atomicFacts", [])
    facts2 = video2.get("atomicFacts", [])

    accurate = 0
    unsupported = 0
    inaccurate = 0
    total = 0

    max_len = max(len(facts1), len(facts2))

    for i in range(max_len):
        f1 = facts1[i] if i < len(facts1) else None
        f2 = facts2[i] if i < len(facts2) else None

        for fact in (f1, f2):
            if fact and fact.get("value") in VALID_FACT_LABELS:
                total += 1

                if fact["value"] == "accurate":
                    accurate += 1
                elif fact["value"] == "unsupported":
                    unsupported += 1
                elif fact["value"] == "inaccurate":
                    inaccurate += 1

    if total == 0:
        return None, None, None

    return (
        accurate / total,
        unsupported / total,
        inaccurate / total
    )


# -------- MAIN --------
coder1 = load_json(coder1_file)
coder2 = load_json(coder2_file)

videos = sorted(set(coder1.keys()) & set(coder2.keys()))

results = {}

for video in videos:

    v1 = coder1[video]
    v2 = coder2[video]

    likert_averages = average_likert_per_question(v1, v2)
    narrative_quality = safe_mean(list(likert_averages.values()))

    accuracy_rate, hallucination_rate, inaccuracy_rate = compute_atomic_rates(v1, v2)

    results[video] = {
        "likert_averages": likert_averages,
        "narrative_quality": narrative_quality,
        "accuracy_rate": accuracy_rate,
        "hallucination_rate": hallucination_rate,
        "inaccuracy_rate": inaccuracy_rate
    }


with open(output_file, "w") as f:
    json.dump(results, f, indent=2)

