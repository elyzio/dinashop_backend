# ProductCategory API

## Purpose and access

Represents ordered product-to-category links and the single primary category. It is authenticated and read-only; writes occur only through Product create/update services.

## Endpoints and filters

- `GET /api/catalog/product-category/`
- `GET /api/catalog/product-category/{id}/`
- Filter by `product`, `category`, or `is_primary`; order by `sort_order`.

A response contains UUID IDs, `is_primary`, and `sort_order`. Direct POST/PATCH/DELETE returns `405`. Missing links return `404`; malformed UUID filters return `400`. Product services reject empty category sets and primary categories not present in `category_ids`. Related models: `Product` and `Category`.

## Usage examples

### List links

```http
GET /api/catalog/product-category/?product=<product-uuid>&is_primary=true&ordering=sort_order
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"f6cc203a-d7a4-469c-a174-fde47a05b82f",
    "product":"0e59eca9-9284-4861-9f29-413899c29fca",
    "product_name":"Classic T-Shirt",
    "category":"f54d5e83-cfed-4097-bdf2-cbe5e0377235",
    "category_name":"Shirts",
    "is_primary":true,
    "sort_order":0
  }]
}
```

Exact filters are `product`, `category`, and `is_primary`. Retrieve one link with `GET /api/catalog/product-category/{id}/`.

### Add, update, and delete behavior

There are no direct write operations. Add or replace category links through `POST /api/catalog/product/` or `PUT|PATCH /api/catalog/product/{id}/` using `category_ids` and `primary_category_id`. This preserves the rule that every product has exactly one primary category.

## Error examples

`POST`, `PUT`, `PATCH`, or `DELETE` on this resource returns `405`:

```json
{"error":{"code":"method_not_allowed","message":"Method \"POST\" not allowed."}}
```

An unknown link UUID returns `404`; malformed UUID filters return `400`; missing authentication returns `401`.
