# StockMovement API

## Purpose and access

Provides immutable stock history plus protected receiving and correction commands. Authentication is required. Existing rows cannot be edited or deleted.

## Endpoints and filters

- `GET /api/inventory/stock-movement/` and `GET .../{id}/`
- `POST /api/inventory/stock-movement/receive/`
- `POST /api/inventory/stock-movement/adjust/`
- Filter by `variant`, `movement_type`, `order`, or `recorded_by`; date filters `from`, `to`; search SKU/product/reference/note; order by time, quantity, or landed cost.

Receive requires a UUID `Idempotency-Key` header and accepts `{ "variant_id":"uuid", "quantity":3, "price_paid_cents":1000, "tax_cents":1, "fees_cents":0, "note":"restock" }`. It locks the balance, applies deterministic half-up per-unit landed cost, increases stock, and appends one movement atomically. A repeated key returns the original response with `replayed: true` and no second stock change.

Adjust accepts `{ "variant_id":"uuid", "quantity_delta":-1, "reason":"damage", "note":"..." }`. Delta cannot be zero, damage must reduce stock, and the result cannot be negative or below promised. These failures return `400`; an invalid/missing idempotency key returns `400`; state conflicts use `409`. Related models: `InventoryBalance`, `ProductVariant`, optional `Order`, `User`, and `AuditEvent`.
