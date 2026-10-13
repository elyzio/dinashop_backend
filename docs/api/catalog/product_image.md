# ProductImage API

## Purpose and access

Stores processed product images through the environment's configured storage: local media in development and Supabase S3-compatible storage in production. Authentication and CSRF rules apply.

## Endpoints and filters

- `GET|POST /api/catalog/product-image/` — upload uses multipart fields `product_id`, `image`, `alt_text`, `sort_order`.
- `GET|PATCH|DELETE /api/catalog/product-image/{id}/` — PATCH accepts metadata only.
- `POST /api/catalog/product-image/reorder/` — `{ "product_id":"uuid", "image_ids":["uuid"] }`.
- Filter by `product`; order by `sort_order` or `created_at`.

JPEG, PNG, and WebP are accepted up to 5 MB and 36 decoded megapixels. The service applies EXIF orientation, strips metadata, scales within 1600×1600, writes WebP quality 82 under a UUID name, and persists dimensions/size. A product may have at most eight images. Reorder must contain the complete image set. Invalid/spoofed images return `400`, oversized input `413`, and unrelated image IDs `400`. Storage deletion occurs after commit; failed writes clean orphan files. Related model: `Product`.
