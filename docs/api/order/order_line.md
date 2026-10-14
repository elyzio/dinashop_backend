# OrderLine API

## Purpose and endpoints

Order lines are immutable snapshots. They can be listed or retrieved, while a special line has one protected receiving command.

```text
GET  /api/order/order-line/?order=<uuid>&kind=special&variant=<uuid>
GET  /api/order/order-line/{id}/
POST /api/order/order-line/{id}/receive/
```

List search covers order number, product name, description, and SKU. POST to the collection, PATCH, and DELETE return `405`.

## Receive a special item

```http
POST /api/order/order-line/{id}/receive/
Idempotency-Key: 9cc75343-e62d-4ca9-af3d-3792467f79bc

{"total_product_cost_cents":7000,"tax_cents":500,"fees_cents":200,"note":"October shipment"}
```

The service requires a confirmed special order, creates a hidden single-variant catalog product in `special-order-stock`, calculates landed cost with deterministic integer rounding, creates its balance, increases `in_hand` and `promised`, creates a reservation and immutable received movement, and attaches the variant to the line. When all special lines are received, the order advances to `item_received`.

Success returns `201` with `order_line`, `movement`, and `replayed`. An identical retry returns `200` without duplicating stock.

## Errors

- `400 validation_error`: negative cost values or a non-special line.
- `409 invalid_transition`: order is not confirmed.
- `409 already_received`: line already has received stock.
- `409 idempotency_conflict`: reused key has different costs or line.
- `405`: unsupported mutation.

Related models: `Product`, `ProductVariant`, `InventoryBalance`, `StockReservation`, and `StockMovement`.
