# User API

## Purpose and access

Authenticates the single v1 owner and exposes only safe profile fields. CSRF, login, token obtain, and token refresh are public and throttled; all other actions require a session or bearer token. User listing, account creation, passwords, groups, permissions, and privilege fields are not exposed.

## Endpoints

- `GET /api/users/user/csrf/` — set cookie and return `{"csrf_token":"..."}`.
- `POST /api/users/user/login/` — `{ "email": "owner@example.com", "password": "..." }`; requires CSRF.
- `POST /api/users/user/logout/` — flush the current session only.
- `GET|PATCH /api/users/user/me/` — read or update `first_name`, `last_name`, and `email`.
- `POST /api/users/user/token/` — obtain access and refresh tokens.
- `POST /api/users/user/token/refresh/` — rotate a refresh token and blacklist the old token.
- `POST /api/users/user/token/blacklist/` — revoke the supplied device refresh token.

There are no filters because there is no user list. A profile response includes UUID `id`, email, names, and safe account timestamps/flags only. Invalid credentials use a generic response; duplicate/invalid email or unsafe fields return `400`. Related models: `NotificationReceipt`, `AuditEvent`, `PriceHistory`, and `StockMovement`.
