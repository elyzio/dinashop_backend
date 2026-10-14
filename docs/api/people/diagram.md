# People model and API flow

```mermaid
flowchart LR
    Owner[Authenticated owner] --> CustomerAPI[/api/people/customer/]
    Owner --> HelperAPI[/api/people/helper/]
    CustomerAPI --> Customer[Customer]
    HelperAPI --> Helper[Helper]
    Customer -->|protected by| Order[Order]
    Helper -->|assigned to| Job[DeliveryJob]
    Helper -->|hands over| COD[CodHandover]
    Job --> Payment[COD Payment]
    Customer --> Metrics[Order count and outstanding balance]
    Helper --> HelperMetrics[Jobs, fees, collected, handed and held]
```

Customers and helpers never authenticate. Historical relations use `PROTECT`; operational removal is deactivation. The seeded walk-in customer is valid only for ordinary pickup orders.

See [Customer](customer.md), [Helper](helper.md), and [API conventions](../README.md).
