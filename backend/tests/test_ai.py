import json

import pytest
import responses

from papers import ai
from papers.models import Question

OPENAI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


@pytest.mark.parametrize("raw", [
    '{"questions": []}',
    '```json\n{"questions": []}\n```',
    'Here you go:\n{"questions": []}\nHope that helps!',
])
def test_parse_json_tolerates_wrapping(raw):
    assert ai.parse_json(raw) == {"questions": []}


def test_parse_json_errors():
    with pytest.raises(ai.AIError):
        ai.parse_json("no json here")
    with pytest.raises(ai.AIError):
        ai.parse_json("{not: valid}")


def test_read_paper_cleans_output(settings, monkeypatch):
    payload = {
        "instructions": "Answer any four",
        "questions": [
            {"number": "1a", "text": "Define recursion.", "marks": 5, "topic": "recursion."},
            {"number": "1b", "text": "  ", "marks": 5, "topic": "x"},  # empty -> dropped
            {"number": None, "text": "Sort this list.", "marks": "ten", "topic": "  sorting algorithms "},
        ],
    }
    monkeypatch.setattr(ai, "complete", lambda *a, **k: json.dumps(payload))
    instructions, questions = ai.read_paper("OAU CSC 201", [b"img"], known_topics={"Recursion"})

    assert instructions == "Answer any four"
    assert questions == [
        {"number": "1a", "text": "Define recursion.", "marks": 5, "topic": "Recursion"},  # matched existing topic
        {"number": "3", "text": "Sort this list.", "marks": None, "topic": "Sorting algorithms"},
    ]


@responses.activate
def test_openai_compatible_transport(settings):
    settings.AI_PROVIDER, settings.AI_API_KEY, settings.AI_ENABLED = "openai", "gm-key", True
    settings.AI_MODEL = "gemini-2.5-flash"
    responses.post(OPENAI_URL, json={"choices": [{"message": {"content": "hello"}}]})

    assert ai.complete("sys", "prompt", [b"\xff\xd8jpeg"]) == "hello"

    request = responses.calls[0].request
    body = json.loads(request.body)
    assert request.headers["Authorization"] == "Bearer gm-key"
    assert body["model"] == "gemini-2.5-flash"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    parts = body["messages"][1]["content"]
    assert parts[0] == {"type": "text", "text": "prompt"}
    assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


@responses.activate
def test_anthropic_transport(settings):
    settings.AI_PROVIDER, settings.AI_API_KEY, settings.AI_ENABLED = "anthropic", "sk-ant", True
    responses.post(ANTHROPIC_URL, json={"content": [{"type": "text", "text": "hi"}]})

    assert ai.complete("sys", "prompt", [b"img"]) == "hi"

    request = responses.calls[0].request
    body = json.loads(request.body)
    assert request.headers["x-api-key"] == "sk-ant"
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert body["system"] == "sys"
    assert body["messages"][0]["content"][0]["source"]["media_type"] == "image/jpeg"


@responses.activate
def test_provider_errors_become_ai_errors(settings):
    settings.AI_PROVIDER, settings.AI_API_KEY, settings.AI_ENABLED = "openai", "k", True
    responses.post(OPENAI_URL, status=429, json={"error": "rate limited"})
    with pytest.raises(ai.AIError, match="429"):
        ai.complete("s", "p")


def test_disabled_ai_raises(settings):
    settings.AI_PROVIDER, settings.AI_ENABLED = "", False
    with pytest.raises(ai.AIError):
        ai.complete("s", "p")


def test_explain_prompt_includes_question(monkeypatch):
    seen = {}

    def fake_complete(system, prompt, *args, **kwargs):
        seen["prompt"] = prompt
        return "### Answer\n42"

    monkeypatch.setattr(ai, "complete", fake_complete)
    question = Question(number="2b", text="What is 6 × 7?", marks=4)
    assert ai.explain("OAU MTH 101", question) == "### Answer\n42"
    assert "Question 2b (4 marks):" in seen["prompt"] and "What is 6 × 7?" in seen["prompt"]
