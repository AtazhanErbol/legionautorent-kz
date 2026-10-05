"""Read-only GLB/Legion hero contract audit, using only Python's standard library.

Usage: python tools/validate_hero_asset.py static/models/hero.glb
Prints JSON to stdout; exit 0 means the checked structure/contract passed, 1 failed.
Redirect stdout to a NEW report file if a saved report is wanted.

This is not the Khronos glTF validator or a visual/physics test. Meshopt/Draco
payloads are not decoded. Bounds use POSITION accessor min/max, integer
normalization, and the complete node transform chain. A transformed local AABB
can overestimate the exact rotated mesh bounds. Skins, morphs, animations, texture
appearance, topology quality, wheel pivot centering and lighting require a real
renderer/visual review. No files are modified and no external URIs are fetched.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import sys


REQUIRED_NODES = (
    "Body", "Roof", "Glass", "Grille", "Headlight_L", "Headlight_R",
    "Taillight_L", "Taillight_R", "Mirror_L", "Mirror_R",
    "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
)
REQUIRED_MATERIALS = (
    "Body_Paint", "Glass", "Headlight_Lens", "Taillight_Lens", "Tire", "Rim",
    "Black_Plastic",
)
COMPONENTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
              5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
          "MAT2": 4, "MAT3": 9, "MAT4": 16}
IDENTITY = [[int(i == j) for j in range(4)] for i in range(4)]


def finite_vector(value, size):
    return (isinstance(value, list) and len(value) == size
            and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                    and math.isfinite(x) for x in value))


def multiply(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4))
             for j in range(4)] for i in range(4)]


def matrix(node):
    if "matrix" in node:
        values = node["matrix"]
        if not finite_vector(values, 16):
            raise ValueError("matrix must contain 16 finite numbers")
        if any(key in node for key in ("translation", "rotation", "scale")):
            raise ValueError("matrix and TRS cannot coexist")
        if any(abs(values[i]) > 1e-8 for i in (3, 7, 11)) or abs(values[15] - 1) > 1e-8:
            raise ValueError("matrix must be affine")
        return [[values[col * 4 + row] for col in range(4)] for row in range(4)]
    translation = node.get("translation", [0, 0, 0])
    rotation = node.get("rotation", [0, 0, 0, 1])
    scale = node.get("scale", [1, 1, 1])
    if not (finite_vector(translation, 3) and finite_vector(rotation, 4)
            and finite_vector(scale, 3)):
        raise ValueError("TRS must contain finite numbers of the correct length")
    if abs(sum(x * x for x in rotation) - 1) > 0.001:
        raise ValueError("rotation quaternion must have unit length")
    x, y, z, w = rotation
    result = [
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w), translation[0]],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w), translation[1]],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y), translation[2]],
        [0, 0, 0, 1],
    ]
    for row in range(3):
        for col in range(3):
            result[row][col] *= scale[col]
    return result


def normalize(value, accessor):
    if not accessor.get("normalized"):
        return value
    kind = accessor["componentType"]
    if kind in (5120, 5122):
        return max(value / (127 if kind == 5120 else 32767), -1)
    if kind in (5121, 5123):
        return value / (255 if kind == 5121 else 65535)
    raise ValueError("normalized component type must be BYTE/SHORT")


def transformed_bounds(accessor, transform):
    lo = [normalize(x, accessor) for x in accessor["min"]]
    hi = [normalize(x, accessor) for x in accessor["max"]]
    points = [tuple(sum(transform[i][j] * p[j] for j in range(3))
                    + transform[i][3] for i in range(3))
              for p in itertools.product(*zip(lo, hi))]
    return ([min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)])


def merge_bounds(bounds):
    if not bounds:
        return None
    lo = [min(b[0][i] for b in bounds) for i in range(3)]
    hi = [max(b[1][i] for b in bounds) for i in range(3)]
    return {"min": lo, "max": hi, "size": [hi[i] - lo[i] for i in range(3)],
            "center": [(hi[i] + lo[i]) / 2 for i in range(3)]}


def read_glb(data):
    if len(data) < 20:
        raise ValueError("file is shorter than a GLB header and JSON chunk header")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("invalid GLB magic, version, or declared file length")
    offset, chunks = 12, []
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("truncated chunk header")
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        if size % 4 or offset + size > len(data):
            raise ValueError("unaligned or truncated chunk")
        chunks.append((kind, data[offset:offset + size]))
        offset += size
    if not chunks or chunks[0][0] != 0x4E4F534A:
        raise ValueError("first chunk must be JSON")
    if sum(kind == 0x4E4F534A for kind, _ in chunks) != 1:
        raise ValueError("GLB must contain exactly one JSON chunk")
    bins = [payload for kind, payload in chunks if kind == 0x004E4942]
    if len(bins) > 1:
        raise ValueError("GLB must contain at most one BIN chunk")
    doc = json.loads(chunks[0][1].decode("utf-8"))
    if not isinstance(doc, dict) or doc.get("asset", {}).get("version") != "2.0":
        raise ValueError("JSON asset.version must be 2.0")
    pending = [doc]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("JSON contains a non-finite number")
    return doc, bins[0] if bins else b""


def validate(data, path="<bytes>"):
    report = {"path": str(path), "bytes": len(data),
              "sha256": hashlib.sha256(data).hexdigest(), "valid": False,
              "errors": [], "warnings": [], "limitations": [
                  "Meshopt/Draco compressed payloads are not decoded; metadata is audited.",
                  "World bounds transform accessor AABBs; rotated bounds can be conservative.",
                  "Visual quality, intersections, normals, wheel pivots, animation/skin/morph "
                  "deformation and texture appearance require a renderer.",
                  "This contract audit does not replace the Khronos glTF validator.",
              ]}
    errors, warnings = report["errors"], report["warnings"]
    try:
        doc, binary = read_glb(data)
    except (ValueError, UnicodeError, AttributeError, struct.error) as exc:
        errors.append(str(exc))
        return report
    try:
        _audit(doc, binary, report)
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, OverflowError,
            RecursionError, struct.error) as exc:
        errors.append(f"Malformed/unsupported JSON structure: {type(exc).__name__}: {exc}")
    report["valid"] = not errors
    report["warnings"] = list(dict.fromkeys(warnings))
    return report


def _audit(doc, binary, report):
    errors, warnings = report["errors"], report["warnings"]
    nodes, meshes, accessors, materials = (doc.get(k, []) for k in
                                         ("nodes", "meshes", "accessors", "materials"))
    views, buffers = doc.get("bufferViews", []), doc.get("buffers", [])
    report["generator"] = doc["asset"].get("generator")
    report["extensions_used"] = doc.get("extensionsUsed", [])
    report["extensions_required"] = doc.get("extensionsRequired", [])
    names = {}
    for i, node in enumerate(nodes):
        names.setdefault(node.get("name", ""), []).append(i)
    missing = [name for name in REQUIRED_NODES if name not in names]
    errors.extend(f"Missing required node: {name}" for name in missing)
    errors.extend(f"Ambiguous required node name: {name}" for name in REQUIRED_NODES
                  if len(names.get(name, [])) > 1)
    report["required_nodes"] = {name: names.get(name, []) for name in REQUIRED_NODES}
    material_names = [m.get("name", "") for m in materials]
    errors.extend(f"Missing required material: {name}" for name in REQUIRED_MATERIALS
                  if name not in material_names)
    for i, material in enumerate(materials):
        pbr = material.get("pbrMetallicRoughness", {})
        factors = pbr.get("baseColorFactor", [1, 1, 1, 1])
        if not finite_vector(factors, 4) or any(not 0 <= x <= 1 for x in factors):
            errors.append(f"Material {i}: invalid baseColorFactor")
        for key in ("metallicFactor", "roughnessFactor"):
            if not isinstance(pbr.get(key, 1), (int, float)) or not 0 <= pbr.get(key, 1) <= 1:
                errors.append(f"Material {i}: invalid {key}")
        emission = material.get("emissiveFactor", [0, 0, 0])
        if not finite_vector(emission, 3) or any(not 0 <= x <= 1 for x in emission):
            errors.append(f"Material {i}: invalid emissiveFactor")
        if material.get("name") in ("Headlight_Lens", "Taillight_Lens") and any(emission):
            errors.append(f"Material {i}: lamp emission must be off by default")
        if material.get("alphaMode", "OPAQUE") not in ("OPAQUE", "MASK", "BLEND"):
            errors.append(f"Material {i}: invalid alphaMode")
        if material.get("name") == "Glass" and material.get("alphaMode") != "BLEND":
            warnings.append("Glass uses a different transparency model than the original BLEND contract")
    report["materials"] = [{"name": m.get("name"),
                             "alpha_mode": m.get("alphaMode", "OPAQUE"),
                             "pbr": m.get("pbrMetallicRoughness", {}),
                             "emissive": m.get("emissiveFactor", [0, 0, 0])}
                            for m in materials]
    def valid_index(value, items):
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(items)

    for i, buffer in enumerate(buffers):
        if "uri" in buffer:
            errors.append(f"Buffer {i}: external/data URI is outside this self-contained GLB contract")
        elif i == 0 and not buffer.get("extensions", {}).get("EXT_meshopt_compression", {}).get("fallback"):
            if not 0 <= buffer.get("byteLength", -1) <= len(binary):
                errors.append(f"Buffer {i}: byteLength exceeds BIN chunk")
    for i, view in enumerate(views):
        if not valid_index(view.get("buffer"), buffers):
            errors.append(f"BufferView {i}: invalid buffer index")
            continue
        if view.get("byteOffset", 0) < 0 or view.get("byteLength", 0) <= 0:
            errors.append(f"BufferView {i}: invalid byte range")
        elif view.get("byteOffset", 0) + view["byteLength"] > buffers[view["buffer"]]["byteLength"]:
            errors.append(f"BufferView {i}: exceeds declared buffer length")
        ext = view.get("extensions", {}).get("EXT_meshopt_compression")
        if ext:
            if not valid_index(ext.get("buffer"), buffers):
                errors.append(f"BufferView {i}: invalid meshopt buffer")
            elif ext.get("byteOffset", 0) + ext.get("byteLength", 0) > buffers[ext["buffer"]]["byteLength"]:
                errors.append(f"BufferView {i}: compressed range exceeds buffer")
    for i, accessor in enumerate(accessors):
        kind, shape, count = (accessor.get(k) for k in ("componentType", "type", "count"))
        if kind not in COMPONENTS or shape not in WIDTHS or not isinstance(count, int) or count <= 0:
            errors.append(f"Accessor {i}: invalid componentType/type/count")
            continue
        if "bufferView" in accessor:
            if not valid_index(accessor["bufferView"], views):
                errors.append(f"Accessor {i}: invalid bufferView")
                continue
            view = views[accessor["bufferView"]]
            width = COMPONENTS[kind][1] * WIDTHS[shape]
            stride = view.get("byteStride", width)
            required = accessor.get("byteOffset", 0) + stride * (count - 1) + width
            if stride < width or required > view["byteLength"]:
                errors.append(f"Accessor {i}: byte range exceeds bufferView")
        if "min" in accessor or "max" in accessor:
            if not finite_vector(accessor.get("min"), WIDTHS[shape]) or not finite_vector(accessor.get("max"), WIDTHS[shape]):
                errors.append(f"Accessor {i}: invalid min/max")
            elif any(a > b for a, b in zip(accessor["min"], accessor["max"])):
                errors.append(f"Accessor {i}: minimum exceeds maximum")
    decoded = {}
    def decode_accessor(index):
        if index in decoded:
            return decoded[index]
        accessor = accessors[index]
        decoded[index] = None
        if "sparse" in accessor:
            warnings.append("Sparse accessor binary payloads are not decoded")
            return None
        if not valid_index(accessor.get("bufferView"), views):
            return None
        view = views[accessor["bufferView"]]
        if view.get("extensions", {}).get("EXT_meshopt_compression"):
            return None
        if view["buffer"] != 0 or buffers[0].get("uri"):
            return None
        kind, size = COMPONENTS[accessor["componentType"]]
        width = WIDTHS[accessor["type"]]
        stride = view.get("byteStride", size * width)
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        unpack = struct.Struct("<" + kind * width)
        decoded[index] = [unpack.unpack_from(binary, offset + i * stride)
                          for i in range(accessor["count"])]
        return decoded[index]
    parents, children, local = {}, {}, {}
    for i, node in enumerate(nodes):
        try:
            local[i] = matrix(node)
        except ValueError as exc:
            errors.append(f"Node {i}: {exc}")
            local[i] = IDENTITY
        children[i] = []
        for child in node.get("children", []):
            if not valid_index(child, nodes):
                errors.append(f"Node {i}: invalid child index {child}")
            elif child in parents:
                errors.append(f"Node {child}: multiple parents/duplicate child reference")
            else:
                parents[child] = i
                children[i].append(child)
        if "mesh" in node and not valid_index(node["mesh"], meshes):
            errors.append(f"Node {i}: invalid mesh index")
    scenes = doc.get("scenes", [])
    selected = doc.get("scene", 0)
    if not valid_index(selected, scenes):
        errors.append("Missing/invalid default scene")
        return
    roots = scenes[selected].get("nodes", [])
    world, active, visiting = {}, set(), set()
    def walk(i, parent_matrix):
        if not valid_index(i, nodes):
            errors.append(f"Scene contains invalid node index {i}")
            return
        if i in visiting:
            errors.append(f"Node hierarchy cycle at {i}")
            return
        if i in active:
            errors.append(f"Node {i}: repeated in active scene")
            return
        visiting.add(i)
        active.add(i)
        world[i] = multiply(parent_matrix, local[i])
        for child in children[i]:
            walk(child, world[i])
        visiting.remove(i)
    for root in roots:
        if root in parents:
            errors.append(f"Scene root {root} also has a parent")
        walk(root, IDENTITY)
    # Check detached hierarchy cycles too, even when absent from the default scene.
    for i in range(len(nodes)):
        seen, parent = set(), i
        while parent in parents:
            if parent in seen:
                errors.append(f"Node hierarchy cycle including {parent}")
                break
            seen.add(parent)
            parent = parents[parent]
    errors.extend(f"Required node is absent from active scene: {name}" for name in REQUIRED_NODES
                  if name in names and names[name][0] not in active)
    def descendants(i):
        result, pending = set(), list(children.get(i, []))
        while pending:
            child = pending.pop()
            if child not in result:
                result.add(child)
                pending.extend(children.get(child, []))
        return result
    for corner in ("FL", "FR", "RL", "RR"):
        wheel = names.get(f"Wheel_{corner}", [])
        if wheel:
            family = descendants(wheel[0])
            for prefix in ("Tire", "Rim"):
                expected = f"{prefix}_{corner}"
                if not any(i in family for i in names.get(expected, [])):
                    errors.append(f"Wheel_{corner}: missing descendant {expected}")
    primitives, mesh_stats, position_ids = [], {}, set()
    for i, mesh in enumerate(meshes):
        if not mesh.get("primitives"):
            errors.append(f"Mesh {i}: no primitives")
        mesh_stats[i] = {"vertices": 0, "triangles": 0, "primitives": 0}
        for j, primitive in enumerate(mesh.get("primitives", [])):
            label = f"Mesh {i} primitive {j}"
            pos = primitive.get("attributes", {}).get("POSITION")
            if not valid_index(pos, accessors):
                errors.append(f"{label}: missing/invalid POSITION")
                continue
            accessor = accessors[pos]
            if accessor.get("type") != "VEC3" or accessor.get("count", 0) <= 0:
                errors.append(f"{label}: POSITION must be non-empty VEC3")
                continue
            if not finite_vector(accessor.get("min"), 3) or not finite_vector(accessor.get("max"), 3):
                errors.append(f"{label}: POSITION requires finite min/max")
                continue
            position_ids.add(pos)
            raw_positions = decode_accessor(pos)
            if raw_positions is not None:
                if any(not math.isfinite(v) for row in raw_positions for v in row):
                    errors.append(f"{label}: non-finite vertex position")
                else:
                    for axis in range(3):
                        actual_lo = min(row[axis] for row in raw_positions)
                        actual_hi = max(row[axis] for row in raw_positions)
                        tolerance = max(1e-5, abs(actual_lo) * 1e-5, abs(actual_hi) * 1e-5)
                        if abs(actual_lo - accessor["min"][axis]) > tolerance or abs(actual_hi - accessor["max"][axis]) > tolerance:
                            errors.append(f"{label}: POSITION metadata does not match decoded bounds")
                            break
            index_id = primitive.get("indices")
            if index_id is not None and not valid_index(index_id, accessors):
                errors.append(f"{label}: invalid indices accessor")
                continue
            index_accessor = accessors[index_id] if index_id is not None else None
            count = index_accessor["count"] if index_accessor else accessor["count"]
            if index_accessor and (index_accessor["type"] != "SCALAR" or index_accessor["componentType"] not in (5121, 5123, 5125)):
                errors.append(f"{label}: invalid indices format")
            if index_id is not None:
                indices = decode_accessor(index_id)
                if indices is not None and any(row[0] >= accessor["count"] for row in indices):
                    errors.append(f"{label}: vertex index is out of bounds")
            mode = primitive.get("mode", 4)
            triangles = count // 3 if mode == 4 else max(0, count - 2) if mode in (5, 6) else 0
            if mode == 4 and count % 3:
                errors.append(f"{label}: TRIANGLES count is not divisible by 3")
            if not triangles:
                errors.append(f"{label}: no triangle geometry")
            if not valid_index(primitive.get("material"), materials):
                errors.append(f"{label}: missing/invalid PBR material")
            if "NORMAL" not in primitive.get("attributes", {}):
                warnings.append("Some primitives have no NORMAL attribute; renderer-generated normals may appear faceted")
            if primitive.get("targets"):
                warnings.append("Morph target deformation is not included in bounds")
            mesh_stats[i]["vertices"] += accessor["count"]
            mesh_stats[i]["triangles"] += triangles
            mesh_stats[i]["primitives"] += 1
            primitives.append((i, pos))
    per_node = {}
    for i in active:
        mesh_id = nodes[i].get("mesh")
        if mesh_id is not None and mesh_id in mesh_stats:
            per_node[i] = [transformed_bounds(accessors[p], world[i]) for m, p in primitives if m == mesh_id]
    node_bounds = {}
    for name in REQUIRED_NODES:
        if name in names:
            family = {names[name][0]} | descendants(names[name][0])
            node_bounds[name] = merge_bounds([b for i in family for b in per_node.get(i, [])])
            if node_bounds[name] is None:
                errors.append(f"Required node has no renderable geometry: {name}")
    report["node_bounds"] = node_bounds
    report["bounds"] = merge_bounds([b for values in per_node.values() for b in values])
    if report["bounds"] is None or min(report["bounds"]["size"]) <= 0:
        errors.append("Scene has empty/degenerate world bounds")
    head, tail = node_bounds.get("Headlight_L"), node_bounds.get("Taillight_L")
    if head and tail and head["center"][2] <= tail["center"][2]:
        errors.append("Orientation contract: headlights must face the +Z end of the car")
    for corner in ("FL", "FR", "RL", "RR"):
        bounds = node_bounds.get(f"Wheel_{corner}")
        if bounds and bounds["center"][0] * (1 if corner.endswith("L") else -1) <= 0:
            errors.append(f"Wheel_{corner}: left/right position contradicts the +X-left contract")
    active_meshes = [nodes[i]["mesh"] for i in active if "mesh" in nodes[i] and nodes[i]["mesh"] in mesh_stats]
    report["counts"] = {"nodes": len(nodes), "active_nodes": len(active),
                        "meshes": len(meshes), "materials": len(materials),
                        "unique_position_vertices": sum(accessors[i]["count"] for i in position_ids),
                        "mesh_primitive_vertices": sum(s["vertices"] for s in mesh_stats.values()),
                        "mesh_triangles": sum(s["triangles"] for s in mesh_stats.values()),
                        "scene_vertices": sum(mesh_stats[i]["vertices"] for i in active_meshes),
                        "scene_triangles": sum(mesh_stats[i]["triangles"] for i in active_meshes),
                        "scene_primitives": sum(mesh_stats[i]["primitives"] for i in active_meshes)}
    report["hierarchy"] = {"default_scene": selected, "roots": roots,
                           "unreferenced_nodes": sorted(set(range(len(nodes))) - active)}
    report["payload_audit"] = {"decoded_accessors": sorted(i for i, data in decoded.items() if data is not None),
                               "metadata_only_accessors": sorted(i for i, data in decoded.items() if data is None)}
    if doc.get("skins") or doc.get("animations"):
        warnings.append("Skins/animations are present; only static node transforms were audited")
    if doc.get("images"):
        warnings.append("Texture image payloads and external image URIs are not decoded or fetched")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("glb", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.glb.read_bytes(), args.glb.resolve())
    except OSError as exc:
        report = {"path": str(args.glb), "valid": False, "errors": [str(exc)]}
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
