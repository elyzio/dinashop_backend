# ProductOptionValue API

## Purpose and access

Represents an allowed value within a product option. The authenticated API is read-only; product aggregate services mutate values.

## Endpoints and filters

- `GET /api/catalog/product-option-value/`
- `GET /api/catalog/product-option-value/{id}/`
- Filter by `option` or `option__product`; search by value; order by `sort_order` or value.

Example response: `{ "id":"uuid", "option":"uuid", "value":"Black", "sort_order":0 }`. Direct mutations return `405`; missing records return `404`. Blank/duplicate values and values assigned across products are rejected during grid validation. Related models: `ProductOption` and `VariantOptionValue`.

## Usage examples

### List and retrieve

```http
GET /api/catalog/product-option-value/?option=<option-uuid>&option__product=<product-uuid>&search=black&ordering=sort_order
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"6647ce9e-1318-4036-8409-e7e77a238fba",
    "option":"ab6e3221-d56c-4391-90a0-b5386268359b",
    "value":"Black",
    "sort_order":0
  }]
}
```

Retrieve one value with `GET /api/catalog/product-option-value/{id}/`. Search checks value text and option name.

### Add, update, and delete behavior

This resource is read-only. Manage option values as part of product creation or with `PUT /api/catalog/product/{id}/variant-grid/`. Centralizing writes prevents values from being attached to options from another product.

## Error examples

Direct writes return `405`:

```json
{"error":{"code":"method_not_allowed","message":"Method \"PATCH\" not allowed."}}
```

An unknown value UUID returns `404`; malformed filters return `400`; missing authentication returns `401`. Duplicate or blank values sent through the variant-grid command produce a `400 validation_error` on `option_definitions`.
