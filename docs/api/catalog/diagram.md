# Catalog app diagrams

The catalog is an aggregate rooted at `Product`. Options, variants, images, pricing history, categories, stock, orders, and refunds integrate through this root.

## Model relationships

```mermaid
flowchart LR
    subgraph CUSTOM[custom app]
        C[Category]
    end

    subgraph USERS[users app]
        U[User]
    end

    subgraph CATALOG[catalog app]
        P[Product]
        PC[ProductCategory]
        PI[ProductImage]
        PO[ProductOption]
        POV[ProductOptionValue]
        PV[ProductVariant]
        VOV[VariantOptionValue]
        PH[PriceHistory]
    end

    subgraph INVENTORY[inventory app]
        IB[InventoryBalance]
        SR[StockReservation]
        SM[StockMovement]
    end

    subgraph SALES[sales apps]
        OL[OrderLine]
        RL[RefundLine]
    end

    PC -->|product FK, CASCADE| P
    PC -->|category FK, PROTECT| C
    PI -->|product FK, CASCADE| P
    PO -->|product FK, CASCADE| P
    POV -->|option FK, CASCADE| PO
    PV -->|product FK, PROTECT| P
    VOV -->|variant FK, CASCADE| PV
    VOV -->|option FK, PROTECT| PO
    VOV -->|value FK, PROTECT| POV
    PH -->|variant FK, PROTECT| PV
    PH -->|changed_by FK, PROTECT| U

    IB -->|variant one-to-one, PROTECT| PV
    SR -->|variant FK, PROTECT| PV
    SM -->|variant FK, PROTECT| PV
    OL -->|variant FK, optional, PROTECT| PV
    RL -->|returned_variant FK, optional, PROTECT| PV
```

`ProductCategory` is the many-to-many bridge between products and categories. `VariantOptionValue` is the bridge that assigns exactly one value for each option to a variant. `InventoryBalance` is created for every variant and is one-to-one.

## Atomic product creation and image upload

```mermaid
flowchart TD
    REQ[POST product] --> V[Validate categories, option definitions, variants, and SKUs]
    V --> TX[Begin PostgreSQL transaction]
    TX --> P1[Create Product]
    P1 --> P2[Create ProductCategory links]
    P2 --> P3[Create options and values]
    P3 --> P4[Create variants and assignments]
    P4 --> P5[Create one InventoryBalance per variant]
    P5 --> A[Append AuditEvent]
    A --> COMMIT[Commit complete aggregate]
    V -->|any invalid value| ROLLBACK[400 and no product records]
    TX -->|any database failure| ROLLBACK

    COMMIT --> IMGREQ[POST product-image multipart]
    IMGREQ --> CHECK[Check type, 5 MB, 36 MP, and eight-image limit]
    CHECK --> WEBP[Orient, resize to 1600 x 1600, strip metadata, encode WebP]
    WEBP --> STORE[Save UUID object using configured storage]
    STORE --> IMGTX[Save ProductImage and AuditEvent]
    IMGTX --> DONE[Return persisted image URL and metadata]
    IMGTX -->|database failure| CLEAN[Delete newly stored orphan object]
```

Images are intentionally outside the product transaction because local or Supabase object storage cannot participate in a PostgreSQL rollback. Pricing commands lock `ProductVariant`, update its current price, and append immutable `PriceHistory` rows.

## Related documentation

- [Product](product.md), [ProductCategory](product_category.md), and [ProductImage](product_image.md)
- [ProductOption](product_option.md), [ProductOptionValue](product_option_value.md), and [VariantOptionValue](variant_option_value.md)
- [ProductVariant](product_variant.md) and [PriceHistory](price_history.md)
- [API conventions](../README.md)
