# Refund API

## Endpoints

```text
GET  /api/payment/refund/?order=<uuid>&method=cash&search=RF-0001
GET  /api/payment/refund/{id}/
POST /api/payment/refund/create/
GET  /api/payment/refund/{id}/receipt/
```

Refunds are immutable. Generic POST on the list, PATCH, and DELETE are unsupported.

## Create example

```http
POST /api/payment/refund/create/
Idempotency-Key: 4b9a7580-5f1d-4e89-bc02-8756a27aaf08

{
  "order_id":"uuid",
  "order_version":6,
  "payment_id":"uuid",
  "lines":[{"order_line_id":"uuid","quantity":1,"disposition":"restock"}],
  "method":"cash",
  "reason":"Customer return"
}
```

The server requires a fulfilled order, locks returned variants, checks cumulative quantities, proportionally allocates discounts/final-price adjustments, calculates `credit_cents` and the actual `cash_refund_cents`, assigns an `RF-` number, and creates stock effects atomically. Restock adds a reversal and increases stock; damaged creates reversal and damaged movements with no net increase.

Receipt GET returns the refund, order, payments, and business settings.

## Errors

- `400 validation_error`: duplicate/unrelated lines, blank reason, or invalid method.
- `409 not_fulfilled`: order has not been fulfilled.
- `409 refund_limit_exceeded`: cumulative quantity exceeds sold quantity.
- `409 return_variant_missing`: returned line has no traceable variant.
- `409 stale_order` or `idempotency_conflict`.
- `405`: immutable operation attempted.
