# VariantOptionValue API

## Purpose and access

Links one variant to exactly one value for each product option. Endpoints require authentication and are read-only; variant-grid services own all mutations.

## Endpoints and filters

- `GET /api/catalog/variant-option-value/`
- `GET /api/catalog/variant-option-value/{id}/`
- Filter by `variant`, `option`, `value`, or product through the variant.

Responses expose UUID references for the assignment. Direct writes return `405`; missing records return `404`. Services reject duplicate option/value assignments and any option or value belonging to a different product. Related models: `ProductVariant`, `ProductOption`, and `ProductOptionValue`.

## Usage examples

### List and retrieve assignments

```http
GET /api/catalog/variant-option-value/?variant=<variant-uuid>&variant__product=<product-uuid>&option=<option-uuid>
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"0fb06a93-cd48-4dc7-b337-077cc6e3ac5a",
    "variant":"2ade7e50-b10c-4d44-a5d0-f39568fac7af",
    "option":"ab6e3221-d56c-4391-90a0-b5386268359b",
    "option_name":"Color",
    "value":"6647ce9e-1318-4036-8409-e7e77a238fba",
    "value_name":"Black"
  }]
}
```

Exact filters are `variant`, `variant__product`, `option`, and `value`. Retrieve one assignment with `GET /api/catalog/variant-option-value/{id}/`.

### Add, update, and delete behavior

This resource is read-only. Assignments are replaced atomically through the product variant-grid command using the variant's `options` object, for example `{"Color":"Black"}`.

## Error examples

Direct writes return `405`:

```json
{"error":{"code":"method_not_allowed","message":"Method \"DELETE\" not allowed."}}
```

An unknown assignment UUID returns `404`; malformed filter UUIDs return `400`; missing authentication returns `401`. Cross-product or incomplete assignments sent through the grid command return `400` under the `variants` field.
