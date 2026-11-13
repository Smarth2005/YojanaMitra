# 🇮🇳 YojanaMitra (योजना मित्र)

> **🔎 Find government schemes. 📚 Understand eligibility. ✅ Apply with confidence.**

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,fastapi,streamlit,docker,githubactions,pytorch,prometheus,grafana&perline=8" alt="YojanaMitra technology stack" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tests-5%20passing-2ea44f" alt="5 tests passing" />
</p>

YojanaMitra is a retrieval-augmented government-scheme finder for Indian citizens. It retrieves text from scheme PDFs and answers with citations rather than relying on unsupported model memory.

## 🏗️ Architecture

```mermaid
flowchart LR
  PDFs[HF gov_myscheme PDFs] --> Parse[pypdf section parser]
  Parse --> Embed[all-MiniLM-L6-v2]
  Embed --> Chroma[(Persistent ChromaDB)]
  User[Streamlit] --> API[FastAPI]
  API --> Retrieve[Filtered semantic retrieval]
  Retrieve --> LLM[OpenAI-compatible LLM]
  LLM --> API
```

## 🚀 Setup

Use Python 3.11 and a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\download_data.py
python -m src.ingest --subset 50
uvicorn src.api:app --reload
streamlit run ui.py
```

The current sample inspection observed `Details`, `Benefits`, `Eligibility`, `Exclusions`, `Application Process`, `Documents Required`, `Frequently Asked Questions`, and `Sources And References` headings. The parser chunks each section at approximately 800 characters with overlap.

## 💬 Ask a question

Start the API and UI in separate terminals:

```powershell
uvicorn src.api:app --reload
streamlit run ui.py
```

Open **http://localhost:8501** and ask questions such as:

> I am a 21-year-old student from Punjab. Which scholarships can I apply for?

## 🤖 LLM providers

Set only environment variables in `.env`: `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`. Groq is the default endpoint; Gemini's OpenAI-compatible endpoint and Ollama work by changing these values. No model or key is hardcoded.

## 🔌 API

`POST /api/ask` accepts `{"question":"...", "profile":{"age":21,"state":"Punjab"}}`. It returns an answer, retrieved sources, query type, and latency. `GET /health` and `GET /metrics` are also available.

## 📊 Evaluation

Run `python eval/run_eval.py`. It prints and saves the measured hit rate in `eval/results.json`; no result is claimed here until it is run against the indexed Chroma database.

## 🧭 Design decisions and limitations

Section-based chunks preserve the meaning of eligibility and benefits. State filtering includes the requested state **or Central** because national schemes apply across states. The provider-agnostic client avoids coupling retrieval to one vendor. Known failure cases include OCR-poor PDFs, ambiguous scheme names, stale source data, and rate-limited free LLM endpoints. The assistant asks for a profile before comparison qualification and always advises official verification.

Data source: myscheme.gov.in via the shrijayan/gov_myscheme dataset.

## 🐳 Docker

```powershell
docker compose up -d
docker compose --profile monitoring up -d
```

The monitoring profile provides Prometheus at **http://localhost:9090** and Grafana at **http://localhost:3000**.
