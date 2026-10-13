# ProductOption API

## Purpose and access

Describes one variation dimension, such as Color or Size. Authenticated read-only endpoints expose the current grid; Product services own writes.

## Endpoints and filters

- `GET /api/catalog/product-option/`
- `GET /api/catalog/product-option/{id}/`
- Filter by `product`; search by option name; order by `sort_order` or name.

Responses include the option UUID, product UUID, name, order, and nested values. Direct mutations return `405`. Product grid validation rejects blank or case-insensitively duplicated option names. Related models: `Product`, `ProductOptionValue`, and `VariantOptionValue`.
