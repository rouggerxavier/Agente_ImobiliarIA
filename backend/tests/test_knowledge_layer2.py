import unicodedata

from agent.knowledge_base import answer_question, retrieve_hybrid


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def test_hybrid_fallback_to_lexical_when_embeddings_disabled(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "false")
    hits = retrieve_hybrid(
        "aceita airbnb e locacao por temporada?",
        top_k=3,
        filters={"domain": "institutional"},
    )
    assert hits
    assert any("locacao_por_temporada_airbnb" in h.chunk.path for h in hits)


def test_domain_hint_geo_without_explicit_filter(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "false")
    result = answer_question("Bessa ou Manaira e melhor para familia?")
    assert result is not None
    assert result["domain"] == "geo"
    assert any("/geo/" in src for src in result["sources"])


def test_topic_rerank_for_custos(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "false")
    result = answer_question(
        "alem do valor do imovel, o que entra de itbi e cartorio?",
        domain="institutional",
        top_k=3,
    )
    assert result is not None
    assert result["topic"] == "custos"
    assert any("custos_compra_itbi_cartorio" in src for src in result["sources"])


def test_geo_city_filter_keeps_city_scope(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "false")
    result = answer_question(
        "Intermares e bom para morar?",
        city="cabedelo",
        domain="geo",
        top_k=3,
    )
    assert result is not None
    assert result["domain"] == "geo"
    assert any("cabedelo/intermares" in _norm(src) for src in result["sources"])
