"""Prepare the supplied continuous camera-orbit film for the scroll hero.

This script preserves both original files, creates complete reference contact
sheets, transcodes the full video (without audio), and extracts real-frame
posters/details. It does not synthesize imagery or alter the car's proportions.

Run: .venv/Scripts/python.exe tools/build_hero_film.py
Use --inspect-only to regenerate the contact sheets without replacing web assets.
FFmpeg is provided by the project-local imageio-ffmpeg installation.
"""

import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "assets/hero-film/source"
PREVIEW_DIR = ROOT / "output/playwright/hero-film-reference"
GIF_NAME = "1_LQmQdk96lvRuSXW5LSJVBA.gif"
VIDEO_NAME = "gemini_generated_video_3917a51a.mp4"
sys.path.insert(0, str(ROOT / ".local/video-tools"))
import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(path):
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def ffmpeg(*arguments):
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *map(str, arguments)],
        check=True,
    )


def metadata(path):
    frames = imageio_ffmpeg.read_frames(str(path))
    result = next(frames)
    frames.close()
    return result


def preserve_source(name):
    """Never overwrite a source file; a differing existing copy is an error."""
    original = Path.home() / "Downloads" / name
    preserved = SOURCE_DIR / name
    if preserved.exists():
        if original.exists() and digest(original) != digest(preserved):
            raise RuntimeError(f"Original and preserved source differ: {name}")
    elif original.exists():
        shutil.copy2(original, preserved)
    else:
        raise FileNotFoundError(original)
    return {"original_path": str(original), **asset(preserved)}


def contact_sheet(frames, destination, columns=4, width=350):
    height = round(frames[0][1].height * width / frames[0][1].width)
    canvas = Image.new(
        "RGB", (columns * width, math.ceil(len(frames) / columns) * (height + 32)), "#101010"
    )
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    for index, (label, frame) in enumerate(frames):
        x, y = (index % columns) * width, (index // columns) * (height + 32)
        canvas.paste(frame.resize((width, height), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 8, y + height + 5), label, font=font, fill="white")
    canvas.save(destination)


def inspect_sources():
    gif = Image.open(SOURCE_DIR / GIF_NAME)
    frames, durations, elapsed, next_time = [], [], 0, 0
    for index in range(gif.n_frames):
        gif.seek(index)
        duration = gif.info.get("duration", 20)
        durations.append(duration)
        if elapsed + duration >= next_time:
            frame = gif.convert("RGB")
            label = f"{elapsed / 1000:.2f}s / frame {index}"
            frames.append((label, frame))
            frame.save(PREVIEW_DIR / f"gif-{len(frames)-1:02d}.jpg", quality=92)
            next_time += 500
        elapsed += duration
    frames.append((f"{elapsed / 1000:.2f}s / final", gif.convert("RGB")))
    contact_sheet(frames, PREVIEW_DIR / "gif-complete-contact.png")

    source = SOURCE_DIR / VIDEO_NAME
    video_metadata = metadata(source)
    # Explicit timestamps, including the final decodable frame, avoid the half
    # frame offset introduced by a general-purpose fps=2 contact-sheet filter.
    times = [index / 2 for index in range(20)] + [9.95]
    frames = []
    for index, time in enumerate(times):
        frame_path = PREVIEW_DIR / f"video-{index+1:02d}.jpg"
        ffmpeg("-ss", time, "-i", source, "-frames:v", 1, "-q:v", 2, frame_path)
        with Image.open(frame_path) as frame:
            frames.append((f"{time:.2f}s", frame.copy()))
    contact_sheet(frames, PREVIEW_DIR / "video-complete-contact.png")
    return {
        "gif": {
            "resolution": gif.size,
            "frames": gif.n_frames,
            "duration_seconds": elapsed / 1000,
            "frame_durations_ms": sorted(set(durations)),
            "all_frames_read": True,
            "sample_interval_seconds": 0.5,
            "contact_sheet": "output/playwright/hero-film-reference/gif-complete-contact.png",
        },
        "video": video_metadata,
        "video_contact_sheet": "output/playwright/hero-film-reference/video-complete-contact.png",
    }


def extract_web_image(name, time, crop=None, width=None, quality=88):
    target = ROOT / "static/img" / f"hero-drive-{name}.webp"
    filters = []
    if crop:
        x, y, w, h = crop
        filters.append(f"crop={w}:{h}:{x}:{y}")
    if width:
        filters.append(f"scale={width}:-2:flags=lanczos")
    arguments = ["-ss", time, "-i", SOURCE_DIR / VIDEO_NAME]
    if filters:
        arguments += ["-vf", ",".join(filters)]
    ffmpeg(*arguments, "-frames:v", 1, "-c:v", "libwebp", "-quality", quality, target)
    with Image.open(target) as image:
        dimensions = image.size
    return {
        **asset(target),
        "source_time_seconds": time,
        "source_crop_xywh": crop,
        "resolution": dimensions,
    }


def verify_video(source, video):
    source_frames, source_seconds = imageio_ffmpeg.count_frames_and_secs(str(source))
    output_frames, output_seconds = imageio_ffmpeg.count_frames_and_secs(str(video))
    atoms = []
    with video.open("rb") as handle:
        while True:
            header = handle.read(8)
            if len(header) != 8:
                break
            size, kind = struct.unpack(">I4s", header)
            if size == 1:
                size = struct.unpack(">Q", handle.read(8))[0]
                header_size = 16
            else:
                header_size = 8
            atoms.append(kind.decode("ascii"))
            if size < header_size:
                break
            handle.seek(size - header_size, 1)
    keyframes = subprocess.run(
        [FFMPEG, "-hide_banner", "-skip_frame", "nokey", "-i", str(video),
         "-vf", "showinfo", "-an", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    times = [float(value) for value in re.findall(r"pts_time:([\d.]+)", keyframes.stderr)]
    verification = {
        "source_video_frames": source_frames,
        "web_video_frames": output_frames,
        "source_video_seconds": source_seconds,
        "web_video_seconds": output_seconds,
        "all_frames_preserved": source_frames == output_frames,
        "top_level_mp4_atoms": atoms,
        "moov_before_mdat": atoms.index("moov") < atoms.index("mdat"),
        "keyframe_times_seconds": times,
        "max_keyframe_interval_seconds": max(b - a for a, b in zip(times, times[1:])),
        "no_audio_track": "audio_codec" not in metadata(video),
    }
    assert verification["all_frames_preserved"]
    assert verification["moov_before_mdat"]
    assert verification["no_audio_track"]
    assert verification["max_keyframe_interval_seconds"] <= 0.5
    return verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect-only", action="store_true")
    args = parser.parse_args()
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sources = [preserve_source(GIF_NAME), preserve_source(VIDEO_NAME)]
    inspection = inspect_sources()
    if args.inspect_only:
        print(json.dumps(inspection, ensure_ascii=False, indent=2))
        return

    video = ROOT / "static/video/hero-drive.mp4"
    ffmpeg(
        "-i", SOURCE_DIR / VIDEO_NAME, "-map", "0:v:0", "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-profile:v", "high", "-level", "3.1", "-pix_fmt", "yuv420p",
        "-g", "12", "-keyint_min", "12", "-sc_threshold", "0",
        "-movflags", "+faststart", video,
    )
    posters = {
        # Identical timestamp and framing make the poster-to-video handoff match.
        "desktop": extract_web_image("poster", 0, quality=84),
        "front_illuminated": extract_web_image("front", 1, quality=86),
        # Mobile is static and uses an illuminated frontal frame. The 720px
        # source crop is exported at its native width, without upscaling.
        "mobile": extract_web_image("mobile", 1, crop=(280, 120, 720, 600), quality=86),
        "profile": extract_web_image("profile", 5.5, quality=88),
        "rear": extract_web_image("rear", 9.7, quality=88),
    }
    details = {
        "headlight": extract_web_image("headlight", 3, crop=(220, 260, 540, 330), quality=91),
        "wheel": extract_web_image("wheel", 4.5, crop=(290, 300, 480, 340), quality=91),
        "taillight": extract_web_image("taillight", 8.5, crop=(470, 230, 490, 320), quality=91),
    }
    detail_frames = []
    for name, record in details.items():
        with Image.open(ROOT / record["path"]) as image:
            detail_frames.append((f"{name} / {record['source_time_seconds']}s", image.copy()))
    contact_sheet(detail_frames, PREVIEW_DIR / "detail-crops.png", columns=3, width=490)
    output_metadata = metadata(video)
    report = {
        "kind": "Full supplied continuous camera-orbit video; no synthesized frames",
        "authorization": "User supplied GIF and MP4 and requested optimized web video, posters and real-frame detail crops",
        "sources": sources,
        "inspection": inspection,
        "output": {**asset(video), **output_metadata},
        "audio": False,
        "encoding": {"codec": "libx264", "preset": "slow", "crf": 18, "profile": "high", "level": "3.1", "pixel_format": "yuv420p"},
        "resolution_preserved": True,
        "frame_rate_preserved": True,
        "entire_video_track_preserved": True,
        "keyframe_interval_frames": 12,
        "keyframe_interval_seconds": 0.5,
        "faststart": True,
        "under_5_megabytes": video.stat().st_size < 5_000_000,
        "posters": posters,
        "details": details,
        "observed_video_timeline": [
            {"start": 0, "end": 1.5, "view": "Frontal view; headlights brighten"},
            {"start": 1.5, "end": 4.5, "view": "Continuous orbit to front three-quarter view"},
            {"start": 4.5, "end": 6.5, "view": "Side profile"},
            {"start": 6.5, "end": 10, "view": "Rear three-quarter view to rear with red taillights"},
        ],
        "gif_composition": [
            "0–1.2s: dominant centered object and large overlapping display typography",
            "1.2–3.4s: whole studio frame narrows and shifts left; copy appears right",
            "3.4–7.4s: overlapping asymmetric detail panels move through the composition",
            "7.4–9.2s: complete final object view returns under large typography",
            "9.2–11.88s: recording closes and returns to initial view; do not reproduce the loading gap",
        ],
        "limitations": [
            "Source video is 1280×720; crops retain source pixels without invented high-resolution detail",
            "The video is supplied AI-generated imagery, not documentary proof of the rental fleet or equipment",
            "Studio background remains part of every video/frame composition; no artificial 3D rotation of a flat image",
        ],
        "ffmpeg_version": imageio_ffmpeg.get_ffmpeg_version(),
        "verification": verify_video(SOURCE_DIR / VIDEO_NAME, video),
    }
    destination = ROOT / "reports/hero_film_asset.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
