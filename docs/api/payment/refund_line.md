# RefundLine API

Refund lines preserve the returned order line, quantity, disposition, allocated credit, and returned variant.

```text
GET /api/payment/refund-line/?refund=<uuid>&order_line=<uuid>&disposition=restock
GET /api/payment/refund-line/{id}/
```

Both endpoints require owner authentication. Creation occurs only through `POST /api/payment/refund/create/`; direct POST, PATCH, and DELETE return `405`. This prevents line values from diverging from refund totals and inventory movements.

Example response:

```json
{"id":"uuid","refund":"uuid","order_line":"uuid","quantity":1,"disposition":"restock","amount_cents":2499,"returned_variant":"uuid"}
```

Errors are `401/403` for authentication/CSRF, `404` for an unknown line, and `405` for unsupported writes.
