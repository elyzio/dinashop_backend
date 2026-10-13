# PriceHistory API

## Purpose and access

Records immutable standard/sale price changes with actor and timestamp. Authenticated clients may inspect but never mutate history.

## Endpoints and filters

- `GET /api/catalog/price-history/`
- `GET /api/catalog/price-history/{id}/`
- Filter by `variant`, `kind`, or `changed_by`; date filters `from`, `to`; newest first.

Example fields include previous/new integer cents, sale window, actor UUID, and UTC `changed_at`. POST/PATCH/DELETE returns `405`; malformed filters return `400`; missing rows return `404`. Records are created only by the variant pricing service after a locked, successful change. Related model: `ProductVariant`.
