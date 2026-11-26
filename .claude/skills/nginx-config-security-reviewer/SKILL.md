---
name: nginx-config-security-reviewer
description: Reviews nginx.conf and site configs for security problems such as TLS 1.0/1.1, weak ciphers, missing HSTS and security headers, the add_header inheritance trap, alias off-by-slash path traversal, autoindex, unlimited body size, $uri in redirects, HTTP without an HTTPS redirect, open admin paths and logins without rate limits. Gives a fixed config. Includes a stdlib Python checker with --self-test.
---

# Nginx Config Security Reviewer

You review nginx configurations the way a careful ops engineer would before a security audit: find the settings that expose data or weaken TLS, explain each one in plain words, and hand back a corrected config that still serves the same routes. You never guess at files you have not seen, and you never tell the user to reload without `nginx -t`.

## Files in this skill

- `scripts/nginx_review.py` - parses nginx config files into blocks and prints findings with severity, line and fix (Python 3 standard library only)
- `references/hardening-checklist.md` - every check the script runs, why it matters and the fix, plus items to check by hand
- `references/tls-and-headers.md` - TLS protocol and cipher settings, HSTS rollout, security headers and how add_header inheritance works
- `templates/review-report.md` - the report you hand back: summary, findings table, config diff, test commands
- `examples/shop-site.conf` - a small shop config from 2019 with 18 findings (3 HIGH)
- `examples/shop-site-fixed.conf` - the same site after the fixes (no findings apart from the include note)

## Workflow

### 1. Collect the full config
Ask for the output of `sudo nginx -T` (it prints the main file and every included file), or for nginx.conf plus the relevant sites-enabled files. Ask what the site does (static, reverse proxy, PHP), which paths must stay public, the nginx version (`nginx -v`) and whether a CDN or load balancer terminates TLS in front of it. Tell the user to remove private keys or secrets before pasting; certificate paths are fine.

### 2. Run the checker
```
python3 scripts/nginx_review.py examples/shop-site.conf
python3 scripts/nginx_review.py /etc/nginx/nginx.conf /etc/nginx/sites-enabled/shop --json
python3 scripts/nginx_review.py --self-test
```
Exit code 1 means HIGH findings, 2 means the file could not be read or parsed (the error names the line).

### 3. Confirm and add manual checks
Read each finding against the user's context: a CDN in front changes TLS findings, an internal-only admin route may already be firewalled, a `return 404` may already hide a path. Then go through the manual items in `references/hardening-checklist.md` (included files, upstream TLS verification, `if` blocks, PHP handlers, file permissions). Drop false positives and say why.

### 4. Deliver
Fill `templates/review-report.md`: HIGH items first, a minimal diff of the config, and the test steps. Explain the add_header inheritance rule whenever ADD_HEADER_INHERITANCE appears, because it surprises most people. Introduce HSTS with a short max-age first if the site has never used it.

## Example result
For `examples/shop-site.conf`: 3 HIGH (TLS 1.0/1.1 enabled, RC4 and 3DES ciphers, `location /images` with `alias .../images/` allowing `/images../` traversal), 6 MEDIUM (unlimited body size, port 80 serving content instead of redirecting, autoindex on /downloads/, /api/ dropping HSTS and nosniff because it sets its own add_header, unprotected /admin/, `$uri` in a redirect), 8 LOW (server_tokens, dotfiles, missing CSP/Referrer-Policy/X-Frame-Options, proxy headers, no rate limit on /api/auth/login) and 1 INFO. `examples/shop-site-fixed.conf` shows the fixes and passes `nginx -t`.

## Rules

- Quote the exact line and the exact replacement; keep changes minimal and route-preserving.
- Always end with `sudo nginx -t && sudo systemctl reload nginx` and a curl check; never suggest a restart that drops connections when a reload works.
- Do not invent directives: check names against the nginx docs for the user's version (for example `http2 on;` needs 1.25.1+, older versions use `listen 443 ssl http2;`).
- Never ask for or repeat private keys, passwords or htpasswd hashes.
- Treat security headers like CSP as a rollout: suggest `Content-Security-Policy-Report-Only` first for complex apps.
