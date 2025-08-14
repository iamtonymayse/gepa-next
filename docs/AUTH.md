# Authentication (Bearer)

Use shared bearer tokens in development (list):
```
Authorization: Bearer ${API_TOKEN}  # gitleaks:allow (docs example; placeholder token)
```

Set `API_BEARER_TOKENS` (JSON list) in `.env`, e.g.:
```
API_BEARER_TOKENS=["<token-1>","<token-2>"]
```

Requests without a valid bearer are rejected unless developer mode is enabled (`python -m innerloop --dev`).

> **Planned**: Production-ready auth (OAuth/OIDC/JWT) is on the roadmap. The dev bearer is a temporary convenience.
