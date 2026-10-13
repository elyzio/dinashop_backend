# AuditEvent API

## Purpose and access

Provides append-only operational history for authenticated owner review. Events can only be written by domain services; POST, PUT, PATCH, and DELETE return `405`.

## Endpoints and filters

- `GET /api/custom/audit-event/`
- `GET /api/custom/audit-event/{id}/`
- Filters: `actor`, `action`, `entity_type`, `entity_id`; date filters: `from`, `to`; search action/type/ID; newest first.

Example records contain `actor`, `action`, entity identity, before/after JSON, request UUID, IP address, and UTC `created_at`. Invalid filter values return `400`; missing records return `404`. Related models include all service-mutated phase-one entities.
