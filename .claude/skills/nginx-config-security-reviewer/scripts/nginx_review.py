#!/usr/bin/env python3
"""Nginx config security reviewer (Python 3 standard library only).

Parses nginx.conf / sites-available files into a block tree and flags common
security and hardening problems: old TLS protocols, weak ciphers, missing HSTS
and security headers, the add_header inheritance trap, alias off-by-slash path
traversal, autoindex, unlimited body size, $uri in redirects (CRLF injection),
plain-HTTP servers without a redirect, open admin paths, login paths without
rate limiting, exposed dotfiles and proxies without forwarding headers.

Usage:
  python3 nginx_review.py site.conf [more.conf ...] [--json]
  python3 nginx_review.py --self-test
Exit codes: 0 = no HIGH findings, 1 = HIGH findings, 2 = unreadable/unparseable input.
"""
import argparse, json, re, sys

SEV_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
OLD_PROTOCOLS = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}
WEAK_CIPHER_WORDS = ["RC4", "DES", "3DES", "MD5", "NULL", "EXPORT", "EXP-", "aNULL", "eNULL", "ADH", "AECDH"]
SECURITY_HEADERS = {
    "x-content-type-options": "X-Content-Type-Options nosniff",
    "x-frame-options": "X-Frame-Options DENY or SAMEORIGIN (or CSP frame-ancestors)",
    "content-security-policy": "Content-Security-Policy",
    "referrer-policy": "Referrer-Policy strict-origin-when-cross-origin",
}
LOGIN_RE = re.compile(r"login|signin|sign-in|auth|token|password|wp-login", re.I)
ADMIN_RE = re.compile(r"admin|phpmyadmin|actuator|server-status|nginx_status|/metrics|wp-admin", re.I)


class ParseError(Exception):
    pass


class Node:
    def __init__(self, name, args, line, children=None):
        self.name, self.args, self.line, self.children = name, args, line, children

    def get(self, name):
        return [c for c in (self.children or []) if c.name == name]

    def first(self, name):
        found = self.get(name)
        return found[0] if found else None

    def walk(self):
        for c in self.children or []:
            yield c
            if c.children is not None:
                yield from c.walk()


def tokenize(text):
    tokens, i, line, n = [], 0, 1, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1; i += 1
        elif ch.isspace():
            i += 1
        elif ch == "#":
            while i < n and text[i] != "\n":
                i += 1
        elif ch in "{};":
            tokens.append((ch, line, True)); i += 1
        elif ch in "\"'":
            q, j, buf = ch, i + 1, []
            while j < n and text[j] != q:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1]); j += 2; continue
                if text[j] == "\n":
                    line += 1
                buf.append(text[j]); j += 1
            if j >= n:
                raise ParseError(f"line {line}: unterminated quote")
            tokens.append(("".join(buf), line, False)); i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "{};":
                if text[j] == "$" and j + 1 < n and text[j + 1] == "{":  # ${var}
                    k = text.find("}", j)
                    j = k + 1 if k != -1 else n
                    continue
                j += 1
            tokens.append((text[i:j], line, False)); i = j
    return tokens


def parse(text):
    tokens = tokenize(text)
    root = Node("main", [], 0, [])
    stack, cur = [root], []
    for tok, line, special in tokens:
        if special and tok == ";":
            if not cur:
                continue
            stack[-1].children.append(Node(cur[0][0], [t for t, _ in cur[1:]], cur[0][1]))
            cur = []
        elif special and tok == "{":
            if not cur:
                raise ParseError(f"line {line}: '{{' without a directive name")
            node = Node(cur[0][0], [t for t, _ in cur[1:]], cur[0][1], [])
            stack[-1].children.append(node); stack.append(node); cur = []
        elif special and tok == "}":
            if cur:
                raise ParseError(f"line {line}: missing ';' before '}}'")
            if len(stack) == 1:
                raise ParseError(f"line {line}: unexpected '}}'")
            stack.pop()
        else:
            cur.append((tok, line))
    if cur:
        raise ParseError(f"line {cur[0][1]}: directive '{cur[0][0]}' not terminated with ';'")
    if len(stack) != 1:
        raise ParseError(f"block '{stack[-1].name}' opened on line {stack[-1].line} is not closed")
    return root


def headers_of(node):
    return {d.args[0].lower(): d for d in node.get("add_header") if d.args}


def is_tls(server):
    for l in server.get("listen"):
        if "ssl" in l.args or "quic" in l.args or any(a.endswith(":443") or a == "443" for a in l.args):
            return True
    s = server.first("ssl")
    return bool(s and s.args and s.args[0] == "on")


def listens_plain(server):
    ls = server.get("listen")
    if not ls:
        return True  # default listen *:80
    for l in ls:
        if not ("ssl" in l.args or "quic" in l.args or any(a.endswith(":443") or a == "443" for a in l.args)):
            return True
    return False


def names(server):
    out = []
    for d in server.get("server_name"):
        out.extend(d.args)
    return set(out) or {"_"}


def inherited(scopes, name):
    """Value of a directive as nginx inherits it: innermost scope that sets it."""
    for s in reversed(scopes):
        d = s.first(name)
        if d is not None:
            return d
    return None


def effective_headers(scopes):
    for s in reversed(scopes):
        h = headers_of(s)
        if h:
            return h
    return {}


def review(text, fname="nginx.conf"):
    root = parse(text)
    http = root.first("http")
    top = http if http is not None else root
    base = [root] + ([http] if http is not None else [])
    servers = [s for s in top.get("server")]
    findings = []

    def add(sev, code, line, msg, fix):
        findings.append({"severity": sev, "code": code, "file": fname, "line": line, "message": msg, "fix": fix})

    for d in root.walk():
        if d.name == "include":
            add("INFO", "INCLUDE_NOT_FOLLOWED", d.line, f"include {' '.join(d.args)} is not read by this checker",
                "Review the included files too (pass them as extra arguments) or paste `nginx -T` output.")

    tokens = [d for d in root.walk() if d.name == "server_tokens"]
    if not any(d.args and d.args[0] == "off" for d in tokens):
        add("LOW", "SERVER_TOKENS", (http or root).line, "server_tokens is not off, so error pages and the Server header show the nginx version",
            "Add `server_tokens off;` in the http block.")

    tls_names = set()
    for s in servers:
        if is_tls(s):
            tls_names |= names(s)

    for s in servers:
        scopes = base + [s]
        label = " ".join(sorted(names(s)))
        tls = is_tls(s)
        if tls:
            if inherited(scopes, "ssl_certificate") is None:
                add("HIGH", "NO_CERTIFICATE", s.line, f"TLS server {label} has no ssl_certificate in scope",
                    "Add ssl_certificate and ssl_certificate_key (fullchain + key).")
            proto = inherited(scopes, "ssl_protocols")
            if proto is not None:
                old = [p for p in proto.args if p in OLD_PROTOCOLS]
                if old:
                    add("HIGH", "OLD_TLS_PROTOCOL", proto.line, f"{label}: ssl_protocols enables {', '.join(old)}",
                        "Use `ssl_protocols TLSv1.2 TLSv1.3;` (SSLv3/TLS 1.0/1.1 are deprecated, RFC 8996).")
            ciph = inherited(scopes, "ssl_ciphers")
            if ciph is not None and ciph.args:
                parts = re.split(r"[:\s]+", " ".join(ciph.args))
                weak = sorted({w for p in parts if p and not p.startswith("!") and not p.startswith("-")
                               for w in WEAK_CIPHER_WORDS if w.lower() in p.lower()})
                if weak:
                    add("HIGH", "WEAK_CIPHERS", ciph.line, f"{label}: ssl_ciphers allows weak suites ({', '.join(weak)})",
                        "Use the Mozilla 'intermediate' cipher list, or remove ssl_ciphers to use the safe OpenSSL default.")
            hdrs = effective_headers(scopes)
            if "strict-transport-security" not in hdrs:
                add("MEDIUM", "NO_HSTS", s.line, f"TLS server {label} sends no Strict-Transport-Security header",
                    'Add `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;` (start with a short max-age).')
            else:
                hsts = hdrs["strict-transport-security"]
                m = re.search(r"max-age=(\d+)", " ".join(hsts.args), re.I)
                if m and int(m.group(1)) < 15552000:
                    add("LOW", "SHORT_HSTS", hsts.line, f"{label}: HSTS max-age {m.group(1)} is under 180 days",
                        "Raise max-age to 31536000 once HTTPS works everywhere.")
            missing = [v for k, v in SECURITY_HEADERS.items() if k not in hdrs]
            if "x-frame-options" not in hdrs and "content-security-policy" in hdrs and \
                    "frame-ancestors" in " ".join(hdrs["content-security-policy"].args):
                missing = [v for v in missing if not v.startswith("X-Frame")]
            if missing:
                add("LOW", "MISSING_SECURITY_HEADERS", s.line, f"{label}: missing {'; '.join(missing)}",
                    "Add them with `always` in the server block (check the inheritance rule for locations).")
        elif listens_plain(s) and names(s) & tls_names:
            redirects = any(r.args and r.args[0] in ("301", "302", "307", "308") and len(r.args) > 1 and r.args[1].startswith("https://")
                            for r in [d for d in s.walk() if d.name == "return"])
            rewrites = any(len(r.args) > 1 and r.args[1].startswith("https://") for r in [d for d in s.walk() if d.name == "rewrite"])
            if not (redirects or rewrites):
                add("MEDIUM", "HTTP_NO_REDIRECT", s.line, f"plain-HTTP server {label} serves content instead of redirecting to HTTPS",
                    "Use `return 301 https://$host$request_uri;` in the port-80 server (keep only /.well-known/acme-challenge/ if needed).")

        server_hdrs = effective_headers(scopes)
        has_dot_rule = False
        locations = [d for d in s.walk() if d.name == "location"]
        for loc in locations:
            path = loc.args[-1] if loc.args else ""
            mod = loc.args[0] if len(loc.args) > 1 else ""
            if mod in ("~", "~*") and (r"/\." in path or path.startswith(r"\.") or r"(^|/)\." in path):
                if loc.get("deny") or any(r.args and r.args[0] in ("403", "404") for r in loc.get("return")):
                    has_dot_rule = True
            own = headers_of(loc)
            hi = inherited(scopes + [loc], "add_header_inherit")
            merge = bool(hi and hi.args and hi.args[0] == "merge")  # nginx 1.29.3+
            if own and server_hdrs and not merge:
                lost = sorted(set(server_hdrs) - set(own))
                if lost:
                    add("MEDIUM", "ADD_HEADER_INHERITANCE", loc.line,
                        f"location {path} has its own add_header, so it silently drops {', '.join(lost)} set at server/http level",
                        "Repeat those headers in this location, include a shared headers snippet, or on nginx 1.29.3+ set `add_header_inherit merge;`.")
            al = loc.first("alias")
            if al and al.args and mod in ("", "^~") and not path.endswith("/") and al.args[0].endswith("/"):
                add("HIGH", "ALIAS_TRAVERSAL", al.line,
                    f"location {path} (no trailing slash) with alias {al.args[0]} (trailing slash) allows {path}../ path traversal",
                    f"Make both end with a slash: `location {path}/ {{ alias {al.args[0]}; }}`.")
            ai = loc.first("autoindex")
            if ai and ai.args and ai.args[0] == "on":
                add("MEDIUM", "AUTOINDEX_ON", ai.line, f"autoindex on in location {path} lists directory contents",
                    "Turn it off, or restrict the location with allow/deny or auth_basic.")
            if ADMIN_RE.search(path):
                guarded = loc.get("deny") or loc.get("auth_basic") or loc.get("auth_request") or loc.get("satisfy") \
                    or any(r.args and r.args[0] in ("403", "404", "444") for r in loc.get("return"))
                if not guarded:
                    add("MEDIUM", "ADMIN_OPEN", loc.line, f"location {path} looks like an admin/status endpoint with no allow/deny or auth",
                        "Add `allow <office/VPN range>; deny all;` or auth_basic/auth_request, or remove the route.")
            if LOGIN_RE.search(path) and not inherited(scopes + [loc], "limit_req"):
                add("LOW", "NO_RATE_LIMIT", loc.line, f"location {path} looks like a login/auth endpoint without limit_req",
                    "Define `limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;` in http and `limit_req zone=login burst=5 nodelay;` here.")
            if loc.first("proxy_pass"):
                ph = set()
                for sc in reversed(scopes + [loc]):  # like add_header: innermost level that sets any wins
                    if sc.get("proxy_set_header"):
                        ph = {d.args[0].lower() for d in sc.get("proxy_set_header") if d.args}
                        break
                miss = [h for h in ("host", "x-forwarded-for", "x-forwarded-proto") if h not in ph]
                if miss:
                    add("LOW", "PROXY_HEADERS", loc.line, f"location {path} proxies without {', '.join(miss)}",
                        "Set proxy_set_header Host $host; X-Forwarded-For $proxy_add_x_forwarded_for; X-Forwarded-Proto $scheme; (note: any proxy_set_header in a location replaces inherited ones).")
        serves_files = inherited(scopes, "root") or any(
            (l.first("root") or l.first("alias")) and not (l.args and l.args[-1].startswith("/.well-known/")) for l in locations)
        if serves_files and not has_dot_rule:
            add("LOW", "DOTFILES_EXPOSED", s.line, f"{label}: no rule blocks hidden files such as /.git/ or /.env",
                r"Add `location ~ /\.(?!well-known) { deny all; }`.")

    for d in root.walk():
        if d.name == "client_max_body_size" and d.args and d.args[0] in ("0", "0m", "0k"):
            add("MEDIUM", "UNLIMITED_BODY", d.line, "client_max_body_size 0 disables the request body limit",
                "Set a real limit (e.g. 10m, or larger only in the upload location).")
        if d.name in ("return", "rewrite", "add_header") and any(re.search(r"\$uri\b|\$document_uri\b", a) for a in d.args):
            add("MEDIUM", "URI_IN_REDIRECT", d.line, f"{d.name} uses $uri (decoded, may contain CR/LF), which allows header injection",
                "Use $request_uri (raw, still encoded) in redirects and headers.")
    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["line"]))
    return {"file": fname, "servers": [{"line": s.line, "names": sorted(names(s)), "tls": is_tls(s)} for s in servers],
            "findings": findings}


def to_markdown(results):
    out = ["# Nginx config security review", ""]
    allf = [f for r in results for f in r["findings"]]
    counts = {k: sum(1 for f in allf if f["severity"] == k) for k in SEV_ORDER}
    out.append("Findings: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    for r in results:
        out += ["", f"## {r['file']}", "", "| Server | Line | TLS |", "|---|---|---|"]
        for s in r["servers"]:
            out.append(f"| {' '.join(s['names'])} | {s['line']} | {'yes' if s['tls'] else 'no'} |")
        out += ["", "| Severity | Code | Line | Problem | Fix |", "|---|---|---|---|---|"]
        for f in r["findings"]:
            out.append(f"| {f['severity']} | {f['code']} | {f['line']} | {f['message']} | {f['fix']} |")
        if not r["findings"]:
            out.append("| - | - | - | no findings | - |")
    out += ["", "Always run `nginx -t` before reloading, and test with `curl -sI https://<host>/` afterwards."]
    return "\n".join(out)


def self_test():
    results = []

    def check(name, cond):
        results.append(cond)
        print(("PASS " if cond else "FAIL ") + name)

    def codes(conf):
        return [f["code"] for f in review(conf)["findings"]]

    good = """
    http {
      server_tokens off;
      limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
      server { listen 80; server_name a.test; return 301 https://$host$request_uri; }
      server {
        listen 443 ssl; http2 on; server_name a.test;
        ssl_certificate /c.pem; ssl_certificate_key /k.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Content-Type-Options nosniff always;
        add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'none'" always;
        add_header Referrer-Policy strict-origin-when-cross-origin always;
        root /srv/www;
        location ~ /\\.(?!well-known) { deny all; }
        location /static/ { alias /srv/static/; }
        location /login { limit_req zone=login burst=5 nodelay; proxy_pass http://app;
          proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme; }
      }
    }"""
    check("clean config has no findings", codes(good) == [])
    check("comments and quotes parsed", parse('a "b c;" d; # x;\n e f;').children[0].args == ["b c;", "d"])
    check("${var} token kept", parse("set $x ${host}a;").children[0].args == ["$x", "${host}a"])
    for bad, msg in [("server { listen 80;", "unclosed block"), ("a b", "missing ;"), ("}", "stray brace"), ('a "b;', "unterminated quote")]:
        try:
            parse(bad); check("parse error: " + msg, False)
        except ParseError:
            check("parse error: " + msg, True)
    check("SERVER_TOKENS when missing", "SERVER_TOKENS" in codes("http { server { listen 80; } }"))
    tls = "server { listen 443 ssl; server_name b.test; ssl_certificate /c; %s }"
    check("OLD_TLS_PROTOCOL", "OLD_TLS_PROTOCOL" in codes(tls % "ssl_protocols TLSv1 TLSv1.2;"))
    check("TLSv1.2 alone fine", "OLD_TLS_PROTOCOL" not in codes(tls % "ssl_protocols TLSv1.2;"))
    check("WEAK_CIPHERS", "WEAK_CIPHERS" in codes(tls % "ssl_ciphers 'HIGH:RC4-SHA:DES-CBC3-SHA';"))
    check("excluded !RC4 is fine", "WEAK_CIPHERS" not in codes(tls % "ssl_ciphers 'HIGH:!aNULL:!MD5:!RC4';"))
    check("NO_CERTIFICATE", "NO_CERTIFICATE" in codes("server { listen 443 ssl; }"))
    check("cert inherited from http", "NO_CERTIFICATE" not in codes("http { ssl_certificate /c; server { listen 443 ssl; } }"))
    check("NO_HSTS", "NO_HSTS" in codes(tls % ""))
    check("SHORT_HSTS", "SHORT_HSTS" in codes(tls % 'add_header Strict-Transport-Security "max-age=300";'))
    check("MISSING_SECURITY_HEADERS", "MISSING_SECURITY_HEADERS" in codes(tls % ""))
    inh = tls % 'add_header Strict-Transport-Security "max-age=31536000"; location /api/ { add_header Cache-Control no-store; }'
    r = review(inh)["findings"]
    check("ADD_HEADER_INHERITANCE names lost header",
          any(f["code"] == "ADD_HEADER_INHERITANCE" and "strict-transport-security" in f["message"] for f in r))
    check("headers inherited when location has none", "ADD_HEADER_INHERITANCE" not in codes(
        tls % 'add_header Strict-Transport-Security "max-age=31536000"; location /api/ { proxy_pass http://x; }'))
    check("add_header_inherit merge respected", "ADD_HEADER_INHERITANCE" not in codes(
        tls % 'add_header_inherit merge; add_header Strict-Transport-Security "max-age=31536000"; location /api/ { add_header Cache-Control no-store; }'))
    check("ALIAS_TRAVERSAL", "ALIAS_TRAVERSAL" in codes("server { location /img { alias /srv/img/; } }"))
    check("alias with matching slashes fine", "ALIAS_TRAVERSAL" not in codes("server { location /img/ { alias /srv/img/; } }"))
    check("regex location alias not flagged", "ALIAS_TRAVERSAL" not in codes(r"server { location ~ ^/img/(.*)$ { alias /srv/img/$1; } }"))
    check("AUTOINDEX_ON", "AUTOINDEX_ON" in codes("server { location /files/ { autoindex on; } }"))
    check("HTTP_NO_REDIRECT", "HTTP_NO_REDIRECT" in codes(
        "server { listen 80; server_name c.test; root /x; } server { listen 443 ssl; server_name c.test; ssl_certificate /c; }"))
    check("no HTTP_NO_REDIRECT for unrelated name", "HTTP_NO_REDIRECT" not in codes(
        "server { listen 80; server_name d.test; } server { listen 443 ssl; server_name c.test; ssl_certificate /c; }"))
    check("ADMIN_OPEN", "ADMIN_OPEN" in codes("server { location /admin/ { proxy_pass http://x; } }"))
    check("admin with deny fine", "ADMIN_OPEN" not in codes("server { location /admin/ { allow 10.0.0.0/8; deny all; } }"))
    check("NO_RATE_LIMIT", "NO_RATE_LIMIT" in codes("server { location /api/login { proxy_pass http://x; } }"))
    check("rate limit inherited from server", "NO_RATE_LIMIT" not in codes(
        "server { limit_req zone=z; location /api/login { proxy_pass http://x; } }"))
    check("PROXY_HEADERS", "PROXY_HEADERS" in codes("server { location / { proxy_pass http://x; } }"))
    check("proxy_set_header in location replaces inherited", "PROXY_HEADERS" in codes(
        "server { proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; "
        "proxy_set_header X-Forwarded-Proto $scheme; location / { proxy_set_header Upgrade $http_upgrade; proxy_pass http://x; } }"))
    check("DOTFILES_EXPOSED", "DOTFILES_EXPOSED" in codes("server { root /srv; }"))
    check("ACME-only port 80 server not flagged for dotfiles", "DOTFILES_EXPOSED" not in codes(
        "server { listen 80; location /.well-known/acme-challenge/ { root /var/www/certbot; } location / { return 301 https://$host$request_uri; } }"))
    check("UNLIMITED_BODY", "UNLIMITED_BODY" in codes("http { client_max_body_size 0; }"))
    check("URI_IN_REDIRECT", "URI_IN_REDIRECT" in codes("server { return 301 https://$host$uri; }"))
    check("$request_uri fine", "URI_IN_REDIRECT" not in codes("server { return 301 https://$host$request_uri; }"))
    check("INCLUDE_NOT_FOLLOWED", "INCLUDE_NOT_FOLLOWED" in codes("http { include /etc/nginx/conf.d/*.conf; }"))
    check("findings sorted HIGH first", review("server { listen 443 ssl; location /files/ { autoindex on; } }")["findings"][0]["severity"] == "HIGH")
    passed = sum(results)
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


def main():
    ap = argparse.ArgumentParser(description="Nginx config security reviewer")
    ap.add_argument("files", nargs="*", help="nginx config files (nginx.conf, sites-available/*, or `nginx -T` output)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.files:
        ap.error("give at least one config file, or --self-test")
    results = []
    for f in a.files:
        try:
            with open(f, encoding="utf-8") as fh:
                results.append(review(fh.read(), f))
        except (OSError, UnicodeDecodeError, ParseError) as e:
            print(f"error: {f}: {e}", file=sys.stderr)
            return 2
    print(json.dumps(results, indent=2) if a.json else to_markdown(results))
    return 1 if any(f["severity"] == "HIGH" for r in results for f in r["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())