# Order model and transaction flow

```mermaid
flowchart TD
    Create[POST order with Idempotency-Key] --> Lock[Lock variants and balances]
    Lock --> Snapshot[Create Order and immutable OrderLine snapshots]
    Snapshot --> Reserve[Create StockReservation and increase promised]
    Reserve --> Kind{Special lines?}
    Kind -- No --> Ordinary[ORD sequence]
    Kind -- Yes --> Special[SO sequence and requested status]
    Special --> Quote[quoted then confirmed]
    Quote --> Receive[Receive each special OrderLine]
    Receive --> Hidden[Hidden Product + Variant + Balance]
    Hidden --> Received[Received movement and reservation]
    Received --> Final[Final price and customer notification]
    Ordinary --> Fulfil[Fulfil pickup or delivery]
    Final --> Fulfil
    Fulfil --> Sold[Consume reservations and create Sold movements]
    Sold --> Pay[Payment and refund services]
    Pay --> Complete[Complete only with zero balance]
```

`Order` integrates with `Customer`, catalog variants, inventory reservations/movements, payments/refunds, and one optional delivery job. See [Order](order.md), [OrderLine](order_line.md), and [Inventory](../inventory/diagram.md).
