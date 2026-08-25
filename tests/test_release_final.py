import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import get_settings, ensure_structure
from app.db import Database
from app.retrieval import _fts_query, index_one, search, reconcile_missing
from app.security import ensure_inside, validate_upload


class ConfigAndSecurityTests(unittest.TestCase):
    def test_chat_provider_new_variable_wins(self):
        with patch.dict(os.environ, {"CHAT_PROVIDER": "gemini", "AI_PROVIDER": "openai"}, clear=False):
            self.assertEqual(get_settings().chat_provider, "gemini")

    def test_legacy_ai_provider_is_supported(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "openai"}, clear=False):
            with patch.dict(os.environ, {}, clear=False):
                old = os.environ.pop("CHAT_PROVIDER", None)
                try:
                    self.assertEqual(get_settings().chat_provider, "openai")
                finally:
                    if old is not None:
                        os.environ["CHAT_PROVIDER"] = old

    def test_embedding_provider_can_be_disabled(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "none"}, clear=False):
            self.assertEqual(get_settings().embedding_provider, "none")

    def test_structure_is_created(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"BRAIN_ROOT": td}, clear=False):
                settings = get_settings()
                ensure_structure(settings)
                self.assertTrue((Path(td) / "00_RAW/INBOX").is_dir())
                self.assertTrue((Path(td) / "90_SYSTEM/database").is_dir())

    def test_ensure_inside_rejects_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "brain"
            root.mkdir()
            with self.assertRaises(ValueError):
                ensure_inside(root, root / ".." / "outside.txt")

    def test_upload_extension_allowlist(self):
        self.assertEqual(validate_upload("Informe.PDF"), "Informe.pdf")
        with self.assertRaises(ValueError):
            validate_upload("payload.html")

    def test_fts_query_is_bounded(self):
        query = " ".join(f"token{i}" for i in range(30))
        self.assertEqual(_fts_query(query).count(" OR "), 11)


class RetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "brain"
        env = {
            "BRAIN_ROOT": str(self.root),
            "CHAT_PROVIDER": "ollama",
            "EMBEDDING_PROVIDER": "none",
            "INDEX_DIRS": "00_RAW,10_WIKI,20_PROJECTS,40_MEMORY",
            "AUTO_INDEX": "false",
        }
        self.env_patch = patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.settings = get_settings()
        ensure_structure(self.settings)
        self.db = Database(self.root / "90_SYSTEM/database/test.db")

    async def asyncTearDown(self):
        self.env_patch.stop()
        self.tmp.cleanup()

    async def test_index_and_lexical_search_work_without_embeddings(self):
        p = self.root / "10_WIKI" / "BitLocker.md"
        p.write_text("# BitLocker\nLa clave de recuperación permite desbloquear una unidad protegida.", encoding="utf-8")
        changed, embed_failed = await index_one(self.db, self.settings, p)
        self.assertTrue(changed)
        self.assertTrue(embed_failed)
        hits = await search(self.db, self.settings, "clave recuperación BitLocker")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["path"], "10_WIKI/BitLocker.md")
        self.assertEqual(self.db.stats()["vectors"], 0)

    async def test_unchanged_document_is_skipped_even_when_embeddings_disabled(self):
        p = self.root / "10_WIKI" / "Docker.md"
        p.write_text("# Docker\nContenedores locales.", encoding="utf-8")
        first = await index_one(self.db, self.settings, p)
        second = await index_one(self.db, self.settings, p)
        self.assertEqual(first, (True, True))
        # Se intenta completar embeddings faltantes; al estar desactivados, no reescribe el documento.
        self.assertEqual(second, (False, True))
        self.assertEqual(self.db.stats()["documents"], 1)

    async def test_reconcile_removes_deleted_source(self):
        p = self.root / "10_WIKI" / "Temporal.md"
        p.write_text("contenido temporal indexable", encoding="utf-8")
        await index_one(self.db, self.settings, p)
        p.unlink()
        removed = reconcile_missing(self.db, self.settings)
        self.assertEqual(removed, 1)
        self.assertEqual(self.db.stats()["documents"], 0)


if __name__ == "__main__":
    unittest.main()
