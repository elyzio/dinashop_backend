# Payment API

## Endpoints

```text
GET  /api/payment/payment/
GET  /api/payment/payment/{id}/
POST /api/payment/payment/record/
GET  /api/payment/payment/{id}/receipt/
```

List filters include `order`, `method`, `received_by`, `from`, `to`, `search`, and `ordering`. Payments are immutable: PATCH and DELETE return `405`.

## Record example

```http
POST /api/payment/payment/record/
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

{
  "order_id":"uuid",
  "order_version":4,
  "amount_cents":5000,
  "method":"cash",
  "tendered_cents":10000,
  "external_reference":"",
  "occurred_at":"2026-10-14T03:00:00Z"
}
```

The server locks the order, rejects overpayment, allocates a `PAY-` number, calculates `change_cents`, records the authenticated actor, increments the order version, and returns `payment` plus `replayed`. For bank transfer or card, omit `tendered_cents`; card means an external terminal already completed the transaction.

Receipt GET returns payment, order snapshots/totals, and business settings.

## Errors

- `400 validation_error`: missing cash tender, non-cash tender, or invalid values.
- `409 stale_order`: version mismatch.
- `409 overpayment`: amount exceeds the current balance.
- `409 terminal_order`: cancelled/completed order.
- `409 idempotency_conflict`: key reused with different payment data.
- `405`: update/delete unsupported.
