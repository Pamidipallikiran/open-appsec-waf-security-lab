# Docker Deployment Architecture

## 1. Overview

The lab uses Docker containers to deploy open-appsec, NGINX,
and vulnerable web applications.

The observed lab environment consists of four running containers.
The repository's Docker Compose template defines only the two
core open-appsec services.

## 2. Running Containers

| Container | Docker Image | Purpose |
|---|---|---|
| appsec-agent | ghcr.io/openappsec/agent:latest | WAF security engine |
| appsec-nginx | ghcr.io/openappsec/nginx-attachment:latest | NGINX integration |
| juice-shop | bkimminich/juice-shop | Vulnerable web application |
| dvwa | vulnerables/web-dvwa | Vulnerable web application |

## 3. Docker Network Architecture

### Agent network

The appsec-agent container is connected to:

- Network: open-appsec-lab_default

### Application network

The following containers are connected to macvlan-lab:

- appsec-nginx
- juice-shop
- dvwa

Network configuration:

| Setting | Value |
|---|---|
| Network driver | macvlan |
| Subnet | 192.168.1.0/24 |
| Gateway | 192.168.1.99 |
| Parent interface | ens18 |

The agent and NGINX attachment are not required to share
the same Docker network. Their observed integration configuration
uses host IPC and a shared memory mount.

## 4. Container Communication Configuration

Both appsec-agent and appsec-nginx use:

- IPC mode: host
- Shared memory mount: /dev/shm/check-point

This shared mount is part of the open-appsec integration
configuration.

These settings describe the observed deployment and do not
independently prove successful WAF inspection.

## 5. Persistent Volume Mounts

### appsec-agent

| Container path | Purpose |
|---|---|
| /etc/cp/conf | Agent configuration |
| /etc/cp/data | Agent data |
| /var/log/nano_agent | Agent logs |
| /ext/appsec | Local configuration |
| /dev/shm/check-point | Shared memory mount |

### appsec-nginx

| Container path | Purpose |
|---|---|
| /etc/nginx/conf.d | NGINX configuration |
| /dev/shm/check-point | Shared memory mount |

## 6. Repository Compose Template

The repository's compose.yaml defines:

- appsec-agent
- appsec-nginx

It expects:

- An existing external Docker network named macvlan-lab.
- An available static IP address of 192.168.1.116.
- Host directories configured through environment variables.
- Agent registration details supplied through a local .env file.

The template does not deploy the Juice Shop or DVWA containers.
These applications are deployed independently in the observed lab.

Optional upstream services such as SmartSync, shared storage,
tuning, and PostgreSQL are not included in this core template.

Do not run the template alongside an existing deployment
that uses the same container names or static IP addresses.

## 7. Setup Steps

Reference commands for rebuilding the lab. Adjust the parent interface,
subnet, gateway and addresses to your host.

1. Create the macvlan network used by all lab containers:

       sudo docker network create -d macvlan \
         --subnet=192.168.1.0/24 --gateway=192.168.1.99 \
         -o parent=ens18 macvlan-lab

2. Start the backend applications on fixed addresses:

       sudo docker run -d --name juice-shop --network macvlan-lab \
         --ip 192.168.1.117 --restart unless-stopped bkimminich/juice-shop
       sudo docker run -d --name dvwa --network macvlan-lab \
         --ip 192.168.1.118 --restart unless-stopped vulnerables/web-dvwa

3. Create the local environment file and add your own agent token:

       cp .env.example .env

4. Validate and start the open-appsec services:

       sudo docker compose --env-file .env config --quiet
       sudo docker compose up -d

Note: a macvlan parent host cannot reach its own macvlan containers
directly. Test from another machine on the 192.168.1.0/24 network.

## 8. Security Considerations

- Never publish agent tokens or environment credentials.
- Do not commit runtime data or sensitive configuration.
- Use trusted and maintained container images.
- Restrict direct access to backend applications.
- Verify that application traffic traverses the WAF inspection path.
- Detection and prevention depend on the active security policy.

## 9. Verification Commands

List running containers:

    sudo docker ps

Inspect Docker networks:

    sudo docker network ls

Inspect the agent IPC configuration:

    sudo docker inspect appsec-agent

Inspect the NGINX configuration:

    sudo docker exec appsec-nginx nginx -T

Validate the repository Compose template without starting containers:

    sudo docker compose --env-file .env.example -f compose.yaml config --quiet
