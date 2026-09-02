# Security Review Checklist

- [ ] JWT with short access TTL (15m) + refresh rotation; HttpOnly secure cookies for refresh
- [ ] RBAC enforced at view + queryset level (admin/analyst/viewer)
- [ ] TLS everywhere (nginx + Django SECURE_* headers)
- [ ] Encryption at rest (Postgres TDE / volume encryption, S3 SSE)
- [ ] Secrets via Vault / AWS Secrets Manager (never in repo)
- [ ] Audit log for every read/write/export/query
- [ ] Rate limiting (DRF throttling) + per-source collection rate limits
- [ ] robots.txt respected, no auth/paywall bypass, ToS checks
- [ ] Input validation, SQL injection & XSS prevention (DRF serializers, CSP)
- [ ] Dependency scanning (Dependabot, pip-audit, npm audit)
- [ ] Container scanning (Trivy) in CI
- [ ] Centralized logging (ELK/Loki) without PII leakage
- [ ] Backup & restore tested for Postgres + S3
- [ ] Penetration test scheduled
