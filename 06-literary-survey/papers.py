#!/usr/bin/env python3
"""Download research papers listed in registry.json.

Usage:
    python papers.py                    # download all pending entries
    python papers.py --status           # print summary table
    python papers.py --validate         # HEAD-check URLs only, no download
    python papers.py --retry            # also retry failed/url_dead entries
    python papers.py --force            # re-download everything
    python papers.py --tag Turpin2023   # act on a single entry
    python papers.py --add urls.txt --prompt prompt2-audit
                                        # append URL list to registry as pending

Stdlib only (urllib, hashlib, json). No pip install required.
Stores PDFs under <papers_dir>/<tag>.pdf. Updates registry atomically
after each entry so a Ctrl+C never corrupts state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REGISTRY_PATH = Path(__file__).parent / "registry.json"
TIMEOUT_SEC = 60
MAX_RETRIES = 3
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)
GOOGLEBOT_UA = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)
# domains where the cert chain is known to be missing/broken in Python's default
# trust store; we fall back to an unverified context after a normal SSL failure.
# `.in` is broad on purpose — many Indian academic/policy hosts run on internal
# PKI chains that Python's default bundle doesn't recognise. The `verify_skipped`
# flag on the registry entry preserves the audit trail.
INSECURE_FALLBACK_DOMAINS = (
    ".in",
)


def make_ssl_context(insecure: bool = False) -> ssl.SSLContext:
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def host_allows_insecure_fallback(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host.endswith(suf) for suf in INSECURE_FALLBACK_DOMAINS)


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        sys.exit(f"registry not found: {REGISTRY_PATH}")
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(reg: dict) -> None:
    """Atomic write with Windows-aware fallback.

    Windows raises PermissionError on os.replace() when another process
    (e.g. an IDE auto-refreshing the file) holds a handle to the
    destination. We retry briefly, then fall back to a direct overwrite
    of the JSON text (still single-write at the OS level for a few-KB
    file, so torn writes are extremely unlikely).
    """
    text = json.dumps(reg, indent=2, ensure_ascii=False)
    tmp = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(5):
        try:
            tmp.replace(REGISTRY_PATH)
            return
        except PermissionError:
            if attempt < 4:
                time.sleep(0.2 * (attempt + 1))
                continue
            # last resort: direct overwrite
            REGISTRY_PATH.write_text(text, encoding="utf-8")
            try:
                tmp.unlink()
            except OSError:
                pass
            return


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_request(
    url: str,
    user_agent: str,
    method: str = "GET",
    extra_headers: dict[str, str] | None = None,
) -> urllib.request.Request:
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", user_agent)
    req.add_header(
        "Accept",
        "application/pdf,application/x-pdf,application/octet-stream,text/html;q=0.9,*/*;q=0.8",
    )
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    # MDPI / Cloudflare-fronted publishers reject requests with no Referer
    host = urlparse(url).netloc
    if "mdpi.com" in host:
        req.add_header("Referer", f"https://{host}/")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    return req


def head_check(url: str, user_agent: str) -> tuple[int | None, str | None]:
    ctx = make_ssl_context(insecure=False)
    try:
        req = make_request(url, user_agent, method="HEAD")
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC, context=ctx) as resp:
            return resp.status, None
    except urllib.error.HTTPError as e:
        # some servers reject HEAD with 405; fall back to GET (no body read)
        if e.code == 405:
            try:
                req = make_request(url, user_agent, method="GET")
                with urllib.request.urlopen(req, timeout=TIMEOUT_SEC, context=ctx) as resp:
                    return resp.status, None
            except Exception as inner:
                return getattr(inner, "code", None), str(inner)
        return e.code, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, str(e)


def sniff_extension(data: bytes, content_type: str) -> str:
    """Pick a sensible file extension from magic bytes + Content-Type."""
    ct = (content_type or "").lower()
    if data[:4] == b"%PDF" or "pdf" in ct:
        return ".pdf"
    head = data[:512].lstrip().lower()
    if "html" in ct or head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        return ".html"
    if "json" in ct:
        return ".json"
    if "xml" in ct:
        return ".xml"
    return ".bin"


def _do_fetch(
    url: str, user_agent: str, ssl_ctx: ssl.SSLContext,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, str, bytes]:
    """Single attempt; returns (status, content_type, data) or raises."""
    req = make_request(url, user_agent, extra_headers=extra_headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC, context=ssl_ctx) as resp:
        status = resp.status
        ctype = resp.headers.get("Content-Type", "")
        data = resp.read()
    return status, ctype, data


def download(
    url: str, out_path_base: Path, user_agent: str
) -> tuple[int | None, int | None, str | None, str | None, Path | None, dict | None]:
    """Returns (http_status, size, sha, error, out_path, meta).
    meta carries flags like {'verify_skipped': True, 'ua_fallback': 'googlebot'}.
    """
    secure_ctx = make_ssl_context(insecure=False)
    insecure_ctx = make_ssl_context(insecure=True)
    last_err = None
    last_status: int | None = None
    meta: dict = {}

    # -- pass 1: normal SSL, default UA, with backoff for transient errors
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            status, ctype, data = _do_fetch(url, user_agent, secure_ctx)
            return _save(data, ctype, status, out_path_base) + (meta,)
        except urllib.error.HTTPError as e:
            last_status = e.code
            last_err = f"HTTP {e.code}: {e.reason}"
            # 403/401/451 → fall through to UA fallback below; other 4xx are terminal
            if e.code in (401, 403, 451):
                break
            if 400 <= e.code < 500:
                return e.code, None, None, last_err, None, meta
        except ssl.SSLError as e:
            last_err = f"SSL: {e}"
            break  # fall through to insecure fallback
        except urllib.error.URLError as e:
            # could be SSL-cert error wrapped in URLError
            reason = getattr(e, "reason", e)
            if isinstance(reason, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(reason):
                last_err = f"SSL: {reason}"
                break
            last_err = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
        except Exception as e:
            last_err = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    # -- pass 2: SSL fallback for whitelisted government domains
    if last_err and "SSL" in last_err and host_allows_insecure_fallback(url):
        try:
            status, ctype, data = _do_fetch(url, user_agent, insecure_ctx)
            meta["verify_skipped"] = True
            return _save(data, ctype, status, out_path_base) + (meta,)
        except Exception as e:
            last_err = f"SSL-fallback: {e}"
            last_status = getattr(e, "code", last_status)

    # -- pass 3: 403/401 fallback with Googlebot UA + same-host Referer
    if last_status in (401, 403, 451):
        host = urlparse(url).netloc
        extra = {"Referer": f"https://{host}/"}
        for ua in (GOOGLEBOT_UA, user_agent):
            try:
                status, ctype, data = _do_fetch(url, ua, secure_ctx, extra_headers=extra)
                meta["ua_fallback"] = "googlebot" if ua == GOOGLEBOT_UA else "default+referer"
                return _save(data, ctype, status, out_path_base) + (meta,)
            except urllib.error.HTTPError as e:
                last_status = e.code
                last_err = f"HTTP {e.code}: {e.reason}"
            except Exception as e:
                last_err = str(e)

    return last_status, None, None, last_err, None, meta


def _save(
    data: bytes, ctype: str, status: int, out_path_base: Path
) -> tuple[int, int, str, None, Path]:
    sha = hashlib.sha256(data).hexdigest()
    ext = sniff_extension(data, ctype)
    out_path = out_path_base.with_suffix(ext)
    for sibling_ext in (".pdf", ".html", ".json", ".xml", ".bin"):
        if sibling_ext != ext:
            sib = out_path_base.with_suffix(sibling_ext)
            if sib.exists():
                try:
                    sib.unlink()
                except OSError:
                    pass
    out_path.write_bytes(data)
    return status, len(data), sha, None, out_path


def derive_tag_from_url(url: str, existing_tags: set[str]) -> str:
    """Auto-generate a tag from a URL when --add doesn't provide one."""
    parsed = urlparse(url)
    base = Path(parsed.path).stem or parsed.netloc
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:40]
    tag = base or "paper"
    n = 1
    candidate = tag
    while candidate in existing_tags:
        n += 1
        candidate = f"{tag}_{n}"
    return candidate


def cmd_add(reg: dict, urls_file: Path, source_prompt: str) -> None:
    if not urls_file.exists():
        sys.exit(f"urls file not found: {urls_file}")
    existing_urls = {p["url"] for p in reg["papers"]}
    existing_tags = {p["tag"] for p in reg["papers"]}
    added = 0
    for line in urls_file.read_text(encoding="utf-8").splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        if url in existing_urls:
            continue
        tag = derive_tag_from_url(url, existing_tags)
        existing_tags.add(tag)
        reg["papers"].append({
            "tag": tag,
            "title": None,
            "year": None,
            "url": url,
            "source_prompt": source_prompt,
            "category": None,
            "relevance": None,
            "status": "pending",
            "filename": None,
            "size_bytes": None,
            "sha256": None,
            "http_status": None,
            "downloaded_at": None,
            "error": None,
        })
        added += 1
        print(f"  + {tag}  {url}")
    save_registry(reg)
    print(f"added {added} new entries")


def select_targets(papers: list[dict], args: argparse.Namespace) -> list[dict]:
    if args.force:
        target_statuses = None
    else:
        target_statuses = {"pending", "url_valid"}
        if args.retry:
            target_statuses |= {"failed", "url_dead"}
    return [
        e for e in papers
        if (args.tag is None or e["tag"] == args.tag)
        and (target_statuses is None or e["status"] in target_statuses)
    ]


def print_status(papers: list[dict]) -> None:
    by_status: dict[str, int] = {}
    for e in papers:
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1
    print(f"\nregistry: {len(papers)} total")
    for s in sorted(by_status):
        print(f"  {s:14s} {by_status[s]}")
    failed = [e for e in papers if e["status"] in ("failed", "url_dead")]
    if failed:
        print("\nfailed / dead URLs:")
        for e in failed:
            err = (e.get("error") or "?")[:80]
            print(f"  {e['tag']:24s} {err}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", action="store_true", help="print summary and exit")
    p.add_argument("--validate", action="store_true", help="HEAD-check URLs only")
    p.add_argument("--force", action="store_true", help="re-act on entries regardless of status")
    p.add_argument("--retry", action="store_true", help="include failed/url_dead in selection")
    p.add_argument("--tag", help="only act on this tag")
    p.add_argument("--add", type=Path, metavar="URLS_FILE",
                   help="append URL list to registry as pending entries")
    p.add_argument("--prompt", default="manual",
                   help="source_prompt label for --add (default: manual)")
    args = p.parse_args()

    reg = load_registry()
    papers = reg["papers"]

    if args.add:
        cmd_add(reg, args.add, args.prompt)
        return

    if args.status:
        print_status(papers)
        return

    user_agent = reg.get("user_agent", DEFAULT_USER_AGENT)
    host_delay = float(reg.get("host_delay_sec", 3))
    papers_dir = Path(__file__).parent / reg.get("papers_dir", "papers")
    papers_dir.mkdir(exist_ok=True)

    selected = select_targets(papers, args)
    if not selected:
        print("nothing to do")
        print_status(papers)
        return

    action = "validating" if args.validate else "downloading"
    print(f"{action} {len(selected)} paper(s) -> {papers_dir}\n")

    last_host_time: dict[str, float] = {}
    for entry in selected:
        host = urlparse(entry["url"]).netloc
        wait = host_delay - (time.monotonic() - last_host_time.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        last_host_time[host] = time.monotonic()

        if args.validate:
            status, err = head_check(entry["url"], user_agent)
            entry["http_status"] = status
            if status and 200 <= status < 400:
                if entry["status"] == "pending":
                    entry["status"] = "url_valid"
                entry["error"] = None
                print(f"  OK   {entry['tag']:24s} {status}  {entry['url']}")
            else:
                entry["status"] = "url_dead"
                entry["error"] = err or f"status {status}"
                print(f"  XX   {entry['tag']:24s} {status}  {entry['error']}")
            save_registry(reg)
            continue

        out_path_base = papers_dir / entry["tag"]
        print(f"  -> {entry['tag']:24s} {entry['url']}")
        status, size, sha, err, out_path, meta = download(entry["url"], out_path_base, user_agent)
        entry["http_status"] = status
        entry["downloaded_at"] = now_iso()
        if err is None and status and 200 <= status < 400 and out_path is not None:
            entry["status"] = "downloaded"
            entry["filename"] = out_path.name
            entry["size_bytes"] = size
            entry["sha256"] = sha
            entry["error"] = None
            entry["verify_skipped"] = bool(meta and meta.get("verify_skipped"))
            entry["ua_fallback"] = (meta or {}).get("ua_fallback")
            tags = []
            if entry["verify_skipped"]:
                tags.append("INSECURE")
            if entry["ua_fallback"]:
                tags.append(f"UA={entry['ua_fallback']}")
            note = f"  ({', '.join(tags)})" if tags else ""
            print(f"     OK  [{out_path.suffix[1:] or '?':4s}] {size:>10,} bytes  sha256:{sha[:12]}...{note}")
        else:
            entry["status"] = "failed"
            entry["error"] = err or f"HTTP {status}"
            if out_path is not None and out_path.exists():
                out_path.unlink()  # don't keep partial files
            print(f"     FAIL {entry['error']}")
        save_registry(reg)

    print()
    print_status(papers)


if __name__ == "__main__":
    main()
