"""A small, provider-agnostic AI client.

Two jobs:
- read_paper: photos of an exam paper -> structured questions tagged with topics
- explain: one question -> a step-by-step worked answer (Markdown)

Providers (settings.AI_PROVIDER):
- "openai": any OpenAI-compatible Chat Completions API, including Google Gemini's
  free tier, Groq and OpenAI itself
- "anthropic": Anthropic's Messages API
- "fake": deterministic canned output for local development and screenshots
"""

import base64
import json
import re

import requests
from django.conf import settings


class AIError(Exception):
    pass


def enabled():
    return settings.AI_ENABLED


# --- Transport --------------------------------------------------------------------


def _openai(system, prompt, images, max_tokens):
    content = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img).decode()}"}}
        for img in images
    ]
    res = requests.post(
        settings.AI_BASE_URL.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
        json={
            "model": settings.AI_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        },
        timeout=90,
    )
    if res.status_code >= 400:
        raise AIError(f"AI provider error {res.status_code}: {res.text[:200]}")
    try:
        return res.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise AIError("Unexpected response from the AI provider.") from exc


def _anthropic(system, prompt, images, max_tokens):
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(img).decode()}}
        for img in images
    ] + [{"type": "text", "text": prompt}]
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.AI_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": settings.AI_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": content}],
        },
        timeout=90,
    )
    if res.status_code >= 400:
        raise AIError(f"AI provider error {res.status_code}: {res.text[:200]}")
    try:
        return "".join(block.get("text", "") for block in res.json()["content"])
    except (KeyError, ValueError) as exc:
        raise AIError("Unexpected response from the AI provider.") from exc


def complete(system, prompt, images=(), max_tokens=2000):
    provider = settings.AI_PROVIDER
    if provider == "fake":
        return _fake(system, prompt, images)
    if not settings.AI_ENABLED:
        raise AIError("AI isn't configured on this server.")
    if provider == "anthropic":
        return _anthropic(system, prompt, list(images), max_tokens)
    return _openai(system, prompt, list(images), max_tokens)


def parse_json(text):
    """Models sometimes wrap JSON in ```fences``` or add a sentence; find the object."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AIError("The AI didn't return JSON.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIError("The AI returned malformed JSON.") from exc


# --- Jobs ---------------------------------------------------------------------------

READ_SYSTEM = (
    "You transcribe university exam papers into structured data for a study app. "
    "Be faithful to the original wording. Never invent questions."
)

READ_PROMPT = """These are photos of a past exam paper for {course}.

Return ONLY a JSON object:
{{
  "instructions": "rubric text such as 'Answer any four questions' (empty string if none)",
  "questions": [
    {{"number": "1a", "text": "full question text", "marks": 5, "topic": "Short Topic Name"}}
  ]
}}

Rules:
- One entry per question or sub-question, in paper order. Put shared context (a scenario, table or code that several
  sub-questions use) into the text of each sub-question that needs it.
- Keep the exact wording. Write maths in plain text with Unicode (x², √, ≤, π), not LaTeX.
- "marks" is a number or null. "topic" is 1–4 words naming the concept examined.
{topic_hint}- Skip anything you can't read rather than guessing. If there are no questions, return an empty list."""

EXPLAIN_SYSTEM = (
    "You are a patient, rigorous tutor helping a Nigerian university student prepare for exams. "
    "You explain clearly and correctly, and you say so when a question is ambiguous or data is missing."
)

EXPLAIN_PROMPT = """Course: {course}
Question {number}{marks}:
{text}

Write a worked answer in Markdown with these sections:
### What the question is asking
### Solution
(step by step; show working and reasoning)
### Answer
(the final answer, concise)
### Revise these concepts
(2–4 bullet points)

Use plain text with Unicode for maths (no LaTeX). Use fenced code blocks for code.
Keep it under 450 words. If the question can't be answered as written, explain what's missing and state your assumption."""


def clean_topic(topic):
    topic = re.sub(r"\s+", " ", (topic or "").strip().strip(".:;,-"))[:60]
    return topic[:1].upper() + topic[1:] if topic else ""


def read_paper(course_label, images, known_topics=()):
    topic_hint = (
        f"- Reuse one of these existing topic names when it fits: {', '.join(sorted(known_topics)[:40])}.\n"
        if known_topics
        else ""
    )
    raw = complete(READ_SYSTEM, READ_PROMPT.format(course=course_label, topic_hint=topic_hint), images, max_tokens=6000)
    data = parse_json(raw)

    known = {t.lower(): t for t in known_topics}
    questions = []
    for i, q in enumerate(data.get("questions") or []):
        text = str(q.get("text") or "").strip()
        if not text:
            continue
        topic = clean_topic(q.get("topic"))
        marks = q.get("marks")
        questions.append({
            "number": str(q.get("number") or i + 1)[:12],
            "text": text,
            "marks": marks if isinstance(marks, int) and 0 < marks < 1000 else None,
            "topic": known.get(topic.lower(), topic),
        })
    return str(data.get("instructions") or "").strip(), questions


def explain(course_label, question):
    marks = f" ({question.marks} marks)" if question.marks else ""
    prompt = EXPLAIN_PROMPT.format(course=course_label, number=question.number, marks=marks, text=question.text)
    text = complete(EXPLAIN_SYSTEM, prompt, max_tokens=1500).strip()
    if not text:
        raise AIError("The AI returned an empty explanation.")
    return text


# --- Fake provider (development only) -------------------------------------------------

FAKE_TOPICS = ["Data structures", "Algorithms", "Complexity", "Recursion", "Databases", "Networking"]


def _fake(system, prompt, images):
    if system == READ_SYSTEM:
        questions = []
        for page in range(max(1, len(images))):
            for part, letter in enumerate("ab"):
                n = page * 2 + part
                questions.append({
                    "number": f"{page + 1}{letter}",
                    "text": f"[Sample question {n + 1}] Explain the key idea behind "
                            f"{FAKE_TOPICS[n % len(FAKE_TOPICS)].lower()} and give one example.",
                    "marks": 5 + part * 5,
                    "topic": FAKE_TOPICS[n % len(FAKE_TOPICS)],
                })
        return json.dumps({"instructions": "Answer any FOUR questions. (Sample data)", "questions": questions})

    return (
        "### What the question is asking\nThis is a **sample explanation** from the development AI provider.\n\n"
        "### Solution\n1. Identify the concept being tested.\n2. State the definition.\n3. Work through an example.\n\n"
        "### Answer\nA concise final answer would appear here.\n\n"
        "### Revise these concepts\n- The core definition\n- A worked example\n"
    )
