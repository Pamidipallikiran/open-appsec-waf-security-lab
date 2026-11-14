#!/usr/bin/env python3
"""Static consistency checks for this repository (standard library only).

Checks
  * compose.yaml / .env.example - every ${VAR} used by Compose is documented,
                                  secret-like variables hold placeholders only
  * Snort rules                 - header shape, msg/flow/service/sid/rev present,
                                  context keyword before content/pcre, unique SIDs
  * NGINX examples              - balanced braces, ';' terminators, and a "lab"
                                  comment next to any 'proxy_ssl_verify off'
  * Markdown                    - balanced code fences, relative links and
                                  #anchors resolve, curl -w '...\\n' pitfall,
                                  personal /home/<user>/ paths
  * Secret patterns             - private keys, common token formats

These checks show the repository is internally consistent. They do NOT show that
open-appsec detects or blocks anything; that needs an event in the open-appsec
portal. They also do not replace `docker compose config` or `nginx -t`
(see `make compose-config` and `make nginx-test`).

Usage:  python3 scripts/validate_repo.py [--root PATH]
Exit status is 0 when there are no errors (warnings are allowed), 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def tracked_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            yield path


# --------------------------------------------------------------------------- #
# Compose and environment file
# --------------------------------------------------------------------------- #
VAR_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")
SECRET_KEY = re.compile(r"(TOKEN|PASSWORD|SECRET|API_?KEY)", re.I)
PLACEHOLDER = re.compile(r"^(YOUR_|your-|<|changeme)", re.I)


def check_env(root: Path) -> None:
    compose, env = root / "compose.yaml", root / ".env.example"
    if not compose.exists() or not env.exists():
        err("compose.yaml and .env.example must both exist")
        return

    defined: set[str] = set()
    for n, line in enumerate(env.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            err(f".env.example:{n}: expected KEY=value")
            continue
        key, _, value = stripped.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        defined.add(key)
        if SECRET_KEY.search(key) and value and not PLACEHOLDER.match(value):
            err(f".env.example:{n}: {key} looks like a real secret; commit a placeholder such as YOUR_{key}")

    for var in sorted(set(VAR_REF.findall(compose.read_text(encoding="utf-8"))) - defined):
        err(f"compose.yaml uses ${{{var}}} but .env.example does not define it")


# --------------------------------------------------------------------------- #
# Snort rules
# --------------------------------------------------------------------------- #
CONTEXT_KEYWORDS = {
    "http_header", "http_raw_header", "http_raw_uri", "http_uri", "http_client_body",
    "http_method", "http_cookie", "http_raw_cookie", "http_stat_code", "http_stat_msg",
}


def split_options(body: str, where: str) -> list[str]:
    options, current, in_quotes, escaped = [], [], False, False
    for ch in body:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            current.append(ch)
            escaped = True
        elif ch == '"':
            current.append(ch)
            in_quotes = not in_quotes
        elif ch == ";" and not in_quotes:
            options.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        options.append(tail)
        err(f"{where}: option '{tail[:40]}' is not terminated with ';'")
    if in_quotes:
        err(f"{where}: unbalanced double quote")
    return [o for o in options if o]


def check_snort(root: Path) -> None:
    rules_dir = root / "detection" / "rules"
    files = sorted(rules_dir.glob("*.rules")) if rules_dir.is_dir() else []
    if not files:
        warn("no Snort rule files found under detection/rules/")
    seen: dict[int, tuple[str, bool]] = {}

    for path in files:
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            commented = line.startswith("#alert") or line.startswith("# alert")
            if commented:
                line = line.lstrip("#").strip()
            elif not line or line.startswith("#"):
                continue
            where = f"{path.name}:{lineno}"
            report = warn if commented else err  # diagnostic rules are advisory only

            if "(" not in line or not line.endswith(")"):
                report(f"{where}: rule must end with an option block closed by ')'")
                continue
            header, _, rest = line.partition("(")
            tokens = re.findall(r"\[[^\]]*\]|\S+", header)
            if len(tokens) != 7 or tokens[4] not in {"->", "<>"}:
                report(f"{where}: header must be 'action proto src sport -> dst dport'")

            opts: list[tuple[str, str]] = []
            for opt in split_options(rest[:-1], where):
                key, _, value = opt.partition(":")
                opts.append((key.strip(), value.strip()))
            keys = {k: v for k, v in reversed(opts)}

            for required in ("msg", "flow", "service", "sid", "rev"):
                if required not in keys:
                    report(f"{where}: missing '{required}' (required for open-appsec signatures)")
            flow = keys.get("flow", "").replace(" ", "")
            if flow and not ("to_server" in flow and "established" in flow):
                report(f"{where}: flow should be 'to_server,established'")
            if keys.get("service") and "http" not in keys["service"]:
                report(f"{where}: service should be 'http'")

            context_seen = False
            for key, _value in opts:
                if key in CONTEXT_KEYWORDS:
                    context_seen = True
                elif key in {"content", "pcre"} and not context_seen:
                    report(f"{where}: '{key}' appears before an HTTP context keyword (e.g. http_header)")
                    break

            sid_text = keys.get("sid", "")
            if sid_text.isdigit():
                sid = int(sid_text)
                if sid in seen:
                    (warn if commented or seen[sid][1] else err)(f"{where}: duplicate SID {sid}")
                seen[sid] = (where, commented)
            elif sid_text:
                report(f"{where}: sid must be numeric")


# --------------------------------------------------------------------------- #
# NGINX examples
# --------------------------------------------------------------------------- #
def strip_nginx_comment(line: str) -> str:
    in_quote = ""
    for i, ch in enumerate(line):
        if in_quote:
            if ch == in_quote:
                in_quote = ""
        elif ch in "\"'":
            in_quote = ch
        elif ch == "#":
            return line[:i]
    return line


def check_nginx(root: Path) -> None:
    base = root / "configurations" / "nginx"
    if not base.is_dir():
        warn("configurations/nginx/ not found")
        return
    for path in sorted(p for p in base.rglob("*") if p.is_file() and ".conf" in p.name):
        raw_lines = path.read_text(encoding="utf-8").splitlines()
        depth = 0
        for n, raw in enumerate(raw_lines, 1):
            code = strip_nginx_comment(raw).strip()
            if not code:
                continue
            where = f"{path.relative_to(root).as_posix()}:{n}"
            depth += code.count("{") - code.count("}")
            if depth < 0:
                err(f"{where}: unmatched '}}'")
                depth = 0
            if not code.endswith((";", "{", "}")):
                err(f"{where}: directive should end with ';'")
            if re.match(r"proxy_ssl_verify\s+off\s*;", code):
                context = " ".join(raw_lines[max(0, n - 4):n - 1]).lower()
                if "lab" not in context or "#" not in context:
                    err(f"{where}: 'proxy_ssl_verify off' needs a nearby comment marking it lab-only")
        if depth != 0:
            err(f"{path.relative_to(root).as_posix()}: unbalanced braces (depth {depth} at end of file)")


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #
FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CURL_PITFALL = re.compile(r"-w\s+'[^']*\\\\n")
HOME_PATH = re.compile(r"/home/[A-Za-z0-9._-]+/")


def slugify(heading: str) -> str:
    text = heading.replace("`", "").lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors_of(lines: list[str]) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        match = None if in_fence else HEADING.match(line)
        if match:
            slug = slugify(match.group(2))
            counts[slug] = counts.get(slug, -1) + 1
            anchors.add(slug if counts[slug] == 0 else f"{slug}-{counts[slug]}")
    return anchors


def check_markdown(root: Path) -> None:
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.relative_to(root).parts:
            continue
        name = path.relative_to(root).as_posix()
        lines = (read(path) or "").splitlines()

        if sum(1 for line in lines if FENCE.match(line)) % 2:
            err(f"{name}: unbalanced ``` code fence")

        anchors = anchors_of(lines)
        in_fence = False
        for n, line in enumerate(lines, 1):
            if FENCE.match(line):
                in_fence = not in_fence
            if in_fence or FENCE.match(line):
                if CURL_PITFALL.search(line):
                    err(f"{name}:{n}: single-quoted curl -w with \\\\n prints a literal \\n; use double quotes and \\n")
                continue
            if HOME_PATH.search(line):
                warn(f"{name}:{n}: personal /home/<user>/ path; use a generic path")
            for target in LINK.findall(line):
                if re.match(r"^(https?:|mailto:)", target):
                    continue
                file_part, _, anchor = target.partition("#")
                dest = path if not file_part else (path.parent / file_part).resolve()
                if file_part and not dest.exists():
                    err(f"{name}:{n}: broken link to '{file_part}'")
                elif anchor and dest.suffix == ".md":
                    dest_anchors = anchors if dest == path else anchors_of((read(dest) or "").splitlines())
                    if anchor not in dest_anchors:
                        err(f"{name}:{n}: anchor '#{anchor}' not found in {dest.name}")


# --------------------------------------------------------------------------- #
# Secrets and housekeeping
# --------------------------------------------------------------------------- #
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b"), "GitHub token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
    (re.compile(r"(?i)\b(token|password|secret|api[_-]?key)\b\s*[:=]\s*['\"]?([A-Za-z0-9+/_-]{20,})"), "credential-like assignment"),
]


def check_secrets(root: Path) -> None:
    for path in tracked_files(root):
        text = read(path)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for pattern, label in SECRET_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                if label == "credential-like assignment" and PLACEHOLDER.match(match.group(2)):
                    continue
                err(f"{path.relative_to(root).as_posix()}:{n}: possible {label}")


def check_housekeeping(root: Path) -> None:
    if not any((root / n).exists() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt")):
        warn("no LICENSE file; choose one (https://choosealicense.com/) so reuse terms are clear")
    gitignore = (root / ".gitignore")
    if not gitignore.exists() or ".env" not in gitignore.read_text(encoding="utf-8").splitlines():
        err(".gitignore must ignore .env")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    root = parser.parse_args().root.resolve()

    check_env(root)
    check_snort(root)
    check_nginx(root)
    check_markdown(root)
    check_secrets(root)
    check_housekeeping(root)

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR:   {e}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
