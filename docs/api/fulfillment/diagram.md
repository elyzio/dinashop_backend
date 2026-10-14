# Fulfillment model and command flow

```mermaid
stateDiagram-v2
    [*] --> Assigned: create eligible job
    Assigned --> OutForDelivery: start
    OutForDelivery --> Delivered: deliver and consume stock
    OutForDelivery --> Failed: fail with reason
    Delivered --> CODPayment: COD remaining balance
    CODPayment --> CodHandover: partial or full handover
    Failed --> CancelledOrder: release reservations and cancel order
```

`DeliveryJob` belongs to one delivery `Order`, one active `Helper`, and optionally one immutable COD `Payment`. See [DeliveryJob](delivery_job.md), [Order](../order/order.md), and [COD handover](../payment/cod_handover.md).
