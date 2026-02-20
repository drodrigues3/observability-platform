# ADR-003: Chainguard Distroless Images for Zero-CVE Containers

**Status:** Accepted
**Date:** 2026-02-20
**Deciders:** SRE Platform Team

---

## Context

All three application images (workload-simulator, stream-processor, metrics-bridge) were built using `python:3.11-slim` (Debian Bookworm) as the final stage. While `slim` removes many packages compared to the full image, it still ships with hundreds of Debian packages (apt, coreutils, bash, libc utilities, etc.) that:

1. Accumulate CVEs over time — a typical `python:3.11-slim` scan returns 50-150+ known vulnerabilities.
2. Expand the attack surface — a shell and package manager inside a production container enable post-exploitation lateral movement.
3. Increase image size — ~150 MB vs ~50 MB for a distroless equivalent.

The project targets **zero known CVEs** in production container images.

## Decision

We adopted **Chainguard distroless Python images** (`cgr.dev/chainguard/python`) with a two-stage build:

| Stage | Image | Role |
|-------|-------|------|
| Builder | `cgr.dev/chainguard/python:latest-dev` | Install Poetry and dependencies (has pip, shell, build tools) |
| Final | `cgr.dev/chainguard/python:latest` | Run application (distroless — no shell, no package manager) |

Both stages share the same Python version, ensuring virtual environment compatibility.

## Alternatives Considered

| Option | CVE Count | Pros | Rejected Because |
|--------|-----------|------|-----------------|
| `python:3.11-slim` (Debian) | 50-150+ | Familiar, wide ecosystem | Too many CVEs; shell present |
| `python:3.11-alpine` | 5-20 | Smaller than slim | musl libc breaks some wheels (confluent-kafka); still has shell/apk |
| `gcr.io/distroless/python3-debian12` | 0-5 | Google-maintained, Debian-based | Less frequently updated; Python version not always current |
| Azure Linux Distroless (`mcr.microsoft.com/cbl-mariner/distroless/python`) | 0-5 | Microsoft-maintained | Smaller community; Python version lag |
| AWS Lambda base (`public.ecr.aws/lambda/python`) | N/A | Optimized for Lambda | Includes Lambda Runtime Interface Client; not suitable for general containers |

## Consequences

### Positive

- **0 CVE target:** Chainguard images are rebuilt daily against the latest package versions and security patches. Trivy scans consistently report zero known vulnerabilities.
- **Minimal attack surface:** No shell (`/bin/sh`), no package manager, no coreutils. An attacker who gains code execution cannot easily pivot.
- **Non-root by default:** The `latest` tag runs as UID 65532 (`nonroot`) — no need for `groupadd`/`useradd`/`chown` in the Dockerfile.
- **Smaller images:** ~50 MB final image vs ~150 MB with `python:3.11-slim`.
- **CI enforcement:** Trivy scans in the GitHub Actions pipeline fail the build on any CRITICAL or HIGH CVE, preventing regressions.

### Negative

- **No shell for debugging:** `kubectl exec` into a running container will fail — there is no shell. Debugging requires ephemeral containers (`kubectl debug`) or log analysis.
- **No Dockerfile HEALTHCHECK:** The `HEALTHCHECK CMD` directive requires `/bin/sh`. This is acceptable because Kubernetes liveness/readiness probes (defined in Helm charts) handle health checking.
- **Image tag volatility:** The free `latest` tag always points to the newest Python version. Pinning to a specific Python minor requires Chainguard's paid tier or version-checking in CI.
- **Builder compatibility:** Both stages must use Chainguard images to ensure the same Python version. Mixing `python:3.11-slim` builder with Chainguard final risks venv path mismatches.

### Mitigations

| Risk | Mitigation |
|------|-----------|
| Cannot debug in-container | Use `kubectl debug --image=busybox` ephemeral containers; rely on structured JSON logs |
| `latest` tag Python version drift | CI tests validate the full application on every push; version mismatch would be caught immediately |
| Wheel compatibility | `confluent-kafka` and all dependencies publish `manylinux` wheels that are compatible with Chainguard's glibc |
