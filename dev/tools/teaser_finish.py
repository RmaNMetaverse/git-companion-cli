"""Mux the finished picture and original AAC score; verify the uploadable MP4."""

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ffmpeg = os.environ.get("TEASER_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Set TEASER_FFMPEG to a local FFmpeg executable.")
    ffprobe = os.environ.get("TEASER_FFPROBE") or shutil.which("ffprobe")
    if not ffprobe:
        ffprobe = str(Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe"))
    work = ROOT / "dev/artifacts/teaser"
    output = ROOT / "dev/media/git-companion-teaser.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(work / "silent-teaser.mp4"),
            "-i",
            str(work / "audio-carrier.mp4"),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c",
            "copy",
            "-t",
            "44",
            "-movflags",
            "+faststart",
            "-metadata",
            "title=Git Companion — A little less friction",
            "-metadata",
            "comment=Original motion graphics and soundtrack. Real app demo captures.",
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
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    assert video["codec_name"] == "h264" and audio["codec_name"] == "aac"
    assert (video["width"], video["height"]) == (1920, 1080)
    assert video["r_frame_rate"] == "30/1" and int(video["nb_frames"]) == 1320
    assert abs(float(info["format"]["duration"]) - 44) < 0.1
    assert int(info["format"]["size"]) < 10_000_000
    info["soundtrack"] = "Original instrumental composition; no third-party music."
    (ROOT / "dev/media/teaser-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info, indent=2))
    print(f"Verified: {output}")


if __name__ == "__main__":
    main()
