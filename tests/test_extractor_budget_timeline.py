from agent.extractor import extract_criteria, parse_budget_range


def test_budget_and_timeline_from_currency_and_days():
    result = extract_criteria("orcamento mensal ate R$ 1800 e mudanca em 30d", [])
    assert result.get("budget") == 1800
    assert result.get("timeline") == "30d"


def test_budget_and_timeline_from_currency_and_months():
    result = extract_criteria("orcamento ate R$ 450000 e prazo 3m", [])
    assert result.get("budget") == 450000
    assert result.get("timeline") == "3m"


def test_budget_range_with_suffixes():
    parsed = parse_budget_range("entre 800 mil e 1.2 milhao")
    assert parsed.get("budget_min") == 800000
    assert parsed.get("budget_max") == 1200000
    assert parsed.get("is_range") is True


def test_budget_with_million_and_timeline():
    result = extract_criteria("orcamento de 1.2 milhao e mudanca em 6m", [])
    assert result.get("budget") == 1200000
    assert result.get("timeline") == "6m"
