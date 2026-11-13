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
| 1000001 | SQL injection in the `q` parameter | Juice Shop | Historically verified: detection and blocking reported |
| 1000030 | `Referer:` header contains `<svg` | DVWA | Historically verified: Web Snort event, Prevent |
| 1000031 | `Referer:` header contains `onload` | DVWA | Historically verified: Web Snort event, Prevent |
| 1000032 | `Referer:` header contains `<svg` and `onload` (case-insensitive) | DVWA | Under investigation |

**Evidence note:** The historical signature results above are not fresh detection tests from 13 November 2026. On that date, the lab checks verified hostname-based routing and backend reachability through the shared frontend at `192.168.1.116`. Those HTTP checks do not independently prove that a custom Snort signature matched or blocked a request.

## 3. Test requests

```bash
# 1000030 / 1000031 (DVWA frontend)
curl -i -H 'Referer: <svg onload=alert(1)>' http://dvwa.lab.local/

# 1000001 (Juice Shop frontend), request shaped to match the rule's pcre
curl -i 'http://juice.lab.local/rest/products/search?q=%27+OR+1%3D1--'
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

The bisection signatures SIDs 1000041-1000044 are currently commented out
in `rules/lab-rules.rules`; they are not active protections. Enable only
the specific diagnostic rule being tested, upload the updated ruleset,
and enforce the applicable policy before sending its request.

Use harmless tokens so the built-in XSS engine cannot interfere. Test
one rule at a time so a Prevent action on one rule does not hide the
results of another.

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: aaa1 bbb1' http://dvwa.lab.local/   # 1000041
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: AAA2'      http://dvwa.lab.local/   # 1000042
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: AAA3 BBB3' http://dvwa.lab.local/   # 1000043
curl -s -o /dev/null -w '%{http_code}\n' -H 'Referer: AAA4 BBB4' http://dvwa.lab.local/   # 1000044
```

The following outcomes are diagnostic clues, not guaranteed conclusions. Confirm each result by checking the Web Snort event fields, the active uploaded ruleset, and the policy applied to the DVWA asset.

| Observed result | Possible interpretation to investigate |
|---|---|
| No event for any | The file is not active; fix deployment first |
| 1000041 matches, 1000042/43 do not | `nocase` is not honored; match case variants instead |
| 1000043 matches, 1000044 does not | `http_header:field` unsupported; use plain `http_header` |
| All match | Syntax is fine; the original issue was ruleset state |

Re-run the Juice Shop test after any upload to confirm the working
signature is unaffected.
