# Authentication (Bearer)

Use a shared bearer token in development:
```
Authorization: Bearer <token>
```

Set `API_BEARER_TOKENS` to a JSON list of tokens and send one as the bearer. Requests without a valid bearer are rejected.

Example:
```
API_BEARER_TOKENS=["secret123","another-token"]
```

> **Planned**: Production-ready auth (OAuth/OIDC/JWT) is on the roadmap. The dev bearer is a temporary convenience.
