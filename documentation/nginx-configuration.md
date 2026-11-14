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

## 4. IP-based SOAR listeners

The extended lab publishes applications on the separate SOAR VM (`192.168.1.121`) through dedicated WAF NGINX listeners:

| Client URL | NGINX listener | Upstream |
|---|---:|---|
| `http://192.168.1.116:9000/` | TCP 9000 | `http://192.168.1.121:9000` (TheHive) |
| `http://192.168.1.116:9001/` | TCP 9001 | `http://192.168.1.121:9001` (Cortex) |
| `https://192.168.1.116/` | TLS 443 | `https://192.168.1.121:443` (MISP) |

The active live configuration uses these IP-based listeners. Juice Shop and DVWA continue to use hostname routing on `192.168.1.116:80`.

The reference configurations are stored under `configurations/nginx/optional/`. They are not automatically loaded by the core NGINX configuration. Review certificate paths and upstream settings before enabling them. The MISP example disables upstream TLS verification as a lab workaround; configure a trusted CA and enable verification before production use.

The live frontend returned HTTP 200 for TheHive, HTTP 303 for Cortex, and HTTP 302 for MISP during checks on 2026-11-14. These responses confirm reachability only.

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

## 7. IP-based SOAR connectivity checks

Run from a client that can reach the WAF frontend:

```bash
curl -sS -o /dev/null -w 'TheHive HTTP: %{http_code}\\n' http://192.168.1.116:9000/
curl -sS -o /dev/null -w 'Cortex HTTP: %{http_code}\\n' http://192.168.1.116:9001/
curl -k -sS -o /dev/null -w 'MISP HTTP: %{http_code}\\n' https://192.168.1.116/
```

Observed on 2026-11-14: TheHive HTTP 200, Cortex HTTP 303, MISP HTTP 302. Redirects are valid application responses. The `-k` option is for the current lab certificate only.

## 8. Configuration Validation and Test Results

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

## 9. open-appsec Inspection and Security Considerations

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


### SOAR XSS detection evidence (2026-11-14)

Controlled URL-encoded XSS test requests were submitted to the IP-based TheHive, Cortex and MISP frontend URLs. Matching Cross Site Scripting events were observed in the open-appsec portal for all three services. The portal showed the Security Action as **Detect**. This supports a detection result for these tests; it does not demonstrate blocking or prevention. The events appeared after a delay, but end-to-end event latency was not measured. HTTP response codes remained the applications’ normal responses (TheHive 200, Cortex 303, MISP 302), which is consistent with Detect-mode testing.
