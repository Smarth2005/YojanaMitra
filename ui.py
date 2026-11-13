"""Streamlit frontend."""

from __future__ import annotations

import os

import requests
import streamlit as st

st.set_page_config(page_title="YojanaMitra", page_icon="🇮🇳")
st.title("YojanaMitra")
st.caption("Find Indian government schemes using retrieved official scheme text.")
st.sidebar.header("Optional profile")
age = st.sidebar.number_input("Age", min_value=0, max_value=120, value=0)
state = st.sidebar.text_input("State / UT")
occupation = st.sidebar.text_input("Occupation")
gender = st.sidebar.text_input("Gender")
question = st.text_area(
    "Describe your situation or ask about a scheme",
    placeholder="I am a 21-year-old student from Punjab. Which scholarships can I apply for?",
)
if st.button("Ask") and question.strip():
    profile = {
        "age": age or None,
        "state": state or None,
        "occupation": occupation or None,
        "gender": gender or None,
    }
    response = requests.post(
        os.getenv("API_URL", "http://localhost:8000") + "/api/ask",
        json={"question": question, "profile": profile},
        timeout=60,
    )
    if response.ok:
        data = response.json()
        st.markdown(data["answer"])
        st.caption(f"Query type: {data['query_type']} | {data['latency_ms']} ms")
        with st.expander("Sources"):
            for source in data["sources"]:
                st.markdown(f"**{source['scheme_name']} — {source['section']}**")
                st.write(source["text"])
                if source["source_url"]:
                    st.link_button("Open source", source["source_url"])
    else:
        st.error(response.text)
st.warning(
    "Data comes from myscheme.gov.in via a public dataset and may be outdated. "
    "Verify details on the official portal before applying."
)
