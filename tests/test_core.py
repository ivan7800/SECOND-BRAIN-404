import tempfile
import unittest
from pathlib import Path

from app.security import safe_filename, validate_upload
from app.extractors import chunk_sections
from app.graph import build_graph

class Tests(unittest.TestCase):
    def test_filename(self):
        self.assertEqual(safe_filename("../../hola.md"), "hola.md")

    def test_extension(self):
        self.assertEqual(validate_upload("nota.MD"), "nota.md")
        with self.assertRaises(ValueError):
            validate_upload("mal.exe")

    def test_chunks(self):
        chunks = chunk_sections(
            [{"text": "Frase de prueba. " * 200, "locator": "x"}],
            400,
            50,
        )
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(len(x["text"]) <= 400 for x in chunks))

    def test_graph_wikilinks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wiki = root / "10_WIKI"
            wiki.mkdir()
            (wiki / "A.md").write_text("# A\n[[B]]", encoding="utf-8")
            (wiki / "B.md").write_text("# B", encoding="utf-8")
            graph = build_graph(root)
            self.assertEqual(graph["node_count"], 2)
            self.assertEqual(graph["edge_count"], 1)

if __name__ == "__main__":
    unittest.main()
