# Helper API

## Purpose and access

Stores non-authenticated delivery helpers. Owner authentication and CSRF rules follow the shared API conventions.

## Endpoints and filters

| Method | URL | Function |
|---|---|---|
| GET, POST | `/api/people/helper/` | List or create helpers |
| GET, PATCH | `/api/people/helper/{id}/` | Retrieve or update contact information |
| POST | `/api/people/helper/{id}/deactivate/` | Block new assignments |
| POST | `/api/people/helper/{id}/reactivate/` | Allow assignments |

Use `search`, `is_active`, and `ordering`. DELETE is intentionally unsupported because delivery and COD history must remain attributable.

```http
POST /api/people/helper/

{"name":"Ken Ito","phone":"090-2222-3333","note":"Evenings"}
```

```http
PATCH /api/people/helper/{id}/

{"note":"Weekends only"}
```

```http
POST /api/people/helper/{id}/deactivate/

{}
```

Responses include server-derived `completed_jobs`, `fees_cents`, `cod_collected_cents`, `cod_handed_over_cents`, and `cod_held_cents`.

## Errors

- `400 validation_error`: blank name or invalid input.
- `404`: helper not found.
- `409 delivery_not_eligible`: an inactive helper was selected when creating a delivery job.
- `405`: DELETE is unsupported.

Related models: `DeliveryJob` and `CodHandover`.
