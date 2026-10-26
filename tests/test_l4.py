import tempfile
import unittest
from pathlib import Path

from prism.deciders.rag import ChunkResult, LocalRAG, _cosine_similarity, _split_text


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def embed_query(self, text):
        return [float(len(text)), 1.0]


class FakeGeneration:
    def __init__(self):
        self.prompt = None

    def generate(self, prompt):
        self.prompt = prompt
        return "grounded answer"


class FakeCollection:
    def __init__(self):
        self.rows = {}

    def upsert(self, ids, documents, metadatas, embeddings):
        self.rows.update(
            {key: (document, metadata, embedding) for key, document, metadata, embedding in zip(ids, documents, metadatas, embeddings)}
        )

    def query(self, embedding, top_k):
        rows = list(self.rows.values())[:top_k]
        return {
            "documents": [[row[0] for row in rows]],
            "metadatas": [[row[1] for row in rows]],
            "distances": [[0.0 for row in rows]],
        }

    def remove_stale(self, source_path, current_ids):
        stale_ids = [
            key for key, value in self.rows.items()
            if value[1].get("source_path") == source_path and key not in current_ids
        ]
        self.delete(stale_ids)

    def get(self, where, include):
        matching = [
            (key, value)
            for key, value in self.rows.items()
            if value[1].get("source_path") == where["source_path"]
        ]
        return {"ids": [key for key, _ in matching], "metadatas": [value[1] for _, value in matching]}

    def delete(self, ids):
        for key in ids:
            self.rows.pop(key, None)


class L4Tests(unittest.TestCase):
    def test_cosine_distance_is_normalized(self):
        self.assertEqual(_cosine_similarity(0), 1.0)
        self.assertEqual(_cosine_similarity(1), 0.0)
        self.assertEqual(_cosine_similarity(2), 0.0)

    def test_chunking_bounds_and_overlap(self):
        chunks = _split_text("one. " * 100, size=40, overlap=5)
        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 40 for chunk in chunks))

    def test_insert_preserves_source_metadata_and_generation_context(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.md"
            path.write_text("A useful local fact.", encoding="utf-8")
            generation = FakeGeneration()
            rag = LocalRAG(
                embedding_provider=FakeEmbeddings(),
                generation_provider=generation,
                storage=FakeCollection(),
            )
            self.assertEqual(len(rag.chunk_and_insert(str(path))), 1)
            result = rag.query("local fact")[0]
            self.assertEqual(result.score, 1.0)
            self.assertEqual(result.metadata["source_path"], str(path.resolve()))
            self.assertEqual(rag.generate("local fact"), "grounded answer")
            self.assertIn("A useful local fact.", generation.prompt)
            self.assertIn(str(path.resolve()), generation.prompt)

    def test_reindex_removes_stale_source_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.md"
            collection = FakeCollection()
            rag = LocalRAG(embedding_provider=FakeEmbeddings(), storage=collection)
            path.write_text("old content", encoding="utf-8")
            old_ids = rag.chunk_and_insert(str(path))
            path.write_text("new content", encoding="utf-8")
            new_ids = rag.chunk_and_insert(str(path))
            self.assertNotEqual(old_ids, new_ids)
            self.assertEqual(set(collection.rows), set(new_ids))

    def test_empty_query_and_threshold_are_rejected(self):
        rag = LocalRAG(embedding_provider=FakeEmbeddings(), storage=FakeCollection())
        with self.assertRaises(ValueError):
            rag.query(" ")
        with self.assertRaises(ValueError):
            rag.get_chunks_above_threshold("query", 1.1)

    def test_cross_document_selection_balances_sources(self):
        results = [
            ChunkResult(f"a{index}", 0.90 - index / 100, {"source_path": "a.pdf"})
            for index in range(4)
        ] + [
            ChunkResult(f"b{index}", 0.80 - index / 100, {"source_path": "b.pdf"})
            for index in range(4)
        ]
        selected = LocalRAG._select_balanced(results, max_chunks_per_source=3, max_total_chunks=8)
        self.assertEqual([item.content for item in selected[:2]], ["a0", "b0"])
        self.assertEqual(sum(item.metadata["source_path"] == "a.pdf" for item in selected), 3)
        self.assertEqual(sum(item.metadata["source_path"] == "b.pdf" for item in selected), 3)

    def test_cross_document_limits_are_validated(self):
        with self.assertRaises(ValueError):
            LocalRAG._select_balanced([], max_chunks_per_source=0, max_total_chunks=8)
        with self.assertRaises(ValueError):
            LocalRAG._select_balanced([], max_chunks_per_source=3, max_total_chunks=0)


if __name__ == "__main__":
    unittest.main()
