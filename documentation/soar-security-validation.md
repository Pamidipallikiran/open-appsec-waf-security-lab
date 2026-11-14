# SOAR Services — WAF Security Validation

## 1. Objective

Validate normal application connectivity and perform controlled XSS test requests against TheHive, Cortex, and MISP through the IP-based open-appsec NGINX frontend.

## 2. Lab endpoints

| Component | Client-facing URL | Upstream |
|---|---|---|
| open-appsec + NGINX | `192.168.1.116` | WAF frontend |
| TheHive | `http://192.168.1.116:9000/` | `192.168.1.121:9000` |
| Cortex | `http://192.168.1.116:9001/` | `192.168.1.121:9001` |
| MISP | `https://192.168.1.116/` | `192.168.1.121:443` |

## 3. Normal traffic validation

Commands used:

```bash
curl -sS -o /dev/null -w "TheHive: HTTP %{http_code}\\n" http://192.168.1.116:9000/
curl -sS -o /dev/null -w "Cortex: HTTP %{http_code}\\n" http://192.168.1.116:9001/
curl -k -sS -o /dev/null -w "MISP: HTTP %{http_code}\\n" https://192.168.1.116/
```

Observed on 2026-11-14:

| Service | Observed response | Result |
|---|---:|---|
| TheHive | HTTP 200 | Application reachable |
| Cortex | HTTP 303 | Application reachable; redirect response |
| MISP | HTTP 302 | Application reachable; redirect to login |

The MISP `-k` option skips certificate verification and is used only for this lab's current certificate.

## 4. Controlled XSS detection tests

The following URL-encoded query-string test was sent separately to each frontend:

```bash
# TheHive
curl -sS -G -o /dev/null -w "TheHive XSS: HTTP %{http_code}\\n" \
  --data-urlencode 'q=<script>alert(1)</script>' \
  http://192.168.1.116:9000/

# Cortex
curl -sS -G -o /dev/null -w "Cortex XSS: HTTP %{http_code}\\n" \
  --data-urlencode 'q=<script>alert(1)</script>' \
  http://192.168.1.116:9001/

# MISP
curl -k -sS -G -o /dev/null -w "MISP XSS: HTTP %{http_code}\\n" \
  --data-urlencode 'q=<script>alert(1)</script>' \
  https://192.168.1.116/
```

Observed application responses on 2026-11-14:

| Service | XSS-test response |
|---|---:|
| TheHive | HTTP 200 |
| Cortex | HTTP 303 |
| MISP | HTTP 302 |

The user subsequently confirmed that the open-appsec portal displayed Cross Site Scripting detections for all three services. A portal screenshot from the same test period showed Critical Cross Site Scripting events, with Security Action **Detect**. The user confirmed that the detections covered TheHive, Cortex and MISP.

**Result: XSS detection confirmed for all three SOAR frontends in Detect mode.** These observations do not establish that the requests were blocked. The application HTTP responses remained their normal response codes, which is consistent with Detect-mode operation.

## 5. Event display latency

The user reported that the matching events appeared in the portal, but appeared with a delay. No exact end-to-end delay was measured, and the available evidence does not identify whether the delay is in agent event generation, event delivery, portal processing, or portal refresh.

A separate timing check on 2026-11-14 recorded a TheHive XSS request completing in approximately 0.0354 seconds (35.4 ms). This measures the HTTP request duration only; it does **not** measure WAF event generation or portal display latency.

## 6. Evidence and limitations

- TheHive, Cortex and MISP IP-based frontends returned their expected application responses.
- Controlled XSS query-string requests were sent to all three frontends.
- Matching Cross Site Scripting events were observed in the open-appsec portal for all three services.
- The portal action shown was **Detect**; prevention is not claimed.
- Event appearance was reported as delayed, but no measured portal latency is available.
- HTTP response codes alone do not prove detection or prevention; the portal event is the detection evidence.

## 7. Conclusion

On 2026-11-14, normal connectivity to TheHive, Cortex and MISP through the IP-based open-appsec NGINX frontend was validated. Controlled XSS tests against all three services produced matching Cross Site Scripting detections in the open-appsec portal with Security Action **Detect**.

The tests confirm detection, not blocking or prevention. Event display was reported as delayed; its exact duration and cause remain unmeasured.

## 8. Test environment

- Frontend: open-appsec with NGINX
- Frontend IP: `192.168.1.116`
- SOAR backend IP: `192.168.1.121`
- Test date: 14 November 2026
- Security action observed: Detect
