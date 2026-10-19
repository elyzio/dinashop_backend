# Report and CSV APIs

## Purpose and endpoints

All report endpoints require authentication and are read-only:

```text
GET /api/report/<report-id>/?from=YYYY-MM-DD&to=YYYY-MM-DD
GET /api/report/<report-id>/csv/?from=YYYY-MM-DD&to=YYYY-MM-DD
```

`from` and `to` are inclusive. When omitted, they default to the current month through today. The start date cannot be after the end date and a range cannot exceed ten years.

Supported report IDs are:

- `sales`
- `profit-per-order`
- `monthly-profit`
- `money-owed`
- `stock-on-hand`
- `low-and-slow-stock`
- `cod-cash`
- `helper-costs`
- `special-outcomes`

## JSON example

```http
GET /api/report/sales/?from=2026-10-01&to=2026-10-31
```

```json
{
  "id": "sales",
  "title": "Sales",
  "description": "Net order totals that were not cancelled or declined.",
  "currency": "USD",
  "from_date": "2026-10-01",
  "to_date": "2026-10-31",
  "generated_at": "2026-10-31T12:00:00Z",
  "columns": [
    {"key": "created_at", "label": "Date", "kind": "datetime"},
    {"key": "order_number", "label": "Order", "kind": "text"},
    {"key": "total_cents", "label": "Total", "kind": "money"}
  ],
  "rows": [
    {
      "created_at": "2026-10-12T03:10:00Z",
      "order_number": "ORD-000031",
      "customer_name": "Example Customer",
      "total_cents": 2500,
      "status": "completed"
    }
  ]
}
```

Columns carry a display kind so clients can consistently render money, dates, months, integers, and statuses. JSON money remains integer cents.

## CSV export

The CSV endpoint uses the same filters and calculations as its JSON endpoint. It returns `text/csv` and a `Content-Disposition` filename such as `sales-2026-10-01-2026-10-31.csv`. Money columns are decimal currency values in the file, and formula-like text is escaped for spreadsheet safety. The browser controls saving or printing. Stock reports are current snapshots; their date parameters keep the request contract consistent but do not reconstruct historical balances.

## Validation and errors

- `400 validation_error`: invalid date format, reversed dates, or a range over ten years.
- `401 authentication_required`: no valid session or bearer token.
- `404 not_found`: unknown report ID.

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid values.",
    "fields": {"from": ["The start date cannot be after the end date."]}
  }
}
```

There are no POST, PATCH, PUT, or DELETE report operations. Correct the owning order, payment, inventory, delivery, or configuration record through its protected domain command; the next report request will reflect it.

See the [reporting diagram](diagram.md) and [dashboard API](dashboard.md).
