import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.benchmark import _rank_for_expected, run_benchmark
from app.config import get_settings, ensure_structure
from app.db import Database
from app.extractors import extract_sections, chunk_sections
from app.retrieval import index_one, local_rerank_score, search
from app.sources import read_source_fragment, resolve_source_path


class StructuralChunkingTests(unittest.TestCase):
    def test_markdown_splits_by_headings_and_keeps_locator(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "note.md"
            p.write_text("# Uno\nTexto A\n\n## Dos\nTexto B", encoding="utf-8")
            sections = extract_sections(p)
            self.assertEqual(len(sections), 2)
            self.assertIn('sección "Uno"', sections[0]["locator"])
            self.assertIn('sección "Dos"', sections[1]["locator"])
            chunks = chunk_sections(sections, 400, 50)
            self.assertTrue(chunks[0]["text"].lower().startswith("# uno") or "uno" in chunks[0]["text"].lower())

    def test_source_fragment_uses_line_locator(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "note.md"
            p.write_text("a\nb\nc\nd\n", encoding="utf-8")
            text = read_source_fragment(p, "líneas 2-3")
            self.assertEqual(text, "b\nc")


class RerankerTests(unittest.TestCase):
    def test_title_and_phrase_improve_local_rerank(self):
        query = "recuperacion bitlocker"
        strong = {
            "title": "BitLocker recuperación.md",
            "locator": "sección recuperación",
            "text": "La recuperación BitLocker usa una clave de recuperación.",
        }
        weak = {
            "title": "Otro.md",
            "locator": "página 1",
            "text": "Documento general sobre cifrado de discos.",
        }
        self.assertGreater(local_rerank_score(query, strong), local_rerank_score(query, weak))

    def test_rank_metric(self):
        items = [{"path": "a.md"}, {"path": "b.md"}]
        self.assertEqual(_rank_for_expected(items, ["b.md"]), 2)
        self.assertIsNone(_rank_for_expected(items, ["c.md"]))


class RetrievalIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "brain"
        env = {
            "BRAIN_ROOT": str(self.root),
            "CHAT_PROVIDER": "ollama",
            "EMBEDDING_PROVIDER": "none",
            "INDEX_DIRS": "00_RAW,10_WIKI,20_PROJECTS,40_MEMORY",
            "AUTO_INDEX": "false",
            "RAG_RERANKER": "local",
            "RAG_RERANK_WEIGHT": "0.30",
        }
        self.env_patch = patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.settings = get_settings()
        ensure_structure(self.settings)
        self.db = Database(self.root / "90_SYSTEM/database/test.db")

    async def asyncTearDown(self):
        self.env_patch.stop()
        self.tmp.cleanup()

    async def test_structural_locator_survives_index_and_search(self):
        p = self.root / "10_WIKI" / "BitLocker.md"
        p.write_text(
            "# Introducción\nCifrado.\n\n## Recuperación\nLa clave de recuperación BitLocker desbloquea la unidad.",
            encoding="utf-8",
        )
        await index_one(self.db, self.settings, p)
        hits = await search(self.db, self.settings, "recuperación BitLocker", top_k=3)
        self.assertTrue(hits)
        self.assertIn("sección", hits[0]["locator"])
        self.assertIsNotNone(hits[0].get("rerank"))

    async def test_source_path_rejects_non_index_area(self):
        out = self.root / "50_OUTPUT" / "Documents" / "secret.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("x", encoding="utf-8")
        with self.assertRaises(ValueError):
            resolve_source_path(self.settings, "50_OUTPUT/Documents/secret.md")

    async def test_benchmark_calculates_hit_rate_and_mrr(self):
        p = self.root / "10_WIKI" / "Memoria.md"
        p.write_text("# Memoria\nLa memoria persistente se aprueba de forma controlada.", encoding="utf-8")
        await index_one(self.db, self.settings, p)
        result = await run_benchmark(
            self.db,
            self.settings,
            [{"query": "memoria persistente controlada", "expected_paths": ["10_WIKI/Memoria.md"]}],
            top_k=3,
        )
        self.assertEqual(result["queries"], 1)
        self.assertEqual(result["hit_rate"], 1.0)
        self.assertEqual(result["mrr"], 1.0)


if __name__ == "__main__":
    unittest.main()
