# Product API

## Purpose and access

Creates and maintains the authenticated owner's product aggregate. A create transaction includes category links, options, values, variants, assignments, and one zeroed `InventoryBalance` per variant. Images are uploaded separately.

## Endpoints and filters

- `GET|POST /api/catalog/product/`
- `GET|PUT|PATCH /api/catalog/product/{id}/`
- `PUT .../{id}/variant-grid/` — atomically replace the option/variant grid.
- `POST .../{id}/visibility/` — `{ "visibility":"hidden" }`.
- Filters: `visibility`, `category_id`; search name/brand/description/SKU; order by name, brand, or timestamps.

Create requests contain `name`, descriptions, `category_ids`, exactly one `primary_category_id`, `option_definitions`, and non-empty `variants`; see the OpenAPI schema for the full example. IDs are UUID strings and prices are integer cents. SKUs are trimmed, uppercased, and globally unique. Every variant must choose exactly one allowed value for every option. A failure rolls back the entire aggregate. Removing referenced/stocked variants deactivates them; hiding promised stock returns `409`. Related models: every catalog model, `Category`, and `InventoryBalance`.
