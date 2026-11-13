"""Query classification, profile extraction, retrieval, and answer generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .llm import generate
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
    return "\n\n".join(chunk.text for chunk in chunks[:5])


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
            chunks = self.retriever.search(question, top_k=5, state=profile.get("state"))
        prompt = f"Question: {question}\nProfile: {profile}\nRetrieved context:\n{_context(chunks)}"
        return RAGResult(self.generator(prompt), chunks, query_type)
