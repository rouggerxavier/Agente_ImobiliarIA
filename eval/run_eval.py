from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.geo_normalizer import location_key

DEFAULT_DATASET = ROOT_DIR / "eval" / "conversations.jsonl"


def _parse_frontmatter(raw: str) -> Tuple[Dict[str, str], str]:
    raw = raw.lstrip("\ufeff")
    if not raw.startswith("---"):
        return {}, raw
    lines = raw.splitlines()
    if len(lines) < 3:
        return {}, raw

    meta: Dict[str, str] = {}
    idx = 1
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "---":
            body = "\n".join(lines[idx + 1 :])
            return meta, body
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip()
        idx += 1
    return {}, raw


def build_knowledge_metadata_index() -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    knowledge_dir = ROOT_DIR / "knowledge"
    if not knowledge_dir.exists():
        return index

    for path in sorted(knowledge_dir.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        rel = path.relative_to(ROOT_DIR).as_posix()
        raw = path.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(raw)
        domain = (meta.get("domain") or ("geo" if "/geo/" in rel else "institutional")).strip().lower()
        topic = (meta.get("topic") or "general").strip().lower()
        index[rel] = {"domain": domain, "topic": topic}
    return index


def load_cases(dataset_path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip().lstrip("\ufeff")
            if not raw:
                continue
            cases.append(json.loads(raw))
            if limit and len(cases) >= limit:
                break
    return cases


def extract_sources_from_reply(reply: str) -> List[str]:
    marker = "Fontes internas:"
    if marker not in reply:
        return []
    tail = reply.split(marker, 1)[1].strip()
    sources_segment = tail.split("\n\n", 1)[0].strip()
    if not sources_segment:
        return []
    out: List[str] = []
    for item in sources_segment.split("|"):
        src = item.strip()
        if not src:
            continue
        out.append(src)
    return out


def classify_route(message: str, reply: str, has_intent: bool) -> str:
    if "Fontes internas:" in reply:
        return "QA_INTERRUPT"

    try:
        from app import faq
    except Exception:
        import faq

    from agent.controller import _is_qa_interrupt

    if faq.detect_faq_intent(message):
        return "QA_INTERRUPT"
    if has_intent and _is_qa_interrupt(message):
        return "QA_INTERRUPT"
    return "TRIAGE"


def _slot_filled(slot: str, state: Any) -> bool:
    if slot == "intent":
        return bool(state.intent)
    if slot == "lead_name":
        return bool((state.lead_profile or {}).get("name"))
    if slot == "lead_phone":
        return bool((state.lead_profile or {}).get("phone"))

    key_alias = {"budget_max": "budget"}
    key = key_alias.get(slot, slot)
    value = getattr(state.criteria, key, None)
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _configure_runtime(use_llm: bool, triage_only: bool) -> None:
    import agent.llm as llm_module
    import agent.rules as rules_module
    import agent.controller as controller_module

    llm_module.USE_LLM = use_llm
    llm_module.TRIAGE_ONLY = triage_only
    rules_module.TRIAGE_ONLY = triage_only
    controller_module.TRIAGE_ONLY = triage_only


def evaluate_case(
    case: Dict[str, Any],
    *,
    knowledge_index: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    from agent.controller import handle_message
    from agent.state import store

    case_id = str(case.get("id") or "case")
    messages = case.get("messages") or []
    expected = case.get("expected") or {}

    session_id = f"eval_{case_id}"
    store.reset(session_id)

    last_reply = ""
    for message in messages:
        response = handle_message(session_id, str(message))
        last_reply = str(response.get("reply") or "")

    state = store.get(session_id)
    last_message = str(messages[-1]) if messages else ""
    observed_route = classify_route(last_message, last_reply, has_intent=bool(state.intent))

    observed_sources_raw = extract_sources_from_reply(last_reply)
    observed_sources_base = [s.split("#", 1)[0] for s in observed_sources_raw]

    observed_topics = set()
    observed_domain = None
    for src in observed_sources_base:
        meta = knowledge_index.get(src)
        if not meta:
            continue
        if observed_domain is None:
            observed_domain = meta.get("domain")
        topic = meta.get("topic")
        if topic:
            observed_topics.add(topic)

    expected_slots = expected.get("slots_should_update") or []
    missing_slots = [slot for slot in expected_slots if not _slot_filled(str(slot), state)]
    slots_ok = not missing_slots

    expected_city = expected.get("city")
    city_ok = True
    if expected_city is not None:
        city_ok = location_key(state.criteria.city) == location_key(str(expected_city))

    expected_neighborhood = expected.get("neighborhood")
    neighborhood_ok = True
    if expected_neighborhood is not None:
        neighborhood_ok = location_key(state.criteria.neighborhood) == location_key(str(expected_neighborhood))

    expected_route = str(expected.get("route") or "")
    route_ok = observed_route == expected_route if expected_route else True

    expected_domain = str(expected.get("domain_should_use") or "none").lower()
    if expected_domain == "none":
        domain_ok = not observed_sources_base or observed_domain is None
    else:
        domain_ok = observed_domain == expected_domain

    expected_topics = [str(t).lower() for t in (expected.get("topics_should_use") or []) if str(t).lower() != "triage_slots"]
    if expected_topics:
        topic_ok = any(topic in observed_topics for topic in expected_topics)
    else:
        topic_ok = True

    expected_sources = [str(s).replace("\\", "/") for s in (expected.get("should_use_sources") or [])]
    sources_ok = True
    if expected_sources:
        observed_set = set(observed_sources_base)
        sources_ok = all(src in observed_set for src in expected_sources)

    checks = {
        "route_ok": route_ok,
        "slots_ok": slots_ok,
        "city_ok": city_ok,
        "neighborhood_ok": neighborhood_ok,
        "domain_ok": domain_ok,
        "topic_ok": topic_ok,
        "sources_ok": sources_ok,
    }
    case_ok = all(checks.values())

    return {
        "id": case_id,
        "ok": case_ok,
        "checks": checks,
        "expected_route": expected_route,
        "observed_route": observed_route,
        "missing_slots": missing_slots,
        "expected_domain": expected_domain,
        "observed_domain": observed_domain,
        "expected_topics": expected_topics,
        "observed_topics": sorted(observed_topics),
        "expected_sources": expected_sources,
        "observed_sources": observed_sources_base,
        "expected_city": expected_city,
        "observed_city": state.criteria.city,
        "expected_neighborhood": expected_neighborhood,
        "observed_neighborhood": state.criteria.neighborhood,
    }


def run_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    limit: Optional[int] = None,
    use_llm: bool = False,
    triage_only: bool = True,
) -> Dict[str, Any]:
    _configure_runtime(use_llm=use_llm, triage_only=triage_only)
    cases = load_cases(dataset_path, limit=limit)
    knowledge_index = build_knowledge_metadata_index()

    results = [evaluate_case(case, knowledge_index=knowledge_index) for case in cases]
    total = len(results)
    if total == 0:
        return {
            "dataset": dataset_path.as_posix(),
            "total_cases": 0,
            "pass_cases": 0,
            "pass_rate": 0.0,
            "check_accuracy": {},
            "failures": [],
        }

    check_names = ["route_ok", "slots_ok", "city_ok", "neighborhood_ok", "domain_ok", "topic_ok", "sources_ok"]
    check_accuracy: Dict[str, float] = {}
    for check in check_names:
        hits = sum(1 for row in results if row["checks"].get(check))
        check_accuracy[check] = hits / total

    pass_cases = sum(1 for row in results if row["ok"])
    failures = [row for row in results if not row["ok"]]

    return {
        "dataset": dataset_path.as_posix(),
        "total_cases": total,
        "pass_cases": pass_cases,
        "pass_rate": pass_cases / total,
        "check_accuracy": check_accuracy,
        "failures": failures,
    }


def load_baseline(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_against_baseline(report: Dict[str, Any], baseline: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    pass_rate_min = baseline.get("pass_rate_min")
    if pass_rate_min is not None and float(report.get("pass_rate", 0.0)) < float(pass_rate_min):
        violations.append(f"pass_rate<{pass_rate_min}")

    total_cases_min = baseline.get("total_cases_min")
    if total_cases_min is not None and int(report.get("total_cases", 0)) < int(total_cases_min):
        violations.append(f"total_cases<{total_cases_min}")

    check_min = baseline.get("check_accuracy_min") or {}
    check_accuracy = report.get("check_accuracy") or {}
    for key, min_value in check_min.items():
        observed = float(check_accuracy.get(key, 0.0))
        if observed < float(min_value):
            violations.append(f"check_accuracy.{key}<{min_value} (got {observed:.3f})")
    return violations


def _print_summary(report: Dict[str, Any], max_failures: int, gate_violations: Optional[List[str]] = None) -> None:
    print(f"Dataset: {report['dataset']}")
    print(f"Cases: {report['total_cases']}")
    print(f"Pass: {report['pass_cases']} ({report['pass_rate']:.1%})")
    print("")
    print("Check accuracy:")
    for key, value in sorted((report.get("check_accuracy") or {}).items()):
        print(f"- {key}: {value:.1%}")

    if gate_violations is not None:
        print("")
        if gate_violations:
            print("Baseline gate: FAILED")
            for item in gate_violations:
                print(f"- {item}")
        else:
            print("Baseline gate: PASSED")

    failures = report.get("failures") or []
    if not failures:
        print("")
        print("No failures.")
        return

    print("")
    print(f"Failures ({len(failures)}):")
    for row in failures[:max_failures]:
        failing_checks = [k for k, v in row.get("checks", {}).items() if not v]
        print(f"- {row['id']}: {', '.join(failing_checks)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Runner de avaliacao para eval/conversations.jsonl")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Caminho do dataset JSONL")
    parser.add_argument("--limit", type=int, default=None, help="Limita quantidade de casos")
    parser.add_argument("--use-llm", action="store_true", help="Executa com USE_LLM=true")
    parser.add_argument("--allow-search", action="store_true", help="Usa TRIAGE_ONLY=false durante a avaliacao")
    parser.add_argument("--output", default="", help="Se informado, salva relatorio JSON neste caminho")
    parser.add_argument("--max-failures", type=int, default=20, help="Quantidade maxima de falhas impressas")
    parser.add_argument("--baseline", default="", help="Arquivo JSON com baseline de qualidade")
    parser.add_argument("--strict", action="store_true", help="Retorna exit code 1 se houver qualquer falha")
    args = parser.parse_args()

    dataset = Path(args.dataset)
    report = run_evaluation(
        dataset_path=dataset,
        limit=args.limit,
        use_llm=args.use_llm,
        triage_only=not args.allow_search,
    )
    gate_violations: Optional[List[str]] = None
    if args.baseline:
        baseline_path = Path(args.baseline)
        baseline = load_baseline(baseline_path)
        gate_violations = evaluate_against_baseline(report, baseline)
        report["baseline_path"] = baseline_path.as_posix()
        report["gate_violations"] = gate_violations
        report["gate_passed"] = len(gate_violations) == 0

    _print_summary(report, max_failures=max(1, args.max_failures), gate_violations=gate_violations)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.strict:
        if gate_violations is not None:
            if gate_violations:
                raise SystemExit(1)
        elif report.get("failures") or []:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
