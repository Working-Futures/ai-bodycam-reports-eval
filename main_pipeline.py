# run_list.py
# Pipeline:
#   YouTube → audio_XX.mp3
#   audio → transcript_raw_XX.json
# run_list.py
# Pipeline:
#   YouTube → audio_XX.mp3
#   audio → transcript_raw_XX.json
#   transcript_raw → transcript_XX.json
#
# Skips any step whose output file already exists.

from pathlib import Path
import traceback

from youtube_to_mp3 import download_youtube_to_mp3
from asr import run_whisperx_pipeline
from json_cleaner import filter_diarized_json


YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=KJUUwBXhfXA",
    "https://www.youtube.com/watch?v=ZYsX7_0xigo",
    "https://www.youtube.com/watch?v=NeQSADZENfk",
    "https://www.youtube.com/watch?v=UWbiw3WI3E0",
    "https://www.youtube.com/watch?v=x8XKKbIyw1o",
    "https://www.youtube.com/watch?v=IjrMfSM6rTI",
    "https://www.youtube.com/watch?v=V0BRzTBNxmI",
    "https://www.youtube.com/watch?v=MUogvjeXSQE",
    "https://www.youtube.com/watch?v=AwNCWvf_2mA",
    "https://www.youtube.com/watch?v=N9n4NH7I7YQ",
    "https://www.youtube.com/watch?v=SM1kjC_VMJw",
    "https://www.youtube.com/watch?v=j-CBfZZAS5o",
    "https://www.youtube.com/watch?v=8r6JEUAsX6A",
    "https://www.youtube.com/watch?v=eqM1DX3AMpY",
    "https://www.youtube.com/watch?v=RDKE118SGnw",
    "https://www.youtube.com/watch?v=sKv9n-Rl3k4",
    "https://www.youtube.com/watch?v=8SHqKxjCfpg",
    "https://www.youtube.com/watch?v=oUgAbntDmDw",
    "https://www.youtube.com/watch?v=AeF0-3WQOPI",
    "https://www.youtube.com/watch?v=r6VQtoaANzs",
    "https://www.youtube.com/watch?v=EIMACktpR-w",
    "https://www.youtube.com/watch?v=01dnglPgjUk",
    "https://www.youtube.com/watch?v=KKuUgtcPtvE",
    "https://www.youtube.com/watch?v=kWFPGXIdXEg",
    "https://www.youtube.com/watch?v=k63GB347qm4",
    "https://www.youtube.com/watch?v=3D7q3L2CJYA",
    "https://www.youtube.com/watch?v=uwFot7ByX48",
    "https://www.youtube.com/watch?v=EI-OTchUTus",
    "https://www.youtube.com/watch?v=8VtnRR9fMVc",
    "https://www.youtube.com/watch?v=fPPQ-3wVZyQ",
    "https://www.youtube.com/watch?v=fGFqJc0j1lg",
    "https://www.youtube.com/watch?v=qPBXuEcqlU0",
    "https://www.youtube.com/watch?v=KFBNXXkefrc",
    "https://www.youtube.com/watch?v=bzBoX8WPPek",
    "https://www.youtube.com/watch?v=sqhPBFaV6GY",
    "https://www.youtube.com/watch?v=_3sJT2XPv78",
    "https://www.youtube.com/watch?v=AJXxMG91b-k",
    "https://www.youtube.com/watch?v=8U3khRIWqhs",
    "https://www.youtube.com/watch?v=TdxZ0P0nQBg",
    "https://www.youtube.com/watch?v=HhVX6hlk9IM",
    "https://www.youtube.com/watch?v=TRevFgHGKRA",
    "https://www.youtube.com/watch?v=-urIoCgX1rY",
    "https://www.youtube.com/watch?v=77JLAy-S_1A",
    "https://www.youtube.com/watch?v=yGKiF1qdkK8",
    "https://www.youtube.com/watch?v=w9kPVx-E8IM",
    "https://www.youtube.com/watch?v=5_1AwTBE8_g",
    "https://www.youtube.com/watch?v=JX3VzrBeyj8",
    "https://www.youtube.com/watch?v=PZQgYqDjfjE",
    "https://www.youtube.com/watch?v=X30swVLvzfQ",
    "https://www.youtube.com/watch?v=bERDnPOki4Y",
    "https://www.youtube.com/watch?v=FaN20cfda5A",
    "https://www.youtube.com/watch?v=d9QN2G1nPxc",
    "https://www.youtube.com/watch?v=Z8ax2NTAwLk",
    "https://www.youtube.com/watch?v=sgFPVSooheg",
    "https://www.youtube.com/watch?v=CcMtu1hyWA8",
    "https://www.youtube.com/watch?v=01UbNaIMahI",
    "https://www.youtube.com/watch?v=1gFLtmJ8F2o",
    "https://www.youtube.com/watch?v=HZLayGrWxQU",
    "https://www.youtube.com/watch?v=DrH8LPTZQjs",
    "https://www.youtube.com/watch?v=Xkt4liQKero",
    "https://www.youtube.com/watch?v=tXgfeR0JhEE",
    "https://www.youtube.com/watch?v=scY_cKiGeRU",
    "https://www.youtube.com/watch?v=mWEKbfSJAtg",
    "https://www.youtube.com/watch?v=zOHCYG0_e7g",
    "https://www.youtube.com/watch?v=IsZU-Ux5kL0",
    "https://www.youtube.com/watch?v=magguwIW7cU",
    "https://www.youtube.com/watch?v=gAWbMGs0e8E",
    "https://www.youtube.com/watch?v=5UUCkVMoefs",
    "https://www.youtube.com/watch?v=J-cGJtX1f0g",
    "https://www.youtube.com/watch?v=K0HAr0YIW8I",
    "https://www.youtube.com/watch?v=1le2rCWq8Xk",
    "https://www.youtube.com/watch?v=gmOggpZlEfs",
    "https://www.youtube.com/watch?v=nS01c0la7lE",
    "https://www.youtube.com/watch?v=Jpc_TogcTI4",
    "https://www.youtube.com/watch?v=21FKxuTlZ54",
    "https://www.youtube.com/watch?v=XhoY6q-ikUk",
    "https://www.youtube.com/watch?v=Df-q3UyjmL8",
    "https://www.youtube.com/watch?v=znDxCTIHGJs",
    "https://www.youtube.com/watch?v=bFNKeGyozzU",
    "https://www.youtube.com/watch?v=b0kBj9QKIgk",
    "https://www.youtube.com/watch?v=xVCX9B9hKgw",
    "https://www.youtube.com/watch?v=t0gucNknscc",
    "https://www.youtube.com/watch?v=2Z_yHeYnNrc",
    "https://www.youtube.com/watch?v=9XQYLmkMD7I",
    "https://www.youtube.com/watch?v=0QLew2J9NKw",
    "https://www.youtube.com/watch?v=41BozYLLiyo",
    "https://www.youtube.com/watch?v=xKHoWTvEtok",
    "https://www.youtube.com/watch?v=IF4xs1dBZoA",
    "https://www.youtube.com/watch?v=YWaF4HlCmp0",
    "https://www.youtube.com/watch?v=mPyWXRgIdRc",
    "https://www.youtube.com/watch?v=KDsaHpKua1o",
    "https://www.youtube.com/watch?v=MfEKINUpzrE",
    "https://www.youtube.com/watch?v=5RijxbPII74",
    "https://www.youtube.com/watch?v=ugyNT-oLaf4",
    "https://www.youtube.com/watch?v=iCd4F9NiAU0",
    "https://www.youtube.com/watch?v=Y6GnuxE77Lk",
    "https://www.youtube.com/watch?v=JaG7l1QvNK0",
    "https://www.youtube.com/watch?v=3TD5XR6Mu1E",
    "https://www.youtube.com/watch?v=CMmLpjtGD7g",
    "https://www.youtube.com/watch?v=AyrgpwIfMSw",
    "https://www.youtube.com/watch?v=13c95MfyK3c",
    "https://www.youtube.com/watch?v=UEeHpDziQV8",
    "https://www.youtube.com/watch?v=zQ-dWrHUc0E",
    "https://www.youtube.com/watch?v=TDQuJhIT5mk",
    "https://www.youtube.com/watch?v=BwWRK0MdxLo",
    "https://www.youtube.com/watch?v=zDJgG6hcs7c",
    "https://www.youtube.com/watch?v=Qrqo8br6Em0",
    "https://www.youtube.com/watch?v=apq5DQis2MQ",
    "https://www.youtube.com/watch?v=YMZ9s8ELsRI",
    "https://www.youtube.com/watch?v=mr4nO3_2Bm4",
    "https://www.youtube.com/watch?v=VZIoqEWYPIo",
    "https://www.youtube.com/watch?v=SQlvlbNh-lE",
]


def run(urls, out_dir="outputs"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    errors_log = out / "errors.log"

    for i, url in enumerate(urls, start=1):
        idx = f"{i:02d}"

        audio = out / f"audio_{idx}.mp3"
        raw = out / f"transcript_raw_{idx}.json"
        clean = out / f"transcript_{idx}.json"

        print(f"\n[{idx}] Processing")

        try:
            # Step 1: Download audio
            if not audio.exists():
                download_youtube_to_mp3(url, str(audio))
            else:
                print(f"[{idx}] audio exists → skipping download")

            # Step 2: WhisperX
            if not raw.exists():
                run_whisperx_pipeline(str(audio), str(raw))
            else:
                print(f"[{idx}] raw transcript exists → skipping ASR")

            # Step 3: Clean transcript
            if not clean.exists():
                filter_diarized_json(str(raw), str(clean))
            else:
                print(f"[{idx}] cleaned transcript exists → skipping cleaning")

            print(f"[{idx}] Done")

        except Exception:
            with errors_log.open("a") as f:
                f.write(f"\n\n--- ERROR {idx} ---\nURL: {url}\n{traceback.format_exc()}")
            print(f"[{idx}] Error (logged)")


if __name__ == "__main__":
    run(YOUTUBE_URLS)

