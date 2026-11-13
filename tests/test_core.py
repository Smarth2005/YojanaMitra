from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api import create_app
from src.ingest import chunk_text, parse_sections
from src.rag import RAGPipeline, classify_query
from src.retriever import RetrievedChunk


def test_pdf_sections_from_observed_headings() -> None:
    sections = parse_sections("Scheme X Details intro Benefits money Eligibility age Documents Required id Application Process online")
    assert sections["Benefits"] == "money"
    assert sections["Eligibility"] == "age"
    assert sections["Documents Required"] == "id"


def test_chunking_has_overlap() -> None:
    chunks = chunk_text("a" * 1700, size=800, overlap=80)
    assert len(chunks) == 3
    assert chunks[0][-80:] == chunks[1][:80]


def test_classification() -> None:
    assert classify_query("Compare A and B") == "comparison"
    assert classify_query("What are the eligibility and documents?") == "detail"
    assert classify_query("Schemes for women entrepreneurs") == "discovery"


def test_metadata_filter_and_state_central() -> None:
    collection = Mock()
    collection.query.return_value = {"documents": [["x"]], "metadatas": [[{"scheme_name": "A"}]], "distances": [[0.1]]}
    embedder = Mock()
    embedder.encode.return_value = [[0.1]]
    from src.retriever import Retriever
    Retriever(collection=collection, embedder=embedder).search("q", state="Punjab")
    where = collection.query.call_args.kwargs["where"]
    assert where == {"$or": [{"state_or_level": "Punjab"}, {"state_or_level": "Central"}]}


def test_api_schema_and_health() -> None:
    chunk = RetrievedChunk("context", {"scheme_name": "A", "section": "Benefits", "source_url": ""}, 0.1)
    retriever = Mock()
    retriever.search.return_value = [chunk]
    client = TestClient(create_app(RAGPipeline(retriever, generator=Mock(return_value="answer"))))
    assert client.get("/health").json() == {"status": "ok"}
    response = client.post("/api/ask", json={"question": "Tell me about a scheme"})
    assert response.status_code == 200
    assert response.json()["query_type"] == "discovery"
