#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCloud docs scraper — section id collector (services-first exploration).

Requirements implemented:
- Include DEFAULT_BASE_URL.
- Explore services one by one (discover /sdk/gcloud/reference/<service> links).
- Optional flag to *silence* actual flag extraction; for now we only collect
  unique names of the `id` attribute of <section> tags.
- Write a TXT file with the global unique names.
- Write TXT files with unique names per service.

Notes:
- Run this script on a machine with internet access.
- Dependencies: requests, beautifulsoup4.

Usage examples:
    python gcloud_section_ids_scraper.py \
        --base-url https://cloud.google.com/sdk/gcloud/reference \
        --max-pages 2000 \
        --out-global global_section_ids.txt \
        --out-per-service-dir services_ids \
        --ids-only true 

    python gcloud_section_ids_scraper.py --help
"""

import argparse
import logging
import time
import re
from collections import deque
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --- Constants ---
DEFAULT_BASE_URL = "https://cloud.google.com/sdk/gcloud/reference"
PATH_PREFIX = "/sdk/gcloud/reference"
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3
SLEEP_SECONDS = 0.25
USER_AGENT = "Mozilla/5.0 (compatible; gcloud-section-ids/1.0; +https://cloud.google.com/sdk/gcloud/reference)"

# --- Logging ---
def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

# --- HTTP helpers ---
def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.text
            elif 300 <= resp.status_code < 400 and "Location" in resp.headers:
                new_url = resp.headers["Location"]
                logging.info(f"redirect: {url} -> {new_url}")
                url = new_url
                continue
            else:
                logging.warning(f"non-200 status {resp.status_code} for {url}")
        except requests.RequestException as e:
            logging.warning(f"request error (attempt {attempt}) for {url}: {e}")
        time.sleep(SLEEP_SECONDS * attempt)
    logging.error(f"failed to fetch after {MAX_RETRIES} attempts: {url}")
    return ""

# --- Link discovery ---
def extract_links(base_url: str, html: str) -> Set[str]:
    """Extract all anchors, absolutize, keep only those under PATH_PREFIX."""
    links: Set[str] = set()
    if not html:
        return links
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        if parsed.path.startswith(PATH_PREFIX):
            links.add(abs_url)
    return links

def discover_services(base_url: str) -> Dict[str, str]:
    """Return mapping {service_name: service_url} for first-level service pages.

    A service page is any link whose path is /sdk/gcloud/reference/<service> (one tail segment).
    """
    logging.info(f"discover-services: base={base_url}")
    html = fetch_html(base_url)
    if not html:
        logging.error("no html at base url; cannot discover services")
        return {}
    links = extract_links(base_url, html)
    services: Dict[str, str] = {}
    for link in sorted(links):
        parsed = urlparse(link)
        parts = [p for p in parsed.path.split("/") if p]
        try:
            ref_idx = parts.index("reference")
        except ValueError:
            continue
        tail = parts[ref_idx + 1:]
        if len(tail) == 1:  # service-level page
            service = tail[0]
            services[service] = link
    logging.info(f"services-found: count={len(services)}")
    for s, u in services.items():
        logging.info(f"  - service: {s} | url: {u}")
    return services

# --- Section id extraction ---
def extract_section_ids(article) -> Set[str]:
    """Collect unique names of the attribute 'id' from <section id='...'> tags."""
    ids: Set[str] = set()
    for section in article.find_all("section"):
        sec_id = section.get("id")
        if sec_id:
            ids.add(sec_id.strip())
    return ids

# --- Crawling a single service ---
def crawl_service(service_url: str, max_pages: int = 2000, ids_only: bool = True) -> Tuple[Set[str], int]:
    """Crawl pages under this service and collect unique <section id> names.

    Returns (section_ids, pages_visited).
    """
    parsed_service = urlparse(service_url)
    service_parts = [p for p in parsed_service.path.split("/") if p]
    ref_idx = service_parts.index("reference")
    service_name = service_parts[ref_idx + 1]

    visited: Set[str] = set()
    queue: deque[str] = deque([service_url])
    section_ids: Set[str] = set()

    logging.info(f"process-service: {service_name} | start={service_url}")

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        logging.info(f"scrap-page: service={service_name} | url={url} | visited={len(visited)} | queued={len(queue)}")
        html = fetch_html(url)
        if not html:
            logging.warning(f"no-html: {url}")
            continue
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article")
        if not article:
            logging.info(f"no-article: {url}")
            continue

        # --- Collect only section IDs for now ---
        ids = extract_section_ids(article)
        if ids:
            logging.info(f"found-section-ids: service={service_name} | count={len(ids)} | url={url}")
            for i in sorted(ids):
                logging.info(f"  - section-id: {i}")
            section_ids.update(ids)
        else:
            logging.info(f"no-section-ids: url={url}")

        # --- Discover more links within this service ---
        new_links = set()
        for link in extract_links(url, html):
            parsed = urlparse(link)
            parts = [p for p in parsed.path.split("/") if p]
            try:
                ref_idx2 = parts.index("reference")
            except ValueError:
                continue
            tail = parts[ref_idx2 + 1:]
            # Keep links under the same service name
            if not tail:
                continue
            if tail[0] != service_name:
                continue
            if link not in visited:
                new_links.add(link)
        if new_links:
            logging.info(f"discover-links: service={service_name} | new={len(new_links)} | from={url}")
            for nl in sorted(new_links):
                logging.info(f"  - queued: {nl}")
                queue.append(nl)

        time.sleep(SLEEP_SECONDS)

    logging.info(f"service-done: {service_name} | pages={len(visited)} | unique-section-ids={len(section_ids)}")
    return section_ids, len(visited)

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="GCloud docs scraper — collect unique <section id> names per service.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Reference index URL (default: %(default)s)")
    parser.add_argument("--max-pages", type=int, default=2000, help="Max pages per service (default: %(default)s)")
    parser.add_argument("--out-global", default="section_ids_global.txt", help="TXT file for global unique section ids")
    parser.add_argument("--out-per-service-dir", default="services_section_ids", help="Directory to write per-service TXT files")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--ids-only", default="true", choices=["true", "false"], help="Silence actual flag extraction; only collect section ids")

    args = parser.parse_args()
    setup_logging(args.log_level)

    base_url = args.base_url
    ids_only = (args.ids_only.lower() == "true")

    logging.info(f"start: base-url={base_url} | ids-only={ids_only}")

    # Discover services from base
    services = discover_services(base_url)
    if not services:
        logging.error("no services discovered; exiting")
        return

    # Prepare output directory
    out_dir = Path(args.out_per_service_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    global_ids: Set[str] = set()
    per_service_counts: Dict[str, int] = {}

    # Explore services one by one
    for service_name, service_url in sorted(services.items()):
        sec_ids, visited_pages = crawl_service(service_url, max_pages=args.max_pages, ids_only=ids_only)
        per_service_counts[service_name] = visited_pages
        global_ids.update(sec_ids)

        # Write per-service TXT
        service_file = out_dir / f"{service_name}_section_ids.txt"
        with service_file.open("w", encoding="utf-8") as f:
            for sid in sorted(sec_ids):
                f.write(sid + "\n")
        logging.info(f"write-per-service: {service_name} -> {service_file} (ids={len(sec_ids)})")

    # Write global TXT
    global_file = Path(args.out_global)
    with global_file.open("w", encoding="utf-8") as f:
        for sid in sorted(global_ids):
            f.write(sid + "\n")
    logging.info(f"write-global: {global_file} (ids={len(global_ids)})")

    # Summary
    logging.info("summary: per-service pages visited")
    for s, cnt in sorted(per_service_counts.items()):
        logging.info(f"  - {s}: pages={cnt}")

if __name__ == "__main__":
    main()
