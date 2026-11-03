# open-appsec WAF Security Lab

A practical Web Application Firewall (WAF) security lab integrating
open-appsec with NGINX to inspect HTTP traffic before it reaches
backend web applications.

## Project Overview

This project demonstrates how a Web Application Firewall can act as
a security layer between clients and backend applications.

The lab uses OWASP Juice Shop and Damn Vulnerable Web Application
(DVWA) to explore reverse proxy architecture, HTTP traffic inspection,
web application security, and attack detection and prevention.

The Juice Shop frontend is integrated with open-appsec and NGINX.
The additional DVWA frontend uses NGINX reverse proxy routing; its
open-appsec inspection path has not yet been independently verified.

## Technologies Used

- open-appsec - Web Application Firewall
- NGINX - Reverse proxy and traffic routing
- Docker - Containerized lab environment
- OWASP Juice Shop - Vulnerable web application
- DVWA - Damn Vulnerable Web Application
- Linux - Lab host operating system

## Lab Architecture

| Component | IP Address | Port |
|---|---|---|
| open-appsec + NGINX frontend | 192.168.1.116 | 80 |
| Additional NGINX frontend | 192.168.1.220 | 80 |
| OWASP Juice Shop backend | 192.168.1.117 | 3000 |
| DVWA backend | 192.168.1.118 | 80 |

See [Network Architecture](architecture/architecture.md) for the
network diagram, traffic flow, and network configuration.

## Documentation

- [Network Architecture](architecture/architecture.md)
- [NGINX Configuration](documentation/nginx-configuration.md)
- [Docker Deployment](documentation/docker-deployment.md)

## Project Objectives

- Deploy open-appsec with NGINX.
- Understand reverse proxy architecture.
- Inspect HTTP requests through the configured WAF integration.
- Explore web application attack detection and prevention.
- Understand WAF security policies.
- Study the importance of restricting direct backend access.
- Document the lab architecture and deployment process.

## Repository Structure

```text
open-appsec-waf-security-lab/
├── architecture/
│   └── architecture.md
├── configurations/
│   └── nginx/
│       └── default.conf
├── documentation/
│   ├── docker-deployment.md
│   └── nginx-configuration.md
├── .env.example
├── .gitignore
├── compose.yaml
└── README.md
