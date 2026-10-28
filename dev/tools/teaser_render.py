"""Render the 44-second teaser: original motion design, real UI, original music.

Developer-only dependencies: Pillow and NumPy. Set TEASER_FFMPEG to a local
FFmpeg with H.264 support. The renderer never changes app code or a user repo.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "dev/artifacts/teaser"
SCREENS = WORK / "screens"
OUT = ROOT / "dev/media"
W, H, FPS, DURATION = 1920, 1080, 30, 44
WHITE = (241, 245, 255)
MUTED = (151, 163, 184)
MINT = (100, 232, 203)
LAV = (175, 168, 255)
AMBER = (255, 203, 139)
SCENES = [(0, 5), (5, 10), (10, 17), (17, 23), (23, 29), (29, 36), (36, 40), (40, 44)]
CHAPTERS = [
    "A LITTLE LESS FRICTION",
    "MEET YOUR COMPANION",
    "FIND YOUR NEXT STEP",
    "HELP, WHEN YOU WANT IT",
    "GIT + GIT LFS",
    "REAL RESULTS",
    "ONE-TIME SETUP",
    "START YOUR NEXT IDEA",
]


@lru_cache(maxsize=48)
def font(size, bold=False, mono=False):
    options = (
        ["C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"]
        if mono
        else ["C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"]
    )
    options += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in options:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    raise RuntimeError("Set up a local sans-serif font for rendering.")


def text(layer, value, x, y, size=32, color=WHITE, bold=False, mono=False, center=False):
    draw = ImageDraw.Draw(layer)
    f = font(size, bold, mono)
    if center:
        x -= draw.textlength(value, font=f) / 2
    draw.text((round(x), round(y)), value, font=f, fill=color, anchor="lt")


def clamp(value):
    return max(0.0, min(1.0, value))


def ease(value):
    value = clamp(value)
    return 1 - (1 - value) ** 3


def pill(layer, value, x, y, color=MINT, size=23, pad=22):
    draw = ImageDraw.Draw(layer)
    width = int(draw.textlength(value, font=font(size, True))) + 2 * pad
    draw.rounded_rectangle(
        (x, y, x + width, y + 54), radius=27, fill=(*color, 18), outline=(*color, 80), width=1
    )
    text(layer, value, x + pad, y + 13, size, color, True)
    return width


def branch(layer, x, y, size, progress=1, color=MINT):
    draw = ImageDraw.Draw(layer)
    pts = [(x, y + size), (x, y), (x + size, y), (x + size * 0.36, y + size)]
    paths = [(pts[0], pts[1]), (pts[1], pts[2]), (pts[2], pts[3]), (pts[3], pts[0])]
    for index, (a, b) in enumerate(paths):
        p = clamp(progress * 4 - index)
        if p:
            end = (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p)
            draw.line([a, end], fill=(*color, 205), width=max(3, int(size / 45)))
    for index, (px, py) in enumerate(pts):
        p = ease(progress * 4 - max(0, index - 1))
        radius = size * 0.043 * p
        if radius:
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)


@lru_cache(maxsize=1)
def background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xx /= W
    yy /= H
    purple = np.exp(-(((xx - 0.79) / 0.45) ** 2 + ((yy - 0.12) / 0.7) ** 2) * 2)
    green = np.exp(-(((xx - 0.14) / 0.45) ** 2 + ((yy - 0.92) / 0.5) ** 2) * 2)
    array = np.zeros((H, W, 3), dtype=np.float32) + [8, 12, 21]
    array += purple[..., None] * [19, 12, 38]
    array += green[..., None] * [0, 23, 21]
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8)).convert("RGBA")


def atmosphere(image, t):
    draw = ImageDraw.Draw(image)
    for i in range(42):
        x = (i * 311.7 + 80) % W
        y = (i * 157.3 - t * (2 + i % 3)) % H
        r = 1 if i % 5 else 2
        v = int(32 + 12 * math.sin(t * 0.35 + i))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(v, v + 10, v + 17))
    for y in range(220, 960, 160):
        draw.line((96, y, W - 96, y), fill=(23, 29, 43), width=1)


@lru_cache(maxsize=64)
def screen(name, width, height, focus=None):
    image = Image.open(SCREENS / f"{name}.png").convert("RGBA")
    if focus:
        image = image.crop(
            tuple(
                int(value * (image.width if index % 2 == 0 else image.height))
                for index, value in enumerate(focus)
            )
        )
    image = ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=18, fill=255)
    image.putalpha(mask)
    shadow = Image.new("RGBA", (image.width + 64, image.height + 64))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (28, 28, image.width + 36, image.height + 36), radius=24, fill=(0, 0, 0, 180)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    shadow.alpha_composite(image, (32, 24))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (32, 24, image.width + 31, image.height + 23), radius=18, outline=(89, 108, 139, 130), width=2
    )
    return shadow


def show_screen(layer, name, x, y, width, height, u, focus=None):
    image = screen(name, width, height, focus)
    layer.alpha_composite(image, (round(x + 64 * (1 - ease(u / 0.65))), round(y + 5 * math.sin(u * 0.8))))


def file_card(layer, ext, label, x, y, color, t):
    draw = ImageDraw.Draw(layer)
    y += 9 * math.sin(t * 0.7 + x)
    draw.rounded_rectangle(
        (x, y, x + 420, y + 240), radius=26, fill=(19, 27, 42, 250), outline=(*color, 110), width=2
    )
    draw.rounded_rectangle(
        (x + 28, y + 28, x + 90, y + 100), radius=10, fill=(*color, 20), outline=(*color, 150), width=2
    )
    draw.line((x + 45, y + 52, x + 73, y + 52), fill=color, width=3)
    draw.line((x + 45, y + 67, x + 73, y + 67), fill=color, width=3)
    text(layer, ext, x + 118, y + 40, 43, color, True, True)
    text(layer, label, x + 30, y + 150, 27, WHITE)


def scene_content(index, u):
    layer = Image.new("RGBA", (W, H))
    shift = 38 * (1 - ease(u / 0.75))
    if index == 0:
        text(layer, "Make room", 130, 270 + shift, 118, WHITE, True)
        text(layer, "for your next", 130, 410 + shift, 118, WHITE, True)
        text(layer, "big idea.", 130, 550 + shift, 118, MINT, True)
        text(layer, "A little less friction. A little more flow.", 138, 735 + shift, 32, MUTED)
        branch(layer, 1240, 355, 360, ease(u / 2.2))
        for label, x, y, color in [
            (".psd", 1150, 750, MINT),
            (".blend", 1520, 255, LAV),
            (".mp4", 1550, 735, AMBER),
        ]:
            pill(layer, label, x, y + 9 * math.sin(u + x), color, 25)
    elif index == 1:
        text(layer, "Meet your", 110, 285 + shift, 87, WHITE, True)
        text(layer, "Git Companion.", 110, 390 + shift, 87, MINT, True)
        text(layer, "Git + Git LFS.", 116, 545 + shift, 37, WHITE)
        text(layer, "One calm place to create.", 116, 600 + shift, 32, MUTED)
        pill(layer, "74 helpful actions", 116, 730, LAV)
        show_screen(layer, "home", 790, 155, 1000, 735, u)
    elif index == 2:
        text(layer, "Less memorizing.", 110, 270 + shift, 79, WHITE, True)
        text(layer, "More making.", 110, 370 + shift, 79, MINT, True)
        text(layer, "Search by task or command.", 117, 520 + shift, 30, MUTED)
        text(layer, "Autocomplete the next step.", 117, 567 + shift, 30, MUTED)
        pill(layer, "Type  /  Complete  /  Review", 116, 700, LAV, 21)
        shot = f"search-{min(6, max(0, int((u - 0.5) / 0.36))):02d}" if u < 3.8 else "completed"
        show_screen(layer, shot, 800, 280, 1020, 650, u, (0.245, 0.29, 0.99, 0.82))
    elif index == 3:
        text(layer, "A little help.", 110, 265 + shift, 83, MINT, True)
        text(layer, "Only when", 110, 370 + shift, 83, WHITE, True)
        text(layer, "you need it.", 110, 472 + shift, 83, WHITE, True)
        text(layer, "Short hints. Expandable examples.", 116, 630 + shift, 28, MUTED)
        pill(layer, "For artists. For curious people.", 116, 735, LAV, 21)
        show_screen(layer, "examples-full", 790, 260, 1040, 680, u, (0.185, 0.235, 0.815, 0.775))
    elif index == 4:
        text(layer, "Big files.", W / 2, 245 + shift, 100, WHITE, True, center=True)
        text(layer, "Still in flow.", W / 2, 365 + shift, 100, MINT, True, center=True)
        for i, (ext, label, color) in enumerate(
            [
                (".psd", "Layered artwork", MINT),
                (".blend", "Scenes & textures", LAV),
                (".mp4", "Motion & media", AMBER),
            ]
        ):
            entrance = 50 * (1 - ease((u - i * 0.16) / 0.8))
            file_card(layer, ext, label, 250 + i * 500, 555 + entrance, color, u)
        text(layer, "Track  /  Transfer  /  Preview cleanup", W / 2, 875, 30, MUTED, center=True)
    elif index == 5:
        text(layer, "Run it.", 110, 265 + shift, 95, MINT, True)
        text(layer, "See what", 110, 382 + shift, 89, WHITE, True)
        text(layer, "happened.", 110, 487 + shift, 89, WHITE, True)
        text(layer, "Live output. Clear outcomes.", 117, 640 + shift, 31, MUTED)
        pill(layer, "Success never feels silent.", 116, 740, MINT, 22)
        name = "prune" if u < 2.3 else "results"
        show_screen(layer, name, 790, 175, 1030, 755, u, (0.02, 0.06, 0.98, 0.93))
    elif index == 6:
        text(layer, "Set up once.", W / 2, 230 + shift, 99, WHITE, True, center=True)
        text(layer, "Create anywhere.", W / 2, 350 + shift, 99, MINT, True, center=True)
        x = 510
        for label, color in [("Windows", MINT), ("macOS", LAV), ("Linux", AMBER)]:
            width = pill(layer, label, x, 520, color, 28, 40)
            x += width + 50
        draw = ImageDraw.Draw(layer)
        draw.rounded_rectangle(
            (420, 650, 1500, 785), radius=22, fill=(12, 20, 31), outline=(66, 88, 111), width=2
        )
        command = "$ git-companion"
        count = min(len(command), int(max(0, u - 0.45) * 14))
        text(layer, command[:count], 520, 692, 48, MINT, mono=True)
        if int(u * 2) % 2 == 0:
            cursor_x = 520 + ImageDraw.Draw(layer).textlength(command[:count], font=font(48, mono=True))
            draw.rectangle((cursor_x + 5, 685, cursor_x + 28, 742), fill=MINT)
        text(
            layer,
            "Setup handles Python. Reopen your terminal. You're ready.",
            W / 2,
            855,
            29,
            MUTED,
            center=True,
        )
    else:
        branch(layer, 890, 185, 140, ease(u / 0.8))
        text(layer, "GIT COMPANION", W / 2, 405 + shift, 99, WHITE, True, center=True)
        text(layer, "Your work. Your history. In good company.", W / 2, 545 + shift, 37, MINT, center=True)
        pill(layer, "$ git-companion", 805, 675, LAV, 28)
        text(
            layer, "github.com/RmaNMetaverse/git-companion-cli", W / 2, 835, 27, WHITE, mono=True, center=True
        )
        text(layer, "Windows  /  macOS  /  Linux", W / 2, 905, 26, MUTED, center=True)
    return layer


def frame(t):
    image = background().copy()
    atmosphere(image, t)
    index = next((i for i, (start, end) in enumerate(SCENES) if start <= t < end), len(SCENES) - 1)
    start, end = SCENES[index]
    u = t - start
    layer = scene_content(index, u)
    fade = ease(u / 0.45) * ease((end - t) / 0.4)
    if fade < 0.999:
        layer.putalpha(layer.getchannel("A").point(lambda value: round(value * fade)))
    image.alpha_composite(layer)
    draw = ImageDraw.Draw(image)
    branch(image, 102, 78, 29, 1)
    text(image, "git companion", 158, 71, 29, WHITE, True)
    text(image, f"{index + 1:02d} / {CHAPTERS[index]}", 1270, 80, 19, MUTED, mono=True)
    draw.line((100, 1008, 1820, 1008), fill=(43, 52, 69), width=2)
    draw.line((100, 1008, 100 + 1720 * clamp(t / DURATION), 1008), fill=MINT, width=3)
    text(image, "GIT + GIT LFS", 100, 1030, 17, MUTED, mono=True)
    text(image, "MADE FOR YOUR NEXT IDEA", 1510, 1030, 17, MUTED, mono=True)
    return image.convert("RGB")


def score():
    sr = 48000
    music = np.zeros((DURATION * sr, 2), np.float32)
    chords = [(57, 60, 64, 71), (53, 57, 60, 67), (48, 55, 60, 64), (55, 59, 62, 69)]
    for section in range(8):
        start = int(section * 5.5 * sr)
        length = min(int(6.3 * sr), len(music) - start)
        tt = np.arange(length, dtype=np.float32) / sr
        envelope = np.minimum(tt / 0.8, 1) * np.minimum((length / sr - tt) / 1.4, 1)
        for j, midi in enumerate(chords[section % 4]):
            hz = 440 * 2 ** ((midi - 69) / 12)
            tone = (
                (np.sin(2 * np.pi * hz * tt) + 0.18 * np.sin(2 * np.pi * hz * 2.003 * tt)) * envelope * 0.028
            )
            music[start : start + length, 0] += tone * (0.82 if j % 2 else 1)
            music[start : start + length, 1] += tone * (1 if j % 2 else 0.82)
    rng = np.random.default_rng(1902)
    beat = 60 / 108
    for b in np.arange(0, DURATION, beat):
        start = int(b * sr)
        n = min(int(0.22 * sr), len(music) - start)
        tt = np.arange(n, dtype=np.float32) / sr
        kick = np.sin(2 * np.pi * (46 * tt + 3.2 * (1 - np.exp(-tt * 30)))) * np.exp(-tt * 24) * 0.105
        music[start : start + n] += kick[:, None]
        n = min(int(0.055 * sr), len(music) - start)
        tt = np.arange(n) / sr
        noise = rng.uniform(-1, 1, n) * np.exp(-tt * 110) * 0.014
        music[start : start + n] += noise[:, None]
    for event in [5, 10, 17, 23, 29, 36, 40]:
        start = int(event * sr)
        tt = np.arange(int(0.4 * sr)) / sr
        chime = np.sin(2 * np.pi * 880 * tt) * np.exp(-tt * 13) * 0.045
        music[start : start + len(tt)] += chime[:, None]
    times = np.arange(len(music)) / sr
    music *= (np.minimum(times / 1.5, 1) * np.minimum((DURATION - times) / 2, 1))[:, None]
    # Master the original score to a comfortable level while leaving headroom for AAC.
    music *= 0.60 / max(1e-8, float(np.max(np.abs(music))))
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / "original-score.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sr)
        output.writeframes((music * 32767).astype("<i2").tobytes())
    return path


def stills():
    WORK.mkdir(parents=True, exist_ok=True)
    tiles = []
    for t in (2.8, 7.6, 13.3, 19.8, 25.8, 32.8, 38.2, 42):
        image = frame(t)
        image.save(WORK / f"frame-{t:04.1f}.jpg", quality=93)
        tile = image.resize((640, 360), Image.Resampling.LANCZOS)
        tiles.append(tile)
    sheet = Image.new("RGB", (1280, 1440))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % 2) * 640, (i // 2) * 360))
    sheet.save(WORK / "storyboard.jpg", quality=93)
    OUT.mkdir(parents=True, exist_ok=True)
    frame(42).save(OUT / "teaser-poster.jpg", quality=94)
    print(WORK / "storyboard.jpg", flush=True)


def render():
    ffmpeg = os.environ.get("TEASER_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Set TEASER_FFMPEG to the installed encoder.")
    encoder = os.environ.get("TEASER_ENCODER", "libx264")
    parameters = (
        ["-preset", "medium", "-crf", "22"]
        if encoder == "libx264"
        else ["-b:v", "1500k", "-maxrate", "1800k", "-bufsize", "3000k", "-look_ahead", "0"]
    )
    video = WORK / "silent-teaser.mp4"
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        encoder,
        *parameters,
        "-pix_fmt",
        "nv12" if encoder == "h264_qsv" else "yuv420p",
        "-movflags",
        "+faststart",
        str(video),
    ]
    with (WORK / "encoder.log").open("w") as log:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
        try:
            for i in range(DURATION * FPS):
                process.stdin.write(frame(i / FPS).tobytes())
                if i % (FPS * 4) == 0:
                    print(f"Rendered {i // FPS:02d}/{DURATION} seconds", flush=True)
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError((WORK / "encoder.log").read_text())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    score()
    print(f"Video rendered: {video}", flush=True)


def preview_gif():
    # A short, silent montage for GitHub's Markdown image renderer.
    moments = [(1.5, 3.5), (11.2, 13.2), (31.5, 33.5), (41.0, 43.0)]
    images = []
    for start, end in moments:
        for time in np.arange(start, end, 0.1):
            image = frame(float(time)).resize((800, 450), Image.Resampling.LANCZOS)
            images.append(
                image.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            )
    path = OUT / "teaser-preview.gif"
    images[0].save(path, save_all=True, append_images=images[1:], duration=100, loop=0, optimize=True)
    print(f"README preview: {path} ({path.stat().st_size / 1e6:.2f} MB)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stills", action="store_true")
    parser.add_argument("--gif", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    if args.stills:
        stills()
    elif args.gif:
        preview_gif()
    else:
        render()
    (WORK / "storyboard.json").write_text(
        json.dumps(
            {
                "duration": DURATION,
                "fps": FPS,
                "resolution": [W, H],
                "scenes": [{"start": a, "end": b, "title": CHAPTERS[i]} for i, (a, b) in enumerate(SCENES)],
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
