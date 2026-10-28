"""Re-render the same action teaser over 60 seconds with longer shot holds.

Every frame is evaluated on the slower timeline, retaining smooth 30 fps camera
motion. Sound events move with the edit but keep their original pitch/duration.
The 44-second and 46-second editions are never overwritten.
"""

import json
import os
import re
import shutil
import subprocess

from PIL import Image, ImageSequence

from . import teaser_action_render as action
from .teaser_action_finish import main as finish

WORK = action.ROOT / "dev/artifacts/teaser-action-60s"
SCALE = 60 / action.DURATION
OUT = action.OUT


def prepare():
    WORK.mkdir(parents=True, exist_ok=True)
    source = (OUT / "teaser-action-captions.vtt").read_text(encoding="utf-8")

    def timestamp(match):
        minutes, seconds, millis = map(int, match.groups())
        total = round(((minutes * 60 + seconds) * 1000 + millis) * SCALE)
        seconds, millis = divmod(total, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    captions = re.sub(r"(\d{2}):(\d{2})\.(\d{3})", timestamp, source)
    assert "00:01:00.000" in captions
    (OUT / "teaser-action-60s-captions.vtt").write_text(captions, encoding="utf-8")
    shutil.copyfile(OUT / "teaser-action-poster.jpg", OUT / "teaser-action-60s-poster.jpg")
    frames, durations = [], []
    with Image.open(OUT / "teaser-action-preview.gif") as preview:
        for frame in ImageSequence.Iterator(preview):
            frames.append(frame.copy())
            durations.append(round(frame.info.get("duration", 100) * SCALE / 10) * 10)
    frames[0].save(
        OUT / "teaser-action-60s-preview.gif",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    (WORK / "edit-decision-list.json").write_text(
        json.dumps(
            {
                "duration": 60,
                "fps": 30,
                "time_scale": SCALE,
                "shots": [
                    {"in": a * SCALE, "out": b * SCALE, "scene": kind, "title": title}
                    for a, b, kind, title in action.SHOTS
                ],
                "change": "Same visuals and 21 shots; every shot lasts 30.43% longer. SFX resynchronized without stretching.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main():
    prepare()
    action.WORK = WORK
    action.render(time_scale=SCALE)
    blender = os.environ.get("TEASER_BLENDER") or shutil.which("blender")
    if not blender:
        raise RuntimeError("Set TEASER_BLENDER to Blender for the original sound-effects AAC encoding.")
    with (WORK / "audio-export.log").open("w") as log:
        subprocess.run(
            [
                blender,
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "--python",
                str(action.ROOT / "dev/tools/teaser_audio.py"),
                "--",
                str(WORK / "action-sfx.wav"),
                str(WORK / "sfx-carrier.mp4"),
                "60",
            ],
            check=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    finish(
        work=WORK,
        output=OUT / "git-companion-action-teaser-60s.mp4",
        duration=60,
        info_name="teaser-action-60s-info.json",
        exact_duration=True,
    )


if __name__ == "__main__":
    main()
