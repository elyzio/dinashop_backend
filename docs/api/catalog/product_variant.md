# ProductVariant API

## Purpose and access

Represents a sellable SKU with server-authoritative pricing and derived stock. The base endpoints are authenticated/read-only; pricing is a protected service command.

## Endpoints and filters

- `GET /api/catalog/product-variant/`
- `GET /api/catalog/product-variant/{id}/`
- `PATCH /api/catalog/product-variant/{id}/pricing/`
- Filter by `product`, `is_active`; search SKU/product/brand; order by SKU, price, or timestamps.

Pricing example: `{ "selling_price_cents":2750, "sale_price_cents":2200, "sale_starts_at":"2026-10-12T00:00:00Z", "sale_ends_at":"2026-10-20T00:00:00Z" }`. The row is locked, dates and non-negative cents validated, and changed fields append immutable `PriceHistory`. Responses include selected options plus `in_hand`, `promised`, `available`, and active price. Direct base mutations return `405`; duplicate SKU/invalid sale windows return `400`. Related models: `Product`, option assignments, inventory, and price history.
