# NGINX Reverse Proxy Configuration

## 1. Overview

NGINX acts as a reverse proxy between clients and backend
web applications.

It receives incoming HTTP requests and forwards them to the
appropriate backend based on the local IP address that received
the request.

NGINX is integrated with open-appsec to provide an application
security inspection layer for both frontends.

## 2. Frontend and Backend Architecture

The frontend IP addresses are used by clients to access
the applications. The backend IP addresses identify the
servers hosting the applications.

| Frontend IP | Backend Application | Backend Address |
|---|---|---|
| 192.168.1.116 | OWASP Juice Shop | 192.168.1.117:3000 |
| 192.168.1.220 | DVWA | 192.168.1.118:80 |

## 3. Backend Selection

The NGINX `map` directive uses `$server_addr` to identify
the local IP address that received the request.

Configuration:

```nginx
map $server_addr $backend {
    192.168.1.116 192.168.1.117:3000;
    192.168.1.220 192.168.1.118:80;
}
```

Complete server block (`configurations/nginx/default.conf`):

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

For example:

1. A client accesses 192.168.1.116.
2. NGINX receives the request on that frontend address.
3. The map directive selects 192.168.1.117:3000.
4. The request is forwarded to the Juice Shop backend.

The same routing logic sends requests received on
192.168.1.220 to the DVWA backend at 192.168.1.118:80.

## 4. Important NGINX Directives

- `map`: Selects a backend based on the frontend IP.
- `proxy_pass`: Forwards requests to the selected backend.
- `proxy_http_version`: Sets the HTTP version used upstream.
- `proxy_set_header`: Passes client and request information
  to the backend.
- `X-Real-IP`: Passes the original client IP address.
- `X-Forwarded-For`: Maintains the forwarded client IP chain.
- `X-Forwarded-Proto`: Passes the original request protocol.

## 5. Configuration Validation

The active configuration was inspected inside the running
NGINX container using:

    sudo docker exec appsec-nginx nginx -T

The loaded configuration matched the repository's
NGINX configuration file.

## 6. Security Considerations

Both frontends pass through the open-appsec inspection path:

- 192.168.1.116 (Juice Shop): a custom Snort signature detects and
  blocks a matching SQL injection request.
- 192.168.1.220 (DVWA): custom diagnostic signatures produced Web Snort
  events with action Prevent.

See [Custom Snort Rules](../detection/custom-snort-rules.md) for the
evidence and test method.

Requests are inspected and potentially blocked only when
they traverse an active open-appsec inspection path with
an appropriate security policy.

NGINX reverse proxy functionality alone does not prove
that a request has been detected or blocked by the WAF.
