# Custom Snort Rules with open-appsec

This guide documents the custom Snort 3 signatures used in the lab, how
they were tested, and how to confirm that a signature (not a built-in
detection) produced an event.

Rules file: [`rules/lab-rules.rules`](rules/lab-rules.rules)

## 1. Requirements for open-appsec signatures

open-appsec's signature guide requires these keywords for a rule to be
enforced: `msg` (shown as the Protection Name), `flow:to_server,established`
and `service:http`. A context keyword such as `http_header`,
`http_raw_uri`, `http_uri` or `http_client_body` must come before
`content` or `pcre`.

Reference: [open-appsec - Write Snort Signatures](https://docs.openappsec.io/snot-rules/write-snort-signatures)

## 2. Signature status

| SID | Purpose | Asset | Status |
|---|---|---|---|
| 1000001 | SQL injection in the `q` parameter | Juice Shop | Verified: detects and blocks |
| 1000030 | `Referer:` header contains `<svg` | DVWA | Verified: Web Snort event, Prevent |
| 1000031 | `Referer:` header contains `onload` | DVWA | Verified: Web Snort event, Prevent |
| 1000032 | `Referer:` header contains `<svg` and `onload` (case-insensitive) | DVWA | Under investigation |

## 3. Test requests

```bash
# 1000030 / 1000031 (DVWA frontend)
curl -i -H 'Referer: <svg onload=alert(1)>' http://192.168.1.220/

# 1000001 (Juice Shop frontend), request shaped to match the rule's pcre
curl -i 'http://192.168.1.116/rest/products/search?q=%27+OR+1%3D1--'
```

## 4. How to confirm a signature matched

| Check | Custom signature matched | Not a signature match |
|---|---|---|
| Practice SubType | **Web Snort** | Web Application |
| Protection Name | The rule's `msg` text | Built-in incident type, e.g. *Cross Site Scripting* |
| Indicators Source | The uploaded rules file | Not present |
| Security Action | Prevent (if the Snort sub-practice is in Prevent) | May show Detect |
| HTTP response | Block page when prevented | Backend response (e.g. `302`) |

A built-in *Web Application* event on the same payload is **not**
evidence that a custom signature matched.

## 5. Open issue: combined signature 1000032

The combined rule produced only a built-in Web Application XSS event
(action Detect, backend returned `302`), with no Web Snort event.
Because 1000030 and 1000031 each work, the combined rule is not yet
explained. Candidate causes, in order of what to rule out first:

1. The uploaded ruleset in force is not the one expected (rules
   replaced, not added; policy not re-enforced).
2. The Snort practice is shared between assets, so an upload replaced
   rules used elsewhere.
3. The importer or engine handles `nocase` or multiple `content`
   options differently from standard Snort 3 (not documented in the
   signature guide).

### Controlled bisection (non-XSS tokens, DVWA only)

Use harmless tokens so the built-in XSS engine cannot interfere, one
token per rule so a Prevent on one does not hide the others
(see `rules/lab-rules.rules`, SIDs 1000041-1000044).

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: aaa1 bbb1' http://192.168.1.220/   # 1000041
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: AAA2'      http://192.168.1.220/   # 1000042
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: AAA3 BBB3' http://192.168.1.220/   # 1000043
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: AAA4 BBB4' http://192.168.1.220/   # 1000044
```

| Result | Interpretation |
|---|---|
| No event for any | The file is not active; fix deployment first |
| 1000041 matches, 1000042/43 do not | `nocase` is not honored; match case variants instead |
| 1000043 matches, 1000044 does not | `http_header:field` unsupported; use plain `http_header` |
| All match | Syntax is fine; the original issue was ruleset state |

Re-run the Juice Shop test after any upload to confirm the working
signature is unaffected.
