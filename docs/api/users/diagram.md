# Users app diagrams

These diagrams show how authentication ownership and audit attribution connect the `users` app to the rest of the backend.

## Model relationships

```mermaid
flowchart LR
    subgraph USERS[users app]
        U[User]
        NR[NotificationReceipt]
    end

    subgraph CUSTOM[custom app]
        AE[AuditEvent]
    end

    subgraph CATALOG[catalog app]
        PH[PriceHistory]
    end

    subgraph INVENTORY[inventory app]
        SM[StockMovement]
    end

    subgraph ORDER[order app]
        O[Order]
    end

    subgraph PAYMENT[payment app]
        P[Payment]
        R[Refund]
        CH[CodHandover]
    end

    subgraph FULFILLMENT[fulfillment app]
        DJ[DeliveryJob]
    end

    NR -->|user FK, many-to-one, CASCADE| U
    AE -->|actor FK, optional, PROTECT| U
    PH -->|changed_by FK, PROTECT| U
    SM -->|recorded_by FK, PROTECT| U
    O -->|created_by FK, PROTECT| U
    P -->|received_by FK, PROTECT| U
    R -->|processed_by FK, PROTECT| U
    CH -->|recorded_by FK, PROTECT| U
    DJ -->|created_by and updated_by FKs, PROTECT| U
```

`NotificationReceipt` is the only operational child deleted with its user. Historical business records use `PROTECT`, which prevents removing the actor while those records exist. In v1 every active authenticated `User` is treated as an owner; customers and helpers are separate records and never authenticate.

## Browser session and JWT interaction

```mermaid
flowchart TD
    B[Browser client] --> C[GET user/csrf]
    C --> CC[CSRF cookie and token]
    CC --> L[POST user/login with X-CSRFToken]
    L --> S[Django session cookie]
    S --> A[SessionAuthentication]

    X[Future non-browser client] --> T[POST user/token]
    T --> J[Access and refresh JWT]
    J --> JA[JWTAuthentication]

    A --> P[IsAuthenticatedOwner]
    JA --> P
    P --> API[Protected API view]
    API --> SV[Domain service]
    SV -.-> AE2[AuditEvent with actor]

    S --> LO[POST logout]
    J --> BL[POST token/blacklist]
    LO --> ONLY1[Only that browser session ends]
    BL --> ONLY2[Only that refresh token is revoked]
```

Session-authenticated `POST`, `PUT`, `PATCH`, and `DELETE` requests require the CSRF header. JWT requests use the bearer access token and do not use Django session CSRF validation.

## Related documentation

- [User API](user.md)
- [NotificationReceipt API](notification_receipt.md)
- [API conventions](../README.md)
