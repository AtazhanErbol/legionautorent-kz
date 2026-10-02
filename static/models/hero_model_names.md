# hero.glb: placeholder model (names and conventions)

PLACEHOLDER ONLY: blocky sedan for developing the scene. Replace with the final licensed model later (see "Swapping").

## Orientation
- glTF standard: +Y up, car FRONT faces +Z, +X is the car's LEFT side. Origin at ground level, centered.
- Size: about 4.8 m long, 1.9 m wide, 1.6 m tall. Scale in code if needed.

## Nodes (use these names in Three.js: `gltf.scene.getObjectByName(...)`)
- `Body`, `Roof`: body paint
- `Glass`: transparent glass
- `Grille`: black plastic
- `Headlight_L`, `Headlight_R`
- `Taillight_L`, `Taillight_R`
- `Mirror_L`, `Mirror_R`
- `Wheel_FL`, `Wheel_FR`, `Wheel_RL`, `Wheel_RR`: pivot at the wheel center. Spin around the X axis. Each contains `Tire_xx` and `Rim_xx`

## Materials (by name)
- `Body_Paint` (metallic 0.9, roughness 0.28, dark graphite; recolor to match brand)
- `Glass` (alphaMode BLEND)
- `Headlight_Lens`, `Taillight_Lens`: emissive is OFF (0,0,0) by default
- `Tire`, `Rim`, `Black_Plastic`

## Headlights on/off
Find materials named `Headlight_Lens` / `Taillight_Lens`. To switch ON: set `material.emissive` to white (headlights) or red (taillights), `emissiveIntensity` about 2-4, plus bloom if used. Add SpotLights at the Headlight_* positions pointing +Z. To switch OFF: emissive back to black.

## Swapping to the final model
Path is a setting in admin (default `static/models/hero.glb`). The code must NOT depend on mesh names directly: keep a small name map in config (`{headlightMaterials: [...], taillightMaterials: [...], wheelNodes: [...]}`) so a purchased model with different names only needs the map updated.
