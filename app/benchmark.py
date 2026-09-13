import json
from pathlib import Path

from .retrieval import search


def load_cases(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases", data) if isinstance(data, dict) else data
    if not isinstance(cases, list):
        raise ValueError("El benchmark debe contener una lista de casos")
    return cases


def _rank_for_expected(items, expected_paths):
    expected = set(expected_paths or [])
    for rank, item in enumerate(items, 1):
        if item.get("path") in expected:
            return rank
    return None


async def run_benchmark(db, settings, cases, top_k=5):
    details = []
    reciprocal_sum = 0.0
    hits = 0
    rank_sum = 0
    ranked_hits = 0

    for raw in cases[:50]:
        query = str(raw.get("query", "")).strip()
        expected_paths = [str(x) for x in raw.get("expected_paths", []) if str(x).strip()]
        source_areas = raw.get("source_areas") or None
        if not query or not expected_paths:
            continue
        items = await search(db, settings, query, top_k=top_k, source_areas=source_areas)
        rank = _rank_for_expected(items, expected_paths)
        hit = rank is not None
        if hit:
            hits += 1
            reciprocal_sum += 1.0 / rank
            rank_sum += rank
            ranked_hits += 1
        details.append({
            "id": raw.get("id") or f"q{len(details) + 1}",
            "query": query,
            "expected_paths": expected_paths,
            "hit": hit,
            "rank": rank,
            "top_paths": [item.get("path") for item in items],
        })

    total = len(details)
    hit_rate = hits / total if total else 0.0
    mrr = reciprocal_sum / total if total else 0.0
    mean_rank = rank_sum / ranked_hits if ranked_hits else None
    return {
        "queries": total,
        "top_k": top_k,
        "hit_rate": round(hit_rate, 4),
        "mrr": round(mrr, 4),
        "mean_rank_when_hit": round(mean_rank, 2) if mean_rank is not None else None,
        "passed": bool(total) and hit_rate >= 0.80 and mrr >= 0.65,
        "thresholds": {"hit_rate": 0.80, "mrr": 0.65},
        "details": details,
    }
