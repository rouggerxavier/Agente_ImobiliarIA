from pathlib import Path
from textwrap import dedent

from application.knowledge import KnowledgeService
from application.knowledge_eval import RAGEvalCase, RAGEvaluator
from infrastructure.knowledge.ingestor import load_file


def _write_doc(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return path


def test_ingestor_loads_markdown_and_preserves_metadata(tmp_path: Path):
    path = _write_doc(
        tmp_path / "financiamento.md",
        """
        ---
        doc_type: financing
        city: joao_pessoa
        neighborhood: manaira
        tags: [credito, banco]
        is_public: true
        updated_at: 2026-03-30
        ---
        # Financiamento

        O banco avalia renda, documentos e capacidade de pagamento.
        """,
    )

    doc = load_file(str(path))

    assert doc is not None
    assert doc.doc_type == "financing"
    assert doc.city == "joao_pessoa"
    assert doc.neighborhood == "manaira"
    assert "credito" in doc.tags
    assert doc.version


def test_knowledge_service_answers_with_sources_and_groundedness(tmp_path: Path):
    _write_doc(
        tmp_path / "financiamento.md",
        """
        ---
        doc_type: financing
        is_public: true
        ---
        # Financiamento basico

        ## Analise
        O banco normalmente avalia renda, documentos e situacao do imovel.

        ## Prazo
        O prazo depende do banco e da documentacao apresentada.
        """,
    )

    service = KnowledgeService(knowledge_dir=tmp_path, auto_load=True)
    result = service.answer("como funciona o financiamento?", top_k=2)

    assert result is not None
    assert result.domain == "financing"
    assert result.is_grounded is True
    assert any("financiamento.md" in source for source in result.sources)
    assert "Fontes internas:" in result.reply_text


def test_knowledge_service_does_not_conflict_with_catalog_questions(tmp_path: Path):
    _write_doc(
        tmp_path / "faq.md",
        """
        ---
        doc_type: faq
        ---
        # FAQ

        ## Atendimento
        Podemos orientar sobre processo de compra e documentacao.
        """,
    )

    service = KnowledgeService(knowledge_dir=tmp_path, auto_load=True)

    assert service.classify_question("tem apartamento no bessa com 3 quartos?") == "catalog"
    assert service.answer("tem apartamento no bessa com 3 quartos?") is None


def test_knowledge_service_filters_geo_by_city_and_neighborhood(tmp_path: Path):
    _write_doc(
        tmp_path / "geo" / "manaira.md",
        """
        ---
        doc_type: geo
        city: joao_pessoa
        neighborhood: manaira
        is_public: true
        ---
        # Manaira

        ## Resumo
        Manaira tem perfil residencial misto e boa conexao com a orla.
        """,
    )

    service = KnowledgeService(knowledge_dir=tmp_path, auto_load=True)
    result = service.answer(
        "Manaira e bom para morar com familia?",
        city="joao_pessoa",
        neighborhood="manaira",
        top_k=1,
    )

    assert result is not None
    assert result.domain == "geo"
    assert result.sources[0].endswith("manaira.md#Resumo")


def test_knowledge_service_blocks_when_context_is_insufficient(tmp_path: Path):
    _write_doc(
        tmp_path / "faq.md",
        """
        ---
        doc_type: faq
        ---
        # FAQ

        ## Atendimento
        Nosso atendimento funciona em horario comercial.
        """,
    )

    service = KnowledgeService(knowledge_dir=tmp_path, auto_load=True)

    assert service.answer("qual a composicao quimica do concreto armado?") is None


def test_rag_evaluator_reports_metrics_and_strategy_comparison(tmp_path: Path):
    _write_doc(
        tmp_path / "financiamento.md",
        """
        ---
        doc_type: financing
        is_public: true
        ---
        # Financiamento

        ## Resumo
        O banco avalia renda, entrada, capacidade de pagamento e documentacao do imovel antes da aprovacao.
        """,
    )

    service = KnowledgeService(knowledge_dir=tmp_path, auto_load=True)
    empty_service = KnowledgeService(knowledge_dir=tmp_path / "vazio", auto_load=False)
    evaluator = RAGEvaluator(service)
    cases = [
        RAGEvalCase(
            question="aceita financiamento?",
            expected_source_substrings=["financiamento.md"],
            expected_domain="financing",
            should_answer=True,
        )
    ]

    report = evaluator.evaluate(cases, top_k=1)
    comparison = evaluator.compare_strategies(cases, {"ok": service, "empty": empty_service}, top_k=1)

    assert report["recall_at_k"] == 1.0
    assert report["groundedness_rate"] == 1.0
    assert comparison["ok"]["pass_rate"] == 1.0
    assert comparison["empty"]["answered_rate"] == 0.0
