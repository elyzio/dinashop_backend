# NotificationReceipt API

## Purpose and access

Stores the authenticated owner's read/dismiss state for server-derived notification fingerprints. Every query is scoped to `request.user`; cross-user access is impossible through these routes.

## Endpoints and filters

- `GET /api/users/notification-receipt/` — paginated list; filter by `notification_id`, `fingerprint`, `read_at`, or `dismissed_at`; order by creation/update/read/dismiss times.
- `POST .../acknowledge/` — upsert `{ "notification_id":"low-stock", "fingerprint":"variant:uuid:4", "action":"read" }`.
- `POST .../read-all/` — `{ "items":[{"notification_id":"low-stock","fingerprint":"..."}] }`.

Acknowledgement is idempotent for `(user, notification_id, fingerprint)`. Empty read-all lists, duplicate supplied versions, or unsupported actions return `400`; missing authentication returns `401`. The API never creates the underlying notification—it only records owner state. Related model: `User`.

## Usage examples

### List the current owner's receipts

```http
GET /api/users/notification-receipt/?notification_id=low-stock&ordering=-updated_at
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"663a9863-6892-4cc5-9c4b-cb0473708533",
    "notification_id":"low-stock",
    "fingerprint":"variant:123:4",
    "read_at":"2026-10-13T01:00:00Z",
    "dismissed_at":null,
    "created_at":"2026-10-13T01:00:00Z",
    "updated_at":"2026-10-13T01:00:00Z"
  }]
}
```

Available exact filters are `notification_id`, `fingerprint`, `read_at`, and `dismissed_at`. Ordering supports `created_at`, `updated_at`, `read_at`, and `dismissed_at`.

### Add or update an acknowledgement

Acknowledgement is an upsert command: it creates the receipt if absent and otherwise updates the existing receipt.

```http
POST /api/users/notification-receipt/acknowledge/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "notification_id":"low-stock",
  "fingerprint":"variant:123:4",
  "action":"dismiss"
}
```

The response is `200` with the receipt. `dismiss` sets both `dismissed_at` and `read_at`; `read` sets `read_at` only. Repeating the same command is safe.

### Mark several notifications read

```http
POST /api/users/notification-receipt/read-all/
Authorization: Bearer <access-token>
Content-Type: application/json

{"items":[
  {"notification_id":"low-stock","fingerprint":"variant:123:4"},
  {"notification_id":"delivery-failed","fingerprint":"order:456:failed"}
]}
```

The response is a JSON array of the created or updated receipt objects. There are no direct detail, PATCH, or DELETE endpoints; state changes must use these commands.

## Error examples

An unsupported action returns `400`:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"action":["\"archive\" is not a valid choice."]}
  }
}
```

An empty or duplicate `read-all` input also returns `400`. Missing authentication returns `401`. `PATCH` or `DELETE` on the collection returns `405`. Receipts are always filtered by the authenticated owner, so one owner cannot list another owner's records.
