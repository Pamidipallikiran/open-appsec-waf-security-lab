# Security Policy

## Scope

This repository documents an isolated lab. OWASP Juice Shop and DVWA are **intentionally
vulnerable**; their vulnerabilities are part of the lab and are not security issues in this
repository.

## What to report

- Secrets, tokens, keys or credentials committed to the repository or its history
- Configuration that weakens a protection without a clear "lab only" warning
- Documentation that claims a security result (detection, prevention, integration) that the recorded
  evidence does not support

## How to report

Use GitHub private reporting: open the repository's **Security** tab and choose **Report a
vulnerability**. Do not post secrets or exploit details in a public issue. If private reporting is
not available, open an issue that says only that you have a security report, without details, and a
private channel will be arranged.

## If you find a leaked secret

Revoke or rotate it first (for example, regenerate the open-appsec agent token in the portal), then
report it. Removing a secret from the latest commit does not remove it from history.

## Safe use

- Run the lab on an isolated network and test only systems you own or are authorized to test.
- Keep `.env`, certificates, private keys and agent state out of Git (they are in `.gitignore`).
- Do not expose the vulnerable applications or the SOAR ports to untrusted networks.
