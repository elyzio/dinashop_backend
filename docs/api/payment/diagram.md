# Payment, refund, and COD flow

```mermaid
flowchart LR
    Order[Order] --> Payment[Payment]
    Order --> Refund[Refund]
    Refund --> Lines[RefundLine]
    Lines --> OrderLine[OrderLine]
    Lines --> Variant[Returned ProductVariant]
    Lines --> Movement[Reversal / Damaged StockMovement]
    Delivery[Delivered COD DeliveryJob] --> CODPayment[Linked cash Payment]
    CODPayment --> Held[Helper-held cash]
    Held --> Handover[CodHandover]
    Payment --> PayReceipt[Payment receipt DTO]
    Refund --> RefundReceipt[Refund receipt DTO]
```

All financial records are append-only. Payment status, refundable values, cash payout, and COD held amounts are derived by backend services.

See [Payment](payment.md), [Refund](refund.md), [RefundLine](refund_line.md), and [COD handover](cod_handover.md).
