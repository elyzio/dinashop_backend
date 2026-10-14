# Custom app diagrams

The `custom` app owns shared master data, singleton business configuration, document numbering, and the cross-domain audit trail.

## Model and integration relationships

```mermaid
flowchart LR
    subgraph CUSTOM[custom app]
        C[Category]
        BS[BusinessSettings]
        DS[DocumentSequence]
        AE[AuditEvent]
    end

    subgraph USERS[users app]
        U[User]
    end

    subgraph CATALOG[catalog app]
        PC[ProductCategory]
        P[Product]
    end

    subgraph OPERATIONS[other domain apps]
        O[Order services]
        PAY[Payment and refund services]
        INV[Inventory services]
        REC[Receipt, report, and alert queries]
    end

    C -->|optional parent FK, PROTECT| C
    PC -->|category FK, PROTECT| C
    PC -->|product FK, CASCADE| P
    AE -->|actor FK, optional, PROTECT| U

    DS -.->|allocates order numbers| O
    DS -.->|allocates payment and refund numbers| PAY
    BS -.->|currency, timezone, receipt text, thresholds| REC
    O -.->|writes audit events| AE
    PAY -.->|writes audit events| AE
    INV -.->|writes audit events| AE
    P -.->|catalog services write audit events| AE
```

Solid arrows are database relationships. Dashed arrows are service/query dependencies without foreign keys. `AuditEvent.entity_type` and `entity_id` are a generic reference, so an audit row describes many model types without creating a database foreign key to each table.

## Category update workflow

```mermaid
flowchart TD
    REQ[Category create or update request] --> SER[Validate explicit API fields]
    SER --> LOCK[Open transaction and lock existing row when updating]
    LOCK --> NAME[Trim and validate sibling name]
    NAME --> CYCLE[Check self-parenting and ancestor cycle]
    CYCLE --> SLUG[Generate collision-safe slug on create]
    SLUG --> SAVE[Save Category]
    SAVE --> AUDIT[Append AuditEvent]
    AUDIT --> COMMIT[Commit transaction]

    CYCLE -->|invalid hierarchy| E400[400 validation_error]
    REQ -->|delete with children, products, or protected slug| E409[409 state conflict]
```

`BusinessSettings` uses the fixed key `default`. `DocumentSequence` is internal-only and must be locked with `select_for_update()` when a number is allocated. `AuditEvent` is read-only through the API.

## Related documentation

- [Category](category.md)
- [BusinessSettings](business_settings.md)
- [DocumentSequence](document_sequence.md)
- [AuditEvent](audit_event.md)
- [API conventions](../README.md)
