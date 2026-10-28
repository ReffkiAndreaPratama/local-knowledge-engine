"""Local embedding engine with lazy loading and graceful degradation.

No model is downloaded silently: the engine reports that a download is
required and refuses to proceed until the user opts in via settings.
"""
from __future__ import annotations

import os
from typing import Iterable

import numpy as np

from app.core.config import settings


class EmbeddingUnavailable(RuntimeError):
    """Raised when embeddings cannot be produced."""


class EmbeddingEngine:
    """Wraps a sentence-transformers model."""

    _instance: "EmbeddingEngine | None" = None
    _model = None

    def __init__(self, model_name: str | None = None, device: str | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE

    @classmethod
    def get_instance(cls) -> "EmbeddingEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- availability -----------------------------------------------------
    @property
    def is_loaded(self) -> bool:
        return EmbeddingEngine._model is not None

    @property
    def storage_estimate_mb(self) -> int:
        """Rough on-disk size of the default model, for user messaging."""
        estimates = {
            "sentence-transformers/all-MiniLM-L6-v2": 90,
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 470,
            "BAAI/bge-small-en-v1.5": 130,
        }
        return estimates.get(self.model_name, 200)

    def ensure_available(self, allow_download: bool = False) -> None:
        """Check whether the model can be loaded without a silent download."""
        if self.is_loaded or allow_download:
            return

        if not settings.ENABLE_SEMANTIC_SEARCH:
            raise EmbeddingUnavailable(
                "Semantic search is disabled. Enable it in settings to use embeddings."
            )

        if not _is_model_cached(self.model_name):
            raise EmbeddingUnavailable(
                f"Embedding model '{self.model_name}' is not downloaded "
                f"(~{self.storage_estimate_mb} MB). Confirm the download in settings first."
            )

    def load_model(self, allow_download: bool = False):
        """Load (or download) the model.

        Downloads only happen when the caller explicitly passes
        ``allow_download=True``. The HTTP API never does this implicitly.
        """
        if EmbeddingEngine._model is not None:
            return EmbeddingEngine._model
        self.ensure_available(allow_download=allow_download)
        return self._load()

    # -- inference --------------------------------------------------------
    def _load(self):
        if EmbeddingEngine._model is not None:
            return EmbeddingEngine._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingUnavailable(
                "sentence-transformers is not installed"
            ) from exc

        try:
            EmbeddingEngine._model = SentenceTransformer(
                self.model_name, device=self.device
            )
        except Exception as exc:
            raise EmbeddingUnavailable(f"Cannot load embedding model: {exc}") from exc

        return EmbeddingEngine._model

    def embed(self, texts: Iterable[str]) -> np.ndarray:
        """Return L2-normalised embeddings for the given texts."""
        texts = [t for t in texts if t and t.strip()]
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)

        model = self._load()
        vectors = model.encode(
            texts,
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        vectors = self.embed([query])
        if vectors.shape[0] == 0:
            raise EmbeddingUnavailable("Empty query")
        return vectors[0]


def _is_model_cached(model_name: str) -> bool:
    """Best-effort check for a locally cached HuggingFace model."""
    cache_home = os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE")
    candidates = []
    if cache_home:
        candidates.append(os.path.join(cache_home, "hub"))
    candidates.append(
        os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    )

    folder = "models--" + model_name.replace("/", "--")
    for base in candidates:
        if os.path.isdir(os.path.join(base, folder)):
            return True
    return False
