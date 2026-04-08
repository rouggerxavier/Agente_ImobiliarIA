from pathlib import Path

from eval.run_eval import evaluate_against_baseline, extract_sources_from_reply, run_evaluation


def test_extract_sources_from_reply_with_followup_text():
    reply = (
        "Em geral, resposta curta.\n\n"
        "Fontes internas: knowledge/financiamento_basico.md#Resumo | knowledge/compra_passo_a_passo.md#Fluxo\n\n"
        "Agora, pra eu te indicar opcoes certas: qual seu orcamento?"
    )
    sources = extract_sources_from_reply(reply)
    assert sources == [
        "knowledge/financiamento_basico.md#Resumo",
        "knowledge/compra_passo_a_passo.md#Fluxo",
    ]


def test_run_evaluation_smoke_first_cases():
    report = run_evaluation(
        dataset_path=Path("eval/conversations.jsonl"),
        limit=5,
        use_llm=False,
        triage_only=True,
    )
    assert report["total_cases"] == 5
    assert "pass_rate" in report
    assert "check_accuracy" in report


def test_baseline_gate_detects_regression():
    report = {
        "total_cases": 100,
        "pass_rate": 0.70,
        "check_accuracy": {"route_ok": 1.0, "sources_ok": 0.65},
    }
    baseline = {
        "total_cases_min": 100,
        "pass_rate_min": 0.72,
        "check_accuracy_min": {"route_ok": 0.99, "sources_ok": 0.70},
    }
    violations = evaluate_against_baseline(report, baseline)
    assert any("pass_rate" in item for item in violations)
    assert any("sources_ok" in item for item in violations)
