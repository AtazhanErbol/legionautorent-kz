# 3D hero references

**Update — 2026-10-03:** The user explicitly approved assembling the three supplied frames (`01-start.png`, `02-scroll-50.png`, `03-end-headlights.png`) into the site's scroll-controlled video with smooth cross-dissolves and a small zoom. This approval overrides the earlier “not site assets” restriction **only for this montage and its posters**. See `HERO_VIDEO.md`. The remaining text below is preserved as the historical 3D art direction; this note makes no separate rights or licensing claim.

Style references for the 3D hero. They are NOT site assets and must not be shipped on the website.

IMPORTANT: the car in these images may look like the client's real car, but the 3D model is a generic car (`static/models/hero.glb`). Do not try to copy the shape, badges or logos. Take only atmosphere, lighting and light glow.

## Files

- `01-start.png`: scroll 0%. Low camera, front three-quarter view, car turned about 30 degrees, headlights OFF, only soft rim light. The left side is empty for the headline.
- `02-scroll-50.png`: scroll 50%. Car in pure side profile, headlights start to glow.
- `03-end-headlights.png`: scroll 100%. Rear three-quarter view, taillights red, headlights fully ON with light beams on the floor. The right side is empty for text.
- `lighting.jpg`: mood reference for studio lighting: dark glossy reflective floor, thin rim lights along the roofline and shoulders, light haze.
- `headlights.jpg`: reference for headlight glow: bloom limited to the lights, soft beams in fog on the floor.

## How to use

- Match the camera angles of the three scroll frames at 0%, 50% and 100% of the hero scroll, interpolating smoothly between them.
- Match the lighting mood of `lighting.jpg` with cheap techniques (environment map, strip lights, fake or blurred floor reflection); keep it light on mobile.
- Match the glow of `headlights.jpg` with emissive materials, soft spotlights and bloom on desktop only.
- If a file listed here is missing, use sensible defaults and mention it in the project README.
