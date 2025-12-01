import subprocess
import os
import uuid

def download_youtube_to_mp3(youtube_url, output_mp3_path):
    """
    Downloads a YouTube video as MP4 and converts it to MP3.
    """
    COOKIES_FILE = "/home/jupyter/cookies.txt"   # <-- EDIT THIS PATH IF NEEDED

    temp_mp4 = f"temp_{uuid.uuid4().hex}.mp4"

    yt_dlp_cmd = [
        "yt-dlp",
        "--cookies", COOKIES_FILE,      # <<--- COOKIES HARDCODED HERE
        "-f", 'bv*[vcodec^=avc1][ext=mp4]+ba[acodec^=mp4a][ext=m4a]/bv*[vcodec^=avc1]+ba/b[ext=mp4]',
        youtube_url,
        "--extractor-args", "youtube:player_js_version=actual",
        "-o", temp_mp4,
    ]

    subprocess.run(yt_dlp_cmd, check=True)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", temp_mp4,
        "-vn",
        "-acodec", "mp3",
        output_mp3_path,
    ]
    subprocess.run(ffmpeg_cmd, check=True)

    if os.path.exists(temp_mp4):
        os.remove(temp_mp4)

    print(f"✅ Saved MP3 to: {output_mp3_path}")
