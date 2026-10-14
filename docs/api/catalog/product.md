# Product API

## Purpose and access

Creates and maintains the authenticated owner's product aggregate. A create transaction includes category links, options, values, variants, assignments, and one zeroed `InventoryBalance` per variant. Images are uploaded separately.

## Endpoints and filters

- `GET|POST /api/catalog/product/`
- `GET|PUT|PATCH /api/catalog/product/{id}/`
- `PUT .../{id}/variant-grid/` — atomically replace the option/variant grid.
- `POST .../{id}/visibility/` — `{ "visibility":"hidden" }`.
- Filters: `visibility`, `category_id`; search name/brand/description/SKU; order by name, brand, or timestamps.

Create requests contain `name`, descriptions, `category_ids`, exactly one `primary_category_id`, `option_definitions`, and non-empty `variants`; see the OpenAPI schema for the full example. IDs are UUID strings and prices are integer cents. SKUs are trimmed, uppercased, and globally unique. Every variant must choose exactly one allowed value for every option. A failure rolls back the entire aggregate. Removing referenced/stocked variants deactivates them; hiding promised stock returns `409`. Related models: every catalog model, `Category`, and `InventoryBalance`.

A product without customer-selectable options still has one internal variant. Send an empty `option_definitions` list, one variant with `options: {}`, and its required SKU and price; the returned product has `has_variants: false`. Initial prices do not create `PriceHistory`. History begins only when a stored price changes.

Special-item receiving creates a hidden one-variant product in the protected `special-order-stock` category. That product is server-managed inventory for the received item; clients must not expose it as a normal storefront/catalog choice or attempt to reconstruct it themselves.

## Usage examples

### List and retrieve products

```http
GET /api/catalog/product/?visibility=active&category_id=<category-uuid>&search=shirt&ordering=name&page=1
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"0e59eca9-9284-4861-9f29-413899c29fca",
    "name":"Classic T-Shirt",
    "description":"Soft cotton shirt.",
    "brand":"Dina",
    "visibility":"active",
    "has_variants":true,
    "category_ids":["f54d5e83-cfed-4097-bdf2-cbe5e0377235"],
    "primary_category_id":"f54d5e83-cfed-4097-bdf2-cbe5e0377235",
    "images":[],
    "option_definitions":[],
    "variants":[],
    "created_at":"2026-10-13T01:00:00Z",
    "updated_at":"2026-10-13T01:00:00Z"
  }]
}
```

Search checks name, brand, description, and variant SKU. Retrieve the complete nested aggregate with `GET /api/catalog/product/{id}/`.

### Add a complete product aggregate

```http
POST /api/catalog/product/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "name":"Classic T-Shirt",
  "description":"Soft cotton shirt.",
  "brand":"Dina",
  "visibility":"active",
  "category_ids":["f54d5e83-cfed-4097-bdf2-cbe5e0377235"],
  "primary_category_id":"f54d5e83-cfed-4097-bdf2-cbe5e0377235",
  "option_definitions":[{"name":"Color","values":["Black","White"]}],
  "variants":[{
    "sku":"SHIRT-BLACK",
    "options":{"Color":"Black"},
    "selling_price_cents":2500,
    "is_active":true
  }]
}
```

Success returns `201` with the nested product. Product, categories, options, values, variants, assignments, initial inventory balances, and audit event are committed atomically. Images are uploaded afterward through the ProductImage API.

### Update product details or categories

```http
PATCH /api/catalog/product/0e59eca9-9284-4861-9f29-413899c29fca/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "name":"Classic Cotton T-Shirt",
  "category_ids":["f54d5e83-cfed-4097-bdf2-cbe5e0377235"],
  "primary_category_id":"f54d5e83-cfed-4097-bdf2-cbe5e0377235"
}
```

`PUT` and `PATCH` accept product details/category links. Visibility and variant changes use the commands below.

### Replace the variant grid

Send the complete desired grid, including IDs for variants that already exist:

```http
PUT /api/catalog/product/0e59eca9-9284-4861-9f29-413899c29fca/variant-grid/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "option_definitions":[{"name":"Color","values":["Black","White"]}],
  "variants":[{
    "id":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "sku":"SHIRT-BLACK",
    "options":{"Color":"Black"},
    "selling_price_cents":2600,
    "is_active":true
  }]
}
```

Omitted unreferenced variants are deleted; variants with stock, reservations, or history are deactivated. The response is the updated product.

Changing between the single-product and option-based modes is allowed only before any existing variant has stock, reservations, movements, order references, or price history. A protected conversion returns `409 variant_mode_locked`. Ordinary option edits within the current mode retain existing variant UUIDs supplied in the request; removed referenced combinations are deactivated.

### Change visibility

```http
POST /api/catalog/product/0e59eca9-9284-4861-9f29-413899c29fca/visibility/
Authorization: Bearer <access-token>
Content-Type: application/json

{"visibility":"hidden"}
```

There is no product DELETE endpoint. Products with transactional history should be hidden instead.

## Error examples

An invalid primary category or duplicate SKU returns `400` and rolls back the aggregate:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"primary_category_id":["The primary category must be selected."]}
  }
}
```

Hiding a product with promised stock returns `409`:

```json
{"error":{"code":"promised_stock_exists","message":"This product cannot be hidden while stock is promised."}}
```

Changing a protected product mode also returns `409`:

```json
{"error":{"code":"variant_mode_locked","message":"Product mode cannot be changed after a variant has stock or operational history."}}
```

Unknown product/category/variant UUIDs return `404` or field-level `400` depending on where they are supplied. Missing authentication returns `401`; `DELETE /api/catalog/product/{id}/` returns `405`.
