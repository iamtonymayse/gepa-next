# Authentication (Bearer)

Use a single shared bearer token in development:
```
Authorization: Bearer <API_BEARER_TOKEN>
```

Set `API_BEARER_TOKEN` in `.env`. Requests without a valid bearer are rejected.

> **Planned**: Production-ready auth (OAuth/OIDC/JWT) is on the roadmap. The dev bearer is a temporary convenience.
