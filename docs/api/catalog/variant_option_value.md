# VariantOptionValue API

## Purpose and access

Links one variant to exactly one value for each product option. Endpoints require authentication and are read-only; variant-grid services own all mutations.

## Endpoints and filters

- `GET /api/catalog/variant-option-value/`
- `GET /api/catalog/variant-option-value/{id}/`
- Filter by `variant`, `option`, `value`, or product through the variant.

Responses expose UUID references for the assignment. Direct writes return `405`; missing records return `404`. Services reject duplicate option/value assignments and any option or value belonging to a different product. Related models: `ProductVariant`, `ProductOption`, and `ProductOptionValue`.
