# ProductImage API

## Purpose and access

Stores processed product images through the environment's configured storage: local media in development and Supabase S3-compatible storage in production. Authentication and CSRF rules apply.

## Endpoints and filters

- `GET|POST /api/catalog/product-image/` — upload uses multipart fields `product_id`, `image`, `alt_text`, `sort_order`.
- `GET|PATCH|DELETE /api/catalog/product-image/{id}/` — PATCH accepts metadata only.
- `POST /api/catalog/product-image/reorder/` — `{ "product_id":"uuid", "image_ids":["uuid"] }`.
- Filter by `product`; order by `sort_order` or `created_at`.

JPEG, PNG, and WebP are accepted up to 5 MB and 36 decoded megapixels. The service applies EXIF orientation, strips metadata, and writes a UUID-named WebP source (maximum 1600×1600). It also creates immutable responsive WebP renditions: `thumbnail` (160 px), `card` (640 px), and `detail` (1280 px). `image_url` remains the compatible source URL; clients should choose renditions through `srcset`. Existing rows without renditions safely fall back to the source image. Run `python manage.py backfill_product_image_renditions` after deployment to create derivatives for old images. A product may have at most eight images. Reorder must contain the complete image set. Invalid/spoofed images return `400`, oversized input `413`, and unrelated image IDs `400`. Storage deletion occurs after commit; failed writes clean orphan files. Related model: `Product`.

## Usage examples

### List and retrieve images

```http
GET /api/catalog/product-image/?product_id=<product-uuid>&ordering=sort_order
Authorization: Bearer <access-token>
```

```json
{
  "count":1,
  "next":null,
  "previous":null,
  "results":[{
    "id":"3ca2f994-e7ef-4c5f-898a-002663bb19ca",
    "product":"0e59eca9-9284-4861-9f29-413899c29fca",
    "image":"http://localhost:8000/media/products/2026/10/uuid.webp",
    "image_url":"http://localhost:8000/media/products/2026/10/uuid.webp",
    "alt_text":"Front view",
    "sort_order":0,
    "width":1600,
    "height":800,
    "file_size_bytes":68420,
    "created_at":"2026-10-13T01:00:00Z"
  }]
}
```

Retrieve one image with `GET /api/catalog/product-image/{id}/`.

### Upload an image

```bash
curl -X POST http://localhost:8000/api/catalog/product-image/ \
  -H "Authorization: Bearer <access-token>" \
  -F "product_id=0e59eca9-9284-4861-9f29-413899c29fca" \
  -F "image=@front.jpg" \
  -F "alt_text=Front view" \
  -F "sort_order=0"
```

Success returns `201` with the processed WebP metadata. The original file is not stored.

### Update metadata

```http
PATCH /api/catalog/product-image/3ca2f994-e7ef-4c5f-898a-002663bb19ca/
Authorization: Bearer <access-token>
Content-Type: application/json

{"alt_text":"Front view on mannequin","sort_order":1}
```

The binary file cannot be replaced by PATCH. Delete and upload a new image when the content changes.

### Reorder all images

```http
POST /api/catalog/product-image/reorder/
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "product_id":"0e59eca9-9284-4861-9f29-413899c29fca",
  "image_ids":[
    "3ca2f994-e7ef-4c5f-898a-002663bb19ca",
    "f55265c5-0e27-41ec-850f-649146fe9127"
  ]
}
```

The array must contain every image for that product exactly once. The response is the reordered image array.

### Delete

```http
DELETE /api/catalog/product-image/3ca2f994-e7ef-4c5f-898a-002663bb19ca/
Authorization: Bearer <access-token>
```

Success is `204`. The database row is removed transactionally and the storage object is deleted after commit.

## Error examples

An invalid/spoofed image returns `400`:

```json
{
  "error":{
    "code":"validation_error",
    "message":"The request contains invalid values.",
    "fields":{"image":["Upload a valid image. The file you uploaded was either not an image or a corrupted image."]}
  }
}
```

Files larger than 5 MB return `413`:

```json
{"error":{"code":"payload_too_large","message":"Product images cannot exceed 5 MB."}}
```

A ninth image returns `409` with code `image_limit_reached`. An incomplete reorder, duplicate image IDs, or IDs from another product returns `400`. Unknown image/product IDs return `404` or a field-level `400`; missing authentication returns `401`.
