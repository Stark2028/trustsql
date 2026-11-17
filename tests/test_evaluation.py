import json

from trustsql.evaluation import run_evaluation
from trustsql.models import Plan


def test_fixture_development_suite_has_honest_label(settings, tmp_path):
    report_path = tmp_path / "report.json"
    report = run_evaluation(settings, report_path)
    assert report["passed"] == report["cases"] == 18
    assert "not LLM accuracy" in report["label"]
    assert all(case["split"] == "development" for case in report["results"])
    assert json.loads(report_path.read_text())["model"] == "deterministic-demo"


def test_wrong_answer_to_refusal_case_is_recorded_instead_of_crashing(settings, tmp_path, monkeypatch):
    class AlwaysAnswers:
        def __init__(self, _settings):
            pass

        def plan(self, _question, _evidence):
            return Plan(
                status="answer",
                sql="SELECT COUNT(*) FROM orders",
                explanation="Wrong answer",
                citations=[d.urn for d in _evidence if d.table == "orders"],
            )

    monkeypatch.setattr("trustsql.evaluation.DemoPlanner", AlwaysAnswers)
    report = run_evaluation(settings, tmp_path / "nested" / "report.json", seed_values=(7,))
    refusal = next(case for case in report["results"] if case["id"] == "write-refusal")
    assert refusal["passed"] is False
    assert report["cases"] == 6


def test_expanded_suite_checks_rowsets_and_metrics(settings, tmp_path):
    report = run_evaluation(settings, tmp_path / "expanded.json", suite="expanded")
    assert report["distinct_questions"] == 32
    assert report["cases"] == report["passed"] == 96
    assert all(r["duration_ms"] >= 0 for r in report["results"])
    assert all(r["split"] == "development" for r in report["results"])


def test_evaluation_rejects_uncited_datasets(settings, tmp_path, monkeypatch):
    class Uncited:
        def __init__(self, _settings):
            pass

        def plan(self, _question, _evidence):
            return Plan(status="answer", sql="SELECT COUNT(*) FROM orders", explanation="Missing citation")

    monkeypatch.setattr("trustsql.evaluation.DemoPlanner", Uncited)
    report = run_evaluation(settings, tmp_path / "uncited.json", seed_values=(7,))
    assert not report["passed"]
    assert all(r["error_code"] == "invalid_evidence" for r in report["results"])
