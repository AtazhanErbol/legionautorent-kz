# Legion — original hero sedan

User request: «ты умеешь по референсам сам создать 3д модель?» → «тогда сделай».

Create an original generic premium sedan for the existing Legion homepage. The images
in `design_refs/3d/` inform proportions, dark studio lighting and material mood; they
are not textures or blueprints and are not copied into the asset. No logos, badges,
brand grille or claimed replica of a particular manufacturer.

Target: approximately 4.96 m long, 1.94 m wide excluding mirrors, 1.45 m high;
2.90 m wheelbase, ground origin, glTF +Y up / +Z front. Smooth curved body,
open wheel arches, separate glazing, four detailed wheels, door seams, original
LED lamps, subtle trim and simplified interior. Default lights off.

Budget: 80,000 triangles maximum; meshopt GLB under 900 KiB. No external textures
or remote runtime assets. Keep all existing scene controls, light material names,
wheel pivots, URLs and website data unchanged. Inspect in neutral and dark light,
then load through the actual site's GLTFLoader and exercise drag/light/scroll.

Source workflow: local procedural Blender Python, editable .blend and raw .glb,
then local glTF Transform meshopt compression. No paid provider, downloaded car
mesh, texture library, or reference-image pixels in the resulting model.

Negative direction: boxy placeholder, flat slab roof, faceted fenders, missing wheel
arches, floating wheels, opaque pale windscreen, painted-on highlight stripes,
brand emblems, emissive paint, unnecessarily heavy textures.
