# Git Companion teasers

## One-minute edit: slower pacing

`git-companion-action-teaser-60s.mp4` is the same action teaser extended to **1:00**, at 1920×1080 and 30 fps, with sound effects only. All 21 shots, camera movements, graphics and features are retained. Every shot lasts about 30% longer, giving the command categories and examples more reading time. Frames are rendered again on the slower timeline; sound effects are resynchronized while retaining their original pitch and duration.

The matching preview, cover, captions and verified metadata use the `teaser-action-60s-` prefix. Both previous videos and their assets are preserved. The main README now features this one-minute version.

Rebuild with `python -m dev.tools.teaser_action_60` in the rendering environment described below, with `TEASER_FFMPEG`, `TEASER_ENCODER` and `TEASER_BLENDER` set. It reuses the existing UI captures, creates new assets under `dev/artifacts/teaser-action-60s/`, encodes the resynchronized effects with Blender and validates the final 1,800-frame H.264/AAC video.

## Second edit: Find it. Learn it. Run it.

**46 seconds, 1920×1080, 30 fps. Original sound effects only, with no music or voiceover.** The faster edit uses 21 main shots, camera orbits, dolly moves, whip transitions, close-ups and rapid category switches. Reading shots hold longer so the command map and examples remain useful.

- `git-companion-action-teaser.mp4`: full second video, H.264 picture and stereo AAC sound effects.
- `teaser-action-preview.gif`: looping silent README montage.
- `teaser-action-poster.jpg`: still cover.
- `teaser-action-captions.vtt`: optional captions.
- `teaser-action-info.json`: verified output metadata and production method.

The nine sidebar workflows are the main story, followed by command search, genuine inline autocomplete and Tab acceptance, the command review form, real Git status output, real LFS prune dry-run output, short hints and expanded Photoshop/Blender examples. The app's 74 curated actions and 148 examples are presented as a practical learning resource. It does not claim to expose every possible Git or Git LFS flag.

### How this video was made

This is a frame-by-frame procedural render. It does not use HTML/CSS animation or a browser screen recording.

1. `dev/tools/teaser_action_capture.py` runs the real Textual/Rich app against a temporary, isolated Git/LFS repository. It navigates actual controls, accepts autocomplete, opens review forms, clicks **Run command**, and exports 27 genuine UI states as SVG. The demo uses placeholder artwork; it never operates on a production repository. Only the displayed demo path is sanitized.
2. `dev/tools/teaser_rasterize.cjs` uses **Sharp** to rasterize those SVGs into crisp PNG textures.
3. `dev/tools/teaser_action_render.py` uses **Python, Pillow and NumPy** to draw every video frame. A pinhole-camera model rotates and projects the UI textures in three dimensions; inverse perspective mapping produces the angled camera views. Keyframed position, scale, rotation and easing create the dolly moves, orbit changes, fast cuts and short whip smears. Typography, grid depth, category cards and graphic accents are drawn directly into the frames.
4. The same renderer synthesizes **48 kHz stereo sound effects** from noise envelopes, filtered clicks and short impacts. Each event is synchronized to a cut, keystroke or action. There is no song, rhythmic backing track, melody or chord progression. The source WAV and event list remain in ignored build artifacts.
5. **FFmpeg** encodes the picture as H.264. On this workstation it uses Intel Quick Sync. **Blender's background video sequencer** encodes the WAV as AAC because this workstation's FFmpeg build has no AAC encoder. A tiny temporary carrier video supplies the AAC stream; FFmpeg discards its picture and muxes the final video with fast-start playback.
6. **FFprobe** verifies the final codecs, duration, 1080p resolution, 30 fps, 1,380 video frames and file size below 10 MB. Storyboard and decoded-frame inspection check layout and legibility.

### Rebuild the second edit

Use an app environment for capture, a Node environment with Sharp for rasterization, and a Python environment with Pillow and NumPy for rendering. These are developer tools; they do not add app runtime dependencies.

```sh
python -m dev.tools.teaser_action_capture
node dev/tools/teaser_rasterize.cjs dev/artifacts/teaser-action/screens
python -m dev.tools.teaser_action_render --stills
python -m dev.tools.teaser_action_render
blender --background --factory-startup --python-exit-code 1 --python dev/tools/teaser_audio.py -- dev/artifacts/teaser-action/action-sfx.wav dev/artifacts/teaser-action/sfx-carrier.mp4 46
python -m dev.tools.teaser_action_finish
python -m dev.tools.teaser_action_render --gif
```

Set `TEASER_FFMPEG` to an installed FFmpeg executable and optionally `TEASER_FFPROBE` to FFprobe. The default video encoder is `libx264`; `TEASER_ENCODER=h264_qsv` selects Intel Quick Sync. Set `SHARP_PATH` if Sharp is available at a separate absolute module path. Intermediate screenshots, WAV audio, edit decisions, sound events and logs live under ignored `dev/artifacts/teaser-action/`.

The original video and its preview assets are preserved below. The main README features the one-minute revision and links to both earlier videos.

## Original edit: A little less friction

The teaser is **44 seconds**, 1920×1080, 30 fps, with an original electronic soundtrack and an editorial style that remains understandable when muted.

- `git-companion-teaser.mp4`: full video for GitHub uploads and sharing; H.264 picture with AAC audio.
- `teaser-preview.gif`: an eight-second silent animated montage for the main README, linked to the full video.
- `teaser-poster.jpg`: still cover image.
- `teaser-captions.vtt`: optional WebVTT captions.

The motion design, branch graphics, soundtrack and layout were created specifically for this project. No stock footage or third-party music is used. UI images are genuine Textual captures from a temporary demo repository with local placeholder artwork files. No production project or user Git settings were modified. System fonts are rendered into the video; font files are not distributed.

## Feature either video on GitHub

The main README already uses a linked animated image, which GitHub's Markdown renderer can display. Commit this media folder together with the README to make the preview and relative MP4 link available in the repository.

For GitHub's native inline video player, drag the MP4 into a GitHub issue or PR comment editor. GitHub uploads the attachment immediately and returns an asset URL; you can copy that URL into the README on its own line. Posting the comment is not required just to obtain the upload URL. GitHub documents a 10 MB upload limit for videos on free plans, and 100 MB on paid plans: [GitHub attachment documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files). No remote upload or push was performed as part of creating these local assets.

## Rebuild the original edit

Developer sources are in `dev/tools/teaser_capture.py`, `teaser_rasterize.cjs`, `teaser_render.py`, `teaser_audio.py` and `teaser_finish.py`.

1. Capture the actual app with `python -m dev.tools.teaser_capture` from an environment containing the app dependencies and Git LFS.
2. Rasterize the SVG files with `node dev/tools/teaser_rasterize.cjs`; install `sharp` or set `SHARP_PATH` to an existing module.
3. Install Pillow and NumPy in a rendering environment. Render a storyboard with `python -m dev.tools.teaser_render --stills`.
4. Set `TEASER_FFMPEG` to a local FFmpeg and run `python -m dev.tools.teaser_render`. The default encoder is `libx264`; `TEASER_ENCODER=h264_qsv` uses Intel Quick Sync when available.
5. Encode the soundtrack using `blender --background --factory-startup --python-exit-code 1 --python dev/tools/teaser_audio.py -- dev/artifacts/teaser/original-score.wav dev/artifacts/teaser/audio-carrier.mp4`. The tiny carrier video's picture is discarded at the next step; its audio is AAC.
6. Run `python -m dev.tools.teaser_finish` with `TEASER_FFMPEG` (and optionally `TEASER_FFPROBE`) set. It muxes the silent picture and original AAC soundtrack with stream copy, fast-start streaming and a 44-second limit. It verifies H.264/AAC, resolution, frame rate, frame count, duration and a file size below 10 MB, then saves `teaser-info.json`.
7. Run `python -m dev.tools.teaser_render --gif` for the README preview.

All intermediate screenshots, original WAV audio, logs and storyboard files live under ignored `dev/artifacts/teaser/`. Finished shareable assets live here so the project root stays uncluttered. These media tools are developer utilities, not runtime dependencies of the app.
