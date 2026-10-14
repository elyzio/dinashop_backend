# DocumentSequence

## Purpose and access

Allocates unique human-readable document numbers while holding a PostgreSQL row lock. It has **no API endpoint**: direct reads or writes could allow duplicate order, payment, or refund numbers.

Application services call `DocumentSequence.next_number(key=..., prefix=...)` inside an atomic transaction. A missing sequence or mismatched prefix is a server configuration error. Authentication, filters, request examples, and HTTP errors do not apply because the model is internal-only. Current consumers are `Order`, `Payment`, and `Refund` services.

## Internal usage example

There are no list, add, update, or delete HTTP operations. The operational-default migration seeds `order / ORD`, `special_order / SO`, `payment / PAY`, and `refund / RF`. Allocate numbers only from a domain service:

```python
from custom.models import DocumentSequence

order_number = DocumentSequence.next_number(key="order", prefix="ORD")
# Example result: ORD-0001
```

`next_number()` opens an atomic transaction and locks the selected row, so simultaneous requests cannot receive the same number. Do not calculate the next value in an API serializer or frontend.

## Error behavior

Calling a nonexistent API such as `GET /api/custom/document-sequence/` returns `404` because no route is registered. A missing database row raises `DocumentSequence.DoesNotExist` inside the calling service. Passing a prefix different from the stored prefix raises `ValueError`, for example:

```text
Sequence 'order' is configured with another prefix.
```

Order and payment services treat these as deployment/configuration failures. Clients must never be allowed to repair a sequence through an HTTP request.
