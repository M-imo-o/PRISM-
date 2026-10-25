"""Command-line runner for the standalone Google-backed L4 RAG system."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .rag import L4Config, L4Error, LocalRAG


def _load_environment() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(item for item in path.rglob("*") if item.suffix.lower() in {".pdf", ".txt", ".md"})
    raise FileNotFoundError(path)


def main() -> int:
    _load_environment()
    parser = argparse.ArgumentParser(description="Index and query PRISM's local L4 RAG store.")
    parser.add_argument("path", type=Path, help="Document file or directory to index")
    parser.add_argument("--query-only", action="store_true", help="Query existing local ChromaDB data")
    parser.add_argument("--store", default=".prism/l4_chroma")
    parser.add_argument("--collection", default="prism_l4_documents")
    parser.add_argument("--embedding-model")
    parser.add_argument("--generation-model")
    parser.add_argument("--top-k", type=int, default=5)
    retrieval_group = parser.add_mutually_exclusive_group()
    retrieval_group.add_argument("--cross-document", dest="cross_document", action="store_true")
    retrieval_group.add_argument("--single-source", dest="cross_document", action="store_false")
    parser.set_defaults(cross_document=True)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--max-chunks-per-source", type=int, default=3)
    parser.add_argument("--max-total-chunks", type=int, default=8)
    parser.add_argument("--threshold", type=float)
    args = parser.parse_args()
    config = L4Config(
        persist_directory=args.store,
        collection_name=args.collection,
        embedding_model=args.embedding_model or os.environ.get(
            "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
        ),
        generation_model=args.generation_model or os.environ.get(
            "GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite"
        ),
    )
    try:
        rag = LocalRAG(config)
        if not args.query_only:
            for document in _files(args.path):
                print(f"Indexed {len(rag.chunk_and_insert(str(document)))} chunks from {document}")
        else:
            print("Using the existing local ChromaDB collection; no documents will be indexed.")
        print("Enter queries; press Ctrl+C or Ctrl+D to exit.")
        while True:
            question = input("\nQuery> ").strip()
            if not question:
                continue
            if args.cross_document:
                results = rag.query_cross_document(
                    question, args.candidate_k, args.max_chunks_per_source,
                    args.max_total_chunks, args.threshold
                )
            elif args.threshold is not None:
                results = rag.get_chunks_above_threshold_with_limit(question, args.threshold, args.top_k)
            else:
                results = rag.query(question, args.top_k)
            for index, result in enumerate(results, 1):
                print(
                    f"\n[{index}] score={result.score:.3f} "
                    f"source={result.metadata.get('source_path')} "
                    f"page={result.metadata.get('page_number', 'n/a')}\n{result.content}"
                )
            print("\nAnswer:")
            print(rag.generate(
                question, args.top_k, args.threshold, args.cross_document,
                args.candidate_k, args.max_chunks_per_source, args.max_total_chunks
            ))
    except (L4Error, FileNotFoundError, ValueError) as exc:
        print(f"L4 error: {exc}")
        return 1
    except (EOFError, KeyboardInterrupt):
        print()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
