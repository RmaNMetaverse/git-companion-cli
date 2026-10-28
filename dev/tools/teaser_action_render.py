"""Second teaser: a deterministic 3D camera edit with original, event-only SFX.

Pillow composites and projectively maps real Textual captures. NumPy generates
the perspective matrices and transient audio. No browser or screen recording.
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
from PIL import Image, ImageDraw, ImageOps

from .teaser_render import branch, clamp, ease, font, text

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "dev/artifacts/teaser-action"
SCREENS = WORK / "screens"
OUT = ROOT / "dev/media"
W, H, FPS, DURATION = 1920, 1080, 30, 46
WHITE, DIM, LIME, CYAN, VIOLET = (
    (244, 248, 246),
    (148, 162, 174),
    (194, 255, 91),
    (92, 231, 218),
    (181, 159, 255),
)
# Deliberate hard cuts, macro inserts and match cuts; reading shots get longer holds.
SHOTS = [
    (0, 1.1, "git", "GIT"),
    (1.1, 2.2, "lfs", "GIT LFS"),
    (2.2, 4.2, "hero", "ONE COMPANION"),
    (4.2, 6.8, "map", "FOLLOW YOUR WORKFLOW"),
    (6.8, 8.6, "changes", "SAVE YOUR WORK"),
    (8.6, 10.4, "branches", "TRY IDEAS"),
    (10.4, 12.2, "lfs-category", "LARGE FILES"),
    (12.2, 14, "cleanup", "RECLAIM SPACE"),
    (14, 17, "library", "LEARN THE MAP"),
    (17, 19.4, "search", "SEARCH EVERY WORKFLOW"),
    (19.4, 21.7, "typing", "AUTOCOMPLETE"),
    (21.7, 23.2, "complete", "TAB. COMPLETED."),
    (23.2, 25.5, "review", "REVIEW THE REAL COMMAND"),
    (25.5, 28.1, "execute", "RUN IT. SEE IT."),
    (28.1, 30.3, "prune", "PREVIEW YOUR CLEANUP"),
    (30.3, 32.3, "hint", "A HINT AT EVERY STEP"),
    (32.3, 35.5, "examples", "OPEN AN EXAMPLE"),
    (35.5, 38, "learn", "BUILD YOUR GIT CONFIDENCE"),
    (38, 40, "montage", "FIND YOUR NEXT MOVE"),
    (40, 42.3, "setup", "SET UP ONCE"),
    (42.3, 46, "end", "GIT COMPANION"),
]
GROUPS = [
    ("01", "For you", "Your next steps"),
    ("02", "Look around", "status / log / diff"),
    ("03", "Save your work", "add / commit / stash"),
    ("04", "Try ideas", "switch / merge / rebase"),
    ("05", "Share & sync", "fetch / pull / push"),
    ("06", "Large files", "lfs track / fetch / status"),
    ("07", "Reclaim space", "lfs prune / clean"),
    ("08", "Recover", "reflog / restore / revert"),
    ("09", "Set up", "init / clone / config"),
]


def mix(a, b, p):
    return a + (b - a) * p


def tag(layer, label, x, y, color=LIME, size=21):
    draw = ImageDraw.Draw(layer)
    width = draw.textlength(label, font=font(size, True, True)) + 36
    draw.rounded_rectangle((x, y, x + width, y + 46), 8, fill=(*color, 18), outline=(*color, 130), width=1)
    text(layer, label, x + 18, y + 11, size, color, True, True)


@lru_cache(maxsize=1)
def backdrop():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = np.exp(-(((xx - 1490) / 700) ** 2 + ((yy - 620) / 620) ** 2) * 2)
    glow2 = np.exp(-(((xx - 220) / 650) ** 2 + ((yy - 100) / 500) ** 2) * 2)
    array = np.zeros((H, W, 3), np.float32) + [6, 10, 14]
    array += glow[..., None] * [15, 30, 24] + glow2[..., None] * [16, 9, 27]
    return Image.fromarray(array.astype(np.uint8)).convert("RGBA")


def environment(layer, t):
    draw = ImageDraw.Draw(layer)
    # A moving vanishing point gives the set depth without obscuring UI text.
    vx = 1080 + 180 * math.sin(t * 0.19)
    for x in range(-2400, 4500, 300):
        draw.line((vx, 395, x + (t * 32) % 300, H), fill=(18, 32, 34), width=1)
    for i in range(12):
        p = ((i / 12 + t * 0.055) % 1) ** 2
        y = 395 + p * 685
        draw.line((0, y, W, y), fill=(15, 29, 31), width=1)
    # Restrained orbital arcs and motion-tracking corners.
    draw.arc((1160, -470, 2450, 820), 60 + t * 4, 120 + t * 4, fill=(35, 57, 55), width=2)
    draw.line((74, 160, 74, 920), fill=(36, 51, 55), width=1)
    draw.line((74, 160, 74, 210), fill=LIME, width=3)


@lru_cache(maxsize=48)
def panel(name, crop=None):
    source = Image.open(SCREENS / f"{name}.png").convert("RGBA")
    if crop:
        source = source.crop(
            tuple(
                int(value * (source.width if i % 2 == 0 else source.height)) for i, value in enumerate(crop)
            )
        )
    source = ImageOps.contain(source, (1800, 1500), Image.Resampling.LANCZOS)
    mask = Image.new("L", source.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, source.width - 1, source.height - 1), 16, fill=255)
    source.putalpha(mask)
    draw = ImageDraw.Draw(source)
    draw.rounded_rectangle((0, 0, source.width - 1, source.height - 1), 16, outline=(94, 130, 132), width=2)
    return source


def project(layer, source, cx, cy, width, yaw=0, pitch=0, roll=0, opacity=1, cast_shadow=True):
    """Project a textured plane through a pinhole camera; inverse-map its pixels."""
    height = width * source.height / source.width
    points = np.array(
        [
            [-width / 2, -height / 2, 0],
            [width / 2, -height / 2, 0],
            [width / 2, height / 2, 0],
            [-width / 2, height / 2, 0],
        ],
        dtype=float,
    )
    a, b, c = map(math.radians, (yaw, pitch, roll))
    ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    points = points @ (rz @ rx @ ry).T
    depth = 2200
    quad = points[:, :2] * (depth / (depth + points[:, 2, None])) + [cx, cy]
    left = max(0, int(quad[:, 0].min()) - 2)
    top = max(0, int(quad[:, 1].min()) - 2)
    right = min(W, int(quad[:, 0].max()) + 3)
    bottom = min(H, int(quad[:, 1].max()) + 3)
    if right <= left or bottom <= top:
        return
    local = quad - [left, top]
    original = [(0, 0), (source.width, 0), (source.width, source.height), (0, source.height)]
    matrix, values = [], []
    for (x, y), (u, v) in zip(local, original, strict=True):
        matrix += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        values += [u, v]
    coeffs = np.linalg.solve(np.array(matrix), np.array(values))
    texture = source.transform(
        (right - left, bottom - top), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC
    )
    if opacity < 1:
        texture.putalpha(texture.getchannel("A").point(lambda x: round(x * opacity)))
    # Grounded hard contact edge, offset downstage, rather than a floating flat screenshot.
    if cast_shadow:
        shadow = Image.new("RGBA", (W, H))
        ImageDraw.Draw(shadow).polygon([(x + 16, y + 24) for x, y in quad], fill=(0, 0, 0, 120))
        layer.alpha_composite(shadow)
    layer.alpha_composite(texture, (left, top))


def camera(layer, name, u, duration, crop=None, width=1230, cx=1190, cy=580, direction=1, close=False):
    p = clamp(u / duration)
    settle = math.exp(-u * 8)
    yaw = direction * (mix(9, -3, p) + 13 * settle)
    pitch = mix(-5, 2, p)
    roll = direction * (mix(-1.3, 0.5, p) - 2 * settle)
    zoom = mix(1.0, 1.06, p) + 0.09 * settle
    if close:
        yaw *= 0.35
        pitch *= 0.35
        roll *= 0.4
    project(
        layer,
        panel(name, crop),
        cx + direction * 130 * settle,
        cy + 24 * settle,
        width * zoom,
        yaw,
        pitch,
        roll,
    )


def title(layer, first, second, u, subtitle=None, color=LIME, x=112, y=250, size=83):
    offset = 38 * (1 - ease(u / 0.35))
    text(layer, first, x, y + offset, size, WHITE, True)
    text(layer, second, x, y + size * 1.14 + offset, size, color, True)
    if subtitle:
        for i, line in enumerate(subtitle.split("\n")):
            text(layer, line, x + 4, y + size * 2.5 + 45 * i, 28, DIM)


def category_scene(layer, category, u, duration, number, subtitle, color):
    # The actual selected sidebar is held at macro scale, paired with its actual actions.
    camera(
        layer,
        f"category-{category}",
        u,
        duration,
        (0.022, 0.267, 0.246, 0.64),
        width=490,
        cx=368,
        cy=578,
        direction=-1,
        close=True,
    )
    camera(
        layer,
        f"category-{category}",
        u,
        duration,
        (0.253, 0.39, 0.98, 0.79),
        width=1065,
        cx=1270,
        cy=610,
        direction=1,
        close=True,
    )
    text(layer, number, 710, 220, 100, color, True, True)
    text(layer, subtitle, 900, 242, 48, WHITE, True)
    draw = ImageDraw.Draw(layer)
    draw.line((650, 595, 700, 595), fill=color, width=4)
    draw.polygon([(700, 595), (687, 587), (687, 603)], fill=color)
    tag(layer, "WORKFLOW  →  USEFUL COMMANDS", 830, 917, color)


def scene(index, u, duration):
    layer = Image.new("RGBA", (W, H))
    kind = SHOTS[index][2]
    if kind in ("git", "lfs"):
        word = "GIT" if kind == "git" else "+ LFS"
        size = 340 if kind == "git" else 275
        word_layer = Image.new("RGBA", (1400, 500))
        text(word_layer, word, 700, 85, size, LIME if kind == "git" else CYAN, True, center=True)
        p = ease(u / 0.35)
        project(
            layer,
            word_layer,
            960,
            490,
            mix(2100, 1500, p) + u * 60,
            mix(-32, 0, p),
            -5 + u * 4,
            mix(-6, 0, p),
            cast_shadow=False,
        )
        text(layer, "YOUR CREATIVE WORK HAS A HISTORY.", 960, 795, 29, WHITE, True, True, center=True)
    elif kind == "hero":
        camera(layer, "home", u, duration, width=1010, cx=1290, cy=580, direction=-1)
        title(layer, "ONE", "COMPANION.", u, "Git + Git LFS.\nBuilt around your next step.", size=86)
        tag(layer, "74 CURATED ACTIONS", 116, 815, CYAN)
    elif kind == "map":
        title(
            layer,
            "FIND YOUR",
            "WORKFLOW.",
            u,
            "9 clear categories.\nUseful commands, grouped by intent.",
            size=72,
        )
        camera(
            layer,
            "home",
            u,
            duration,
            (0.022, 0.267, 0.246, 0.64),
            width=500,
            cx=1030,
            cy=585,
            direction=-1,
            close=True,
        )
        text(layer, "01—09", 1410, 325, 68, LIME, True, True)
        text(layer, "Browse.", 1410, 435, 47, WHITE, True)
        text(layer, "Understand.", 1410, 505, 47, WHITE, True)
        text(layer, "Take action.", 1410, 575, 47, WHITE, True)
        tag(layer, "THE SIDEBAR IS YOUR MAP", 1380, 735, CYAN, 18)
    elif kind in ("changes", "branches", "lfs-category", "cleanup"):
        values = {
            "changes": ("changes", "03", "Save your work", LIME),
            "branches": ("branches", "04", "Try ideas", VIOLET),
            "lfs-category": ("lfs", "06", "Large files", CYAN),
            "cleanup": ("cleanup", "07", "Reclaim space", LIME),
        }
        category, number, subtitle, color = values[kind]
        category_scene(layer, category, u, duration, number, subtitle, color)
    elif kind == "library":
        text(layer, "LESS GUESSING. MORE UNDERSTANDING.", 112, 192, 56, WHITE, True)
        for i, (number, name, commands) in enumerate(GROUPS):
            col, row = i % 3, i // 3
            p = ease((u - i * 0.045) / 0.32)
            x, y = 112 + col * 570, 320 + row * 190 + 35 * (1 - p)
            color = (LIME, CYAN, VIOLET)[col]
            draw = ImageDraw.Draw(layer)
            draw.rounded_rectangle(
                (x, y, x + 540, y + 166), 13, fill=(16, 24, 29, 255), outline=(43, 66, 65), width=1
            )
            text(layer, number, x + 22, y + 25, 24, color, True, True)
            text(layer, name, x + 80, y + 23, 32, WHITE, True)
            text(layer, commands, x + 23, y + 100, 23, color, mono=True)
        text(
            layer,
            "A practical command library you can explore at your own pace.",
            960,
            960,
            28,
            DIM,
            center=True,
        )
    elif kind == "search":
        title(layer, "SEARCH", "YOUR WAY.", u, "Use a task. A command. A flag.", size=79)
        name = "search-save" if u < 1.25 else "search-flags"
        camera(
            layer, name, u % 1.25, 1.25, (0.25, 0.267, 0.98, 0.79), width=1125, cx=1250, cy=590, close=True
        )
        tag(layer, "Ctrl+F  /  ALL COMMANDS", 116, 760, CYAN)
    elif kind == "typing":
        text(layer, "START TYPING.", 112, 208, 72, WHITE, True)
        text(layer, "LET THE COMMAND FIND YOU.", 112, 305, 48, CYAN, True)
        name = f"typing-{min(6, int(max(0, u - 0.1) / 0.19))}"
        camera(layer, name, u, duration, (0.25, 0.267, 0.98, 0.65), width=1520, cx=1040, cy=675, close=True)
        tag(layer, "INLINE SUGGESTION", 1430, 310, CYAN, 18)
    elif kind == "complete":
        camera(
            layer,
            "completed",
            u,
            duration,
            (0.25, 0.267, 0.98, 0.58),
            width=1510,
            cx=1000,
            cy=580,
            direction=-1,
            close=True,
        )
        text(layer, "TAB.", 112, 207, 132, LIME, True)
        text(layer, "COMPLETED.", 490, 238, 86, WHITE, True)
        text(layer, "Suggestions complete. You decide when to run.", 960, 907, 30, DIM, center=True)
    elif kind == "review":
        title(layer, "REVIEW.", "THEN RUN.", u, "See the exact Git command\nbefore you execute it.", size=78)
        camera(
            layer,
            "review-status",
            u,
            duration,
            (0.18, 0.25, 0.82, 0.77),
            width=1060,
            cx=1240,
            cy=600,
            direction=-1,
            close=True,
        )
    elif kind == "execute":
        title(layer, "RUN IT.", "SEE IT.", u, "Real output.\nA clear result.", size=88)
        camera(
            layer,
            "results-status",
            u,
            duration,
            (0.03, 0.09, 0.97, 0.74),
            width=1150,
            cx=1250,
            cy=600,
            close=True,
        )
        tag(layer, "COMMAND EXECUTION  /  SUCCESS", 116, 830, LIME, 18)
    elif kind == "prune":
        text(layer, "PREVIEW THE CLEANUP FIRST.", 112, 205, 64, WHITE, True)
        tag(layer, "git lfs prune --dry-run", 112, 315, CYAN, 27)
        camera(
            layer,
            "results-prune",
            u,
            duration,
            (0.03, 0.09, 0.97, 0.46),
            width=1390,
            cx=1080,
            cy=680,
            direction=-1,
            close=True,
        )
    elif kind == "hint":
        title(layer, "LEARN AS", "YOU GO.", u, "Every action has a short hint.", size=84)
        camera(layer, "hint", u, duration, (0.253, 0.39, 0.98, 0.78), width=1160, cx=1260, cy=595, close=True)
        tag(layer, "PLAIN LANGUAGE. LESS FRICTION.", 116, 795, CYAN, 18)
    elif kind == "examples":
        title(
            layer,
            "CURIOUS?",
            "GO DEEPER.",
            u,
            "Expand a real example.\nLearn what the command means.",
            size=75,
        )
        camera(
            layer,
            "examples",
            u,
            duration,
            (0.185, 0.265, 0.815, 0.745),
            width=1090,
            cx=1255,
            cy=585,
            direction=-1,
            close=True,
        )
        tag(layer, "F2  /  DETAILS & EXAMPLES", 116, 805, VIOLET)
    elif kind == "learn":
        text(layer, "A COMPANION. AND A FIELD GUIDE.", 112, 190, 61, WHITE, True)
        camera(
            layer,
            "search-lfs",
            u,
            duration,
            (0.253, 0.39, 0.68, 0.81),
            width=740,
            cx=560,
            cy=645,
            direction=-1,
            close=True,
        )
        text(layer, "74", 1080, 360, 160, LIME, True, True)
        text(layer, "curated actions", 1087, 555, 44, WHITE, True)
        text(layer, "Short hints.", 1087, 665, 31, DIM)
        text(layer, "148 expandable examples.", 1087, 715, 31, DIM)
        text(layer, "Explore before you execute.", 1087, 765, 31, CYAN)
    elif kind == "montage":
        names = ["category-inspect", "category-sync", "category-recover", "category-setup"]
        sub = min(3, int(u / 0.5))
        camera(
            layer,
            names[sub],
            u % 0.5,
            0.5,
            (0.022, 0.267, 0.98, 0.79),
            width=1540,
            cx=1000,
            cy=650,
            direction=(-1) ** sub,
            close=True,
        )
        text(
            layer,
            ["LOOK AROUND.", "SHARE & SYNC.", "RECOVER.", "SET UP."][sub],
            112,
            196,
            77,
            LIME if sub % 2 == 0 else CYAN,
            True,
        )
    elif kind == "setup":
        title(layer, "SET UP ONCE.", "MAKE YOUR NEXT MOVE.", u, x=112, y=220, size=83)
        for i, label in enumerate(["Windows", "macOS", "Linux"]):
            tag(layer, label, 116 + i * 255, 522, (LIME, CYAN, VIOLET)[i], 30)
        text(layer, "$ git-companion", 116, 680, 73, LIME, True, True)
        text(layer, "Run setup. Reopen your terminal. You're ready.", 120, 820, 32, DIM)
    else:
        branch(layer, 904, 190, 112, ease(u / 0.45), LIME)
        text(layer, "GIT COMPANION", 960, 410, 115, WHITE, True, center=True)
        text(layer, "FIND IT. LEARN IT. RUN IT.", 960, 570, 52, LIME, True, center=True)
        text(layer, "$ git-companion", 960, 705, 43, CYAN, mono=True, center=True)
        text(layer, "github.com/RmaNMetaverse/git-companion-cli", 960, 860, 29, WHITE, mono=True, center=True)
    return layer


def frame(t):
    index = next((i for i, (a, b, _, _) in enumerate(SHOTS) if a <= t < b), len(SHOTS) - 1)
    start, end, _kind, chapter = SHOTS[index]
    u = t - start
    image = backdrop().copy()
    environment(image, t)
    content = scene(index, u, end - start)
    # Whip-pan inserts have a brief lateral smear; reading holds stay crisp.
    if index in (2, 3, 4, 5, 6, 7, 9, 12, 13, 14, 16, 17) and 0 <= u < 0.10:
        p = 1 - u / 0.10
        smear = Image.new("RGBA", (W, H))
        for shift, alpha in ((-60, 0.14), (-30, 0.24), (0, 0.62)):
            ghost = content.copy()
            ghost.putalpha(ghost.getchannel("A").point(lambda x, a=alpha: int(x * a)))
            smear.alpha_composite(ghost, (round(shift * p), 0))
        content = smear
    image.alpha_composite(content)
    # Static framing gives the camera edits a stable brand anchor.
    branch(image, 112, 73, 29, color=LIME)
    text(image, "GIT COMPANION", 166, 72, 24, WHITE, True, True)
    text(image, f"{index + 1:02d} / {chapter}", 1090, 79, 20, DIM, mono=True)
    draw = ImageDraw.Draw(image)
    draw.line((112, 1006, 1808, 1006), fill=(39, 55, 56), width=2)
    draw.line((112, 1006, 112 + 1696 * clamp(t / DURATION), 1006), fill=LIME, width=3)
    text(image, "GIT + GIT LFS / YOUR NEXT MOVE", 112, 1030, 17, DIM, mono=True)
    text(image, "WINDOWS / macOS / LINUX", 1480, 1030, 17, DIM, mono=True)
    if t > DURATION - 0.35:
        black = Image.new("RGBA", (W, H), (6, 10, 14, int(255 * clamp((t - DURATION + 0.35) / 0.35))))
        image.alpha_composite(black)
    return image.convert("RGB")


def sound_effects(time_scale=1.0):
    """Noise sweeps, mechanical key taps and impacts, with silence between events.

    There is no backing track, melody, chord progression or metronomic beat.
    """
    sr = 48000
    audio = np.zeros((round(DURATION * time_scale * sr), 2), np.float32)
    rng = np.random.default_rng(19771)
    events = []

    def add(at, duration, kind, level=0.4, pan=0):
        at *= time_scale
        n = int(duration * sr)
        tt = np.arange(n, dtype=np.float32) / sr
        noise = rng.uniform(-1, 1, n).astype(np.float32)
        if kind == "whoosh":
            # Modulated noise with moving spectral emphasis, never a pitched note.
            low = np.convolve(noise, np.ones(17) / 17, mode="same")
            high = noise - np.convolve(noise, np.ones(5) / 5, mode="same")
            env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.7
            signal = (low * 1.7 + high * (0.1 + 0.2 * tt / duration)) * env
        elif kind == "impact":
            phase = 2 * np.pi * (43 * tt + 2.5 * (1 - np.exp(-tt * 40)))
            signal = np.sin(phase) * np.exp(-tt * 19) + noise * np.exp(-tt * 70) * 0.15
            signal *= np.minimum(tt * 1000, 1)
        elif kind == "key":
            filtered = noise - np.convolve(noise, np.ones(7) / 7, mode="same")
            signal = filtered * np.exp(-tt * 160) * (0.65 + 0.35 * np.cos(tt * 2100))
        else:
            signal = (noise * 0.7 + np.sin(tt * 2 * np.pi * (130 - tt * 260)) * 0.3) * np.exp(-tt * 55)
        a = max(0, int(at * sr))
        n = min(n, len(audio) - a)
        pans = np.linspace(pan, -pan, n) if kind == "whoosh" else np.full(n, pan)
        audio[a : a + n, 0] += signal[:n] * level * np.sqrt((1 - pans) / 2)
        audio[a : a + n, 1] += signal[:n] * level * np.sqrt((1 + pans) / 2)
        events.append({"time": round(at, 3), "duration": duration, "effect": kind})

    for i, (start, _, kind, _) in enumerate(SHOTS):
        add(max(0, start - 0.13), 0.28 if i % 3 else 0.4, "whoosh", 0.48, (-1) ** i * 0.8)
        if kind in ("git", "lfs", "hero", "library", "execute", "end"):
            add(start + 0.025, 0.25, "impact", 0.36)
        else:
            add(start + 0.05, 0.10, "click", 0.16)
    for at in [17.25, 17.39, 17.52, 17.67, 18.45, 18.56, 18.69, 18.83, 18.96]:
        add(at, 0.043, "key", 0.21, -0.2)
    for i in range(7):
        add(19.52 + i * 0.19, 0.045, "key", 0.23, -0.2 + i * 0.05)
    for at in [21.77, 25.55, 28.16, 32.36, 38.5, 39, 39.5]:
        add(at, 0.12, "click", 0.26, 0.2)
    peak = float(np.max(np.abs(audio)))
    audio *= 0.65 / max(peak, 1e-8)
    WORK.mkdir(parents=True, exist_ok=True)
    with wave.open(str(WORK / "action-sfx.wav"), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sr)
        output.writeframes((audio * 32767).astype("<i2").tobytes())
    (WORK / "sound-events.json").write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
    print(f"Original SFX: {len(events)} transient events; peak {20 * math.log10(0.65):.1f} dBFS", flush=True)


def stills():
    tiles = []
    for i, (start, end, kind, _) in enumerate(SHOTS):
        image = frame(start + (end - start) * 0.58)
        image.save(WORK / f"shot-{i:02d}-{kind}.jpg", quality=93)
        tile = image.resize((480, 270), Image.Resampling.LANCZOS)
        tiles.append(tile)
    sheet = Image.new("RGB", (1920, math.ceil(len(tiles) / 4) * 270))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % 4) * 480, (i // 4) * 270))
    sheet.save(WORK / "storyboard.jpg", quality=94)
    frame(43.8).save(OUT / "teaser-action-poster.jpg", quality=94)
    print(WORK / "storyboard.jpg", flush=True)


def render(shot=None, time_scale=1.0):
    ffmpeg = os.environ.get("TEASER_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Set TEASER_FFMPEG to the local FFmpeg encoder.")
    encoder = os.environ.get("TEASER_ENCODER", "libx264")
    settings = (
        ["-preset", "medium", "-crf", "19"]
        if encoder == "libx264"
        else ["-b:v", "1700k", "-maxrate", "2100k", "-bufsize", "4200k", "-look_ahead", "0"]
    )
    if time_scale > 1:
        settings = ["-b:v", "1200k", "-maxrate", "1500k", "-bufsize", "3000k"]
        if encoder == "h264_qsv":
            settings += ["-look_ahead", "0"]
    first = round(SHOTS[shot][0] * FPS * time_scale) if shot is not None else 0
    duration = round(DURATION * time_scale)
    last = round(SHOTS[shot][1] * FPS * time_scale) if shot is not None else duration * FPS
    destination = WORK / (f"shot-{shot:02d}.mp4" if shot is not None else "silent-action.mp4")
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
        *settings,
        "-pix_fmt",
        "nv12" if encoder == "h264_qsv" else "yuv420p",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    with (WORK / "encoder.log").open("w") as log:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
        try:
            for i in range(first, last):
                process.stdin.write(frame(i / FPS / time_scale).tobytes())
                if i % (FPS * 2) == 0:
                    print(f"Rendered {i // FPS:02d}/{duration}s", flush=True)
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError((WORK / "encoder.log").read_text())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    if shot is None:
        sound_effects(time_scale)


def preview():
    images = []
    for start, end in [(4.7, 6.3), (7.1, 8.3), (19.7, 21.3), (25.9, 27.5), (32.8, 34.4), (43, 44.6)]:
        for t in np.arange(start, end, 0.1):
            image = frame(float(t)).resize((800, 450), Image.Resampling.LANCZOS)
            images.append(
                image.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            )
    path = OUT / "teaser-action-preview.gif"
    images[0].save(path, save_all=True, append_images=images[1:], duration=100, loop=0, optimize=True)
    print(f"Preview: {path} ({path.stat().st_size / 1e6:.2f} MB)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stills", action="store_true")
    parser.add_argument("--gif", action="store_true")
    parser.add_argument("--sfx", action="store_true")
    parser.add_argument(
        "--shot", type=int, choices=range(len(SHOTS)), help="Render one shot as an editing insert."
    )
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.stills:
        stills()
    elif args.gif:
        preview()
    elif args.sfx:
        sound_effects()
    else:
        render(args.shot)
    (WORK / "edit-decision-list.json").write_text(
        json.dumps(
            {
                "duration": DURATION,
                "fps": FPS,
                "shots": [{"in": a, "out": b, "scene": kind, "title": title} for a, b, kind, title in SHOTS],
                "audio": "Original transient sound effects only; no music.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
