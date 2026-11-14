# open-appsec WAF Security Lab

![open-appsec](https://img.shields.io/badge/WAF-open--appsec-0A66C2)
![NGINX](https://img.shields.io/badge/Reverse%20Proxy-NGINX-009639)
![Docker](https://img.shields.io/badge/Runtime-Docker%20Compose-2496ED)
![SOAR](https://img.shields.io/badge/SOAR-TheHive%20%7C%20Cortex%20%7C%20MISP-6A5ACD)
![Scope](https://img.shields.io/badge/Scope-Isolated%20Lab%20Only-orange)

A hands-on Web Application Firewall and SOC integration lab. The WAF
layer uses **open-appsec + NGINX** to protect and reverse-proxy
intentionally vulnerable applications. The extended deployment also
publishes **TheHive, Cortex, and MISP** from a separate SOAR VM through
the same NGINX frontend.

> **Lab use only.** Juice Shop and DVWA are deliberately vulnerable.
> Run this environment on an isolated network and test only systems you
> own or are explicitly authorized to test.

---

## Overall architecture

The extended deployment has two virtual machines:

- **WAF VM:** NGINX, the open-appsec NGINX attachment, and the
  open-appsec agent. It reverse-proxies web applications and the SOAR
  web interfaces.
- **SOAR VM:** TheHive, Cortex, and MISP. These services remain on a
  separate host and are reached through NGINX virtual hosts.

```mermaid
flowchart TB
    CLIENT["Browser / Security Tester"]
    ANALYST["SOC Analyst"]
    PORTAL["open-appsec Cloud Portal"]

    subgraph WAFVM["VM 1 — WAF SERVER"]
        direction TB
        NGINX["NGINX Reverse Proxy<br/>192.168.1.116"]
        ATTACH["open-appsec NGINX Attachment"]
        AGENT["open-appsec Agent / Inspection Engine"]
        NGINX <--> |"Shared memory / IPC"| ATTACH
        ATTACH <--> AGENT
        subgraph WEB["Web Application Backends"]
            JUICE["Juice Shop<br/>192.168.1.117:3000"]
            DVWA["DVWA<br/>192.168.1.118:80"]
        end
        NGINX --> JUICE
        NGINX --> DVWA
    end

    subgraph SOARVM["VM 2 — SOAR SERVER · 192.168.1.121"]
        THEHIVE["TheHive :9000"]
        CORTEX["Cortex :9001"]
        MISP["MISP HTTPS :443"]
    end

    CLIENT --> NGINX
    ANALYST --> NGINX
    NGINX -->|"192.168.1.116:9000"| THEHIVE
    NGINX -->|"192.168.1.116:9001"| CORTEX
    NGINX -->|"https://192.168.1.116"| MISP
    AGENT <-->|"Policy / telemetry"| PORTAL
    THEHIVE -.->|"Integration paths to validate"| CORTEX
    THEHIVE -.->|"Threat-intel integration to validate"| MISP
```

See [Overall WAF and SOAR Architecture](architecture/architecture.md)
for the complete topology, network inventory, traffic flow, and
validation boundaries.

## Network and service inventory

| Component | Address | Access |
|---|---|---|
| WAF NGINX frontend | `192.168.1.116` | HTTP / HTTPS virtual hosts |
| Juice Shop backend | `192.168.1.117:3000` | Through WAF |
| DVWA backend | `192.168.1.118:80` | Through WAF frontend `192.168.1.116` |
| SOAR VM | `192.168.1.121` | Separate VM |
| TheHive backend | `192.168.1.121:9000` | Proxied through `http://192.168.1.116:9000` |
| Cortex backend | `192.168.1.121:9001` | Proxied through `http://192.168.1.116:9001` |
| MISP backend | `192.168.1.121:443` | Proxied through `https://192.168.1.116` |

The current SOAR VM address is `192.168.1.121`. Its previous address was `192.168.1.114`.

### SOAR frontend URLs

The current SOAR frontends use IP-based listeners; no SOAR hostname or client hosts-file entry is required:

- TheHive: `http://192.168.1.116:9000/`
- Cortex: `http://192.168.1.116:9001/`
- MISP: `https://192.168.1.116/` (the lab frontend certificate is self-signed; use `curl -k` for command-line validation only).

Juice Shop and DVWA continue to use hostname routing on `192.168.1.116:80`.

## Components

| Component | Role |
|---|---|
| open-appsec agent | WAF inspection engine and policy management |
| open-appsec NGINX attachment | Integrates NGINX request processing with open-appsec |
| NGINX | Client-facing reverse proxy and virtual-host routing |
| OWASP Juice Shop | Intentionally vulnerable web application |
| DVWA | Intentionally vulnerable web application |
| TheHive | Security incident and case management |
| Cortex | Analyzer and responder platform |
| MISP | Threat-intelligence platform |

The WAF Compose template deploys only the open-appsec agent and NGINX
attachment. The vulnerable applications and SOAR stack are separate
services/hosts in the observed lab; they are not added to that Compose
project.

## Quick Start — WAF core

```bash
git clone https://github.com/Pamidipallikiran/open-appsec-waf-security-lab.git
cd open-appsec-waf-security-lab

cp .env.example .env
nano .env                       # add your own agent token and e-mail

docker compose --env-file .env.example -f compose.yaml config --quiet
docker compose up -d
docker compose ps
```

Prerequisites (macvlan network, backend containers, host requirements)
are in the [Docker Deployment guide](documentation/docker-deployment.md).

The SOAR reverse-proxy topology and validation procedure are documented
separately in [SOAR Integration](documentation/soar-integration.md).
Do not run the WAF Compose template on the SOAR VM.

## Verification status and evidence

| Area | Status | Evidence / limitation |
|---|---|---|
| Juice Shop reverse proxy | Verified | Baseline application response through WAF frontend |
| TheHive reverse proxy | Verified | Application HTML returned through WAF frontend |
| Cortex reverse proxy | Verified | Expected redirect / application response through WAF frontend |
| MISP reverse proxy | Verified | Expected login redirect through HTTPS WAF frontend |
| open-appsec NGINX module / attachment | Verified | Module loaded and attachment registration observed |
| SOAR XSS detection | Detected (14 Nov 2026) | User-observed open-appsec portal events for controlled XSS requests to TheHive, Cortex and MISP; action recorded as Detect, not Prevent |
| SOAR event display latency | Observed delay | Events appeared after the requests; exact portal delay was not measured |
| SOAR XSS prevention | Not tested | Detect-mode events do not establish blocking |
| DVWA reverse proxy | Verified (2026-11-13) | HTTP 302 redirect to `login.php` through frontend `192.168.1.116`; confirms routing, not WAF detection or prevention |
| Automatic WAF-event-to-TheHive case creation | Not verified | Treat as a future integration until a controlled end-to-end test succeeds |
| TheHive-to-Cortex / MISP integrations | Validate separately | Reverse-proxy access does not prove application-level integration |

Historical custom Snort signature tests are documented in
[Custom Snort Rules](detection/custom-snort-rules.md). Re-run the
controlled tests against the current runtime and confirm the event's
Practice SubType, Protection Name, and Security Action before reporting
a detection or prevention result.

### Reproduce the routing checks

Check NGINX configuration syntax:

```bash
docker exec appsec-nginx nginx -t
```

Test Juice Shop routing:

```bash
curl -sS -D - -o /dev/null --resolve juice.lab.local:80:192.168.1.116 http://juice.lab.local/
```

Test DVWA routing:

```bash
curl -sS -D - -o /dev/null --resolve dvwa.lab.local:80:192.168.1.116 http://dvwa.lab.local/
```

Recorded checks on 2026-11-13 returned HTTP 200 for Juice Shop and HTTP 302 to `login.php` for DVWA. These checks verify routing and reachability only; they do not independently prove WAF detection or prevention.

For WAF validation, inspect the open-appsec event and confirm its protection details, indicators, practice subtype and security action. See [Custom Snort Rules](detection/custom-snort-rules.md).

## Recorded Live Lab Status

Snapshot date: 2026-11-14.

| Component | Recorded address |
|---|---|
| WAF host | `192.168.1.113` |
| NGINX frontend | `192.168.1.116` |
| OWASP Juice Shop | `192.168.1.117:3000` |
| DVWA | `192.168.1.118:80` |
| SOAR host | `192.168.1.121` |
| Docker network | `macvlan-lab` |

The NGINX hostname routing for Juice Shop and DVWA was verified. The NGINX configuration syntax check also passed.

On 2026-11-14, IP-based TheHive, Cortex and MISP frontend requests returned HTTP 200, 303 and 302 respectively. Controlled XSS requests returned the same application responses and were subsequently observed as detections in the open-appsec portal. The portal action was Detect; this confirms detection, not prevention. Event appearance was reported as delayed, but the exact delay was not measured. MISP HTTPS testing used `curl -k`, which skips certificate verification.

Historical WAF detection tests are documented separately and must not be treated as fresh tests performed on this snapshot date.

## Optional SOAR Reverse Proxies

Reference configurations are provided in:

- `configurations/nginx/optional/thehive-cortex.conf.example`
- `configurations/nginx/optional/misp.conf.example`

The current live configuration uses IP-based listeners on ports 9000, 9001 and 443. The examples are not loaded automatically by the default NGINX configuration; review upstream addresses and certificate paths before enabling them.

The MISP example disables upstream TLS certificate verification as a temporary lab workaround. This is not suitable for production. Configure a trusted CA certificate and enable upstream verification before production use.

## Documentation

| Document | Contents |
|---|---|
| [Overall WAF and SOAR Architecture](architecture/architecture.md) | Two-VM topology, IP inventory, request flow, SOAR workflow |
| [SOAR Reverse-Proxy Integration](documentation/soar-integration.md) | TheHive, Cortex, and MISP routing and validation |
| [NGINX Configuration](documentation/nginx-configuration.md) | Backend selection and proxy directives |
| [Docker Deployment](documentation/docker-deployment.md) | WAF containers, networks, volumes, setup |
| [Custom Snort Rules](detection/custom-snort-rules.md) | Signatures, controlled tests, and event verification |

## Repository structure

```text
open-appsec-waf-security-lab/
├── architecture/
│   └── architecture.md
├── configurations/
│   └── nginx/
│       ├── default.conf
│       └── optional/
│           ├── misp.conf.example
│           └── thehive-cortex.conf.example
├── detection/
│   ├── custom-snort-rules.md
│   └── rules/
│       └── lab-rules.rules
├── documentation/
│   ├── docker-deployment.md
│   ├── nginx-configuration.md
│   └── soar-integration.md
├── .env.example
├── .gitignore
├── compose.yaml
└── README.md
```

## Security notes

- Secrets live only in a local `.env` (git-ignored). Only
  `.env.example` is committed. Never publish agent tokens, API keys,
  passwords, or private keys.
- Agent state and runtime data are git-ignored because they can contain
  registration material.
- The agent and NGINX attachment use host IPC and a shared-memory mount
  as required by this integration. Treat the host as trusted lab
  infrastructure.
- Restrict direct access to backend applications and SOAR service ports
  so traffic cannot bypass the intended reverse-proxy path.
- The current MISP upstream TLS verification bypass is lab-only. Use a
  trusted certificate and enable verification for production.
- Keep the deliberately vulnerable applications isolated from untrusted
  networks.

## Learning objectives

- Deploy open-appsec with NGINX in containers.
- Understand reverse-proxy routing and backend selection.
- Inspect HTTP traffic through a WAF integration.
- Write, import, and verify custom Snort signatures.
- Distinguish detection from prevention using authoritative events.
- Publish multiple applications through NGINX virtual hosts.
- Understand how TheHive, Cortex, and MISP support SOC investigation.
- Separate reverse-proxy connectivity from end-to-end SOAR automation.

## Disclaimer

Educational and authorized security testing only. The vulnerable
applications must never be exposed to untrusted networks.

## Author

**Kiran Pamidipalli** — Cybersecurity / SOC Analyst
