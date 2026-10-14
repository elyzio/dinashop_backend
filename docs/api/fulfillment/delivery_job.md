# DeliveryJob API

## Endpoints

| Method | URL | Function |
|---|---|---|
| GET, POST | `/api/fulfillment/delivery-job/` | List or assign |
| GET | `/api/fulfillment/delivery-job/{id}/` | Retrieve |
| POST | `/{id}/start/` | Assigned → out for delivery |
| POST | `/{id}/deliver/` | Fulfil and mark delivered |
| POST | `/{id}/fail/` | Fail, release stock, cancel order |

List supports `status`, `helper`, `order`, `search`, and `ordering`. Generic PATCH and DELETE return `405`.

## Examples

```http
POST /api/fulfillment/delivery-job/

{"order_id":"uuid","helper_id":"uuid","fee_cents":1200,"fuel_cents":300,"order_version":4}
```

Only a confirmed delivery order with no job and an active helper is eligible.

```json
// start
{"order_version":5}

// fail
{"order_version":6,"failure_reason":"Customer unavailable"}
```

Deliver requires an idempotency header:

```http
POST /api/fulfillment/delivery-job/{id}/deliver/
Idempotency-Key: d2342cf6-e843-46d9-95f2-442c5abc3185

{"order_version":6}
```

Delivery atomically consumes reservations and writes sold movements. For COD, it also creates a cash payment for the exact remaining balance and links it as `cod_payment`. Failure releases reservations, marks the job failed, cancels the order with the same reason, and preserves financial history.

## Errors

- `400 validation_error`: negative costs or missing failure reason.
- `409 delivery_not_eligible` or `delivery_exists`.
- `409 invalid_transition`: command is not legal from the current state.
- `409 stale_order`: order version mismatch.
- `409 idempotency_conflict`: delivered COD job used another key.
- `405`: arbitrary update or deletion attempted.
