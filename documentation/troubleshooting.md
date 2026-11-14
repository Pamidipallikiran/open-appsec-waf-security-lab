# Troubleshooting

Start with the symptom. Container names below (`appsec-agent`, `appsec-nginx`) are the ones used by
`compose.yaml`.

> Entries marked **(general)** are common Docker, NGINX or open-appsec behaviour and were not each
> reproduced in this lab. Entries marked **(recorded)** come from lab observations documented
> elsewhere in this repository.

## Quick checks

```bash
sudo docker ps
sudo docker exec appsec-nginx nginx -t
sudo docker logs --tail 50 appsec-agent
sudo docker logs --tail 50 appsec-nginx
```

## Compose and networking

| Symptom | Likely cause | What to check or do |
|---|---|---|
| `network macvlan-lab declared as external, but could not be found` **(general)** | The external network does not exist yet | Create it: see [macvlan Setup](macvlan-setup.md) |
| NGINX frontend unreachable from the Docker host but works from another machine **(general)** | macvlan isolates the host from its containers | Test from another LAN machine, or add the host shim from [macvlan Setup](macvlan-setup.md) |
| Container fails to start, address already in use **(general)** | `192.168.1.116` is held by another device or container | Pick a free address and set `NGINX_IPV4_ADDRESS` in `.env` |
| Compose warns that a variable is not set **(general)** | `.env` is missing or incomplete | `cp .env.example .env`, then fill in the agent token and e-mail |
| Agent does not register **(general)** | Missing or wrong `APPSEC_AGENT_TOKEN`, or no outbound access | `docker logs appsec-agent`; if a proxy is needed, set `APPSEC_HTTPS_PROXY` |
| Compose started next to an existing deployment and fails **(recorded)** | Duplicate container names, addresses or host resources | Do not run the template beside a running deployment; see [Docker Deployment](docker-deployment.md) |

## NGINX and upstreams

| Symptom | Likely cause | What to check or do |
|---|---|---|
| `nginx -t` fails with `cannot load certificate` **(general)** | The MISP example references `/etc/nginx/certs/misp.crt` and `misp.key`, which are not in the repository | Mount your certificate and key into the NGINX container, or do not enable the MISP example |
| `502 Bad Gateway` **(general)** | The upstream is down, unreachable, or the address is stale | Check the `proxy_pass` address. The SOAR VM moved from `192.168.1.114` to `192.168.1.121`; any old upstream address must be updated |
| `juice.lab.local` / `dvwa.lab.local` do not resolve **(general)** | The client has no hosts-file or DNS entry | Add `192.168.1.116 juice.lab.local dvwa.lab.local` to the client hosts file, or use `curl --resolve` |
| Unknown hostname lands on Juice Shop **(recorded)** | `map $host $backend` uses Juice Shop as the default | Expected behaviour of `default.conf` |
| Browser or `curl` warns about the MISP certificate **(recorded)** | The lab frontend certificate is self-signed | Use `curl -k` for lab checks only; replace the certificate for anything beyond the lab |
| MISP works but upstream TLS is not verified **(recorded)** | `proxy_ssl_verify off` is set as a lab workaround | Install a trusted certificate and set `proxy_ssl_verify on` before production use |

## WAF events and signatures

| Symptom | Likely cause | What to check or do |
|---|---|---|
| Request returns a normal page but there is no event **(recorded)** | An HTTP status code is not evidence of inspection or detection | Look for the event in the open-appsec portal; confirm the asset, policy and practice mode |
| Event exists but the request was not blocked **(recorded)** | The practice is in **Detect** mode | Detect reports without blocking; prevention needs Prevent mode and proof that the request never reached the backend |
| Event appears late **(recorded)** | Portal delay; its duration was not measured in this lab | Wait and refresh before concluding that nothing was logged |
| Custom signature never matches **(recorded)** | Missing `msg`, `flow:to_server,established` or `service:http`, or no HTTP context keyword before `content`/`pcre` | See [Custom Snort Rules](../detection/custom-snort-rules.md) |
| Only a built-in *Web Application* event appears **(recorded)** | A built-in protection matched; that is not a signature match | Check Practice SubType (*Web Snort*), Protection Name and Indicators Source |
| Signatures disappear after an upload **(recorded)** | The uploaded ruleset replaced the earlier one, or another asset shares the Snort practice | Re-upload the full rule file and re-enforce the policy |

## Static checks fail

Run `make validate`. Each message names the file and line. The most common ones:

- `compose.yaml uses ${VAR} but .env.example does not define it`: add the variable to `.env.example`.
- `single-quoted curl -w ... prints a literal \n`: use double quotes, for example `-w "HTTP %{http_code}\n"`.
- `anchor '#...' not found`: the heading text changed; update the link.
