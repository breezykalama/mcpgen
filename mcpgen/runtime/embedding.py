import hashlib
import math
import os
import re
from functools import lru_cache
from typing import Any

LOCAL_EMBEDDING_DIMENSIONS = 64
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


def generate_tool_embeddings(tools: list) -> list:
    """Generate embedding records for generated tools."""
    return [
        {
            "tool_name": get_tool_value(tool, "name"),
            "text": build_tool_text(tool),
            "embedding": embed_text(build_tool_text(tool)),
        }
        for tool in tools
    ]


def embed_query(query: str) -> list[float]:
    return embed_text(query)


def cosine_similarity(vec1, vec2) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot = sum(left * right for left, right in zip(vec1, vec2))
    norm1 = math.sqrt(sum(value * value for value in vec1))
    norm2 = math.sqrt(sum(value * value for value in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def embed_text(text: str) -> list[float]:
    if os.getenv("MCPGEN_EMBEDDING_BACKEND") != "sentence-transformers":
        return local_embedding(text)

    try:
        return sentence_transformer_embedding(text)
    except Exception:
        return local_embedding(text)


@lru_cache(maxsize=1)
def load_sentence_transformer():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(DEFAULT_MODEL_NAME)


def sentence_transformer_embedding(text: str) -> list[float]:
    model = load_sentence_transformer()
    embedding = model.encode(text, normalize_embeddings=True)
    return [float(value) for value in embedding.tolist()]


def local_embedding(text: str) -> list[float]:
    vector = [0.0] * LOCAL_EMBEDDING_DIMENSIONS
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % LOCAL_EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def build_tool_text(tool: Any) -> str:
    parts = [
        get_tool_value(tool, "name"),
        get_tool_value(tool, "description"),
    ]
    tags = get_tool_value(tool, "tags") or []
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)
    return " ".join(part for part in parts if part).strip()


def get_tool_value(tool: Any, key: str):
    if isinstance(tool, dict):
        return tool.get(key)
    return getattr(tool, key, None)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())
