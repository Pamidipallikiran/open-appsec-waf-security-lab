# SOAR Services Behind the open-appsec NGINX Reverse Proxy

## 1. Purpose

This guide documents how the separate SOAR VM publishes TheHive, Cortex,
and MISP through the NGINX reverse proxy running on the WAF VM.

The SOAR applications remain on their own VM. This is a reverse-proxy
integration, not a request to move the SOAR containers into the WAF
VM's Docker Compose project.

## 2. Topology

| Host | Address | Purpose |
|---|---|---|
| WAF VM | `192.168.1.116` | NGINX + open-appsec frontend |
| SOAR VM | `192.168.1.114` | TheHive, Cortex, and MISP backends |

| Public lab hostname | NGINX upstream |
|---|---|
| `thehive.lab.local` | `http://192.168.1.114:9000` |
| `cortex.lab.local` | `http://192.168.1.114:9001` |
| `misp.lab.local` | `https://192.168.1.114:443` |

The SOAR VM address is currently `192.168.1.114`. An older address,
`192.168.1.112`, is no longer the SOAR VM address and should not be
copied into new proxy configuration.

## 3. Client name resolution

Configure local DNS or a hosts file on each client so these names
resolve to the WAF frontend address:

```text
192.168.1.116  thehive.lab.local
192.168.1.116  cortex.lab.local
192.168.1.116  misp.lab.local
```

Use `http://thehive.lab.local/`, `http://cortex.lab.local/`, and
`https://misp.lab.local/` according to the active virtual-host
configuration.

## 4. NGINX virtual-host behavior

The active WAF VM configuration uses separate NGINX server blocks:

- `thehive.lab.local` proxies to `http://192.168.1.114:9000`.
- `cortex.lab.local` proxies to `http://192.168.1.114:9001`.
- `misp.lab.local` proxies to the SOAR VM's HTTPS service on port 443.

TheHive and Cortex proxy blocks preserve the Host header, original
client address, forwarded-for chain, and original scheme. They also
support HTTP upgrade headers and use an extended read timeout for
long-running application requests.

The MISP upstream currently uses TLS with upstream certificate
verification disabled because the lab certificate is self-signed or
expired. This setting is not suitable for production. Install a
trusted upstream certificate, configure the correct CA trust, and
enable certificate verification before using this pattern outside an
isolated lab.

The live configuration is maintained on the WAF VM in
`/home/kiranwaf/open-appsec-lab/nginx-config/`. The repository's
`configurations/nginx/default.conf` is the core Juice Shop / DVWA
example and is not a complete copy of the live multi-virtual-host
configuration. Keep secrets and private keys out of the repository.

## 5. Request path

1. The client resolves the service hostname to `192.168.1.116`.
2. The request reaches the NGINX frontend on the WAF VM.
3. The open-appsec NGINX attachment integrates the request with the
   local inspection engine.
4. NGINX selects the upstream using the request's virtual-host name.
5. The request is forwarded over the lab network to the SOAR VM.
6. TheHive, Cortex, or MISP returns its response through NGINX.

A successful application response proves that the reverse-proxy path
works. It does not independently prove that a particular request was
detected or blocked by open-appsec. Confirm the corresponding security
event and action in the open-appsec portal.

## 6. Connectivity checks

Run these from a client that can reach the WAF frontend:

```bash
# TheHive
curl -sS -o /dev/null -w 'TheHive HTTP: %{http_code}\n' \
  --resolve thehive.lab.local:80:192.168.1.116 \
  http://thehive.lab.local/

# Cortex
curl -sS -o /dev/null -w 'Cortex HTTP: %{http_code}\n' \
  --resolve cortex.lab.local:80:192.168.1.116 \
  http://cortex.lab.local/

# MISP (the -k flag is for the current lab certificate only)
curl -k -sS -o /dev/null -w 'MISP HTTP: %{http_code}\n' \
  --resolve misp.lab.local:443:192.168.1.116 \
  https://misp.lab.local/
```

Expected responses may include redirects (for example, Cortex or MISP
redirecting to a login page). A redirect can be a valid connectivity
result; inspect the Location header and final application page.

## 7. Operational and security notes

- Keep the SOAR VM's current address consistent in all upstream
  definitions.
- Restrict backend ports 9000, 9001, and 443 to trusted sources,
  preferably the WAF VM and approved administrators.
- Do not expose Juice Shop or DVWA directly to untrusted networks.
- Do not publish API tokens, passwords, MISP keys, or TLS private keys.
- The current reverse-proxy tests confirm TheHive, Cortex, and MISP
  application responses through the WAF frontend.
- The current evidence does not establish automatic open-appsec event
  forwarding to TheHive. Implement and test that workflow separately.
- TheHive-to-Cortex and TheHive-to-MISP integration links in the overall
  architecture are intended integration paths; verify each in its
  application's configuration and with a controlled test.

## 8. Validation checklist

- [ ] Client DNS or hosts-file entries resolve all three names to the WAF.
- [ ] TheHive login page is reachable through `thehive.lab.local`.
- [ ] Cortex login page is reachable through `cortex.lab.local`.
- [ ] MISP login page is reachable through `misp.lab.local`.
- [ ] open-appsec portal shows the expected asset and policy.
- [ ] A controlled request produces a matching detection event.
- [ ] Prevent-mode behavior is verified by an event with Prevent action
      and by confirming the request did not reach the backend.
- [ ] Any desired TheHive/Cortex/MISP integrations are tested end to end.
- [ ] Automatic WAF-event-to-TheHive case creation is tested separately,
      if that automation is part of the project scope.
