# Order API

## Purpose

Creates immutable transaction snapshots and exposes explicit state commands. Generic order PATCH and DELETE are intentionally unsupported. All endpoints require owner authentication; writes using sessions require CSRF.

## Endpoints

| Method | URL | Function |
|---|---|---|
| GET, POST | `/api/order/order/` | Search/list or idempotently create |
| GET | `/api/order/order/{id}/` | Full order and derived financial state |
| POST | `/{id}/cancel/` | Cancel and release reservations |
| POST | `/{id}/fulfill/` | Fulfil a pickup order |
| POST | `/{id}/complete/` | Complete a fulfilled zero-balance order |
| POST | `/{id}/special-transition/` | Requested → quoted → confirmed |
| POST | `/{id}/set-final-price/` | Store actual tax/final price |
| POST | `/{id}/mark-customer-notified/` | Record notification and acceptance |
| POST | `/{id}/decline/` | Decline increased special pricing |
| GET | `/{id}/receipt/` | Persisted receipt DTO |

List filters: `type=ordinary|special`, `status`, `special_status`, `payment_status`, `delivery_method`, `customer_id`, `from`, `to`, `search`, and `ordering`.

## Create example

```http
POST /api/order/order/
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

{
  "customer_id":"uuid",
  "lines":[
    {"kind":"catalog","variant_id":"uuid","quantity":2},
    {"kind":"special","description":"Imported lamp","quantity":1,"unit_price_cents":12000,"estimated_tax_cents":500}
  ],
  "discount_cents":500,
  "delivery_method":"pickup",
  "pickup_timing":"later",
  "delivery_address":"",
  "cod":false,
  "customer_accepted_price_change":true,
  "initial_payment":{"amount_cents":3000,"method":"cash","tendered_cents":5000}
}
```

The server chooses active catalog prices unless `unit_price_cents` explicitly overrides one, snapshots names/SKUs, assigns `ORD-` or `SO-`, locks stock, and returns `{ "order": {...}, "replayed": false }`. Responses include totals, balance, payment status, estimate flag, allowed actions, and `version`.

## Command examples

```json
// cancel
{"version":3,"reason":"Customer cancelled"}

// special transition
{"version":3,"target":"quoted"}

// final price
{"version":6,"final_price_cents":13200,"lines":[{"order_line_id":"uuid","actual_tax_cents":700}]}

// notification
{"version":7,"accepted_price_change":true}

// decline
{"version":7,"method":"cash","reason":"Customer declined the higher price"}
```

Every state command checks `version`; use the new version returned by the previous response. Order receipt responses contain the order, payment/refund records, and current business settings; the browser remains responsible for rendering and printing.

## Errors

- `400 validation_error`: malformed lines, missing address/contact, invalid pickup/COD combination, or discount above subtotal.
- `409 idempotency_conflict`: a creation key was reused with changed input.
- `409 stale_order`: supplied version is no longer current.
- `409 insufficient stock`/`stock_conflict`: inventory cannot satisfy the command.
- `409 invalid_transition`: command is not legal from the current state.
- `409 balance_due`: completion attempted before settlement.
- `405`: PATCH or DELETE is unsupported.

Catalog prices, totals, stock, change, balances, and allowed transitions are server authoritative.
