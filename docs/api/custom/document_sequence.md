# DocumentSequence

## Purpose and access

Allocates unique human-readable document numbers while holding a PostgreSQL row lock. It has **no API endpoint**: direct reads or writes could allow duplicate order, payment, or refund numbers.

Application services call `DocumentSequence.next_number(key=..., prefix=...)` inside an atomic transaction. A missing sequence or mismatched prefix is a server configuration error. Authentication, filters, request examples, and HTTP errors do not apply because the model is internal-only. Related future models: `Order`, `Payment`, and `Refund`.
