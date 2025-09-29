# backend/services/knowledge_updater.py

import os
import json
import hashlib
import requests
from urllib.parse import urljoin
from backend.core.types.enums import UpdateMode
from backend.core.types.entities import ServiceCommand
from typing import Dict, List, Union, Optional
from bs4 import BeautifulSoup, ResultSet, Tag  # pip install beautifulsoup4
import logging as log

#log.basicConfig(level=log.INFO, format="%(levelname)s:%(message)s")
log.basicConfig(level=log.INFO)

class KnowledgeUpdater():
    BASE_URL = "https://cloud.google.com/sdk/gcloud/reference"
    SDK_RELATIVE_URL = "/sdk/gcloud/reference/"
    PLUGINS_DIR = "plugins"

    def __init__(self, recursion_level_limit: int=1):
        self.recursion_level_limit = recursion_level_limit
        self.reset_recursion()
        
        # Make directories
        os.makedirs(self.PLUGINS_DIR, exist_ok=True)
    
    def reset_recursion(self):
        self.recursion_level = 0
        self.continue_recursion = True
    
    def commit_recursion(self):
        self.recursion_level += 1

        log.info(f"Going UP to level '{self.recursion_level}'")
    
    def uncommit_recursion(self):
        self.recursion_level -= 1

        log.info(f"Going DOWN to level '{self.recursion_level}'")

    def can_next_recursion(self):
        if self.recursion_level < self.recursion_level_limit:
            self.commit_recursion()
        else:
            log.info(f"Blocked next recursion: level limit reached '{self.recursion_level_limit}'. Going down")
            self.reset_recursion()
        
        return self.continue_recursion

    # -----------------------------
    # Public entrypoint
    # -----------------------------
    def run_update(
        self,
        mode: UpdateMode,
        target_update: Optional[Union[str, List[str]]] = None
    ):
        log.info(f"Start update mode {mode} - Target: {str(target_update)}")
        
        if mode == UpdateMode.FULL:
            self._update_all_services()
        elif mode == UpdateMode.PARTIAL:
            if not target_update:
                raise ValueError("PARTIAL update requires target_update as list/tuple of commands.")
            self._update_services(target_update)
        elif mode == UpdateMode.SINGLE:
            if not target_update:
                raise ValueError("SINGLE update requires target_update as string or list of length 1.")
            if isinstance(target_update, (list, tuple)):
                if len(target_update) != 1:
                    raise ValueError("SINGLE update requires exactly one command.")
                target_update = target_update[0]
            self._update_single(target_update)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    # -----------------------------
    # Private helpers
    # -----------------------------
    def _update_all_services(self) -> Dict[str, Dict]:
        """Fetch and parse all services listed at reference root."""
        index_html = requests.get(self.BASE_URL).text
        soup = BeautifulSoup(index_html, "html.parser")

        # Extract all service links from index page
        commands_data: Dict[str, ServiceCommand] = {}
        section_tags = soup.select_one("ul.devsite-nav-section")
        for section_tag in section_tags:
            href: str = section_tag.select_one("li a[href]") \
                              .get("href", "")
            if not href.startswith("/sdk/gcloud/reference/"):
                continue
            service = href.split("/")[-1]
            if not service or service == "reference":
                continue

            commands_data[service] = self._scrape_command_page(service)

        # Serialize to JSON
        print("Scraping relative urls\n---------------------")
        for k, v in commands_data.items():
            filename = f"{service}_command.json"
            self._save_json(filename, k, {k, v.to_dict()})

        # common tag element
        article = soup.find("article") # .devsite-article

        # Extract global and other flags
        global_flags = self._extract_flags(article, "section[id='GLOBAL-FLAGS'] dl")
        filename = "global_flags.json"
        self._save_json(filename, "", global_flags)

        other_flags = self._extract_flags(article, "section[id='OTHER-FLAGS'] dl")
        filename = "other_flags.json"
        self._save_json(filename, "", other_flags)

        return {k: v.to_dict() for k, v in commands_data.items()}

    def _update_services(self, services: List[str]) -> Dict[str, Dict]:
        """Fetch and parse only a list of services."""
        for svc in services:
            self._update_single(svc)

    def _update_single(self, service: str) -> Dict[str, Dict]:
        """Fetch and parse a single service."""
        service_data = self._scrape_command_page(service).to_dict()
        filename = f"{service}_command.json"
        self._save_json(filename, service, service_data)

    def _scrape_command_page(self, service: str) -> ServiceCommand:
        """Scrape details of a single gcloud service page."""
        url = f"{self.BASE_URL}/{service}"

        log.info(f"scrap-command: {url}")

        resp = requests.get(url)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        article = soup.find("article") # .devsite-article

        # Synopsis
        synopsis = self._get_key_text(article, "section[id='SYNOPSIS']")
        
        # Long description
        desc = self._get_key_text(article, "section[id='DESCRIPTION']")
        
        # Commands
        cmd_section = article.select_one("section[id='COMMAND']")
        #data_cmds = self._get_groups(cmd_section, service) if cmd_section else {}
        data_cmds = self._get_recursive_groups(cmd_section, service) if cmd_section else {}
        
        # Groups
        group_section = article.select_one("section[id='GROUP']")
        #data_groups = self._get_groups(group_section,) if group_section else {}
        data_groups = self._get_recursive_groups(group_section, service) if group_section else {}

        # Positional arguments
        positional_args = self._extract_flags(article, "section[id='POSITIONAL-ARGUMENTS'] dl")
        
        # Required flags
        required_flags = self._extract_flags(article, "section[id='REQUIRED-FLAGS'] dl")
        
        # Signature
        raw_string = f"{service}.{'.'.join(sorted(data_groups.keys()))}.{'.'.join(sorted(data_cmds.keys()))}"
        sha256_sign = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

        return ServiceCommand(
            service_url=url,
            service_name=f"{service}",
            description=desc,
            command_synopsis=synopsis,
            sha256_sign=sha256_sign,
            positional_args=positional_args,
            required_flags=required_flags,
            base_groups=data_groups,
            base_commands=data_cmds
        )
    
    def _get_key_text(self, tag: Tag, css_selector: str):
        if not tag:
            return ""
        
        selector = tag.select_one(css_selector)
        if not selector:
            return ""
        
        parts = selector.get_text().split("\n")
        parts = [part for part in parts if part]
        return parts[-1] # text at last element

    def _get_groups(self, section: Tag, service: str):
        tags = section.select("a[href]")
        service_relative_url = urljoin(self.SDK_RELATIVE_URL, service)
    
        # Groups name and url
        return dict(
            [
                (
                    t.get_text(strip=True),
                    t.get("href", "").replace(service_relative_url, "")
                )
                for t in tags
            ]
        )
    
    def _get_recursive_groups(self, section: Tag, service: str):
        groups_data = {}
        service_relative_url = urljoin(self.SDK_RELATIVE_URL, service)

        for tag in section.select("a[href]"):
            group_name = tag.get_text(strip=True)
            group_url = tag.get("href", "").replace(service_relative_url, "")

            if self.can_next_recursion():
                relative_recursive_url = service + group_url
                group_values = self._scrape_command_page(relative_recursive_url)
            else:
                group_values = group_url

            groups_data[group_name] = group_values

        # Groups name and url
        return groups_data

    def _extract_flags(self, tag: Tag, css_selector: str) -> Dict:
        """Extract global flags section from root reference page."""

        section_dl = tag.select_one(css_selector)
        if not section_dl:
            return {}

        flags_dict = {}
        for dt, dd in zip(section_dl.select("dt"), section_dl.select("dd")):
            flag_name = dt.get("id", "").replace("-", "")
            flag_text = dd.get_text(strip=True)
            desc_text = dd.get_text(strip=True)
            
            flags_dict[flag_name] = {
                "flag": flag_text, 
                "description": desc_text
                }
            
        return flags_dict

    # -----------------------------
    # Utilities
    # -----------------------------
    def _save_json(self, filename: str, service: str, data: Dict):
        os.makedirs(os.path.join(self.PLUGINS_DIR, service), exist_ok=True)
        path = os.path.join(self.PLUGINS_DIR, service, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        log.info(f"save-json: Saved file '{filename}' at directory '{service}'")
