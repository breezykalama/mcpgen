from mcpgen.core.models import RiskLevel, Tool
from mcpgen.runtime.embedding import cosine_similarity, embed_query, generate_tool_embeddings


def test_embedding_generation_works() -> None:
    tools = [
        Tool(
            name="create_invoice",
            description="Create invoice for customer",
            method="POST",
            path="/invoices",
            risk_level=RiskLevel.MEDIUM,
        )
    ]

    embeddings = generate_tool_embeddings(tools)

    assert embeddings[0]["tool_name"] == "create_invoice"
    assert embeddings[0]["text"] == "create_invoice Create invoice for customer"
    assert embeddings[0]["embedding"]


def test_embed_query_and_cosine_similarity_work() -> None:
    query = embed_query("invoice customer")
    same = cosine_similarity(query, query)

    assert same > 0.99
