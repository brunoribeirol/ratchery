---
name: api-contract-review
description: Review an API change for request/response contracts, compatibility, validation, errors, auth, pagination, idempotency, and documentation. Use only in repositories exposing HTTP/RPC APIs or formal API schemas.
---

# API Contract Review

- Identify routes/RPC methods, schemas, consumers, and compatibility guarantees.
- Check request validation, response shape, status/error semantics, auth/authz, pagination, filtering, idempotency, and rate-limit implications.
- Compare implementation with OpenAPI, GraphQL, protobuf, or other committed contracts when present.
- Flag breaking changes explicitly and propose versioning or migration paths when required.
- Check tests at contract boundaries rather than only internal units.
- Return affected endpoints/contracts, compatibility risk, and validation cases.
