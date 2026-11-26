# Nginx Hardening Checklist

Every code the script prints, why it matters and the fix. Severity is the default; raise or lower it with context.

## HIGH

### OLD_TLS_PROTOCOL
`ssl_protocols` lists SSLv3, TLSv1 or TLSv1.1. These are deprecated (RFC 8996), fail PCI DSS and allow downgrade attacks. Fix: `ssl_protocols TLSv1.2 TLSv1.3;` (the default since nginx 1.23.4, so deleting the line also works on new versions). Only very old clients (Android 4.3, IE on Windows 7 without updates) lose access.

### WEAK_CIPHERS
`ssl_ciphers` allows RC4, DES/3DES (SWEET32), MD5, NULL, EXPORT or anonymous (aNULL/ADH) suites. Entries starting with `!` or `-` are exclusions and are fine. Fix: use the Mozilla "intermediate" list from ssl-config.mozilla.org or remove `ssl_ciphers` to use the OpenSSL default, and set `ssl_prefer_server_ciphers off;` when only modern AEAD suites remain.

### NO_CERTIFICATE
A server listens with `ssl` but no `ssl_certificate` is set in it or in http. nginx refuses to start or fails the handshake. Add `ssl_certificate` (full chain) and `ssl_certificate_key`.

### ALIAS_TRAVERSAL (off-by-slash)
`location /images { alias /var/www/media/images/; }`: a request for `/images../secret.txt` maps to `/var/www/media/images/../secret.txt`, so files one level above the alias are readable (a well-known finding in many audits). Fix: both the location and the alias end with a slash, `location /images/ { alias /var/www/media/images/; }`, or use `root` when the path matches the folder name.

## MEDIUM

### HTTP_NO_REDIRECT
A port-80 server with the same server_name as an HTTPS server serves pages instead of redirecting. Users and cookies stay on plain HTTP. Fix:
```
server {
    listen 80;
    server_name shop.example.com;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}
```

### NO_HSTS
No `Strict-Transport-Security` header on an HTTPS server, so the first request of a session can be downgraded. See `tls-and-headers.md` for the rollout.

### ADD_HEADER_INHERITANCE
nginx inherits `add_header` from the parent level only when the current level has no `add_header` at all. One `add_header Cache-Control no-store;` in `location /api/` drops every security header from the server block for that location. Fix: repeat the headers in that location, or keep them in a snippet (`include snippets/security-headers.conf;`) and include it in every block that has its own add_header. On nginx 1.29.3+ `add_header_inherit merge;` in http makes child blocks add to the parent headers instead of replacing them. `proxy_set_header`, `fastcgi_param` and `proxy_hide_header` follow the same rule.

### AUTOINDEX_ON
Directory listing shows every file name, including backups and exports nobody linked. Turn it off or protect the location.

### ADMIN_OPEN
Paths such as /admin, /phpmyadmin, /actuator, /server-status, /nginx_status or /metrics without allow/deny, auth_basic or auth_request. Fix: `allow 10.20.0.0/16; deny all;` (office or VPN range), or `auth_request` to an SSO service. Basic auth only over HTTPS.

### UNLIMITED_BODY
`client_max_body_size 0` disables the request size limit, making disk and memory exhaustion easy. Keep the default 1m or a real limit in http, and raise it only in the upload location.

### URI_IN_REDIRECT
`$uri` is normalized and URL-decoded, so `%0d%0a` becomes a real line break and an attacker can inject headers (`Set-Cookie`) into the redirect response. Use `$request_uri` (the raw, still-encoded request line) in `return`, `rewrite` targets and `add_header`.

## LOW

### SERVER_TOKENS
The version appears in the `Server` header and on error pages, which helps attackers match known CVEs. `server_tokens off;` in http.

### MISSING_SECURITY_HEADERS
On HTTPS servers: `X-Content-Type-Options nosniff`, `X-Frame-Options` (or CSP `frame-ancestors`), `Content-Security-Policy`, `Referrer-Policy`. Add them with `always` so they are also sent on 4xx/5xx responses.

### SHORT_HSTS
HSTS max-age under 180 days. Fine during rollout; raise it to one year afterwards.

### DOTFILES_EXPOSED
The server serves files but has no rule for hidden files, so `/.git/config`, `/.env` or `/.htpasswd` may be downloadable if they exist under the web root. Fix: `location ~ /\.(?!well-known) { deny all; }` (keeps ACME challenges working).

### NO_RATE_LIMIT
A login, auth or token path without `limit_req`. Add a zone in http and apply it to the location; return 429 with `limit_req_status 429;`.

### PROXY_HEADERS
A `proxy_pass` location that does not send Host, X-Forwarded-For and X-Forwarded-Proto, so the app logs the proxy's IP, builds wrong redirect URLs and may think HTTPS requests are HTTP. Remember the inheritance rule: one `proxy_set_header` in the location replaces all inherited ones.

## INFO

### INCLUDE_NOT_FOLLOWED
The script reads only the files you pass. Ask for `nginx -T` or the included files.

## Check by hand (not automated)
- `proxy_pass https://...` to an upstream on the internet without `proxy_ssl_verify on;` and `proxy_ssl_trusted_certificate`.
- PHP: `location ~ \.php$` must use `try_files $uri =404;` (or `fastcgi_split_path_info` with a check) so uploaded images cannot run as PHP; uploads directories should never pass to PHP.
- `if` inside location with anything other than `return` or `rewrite ... last` ("if is evil").
- `default_server` blocks: an unknown Host should get `return 444;` with a self-signed or `ssl_reject_handshake on;` (1.19.4+) instead of the first site.
- Permissions: nginx workers should not be able to write the web root; private keys `chmod 600`, owned by root.
- Large headers / slow clients: `client_body_timeout`, `client_header_timeout`, `large_client_header_buffers` for public APIs under attack.
- Logging: access logs must not record tokens in query strings; use a custom log_format if needed.
