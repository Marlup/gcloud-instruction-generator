# backend/services/knowledge_updater.py

import os
import json
import hashlib
import requests
from urllib.parse import urljoin
from backend.core.types.enums import UpdateMode
from backend.core.types.entities import ServiceCommand
from typing import Dict, List, Union, Optional
from bs4 import BeautifulSoup, Tag  # pip install beautifulsoup4
import logging
from .utils import get_duration

logger = logging.getLogger(__name__)

class GCPKnowledgeUpdater():
    BASE_URL = "https://cloud.google.com/sdk/gcloud/reference"
    SDK_RELATIVE_URL = "/sdk/gcloud/reference/"
    PLUGINS_DIR = "data/plugins"
    DATA_DIR = "data/web-gcloud"

    def __init__(self, recursion_level_limit: int=1):
        self.recursion_level_limit = recursion_level_limit
        self.reset_recursion()
        self.unprocessed_parts = []
        
        # Make directories
        os.makedirs(self.DATA_DIR, exist_ok=True)
    def reset_unprocessed(self):
        self.unprocessed_parts = []
    def reset_recursion(self):
        self.recursion_level = 0
        self.continue_recursion = True
    def commit_recursion(self):
        self.recursion_level += 1

        #logging.info(f"Going UP to level '{self.recursion_level}'")
    def uncommit_recursion(self):
        self.recursion_level -= 1

        #logging.info(f"Going DOWN to level '{self.recursion_level}\n'")
    def can_next_recursion(self):
        if self.recursion_level < self.recursion_level_limit:
            self.commit_recursion()
        else:
            self.reset_recursion()
            #logging.info(f"Blocked next recursion: level limit reached '{self.recursion_level_limit}'. Going down to level '{self.recursion_level}'\n")
        
        return self.continue_recursion
    # ==================
    # Public entrypoint
    # ==================
    def run_update(
        self,
        mode: UpdateMode,
        target_services: Optional[Union[str, List[str]]] = None
    ):
        logging.info(f"Starting. Mode: '{mode.value}'. Target: {str(target_services)}\\n")
        
        if mode == UpdateMode.FULL:
            self._update_all_services()
        elif mode == UpdateMode.PARTIAL:
            if not target_services:
                raise ValueError("PARTIAL update requires target_services as list/tuple of commands.")
            self._update_services(target_services)
        elif mode == UpdateMode.SINGLE:
            if not target_services:
                raise ValueError("SINGLE update requires target_services as string or list of length 1.")
            if isinstance(target_services, (list, tuple)):
                if len(target_services) != 1:
                    raise ValueError("SINGLE update requires exactly one command.")
                target_services = target_services[0]
            self._update_single(target_services)
        elif mode == UpdateMode.PATCH:
            self._patch_unprocessed(target_services)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
    # ==================
    # Private helpers
    # ==================
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

            commands_data[service] = self._try_scrape_command_page(service)

        # Serialize to JSON
        print("Scraping relative urls\n---------------------")
        for k, v in commands_data.items():
            filename = f"{service}_command.json"
            self._save_service_json(filename, k, {k, v.to_dict()})

        # common tag element
        article = soup.find("article") # .devsite-article

        # Extract global and other flags
        global_flags = self._extract_flags(article, "section[id='GLOBAL-FLAGS'] dl")
        filename = "global_flags.json"
        self._save_service_json(filename, "", global_flags)

        other_flags = self._extract_flags(article, "section[id='OTHER-FLAGS'] dl")
        filename = "other_flags.json"
        self._save_service_json(filename, "", other_flags)

        return {k: v.to_dict() for k, v in commands_data.items()}
    def _update_services(self, services: List[str]) -> Dict[str, Dict]:
        """Fetch and parse only a list of services."""
        for svc in services:
            self._update_single(svc)
    @get_duration
    def _patch_unprocessed(self, target_services: Optional[Union[str, List[str]]] = None):
        """Process unscraped entities from unprocessed.json files in data directories."""
        logging.info("Starting PATCH mode to process unscraped entities")
        
        # Get list of services to patch
        if target_services:
            if isinstance(target_services, str):
                services_to_patch = [target_services]
            else:
                services_to_patch = target_services
        else:
            # Get all directories in DATA_DIR that have unprocessed.json
            services_to_patch = []
            if os.path.exists(self.DATA_DIR):
                for item in os.listdir(self.DATA_DIR):
                    item_path = os.path.join(self.DATA_DIR, item)
                    if os.path.isdir(item_path):
                        unprocessed_path = os.path.join(item_path, "unprocessed.json")
                        if os.path.exists(unprocessed_path):
                            services_to_patch.append(item)
        
        logging.info(f"Services to patch: {services_to_patch}")
        
        # Process each service
        for service in services_to_patch:
            self._patch_service_unprocessed(service)
    
    def _patch_service_unprocessed(self, service: str):
        """Process unprocessed entities for a specific service."""
        unprocessed_path = os.path.join(self.DATA_DIR, service, "unprocessed.json")
        
        if not os.path.exists(unprocessed_path):
            logging.info(f"No unprocessed.json found for service '{service}'")
            return
        
        # Read unprocessed entities
        try:
            with open(unprocessed_path, "r", encoding="utf-8") as f:
                unprocessed_entities = json.load(f)
                if not isinstance(unprocessed_entities, list):
                    unprocessed_entities = [unprocessed_entities]
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Failed to read unprocessed.json for '{service}': {e}")
            return
        
        if not unprocessed_entities:
            logging.info(f"No unprocessed entities found for service '{service}'")
            return
        
        logging.info(f"Processing {len(unprocessed_entities)} unprocessed entities for service '{service}'")
        
        # Read existing service data
        service_json_path = os.path.join(self.DATA_DIR, service, f"{service}_command.json")
        existing_data = {}
        if os.path.exists(service_json_path):
            try:
                with open(service_json_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                logging.error(f"Failed to read existing data for '{service}': {e}")
        
        # Process each unprocessed entity
        successfully_processed = []
        still_unprocessed = []
        
        for entity in unprocessed_entities:
            group_name = entity.get("group_name", "")
            url = entity.get("url", "")
            
            if not url:
                logging.warning(f"Skipping entity with no URL: {entity}")
                still_unprocessed.append(entity)
                continue
            
            # Extract the relative path from the URL
            relative_path = url.replace(f"{self.BASE_URL}/", "")
            
            try:
                # Try to scrape the entity
                scraped_data = self._try_scrape_command_page(relative_path)
                
                if scraped_data:
                    # Successfully scraped, merge into existing data
                    if not existing_data:
                        existing_data = {}
                    
                    # Update the appropriate section (base_groups or base_commands)
                    # This is simplified - you may need to adjust based on your data structure
                    logging.info(f"Successfully scraped: {group_name} ({url})")
                    successfully_processed.append(entity)
                else:
                    logging.warning(f"Failed to scrape: {group_name} ({url})")
                    still_unprocessed.append(entity)
            except Exception as e:
                logging.error(f"Error scraping {group_name} ({url}): {e}")
                still_unprocessed.append(entity)
        
        # Save updated service data if we processed anything
        if successfully_processed:
            logging.info(f"Successfully processed {len(successfully_processed)} entities for '{service}'")
            # Note: The data is already saved in _try_scrape_command_page flow
        
        # Update unprocessed.json with entities that still failed
        if still_unprocessed:
            logging.info(f"Still {len(still_unprocessed)} unprocessed entities for '{service}'")
            with open(unprocessed_path, "w", encoding="utf-8") as f:
                json.dump(still_unprocessed, f, indent=2, ensure_ascii=False)
        else:
            # All entities processed successfully, remove unprocessed.json
            logging.info(f"All unprocessed entities resolved for '{service}', removing unprocessed.json")
            os.remove(unprocessed_path)
    @get_duration
    def _update_single(self, service: str) -> Dict[str, Dict]:
        """Fetch and parse a single service."""
        service_data = self._try_scrape_command_page(service).to_dict()
        filename = f"{service}_command.json"
        self._save_service_json(filename, service, service_data)
    def _try_scrape_command_page(self, service: str) -> ServiceCommand:
        url = f"{self.BASE_URL}/{service}"

        try:
            return self._scrape_command_page(service, url)
        except Exception as e:
            logging.info(f"_try_scrape_command_page. Exception at url : '{url}'. Reason : '{e}' ")
            return None
    def _scrape_command_page(self, service: str, url: str) -> ServiceCommand:
        """Scrape details of a single gcloud service page."""
        logging.info(f"scrap-command: {url}")

        resp = requests.get(url)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        article = soup.find("article") # .devsite-article

        # Synopsis
        synopsis = self._get_key_text(article, "section[id='SYNOPSIS']")
        
        # Long description
        desc = self._get_key_text(article, "section[id='DESCRIPTION']")
        
        # Commands
        data_cmds = self._get_recursive_groups(article, "section[id='COMMAND']", service)
        
        # Groups
        data_groups = self._get_recursive_groups(article, "section[id='GROUP']", service)

        # Positional arguments
        # - Tag 'dl' with 'class' attr. contains all the 'dl', 'dd' and 'dt' tags for the flags and arguments
        positional_args = self._extract_flags(article, "section[id='POSITIONAL-ARGUMENTS'] dl[class]")
        
        # Required flags
        required_flags = self._extract_flags(article, "section[id='REQUIRED-FLAGS'] dl[class]")

        # Optional flags
        optional_flags = self._extract_flags(article, "section[id='OPTIONAL-FLAGS'] dl[class]")
        
        # General flags (FLAGS or LIST-COMMAND-FLAGS)
        flags = self._extract_flags(article, "section[id='FLAGS'] dl[class]")
        if not flags:
             flags = self._extract_flags(article, "section[id='LIST-COMMAND-FLAGS'] dl[class]")
        
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
            optional_flags=optional_flags,
            flags=flags,
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
        return "\n".join(parts[1:]) # text located after the first element
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
    def _get_recursive_groups(self, tag: Tag, css_selector: str, service: str):
        groups_data = {}
        service_relative_url = urljoin(self.SDK_RELATIVE_URL, service)
        if not tag:
            return {}
        
        section = tag.select_one(css_selector)

        if not section:
            return {}

        for tag in section.select("a[href]"):
            group_name = tag.get_text(strip=True)
            group_url = tag.get("href", "").replace(service_relative_url, "")

            if self.can_next_recursion():
                relative_recursive_url = service + group_url

                group_values = self._try_scrape_command_page(relative_recursive_url)
            else:
                group_values = group_url
            
            if not group_values:
                self._register_unprocessed_groups(
                    {
                        "service_name": service.split("/")[0],
                        "group_name": group_name,
                        "url": f"{self.BASE_URL}/{relative_recursive_url}"
                    }
                    )

            groups_data[group_name] = group_values

        # Groups name and url
        return groups_data
    def _extract_flags(self, tag: Tag, css_selector: str) -> Dict:
        """Extract global flags section from root reference page."""

        if not tag:
            return {}

        # The first tag contains the tags related to each flag
        section_dl = tag.select_one(css_selector)
        if not section_dl:
            return {}

        flags_dict = {}
        # Tag 'dd' contains descriptions; 'dt' the actual flag or argument
        #for dt, dd in zip(section_dl.select("dt[id^='--']"), section_dl.select("dd")):
        #for dt in section_dl.select("dt[id^='--']"):
        for dt in section_dl.find("dt", id=True):
            dd = dt.find_next_sibling('dd')
            flag_raw_name = dt.get("id", "")
            if not flag_raw_name:
                continue
            
            flag_name = flag_raw_name.replace("--", "")
            flag_content = dt.get_text(strip=True)
            flag_desc = dd.get_text(strip=True)
            
            flags_dict[flag_name] = {
                "content": flag_content, 
                "description": flag_desc
                }
            
        return flags_dict
    # ==================
    # Utilities
    # ==================
    def _save_service_json(self, filename: str, service: str, data: Dict):
        os.makedirs(os.path.join(self.DATA_DIR, service), exist_ok=True)
        path = os.path.join(self.DATA_DIR, service, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self._write_unprocessed(service)

        logging.info(f"save-json: Saved file '{filename}' at directory '{service}', path '{path}'")
    def _register_unprocessed_groups(self, group_detail: Dict[str, str]):
        self.unprocessed_parts.append(group_detail)
    def _write_unprocessed(self, service: str):
        path = os.path.join(self.DATA_DIR, service, "unprocessed.json")
        if not self.unprocessed_parts:
            return
        
        # Read existing unprocessed items if file exists
        existing_items = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing_items = json.load(f)
                    if not isinstance(existing_items, list):
                        existing_items = [existing_items]
            except (json.JSONDecodeError, ValueError):
                # If file is corrupted or invalid JSON, start fresh
                existing_items = []
        
        # Append new unprocessed items
        existing_items.extend(self.unprocessed_parts)
        
        # Write the complete list
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing_items, f, indent=2, ensure_ascii=False)
        
        self.unprocessed_parts = []
