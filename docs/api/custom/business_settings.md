# BusinessSettings API

## Purpose and access

Stores the singleton `default` business/receipt configuration. The authenticated owner may manage it; every create/update appends an `AuditEvent`.

## Endpoint

- `GET /api/custom/business-settings/current/` — `404` until configured.
- `PUT .../current/` — create or fully replace the default record.
- `PATCH .../current/` — partial update; requires an existing record.

Example: `{ "business_name":"Dina Shop", "currency":"JPY", "timezone":"Asia/Tokyo", "low_stock_threshold":5 }`. Currency is normalized to exactly three uppercase letters, timezone must be a valid IANA name, and numeric limits must be non-negative. There are no list filters because this is a singleton. Related model: `AuditEvent`; receipt and alert consumers read this configuration.
