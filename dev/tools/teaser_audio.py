"""Blender background-only helper: encode the original score as an AAC carrier MP4."""

import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1 :]
source, destination = (Path(value).resolve() for value in args[:2])
duration = float(args[2]) if len(args) > 2 else 44
scene = bpy.context.scene
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = round(duration * 30)
editor = scene.sequence_editor_create()
editor.strips.new_sound("Original Git Companion audio", str(source), channel=2, frame_start=1)
editor.strips.new_effect("Audio carrier", type="COLOR", channel=1, frame_start=1, length=scene.frame_end)
scene.render.resolution_x = 16
scene.render.resolution_y = 16
scene.render.resolution_percentage = 100
scene.render.use_sequencer = True
if hasattr(scene.render.image_settings, "media_type"):
    scene.render.image_settings.media_type = "VIDEO"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "MPEG4"
scene.render.ffmpeg.audio_codec = "AAC"
scene.render.ffmpeg.audio_bitrate = 96
scene.render.filepath = str(destination)
bpy.ops.render.render(animation=True)
if not destination.exists() or destination.stat().st_size < 1000:
    raise RuntimeError("AAC export did not produce an audio carrier file.")
print(f"Encoded original soundtrack: {destination}")
