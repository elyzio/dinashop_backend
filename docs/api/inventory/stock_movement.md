# StockMovement API

## Purpose and access

Provides immutable stock history plus protected receiving and correction commands. Authentication is required. Existing rows cannot be edited or deleted.

Order fulfilment appends `sold` movements. Special-line receiving appends `received` movements for hidden special-stock variants. Refunds append `returned` movements and, for damaged goods, a compensating `damaged` movement. These records are produced only by their owning transactional services.

## Endpoints and filters

- `GET /api/inventory/stock-movement/` and `GET .../{id}/`
- `POST /api/inventory/stock-movement/receive/`
- `POST /api/inventory/stock-movement/adjust/`
- Filter by `variant`, `movement_type`, `order`, or `recorded_by`; date filters `from`, `to`; search SKU/product/reference/note; order by time, quantity, or landed cost.

Receive requires a UUID `Idempotency-Key` header and accepts `{ "variant_id":"uuid", "quantity":3, "price_paid_cents":1000, "tax_cents":1, "fees_cents":0, "note":"restock" }`. It locks the balance, applies deterministic half-up per-unit landed cost, increases stock, and appends one movement atomically. A repeated key returns the original response with `replayed: true` and no second stock change.

`price_paid_cents` is the total product cost for all units in this receipt, not a per-unit value. The landed cost is `(price_paid_cents + tax_cents + fees_cents) / quantity`, rounded half-up to integer cents. Only active variants may be received. Clients should keep the same idempotency key when retrying an unchanged form after a network failure and generate a new key after any receipt input changes.

Adjust accepts `{ "variant_id":"uuid", "quantity_delta":-1, "reason":"damage", "note":"..." }`. Delta cannot be zero, damage must reduce stock, and the result cannot be negative or below promised. These failures return `400`; an invalid/missing idempotency key returns `400`; state conflicts use `409`. Related models: `InventoryBalance`, `ProductVariant`, optional `Order`, `User`, and `AuditEvent`.

## Usage examples

### List and retrieve movements

```http
GET /api/inventory/stock-movement/?variant=<variant-uuid>&movement_type=received&from=2026-10-01&to=2026-10-31&search=SHIRT&ordering=-created_at
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"469d44b2-66f7-45d4-92d5-b4a6ffdfc4c7",
    "variant":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "sku":"SHIRT-BLACK",
    "movement_type":"received",
    "quantity_delta":3,
    "reference":"RECEIVE-550E8400-E29B-41D4-A716-446655440000",
    "order":null,
    "price_paid_cents":1000,
    "tax_cents":1,
    "fees_cents":0,
    "landed_cost_cents":334,
    "note":"Supplier delivery",
    "idempotency_key":"550e8400-e29b-41d4-a716-446655440000",
    "recorded_by":"81db6f41-8a94-4d1c-aea2-37f2c63efdb2",
    "recorded_by_email":"owner@example.com",
    "created_at":"2026-10-13T01:00:00Z"
  }]
}
```

Exact filters are `variant`, `movement_type`, `order`, and `recorded_by`. Search checks SKU, product name, reference, and note. Retrieve one movement with `GET /api/inventory/stock-movement/{id}/`.

### Receive stock

```http
POST /api/inventory/stock-movement/receive/
Authorization: Bearer <access-token>
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "variant_id":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
  "quantity":3,
  "price_paid_cents":1000,
  "tax_cents":1,
  "fees_cents":0,
  "order_id":null,
  "note":"Supplier delivery"
}
```

The first request returns `201`:

```json
{
  "movement":{
    "id":"469d44b2-66f7-45d4-92d5-b4a6ffdfc4c7",
    "variant":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "sku":"SHIRT-BLACK",
    "movement_type":"received",
    "quantity_delta":3,
    "reference":"RECEIVE-550E8400-E29B-41D4-A716-446655440000",
    "order":null,
    "price_paid_cents":1000,
    "tax_cents":1,
    "fees_cents":0,
    "landed_cost_cents":334,
    "note":"Supplier delivery",
    "idempotency_key":"550e8400-e29b-41d4-a716-446655440000",
    "recorded_by":"81db6f41-8a94-4d1c-aea2-37f2c63efdb2",
    "recorded_by_email":"owner@example.com",
    "created_at":"2026-10-13T01:00:00Z"
  },
  "balance":{
    "id":"115655c7-13c3-4470-a455-0fa887b560f3",
    "variant":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "sku":"SHIRT-BLACK",
    "product_id":"0e59eca9-9284-4861-9f29-413899c29fca",
    "product_name":"Classic T-Shirt",
    "in_hand":3,
    "promised":0,
    "available":3,
    "last_landed_cost_cents":334,
    "updated_at":"2026-10-13T01:00:00Z"
  },
  "replayed":false
}
```

Repeating the same UUID key returns `200` with the original movement and `replayed: true`; stock is not increased again.

### Correct stock

```http
POST /api/inventory/stock-movement/adjust/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "variant_id":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
  "quantity_delta":-1,
  "reason":"damage",
  "note":"Damaged during handling"
}
```

Success returns `201` with `movement` and the updated `balance`. Damage creates a `damaged` movement; `count_correction`, `found_stock`, and `other` create an `adjustment` movement.

### Update and delete behavior

Existing movement rows are immutable. `PATCH` and `DELETE` are not exposed. Correct a previous operational mistake with a new explicit adjustment/reversal workflow rather than editing history.

Order-linked movement commands are documented under [OrderLine receiving](../order/order_line.md), [Order fulfilment](../order/order.md), [Refund](../payment/refund.md), and [DeliveryJob](../fulfillment/delivery_job.md).

## Error examples

Missing or malformed idempotency keys return `400`:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"idempotency_key":["The Idempotency-Key header must be a UUID."]}
  }
}
```

An adjustment below zero or below promised stock returns `400`:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"quantity_delta":["In-hand stock cannot be lower than promised stock."]}
  }
}
```

Zero delta, positive damage, inactive/unknown receiving variants, or negative money values also return `400`. An unknown movement UUID returns `404`; missing authentication returns `401`; direct collection POST, PATCH, or DELETE returns `405`.
