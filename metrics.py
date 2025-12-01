import json, csv, re
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer, util

_WORD_RE = re.compile(r"[A-Za-z0-9']+")

def tokenize(s: str):
    return _WORD_RE.findall((s or "").lower())

def wer(ref: str, hyp: str) -> float:
    r, h = tokenize(ref), tokenize(hyp)
    R, H = len(r), len(h)
    if R == 0:
        return 0.0 if H == 0 else 1.0
    dp = [[0]*(H+1) for _ in range(R+1)]
    for i in range(R+1): dp[i][0] = i
    for j in range(H+1): dp[0][j] = j
    for i in range(1, R+1):
        for j in range(1, H+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,
                dp[i][j-1] + 1,
                dp[i-1][j-1] + cost
            )
    return dp[R][H] / R

def sbert_score(model, a: str, b: str) -> float:
    ea = model.encode(a or "", convert_to_tensor=True)
    eb = model.encode(b or "", convert_to_tensor=True)
    return float(util.cos_sim(ea, eb).item())

def load_json(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def pad_to_equal(gt: List[Dict], asr: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    n_gt, n_asr = len(gt), len(asr)
    if n_gt == n_asr:
        return gt, asr
    pad_seg = {"text": "", "speaker": ""}
    if n_gt < n_asr:
        gt = gt + [pad_seg.copy() for _ in range(n_asr - n_gt)]
    else:
        asr = asr + [pad_seg.copy() for _ in range(n_gt - n_asr)]
    return gt, asr

def run_metrics(gt_path: str, asr_path: str, out_prefix: str) -> dict:
    """
    Runs WER, semantic similarity, and speaker accuracy evaluation.
    Writes CSV + JSON outputs following the metrics_pad.py behavior.
    
    Parameters:
        gt_path (str)  - path to ground truth JSON
        asr_path (str) - path to ASR JSON
        out_prefix (str) - prefix for output files (e.g., "results/run1")
    
    Returns:
        dict summary of overall metrics
    """

    gt = load_json(gt_path)
    asr = load_json(asr_path)

    orig_gt_len, orig_asr_len = len(gt), len(asr)
    gt, asr = pad_to_equal(gt, asr)
    print(f"Aligned lengths: GT {orig_gt_len} → {len(gt)}, ASR {orig_asr_len} → {len(asr)}")

    model = SentenceTransformer('all-MiniLM-L6-v2')

    rows = []
    tot_sem, tot_wer, spk_ok = 0.0, 0.0, 0

    for i, (g, a) in enumerate(zip(gt, asr), start=1):
        gt_text = g.get("text", "") or ""
        asr_text = a.get("text", "") or ""

        sem = sbert_score(model, gt_text, asr_text)
        w = wer(gt_text, asr_text)
        spk = int((g.get("speaker","").strip()) == (a.get("speaker","").strip()))

        tot_sem += sem
        tot_wer += w
        spk_ok += spk

        rows.append({
            "index": i,
            "gt_speaker": g.get("speaker",""),
            "asr_speaker": a.get("speaker",""),
            "speaker_correct": spk,
            "semantic_similarity": round(sem, 6),
            "wer": round(w, 6),
            "gt_text": gt_text,
            "asr_text": asr_text
        })

    n = len(rows) if rows else 1

    summary = {
        "segments_compared": len(rows),
        "average_semantic_similarity": round(tot_sem / n, 6),
        "average_wer": round(tot_wer / n, 6),
        "speaker_accuracy": round(spk_ok / n, 6),
        "notes": (
            "Empty segments preserved. Shorter file padded with empty rows "
            "so extra/hallucinated content is penalized."
        )
    }

    # Output CSV
    csv_path = f"{out_prefix}_per_segment.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    # Output summary JSON
    summ_path = f"{out_prefix}_summary.json"
    with open(summ_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Segments compared: {summary['segments_compared']}")
    print(f"Avg Semantic Similarity: {summary['average_semantic_similarity']:.4f}")
    print(f"Avg WER:                {summary['average_wer']:.4f}")
    print(f"Speaker Accuracy:       {summary['speaker_accuracy']:.4f}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {summ_path}")

    return summary
