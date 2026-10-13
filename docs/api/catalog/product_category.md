# ProductCategory API

## Purpose and access

Represents ordered product-to-category links and the single primary category. It is authenticated and read-only; writes occur only through Product create/update services.

## Endpoints and filters

- `GET /api/catalog/product-category/`
- `GET /api/catalog/product-category/{id}/`
- Filter by `product`, `category`, or `is_primary`; order by `sort_order`.

A response contains UUID IDs, `is_primary`, and `sort_order`. Direct POST/PATCH/DELETE returns `405`. Missing links return `404`; malformed UUID filters return `400`. Product services reject empty category sets and primary categories not present in `category_ids`. Related models: `Product` and `Category`.
