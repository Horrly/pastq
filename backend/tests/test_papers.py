import pytest
from django.core.management import call_command

from papers import ai
from papers.models import Course, Explanation, Paper, Question, University

pytestmark = pytest.mark.django_db


def put_questions(client, paper_id, questions):
    return client.put(f"/api/papers/{paper_id}/questions/", {"questions": questions}, format="json")


class TestCourses:
    def test_create_normalises_code(self, ada_api, oau):
        res = ada_api.post("/api/courses/", {"university": "oau", "code": "mth-101", "title": "Elementary Maths"},
                           format="json")
        assert res.status_code == 201
        assert (res.data["code"], res.data["slug"]) == ("MTH 101", "oau-mth-101")

    def test_duplicate_code_rejected(self, ada_api, csc201):
        res = ada_api.post("/api/courses/", {"university": "oau", "code": "CSC 201", "title": "Again"}, format="json")
        assert res.status_code == 400

    def test_bad_code_and_level(self, ada_api, oau):
        assert ada_api.post("/api/courses/", {"university": "oau", "code": "HELLO", "title": "x"},
                            format="json").status_code == 400
        assert ada_api.post("/api/courses/", {"university": "oau", "code": "CSC 305", "title": "x", "level": 250},
                            format="json").status_code == 400

    @pytest.mark.parametrize("q", ["csc201", "CSC 201", "csc-201", "programming"])
    def test_search(self, anon, csc201, q):
        assert [c["code"] for c in anon.get(f"/api/courses/?q={q}").data] == ["CSC 201"]

    def test_creating_requires_login(self, anon, oau):
        assert anon.post("/api/courses/", {"university": "oau", "code": "X 1", "title": "x"}).status_code == 401


class TestCoursePage:
    def test_papers_and_top_topics(self, anon, upload):
        upload()
        upload(year=2022)
        data = anon.get("/api/courses/oau-csc-201/").data
        assert [p["session"] for p in data["papers"]] == ["2023/2024", "2022/2023"]
        assert data["papers"][0]["question_count"] == 2
        top = data["top_topics"][0]
        assert top["papers"] == 2  # the topic appeared in both years

    def test_practice(self, anon, upload):
        upload(files=None)
        questions = anon.get("/api/courses/oau-csc-201/practice/?n=5").data
        assert len(questions) == 2
        assert questions[0]["paper"]["session"] == "2023/2024"

        topic = questions[0]["topic"]
        only = anon.get(f"/api/courses/oau-csc-201/practice/?topic={topic}").data
        assert {q["topic"] for q in only} == {topic}


class TestEditingQuestions:
    def test_uploader_can_type_questions(self, ada_api, upload, settings):
        settings.AI_PROVIDER, settings.AI_ENABLED = "", False
        paper_id = upload().data["id"]
        res = put_questions(ada_api, paper_id, [
            {"number": "", "text": "  Define an algorithm. ", "marks": 5, "topic": "algorithms"},
            {"number": "2", "text": "Explain Big-O.", "topic": ""},
        ])
        assert res.status_code == 200
        assert res.data["status"] == "ready"
        assert [(q["number"], q["text"], q["topic"]) for q in res.data["questions"]] == [
            ("1", "Define an algorithm.", "Algorithms"), ("2", "Explain Big-O.", ""),
        ]

    def test_others_cannot_edit(self, tunde_api, upload):
        paper_id = upload().data["id"]
        assert put_questions(tunde_api, paper_id, []).status_code == 403

    def test_explanations_survive_unrelated_edits(self, ada_api, upload):
        paper_id = upload().data["id"]
        questions = ada_api.get(f"/api/papers/{paper_id}/").data["questions"]
        ada_api.post(f"/api/questions/{questions[0]['id']}/explain/")

        edited = [{"number": q["number"], "text": q["text"], "marks": q["marks"], "topic": q["topic"]} for q in questions]
        edited[1]["text"] = "A corrected second question."
        res = put_questions(ada_api, paper_id, edited)
        assert res.data["questions"][0]["explanation"] is not None  # unchanged question kept its explanation
        assert Explanation.objects.count() == 1


class TestExplanations:
    def test_generated_once_and_shared(self, ada_api, tunde_api, upload, monkeypatch):
        question_id = Question.objects.get(pk=upload().data["questions"][0]["id"]).id
        calls = []
        real = ai.explain
        monkeypatch.setattr(ai, "explain", lambda *a: calls.append(1) or real(*a))

        first = ada_api.post(f"/api/questions/{question_id}/explain/")
        second = tunde_api.post(f"/api/questions/{question_id}/explain/")
        assert (first.status_code, second.status_code) == (201, 200)
        assert first.data["id"] == second.data["id"] and len(calls) == 1
        assert "### Solution" in first.data["text"]

    def test_requires_login(self, anon, upload):
        question_id = upload().data["questions"][0]["id"]
        assert anon.post(f"/api/questions/{question_id}/explain/").status_code == 401

    def test_daily_limit_only_counts_new_ones(self, ada_api, tunde_api, upload, settings):
        settings.EXPLANATIONS_PER_USER_PER_DAY = 1
        q1, q2 = [q["id"] for q in upload().data["questions"]]
        assert tunde_api.post(f"/api/questions/{q1}/explain/").status_code == 201
        assert tunde_api.post(f"/api/questions/{q2}/explain/").status_code == 429
        assert tunde_api.post(f"/api/questions/{q1}/explain/").status_code == 200  # cached: always free

    def test_unavailable_without_ai(self, ada_api, upload, settings):
        question_id = upload().data["questions"][0]["id"]
        settings.AI_PROVIDER, settings.AI_ENABLED = "", False
        assert ada_api.post(f"/api/questions/{question_id}/explain/").status_code == 503

    def test_ai_errors_are_friendly(self, ada_api, upload, monkeypatch):
        question_id = upload().data["questions"][0]["id"]
        monkeypatch.setattr(ai, "complete", lambda *a, **k: (_ for _ in ()).throw(ai.AIError("500")))
        res = ada_api.post(f"/api/questions/{question_id}/explain/")
        assert res.status_code == 503 and "try again" in res.data["detail"]

    def test_votes(self, ada_api, tunde_api, upload):
        question_id = upload().data["questions"][0]["id"]
        explanation_id = ada_api.post(f"/api/questions/{question_id}/explain/").data["id"]

        ada_api.post(f"/api/explanations/{explanation_id}/vote/", {"value": 1}, format="json")
        res = tunde_api.post(f"/api/explanations/{explanation_id}/vote/", {"value": -1}, format="json")
        assert (res.data["helpful"], res.data["not_helpful"], res.data["my_vote"]) == (1, 1, -1)

        res = tunde_api.post(f"/api/explanations/{explanation_id}/vote/", {"value": 1}, format="json")  # change mind
        assert (res.data["helpful"], res.data["not_helpful"]) == (2, 0)
        assert tunde_api.post(f"/api/explanations/{explanation_id}/vote/", {"value": 5}, format="json").status_code == 400


class TestModeration:
    def test_flag_and_hide(self, ada_api, tunde_api, anon, upload):
        paper_id = upload().data["id"]
        assert tunde_api.post(f"/api/papers/{paper_id}/flag/", {"reason": "Wrong course"}, format="json").status_code == 201
        assert tunde_api.post(f"/api/papers/{paper_id}/flag/", {"reason": ""}, format="json").status_code == 400

        Paper.objects.filter(pk=paper_id).update(is_hidden=True)
        assert anon.get(f"/api/papers/{paper_id}/").status_code == 404
        assert tunde_api.get(f"/api/papers/{paper_id}/").status_code == 404
        assert ada_api.get(f"/api/papers/{paper_id}/").status_code == 200  # uploader still sees it
        assert anon.get("/api/courses/oau-csc-201/").data["paper_total"] == 0

    def test_retry_reading(self, ada_api, tunde_api, upload, monkeypatch):
        def boom(*a, **k):
            raise ai.AIError("temporary")

        with monkeypatch.context() as m:
            m.setattr(ai, "complete", boom)
            paper_id = upload().data["id"]
        assert Paper.objects.get(pk=paper_id).status == "needs_text"

        assert tunde_api.post(f"/api/papers/{paper_id}/retry/").status_code == 403
        assert ada_api.post(f"/api/papers/{paper_id}/retry/").status_code == 200
        assert Paper.objects.get(pk=paper_id).status == "ready"


class TestHomeAndSetup:
    def test_stats_and_leaderboard(self, anon, upload, tunde_api):
        upload()
        upload(year=2022)
        upload(year=2021, client=tunde_api)
        data = anon.get("/api/stats/").data
        assert (data["papers"], data["questions"], data["courses"]) == (3, 6, 1)
        assert data["top_contributors"] == [{"username": "ada", "uploads": 2}, {"username": "tunde", "uploads": 1}]
        assert len(data["recent_papers"]) == 3

    def test_config(self, anon):
        assert anon.get("/api/config/").data["ai_enabled"] is True

    def test_seed_universities_idempotent(self):
        call_command("seed_universities")
        call_command("seed_universities")
        assert University.objects.filter(short_name="OAU").exists()
        assert University.objects.count() == 10

    def test_health(self, anon):
        assert anon.get("/api/health/").json() == {"status": "ok"}

    def test_course_slug(self, oau):
        assert Course.objects.create(university=oau, code="gst 111", title="x").slug == "oau-gst-111"
