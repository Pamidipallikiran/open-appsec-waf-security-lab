# NGINX Reverse Proxy Configuration

## 1. Overview

NGINX is the client-facing reverse proxy on the WAF VM. The open-appsec
NGINX attachment integrates request processing with the local open-appsec
agent. NGINX routes permitted requests to the relevant backend.

The extended deployment also uses name-based virtual hosts for TheHive,
Cortex, and MISP, which remain on a separate SOAR VM. See
[SOAR Reverse-Proxy Integration](soar-integration.md).

## 2. Core web-application routing

The repository's reproducible core example uses a local-address map:

| Frontend IP | Backend application | Backend address | Current runtime note |
|---|---|---|---|
| 192.168.1.116 | OWASP Juice Shop | 192.168.1.117:3000 | Active NGINX frontend |
| 192.168.1.220 | DVWA | 192.168.1.118:80 | Mapping exists; .220 is not attached to the current active NGINX container |

The map directive selects the upstream based on the local IP address
that received the request:

```nginx
map $server_addr $backend {
    192.168.1.116 192.168.1.117:3000;
    192.168.1.220 192.168.1.118:80;
}
```

The server block in
[`configurations/nginx/default.conf`](../configurations/nginx/default.conf)
uses the selected upstream:

```nginx
server {
    listen 80 default_server;
    server_name _;

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

For example, a request received on `192.168.1.116` is routed to
`192.168.1.117:3000`. The DVWA mapping is usable only when the
`192.168.1.220` frontend is actually assigned to an active NGINX
instance.

## 3. SOAR virtual hosts

The deployed WAF VM also has separate virtual hosts for the SOAR
applications. They route by hostname rather than by the core
`$server_addr` backend map:

| Hostname | Upstream |
|---|---|
| `thehive.lab.local` | `http://192.168.1.114:9000` |
| `cortex.lab.local` | `http://192.168.1.114:9001` |
| `misp.lab.local` | `https://192.168.1.114:443` |

The live configuration is maintained on the WAF VM under
`/home/kiranwaf/open-appsec-lab/nginx-config/`. The repository does not
currently include a byte-for-byte copy of every live virtual-host file;
the core `default.conf` is a reproducible Juice Shop / DVWA example.
Refer to [SOAR Reverse-Proxy Integration](soar-integration.md) for
routing behavior, DNS entries, connectivity checks, and TLS notes.

The SOAR VM's current IP is `192.168.1.114`. Do not use the old
`192.168.1.112` address.

## 4. Important NGINX directives

- `map`: Selects a backend based on the frontend IP address.
- `proxy_pass`: Forwards requests to the selected backend.
- `proxy_http_version`: Sets the HTTP version used upstream.
- `proxy_set_header`: Passes client and request information upstream.
- `X-Real-IP`: Passes the original client IP address.
- `X-Forwarded-For`: Maintains the forwarded client IP chain.
- `X-Forwarded-Proto`: Passes the original request protocol.

The SOAR virtual hosts additionally preserve the Host header and
forwarded host information, support WebSocket/HTTP upgrade headers where
needed, and use an extended read timeout for long-running requests.

## 5. Configuration validation

Inspect the configuration loaded by the running NGINX container:

```bash
sudo docker exec appsec-nginx nginx -t
sudo docker exec appsec-nginx nginx -T
```

A successful syntax test proves that NGINX accepts the configuration;
it does not prove that a backend is reachable or that open-appsec
blocked a malicious request.

## 6. WAF verification

To establish that a request was inspected and acted on:

1. Send a controlled test request through the WAF frontend.
2. Find the matching event in the open-appsec portal or authoritative
   event log.
3. Check the Practice SubType, Protection Name, and Security Action.
4. For a prevention claim, verify the action is **Prevent** and confirm
   the request did not reach the backend.

Historical custom Snort tests for Juice Shop and DVWA are documented in
[Custom Snort Rules](../detection/custom-snort-rules.md). The current
runtime's event-level verdict should be rechecked before reporting
detection or prevention as verified.

## 7. Security considerations

- Restrict direct access to backend applications so clients cannot
  bypass the intended WAF path.
- Keep SOAR backend ports restricted to the WAF VM and trusted
  administrators.
- Use trusted TLS certificates and enable upstream certificate
  verification. The current MISP lab proxy disables upstream TLS
  verification because of its self-signed/expired certificate; this is
  not a production configuration.
- Do not commit secrets, API keys, agent tokens, or private keys.
- Reverse-proxy connectivity alone is not evidence of WAF inspection,
  detection, or prevention.
