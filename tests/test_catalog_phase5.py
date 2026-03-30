from application.catalog import CatalogService
from application.catalog_ingestion import CatalogIngestionService, dict_to_property
from domain.entities import Lead, LeadPreferences, Property
from domain.enums import LeadIntent, PropertyPurpose, PropertyStatus, PropertyType
from infrastructure.persistence.in_memory import InMemoryPropertyRepository


def test_inmemory_search_returns_both_purpose_for_sale_and_rent():
    repo = InMemoryPropertyRepository()
    property_model = Property(
        city="João Pessoa",
        neighborhood="Manaíra",
        property_type=PropertyType.APARTMENT,
        purpose=PropertyPurpose.BOTH,
        price=850_000,
        rent_price=4_500,
    )
    repo.save(property_model)

    sale_results = repo.search(city="João Pessoa", purpose=PropertyPurpose.SALE, status=PropertyStatus.AVAILABLE, limit=10)
    rent_results = repo.search(city="João Pessoa", purpose=PropertyPurpose.RENT, status=PropertyStatus.AVAILABLE, limit=10)

    assert [item.id for item in sale_results] == [property_model.id]
    assert [item.id for item in rent_results] == [property_model.id]


def test_dict_to_property_parses_brazilian_currency_and_preserves_false_flags():
    prop = dict_to_property(
        {
            "id": "ext-1",
            "cidade": "João Pessoa",
            "bairro": "Manaíra",
            "tipo": "apartamento",
            "preco_venda": "R$ 1.600.000,00",
            "preco_aluguel": "R$ 4.500,00",
            "mobiliado": False,
            "aceita_pet": False,
            "permite_temporada": False,
        }
    )

    assert prop.price == 1_600_000
    assert prop.rent_price == 4_500
    assert prop.furnished is False
    assert prop.pet_friendly is False
    assert prop.allows_short_term_rental is False


def test_catalog_ingestion_upserts_reactivated_property_by_external_ref():
    repo = InMemoryPropertyRepository()
    service = CatalogIngestionService(repo)
    item = {
        "id": "ext-2",
        "cidade": "João Pessoa",
        "bairro": "Manaíra",
        "tipo": "apartamento",
        "preco_venda": "R$ 900.000,00",
    }

    first_report = service.ingest_dicts([item])
    assert first_report.ingested == 1

    archive_report = service.ingest_dicts([], full_replace=True)
    assert archive_report.archived == 1

    second_report = service.ingest_dicts([item])
    all_properties = repo.search(status=None, limit=100)

    assert second_report.updated == 1
    assert len(all_properties) == 1
    assert all_properties[0].status == PropertyStatus.AVAILABLE


def test_catalog_service_formats_recommendations_from_runtime_profile():
    repo = InMemoryPropertyRepository()
    repo.save(
        Property(
            external_ref="prop-1",
            city="João Pessoa",
            neighborhood="Manaíra",
            property_type=PropertyType.APARTMENT,
            purpose=PropertyPurpose.SALE,
            price=800_000,
            bedrooms=3,
            parking=2,
            area_m2=95,
            description="Apartamento com varanda e lazer completo",
            status=PropertyStatus.AVAILABLE,
        )
    )

    service = CatalogService(repo)
    lead = Lead(
        preferences=LeadPreferences(
            intent=LeadIntent.BUY,
            city="João Pessoa",
            neighborhood="Manaíra",
            property_type=PropertyType.APARTMENT,
            budget_max=900_000,
            bedrooms_min=3,
        )
    )

    matches = service.recommend(lead, conversation_id="conv-1", limit=1)
    payload = service.serialize_matches(matches, lead.preferences.intent.value)
    reply = service.build_recommendation_reply(matches, lead)

    assert len(matches) == 1
    assert payload[0]["id"] == "prop-1"
    assert payload[0]["preco_venda"] == 800_000
    assert "Encontrei estas opções" in reply
