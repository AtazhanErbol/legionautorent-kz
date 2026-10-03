# LEGION scroll film

The user supplied both files in `source/` for the October 3, 2026 hero animation update. The copies are byte-identical to the supplied downloads; source checksums are recorded in `reports/hero_film_asset.json`. The earlier three-still montage and 3D experiments remain in their original locations.

- `1_LQmQdk96lvRuSXW5LSJVBA.gif`: composition and motion reference, 557 frames, 11.88 seconds. It is not shipped as a website asset.
- `gemini_generated_video_3917a51a.mp4`: the supplied car film, 1280×720, 24 fps, 240 video frames. The original also has audio.

Run `.venv/Scripts/python.exe tools/build_hero_film.py` from the repository root to reproduce the web MP4 and WebP frames. FFmpeg comes from the project-local `.local/video-tools` installation of `imageio-ffmpeg`. `--inspect-only` regenerates the timestamped contact sheets without replacing web assets.

The web film keeps all 240 video frames, full duration and original proportions, removes audio, and uses H.264 with a keyframe every 0.5 seconds and MP4 faststart. Crops are extracted from the actual supplied frames at their native pixel sizes. No new imagery or apparent 3D rotation of a still image is generated.

Contact sheets are in `output/playwright/hero-film-reference/`. The asset report includes poster/crop coordinates, timestamps, hashes, frame-count verification, keyframe timestamps and MP4 atom order.

The supplied film is a visual illustration. Its appearance is not used as evidence of catalogue specifications, equipment or availability.
