import whisperx
import gc
import torch
import json
import os

def run_whisperx_pipeline(audio_path, output_json_path):
    """
    Runs full WhisperX pipeline:
    1. Transcription
    2. Alignment
    3. Diarization
    4. Save result as JSON
    """
    HF_TOKEN = "PUT_YOUR_HF_TOKEN_HERE"   # <--- EDIT THIS LINE ONLY

    # Config
    device = "cuda" if torch.cuda.is_available() else "cpu"
    batch_size = 16
    compute_type = "float16" if device == "cuda" else "int8"
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # Load audio
    audio = whisperx.load_audio(audio_path)

    # Transcription
    model = whisperx.load_model("large-v3", device, compute_type=compute_type)
    result = model.transcribe(audio, batch_size=batch_size, language="en")

    # Cleanup
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # Alignment
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )

    result = whisperx.align(
        result["segments"], model_a, metadata, audio, device,
        return_char_alignments=False
    )

    # Cleanup
    del model_a
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # Diarization
    diarize_model = whisperx.diarize.DiarizationPipeline(
        use_auth_token=HF_TOKEN,   
        device=device
    )

    diarize_segments = diarize_model(audio_path)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    # Save output
    with open(output_json_path, "w") as f:
        json.dump(result["segments"], f, indent=2)

    print(f"✅ Done! Saved to {output_json_path}")
    return result["segments"]

