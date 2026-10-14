# PriceHistory API

## Purpose and access

Records immutable standard/sale price changes with actor and timestamp. Authenticated clients may inspect but never mutate history.

## Endpoints and filters

- `GET /api/catalog/price-history/`
- `GET /api/catalog/price-history/{id}/`
- Filter by `variant`, `kind`, or `changed_by`; date filters `from`, `to`; newest first.

Example fields include previous/new integer cents, sale window, actor UUID, and UTC `changed_at`. POST/PATCH/DELETE returns `405`; malformed filters return `400`; missing rows return `404`. Records are created only by the variant pricing service after a locked, successful change. Related model: `ProductVariant`.

## Usage examples

### List and retrieve history

```http
GET /api/catalog/price-history/?variant=<variant-uuid>&kind=standard&changed_by=<user-uuid>&from=2026-10-01&to=2026-10-31&ordering=-changed_at
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"b6fece63-0195-4ce4-a3b1-e7fe1a4a6165",
    "variant":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "kind":"standard",
    "previous_cents":2500,
    "new_cents":2750,
    "sale_starts_at":null,
    "sale_ends_at":null,
    "changed_by":"81db6f41-8a94-4d1c-aea2-37f2c63efdb2",
    "changed_by_email":"owner@example.com",
    "changed_at":"2026-10-13T01:00:00Z"
  }]
}
```

Retrieve one row with `GET /api/catalog/price-history/{id}/`. `kind` is `standard` or `sale`; `from` and `to` filter the change date.

### Add, update, and delete behavior

There are no direct write operations. `PATCH /api/catalog/product-variant/{id}/pricing/` creates the appropriate immutable history rows automatically in the same transaction.

History begins with the first actual change to a stored standard or sale price. Variant creation does not add a synthetic `null`-to-initial-price record, and an unchanged pricing request does not add a duplicate history entry.

## Error examples

Direct writes return `405`:

```json
{"error":{"code":"method_not_allowed","message":"Method \"POST\" not allowed."}}
```

An unknown history UUID returns `404`; invalid `kind`, actor UUID, or date input returns `400`; missing authentication returns `401`.
