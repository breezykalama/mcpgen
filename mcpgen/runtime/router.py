import re
from collections import Counter

from mcpgen.core.models import Tool
from mcpgen.runtime.embedding import cosine_similarity, embed_query
from mcpgen.runtime.metrics import record_metric


def select_relevant_tools(query: str, tools: list[Tool], limit: int = 5) -> list[Tool]:
    """Select relevant tools using simple keyword matching."""
    return [item["tool"] for item in rank_relevant_tools(query, tools, limit=limit)]


def rank_relevant_tools(
    query: str,
    tools: list[Tool],
    limit: int = 5,
    embeddings: list[dict] | None = None,
    routing_mode: str = "keyword",
    config: dict | None = None,
) -> list[dict]:
    """Rank tools using semantic embeddings when available, otherwise keywords."""
    if routing_mode == "semantic":
        try:
            ranked = rank_relevant_tools_semantic(query, tools, embeddings or [], limit=limit)
            record_routing_metrics(ranked, config)
            return ranked
        except Exception:
            ranked = rank_relevant_tools_keyword(query, tools, limit=limit)
            record_routing_metrics(ranked, config)
            return ranked

    ranked = rank_relevant_tools_keyword(query, tools, limit=limit)
    record_routing_metrics(ranked, config)
    return ranked


def rank_relevant_tools_semantic(query: str, tools: list[Tool], embeddings: list[dict], limit: int = 5) -> list[dict]:
    if not embeddings:
        raise ValueError("Embeddings unavailable.")

    query_embedding = embed_query(query)
    embeddings_by_name = {item["tool_name"]: item["embedding"] for item in embeddings}
    scored_tools = []

    for tool in tools:
        tool_embedding = embeddings_by_name.get(tool.name)
        if tool_embedding is None:
            continue

        score = cosine_similarity(query_embedding, tool_embedding)
        if score > 0:
            scored_tools.append(
                {
                    "tool": tool,
                    "score": score,
                    "matched_terms": [],
                    "routing_mode": "semantic",
                }
            )

    if not scored_tools:
        raise ValueError("No semantic matches.")

    scored_tools.sort(key=lambda item: (-item["score"], item["tool"].name))
    return scored_tools[:limit]


def rank_relevant_tools_keyword(query: str, tools: list[Tool], limit: int = 5) -> list[dict]:
    """Rank tools and explain why each tool matched using keywords."""
    query_terms = tokenize(query)
    if not query_terms:
        return [
            {
                "tool": tool,
                "score": 0,
                "matched_terms": [],
                "routing_mode": "keyword",
            }
            for tool in tools[:limit]
        ]

    scored_tools = []
    for tool in tools:
        searchable_text = f"{tool.name} {tool.description}"
        tool_terms = tokenize(searchable_text)
        matched_terms = sorted((query_terms & tool_terms).keys())
        score = sum((query_terms & tool_terms).values())
        if score > 0:
            scored_tools.append(
                {
                    "tool": tool,
                    "score": score,
                    "matched_terms": matched_terms,
                    "routing_mode": "keyword",
                }
            )

    scored_tools.sort(key=lambda item: (-item["score"], item["tool"].name))
    return scored_tools[:limit]


def tokenize(text: str) -> Counter[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return Counter(normalize_word(word) for word in words)


def normalize_word(word: str) -> str:
    if len(word) > 3 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def record_routing_metrics(ranked_tools: list[dict], config: dict | None) -> None:
    if config is None:
        return

    for item in ranked_tools:
        tool = item["tool"]
        record_metric(
            {
                "action": "tool_routed",
                "tool_name": tool.name,
                "routing_mode": item.get("routing_mode", config.get("routing_mode", "keyword")),
            },
            config,
        )
