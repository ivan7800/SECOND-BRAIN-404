import re
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")

def _node_id(path, root):
    return str(path.relative_to(root)).replace("\\", "/")

def build_graph(brain_root, areas=None, max_nodes=500):
    areas = areas or ("10_WIKI", "20_PROJECTS", "30_CONTEXT", "40_MEMORY")
    md_files = []
    for area in areas:
        folder = brain_root / area
        if folder.exists():
            md_files.extend(p for p in folder.rglob("*.md") if p.is_file())

    md_files = sorted(md_files)[:max_nodes]
    by_stem = {}
    nodes = []
    for path in md_files:
        nid = _node_id(path, brain_root)
        stem = path.stem
        by_stem.setdefault(stem.lower(), []).append(nid)
        nodes.append({
            "id": nid,
            "label": stem,
            "area": nid.split("/", 1)[0],
            "path": nid,
        })

    edge_keys = set()
    edges = []
    unresolved = set()

    for path in md_files:
        src = _node_id(path, brain_root)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw in WIKILINK_RE.findall(text):
            target_name = raw.strip()
            candidates = by_stem.get(Path(target_name).stem.lower(), [])
            if candidates:
                target = candidates[0]
                key = tuple(sorted((src, target)))
                if src != target and key not in edge_keys:
                    edge_keys.add(key)
                    edges.append({"source": src, "target": target, "type": "wikilink"})
            else:
                unresolved.add(target_name)

    degree = {}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1

    for node in nodes:
        node["degree"] = degree.get(node["id"], 0)

    return {
        "nodes": nodes,
        "edges": edges,
        "unresolved": sorted(unresolved)[:100],
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
