# StockReservation API

## Purpose and access

Diagnoses stock reserved for order lines. The authenticated API is read-only in phase one; creation, consumption, and release are deferred to order services.

## Endpoints and filters

- `GET /api/inventory/stock-reservation/`
- `GET /api/inventory/stock-reservation/{id}/`
- Filter by `variant`, `status`, or `order_line`; search SKU/order number; order by creation/release/consumption times.

Responses contain UUID relations, positive whole quantity, machine status (`active`, `consumed`, `released`), and UTC timestamps. Direct mutations return `405`; missing rows return `404`. Future order commands must update reservations and `InventoryBalance.promised` in one locked transaction. Related models: `InventoryBalance`, `ProductVariant`, and `OrderLine`.
