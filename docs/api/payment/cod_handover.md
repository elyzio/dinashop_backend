# CodHandover API

## Endpoints

```text
GET  /api/payment/cod-handover/
GET  /api/payment/cod-handover/{id}/
POST /api/payment/cod-handover/record/
GET  /api/payment/cod-handover/summary/?helper_id=<uuid>
```

List filters include helper, order, recorder, date range, search, and ordering. Handovers are append-only.

```http
POST /api/payment/cod-handover/record/
Idempotency-Key: f5343595-b1b3-4f08-81fa-b66557e76de5

{"helper_id":"uuid","order_id":"uuid","amount_cents":2000,"handed_over_at":"2026-10-14T04:00:00Z"}
```

The service locks the delivered job and existing handovers, verifies the helper/order pairing, and prevents cumulative handover above the linked COD payment. Partial handovers are valid.

Summary returns total and per-order `collected_cents`, `handed_over_cents`, and `held_cents`. Historical collected cash is not rewritten by later refunds.

Errors include `409 cod_delivery_not_found`, `409 cod_handover_exceeds_held`, `409 idempotency_conflict`, and `405` for update/delete.
