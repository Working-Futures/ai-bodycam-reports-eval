import json
import time
from pathlib import Path
from google import genai
from google.genai import types


def batch_generate_atomic_facts(
    api_key: str,
    input_dir: str = "narratives",
    output_dir: str = "atomic_facts",
    total_files: int = 112,
    model: str = "models/gemini-3-pro-preview",
    batch_requests_jsonl: str = "atomic_facts_requests.jsonl",
    batch_results_jsonl: str = "atomic_facts_results.jsonl",
    poll_seconds: int = 20,
) -> None:
    """
    End-to-end batch pipeline in ONE function:

    Input:
      narratives/narrative_01.txt ... narratives/narrative_112.txt

    Output:
      atomic_facts/atomic_facts_01.txt ... atomic_facts/atomic_facts_112.txt

    Steps:
      1) Build JSONL batch requests from narrative txt files
      2) Upload JSONL
      3) Create batch job
      4) Poll until completion
      5) Download results JSONL
      6) Write atomic facts text files
    """

    input_dir_p = Path(input_dir)
    output_dir_p = Path(output_dir)
    output_dir_p.mkdir(parents=True, exist_ok=True)

    batch_requests_path = Path(batch_requests_jsonl)
    batch_results_path = Path(batch_results_jsonl)

    prompt = """You are an information extraction assistant. Your task is to decompose a police report into atomic fact sentences.
Definition:
 An atomic fact is a short, self-contained sentence that conveys exactly one piece of verifiable information from the report — no interpretation, inference, or combination of multiple facts.
Instructions:
Use only the information explicitly stated in the report.

Maintain first-person perspective when the officer is speaking (e.g., “I arrived at the scene.”).

Do not include times, names, or locations unless explicitly given. If placeholders are used in the text (e.g., [INSERT: name of driver]), keep them as-is.

Each fact should be one simple, declarative sentence.

Output only the atomic fact sentences, one per line, with no numbering or extra commentary.
"""

    client = genai.Client(api_key=api_key)

    # ---- 1) Build requests JSONL ----
    with open(batch_requests_path, "w", encoding="utf-8") as f:
        for i in [63]:
            idx = f"{i:02d}"
            narrative_path = input_dir_p / f"narrative_{idx}.txt"

            if not narrative_path.exists():
                print(f"[MISSING] {narrative_path}")
                continue

            report_text = narrative_path.read_text(encoding="utf-8")
            full_prompt = f"{prompt}\n\nReport:\n{report_text}"

            line = {
                "key": f"narrative_{idx}",
                "request": {
                    "contents": [
                        {"parts": [{"text": full_prompt}]}
                    ]
                },
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"Wrote batch requests to {batch_requests_path}")

    # ---- 2) Upload JSONL ----
    uploaded_file = client.files.upload(
        file=str(batch_requests_path),
        config=types.UploadFileConfig(
            display_name="atomic-facts",
            mime_type="jsonl",
        ),
    )
    print(f"Uploaded: {uploaded_file.name}")

    # ---- 3) Create batch job ----
    batch_job = client.batches.create(
        model=model,
        src=uploaded_file.name,
        config={"display_name": "atomic-facts"},
    )
    print(f"Batch job started: {batch_job.name}")

    # ---- 4) Poll until completion ----
    while True:
        job = client.batches.get(name=batch_job.name)
        state = job.state.name
        print(f"Batch state: {state}")

        if state == "JOB_STATE_SUCCEEDED":
            break

        if state in {"JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}:
            raise RuntimeError(f"Batch ended unsuccessfully: {state}")

        time.sleep(poll_seconds)

    # ---- 5) Download results JSONL ----
    result_file_name = job.dest.file_name
    result_bytes = client.files.download(file=result_file_name)
    result_text = result_bytes.decode("utf-8")

    batch_results_path.write_text(result_text, encoding="utf-8")
    print(f"Downloaded results to {batch_results_path}")

    # ---- 6) Results JSONL -> individual .txt files ----
    def _extract_text(obj: dict) -> str | None:
        if "error" in obj:
            return None
        resp = obj.get("response")
        if not resp:
            return None

        parts = resp["candidates"][0]["content"]["parts"]
        texts = [p.get("text", "") for p in parts if p.get("text")]
        return "".join(texts).strip() if texts else None

    written = 0
    with open(batch_results_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)

            key = obj.get("key", "")
            if not key.startswith("narrative_"):
                continue

            idx = key.split("_")[-1]  # "01"
            atomic_text = _extract_text(obj)

            if atomic_text is None:
                print(f"Error for {key}: {obj.get('error')}")
                continue

            out_path = output_dir_p / f"atomic_facts_{idx}.txt"
            out_path.write_text(atomic_text, encoding="utf-8")
            written += 1
            print(f"Wrote {out_path}")

    print(f"Done. Wrote {written} atomic facts files to {output_dir_p}")
