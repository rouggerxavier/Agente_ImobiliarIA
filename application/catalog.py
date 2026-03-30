"""
[M3] Catálogo / Imóveis — busca, recomendação e ingestão.

Casos de uso:
- SearchProperties: filtros estruturados
- RecommendProperties: matching perfil ↔ imóvel com score e ranking
- ExplainRecommendation: pitch de venda por imóvel
- IngestProperty: adiciona/atualiza imóvel
- ArchiveProperty: remove do catálogo ativo
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from domain.entities import Lead, Property, Recommendation
from domain.enums import PropertyPurpose, PropertyStatus, PropertyType
from domain.repositories import PropertyRepository, RecommendationRepository
from application.catalog_semantic import SemanticCatalogSearch, HybridResult
from core.trace import get_logger

logger = get_logger(__name__)


@dataclass
class PropertyMatch:
    """Resultado de matching entre lead e imóvel."""
    property: Property
    match_score: float          # 0.0 → 1.0
    match_reasons: List[str]    # Por que foi recomendado
    sales_pitch: str            # Frase orientada a venda
    rank: int = 1


@dataclass
class SearchFilters:
    """Filtros estruturados para busca de imóveis."""
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    purpose: Optional[PropertyPurpose] = None
    property_type: Optional[PropertyType] = None
    bedrooms_min: Optional[int] = None
    budget_max: Optional[int] = None
    budget_min: Optional[int] = None
    parking_min: Optional[int] = None
    furnished: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    allows_short_term_rental: Optional[bool] = None
    leisure_required: Optional[bool] = None
    condo_max: Optional[int] = None
    limit: int = 5
    order_by: str = "relevance"  # "relevance" | "price_asc" | "price_desc" | "newest"


class CatalogService:
    """
    [M3] Serviço de catálogo de imóveis.

    Responsável por busca estruturada e recomendação com matching.
    Não chama LLM diretamente — recebe pitch gerado externamente.
    """

    def __init__(
        self,
        property_repo: PropertyRepository,
        recommendation_repo: Optional[RecommendationRepository] = None,
    ) -> None:
        self._properties = property_repo
        self._recommendations = recommendation_repo
        self._semantic = SemanticCatalogSearch()
        self._semantic_ready = False

    def build_semantic_index(self) -> None:
        """
        Constrói o índice semântico TF-IDF sobre todos os imóveis disponíveis.
        Deve ser chamado após ingestão ou na inicialização.
        """
        all_props = self._properties.search(status=PropertyStatus.AVAILABLE, limit=9999)
        self._semantic.rebuild_index(all_props)
        self._semantic_ready = True
        logger.info("semantic_index_built", extra={"size": self._semantic.index_size})

    def build_filters_for_lead(self, lead: Lead, limit: int = 5) -> SearchFilters:
        pref = lead.preferences
        return SearchFilters(
            city=pref.city,
            neighborhood=pref.neighborhood,
            purpose=self._target_purpose_for_lead(lead),
            property_type=pref.property_type,
            bedrooms_min=pref.bedrooms_min,
            budget_max=pref.budget_max,
            budget_min=pref.budget_min,
            furnished=pref.furnished,
            pet_friendly=pref.pet_friendly,
            allows_short_term_rental=pref.allows_short_term_rental,
            condo_max=pref.condo_max,
            limit=limit,
        )

    def can_recommend(self, lead: Lead) -> bool:
        pref = lead.preferences
        has_location = bool(pref.city or pref.neighborhood)
        has_budget = pref.budget_max is not None and pref.budget_max > 0
        has_type = pref.property_type is not None
        return bool(pref.intent and has_location and has_budget and has_type)

    def serialize_matches(self, matches: List[PropertyMatch], intent: Optional[str] = None) -> List[Dict[str, Any]]:
        serialized: List[Dict[str, Any]] = []
        for match in matches:
            prop = match.property
            serialized.append(
                {
                    "id": prop.external_ref or prop.id,
                    "property_id": prop.id,
                    "external_ref": prop.external_ref,
                    "titulo": prop.highlights[0] if prop.highlights else f"{prop.property_type.value.title()} em {prop.neighborhood}",
                    "bairro": prop.neighborhood,
                    "cidade": prop.city,
                    "quartos": prop.bedrooms,
                    "suites": prop.suites,
                    "banheiros": prop.bathrooms,
                    "vagas": prop.parking,
                    "area_m2": prop.area_m2,
                    "preco_venda": prop.price,
                    "preco_aluguel": prop.rent_price,
                    "descricao_curta": match.sales_pitch,
                    "match_score": match.match_score,
                    "match_reasons": list(match.match_reasons),
                    "purpose": prop.purpose.value,
                    "intent": intent,
                }
            )
        return serialized

    def build_recommendation_reply(self, matches: List[PropertyMatch], lead: Lead) -> str:
        if not matches:
            return self.fallback_message(self.build_filters_for_lead(lead, limit=3))

        label = "compra" if self._target_purpose_for_lead(lead) == PropertyPurpose.SALE else "locação"
        lines = [f"Encontrei estas opções para {label}:"]
        for idx, match in enumerate(matches[:3], start=1):
            lines.append(f"{idx}. {match.sales_pitch}")
        lines.append("Se quiser, eu também posso refinar por bairro, orçamento ou tipologia.")
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Busca estruturada
    # ─────────────────────────────────────────────────────────────────────────

    def search(self, filters: SearchFilters) -> List[Property]:
        """
        Busca imóveis por filtros estruturados.
        Retorna lista ordenada por relevância simples.
        """
        results = self._properties.search(
            city=filters.city,
            neighborhood=filters.neighborhood,
            purpose=filters.purpose,
            property_type=filters.property_type,
            bedrooms_min=filters.bedrooms_min,
            budget_max=filters.budget_max,
            budget_min=filters.budget_min,
            status=PropertyStatus.AVAILABLE,
            limit=filters.limit * 3,  # busca extra para poder rankar
            order_by=filters.order_by,
        )

        # Aplica filtros adicionais que o repositório pode não suportar
        filtered = self._apply_extra_filters(results, filters)

        logger.info(
            "catalog_search",
            extra={
                "filters": {k: v for k, v in filters.__dict__.items() if v is not None},
                "total_found": len(filtered),
            },
        )
        return filtered[: filters.limit]

    def _apply_extra_filters(self, properties: List[Property], f: SearchFilters) -> List[Property]:
        out = []
        for p in properties:
            if f.furnished is not None and p.furnished is not None and p.furnished != f.furnished:
                continue
            if f.pet_friendly is not None and p.pet_friendly is not None and p.pet_friendly != f.pet_friendly:
                continue
            if f.allows_short_term_rental is not None and p.allows_short_term_rental is not None:
                if p.allows_short_term_rental != f.allows_short_term_rental:
                    continue
            if f.condo_max is not None and p.condo_fee is not None and p.condo_fee > f.condo_max:
                continue
            if f.parking_min is not None and p.parking is not None and p.parking < f.parking_min:
                continue
            if f.leisure_required and not p.amenities.has_pool and not p.amenities.has_gym:
                continue
            out.append(p)
        return out

    def hybrid_search(
        self,
        query: str,
        filters: SearchFilters,
        semantic_weight: float = 0.4,
    ) -> List["HybridResult"]:
        """
        Busca híbrida: aplica filtros estruturados e depois reranking semântico.

        Args:
            query: Texto livre (ex: "2 quartos perto da praia com piscina")
            filters: Filtros estruturados aplicados antes do reranking
            semantic_weight: Peso do componente semântico (0.0–1.0)

        Returns:
            Lista de HybridResult ordenada por score combinado.
        """
        if not self._semantic_ready:
            self.build_semantic_index()

        candidates = self.search(filters)
        if not candidates:
            return []

        return self._semantic.hybrid_search(
            query=query,
            candidates=candidates,
            semantic_weight=semantic_weight,
            structural_weight=1.0 - semantic_weight,
            top_k=filters.limit,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Recomendação com matching
    # ─────────────────────────────────────────────────────────────────────────

    def recommend(
        self,
        lead: Lead,
        conversation_id: str = "",
        limit: int = 3,
        allow_alternatives: bool = True,
    ) -> List[PropertyMatch]:
        """
        Recomenda imóveis para o lead com base em seu perfil.

        - Filtra por perfil completo primeiro.
        - Se não houver resultados exatos, oferece alternativas controladas
          (flexibiliza um critério por vez) quando allow_alternatives=True.
        - Persiste as recomendações no RecommendationRepository se disponível.
        - Garante que imóvel incompatível com perfil seja sinalizado.
        """
        filters = self.build_filters_for_lead(lead, limit=limit * 4)

        candidates = self.search(filters)
        is_alternative = False

        if not candidates and allow_alternatives:
            candidates, is_alternative = self._search_alternatives(filters, lead, limit)

        if not candidates:
            logger.info("no_properties_found", extra={"lead_id": lead.id})
            return []

        # Calcula score e filtra imóveis incompatíveis antes de rankar
        matches = []
        for p in candidates:
            incompatibilities = self._check_incompatibilities(lead, p, filters.purpose)
            if incompatibilities and not is_alternative:
                # Imóvel incompatível com critério essencial — pula
                logger.debug(
                    "property_incompatible",
                    extra={"property_id": p.id, "reasons": incompatibilities},
                )
                continue
            match = self._score_match(lead, p, filters.purpose)
            if is_alternative:
                match.match_reasons.insert(0, "Alternativa próxima ao seu perfil")
            matches.append(match)

        matches.sort(key=lambda m: m.match_score, reverse=True)

        for i, m in enumerate(matches[:limit]):
            m.rank = i + 1

        # Persiste recomendações
        if self._recommendations and conversation_id:
            for m in matches[:limit]:
                rec = Recommendation(
                    lead_id=lead.id,
                    conversation_id=conversation_id,
                    property_id=m.property.id,
                    rank=m.rank,
                    match_score=m.match_score,
                    match_reasons=m.match_reasons,
                    sales_pitch=m.sales_pitch,
                    shown_to_lead=True,
                )
                self._recommendations.save(rec)

        logger.info(
            "properties_recommended",
            extra={
                "lead_id": lead.id,
                "count": len(matches[:limit]),
                "is_alternative": is_alternative,
            },
        )
        return matches[:limit]

    def _check_incompatibilities(self, lead: Lead, prop: Property, purpose: Optional[PropertyPurpose]) -> List[str]:
        """
        Verifica se o imóvel é incompatível com critérios essenciais do lead.
        Retorna lista de incompatibilidades; vazia = compatível.
        """
        pref = lead.preferences
        issues: List[str] = []

        # Imóvel indisponível
        if not prop.is_showable():
            issues.append(f"Imóvel com status {prop.status.value}")

        # Orçamento estourado por mais de 20% (tolerância de 20%)
        price = self._price_for_property(prop, purpose)
        if pref.budget_max and price and price > pref.budget_max * 1.20:
            issues.append(
                f"Preço R$ {price:,.0f} acima do orçamento R$ {pref.budget_max:,.0f}".replace(",", ".")
            )

        # Pet obrigatório mas imóvel não aceita
        if pref.pet_friendly and prop.pet_friendly is False:
            issues.append("Lead precisa de imóvel pet-friendly")

        return issues

    def _search_alternatives(
        self, filters: SearchFilters, lead: Lead, limit: int
    ) -> tuple:
        """
        Tenta encontrar alternativas flexibilizando critérios um por vez.
        Retorna (candidates, True) se encontrou alternativas, senão ([], False).

        Ordem de flexibilização:
        1. Remove filtro de bairro
        2. Amplia orçamento em 15%
        3. Reduz quartos mínimos em 1
        4. Remove filtro de tipo de imóvel
        """
        relaxations = [
            ("neighborhood", None),
            ("budget_max", int(filters.budget_max * 1.15) if filters.budget_max else None),
            ("bedrooms_min", max(1, (filters.bedrooms_min or 1) - 1)),
            ("property_type", None),
        ]

        for field_name, new_value in relaxations:
            relaxed = SearchFilters(
                city=filters.city,
                neighborhood=filters.neighborhood,
                purpose=filters.purpose,
                property_type=filters.property_type,
                bedrooms_min=filters.bedrooms_min,
                budget_max=filters.budget_max,
                budget_min=filters.budget_min,
                furnished=filters.furnished,
                pet_friendly=filters.pet_friendly,
                condo_max=filters.condo_max,
                limit=limit * 4,
            )
            setattr(relaxed, field_name, new_value)
            candidates = self.search(relaxed)
            if candidates:
                logger.info(
                    "alternatives_found",
                    extra={"lead_id": lead.id, "relaxed_field": field_name, "count": len(candidates)},
                )
                return candidates, True

        return [], False

    def _score_match(self, lead: Lead, prop: Property, purpose: Optional[PropertyPurpose]) -> PropertyMatch:
        """
        Calcula score de compatibilidade entre lead e imóvel.
        Retorna PropertyMatch com score 0.0–1.0 e razões.
        """
        pref = lead.preferences
        score = 0.0
        reasons: List[str] = []
        max_score = 0.0

        # Orçamento (peso 30%)
        max_score += 0.30
        price = self._price_for_property(prop, purpose)
        if pref.budget_max and price:
            if price <= pref.budget_max:
                ratio = price / pref.budget_max
                score += 0.30 * (1.0 - max(0, ratio - 0.7))
                reasons.append(f"Preço dentro do orçamento (R$ {price:,.0f})".replace(",", "."))

        # Quartos (peso 25%)
        max_score += 0.25
        if pref.bedrooms_min and prop.bedrooms:
            if prop.bedrooms >= pref.bedrooms_min:
                score += 0.25
                reasons.append(f"{prop.bedrooms} quartos (mín. {pref.bedrooms_min})")

        # Localização (peso 20%)
        max_score += 0.20
        if pref.city and prop.city:
            if pref.city.lower() in prop.city.lower():
                score += 0.10
                reasons.append(f"Cidade: {prop.city}")
        if pref.neighborhood and prop.neighborhood:
            if pref.neighborhood.lower() in prop.neighborhood.lower():
                score += 0.10
                reasons.append(f"Bairro: {prop.neighborhood}")

        # Tipo (peso 10%)
        max_score += 0.10
        if pref.property_type and prop.property_type:
            if pref.property_type == prop.property_type:
                score += 0.10
                reasons.append(f"Tipo: {prop.property_type.value}")

        # Pet (peso 5%)
        max_score += 0.05
        if pref.pet_friendly and prop.pet_friendly:
            score += 0.05
            reasons.append("Aceita pets")

        # Lazer (peso 5%)
        max_score += 0.05
        if pref.leisure_required and (prop.amenities.has_pool or prop.amenities.has_gym):
            score += 0.05
            reasons.append("Área de lazer disponível")

        # Condomínio (peso 5%)
        max_score += 0.05
        if pref.condo_max and prop.condo_fee and prop.condo_fee <= pref.condo_max:
            score += 0.05
            reasons.append(f"Condomínio R$ {prop.condo_fee:,.0f}".replace(",", "."))

        normalized = score / max_score if max_score > 0 else 0.0

        # Pitch de venda básico — será enriquecido com LLM na Fase 5
        pitch = self._build_pitch(prop, reasons, purpose)

        return PropertyMatch(
            property=prop,
            match_score=round(normalized, 3),
            match_reasons=reasons,
            sales_pitch=pitch,
        )

    def _build_pitch(self, prop: Property, reasons: List[str], purpose: Optional[PropertyPurpose]) -> str:
        """
        Gera pitch de venda orientado a conversão.
        Destaca diferenciais relevantes para o lead.
        """
        parts = []
        if prop.bedrooms:
            suite_txt = f" ({prop.suites} suíte{'s' if (prop.suites or 0) > 1 else ''})" if prop.suites else ""
            parts.append(f"{prop.bedrooms} quartos{suite_txt}")
        if prop.area_m2:
            parts.append(f"{prop.area_m2:.0f}m²")
        if prop.neighborhood:
            parts.append(f"no {prop.neighborhood}")
        if prop.city:
            parts.append(f"em {prop.city}")

        price = self._price_for_property(prop, purpose)
        if price:
            label = "Aluguel" if purpose == PropertyPurpose.RENT else "Venda"
            parts.append(f"{label}: R$ {price:,.0f}".replace(",", "."))

        # Destaques de amenidades
        highlights = []
        if prop.amenities.has_pool:
            highlights.append("piscina")
        if prop.amenities.has_gym:
            highlights.append("academia")
        if prop.amenities.has_gourmet_area:
            highlights.append("área gourmet")
        if prop.amenities.has_balcony:
            highlights.append("varanda")
        if prop.furnished:
            highlights.append("mobiliado")
        if prop.pet_friendly:
            highlights.append("aceita pets")
        if prop.micro_location:
            highlights.append(prop.micro_location)

        desc = " | ".join(parts) if parts else "Imóvel disponível"
        if highlights:
            desc += f" — {', '.join(highlights[:3])}"
        if reasons:
            compat = "; ".join(r for r in reasons[:2] if "Alternativa" not in r)
            if compat:
                desc += f". Atende: {compat}."
        return desc

    def _target_purpose_for_lead(self, lead: Lead) -> PropertyPurpose:
        intent = lead.preferences.intent.value if lead.preferences.intent else ""
        return PropertyPurpose.RENT if intent == "alugar" else PropertyPurpose.SALE

    def _price_for_property(self, prop: Property, purpose: Optional[PropertyPurpose]) -> int:
        if purpose == PropertyPurpose.RENT:
            return prop.rent_price or prop.price or 0
        if purpose == PropertyPurpose.SALE:
            return prop.price or prop.rent_price or 0
        return prop.price or prop.rent_price or 0

    # ─────────────────────────────────────────────────────────────────────────
    # Ingestão
    # ─────────────────────────────────────────────────────────────────────────

    def ingest(self, prop: Property) -> Property:
        """Adiciona ou atualiza imóvel no catálogo."""
        # Valida campos obrigatórios
        if not prop.city or not prop.property_type:
            raise ValueError("Imóvel precisa de city e property_type")

        saved = self._properties.save(prop)
        logger.info(
            "property_ingested",
            extra={"property_id": saved.id, "city": saved.city, "type": saved.property_type.value},
        )
        return saved

    def archive(self, property_id: str) -> None:
        """Remove imóvel do catálogo ativo (soft delete via status)."""
        prop = self._properties.get_by_id(property_id)
        if prop is None:
            raise ValueError(f"Imóvel {property_id} não encontrado")
        prop.status = PropertyStatus.OFF_MARKET
        self._properties.save(prop)
        logger.info("property_archived", extra={"property_id": property_id})

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback para ausência de resultados
    # ─────────────────────────────────────────────────────────────────────────

    def fallback_message(self, filters: SearchFilters) -> str:
        """Mensagem quando não há imóveis compatíveis."""
        parts = []
        if filters.city:
            parts.append(f"em {filters.city}")
        if filters.neighborhood:
            parts.append(f"no {filters.neighborhood}")
        if filters.budget_max:
            parts.append(f"até R$ {filters.budget_max:,.0f}".replace(",", "."))
        context = " ".join(parts) or "com esses critérios"
        return (
            f"Ainda não temos imóveis disponíveis {context} no momento. "
            "Vou repassar seu perfil para nosso corretor, que pode ter opções "
            "que ainda não estão no sistema. Podemos entrar em contato com você?"
        )
