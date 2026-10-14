# BusinessSettings API

## Purpose and access

Stores the singleton `default` business/receipt configuration. The authenticated owner may manage it; every create/update appends an `AuditEvent`.

## Endpoint

- `GET /api/custom/business-settings/current/` — `404` until configured.
- `PUT .../current/` — create or fully replace the default record.
- `PATCH .../current/` — partial update; requires an existing record.

Example: `{ "business_name":"Dina Shop", "currency":"JPY", "timezone":"Asia/Tokyo", "low_stock_threshold":5 }`. Currency is normalized to exactly three uppercase letters, timezone must be a valid IANA name, and numeric limits must be non-negative. There are no list filters because this is a singleton. Related model: `AuditEvent`; receipt and alert consumers read this configuration.

## Usage examples

### Read the singleton

```http
GET /api/custom/business-settings/current/
Authorization: Bearer <access-token>
```

```json
{
  "id":"31f4c004-66d8-40d8-8f5e-0b4452becaf3",
  "business_name":"Dina Shop",
  "address":"Tokyo",
  "phone":"+81 00 0000 0000",
  "registration_id":"REG-100",
  "receipt_footer":"Thank you",
  "currency":"JPY",
  "timezone":"Asia/Tokyo",
  "low_stock_threshold":5,
  "created_at":"2026-10-13T01:00:00Z",
  "updated_at":"2026-10-13T01:00:00Z"
}
```

There is no list endpoint because only the fixed `default` record is used.

### Add or fully submit settings

```http
PUT /api/custom/business-settings/current/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "business_name":"Dina Shop",
  "address":"Tokyo",
  "phone":"+81 00 0000 0000",
  "registration_id":"REG-100",
  "receipt_footer":"Thank you",
  "currency":"JPY",
  "timezone":"Asia/Tokyo",
  "low_stock_threshold":5
}
```

The first `PUT` creates the record and returns `201`; later `PUT` requests update it and return `200`. Send every desired field when using `PUT`.

### Update selected fields

```http
PATCH /api/custom/business-settings/current/
Authorization: Bearer <access-token>
Content-Type: application/json

{"receipt_footer":"Thank you for shopping with us","low_stock_threshold":8}
```

Success returns `200` with the complete record. Every successful create or update adds an `AuditEvent`. Delete is not supported.

## Error examples

`GET` or `PATCH` before initial `PUT` returns `404`:

```json
{"error":{"code":"not_found","message":"No BusinessSettings matches the given query."}}
```

Invalid configuration returns `400`:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"timezone":["Use a valid IANA timezone."]}
  }
}
```

Currency must contain exactly three letters and is uppercased. A blank business name or negative stock threshold returns `400`; missing authentication returns `401`; `DELETE current/` returns `405`.
