import json
import time
from pathlib import Path
from google import genai
from google.genai import types


def batch_generate_narratives(
    api_key: str,
    input_dir: str = "outputs",
    output_dir: str = "narratives",
    total_transcripts: int = 112,
    model: str = "models/gemini-3-pro-preview",
    batch_requests_jsonl: str = "batch_requests.jsonl",
    batch_results_jsonl: str = "batch_results.jsonl",
    poll_seconds: int = 20,
) -> None:
    """
    End-to-end batch pipeline in ONE function:

    1) Builds batch_requests.jsonl from:
         outputs/transcript_raw_01.json ... outputs/transcript_raw_112.json
    2) Uploads JSONL
    3) Creates batch job
    4) Polls until completion
    5) Downloads results JSONL
    6) Writes one output per transcript:
         narratives/narrative_01.txt ... narratives/narrative_112.txt
    """

    input_dir_p = Path(input_dir)
    output_dir_p = Path(output_dir)
    output_dir_p.mkdir(parents=True, exist_ok=True)

    batch_requests_path = Path(batch_requests_jsonl)
    batch_results_path = Path(batch_results_jsonl)

    instruction = (
        'Using the provided body-worn camera audio transcript, write the “Narrative” section of a police report from my perspective. Begin with “Narrative:” and write 1–4 paragraphs in first-person past tense. The narrative must follow a chronological sequence of events of the incident at hand. Clearly and accurately identify and describe all key individuals involved (e.g., suspect, victim, witnesses, and officer) and describe what each party did, in sequence. Explain how and why the incident occurred to the extent supported by the audio. The narrative must accurately document whether Miranda or other legal warnings were provided if present in the transcript, whether the individual complied, resisted, or fled, any searches or investigative actions taken, any use of force, how evidence was collected or stored, and whether the basis for probable cause, citation, or arrest was stated if this information is present in the transcript. If this information is not present in the transcript, do not include it in the output report, and do not note that it was not included in the transcript. Use only information explicitly present in the audio transcript. If any required detail is missing, unclear, or not audible, insert an inline placeholder in the form [INSERT: specific missing detail]. The output must be a single, continuous narrative with no bullet points, headings, analysis, or refusal language. Do not include details that do not pertain to the incident which the police report is being written about.'
    )

    # ---- Client ----
    client = genai.Client(api_key=api_key)

    # ---- 1) Build requests JSONL ----
    with open(batch_requests_path, "w", encoding="utf-8") as f:
        for i in range(1, total_transcripts + 1):
            idx = f"{i:02d}"
            transcript_path = input_dir_p / f"transcript_raw_{idx}.json"

            if not transcript_path.exists():
                print(f"[MISSING] {transcript_path}")
                continue

            with open(transcript_path, "r", encoding="utf-8") as t:
                transcript_raw = t.read()

            prompt = f"{instruction}\n\nTranscript (JSON):\n{transcript_raw}"

            line = {
                "key": f"transcript_raw_{idx}",
                "request": {
                    "contents": [
                        {"parts": [{"text": prompt}]}
                    ]
                },
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"Wrote batch requests to {batch_requests_path}")

    # ---- 2) Upload JSONL ----
    uploaded_file = client.files.upload(
        file=str(batch_requests_path),
        config=types.UploadFileConfig(
            display_name="police-narratives",
            mime_type="jsonl",
        ),
    )
    print(f"Uploaded: {uploaded_file.name}")

    # ---- 3) Create batch job ----
    batch_job = client.batches.create(
        model=model,
        src=uploaded_file.name,
        config={"display_name": "police-narratives"},
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

        # Most common shape:
        # response.candidates[0].content.parts[0].text
        parts = resp["candidates"][0]["content"]["parts"]

        # Sometimes the model returns multiple parts; join them.
        texts = [p.get("text", "") for p in parts if p.get("text")]
        return "".join(texts).strip() if texts else None

    written = 0
    with open(batch_results_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)

            key = obj.get("key", "")
            if not key.startswith("transcript_raw_"):
                continue

            idx = key.split("_")[-1]  # "01"
            narrative = _extract_text(obj)

            if narrative is None:
                print(f"Error for {key}: {obj.get('error')}")
                continue

            out_path = output_dir_p / f"narrative_{idx}.txt"
            out_path.write_text(narrative, encoding="utf-8")
            written += 1
            print(f"Wrote {out_path}")

    print(f"Done. Wrote {written} narrative files to {output_dir_p}")
