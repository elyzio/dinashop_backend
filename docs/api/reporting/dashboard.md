# Dashboard summary API

## Purpose

`GET /api/dashboard/summary/` returns the small, server-authoritative dataset required by the React dashboard. It avoids downloading every operational record merely to calculate totals in the browser.

Authentication is required. Session requests include the Django session cookie; bearer clients may use JWT. This endpoint is read-only and has no add, update, or delete operation.

## Response

```json
{
  "generated_at": "2026-10-16T03:00:00Z",
  "currency": "USD",
  "metrics": {
    "orders_to_deliver": 2,
    "active_orders": 5,
    "balance_due_cents": 18400,
    "cod_cash_held_cents": 5000,
    "profit_this_month_cents": 42750,
    "profit_is_provisional": true
  },
  "special_orders": [
    {
      "id": "4c808067-42b1-4f27-a6eb-71c5ac51f64f",
      "number": "SO-000012",
      "customer_name": "Example Customer",
      "description": "Imported shoes",
      "estimated_total_cents": 9200,
      "special_status": "item_received"
    }
  ],
  "attention": [
    {
      "kind": "order",
      "label": "SO-000012 needs a final price",
      "detail": "Item received; actual tax has not been entered.",
      "entity_id": "4c808067-42b1-4f27-a6eb-71c5ac51f64f"
    }
  ],
  "monthly_profit": [
    {"month": "2026-10", "profit_cents": 42750, "provisional": true}
  ]
}
```

Profit is provisional when an included sold line has no known landed cost. COD held is collected COD payment value minus recorded handovers. Attention results currently include special orders awaiting a final price or customer notification and active products at or below the low-stock threshold.

## Errors

- `401 authentication_required`: no valid session or bearer token.
- `500 server_error`: an unexpected query failure; no partial summary is returned.

```json
{
  "error": {
    "code": "authentication_required",
    "message": "Authentication credentials were not provided.",
    "fields": {}
  }
}
```

See the [reporting diagram](diagram.md) and [report API](report.md).
