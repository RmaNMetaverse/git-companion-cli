"""Mux and validate the second teaser without touching the first one."""

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "dev/artifacts/teaser-action"
OUT = ROOT / "dev/media"


def main(work=WORK, output=None, duration=46, info_name="teaser-action-info.json", exact_duration=False):
    ffmpeg = os.environ.get("TEASER_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Set TEASER_FFMPEG to your encoder.")
    ffprobe = os.environ.get("TEASER_FFPROBE") or str(
        Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    )
    output = output or OUT / "git-companion-action-teaser.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(work / "silent-action.mp4"),
            # Omit only the silent audio tail so AAC packet padding cannot extend
            # the container past the last video frame on exact-duration exports.
            *(["-t", str(duration - 0.05)] if exact_duration else []),
            "-i",
            str(work / "sfx-carrier.mp4"),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c",
            "copy",
            "-t",
            str(duration),
            "-movflags",
            "+faststart",
            "-metadata",
            "title=Git Companion — Find it. Learn it. Run it.",
            "-metadata",
            "comment=Original motion graphics; actual Textual UI; original sound effects only. No music.",
            str(output),
        ],
        check=True,
    )
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,profile,width,height,r_frame_rate,nb_frames,sample_rate,channels",
            "-of",
            "json",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(result.stdout)
    video = next(x for x in info["streams"] if x["codec_type"] == "video")
    audio = next(x for x in info["streams"] if x["codec_type"] == "audio")
    assert video["codec_name"] == "h264" and audio["codec_name"] == "aac"
    assert (video["width"], video["height"]) == (1920, 1080)
    assert video["r_frame_rate"] == "30/1" and int(video["nb_frames"]) == duration * 30
    assert abs(float(info["format"]["duration"]) - duration) < 0.1
    if exact_duration:
        assert abs(float(info["format"]["duration"]) - duration) < 0.001
    assert int(info["format"]["size"]) < 10_000_000
    info["audio_design"] = (
        "Original event-synchronized sound effects only. No music, voice or third-party assets."
    )
    info["picture_method"] = (
        "Pillow/NumPy frame rendering with perspective-projected authentic Textual captures."
    )
    info["edit"] = "21 primary shots, whip transitions, camera orbits, dolly moves and macro inserts."
    (OUT / info_name).write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info, indent=2), flush=True)


if __name__ == "__main__":
    main()
