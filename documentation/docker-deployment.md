# Docker Deployment Architecture

## 1. Overview

The lab uses Docker containers to deploy open-appsec, its NGINX attachment, and two vulnerable web applications.

The recorded environment contains four running containers. The repository Compose template defines only the two core open-appsec services. The vulnerable applications are deployed independently.
## 2. Running Containers

| Container | Docker Image | Purpose |
|---|---|---|
| appsec-agent | ghcr.io/openappsec/agent:latest | WAF security engine |
| appsec-nginx | ghcr.io/openappsec/nginx-attachment:latest | NGINX integration and WAF frontend |
| juice-shop | bkimminich/juice-shop | Vulnerable web application backend |
| dvwa | vulnerables/web-dvwa | Vulnerable web application backend |

The recorded frontend and backend addresses are:

| Component | Address |
|---|---|
| WAF host | 192.168.1.113 |
| NGINX frontend | 192.168.1.116:80 |
| Juice Shop backend | 192.168.1.117:3000 |
| DVWA backend | 192.168.1.118:80 |
| Host macvlan shim | 192.168.1.119 |

## 3. Docker Network Architecture

### Agent network

The appsec-agent container is connected to the Docker network:

- Network: `open-appsec-lab_default`
- Container address recorded during inspection: `172.18.0.2`

### Application network

The following containers are connected to `macvlan-lab`:

- appsec-nginx
- juice-shop
- dvwa

| Setting | Recorded value |
|---|---|
| Network driver | macvlan |
| Subnet | 192.168.1.0/24 |
| Gateway | 192.168.1.99 |
| Parent interface | ens18 |
| Host shim interface | macvlan-host@ens18 |
| Host shim address | 192.168.1.119/24 |

The agent and NGINX attachment use host IPC and a shared memory mount for their observed integration configuration. They do not need to share the same Docker network.

## 4. Container Communication Configuration

Both `appsec-agent` and `appsec-nginx` use the following integration settings:

- IPC mode: `host`
- Shared memory mount: `/dev/shm/check-point`

These settings support communication between the open-appsec agent and NGINX attachment. Their presence alone does not prove that traffic is being inspected or blocked.

## 5. Persistent Volume Mounts

### appsec-agent

| Container path | Purpose |
|---|---|
| /etc/cp/conf | Agent configuration |
| /etc/cp/data | Agent data |
| /var/log/nano_agent | Agent logs |
| /ext/appsec | Local configuration |
| /dev/shm/check-point | Shared memory integration |

### appsec-nginx

| Container path | Purpose |
|---|---|
| /etc/nginx/conf.d | NGINX configuration |
| /dev/shm/check-point | Shared memory integration |

The paths above describe the recorded container configuration. Confirm actual host-side bind sources with `docker inspect` before attempting to back up or migrate persistent data.

## 6. Repository Compose Template

The repository `compose.yaml` defines only these two services:

- `appsec-agent`
- `appsec-nginx`

It expects:

- An existing external Docker network named `macvlan-lab`.
- The frontend address `192.168.1.116` to be available.
- Host directories configured through environment variables.
- Agent registration details supplied through a local `.env` file.

The template does not deploy Juice Shop, DVWA, TheHive, Cortex, or MISP. Those services are managed separately in this lab.

Optional SmartSync, shared storage, tuning, and PostgreSQL services are not included in the core template.

Do not start this template alongside an existing deployment using the same container names, network addresses, or host resources. Review the Compose configuration before deployment.

## 7. Hostname-Based Traffic Flow

The NGINX frontend routes requests according to the HTTP hostname:

| Hostname | Frontend | Backend |
|---|---|---|
| `juice.lab.local` | 192.168.1.116:80 | 192.168.1.117:3000 |
| `dvwa.lab.local` | 192.168.1.116:80 | 192.168.1.118:80 |

Both hostnames must resolve to `192.168.1.116` on the client machine. The NGINX configuration selects the corresponding backend using the request hostname.

The optional SOAR reverse-proxy hostnames are:

| Hostname | Backend service |
|---|---|
| `thehive.lab.local` | 192.168.1.114:9000 |
| `cortex.lab.local` | 192.168.1.114:9001 |
| `misp.lab.local` | 192.168.1.114:443 (HTTPS) |

These SOAR routes are optional examples and do not mean that the SOAR services are deployed by this repository Compose template.

## 8. Security Considerations

- Never publish agent tokens or environment credentials.
- Do not commit runtime data, generated certificates, or sensitive configuration.
- Use trusted and maintained container images.
- Restrict direct access to vulnerable application backends.
- Verify that application traffic traverses the intended WAF inspection path.
- Detection and prevention depend on the active open-appsec security policy.
- An HTTP response code confirms application reachability, not WAF detection or prevention.

The optional MISP reverse-proxy example uses disabled upstream TLS verification as a lab workaround. Do not use that setting in production; configure and validate the backend certificate instead.

## 9. Verification Commands

List running containers:

```bash
sudo docker ps
```

Inspect Docker networks:

```bash
sudo docker network ls
sudo docker network inspect macvlan-lab
```

Inspect container network and IPC settings:

```bash
sudo docker inspect appsec-agent
sudo docker inspect appsec-nginx
```

Validate the NGINX configuration:

```bash
sudo docker exec appsec-nginx nginx -t
```

Inspect the active NGINX configuration:

```bash
sudo docker exec appsec-nginx nginx -T
```

Validate the repository Compose template without starting containers:

```bash
sudo docker compose --env-file .env.example -f compose.yaml config --quiet
```

The Compose validation command checks configuration only. It does not start services.
