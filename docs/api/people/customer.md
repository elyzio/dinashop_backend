# Customer API

## Purpose and access

Stores customer contact data while orders retain immutable name, phone, and delivery-address snapshots. All endpoints require owner session or bearer authentication; session writes require CSRF.

## Endpoints and filters

| Method | URL | Function |
|---|---|---|
| GET, POST | `/api/people/customer/` | Paginated list or create |
| GET, PATCH | `/api/people/customer/{id}/` | Retrieve or safely update |
| POST | `/api/people/customer/{id}/deactivate/` | Prevent future selection |
| POST | `/api/people/customer/{id}/reactivate/` | Restore future selection |

List supports `search`, `is_active`, `is_walk_in`, `ordering`, `page`, and `page_size`. Search covers name, phone, normalized phone, address, and note. Hard DELETE is unsupported and returns `405`.

## Examples

```http
GET /api/people/customer/?search=555&is_active=true&ordering=name
```

```http
POST /api/people/customer/
Content-Type: application/json
X-CSRFToken: <token>

{"name":"Aiko Tanaka","phone":"+81 90-1234-5678","address":"Tokyo","note":"Call first"}
```

```http
PATCH /api/people/customer/{id}/

{"address":"Updated address"}
```

Successful responses include `normalized_phone`, `order_count`, `outstanding_cents`, and a nullable `duplicate_phone_warning`. Duplicate phones are warnings, not validation failures.

```http
POST /api/people/customer/{id}/deactivate/

{}
```

## Validation and errors

- `400 validation_error`: blank name or invalid field value.
- `401 authentication_required`: no valid session or token.
- `403 permission_denied`: invalid CSRF or non-owner access.
- `404`: unknown UUID.
- `409 walk_in_protected`: attempted update or deactivation of the system walk-in customer.
- `405`: DELETE or another unsupported method.

Delivery and special-order services reject the walk-in customer and require a usable phone number. Related models: `Order`, `Payment`, and `Refund`.
