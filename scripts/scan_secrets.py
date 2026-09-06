#!/usr/bin/env python3
"""
scan_secrets.py — run this before you commit.

Scans every text file in the repo for things that should never be published from
a home automation config: private IPs, MAC addresses, RTSP credentials, tokens,
webhook paths, email addresses, and opaque Home Assistant device IDs.

Exits non-zero on any hit, so it works as a pre-commit hook:

    ln -s ../../scripts/scan_secrets.py .git/hooks/pre-commit

To also scan for your own family names, put one per line in a file called
`.private-terms` at the repo root. That file is gitignored, so your names never
end up in the repository just because you scanned for them.
"""
import re
import os
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    os.pardir))

FATAL = {
    "private_ipv4": r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b",
    "mac_address": r"\b(?!AA:BB:CC:DD:EE:FF)(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b",
    "rtsp_credential": r"rtsp://(?!<|user:pass@)[^:/@\s]+:[^@\s]+@",
    "token_assignment": (r"(?i)\b(?:api[_-]?key|access[_-]?token|bearer|llat|password|passwd)"
                         r"\s*[:=]\s*(?!<|\"?\{\{|''|\"\"|$)\S{6,}"),
    "jwt": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    "webhook_path": r"/api/webhook/[A-Za-z0-9_-]{8,}",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "nabucasa_host": r"[a-z0-9]{8,}\.ui\.nabu\.casa",
    "coordinates": r"\b[0-9]{1,2}\.\d{4,}\s*,\s*-?1?[0-9]{1,2}\.\d{4,}\b",
    "opaque_device_id": r"\b[0-9a-f]{32}\b",
}

SKIP_EXT = {'.wav', '.mp3', '.png', '.jpg', '.jpeg', '.gif', '.zip'}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}
# This file necessarily contains the patterns it searches for.
SKIP_FILES = {os.path.join('scripts', 'scan_secrets.py')}


def load_private_terms():
    p = os.path.join(ROOT, '.private-terms')
    if not os.path.exists(p):
        return None
    terms = [t.strip() for t in open(p, encoding='utf-8') if t.strip()
             and not t.startswith('#')]
    if not terms:
        return None
    return re.compile(r'(?i)\b(' + '|'.join(re.escape(t) for t in terms) + r')\b')


def main():
    private = load_private_terms()
    if private:
        print("scanning with .private-terms loaded")

    hits = Counter()
    failures = []
    nfiles = 0

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT)
            if rel in SKIP_FILES or os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            nfiles += 1
            try:
                text = open(path, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            checks = dict(FATAL)
            if private:
                checks['private_term'] = private.pattern
            for name, pattern in checks.items():
                found = re.findall(pattern, text)
                if not found:
                    continue
                # The MIT copyright line is the one intentional personal name.
                if name == 'private_term' and rel == 'LICENSE':
                    continue
                hits[name] += len(found)
                uniq = sorted({f if isinstance(f, str) else str(f) for f in found})
                failures.append((rel, name, len(found), uniq[:6]))

    print(f"scanned {nfiles} text files under {ROOT}")
    if failures:
        print("\nFAILURES — do not commit:")
        for rel, name, n, uniq in failures:
            print(f"  {rel}\n      [{name}] {n} hits -> {uniq}")
        print("\ntotals:", dict(hits))
        return 1
    print("clean — no secrets found.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
