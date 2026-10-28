# ProductVariant API

## Purpose and access

Represents a sellable SKU with server-authoritative pricing, derived stock, and an optional primary barcode. The base endpoints are authenticated/read-only; pricing and barcode generation are protected service commands.

## Endpoints and filters

- `GET /api/catalog/product-variant/`
- `GET /api/catalog/product-variant/{id}/`
- `PATCH /api/catalog/product-variant/{id}/pricing/`
- `POST /api/catalog/product-variant/{id}/barcode/generate/`
- `GET /api/catalog/product-variant/barcode-lookup/?barcode=<value>`
- Filter by `product`, `is_active`; search SKU/barcode/product/brand; order by SKU, price, or timestamps.

Pricing example: `{ "selling_price_cents":2750, "sale_price_cents":2200, "sale_starts_at":"2026-10-12T00:00:00Z", "sale_ends_at":"2026-10-20T00:00:00Z" }`. The row is locked, dates and non-negative cents validated, and changed fields append immutable `PriceHistory`. Responses include selected options plus `in_hand`, `promised`, `available`, and active price. Direct base mutations return `405`; duplicate SKU/invalid sale windows return `400`. Related models: `Product`, option assignments, inventory, and price history.

## Usage examples

### List and retrieve variants

```http
GET /api/catalog/product-variant/?product=<product-uuid>&is_active=true&search=SHIRT&ordering=sku
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "product":"0e59eca9-9284-4861-9f29-413899c29fca",
    "sku":"SHIRT-BLACK",
    "barcode":"0012345678905",
    "is_active":true,
    "selling_price_cents":2500,
    "sale_price_cents":2200,
    "sale_starts_at":"2026-10-12T00:00:00Z",
    "sale_ends_at":"2026-10-20T00:00:00Z",
    "active_price_cents":2200,
    "options":{"Color":"Black"},
    "in_hand":10,
    "promised":2,
    "available":8,
    "last_landed_cost_cents":1200,
    "last_sale_at":null,
    "created_at":"2026-10-13T01:00:00Z",
    "updated_at":"2026-10-13T01:00:00Z"
  }]
}
```

Retrieve one variant with `GET /api/catalog/product-variant/{id}/`. Search checks SKU, barcode, product name, and brand.

### Add, update, and remove variants

There is no direct variant POST/PATCH/DELETE. Add or modify variants with `POST /api/catalog/product/` or `PUT /api/catalog/product/{product_id}/variant-grid/`. Omitting a referenced or stocked variant from the grid deactivates it instead of destroying history.

Each variant may have one globally unique barcode. Manual values are printable ASCII strings up to 100 characters. The server trims outer whitespace, converts blank input to `null`, and otherwise preserves leading zeroes, internal characters, and letter case. Deactivation does not release a barcode for reuse.

To allocate a Dina Shop barcode for an existing barcode-less variant:

```http
POST /api/catalog/product-variant/2ade7e50-b10c-4d44-a5d0-f39568fac7af/barcode/generate/
Authorization: Bearer <access-token>
```

The command locks the variant and the `barcode` document sequence, assigns a value such as `DS-000000000001`, records an audit event, and returns the updated variant. It never replaces an existing barcode; that conflict returns `409 barcode_exists`.

Cashier lookup uses an exact value without GTIN padding or case conversion:

```http
GET /api/catalog/product-variant/barcode-lookup/?barcode=0012345678905
Authorization: Bearer <access-token>
```

```json
{
  "id":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
  "product_id":"0e59eca9-9284-4861-9f29-413899c29fca",
  "product_name":"Classic T-Shirt",
  "product_brand":"Dina",
  "primary_image":null,
  "sku":"SHIRT-BLACK",
  "barcode":"0012345678905",
  "options":{"Color":"Black"},
  "active_price_cents":2200,
  "is_sale_active":true,
  "available":8
}
```

Unknown values return `404 barcode_not_found`. Hidden products and inactive variants return `409 variant_not_sellable`; a zero available balance returns `409 sold_out`.

### Update pricing

```http
PATCH /api/catalog/product-variant/2ade7e50-b10c-4d44-a5d0-f39568fac7af/pricing/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "selling_price_cents":2750,
  "sale_price_cents":2300,
  "sale_starts_at":"2026-10-13T00:00:00Z",
  "sale_ends_at":"2026-10-20T00:00:00Z"
}
```

Success returns `200` with the updated variant. The service locks the row and appends standard and/or sale `PriceHistory` records only for changed values.

The initial price supplied when a variant is created is its starting state and does not create history. Re-submitting unchanged pricing also creates no row. Existing clients must preserve `is_active`, sale price, and sale-window values when replacing a full variant grid; omission is interpreted according to the write serializer rather than as a UI-only state.

## Error examples

An empty pricing request or invalid sale period returns `400`:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"sale_ends_at":["Sale end must be after sale start."]}
  }
}
```

Negative cents return `400`. Duplicate or invalid manual barcodes return field-level `400` errors. An unknown variant returns `404`; missing authentication returns `401`; direct `POST`, base `PATCH`, or `DELETE` returns `405`.
