# ProductOptionValue API

## Purpose and access

Represents an allowed value within a product option. The authenticated API is read-only; product aggregate services mutate values.

## Endpoints and filters

- `GET /api/catalog/product-option-value/`
- `GET /api/catalog/product-option-value/{id}/`
- Filter by `option` or `option__product`; search by value; order by `sort_order` or value.

Example response: `{ "id":"uuid", "option":"uuid", "value":"Black", "sort_order":0 }`. Direct mutations return `405`; missing records return `404`. Blank/duplicate values and values assigned across products are rejected during grid validation. Related models: `ProductOption` and `VariantOptionValue`.
