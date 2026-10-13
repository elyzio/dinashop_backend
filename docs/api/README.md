# Phase-One API

The phase-one API covers `users`, `custom`, `catalog`, and `inventory`. Its base URL is `/api/`; class segments are singular kebab-case. Interactive OpenAPI documentation is at `/api/docs/` and the schema is at `/api/schema/`. Both require authentication.

## Authentication

Browser clients should call `GET /api/users/user/csrf/`, retain the session and CSRF cookies, and send `X-CSRFToken` on every unsafe session-authenticated request. JWT clients use the token, refresh, and blacklist endpoints and send `Authorization: Bearer <access-token>`. Logging out or blacklisting a refresh token affects only that session or device.

All endpoints require authentication except CSRF bootstrap, login, token obtain, and token refresh. Login and token endpoints are throttled. There is no user-management API in v1.

## Representation conventions

- JSON fields are snake_case. IDs are UUID strings.
- Money is represented as integer cents; quantities are whole integers.
- Times are ISO-8601 UTC values. Clients may display them in the configured business timezone.
- Lists use page-number pagination (`page`, `page_size`; maximum 100), and may expose `search`, `ordering`, and documented filters.
- Unsafe session requests require CSRF. Multipart is used only for image uploads.
- Server values are authoritative for stock, landed cost, prices, and history.

Validation failures have this shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid values.",
    "fields": {"name": ["This field is required."]}
  }
}
```

Status conventions are `400` invalid input, `401` missing/invalid authentication, `403` CSRF or permission failure, `404` missing resource, `409` valid operation blocked by state, and `413` oversized upload. Create commands return `201`; successful reads/updates and idempotent replays return `200`; successful deletion/logout returns `204`.

## Model documentation

- Users: [User](users/user.md), [NotificationReceipt](users/notification_receipt.md)
- Custom: [Category](custom/category.md), [BusinessSettings](custom/business_settings.md), [DocumentSequence](custom/document_sequence.md), [AuditEvent](custom/audit_event.md)
- Catalog: [Product](catalog/product.md), [ProductCategory](catalog/product_category.md), [ProductImage](catalog/product_image.md), [ProductOption](catalog/product_option.md), [ProductOptionValue](catalog/product_option_value.md), [ProductVariant](catalog/product_variant.md), [VariantOptionValue](catalog/variant_option_value.md), [PriceHistory](catalog/price_history.md)
- Inventory: [InventoryBalance](inventory/inventory_balance.md), [StockReservation](inventory/stock_reservation.md), [StockMovement](inventory/stock_movement.md)

## Safety boundaries

Product aggregate writes, price updates, image processing, and stock commands run through services. History tables are append-only through the API. Product images are uploaded after product creation because object storage cannot participate in the PostgreSQL transaction. Order-driven reservation mutations are intentionally deferred until the order API phase.
