#!/usr/bin/env python
"""Download the configured sentence-transformers model into the local cache.

This is the explicit opt-in step for semantic search. Local Knowledge Engine
never downloads a model as a side effect of indexing or searching.

Usage:
    cd backend
    .venv/Scripts/python.exe ../scripts/download_embedding_model.py
    # optional:
    .venv/Scripts/python.exe ../scripts/download_embedding_model.py --model BAAI/bge-small-en-v1.5
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Hugging Face model id (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--cache",
        default=None,
        help="Optional HF_HOME/cache directory (default: Hugging Face default)",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Print the expected download size and exit",
    )
    args = parser.parse_args()

    if args.cache:
        os.environ["HF_HOME"] = args.cache

    from app.embeddings.engine import EmbeddingEngine

    engine = EmbeddingEngine(model_name=args.model)
    print(f"Model: {args.model}")
    print(f"Estimated download: ~{engine.storage_estimate_mb} MB")
    if args.estimate_only:
        return 0

    try:
        from sentence_transformers import SentenceTransformer

        print("Downloading/loading model. This requires internet access the first time…")
        SentenceTransformer(args.model, device="cpu")
    except ImportError:
        print(
            "sentence-transformers is not installed. Run:\n"
            "  pip install sentence-transformers",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        print(f"Could not download the model: {exc}", file=sys.stderr)
        return 1

    print("Done. The model is cached locally; enable semantic search in Settings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
