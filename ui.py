"""Premium Streamlit chat interface for YojanaMitra."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

from src.ui_components import render_scheme_cards, render_sidebar, render_sources


st.set_page_config(
    page_title="YojanaMitra · Government scheme discovery",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    :root { --ink:#14213d; --muted:#667085; --teal:#087f8c; --line:#e6e9ef; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background:#f7f8fa; color:var(--ink); }
    [data-testid="stSidebar"] { background:#101c35; border-right:0; }
    [data-testid="stSidebar"] * { color:#e7edf7; }
    [data-testid="stSidebar"] .stCaption { color:#aebbd0; }
    .brand-lockup { display:flex; gap:.7rem; align-items:center; padding:.5rem 0 1rem; }
    .brand-mark { width:36px; height:36px; border-radius:11px; display:grid;
      place-items:center; background:#4fd1c5; color:#10213e; font-weight:700; font-size:1.2rem; }
    .brand-name { font-weight:700; font-size:1.15rem; color:white; }
    .brand-subtitle { font-size:.7rem; color:#aebbd0; margin-top:.1rem; }
    .sidebar-divider { height:1px; background:#2b3a56; margin:1rem 0; }
    .sidebar-label, .section-kicker { letter-spacing:.12em; font-weight:700; font-size:.68rem; color:#8fa1bd; margin:1rem 0 .45rem; }
    .sidebar-footer { color:#8fa1bd; font-size:.72rem; margin-top:2rem; padding:.8rem 0; }
    .hero { max-width:860px; margin:3.2rem auto 1.4rem; text-align:center; }
    .eyebrow { color:var(--teal); font-weight:700; letter-spacing:.12em; font-size:.72rem; }
    .hero h1 { font-size:clamp(2rem,4vw,3.55rem); line-height:1.05; letter-spacing:-.05em; margin:.65rem 0; }
    .hero p { color:var(--muted); font-size:1.05rem; max-width:650px; margin:auto; }
    .trust-row { text-align:center; color:#667085; font-size:.8rem; margin:1.3rem 0; }
    .trust-dot { color:#16a394; font-size:1.2rem; vertical-align:middle; }
    .prompt-card { min-height:82px; padding:.9rem 1rem; border:1px solid var(--line);
      border-radius:14px; background:white; box-shadow:0 3px 14px rgba(20,33,61,.04); }
    .prompt-card strong { display:block; font-size:.88rem; color:var(--ink); margin-bottom:.25rem; }
    .prompt-card span { font-size:.78rem; color:var(--muted); }
    .scheme-card { background:#fff; border:1px solid var(--line); border-radius:15px;
      padding:1rem; min-height:185px; box-shadow:0 4px 16px rgba(20,33,61,.05); }
    .scheme-card h3 { margin:.75rem 0 .4rem; font-size:1rem; color:var(--ink); }
    .scheme-card p { color:var(--muted); font-size:.78rem; min-height:38px; }
    .scheme-card-top { display:flex; justify-content:space-between; gap:.4rem; align-items:center; }
    .status-pill { background:#e6f7f3; color:#087f71; border-radius:99px; padding:.25rem .5rem;
      font-size:.62rem; font-weight:700; letter-spacing:.04em; }
    .coverage { color:#8490a3; font-size:.64rem; text-align:right; }
    .scheme-card-note { border-top:1px solid #eef0f4; padding-top:.6rem; color:#8490a3; font-size:.7rem; }
    .disclaimer { margin:2rem 0 1rem; padding:.8rem 1rem; border:1px solid #f0dfc0;
      border-radius:10px; background:#fffaf0; color:#7c5c2a; font-size:.78rem; }
    [data-testid="stChatMessage"] { border-radius:14px; }
    .stButton > button { border-radius:10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def clear_conversation() -> None:
    st.session_state.messages = []
    st.session_state.recent_questions = []
    st.rerun()


for key, default in {
    "messages": [],
    "recent_questions": [],
    "profile": {"age": 0, "state": "", "occupation": "", "gender": "Prefer not to say"},
}.items():
    st.session_state.setdefault(key, default)

profile = render_sidebar(**st.session_state.profile, on_clear=clear_conversation)
st.session_state.profile = profile

if not st.session_state.messages:
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">PERSONALISED SCHEME DISCOVERY</div>
          <h1>Discover the support you're eligible for.</h1>
          <p>Explore government schemes, understand eligibility and get reliable guidance —
          all through one conversation.</p>
        </div>
        <div class="trust-row"><span class="trust-dot">●</span>
        Answers grounded in government scheme documents</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='section-kicker'>TRY ASKING</div>", unsafe_allow_html=True)
    prompts = [
        ("🎓", "Find scholarships for students"),
        ("🌾", "Government assistance for farmers"),
        ("🚀", "Schemes for women entrepreneurs"),
        ("⌂", "Housing and financial support schemes"),
    ]
    prompt_columns = st.columns(4)
    for column, (icon, prompt) in zip(prompt_columns, prompts):
        with column:
            st.markdown(
                f"<div class='prompt-card'><strong>{icon} {prompt}</strong>"
                "<span>Explore relevant schemes</span></div>",
                unsafe_allow_html=True,
            )
            if st.button("Ask this", key=f"prompt-{prompt}", use_container_width=True):
                st.session_state.pending_question = prompt
                st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            if message.get("meta"):
                st.caption(message["meta"])
            render_scheme_cards(message.get("sources", []))
            render_sources(message.get("sources", []))

question = st.chat_input("Ask about eligibility, benefits, documents or application process…")
question = question or st.session_state.pop("pending_question", None)
if question and question.strip():
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.recent_questions.append(question)
    with st.chat_message("user"):
        st.markdown(question)
    context = ""
    previous_user_messages = [
        item["content"] for item in st.session_state.messages[:-1] if item["role"] == "user"
    ]
    if previous_user_messages:
        context = f"Previous user context: {previous_user_messages[-2:]}\n"
    payload_profile: dict[str, Any] = {
        key: value
        for key, value in profile.items()
        if value not in (None, "", 0, "Prefer not to say")
    }
    with st.chat_message("assistant"):
        with st.spinner("Searching verified scheme documents…"):
            try:
                response = requests.post(
                    os.getenv("API_URL", "http://localhost:8000") + "/api/ask",
                    json={"question": context + question, "profile": payload_profile},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                answer = data["answer"]
                st.markdown(answer)
                meta = f"{data['query_type'].title()} · {data['latency_ms']} ms"
                st.caption(meta)
                render_scheme_cards(data.get("sources", []))
                render_sources(data.get("sources", []))
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "meta": meta,
                        "sources": data.get("sources", []),
                    }
                )
            except requests.RequestException as exc:
                error = f"Unable to reach the YojanaMitra API: {exc}"
                st.error(error)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error, "sources": []}
                )

st.markdown(
    '<div class="disclaimer">⚠️ Source data comes from myscheme.gov.in via a public '
    "dataset and may be outdated. Verify eligibility and application details on the "
    "official portal before applying.</div>",
    unsafe_allow_html=True,
)
