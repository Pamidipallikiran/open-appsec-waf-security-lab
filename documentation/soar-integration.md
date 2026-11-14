# SOAR Services Behind the open-appsec NGINX Reverse Proxy

## 1. Purpose

This guide documents how the separate SOAR VM publishes TheHive, Cortex, and MISP through the NGINX reverse proxy running on the WAF VM. The SOAR applications remain on their own VM; they are not moved into the WAF VM's Docker Compose project.

## 2. Topology

| Host | Address | Purpose |
|---|---|---|
| WAF VM / NGINX frontend | `192.168.1.116` | NGINX + open-appsec frontend |
| SOAR VM | `192.168.1.121` | TheHive, Cortex, and MISP backends |

| Client-facing URL | NGINX upstream |
|---|---|
| `http://192.168.1.116:9000/` (TheHive) | `http://192.168.1.121:9000` |
| `http://192.168.1.116:9001/` (Cortex) | `http://192.168.1.121:9001` |
| `https://192.168.1.116/` (MISP) | `https://192.168.1.121:443` |

The current SOAR frontend is IP-based. TheHive and Cortex use dedicated TCP ports 9000 and 9001; MISP uses HTTPS on port 443. Juice Shop and DVWA continue to use hostname-based routing on frontend port 80.

## 3. Client access

No SOAR hostname or hosts-file entry is required for the current IP-based URLs. Open the URLs listed in the topology table from a client that can reach the WAF frontend.

MISP currently uses a lab certificate. The `curl -k` option skips certificate verification and should be used only for lab validation.

## 4. NGINX listener behavior

The active WAF VM configuration uses separate NGINX server blocks:

- Listener `9000` proxies to `http://192.168.1.121:9000` (TheHive).
- Listener `9001` proxies to `http://192.168.1.121:9001` (Cortex).
- TLS listener `443` proxies to `https://192.168.1.121:443` (MISP).

TheHive and Cortex proxy blocks preserve the Host header, original client address, forwarded-for chain, and original scheme. They also support HTTP upgrade headers and use an extended read timeout for long-running application requests.

The MISP upstream currently uses TLS with upstream certificate verification disabled because the lab certificate is self-signed or expired. This setting is not suitable for production. Install a trusted upstream certificate, configure the correct CA trust, and enable certificate verification before using this pattern outside an isolated lab.

The live configuration is maintained on the WAF VM in the `open-appsec-lab/nginx-config/` directory. The repository's `configurations/nginx/default.conf` is the core Juice Shop / DVWA example and is not a complete copy of the live multi-listener configuration. Keep secrets and private keys out of the repository.

## 5. Request path

1. The client connects to the appropriate IP-based frontend URL on `192.168.1.116`.
2. The request reaches the matching NGINX listener on the WAF VM.
3. The open-appsec NGINX attachment integrates the request with the local inspection engine.
4. NGINX forwards the request to the corresponding SOAR backend on `192.168.1.121`.
5. TheHive, Cortex, or MISP returns its response through NGINX.

A successful application response proves that the reverse-proxy path works. It does not independently prove that a particular request was detected or blocked by open-appsec. Confirm the corresponding security event and action in the open-appsec portal.

## 6. Connectivity checks

Run these from a client that can reach the WAF frontend:

```bash
# TheHive
curl -sS -o /dev/null -w "TheHive HTTP: %{http_code}\n" http://192.168.1.116:9000/

# Cortex
curl -sS -o /dev/null -w "Cortex HTTP: %{http_code}\n" http://192.168.1.116:9001/

# MISP (the -k flag is for the current lab certificate only)
curl -k -sS -o /dev/null -w "MISP HTTP: %{http_code}\n" https://192.168.1.116/
```

Observed on 2026-11-14: TheHive HTTP 200, Cortex HTTP 303, and MISP HTTP 302. Redirects can be valid application responses; inspect the Location header and final application page when needed.

## 7. Operational and security notes

- Keep the SOAR VM's current address consistent in all upstream definitions.
- Restrict backend ports 9000, 9001, and 443 to trusted sources, preferably the WAF VM and approved administrators.
- Do not expose Juice Shop or DVWA directly to untrusted networks.
- Do not publish API tokens, passwords, MISP keys, or TLS private keys.
- Reverse-proxy reachability does not establish automatic open-appsec event forwarding to TheHive. Implement and test that workflow separately.
- TheHive-to-Cortex and TheHive-to-MISP integration links in the overall architecture are intended integration paths; verify each in its application's configuration and with a controlled test.

## 8. Validation checklist

- [ ] TheHive login page is reachable through `http://192.168.1.116:9000/`.
- [ ] Cortex login page is reachable through `http://192.168.1.116:9001/`.
- [ ] MISP login page is reachable through `https://192.168.1.116/`.
- [ ] open-appsec portal shows the expected asset and policy.
- [x] Controlled XSS tests produced matching detection events for all three SOAR frontends (Detect action, 2026-11-14).
- [ ] Prevent-mode behavior is verified by an event with Prevent action and by confirming the request did not reach the backend.
- [ ] Any desired TheHive/Cortex/MISP integrations are tested end to end.
- [ ] Automatic WAF-event-to-TheHive case creation is tested separately, if that automation is part of the project scope.

## 9. Recorded SOAR WAF validation (2026-11-14)

Baseline requests to the IP-based frontends returned TheHive HTTP 200, Cortex HTTP 303, and MISP HTTP 302. Controlled URL-encoded XSS test requests were sent to all three frontends. Matching Cross Site Scripting events were observed in the open-appsec portal for TheHive, Cortex and MISP. The recorded Security Action was **Detect**.

This confirms detection for the observed tests, not prevention. Event appearance was reported as delayed; no precise end-to-end latency measurement was captured. A separate TheHive request timing was approximately 35.4 ms, which measures application response time only, not event generation or portal display latency.
