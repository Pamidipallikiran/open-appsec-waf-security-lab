# Changelog

All notable changes to this repository are recorded here.

## Unreleased

### Added

- `scripts/validate_repo.py`: dependency-free checks for Compose variables, Snort signatures,
  NGINX examples, Markdown links and anchors, and secret patterns.
- `scripts/check-nginx.sh`: `nginx -t` for the example configurations in a throwaway container.
- `Makefile` with `validate`, `compose-config` and `nginx-test` targets.
- GitHub Actions workflow `validate.yml` running the three checks above.
- `documentation/macvlan-setup.md`: creating the `macvlan-lab` network and the host shim.
- `documentation/troubleshooting.md`: symptoms, causes and checks for the common failures.
- `SECURITY.md`, `CONTRIBUTING.md`, a pull request template, `.editorconfig` and `.gitattributes`.
- README: contents list, CI badge, validation section and roadmap of untested items.

### Changed

- `compose.yaml` reads the NGINX frontend address from `NGINX_IPV4_ADDRESS` (default unchanged:
  `192.168.1.116`); the variable is documented in `.env.example`.
- `documentation/docker-deployment.md`: replaced the outdated SOAR hostnames and the stale
  `192.168.1.114:9000` note with the current IP-based listeners.
- README repository tree and documentation table now list every file.

### Fixed

- Six `curl -w '...\\n'` examples printed a literal `\n`; they now use double quotes.
- Removed a personal home-directory path from `documentation/soar-integration.md`.
