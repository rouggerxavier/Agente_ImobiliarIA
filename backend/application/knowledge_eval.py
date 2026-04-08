"""
[Fase 6 - 12.5] Avaliador simples de RAG para benchmark minimo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from application.knowledge import KnowledgeService


@dataclass
class RAGEvalCase:
    question: str
    expected_source_substrings: List[str] = field(default_factory=list)
    expected_domain: Optional[str] = None
    should_answer: bool = True
    city: Optional[str] = None
    neighborhood: Optional[str] = None


@dataclass
class RAGEvalCaseResult:
    question: str
    answered: bool
    sources: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    grounded: bool = False
    source_recall_hit: bool = False
    policy_ok: bool = True


class RAGEvaluator:
    """Benchmark minimo de recuperacao, groundedness e aderencia."""

    def __init__(self, service: KnowledgeService) -> None:
        self._service = service

    def evaluate(self, cases: List[RAGEvalCase], top_k: int = 3) -> Dict[str, object]:
        results: List[RAGEvalCaseResult] = []
        recall_hits = 0
        grounded_hits = 0
        hallucinations = 0
        policy_hits = 0
        answered_cases = 0
        passed_cases = 0

        for case in cases:
            result = self._service.answer(
                case.question,
                city=case.city,
                neighborhood=case.neighborhood,
                top_k=top_k,
            )
            answered = result is not None
            if answered:
                answered_cases += 1

            source_hit = _has_expected_source(result.sources if result else [], case.expected_source_substrings)
            grounded = bool(result and result.is_grounded)
            policy_ok = bool((not result) or all("internal" not in source and "sensitive" not in source for source in result.sources))
            if source_hit:
                recall_hits += 1
            if grounded:
                grounded_hits += 1
            if policy_ok:
                policy_hits += 1
            if answered and not grounded:
                hallucinations += 1

            domain_ok = case.expected_domain is None or ((result.domain if result else None) == case.expected_domain)
            answered_ok = answered == case.should_answer
            if answered_ok and domain_ok and (source_hit or not case.expected_source_substrings) and policy_ok:
                passed_cases += 1

            results.append(
                RAGEvalCaseResult(
                    question=case.question,
                    answered=answered,
                    sources=result.sources if result else [],
                    domain=result.domain if result else None,
                    grounded=grounded,
                    source_recall_hit=source_hit,
                    policy_ok=policy_ok,
                )
            )

        total = max(len(cases), 1)
        return {
            "total_cases": len(cases),
            "answered_rate": round(answered_cases / total, 3),
            "pass_rate": round(passed_cases / total, 3),
            "recall_at_k": round(recall_hits / total, 3),
            "groundedness_rate": round(grounded_hits / total, 3),
            "hallucination_rate": round(hallucinations / total, 3),
            "policy_adherence_rate": round(policy_hits / total, 3),
            "results": [result.__dict__ for result in results],
        }

    def compare_strategies(
        self,
        cases: List[RAGEvalCase],
        strategies: Dict[str, KnowledgeService],
        top_k: int = 3,
    ) -> Dict[str, Dict[str, object]]:
        comparison: Dict[str, Dict[str, object]] = {}
        for name, service in strategies.items():
            comparison[name] = RAGEvaluator(service).evaluate(cases, top_k=top_k)
        return comparison


def _has_expected_source(sources: List[str], expected: List[str]) -> bool:
    if not expected:
        return True
    normalized_sources = [source.lower() for source in sources]
    for fragment in expected:
        lowered = fragment.lower()
        if any(lowered in source for source in normalized_sources):
            return True
    return False
