# InventoryBalance API

## Purpose and access

Provides the current stock totals for each variant. It is authenticated and read-only; receipt, adjustment, and later order services are the only writers.

## Endpoints and filters

- `GET /api/inventory/inventory-balance/`
- `GET /api/inventory/inventory-balance/{id}/`
- Filter by `variant` or product through the variant; search SKU/product; order by `in_hand`, `promised`, `updated_at`, or landed cost.

Example: `{ "variant":"uuid", "in_hand":10, "promised":3, "available":7, "last_landed_cost_cents":425 }`. Direct mutation returns `405`. The database and services enforce `0 <= promised <= in_hand`; invalid filters return `400` and missing balances `404`. Related models: `ProductVariant`, `StockReservation`, and `StockMovement`.

## Usage examples

### List balances

```http
GET /api/inventory/inventory-balance/?variant__product=<product-uuid>&status=available&search=SHIRT&ordering=-in_hand&page=1
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"115655c7-13c3-4470-a455-0fa887b560f3",
    "variant":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "sku":"SHIRT-BLACK",
    "product_id":"0e59eca9-9284-4861-9f29-413899c29fca",
    "product_name":"Classic T-Shirt",
    "in_hand":10,
    "promised":3,
    "available":7,
    "last_landed_cost_cents":425,
    "updated_at":"2026-10-13T01:00:00Z"
  }]
}
```

Exact filters are `variant` and `variant__product`. `status=available` selects `in_hand > 0`; `status=out_of_stock` selects `in_hand = 0`. Search checks SKU, product name, and brand. Ordering supports `in_hand`, `promised`, landed cost, and update time.

### Retrieve one balance

```http
GET /api/inventory/inventory-balance/115655c7-13c3-4470-a455-0fa887b560f3/
Authorization: Bearer <access-token>
```

The response is the single balance object.

### Add, update, and delete behavior

Direct writes are disabled. A balance is created automatically when a variant is created. Receiving and adjustment commands update it under a row lock; future order services will update `promised`. Deleting a balance would break stock history and is not exposed.

## Error examples

Direct `POST`, `PATCH`, or `DELETE` returns `405`:

```json
{"error":{"code":"method_not_allowed","message":"Method \"PATCH\" not allowed."}}
```

An unknown balance UUID returns `404`; malformed variant/product filters return `400`; missing authentication returns `401`.
