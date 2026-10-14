# StockReservation API

## Purpose and access

Shows stock reserved for order lines. The authenticated API is read-only; order services create, consume, and release reservations while locking the associated balances.

## Endpoints and filters

- `GET /api/inventory/stock-reservation/`
- `GET /api/inventory/stock-reservation/{id}/`
- Filter by `variant`, `status`, or `order_line`; search SKU/order number; order by creation/release/consumption times.

Responses contain UUID relations, positive whole quantity, machine status (`active`, `consumed`, `released`), and UTC timestamps. Direct mutations return `405`; missing rows return `404`. Order creation and special-item receiving create reservations; fulfilment consumes them; cancellation, decline, and failed delivery release them. Each command updates `InventoryBalance.promised` in the same locked transaction. Related models: `InventoryBalance`, `ProductVariant`, `Order`, and `OrderLine`.

## Usage examples

### List reservations

```http
GET /api/inventory/stock-reservation/?variant=<variant-uuid>&status=active&order_line__order=<order-uuid>&search=ORD-0001&ordering=-created_at
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"817a28f0-0d53-46b3-b581-ad98a05cbd5d",
    "order_line":"db7a2175-b94a-41c5-913d-7723fde8a584",
    "order_id":"911296e7-8b96-4ee0-a6d9-8c54030e1df7",
    "variant":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "sku":"SHIRT-BLACK",
    "quantity":2,
    "status":"active",
    "created_at":"2026-10-13T01:00:00Z",
    "released_at":null,
    "consumed_at":null
  }]
}
```

Exact filters are `variant`, `status`, `order_line`, and `order_line__order`. Search checks variant SKU and order number. Ordering supports creation, release, and consumption times.

### Retrieve one reservation

```http
GET /api/inventory/stock-reservation/817a28f0-0d53-46b3-b581-ad98a05cbd5d/
Authorization: Bearer <access-token>
```

### Add, update, and delete behavior

There are no direct reservation commands. Use the documented order and delivery commands; both reservation endpoints remain diagnostic/read-only.

## Error examples

Direct writes return `405`:

```json
{"error":{"code":"method_not_allowed","message":"Method \"POST\" not allowed."}}
```

An unknown reservation UUID returns `404`; an invalid status or malformed relation filter returns `400`; missing authentication returns `401`.
