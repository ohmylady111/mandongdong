#!/usr/bin/env python3
"""
授权来源漫画/图集下载模板（Scrapling 版）

只用于：
- 你自己的网站 / 你拥有版权的内容
- 你被明确授权可归档、备份、迁移的页面

支持：
1) 纯命令行参数
2) 用 --config 读取 JSON 配置文件（更适合长期复用）
3) 作为模块被 UI/打包程序调用
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from scrapling.fetchers import DynamicFetcher, Fetcher

COMMON_IMAGE_SELECTORS = [
    ".comic-page img::attr(src)",
    ".comic-page img::attr(data-src)",
    ".viewer img::attr(src)",
    ".viewer img::attr(data-src)",
    ".manga-page img::attr(src)",
    ".manga-page img::attr(data-src)",
    ".page-chapter img::attr(src)",
    ".page-chapter img::attr(data-src)",
    "main img::attr(src)",
    "main img::attr(data-src)",
    "article img::attr(src)",
    "article img::attr(data-src)",
    "img::attr(src)",
    "img::attr(data-src)",
]

COMMON_PAGE_LINK_SELECTORS = [
    ".chapter-list a::attr(href)",
    ".chapters a::attr(href)",
    ".episode-list a::attr(href)",
    ".content a::attr(href)",
]

TITLE_SELECTORS = [
    'meta[property="og:title"]::attr(content)',
    'meta[name="twitter:title"]::attr(content)',
    "title::text",
    "h1::text",
]

BLOCKLIST_SUBSTRINGS = [
    "avatar",
    "logo",
    "icon",
    "sprite",
    "banner",
    "ads",
    "doubleclick",
    "googlesyndication",
    "gravatar",
]

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0 Safari/537.36"
)


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip("._ ")
    return text[:120] or "untitled"


def unique_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def same_origin(url_a: str, url_b: str) -> bool:
    a = urlparse(url_a)
    b = urlparse(url_b)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def likely_image_url(url: str) -> bool:
    low = url.lower()
    if any(bad in low for bad in BLOCKLIST_SUBSTRINGS):
        return False
    parsed = urlparse(low)
    path = parsed.path
    if any(path.endswith(ext) for ext in VALID_IMAGE_EXTS):
        return True
    return any(token in path for token in ["/image", "/img", "/page", "/upload"]) and not path.endswith(".svg")


def ext_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in VALID_IMAGE_EXTS:
        if path.endswith(ext):
            return ext
    return ".jpg"


def infer_title_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    return slugify(parts[-1] if parts else parsed.netloc)


def load_config_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path).expanduser()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object")
    return data


def merge_args_with_config(args: argparse.Namespace, config: dict[str, Any]) -> argparse.Namespace:
    merged = vars(args).copy()

    defaults = {
        "title": None,
        "dynamic": False,
        "wait_ms": 1500,
        "delay": 0.3,
        "referer": None,
        "user_agent": None,
        "same_origin_only": False,
        "img_selector": [],
        "page_link_selector": [],
        "img_regex": None,
        "page_link_regex": None,
        "manifest_name": "manifest.json",
        "dry_run": False,
        "flat": False,
        "preview_limit": 8,
        "skip_existing": True,
        "download_timeout": 60,
        "retries": 2,
        "page_start": 1,
        "page_end": None,
        "page_limit": None,
        "save_discovery": True,
        "use_common_page_selectors": False,
    }

    for key, value in config.items():
        if key not in merged:
            continue
        if merged[key] == defaults.get(key):
            merged[key] = value

    for required in ["url", "out"]:
        if not merged.get(required):
            raise ValueError(f"Missing required setting: {required}")

    if not isinstance(merged.get("img_selector") or [], list):
        raise ValueError("img_selector in config must be a list")
    if not isinstance(merged.get("page_link_selector") or [], list):
        raise ValueError("page_link_selector in config must be a list")

    return argparse.Namespace(**merged)


def fetch_page(url: str, dynamic: bool = False, wait_ms: int = 1500):
    if dynamic:
        return DynamicFetcher.fetch(
            url,
            headless=True,
            disable_resources=False,
            network_idle=True,
            wait=wait_ms,
        )
    return Fetcher.get(url, stealthy_headers=True)


def extract_many(page, selectors: list[str]) -> list[str]:
    values: list[str] = []
    for selector in selectors:
        try:
            found = page.css(selector).getall()
        except Exception:
            found = []
        if not found:
            continue
        for val in found:
            if isinstance(val, str):
                cleaned = val.strip()
                if cleaned:
                    values.append(cleaned)
    return unique_keep_order(values)


def extract_first(page, selectors: list[str]) -> str | None:
    values = extract_many(page, selectors)
    return values[0] if values else None


def infer_title_from_page(page, fallback_url: str) -> str:
    title = extract_first(page, TITLE_SELECTORS)
    if title:
        title = re.sub(r"\s*[-|_–—]\s*[^-|_–—]+$", "", title).strip()
        title = slugify(title)
        if title and title != "untitled":
            return title
    return infer_title_from_url(fallback_url)


def page_slug(page_url: str) -> str:
    parsed = urlparse(page_url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return "page"
    return slugify(parts[-1])


def apply_page_window(urls: list[str], page_start: int, page_end: int | None, page_limit: int | None) -> list[str]:
    start_idx = max(page_start, 1) - 1
    subset = urls[start_idx:]
    if page_end is not None and page_end >= page_start:
        subset = subset[: page_end - page_start + 1]
    if page_limit is not None and page_limit >= 0:
        subset = subset[:page_limit]
    return subset


def collect_target_pages(start_url: str, args, start_page=None) -> list[str]:
    selectors = list(args.page_link_selector or [])
    if not selectors and args.use_common_page_selectors:
        selectors = COMMON_PAGE_LINK_SELECTORS
    if not selectors:
        return [start_url]

    page = start_page or fetch_page(start_url, dynamic=args.dynamic, wait_ms=args.wait_ms)
    raw_links = extract_many(page, selectors)
    abs_links = [urljoin(start_url, link) for link in raw_links]

    if args.same_origin_only:
        abs_links = [u for u in abs_links if same_origin(start_url, u)]

    if args.page_link_regex:
        rx = re.compile(args.page_link_regex)
        abs_links = [u for u in abs_links if rx.search(u)]

    abs_links = unique_keep_order(abs_links)
    return abs_links or [start_url]


def collect_images(page_url: str, args) -> list[str]:
    page = fetch_page(page_url, dynamic=args.dynamic, wait_ms=args.wait_ms)
    selectors = args.img_selector or COMMON_IMAGE_SELECTORS
    raw_urls = extract_many(page, selectors)
    abs_urls = [urljoin(page_url, u) for u in raw_urls]

    if args.same_origin_only:
        abs_urls = [u for u in abs_urls if same_origin(page_url, u)]

    if args.img_regex:
        rx = re.compile(args.img_regex)
        abs_urls = [u for u in abs_urls if rx.search(u)]

    abs_urls = [u for u in abs_urls if likely_image_url(u)]
    return unique_keep_order(abs_urls)


def download_file(
    url: str,
    dest: Path,
    referer: str | None = None,
    user_agent: str | None = None,
    timeout: int = 60,
    retries: int = 2,
    skip_existing: bool = True,
) -> str:
    if skip_existing and dest.exists() and dest.stat().st_size > 0:
        return "skipped"

    headers = {
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer

    last_error = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            dest.write_bytes(data)
            return "downloaded"
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(1.5 * (attempt + 1), 5))
            else:
                raise last_error
    raise last_error


def print_preview(name: str, items: list[str], limit: int) -> None:
    print(f"[preview] {name}: {len(items)}")
    for item in items[:limit]:
        print(f"  - {item}")
    if len(items) > limit:
        print(f"  ... (+{len(items) - limit} more)")


def write_text_list(path: Path, items: list[str]) -> None:
    path.write_text("\n".join(items) + ("\n" if items else ""), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download images from an authorized manga/gallery source using Scrapling.")
    parser.add_argument("--config", help="JSON config file path")
    parser.add_argument("--url", help="Authorized source page URL")
    parser.add_argument("--out", help="Output directory on local disk / mounted NAS path")
    parser.add_argument("--title", help="Optional folder name override")
    parser.add_argument("--dynamic", action="store_true", help="Use browser rendering for JS-heavy pages")
    parser.add_argument("--wait-ms", type=int, default=1500, help="Extra wait after page load in dynamic mode")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between downloads (seconds)")
    parser.add_argument("--referer", help="Optional Referer header for anti-hotlink protection")
    parser.add_argument("--user-agent", help="Optional custom User-Agent")
    parser.add_argument("--same-origin-only", action="store_true", help="Keep only URLs from the same origin")
    parser.add_argument("--dry-run", action="store_true", help="Only inspect discovered pages/images, do not download")
    parser.add_argument("--flat", action="store_true", help="Save all images into one folder instead of per-page subfolders")
    parser.add_argument("--preview-limit", type=int, default=8, help="How many URLs to print in dry-run preview")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip files that already exist (default: on)")
    parser.add_argument("--download-timeout", type=int, default=60, help="Timeout per image download in seconds")
    parser.add_argument("--retries", type=int, default=2, help="Retries per image download")
    parser.add_argument("--page-start", type=int, default=1, help="Start from Nth discovered page (1-based)")
    parser.add_argument("--page-end", type=int, help="End at Nth discovered page (1-based, inclusive)")
    parser.add_argument("--page-limit", type=int, help="Download at most N discovered pages")
    parser.add_argument("--save-discovery", action="store_true", default=True, help="Write discovered pages/images lists next to manifest")
    parser.add_argument("--use-common-page-selectors", action="store_true", help="Try built-in common chapter-list selectors when page_link_selector is empty")

    parser.add_argument(
        "--img-selector",
        action="append",
        default=[],
        help="CSS selector that returns image URLs, e.g. '.comic-page img::attr(src)' (repeatable)",
    )
    parser.add_argument(
        "--page-link-selector",
        action="append",
        default=[],
        help="CSS selector that returns chapter/subpage hrefs, e.g. '.chapter-list a::attr(href)' (repeatable)",
    )
    parser.add_argument("--img-regex", help="Optional regex to keep only matching image URLs")
    parser.add_argument("--page-link-regex", help="Optional regex to keep only matching subpage URLs")
    parser.add_argument("--manifest-name", default="manifest.json", help="Manifest filename")
    return parser


def build_default_namespace() -> argparse.Namespace:
    parser = build_arg_parser()
    return parser.parse_args([])


def build_namespace_from_config(config: dict[str, Any]) -> argparse.Namespace:
    return merge_args_with_config(build_default_namespace(), config)


def run_with_args(args: argparse.Namespace) -> int:
    start_page = fetch_page(args.url, dynamic=args.dynamic, wait_ms=args.wait_ms)
    root_name = args.title or infer_title_from_page(start_page, args.url)
    root_dir = Path(args.out).expanduser() / root_name
    root_dir.mkdir(parents=True, exist_ok=True)

    discovered_pages = collect_target_pages(args.url, args, start_page=start_page)
    target_pages = apply_page_window(discovered_pages, args.page_start, args.page_end, args.page_limit)

    manifest: dict[str, Any] = {
        "source_url": args.url,
        "root_dir": str(root_dir),
        "title": root_name,
        "dynamic": args.dynamic,
        "dry_run": args.dry_run,
        "flat": args.flat,
        "page_start": args.page_start,
        "page_end": args.page_end,
        "page_limit": args.page_limit,
        "discovered_page_count": len(discovered_pages),
        "selected_page_count": len(target_pages),
        "pages": [],
    }

    print(f"[info] title: {root_name}")
    print(f"[info] discovered pages: {len(discovered_pages)}")
    print(f"[info] selected pages: {len(target_pages)}")

    if args.save_discovery:
        write_text_list(root_dir / "discovered_pages.txt", discovered_pages)

    if args.dry_run:
        print_preview("pages", target_pages, args.preview_limit)

    global_image_index = 1

    for page_idx, page_url in enumerate(target_pages, start=1):
        folder_name = f"{page_idx:03d}_{page_slug(page_url)}"
        page_folder = root_dir if args.flat else (root_dir / folder_name)
        page_folder.mkdir(parents=True, exist_ok=True)

        print(f"[info] scanning page {page_idx}/{len(target_pages)}: {page_url}")
        image_urls = collect_images(page_url, args)
        print(f"[info] found {len(image_urls)} image(s)")

        if args.save_discovery:
            write_text_list(root_dir / f"images_{page_idx:03d}.txt", image_urls)

        if args.dry_run:
            print_preview(f"images from page {page_idx}", image_urls, args.preview_limit)

        saved_files = []
        skipped_files = []
        failed_urls = []

        for img_idx, img_url in enumerate(image_urls, start=1):
            if args.dry_run:
                continue

            ext = ext_from_url(img_url)
            seq = global_image_index if args.flat else img_idx
            filename = f"{seq:03d}{ext}"
            dest = page_folder / filename
            try:
                result = download_file(
                    img_url,
                    dest,
                    referer=args.referer or page_url,
                    user_agent=args.user_agent,
                    timeout=args.download_timeout,
                    retries=args.retries,
                    skip_existing=args.skip_existing,
                )
                if result == "skipped":
                    skipped_files.append(filename)
                    print(f"[skip] {dest}")
                else:
                    saved_files.append(filename)
                    print(f"[ok] {dest}")
                global_image_index += 1
            except Exception as exc:
                failed_urls.append(img_url)
                print(f"[warn] failed: {img_url} -> {exc}", file=sys.stderr)
            time.sleep(args.delay)

        manifest["pages"].append(
            {
                "page_index": page_idx,
                "page_url": page_url,
                "page_folder": str(page_folder),
                "image_count": len(image_urls),
                "saved_files": saved_files,
                "skipped_files": skipped_files,
                "failed_urls": failed_urls,
            }
        )

    manifest_path = root_dir / args.manifest_name
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] manifest -> {manifest_path}")
    return 0


def run_config(config: dict[str, Any]) -> int:
    args = build_namespace_from_config(config)
    return run_with_args(args)


def run_config_path(path: str | Path) -> int:
    config = load_config_file(str(path))
    return run_config(config)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    raw_args = parser.parse_args(argv)
    config = load_config_file(raw_args.config)
    args = merge_args_with_config(raw_args, config)
    return run_with_args(args)


if __name__ == "__main__":
    raise SystemExit(main())
