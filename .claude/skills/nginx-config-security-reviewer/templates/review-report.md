# Nginx security review: <site or server name>

**Version:** <nginx 1.26.3, OpenSSL 3.x>   **Role:** <static site / reverse proxy to Node on :3000 / PHP-FPM>
**Files reviewed:** <nginx -T output, 2 files>   **TLS terminated by:** <nginx / CDN / load balancer>
**Summary:** <one sentence: the most serious problem and what the fix changes>

## Findings
| # | Severity | Code | File:line | Problem | Fix |
|---|---|---|---|---|---|
| 1 | HIGH | <ALIAS_TRAVERSAL> | <nginx.conf:51> | <location /images allows /images../> | <location /images/ { alias .../images/; }> |
| 2 | <MEDIUM> | <...> | <...> | <...> | <...> |

## Not changed (with reason)
- <ADMIN_OPEN on /admin/: already limited by the cloud firewall to the VPN; added deny all anyway? yes/no>

## Config changes
```diff
- ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
+ ssl_protocols TLSv1.2 TLSv1.3;
```

## Apply and test
1. Back up: `sudo cp -a /etc/nginx /etc/nginx.bak-<date>`
2. Edit, then `sudo nginx -t && sudo systemctl reload nginx`
3. Checks:
   - `curl -sI https://<host>/` shows the security headers
   - `curl -sI http://<host>/x?y=1` returns 301 to the same path on https
   - <path traversal / dotfile / admin checks from the findings>
4. Roll back: restore the backup and reload.

## Follow-ups
- <HSTS: raise max-age to 31536000 after <date>>
- <CSP: move from Report-Only to enforcing after reviewing reports>
