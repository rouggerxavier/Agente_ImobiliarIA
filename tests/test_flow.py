import unicodedata
from unittest.mock import patch

from agent.controller import handle_message
from agent.state import store
from agent import llm as llm_module


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def test_happy_path_rent_manaira():
    """Teste com fallback deterministico para comportamento previsivel."""
    session = "t1"
    store.reset(session)

    with patch.object(llm_module, "USE_LLM", False), patch(
        "agent.extractor.extract_criteria",
        return_value={
            "city": "Joao Pessoa",
            "neighborhood": "Manaira",
            "property_type": "apartamento",
            "bedrooms": 2,
            "budget": 3000,
        },
    ):
        resp = handle_message(session, "quero alugar um ape em Manaira ate 3 mil, 2 quartos")

    assert resp["state"]["intent"] == "alugar"
    assert resp["state"]["criteria"]["neighborhood"] == "Manaira"
    assert resp["state"]["criteria"]["bedrooms"] == 2


def test_missing_location_triggers_question():
    """Teste que pergunta localização quando falta."""
    session = "t2"
    store.reset(session)

    with patch.object(llm_module, "USE_LLM", False):
        resp = handle_message(session, "quero alugar por 2000 um apartamento")

    reply_norm = _normalize(resp["reply"])
    assert any(
        token in reply_norm
        for token in ("cidade", "bairro", "localiza", "joao pessoa", "cabedelo")
    )


def test_zero_results_handles_gracefully():
    """Teste que lida bem com zero resultados."""
    session = "t3"
    store.reset(session)

    with patch.object(llm_module, "USE_LLM", False), patch(
        "agent.extractor.extract_criteria",
        return_value={
            "city": "Joao Pessoa",
            "neighborhood": "Manaira",
            "property_type": "casa",
            "budget": 100,
        },
    ):
        resp = handle_message(session, "quero alugar casa em Manaira ate 100 reais")

    assert resp["state"]["intent"] == "alugar"
    assert resp["state"]["criteria"]["city"] == "Joao Pessoa"
    assert resp["state"]["criteria"]["budget"] == 100
