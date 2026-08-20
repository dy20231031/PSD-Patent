from engine.ontology.loader import load_all_knowledge, build_canonical_indexes
from engine.ontology.validator import validate_knowledge_base

def test_knowledge_base_validates():
    assert validate_knowledge_base() == []

def test_expected_counts():
    kb=load_all_knowledge()
    assert len(kb["claim_elements"]["items"]) == 144
    assert len(kb["functions"]["items"]) == 69
    assert len(kb["relations"]["items"]) == 46
    assert len(kb["states_modes"]["state_dimensions"]) == 10
    assert len(kb["states_modes"]["operation_modes"]) == 4
    assert len(kb["constraints"]["items"]) == 12
    assert len(kb["constraints"]["operators"]) == 18
    assert len(kb["constraints"]["context_qualifiers"]) == 8
    assert len(kb["problems"]["items"]) == 47
    assert len(kb["effects_design_attributes"]["effects"]) == 65
    assert len(kb["effects_design_attributes"]["design_attributes"]) == 20

def test_indexes_include_core_terms():
    idx=build_canonical_indexes()
    assert "Drive Cable" in idx["claim_elements"]
    assert "maintain_tension" in idx["functions"]
    assert "guided_by" in idx["relations"]
    assert "tension_loss_or_slack" in idx["problems"]
    assert "stabilize_tension" in idx["effects"]
