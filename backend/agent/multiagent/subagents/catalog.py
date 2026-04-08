from __future__ import annotations

from typing import List

from ..contracts import OrchestratorRequest, SubagentResult
from ..skills import PropertyCatalogSearchSkill, SkillContext


def _format_catalog_reply(properties: List[dict], intent: str) -> str:
    if not properties:
        return "Nao encontrei opcoes com os filtros atuais. Posso te ajudar a ajustar bairro, quartos ou orcamento."

    intro = "Encontrei algumas opcoes para aluguel:" if intent == "alugar" else "Encontrei algumas opcoes para compra:"
    lines = [intro]

    for idx, prop in enumerate(properties[:3], start=1):
        title = prop.get("titulo") or prop.get("tipo") or "Imovel"
        neighborhood = prop.get("bairro") or "bairro nao informado"
        city = prop.get("cidade") or "cidade nao informada"
        price = prop.get("preco_aluguel") if intent == "alugar" else prop.get("preco_venda")
        if price:
            price_txt = f"R$ {int(price):,}".replace(",", ".")
        else:
            price_txt = "preco sob consulta"
        lines.append(f"{idx}. {title} - {neighborhood}, {city} - {price_txt}")

    lines.append("Se quiser, eu sigo com a triagem completa para refinar ainda mais.")
    return "\n".join(lines)


class CatalogSubagent:
    name = "catalog_subagent"

    def __init__(self) -> None:
        self._skill = PropertyCatalogSearchSkill()

    def run(self, request: OrchestratorRequest) -> SubagentResult:
        result = self._skill.run(
            SkillContext(
                session_id=request.session_id,
                message=request.message,
                correlation_id=request.correlation_id,
            )
        )

        if not result.success:
            return SubagentResult(
                payload={
                    "reply": "Nao consegui consultar o catalogo agora. Vou seguir com o fluxo padrao de triagem.",
                    "catalog_error": result.error,
                },
                handled=False,
                reason=result.error or "catalog_skill_failed",
                requires_handoff=True,
            )

        properties = result.data.get("properties") or []
        intent = result.data.get("intent", "comprar")
        reply = _format_catalog_reply(properties, intent)

        requires_handoff = len(properties) == 0
        return SubagentResult(
            payload={
                "reply": reply,
                "properties": [p.get("id") for p in properties[:6]],
                "catalog": {
                    "filters": result.data.get("filters", {}),
                    "count": len(properties),
                    "intent": intent,
                },
            },
            handled=not requires_handoff,
            reason="catalog_search",
            requires_handoff=requires_handoff,
        )

