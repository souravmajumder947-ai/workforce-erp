"""Public questions use the OpenAI Responses API independently of ERP records."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def api_key():
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key.strip()
    try:
        return str(st.secrets.get("OPENAI_API_KEY", "")).strip()
    except StreamlitSecretNotFoundError:
        return ""


def _plain_markdown(text):
    return re.sub(r"([\\`*_{}\[\]()<>#!|~])", r"\\\1", text)


def answer_markdown(result):
    parts = []
    for item in result.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                parts.append(_plain_markdown(content.get("refusal", "")))
                continue
            if content.get("type") != "output_text":
                continue
            text = content.get("text", "")
            citations = {}
            for annotation in content.get("annotations", []):
                if annotation.get("type") != "url_citation":
                    continue
                url = annotation.get("url", "")
                try:
                    parsed = urlsplit(url)
                except ValueError:
                    continue
                if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
                    continue
                offset = annotation.get("end_index")
                if not isinstance(offset, int) or not 0 <= offset <= len(text):
                    offset = len(text)
                label = _plain_markdown(str(annotation.get("title") or parsed.hostname)[:130])
                target = quote(url, safe=":/?&=#%+;,~@")
                link = f"[{label}]({target})"
                links = citations.setdefault(offset, [])
                if link not in links:
                    links.append(link)
            spans = []
            cursor = 0
            for offset, links in sorted(citations.items()):
                spans.extend((_plain_markdown(text[cursor:offset]), " " + " · ".join(links)))
                cursor = offset
            spans.append(_plain_markdown(text[cursor:]))
            parts.append("".join(spans))
    return "\n\n".join(part for part in parts if part.strip())


def ask_public(question, key):
    data = {
        "model": os.environ.get("JARVIS_OPENAI_MODEL") or "gpt-5-mini",
        "input": question,
        "instructions": ("Answer this public question clearly. Use web search for current or uncertain facts. "
                         "State when facts cannot be verified. You have no access to private ERP records, so "
                         "send ERP requests back to the ERP reporting tabs. Use short plain-text paragraphs."),
        "tools": [{"type": "web_search"}],
        "store": False,
        "max_output_tokens": 1600,
    }
    request = Request(
        "https://api.openai.com/v1/responses", data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=40) as response:
            result = json.load(response)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise ValueError("The OpenAI connection was rejected. Ask the ERP admin to check the server key and project access.") from None
        if exc.code == 429:
            raise ValueError("The AI account is rate limited or out of quota. Try again later or contact the ERP admin.") from None
        raise ValueError("The AI service could not answer this request. Try again.") from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError("The AI service could not be reached. Try again.") from None
    answer = answer_markdown(result)
    if not answer:
        raise ValueError("The AI did not return an answer. Try a shorter question.")
    return answer


def render_public_questions(username):
    key = api_key()
    if not key:
        st.info("General questions and web search need an OpenAI API key configured in Streamlit app secrets.")
        return
    st.caption("Use this tab for public topics. Your typed question is sent to OpenAI. Use the ERP tabs for company and employee records.")
    state_key = f"jarvis_public_answer_{username}"
    prompt = st.chat_input("Ask a general question", max_chars=2000, key=f"jarvis_public_prompt_{username}")
    if prompt and prompt.strip():
        st.session_state.pop(state_key, None)
        try:
            with st.spinner("JARVIS is checking your question…"):
                st.session_state[state_key] = (prompt.strip(), ask_public(prompt.strip(), key))
        except ValueError as exc:
            st.error(str(exc))
    answer = st.session_state.get(state_key)
    if answer:
        with st.chat_message("user"):
            st.text(answer[0])
        with st.chat_message("assistant"):
            st.markdown(answer[1])
