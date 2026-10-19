# Reporting integration diagram

Reporting is a read-only project package. It owns no database models or migrations; it combines persisted records from their domain apps at request time.

```mermaid
flowchart LR
    React[React dashboard and reports]
    Auth[Session/JWT authentication]
    Dashboard[GET /api/dashboard/summary/]
    Report[GET /api/report/report-id/]
    CSV[GET /api/report/report-id/csv/]
    Service[Reporting query service]
    Orders[(Order and OrderLine)]
    Payments[(Payment, Refund, COD handover)]
    Inventory[(Variant and InventoryBalance)]
    Delivery[(DeliveryJob and Helper)]
    Settings[(BusinessSettings)]

    React --> Auth
    Auth --> Dashboard
    Auth --> Report
    Auth --> CSV
    Dashboard --> Service
    Report --> Service
    CSV --> Service
    Service --> Orders
    Service --> Payments
    Service --> Inventory
    Service --> Delivery
    Service --> Settings
```

Money stays in integer cents in JSON. CSV exports format money as decimal currency values for spreadsheet use. Dates are inclusive and interpreted using the configured business timezone.

- [Dashboard summary](dashboard.md)
- [Reports and CSV exports](report.md)
- [API index](../README.md)
