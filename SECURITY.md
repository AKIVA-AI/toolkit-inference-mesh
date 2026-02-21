# Security Policy (Toolkit Inference Mesh)

## Reporting a vulnerability

If you believe you have found a security vulnerability, do not open a public issue with exploit details.
Instead, report it privately via your organizationâ€™s security channel.

## Security notes (important)

This project is a distributed inference engine and includes networked components.

Before running in production, ensure you have:

- Authn/Authz in front of exposed HTTP endpoints (do not expose the scheduler API unauthenticated).
- TLS termination (load balancer, reverse proxy, or service mesh) for any external access.
- Network policy that restricts cluster ports to the VPC/subnet only.
- Explicit pinned P2P ports (avoid random ports on cloud deployments).
- Secrets management (do not bake API keys into images; use Secret Manager/Vault/KMS).

## Supported versions

Only the latest released version is supported with security fixes.


