import re
from collections import Counter

from mcpgen.core.models import Tool


def select_relevant_tools(query: str, tools: list[Tool], limit: int = 5) -> list[Tool]:
    """Select relevant tools using simple keyword matching."""
    return [item["tool"] for item in rank_relevant_tools(query, tools, limit=limit)]


def rank_relevant_tools(query: str, tools: list[Tool], limit: int = 5) -> list[dict]:
    """Rank tools and explain why each tool matched."""
    query_terms = tokenize(query)
    if not query_terms:
        return [
            {
                "tool": tool,
                "score": 0,
                "matched_terms": [],
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
