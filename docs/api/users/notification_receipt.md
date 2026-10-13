# NotificationReceipt API

## Purpose and access

Stores the authenticated owner's read/dismiss state for server-derived notification fingerprints. Every query is scoped to `request.user`; cross-user access is impossible through these routes.

## Endpoints and filters

- `GET /api/users/notification-receipt/` — paginated list; filter by `notification_id`, `fingerprint`, `read_at`, or `dismissed_at`; order by creation/update/read/dismiss times.
- `POST .../acknowledge/` — upsert `{ "notification_id":"low-stock", "fingerprint":"variant:uuid:4", "action":"read" }`.
- `POST .../read-all/` — `{ "items":[{"notification_id":"low-stock","fingerprint":"..."}] }`.

Acknowledgement is idempotent for `(user, notification_id, fingerprint)`. Empty read-all lists, duplicate supplied versions, or unsupported actions return `400`; missing authentication returns `401`. The API never creates the underlying notification—it only records owner state. Related model: `User`.
