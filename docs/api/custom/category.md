# Category API

## Purpose and access

Maintains the product category hierarchy. All operations require owner authentication; unsafe session requests require CSRF.

## Endpoints and filters

- `GET|POST /api/custom/category/`
- `GET|PUT|PATCH|DELETE /api/custom/category/{id}/`
- Filters: `status`, `parent_id`; search: `name`, `slug`; ordering: `name`, `sort_order`, timestamps.

Create example: `{ "name":"Shirts", "parent_id":"uuid", "status":"active", "sort_order":0 }`. Slugs are collision-safe and generated server-side. Names are trimmed; case-insensitive duplicate sibling names, self-parenting, and cycles return `400`. Deletion returns `409` when children/product links exist or the slug is reserved for special-stock workflows. Responses include derived `child_count` and `product_count`. Related model: `ProductCategory`.

## Usage examples

### List and retrieve

```http
GET /api/custom/category/?status=active&parent_id=<parent-uuid>&search=shirt&ordering=sort_order&page=1
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"f54d5e83-cfed-4097-bdf2-cbe5e0377235",
    "name":"Shirts",
    "slug":"shirts",
    "parent_id":null,
    "status":"active",
    "sort_order":0,
    "child_count":0,
    "product_count":3,
    "created_at":"2026-10-13T01:00:00Z",
    "updated_at":"2026-10-13T01:00:00Z"
  }]
}
```

Retrieve one category with `GET /api/custom/category/{id}/`. Search checks `name` and `slug`; ordering supports `name`, `sort_order`, `created_at`, and `updated_at`.

### Add

```http
POST /api/custom/category/
Authorization: Bearer <access-token>
Content-Type: application/json

{"name":"Shirts","parent_id":null,"status":"active","sort_order":10}
```

Success returns `201` with the generated slug and derived counts.

### Update

Use `PATCH` for selected fields:

```http
PATCH /api/custom/category/f54d5e83-cfed-4097-bdf2-cbe5e0377235/
Authorization: Bearer <access-token>
Content-Type: application/json

{"name":"T-Shirts","sort_order":20}
```

Use `PUT` with the complete writable representation: `name`, `parent_id`, `status`, and `sort_order`. Both return `200` with the updated category.

### Delete

```http
DELETE /api/custom/category/f54d5e83-cfed-4097-bdf2-cbe5e0377235/
Authorization: Bearer <access-token>
```

Success is `204 No Content`. Delete is allowed only when no child category or product link exists and the slug is not protected.

## Error examples

Duplicate sibling names or a hierarchy cycle return `400`:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"name":["A sibling category with this name already exists."]}
  }
}
```

A structurally valid delete blocked by relationships returns `409`:

```json
{"error":{"code":"category_has_children","message":"Move or remove child categories first."}}
```

An unknown UUID returns `404`; malformed UUID input or invalid status returns `400`; missing authentication returns `401`.
