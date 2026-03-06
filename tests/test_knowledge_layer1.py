import unicodedata

from agent import tools
from agent.extractor import detect_neighborhood
from agent.knowledge_base import answer_question


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def test_answer_question_institutional_custos():
    result = answer_question(
        "alem do valor do imovel, quais custos entram na compra?",
        domain="institutional",
        topic="custos",
        top_k=3,
    )
    assert result is not None
    assert "caso concreto" in _norm(result["answer"])
    assert any("custos_compra_itbi_cartorio" in src for src in result["sources"])


def test_neighborhood_registry_contains_knowledge_entries():
    neighborhoods = tools.get_neighborhoods()
    normalized = {_norm(n) for n in neighborhoods}
    assert "ponta do seixas" in normalized
    assert "barra de gramame" in normalized


def test_detect_neighborhood_accepts_underscore_text():
    known = tools.get_neighborhoods()
    detected = detect_neighborhood("quero apartamento no cabo_branco", known)
    assert detected is not None
    assert "cabo branco" in _norm(detected)

