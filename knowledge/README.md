# PSD JSON Knowledge Base

This directory is the machine-readable representation of the frozen PSD patent knowledge engineering artifacts.

## Source versions

- PSD Core Taxonomy v1.4
- Claim Element & Component Dictionary v1.3
- Function Vocabulary v1.2
- Relation Vocabulary v1.2
- State / Mode & Claim Constraint Vocabulary v1.1
- Problem Vocabulary v1.1
- Effect / Design Attribute Vocabulary v1.1
- PSD Core Ontology v1.0

## Files

- `taxonomy.json`: 73 technology nodes + 18 architecture values
- `claim_elements.json`: 144 canonical Claim Elements
- `functions.json`: 69 canonical Functions
- `relations.json`: 46 canonical Relations
- `states_modes.json`: 10 state dimensions + 4 operation modes
- `constraints.json`: 12 constraint types + 18 operators + 8 context qualifiers
- `problems.json`: 47 canonical Problems
- `effects_design_attributes.json`: 65 Effects + 20 Design Attributes
- `ontology_meta.json`: integrated ontology classes, edges, evidence rules, validation rules, and report mapping

## Important runtime rules

1. Original patent expressions and evidence must be preserved.
2. Unknown elements/problems/effects may remain `unmapped_candidate`; do not force normalization.
3. `Typical / Compatible Taxonomy` is a hint, not an automatic patent technology label.
4. Domain inference (E4/PE4/EE4) must not be emitted as Patent Fact.
5. Problem-to-Effect connections require patent-specific evidence.
