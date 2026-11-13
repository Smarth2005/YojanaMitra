"""PDF parsing, section chunking, and persistent Chroma ingestion."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from .config import CHROMA_DIR, RAW_DATA_DIR, SUBSET_SIZE

SECTION_LABELS = (
    "Details",
    "Benefits",
    "Eligibility",
    "Exclusions",
    "Application Process",
    "Documents Required",
    "Frequently Asked Questions",
    "Sources And References",
)
_SECTION_PATTERN = re.compile(
    r"(?P<label>" + "|".join(re.escape(label) for label in SECTION_LABELS) + r")",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SchemeRecord:
    scheme_name: str
    state_or_level: str
    category: str
    sections: dict[str, str]
    section_pages: dict[str, list[int]]
    source_url: str = ""
    source_file: str = ""


def clean_text(text: str) -> str:
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _label_value(text: str, label: str, fallback: str) -> str:
    pattern = re.compile(
        rf"{re.escape(label)}\s*[:\-]?\s*(.+?)(?=(?:Details|Benefits|Eligibility|"
        rf"Exclusions|Application Process|Documents Required|Frequently Asked Questions|"
        rf"Sources And References)\b|$)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    return clean_text(match.group(1)) if match else fallback


def parse_sections(text: str) -> dict[str, str]:
    """Split extracted text using headings observed in the source PDFs."""
    normalized = clean_text(text)
    matches = list(_SECTION_PATTERN.finditer(normalized))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        label = next(
            candidate for candidate in SECTION_LABELS
            if candidate.lower() == match.group("label").lower()
        )
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        value = clean_text(normalized[start:end])
        if value:
            sections[label] = value
    if "Details" not in sections:
        sections["Details"] = normalized
    return sections


def _section_pages(page_texts: list[str]) -> dict[str, list[int]]:
    normalized_pages = [clean_text(page) for page in page_texts]
    full_text = " ".join(normalized_pages)
    page_ranges: list[tuple[int, int, int]] = []
    cursor = 0
    for page_number, page in enumerate(normalized_pages, start=1):
        page_ranges.append((cursor, cursor + len(page), page_number))
        cursor += len(page) + 1

    matches = list(_SECTION_PATTERN.finditer(full_text))
    result: dict[str, list[int]] = {}
    for index, match in enumerate(matches):
        label = next(
            candidate for candidate in SECTION_LABELS
            if candidate.lower() == match.group("label").lower()
        )
        end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)
        pages = [
            page_number
            for start, finish, page_number in page_ranges
            if match.start() < finish and end > start
        ]
        if pages:
            result[label] = pages
    return result


def parse_pdf(path: Path) -> SchemeRecord:
    page_texts = [page.extract_text() or "" for page in PdfReader(str(path)).pages]
    text = "\n".join(page_texts)
    cleaned = clean_text(text)
    sections = parse_sections(cleaned)
    section_pages = _section_pages(page_texts)
    if "Details" not in section_pages:
        section_pages["Details"] = [1]
    title_match = re.search(r"^(.{1,180}?\bScheme)\b", cleaned, re.IGNORECASE)
    title = clean_text(title_match.group(1)) if title_match else path.stem.replace("_", " ").title()
    title = re.sub(r"^(?:Back|Details|Benefits|Eligibility|Scheme)\s*", "", title).strip()
    state = next(
        (
            candidate
            for candidate in ("Andaman and Nicobar", "Punjab", "Lakshadweep", "Haryana")
            if candidate.lower() in cleaned.lower()
        ),
        "Central",
    )
    category = _label_value(cleaned, "Category", "General")
    source_url = _label_value(cleaned, "Source URL", "")
    return SchemeRecord(
        title, state, category, sections, section_pages, source_url, str(path)
    )


def chunk_text(text: str, size: int = 800, overlap: int = 80) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def record_chunks(record: SchemeRecord) -> Iterable[tuple[str, dict[str, str]]]:
    for section, text in record.sections.items():
        pages = record.section_pages.get(section, [1])
        for index, chunk in enumerate(chunk_text(text)):
            document = f"Scheme: {record.scheme_name} | Section: {section}\n{chunk}"
            chunk_id = hashlib.sha1(
                f"{record.source_file}|{section}|{index}|{chunk}".encode()
            ).hexdigest()
            yield chunk_id, {
                "document": document,
                "metadata": {
                    "scheme_name": record.scheme_name,
                    "section": section,
                    "state_or_level": record.state_or_level,
                    "category": record.category,
                    "source_url": record.source_url,
                    "source_file": record.source_file,
                    "source_document": Path(record.source_file).name,
                    "page_number": pages[0],
                    "page_numbers": ", ".join(str(page) for page in pages),
                },
            }


def _selected_files(raw_dir: Path, subset_size: int) -> list[Path]:
    files = sorted(raw_dir.rglob("*.pdf"))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in files:
        stem = re.sub(r"\s+copy$", "", path.stem, flags=re.IGNORECASE)
        if stem.lower() in seen:
            continue
        seen.add(stem.lower())
        unique.append(path)
    if not subset_size:
        return unique
    priority_terms = ("farmer", "kisan", "student", "scholar", "punjab", "agri")
    priority = [
        path for path in unique
        if any(term in path.stem.lower() for term in priority_terms)
    ]
    remainder = [path for path in unique if path not in priority]
    return (priority + remainder)[:subset_size]


def ingest(raw_dir: Path = RAW_DATA_DIR, subset_size: int = SUBSET_SIZE) -> int:
    import chromadb
    from sentence_transformers import SentenceTransformer

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection("yojanamitra")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    records = [parse_pdf(path) for path in _selected_files(raw_dir, subset_size)]
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    for record in records:
        for chunk_id, item in record_chunks(record):
            ids.append(chunk_id)
            documents.append(item["document"])
            metadatas.append(item["metadata"])
    if ids:
        embeddings = model.encode(documents, normalize_embeddings=True).tolist()
        collection.upsert(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
        )
    return len(ids)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", type=int, default=SUBSET_SIZE)
    args = parser.parse_args()
    print(f"Indexed {ingest(subset_size=args.subset)} chunks")
