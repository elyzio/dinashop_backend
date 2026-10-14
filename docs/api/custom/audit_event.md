# AuditEvent API

## Purpose and access

Provides append-only operational history for authenticated owner review. Events can only be written by domain services; POST, PUT, PATCH, and DELETE return `405`.

## Endpoints and filters

- `GET /api/custom/audit-event/`
- `GET /api/custom/audit-event/{id}/`
- Filters: `actor`, `action`, `entity_type`, `entity_id`; date filters: `from`, `to`; search action/type/ID; newest first.

Example records contain `actor`, `action`, entity identity, before/after JSON, request UUID, IP address, and UTC `created_at`. Invalid filter values return `400`; missing records return `404`. Related models include all service-mutated phase-one entities.

## Usage examples

### List and filter

```http
GET /api/custom/audit-event/?entity_type=catalog.Product&action=product.created&from=2026-10-01&to=2026-10-31&ordering=-created_at
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"c1429046-22f7-475e-a13c-fe493c11fed5",
    "actor":"81db6f41-8a94-4d1c-aea2-37f2c63efdb2",
    "actor_email":"owner@example.com",
    "action":"product.created",
    "entity_type":"catalog.Product",
    "entity_id":"0e59eca9-9284-4861-9f29-413899c29fca",
    "before":{},
    "after":{"name":"Classic T-Shirt"},
    "request_id":null,
    "ip_address":"127.0.0.1",
    "created_at":"2026-10-13T01:00:00Z"
  }]
}
```

Exact filters are `actor`, `action`, `entity_type`, and `entity_id`. `search` checks action, entity type, and entity ID. `from` and `to` filter UTC creation dates.

### Retrieve one event

```http
GET /api/custom/audit-event/c1429046-22f7-475e-a13c-fe493c11fed5/
Authorization: Bearer <access-token>
```

The response is the single event object. Events are created internally in the same transaction as the business operation; there is no public add, update, or delete operation.

## Error examples

Direct writes return `405`:

```http
POST /api/custom/audit-event/
Authorization: Bearer <access-token>
Content-Type: application/json

{"action":"fake.event"}
```

```json
{"error":{"code":"method_not_allowed","message":"Method \"POST\" not allowed."}}
```

An unknown event UUID returns `404`; malformed UUID filters return `400`; missing authentication returns `401`.
