# NGINX Reverse Proxy Configuration

## 1. Overview

NGINX acts as the reverse proxy for the vulnerable web applications. It receives HTTP requests through the open-appsec NGINX frontend and selects the backend using the HTTP hostname.

The repository configuration is maintained at `configurations/nginx/default.conf`.

## 2. Frontend and Backend Architecture

Both applications share one NGINX frontend address. NGINX distinguishes them using the HTTP Host header.

| Hostname | Frontend address | Backend application | Backend address |
|---|---|---|---|
| `juice.lab.local` | 192.168.1.116:80 | OWASP Juice Shop | 192.168.1.117:3000 |
| `dvwa.lab.local` | 192.168.1.116:80 | DVWA | 192.168.1.118:80 |

The client must resolve both hostnames to `192.168.1.116`. The frontend does not require a separate IP address for each application.

## 3. Backend Selection

The NGINX `map` directive evaluates `$host` and assigns the corresponding backend to `$backend`.

The repository configuration is:

```nginx
# Route vulnerable applications by hostname through the open-appsec NGINX frontend.

map $host $backend {
    default         192.168.1.117:3000;
    juice.lab.local 192.168.1.117:3000;
    dvwa.lab.local  192.168.1.118:80;
}

server {
    listen 80 default_server;
    server_name juice.lab.local dvwa.lab.local _;

    location / {
        proxy_pass http://$backend;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The default mapping sends unmatched hostnames to Juice Shop. The explicit hostname entries route Juice Shop and DVWA to their respective backends.

## 4. SOAR Virtual Hosts

The extended lab deployment also uses NGINX virtual hosts to provide access to applications running on the separate SOAR VM (`192.168.1.121`).

| Hostname | Upstream |
|---|---|
| `thehive.lab.local` | `http://192.168.1.121:9000` |
| `cortex.lab.local` | `http://192.168.1.121:9001` |
| `misp.lab.local` | `https://192.168.1.121:443` |

### Direct TheHive IP-based access

The optional TheHive/Cortex configuration also includes a dedicated
NGINX listener on port `9000` for IP-based access:

| Client URL (current frontend) | NGINX upstream |
|---|---|
| `http://192.168.1.116:9000` | `http://192.168.1.121:9000` |

The frontend address `.116` is the currently configured WAF NGINX
container address. The SOAR backend is `.121`. The planned frontend
address `.114` has not yet been deployed or verified.

This listener provides reverse-proxy reachability. Confirm open-appsec
inspection and prevention separately through the security event logs.

These are optional reverse-proxy examples stored under `configurations/nginx/optional/`. They are not automatically loaded by the core NGINX configuration. Review and configure the required certificates and hostname resolution before enabling them.

The MISP example disables upstream TLS certificate verification as a lab workaround for its current certificate. Enable proper certificate verification before production use.

Reverse-proxy connectivity does not prove that WAF events are automatically forwarded to TheHive or that TheHive, Cortex and MISP integrations are operational. Configure and validate those application-level integrations separately. See [SOAR Integration](soar-integration.md).

## 5. Important NGINX Directives

- `map $host $backend`: Selects the upstream backend using the requested hostname.
- `default`: Defines the backend used when no explicit hostname mapping matches.
- `proxy_pass`: Forwards the request to the selected backend.
- `proxy_http_version`: Sets the HTTP version for upstream communication.
- `proxy_set_header Upgrade`: Passes the WebSocket upgrade header.
- `proxy_set_header Connection`: Passes the connection upgrade directive.
- `Host`: Preserves the requested hostname for the backend.
- `X-Real-IP`: Passes the original client IP address.
- `X-Forwarded-For`: Maintains the forwarded client IP chain.
- `X-Forwarded-Proto`: Passes the original request protocol.

## 6. Request Flow

### OWASP Juice Shop

1. The client requests `http://juice.lab.local`.
2. DNS or the client hosts file resolves the hostname to `192.168.1.116`.
3. The NGINX frontend receives the HTTP request.
4. The `$host` map selects `192.168.1.117:3000`.
5. NGINX forwards the request to the Juice Shop backend.

### DVWA

1. The client requests `http://dvwa.lab.local`.
2. DNS or the client hosts file resolves the hostname to `192.168.1.116`.
3. The NGINX frontend receives the HTTP request.
4. The `$host` map selects `192.168.1.118:80`.
5. NGINX forwards the request to the DVWA backend.

## 7. Configuration Validation and Test Results

The following checks were performed against the running lab deployment on 2026-11-13:

| Test | Result | What it confirms |
|---|---|---|
| `nginx -t` inside `appsec-nginx` | Successful | NGINX configuration syntax is valid |
| `juice.lab.local` through frontend `192.168.1.116` | HTTP 200 | Juice Shop routing and reachability |
| `dvwa.lab.local` through frontend `192.168.1.116` | HTTP 302 to `login.php` | DVWA routing and reachability |

Example hostname-routing tests:

```bash
curl --resolve juice.lab.local:80:192.168.1.116 http://juice.lab.local/
curl --resolve dvwa.lab.local:80:192.168.1.116 http://dvwa.lab.local/
```

Inspect the loaded NGINX configuration:

```bash
sudo docker exec appsec-nginx nginx -t
sudo docker exec appsec-nginx nginx -T
```

The HTTP responses establish routing and backend reachability. They do not independently establish that open-appsec detected or prevented an attack.

## 8. open-appsec Inspection and Security Considerations

The NGINX frontend is integrated with the open-appsec agent. Actual inspection and prevention depend on the active agent integration, security policy, and traffic path.

Previously recorded lab observations include:

- Juice Shop: a custom SQL injection signature (SID 1000001) was previously reported to detect and block a matching request.
- DVWA: diagnostic custom signatures (SIDs 1000030 and 1000031) previously produced Web Snort events with the Security Action recorded as Prevent.

These are historical observations. They are not presented as fresh detection tests from 2026-11-13.

For evidence, inspect the open-appsec event details, including Practice SubType, Protection Name, Indicators Source, and Security Action. An HTTP status code alone is not proof of a signature match or prevention.

To verify a new WAF test:

1. Send a controlled test request through the WAF frontend.
2. Find the matching event in the open-appsec portal or authoritative agent event log.
3. Inspect the Practice SubType, Protection Name, Indicators Source, and Security Action.
4. Claim prevention only when the event records **Prevent** and the request is confirmed to have been blocked before reaching the backend.

See [Custom Snort Rules](../detection/custom-snort-rules.md) for signature details and the recorded test methodology.

Restrict direct access to backend application ports where practical, so clients use the intended WAF frontend. Do not expose vulnerable applications to untrusted networks.
