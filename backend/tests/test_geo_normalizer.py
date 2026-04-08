from agent.geo_normalizer import canonical_city, canonical_neighborhood, location_key


def test_canonical_city_aliases():
    assert canonical_city("joão pessoa") == "Joao Pessoa"
    assert canonical_city("JP") == "Joao Pessoa"
    assert canonical_city("santa_rita") == "Santa Rita"


def test_canonical_neighborhood_from_known_registry():
    known = ["Manaira", "Tambaú", "Cabo Branco"]
    assert canonical_neighborhood("manaíra", known=known) == "Manaira"
    assert canonical_neighborhood("cabo_branco", known=known) == "Cabo Branco"


def test_location_key_collapses_variants():
    assert location_key("  Tambaú  ") == "tambau"
    assert location_key("TAMBAU") == "tambau"
    assert location_key("tamba_u") == "tamba u"
