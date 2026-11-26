# TLS and Security Headers

## TLS settings that pass most audits (nginx 1.25+ with OpenSSL 1.1.1 or 3.x)
```
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;
```
This is the Mozilla "intermediate" profile. TLS 1.3 suites are not set with ssl_ciphers (OpenSSL handles them). If DHE suites stay, provide `ssl_dhparam` with at least 2048 bits or drop the DHE entries.

OCSP stapling (`ssl_stapling on; ssl_stapling_verify on;`) is optional; Let's Encrypt ended OCSP support in 2025, so do not add it for LE certificates.

HTTP/2: `http2 on;` inside the server on nginx 1.25.1+; older versions use `listen 443 ssl http2;`.

## HSTS rollout
1. Make sure every subdomain works over HTTPS.
2. Start short: `add_header Strict-Transport-Security "max-age=300" always;`
3. After a week without problems: `max-age=31536000; includeSubDomains`.
4. Only add `preload` and submit to hstspreload.org when you are sure; removal takes months.
HSTS on plain HTTP responses is ignored by browsers, so set it on the 443 server.

## Security headers
| Header | Typical value | Notes |
|---|---|---|
| X-Content-Type-Options | `nosniff` | Stops MIME sniffing of uploads |
| X-Frame-Options | `DENY` or `SAMEORIGIN` | Clickjacking; CSP `frame-ancestors` is the modern equivalent |
| Content-Security-Policy | `default-src 'self'` and more | App-specific; roll out with `Content-Security-Policy-Report-Only` |
| Referrer-Policy | `strict-origin-when-cross-origin` | Keeps paths and query strings out of other sites' logs |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` | Optional |
Add `always` so headers are also sent on error responses.

## The add_header inheritance rule
```
server {
    add_header X-Content-Type-Options nosniff always;   # A
    location / { }                                      # gets A
    location /api/ {
        add_header Cache-Control no-store;              # gets ONLY this one, A is gone
    }
}
```
A block inherits add_header from its parent only if it defines none itself. Keep shared headers in a snippet and include it in every block that adds its own. nginx 1.29.3 (October 2025) added `add_header_inherit merge;`, which makes nested blocks add to the inherited headers; check `nginx -v` before suggesting it (Debian 13 ships 1.26).

## Testing
```
sudo nginx -t && sudo systemctl reload nginx
curl -sI https://shop.example.com/ | grep -iE 'strict|x-content|x-frame|content-security|referrer|server:'
curl -sI http://shop.example.com/page?x=1        # expect 301 to https://shop.example.com/page?x=1
curl -s -o /dev/null -w '%{http_code}\n' https://shop.example.com/.git/config   # expect 403 or 404
curl -s -o /dev/null -w '%{http_code}\n' https://shop.example.com/images../      # expect 404 after the alias fix
openssl s_client -connect shop.example.com:443 -tls1_1 </dev/null   # expect a handshake failure
```
For a full external check: SSL Labs server test or `testssl.sh shop.example.com`.
