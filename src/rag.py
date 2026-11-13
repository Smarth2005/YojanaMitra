"""Query classification, profile extraction, retrieval, and answer generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .llm import generate
from .config import RETRIEVAL_DISTANCE_THRESHOLD
from .retriever import RetrievedChunk, Retriever


@dataclass(frozen=True)
class RAGResult:
    answer: str
    sources: list[RetrievedChunk]
    query_type: str


def classify_query(question: str) -> str:
    lowered = question.lower()
    if "compare" in lowered or "difference" in lowered or "versus" in lowered or " vs " in lowered:
        return "comparison"
    if any(word in lowered for word in ("eligibility", "benefits", "documents", "application process", "how do i apply")):
        return "detail"
    return "discovery"


def extract_profile(question: str) -> dict[str, str]:
    profile: dict[str, str] = {}
    age = re.search(r"\b(\d{1,3})[- ]?year[- ]?old\b", question, re.I)
    state = re.search(r"\bfrom ([A-Za-z ]+?)(?:[,.]|$)", question, re.I)
    if age:
        profile["age"] = age.group(1)
    if state:
        profile["state"] = state.group(1).strip()
    for value in ("student", "farmer", "entrepreneur", "startup", "unemployed", "women", "woman"):
        if value in question.lower():
            profile["occupation" if value not in {"women", "woman"} else "gender"] = value
    return profile


def _context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[Source: {chunk.metadata.get('source_document', chunk.metadata.get('source_file', ''))}, "
        f"Page {chunk.metadata.get('page_number', 1)}; "
        f"Scheme metadata: state_or_level={chunk.metadata.get('state_or_level', '')}, "
        f"category={chunk.metadata.get('category', '')}]\n{chunk.text}"
        for chunk in chunks[:5]
    )


def _diverse_discovery_chunks(
    retriever: Retriever, question: str, state: str | None
) -> list[RetrievedChunk]:
    candidates = retriever.search(question, top_k=15, state=state)
    selected: list[RetrievedChunk] = []
    seen_schemes: set[str] = set()
    for chunk in candidates:
        scheme = str(chunk.metadata.get("scheme_name", "")).strip().lower()
        if scheme and scheme not in seen_schemes:
            selected.append(chunk)
            seen_schemes.add(scheme)
        if len(selected) == 5:
            break
    return selected or candidates[:5]


class RAGPipeline:
    def __init__(self, retriever: Retriever, generator: Any = generate):
        self.retriever = retriever
        self.generator = generator

    def answer(self, question: str, profile: dict[str, Any] | None = None) -> RAGResult:
        query_type = classify_query(question)
        profile = {**extract_profile(question), **(profile or {})}
        if query_type == "comparison":
            names = re.findall(r"(?:compare|between)\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)(?:[?.]|$)", question, re.I)
            if not names:
                return RAGResult("Please provide the two scheme names to compare.", [], query_type)
            if not profile:
                return RAGResult("Please provide your profile (age, state, occupation, and gender) so I can assess which scheme you may qualify for.", [], query_type)
            chunks = self.retriever.search(question, top_k=5)
        elif query_type == "detail":
            chunks = self.retriever.search(
                question, top_k=5, sections=["Eligibility", "Benefits", "Documents Required", "Application Process"]
            )
        else:
            chunks = _diverse_discovery_chunks(
                self.retriever, question, profile.get("state")
            )
        chunks = [
            chunk
            for chunk in chunks
            if chunk.distance <= RETRIEVAL_DISTANCE_THRESHOLD
        ]
        if not chunks:
            return RAGResult(
                "Insufficient official policy evidence",
                [],
                query_type,
            )
        prompt = (
            f"Question: {question}\nProfile: {profile}\n"
            "For discovery questions, treat retrieved Central schemes as nationwide "
            "schemes that may apply in the user's state. List relevant Central schemes "
            "even when the state name is not repeated in their text. Clearly distinguish "
            "state-specific evidence from nationwide evidence and do not claim certainty. "
            "The retrieved candidate scheme names are: "
            + ", ".join(sorted({chunk.metadata.get("scheme_name", "") for chunk in chunks}))
            + ". If any candidate matches the user's topic, mention it instead of saying "
            "that no schemes were retrieved.\n"
            "Cite every factual claim using [Document Name, Page X]. "
            "If the context does not support a claim, say it is unavailable.\n"
            f"Retrieved context:\n{_context(chunks)}"
        )
        return RAGResult(self.generator(prompt), chunks, query_type)
