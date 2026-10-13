# Category API

## Purpose and access

Maintains the product category hierarchy. All operations require owner authentication; unsafe session requests require CSRF.

## Endpoints and filters

- `GET|POST /api/custom/category/`
- `GET|PUT|PATCH|DELETE /api/custom/category/{id}/`
- Filters: `status`, `parent_id`; search: `name`, `slug`; ordering: `name`, `sort_order`, timestamps.

Create example: `{ "name":"Shirts", "parent_id":"uuid", "status":"active", "sort_order":0 }`. Slugs are collision-safe and generated server-side. Names are trimmed; case-insensitive duplicate sibling names, self-parenting, and cycles return `400`. Deletion returns `409` when children/product links exist or the slug is reserved for special-stock workflows. Responses include derived `child_count` and `product_count`. Related model: `ProductCategory`.
