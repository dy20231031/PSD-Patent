# V0.6.2 Stage 1 & 2 Visualization Update

## What was added

This update adds the **stable visualization layer** discussed for the deployed patent report UI.

### Stage 1 additions
- PSD technology / problem / function tag badges
- dependent-claim tree style view
- operation-principle step flow cards
- cleaner report-first layout
- related-patent comparison table retained in public-report style

### Stage 2 additions
- independent-claim component map
- relation structure visualization (stable relation cards)
- Module 2 comparison summary cards
- Module 2 technology-development flow strip
- per-related-patent comparison cards for common points / differences

## Stability decisions
- No Stage 3 patent-figure embedding was added.
- Deprecated `use_container_width` usage was replaced with `width="stretch"`.
- No backend extraction logic was changed; this update is focused on rendering and UX.

## Main file changed
- `streamlit_app.py`

## Compatibility
- Compatible with the V0.6.1 two-call optimized backend.
- Test status: `29 passed`
