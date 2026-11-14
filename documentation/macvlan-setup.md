# macvlan Network Setup

The Compose template expects an **external** Docker network named `macvlan-lab`. It does not
create it. This guide shows how to create that network and the host-side shim interface from the
values recorded in [Docker Deployment](docker-deployment.md).

> **Status:** the commands below are derived from the recorded lab configuration. They were not
> re-run when this guide was written. Check every address against your own LAN before running them.

## 1. Recorded configuration

| Setting | Recorded value |
|---|---|
| Network name | `macvlan-lab` |
| Driver | `macvlan` |
| Subnet | `192.168.1.0/24` |
| Gateway | `192.168.1.99` |
| Parent interface | `ens18` |
| Host shim interface | `macvlan-host` |
| Host shim address | `192.168.1.119/24` |
| Addresses used by containers | `192.168.1.116` (NGINX), `192.168.1.117` (Juice Shop), `192.168.1.118` (DVWA) |

## 2. Before you start

- Confirm the parent interface name with `ip -br link`. The lab used `ens18`; yours may differ.
- Pick container addresses that are **outside your DHCP pool** and not used by another device,
  otherwise two machines will answer for the same address.
- The parent interface must be on the LAN the containers should join. On a virtual machine, the
  hypervisor network adapter may need to allow multiple MAC addresses (promiscuous mode in
  VirtualBox, equivalent settings elsewhere).

## 3. Create the Docker network

```bash
sudo docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.99 \
  -o parent=ens18 \
  macvlan-lab
```

Verify it:

```bash
sudo docker network ls
sudo docker network inspect macvlan-lab
```

## 4. Add the host shim (optional, for host-to-container access)

macvlan isolates containers from the Docker host: the host cannot reach `192.168.1.116` directly.
Other machines on the LAN can. A shim interface on the host removes that limitation.

```bash
sudo ip link add macvlan-host link ens18 type macvlan mode bridge
sudo ip addr add 192.168.1.119/24 dev macvlan-host
sudo ip link set macvlan-host up
```

Notes:

- These settings are **not persistent**. They disappear on reboot unless you add them to your
  network configuration (netplan, systemd-networkd or a boot-time unit).
- If the host loses LAN connectivity after adding the shim, use a `/32` address for the shim and
  add routes only for the container addresses instead of a `/24`:

  ```bash
  sudo ip addr add 192.168.1.119/32 dev macvlan-host
  sudo ip route add 192.168.1.116/30 dev macvlan-host
  ```

## 5. Confirm it works

From a **different machine** on the LAN, once the Compose stack is running:

```bash
curl -sS -D - -o /dev/null --resolve juice.lab.local:80:192.168.1.116 http://juice.lab.local/
```

From the Docker host (only if you created the shim):

```bash
ping -c 2 192.168.1.116
```

If something fails, see [Troubleshooting](troubleshooting.md).

## 6. Change the NGINX frontend address

`compose.yaml` reads the frontend address from `NGINX_IPV4_ADDRESS` (default `192.168.1.116`). Set
it in your local `.env` if your LAN uses a different free address. Update the upstream addresses in
`configurations/nginx/` to match your backends as well.
