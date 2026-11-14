# SOAR Services — WAF Security Validation

## 1. Objective

Validate normal application connectivity and perform controlled XSS test requests against TheHive, Cortex, and MISP through the open-appsec-protected NGINX frontend.

## 2. Lab endpoints

| Component | Frontend |
|---|---|
| open-appsec + NGINX | `192.168.1.116` |
| TheHive | `thehive.lab.local` |
| Cortex | `cortex.lab.local` |
| MISP | `misp.lab.local` |

## 3. Normal traffic validation

| Service | Observed response | Result |
|---|---|---|
| TheHive | HTTP 200 | Application reachable |
| Cortex | HTTP 303, followed by HTTP 200 | Application reachable |
| MISP | HTTP 302 redirect to `/users/login` | Application reachable |

The MISP redirect is expected for an unauthenticated request.

## 4. Controlled XSS test

A GET request containing the URL-encoded string `<script>alert(1)</script>` in the `waf_test` query parameter was sent to each service through the WAF frontend.

| Service | Observed response | Matching event in searched open-appsec logs |
|---|---|---|
| TheHive | HTTP 200 | Not found |
| Cortex | HTTP 303 | Not found |
| MISP | HTTP 302 | Not found |

These response codes are application responses and do not establish whether the WAF detected or prevented the test payload.

## 5. Evidence and limitations

- The three application frontends returned their expected baseline responses.
- The XSS test requests returned HTTP responses rather than an observed WAF block response.
- Searches of `/home/kiranwaf/open-appsec-lab/appsec-logs/` for `waf_test`, `alert(1)`, and the respective service hostnames returned no matching entries.
- Detection and prevention are therefore **not confirmed** by the evidence collected so far.
- An empty log search does not prove that inspection did not occur. Additional request-level inspection evidence is required before making that claim.

## 6. Conclusion

Normal connectivity to TheHive, Cortex, and MISP through the open-appsec NGINX frontend was validated.

Controlled XSS test requests were submitted to all three services. No matching request-level detection or prevention events were found in the logs searched. The security verdict remains inconclusive and should not be reported as a successful block or detection.

## 7. Test environment

- Frontend: open-appsec with NGINX
- Frontend IP: `192.168.1.116`
- Test date: 14 November 2026
