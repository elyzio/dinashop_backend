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

There are no filters because there is no user list. A profile response includes UUID `id`, email, first name, and last name only. Invalid credentials use a generic response. Related models: `NotificationReceipt`, `AuditEvent`, `PriceHistory`, and `StockMovement`.

## Usage examples

### Start a browser session

First obtain a CSRF token. The response also sets the `csrftoken` cookie.

```http
GET /api/users/user/csrf/
```

```json
{"csrf_token":"generated-token"}
```

Then send the cookie and token when logging in:

```http
POST /api/users/user/login/
Content-Type: application/json
Cookie: csrftoken=generated-token
X-CSRFToken: generated-token

{"email":"owner@example.com","password":"your-password"}
```

```json
{
  "id":"81db6f41-8a94-4d1c-aea2-37f2c63efdb2",
  "email":"owner@example.com",
  "first_name":"Dina",
  "last_name":"Owner"
}
```

The response sets the `sessionid` cookie. Send both cookies plus `X-CSRFToken` for later unsafe browser requests.

### Read and update the current owner

```http
GET /api/users/user/me/
Authorization: Bearer <access-token>
```

`PATCH` supports only `first_name` and `last_name`; email and privilege fields cannot be changed here.

```http
PATCH /api/users/user/me/
Authorization: Bearer <access-token>
Content-Type: application/json

{"first_name":"Dina","last_name":"Shop Owner"}
```

The response is the updated four-field profile. There is no owner list, create, password-change, privilege-update, or delete endpoint in v1.

### Obtain, rotate, and revoke JWTs

```http
POST /api/users/user/token/
Content-Type: application/json

{"email":"owner@example.com","password":"your-password"}
```

```json
{"refresh":"<refresh-token>","access":"<access-token>"}
```

```http
POST /api/users/user/token/refresh/
Content-Type: application/json

{"refresh":"<current-refresh-token>"}
```

Rotation returns a new access token and refresh token and blacklists the old refresh token. Revoke the current device with:

```http
POST /api/users/user/token/blacklist/
Content-Type: application/json

{"refresh":"<current-refresh-token>"}
```

### Log out the current browser

```http
POST /api/users/user/logout/
Cookie: sessionid=<session>; csrftoken=<token>
X-CSRFToken: <token>
```

Success is `204 No Content`; other browser sessions remain active.

## Error examples

Invalid login credentials return `400` without revealing whether the email exists:

```json
{"error":{"code":"invalid_credentials","message":"The email or password is incorrect."}}
```

Missing authentication on `/me/` or `/logout/` returns `401`:

```json
{"error":{"code":"authentication_required","message":"Valid authentication credentials are required."}}
```

Missing or incorrect CSRF on session login or another unsafe session request returns `403`. This response comes from Django's CSRF middleware and may be HTML rather than the normal DRF JSON envelope. An invalid or blacklisted refresh token returns `401` with a token validation error. `DELETE /api/users/user/me/` returns `405` because deleting users is not exposed.
