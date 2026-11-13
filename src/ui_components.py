"""Reusable presentation components for the Streamlit application."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


def render_brand() -> None:
    st.markdown(
        """
        <div class="brand-lockup">
          <div class="brand-mark">Y</div>
          <div>
            <div class="brand-name">YojanaMitra</div>
            <div class="brand-subtitle">Your scheme discovery companion</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(
    age: int,
    state: str,
    occupation: str,
    gender: str,
    on_clear: Callable[[], None],
) -> dict[str, Any]:
    with st.sidebar:
        render_brand()
        st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
        if st.button("＋  New conversation", use_container_width=True, type="primary"):
            on_clear()
        st.markdown("<div class='sidebar-label'>WORKSPACE</div>", unsafe_allow_html=True)
        st.button("⌕  Discover schemes", use_container_width=True)
        st.button("◇  Compare schemes", use_container_width=True)
        st.button("☆  Saved schemes", use_container_width=True)
        st.markdown("<div class='sidebar-label'>RECENT</div>", unsafe_allow_html=True)
        for item in st.session_state.get("recent_questions", [])[-4:][::-1]:
            st.caption(f"  {item[:34]}{'…' if len(item) > 34 else ''}")
        st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-label'>ELIGIBILITY PREFERENCES</div>", unsafe_allow_html=True)
        age = st.number_input("Age", min_value=0, max_value=120, value=age, step=1)
        state = st.text_input("State / Union Territory", value=state)
        occupation = st.text_input("Occupation", value=occupation)
        gender = st.selectbox(
            "Gender",
            ["Prefer not to say", "Female", "Male", "Other"],
            index=["Prefer not to say", "Female", "Male", "Other"].index(gender),
        )
        st.markdown(
            "<div class='sidebar-footer'>⌁ Powered by Retrieval-Augmented Generation</div>",
            unsafe_allow_html=True,
        )
    return {"age": age, "state": state, "occupation": occupation, "gender": gender}


def render_scheme_cards(sources: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        grouped.setdefault(source.get("scheme_name", "Retrieved scheme"), []).append(source)
    if not grouped:
        return
    st.markdown("<div class='section-kicker'>RETRIEVED SCHEMES</div>", unsafe_allow_html=True)
    columns = st.columns(min(2, len(grouped)))
    for index, (name, scheme_sources) in enumerate(grouped.items()):
        with columns[index % len(columns)]:
            sections = {item.get("section", "") for item in scheme_sources}
            coverage = "Central / nationwide candidate"
            st.markdown(
                f"""
                <div class="scheme-card">
                  <div class="scheme-card-top">
                    <span class="status-pill">POTENTIAL MATCH</span>
                    <span class="coverage">{coverage}</span>
                  </div>
                  <h3>{name}</h3>
                  <p>Retrieved evidence covers: {", ".join(sorted(sections))}.</p>
                  <div class="scheme-card-note">Eligibility requires verification against your full profile.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("View retrieved details"):
                for item in scheme_sources:
                    st.markdown(f"**{item.get('section', 'Source section')}**")
                    st.caption(
                        f"{item.get('source_document', 'Official scheme document')} · "
                        f"Page {item.get('page_number', 1)}"
                    )
                    st.write(item.get("text", ""))
                    if item.get("source_url"):
                        st.link_button("Open official source", item["source_url"])


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander(f"⌁  Sources & references · {len(sources)} retrieved passages"):
        for index, source in enumerate(sources, start=1):
            st.markdown(
                f"**{index}. {source.get('scheme_name', 'Scheme')}** · "
                f"{source.get('section', 'Section')} · "
                f"{source.get('source_document', 'Official document')} · "
                f"Page {source.get('page_number', 1)}"
            )
            st.caption(source.get("text", ""))
            if source.get("source_url"):
                st.link_button("Open source", source["source_url"])
