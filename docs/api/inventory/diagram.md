# Inventory app diagrams

Inventory separates the mutable current balance from explicit reservations and immutable movement history.

## Model relationships

```mermaid
flowchart LR
    subgraph CATALOG[catalog app]
        PV[ProductVariant]
    end

    subgraph INVENTORY[inventory app]
        IB[InventoryBalance]
        SR[StockReservation]
        SM[StockMovement]
    end

    subgraph ORDER[order app]
        O[Order]
        OL[OrderLine]
    end

    subgraph USERS[users app]
        U[User]
    end

    subgraph CUSTOM[custom app]
        AE[AuditEvent]
    end

    IB -->|variant one-to-one, PROTECT| PV
    SR -->|variant FK, PROTECT| PV
    SR -->|order_line one-to-one, PROTECT| OL
    SM -->|variant FK, PROTECT| PV
    SM -->|order FK, optional, PROTECT| O
    SM -->|recorded_by FK, PROTECT| U
    SM -.->|service writes generic audit event| AE
```

`InventoryBalance` is the current snapshot: `available = in_hand - promised`. `StockReservation` explains promised quantities per order line. `StockMovement` is the append-only ledger explaining how stock changed.

## Receiving and adjustment commands

```mermaid
flowchart TD
    R[Receive request] --> KEY[Validate UUID Idempotency-Key]
    KEY --> EXISTS{Movement already exists?}
    EXISTS -->|yes| REPLAY[Return original movement and balance, replayed true]
    EXISTS -->|no| TX[Begin transaction]
    TX --> LOCK[Lock InventoryBalance with select_for_update]
    LOCK --> COST[Calculate half-up per-unit landed cost]
    COST --> ADD[Increase in_hand and update landed cost]
    ADD --> MOVE[Append received StockMovement]
    MOVE --> AUDIT[Append AuditEvent]
    AUDIT --> COMMIT[Commit once]

    ADJ[Adjustment request] --> ALOCK[Lock InventoryBalance]
    ALOCK --> VALID{New in_hand is non-negative and at least promised?}
    VALID -->|no| BAD[400 validation_error, rollback]
    VALID -->|yes| UPDATE[Update balance]
    UPDATE --> AMOVE[Append damaged or adjustment movement]
    AMOVE --> AAUDIT[Append AuditEvent and commit]
```

## Reservation integration in the order phase

```mermaid
flowchart LR
    CREATE[Order service creates catalog line] --> LOCK[Lock variant balance]
    LOCK --> CHECK{available stock covers quantity?}
    CHECK -->|yes| RES[Create active StockReservation]
    RES --> PROMISE[Increase InventoryBalance.promised]
    PROMISE --> FULFIL{Order outcome}
    FULFIL -->|fulfilled| CONSUME[Mark consumed, reduce in_hand and promised, append sold movement]
    FULFIL -->|cancelled| RELEASE[Mark released, reduce promised]
    CHECK -->|no| REJECT[Reject order line]
```

The reservation workflow is documented for integration, but its mutation endpoints remain deferred until the order API phase. Phase one exposes reservations read-only.

## Related documentation

- [InventoryBalance](inventory_balance.md)
- [StockReservation](stock_reservation.md)
- [StockMovement](stock_movement.md)
- [API conventions](../README.md)
