# InventoryBalance API

## Purpose and access

Provides the current stock totals for each variant. It is authenticated and read-only; receipt, adjustment, and later order services are the only writers.

## Endpoints and filters

- `GET /api/inventory/inventory-balance/`
- `GET /api/inventory/inventory-balance/{id}/`
- Filter by `variant` or product through the variant; search SKU/product; order by `in_hand`, `promised`, `updated_at`, or landed cost.

Example: `{ "variant":"uuid", "in_hand":10, "promised":3, "available":7, "last_landed_cost_cents":425 }`. Direct mutation returns `405`. The database and services enforce `0 <= promised <= in_hand`; invalid filters return `400` and missing balances `404`. Related models: `ProductVariant`, `StockReservation`, and `StockMovement`.
