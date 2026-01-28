from youtube_to_mp3 import download_youtube_to_mp3
from asr import run_whisperx_pipeline
from json_cleaner import filter_diarized_json
from prompt import generative_narrative
download_youtube_to_mp3(
    youtube_url="https://www.youtube.com/watch?v=k63GB347qm4",
    output_mp3_path="output_audio.mp3"
)
run_whisperx_pipeline("output_audio.mp3", "output_json_path.json")
filter_diarized_json("output_json_path.json", "output_json_cleaned.json"


