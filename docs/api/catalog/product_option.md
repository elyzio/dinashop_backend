# ProductOption API

## Purpose and access

Describes one variation dimension, such as Color or Size. Authenticated read-only endpoints expose the current grid; Product services own writes.

## Endpoints and filters

- `GET /api/catalog/product-option/`
- `GET /api/catalog/product-option/{id}/`
- Filter by `product`; search by option name; order by `sort_order` or name.

Responses include the option UUID, product UUID, name, order, and nested values. Direct mutations return `405`. Product grid validation rejects blank or case-insensitively duplicated option names. Related models: `Product`, `ProductOptionValue`, and `VariantOptionValue`.

## Usage examples

### List and retrieve

```http
GET /api/catalog/product-option/?product=<product-uuid>&search=color&ordering=sort_order
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"ab6e3221-d56c-4391-90a0-b5386268359b",
    "product":"0e59eca9-9284-4861-9f29-413899c29fca",
    "name":"Color",
    "sort_order":0,
    "values":[
      {"id":"6647ce9e-1318-4036-8409-e7e77a238fba","option":"ab6e3221-d56c-4391-90a0-b5386268359b","value":"Black","sort_order":0}
    ]
  }]
}
```

Retrieve one option with `GET /api/catalog/product-option/{id}/`. Search checks option and product names.

### Add, update, and delete behavior

The endpoints are read-only. Create and update options through product creation or `PUT /api/catalog/product/{id}/variant-grid/`. The grid command also safely removes unused options while protecting referenced assignments.

## Error examples

Direct `POST`, `PATCH`, or `DELETE` returns `405`:

```json
{"error":{"code":"method_not_allowed","message":"Method \"POST\" not allowed."}}
```

An unknown option UUID returns `404`; malformed product filters return `400`; missing authentication returns `401`.
