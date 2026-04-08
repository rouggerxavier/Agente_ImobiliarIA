from __future__ import annotations

from agent.multiagent.skills import KnowledgeLookupSkill, PropertyCatalogSearchSkill, SkillContext


def test_property_catalog_skill_handles_tool_failure(monkeypatch):
    from agent import tools

    def _raise(*args, **kwargs):
        raise RuntimeError("forced_failure")

    monkeypatch.setattr(tools, "search_properties", _raise)

    skill = PropertyCatalogSearchSkill()
    result = skill.run(SkillContext(session_id="s", message="quero catalogo em Manaira"))

    assert result.success is False
    assert result.error is not None
    assert "search_failed" in result.error


def test_knowledge_skill_returns_error_when_no_answer(monkeypatch):
    from agent.multiagent.skills import knowledge_lookup as skill_module

    monkeypatch.setattr(skill_module, "answer_question", lambda *args, **kwargs: None)

    skill = KnowledgeLookupSkill()
    result = skill.run(SkillContext(session_id="s", message="duvida muito especifica"))

    assert result.success is False
    assert result.error == "knowledge_not_found"

