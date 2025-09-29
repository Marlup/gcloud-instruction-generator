# backend/services/knowledge_updater.py

from typing import Dict, List
from dataclasses import dataclass, asdict

@dataclass
class ServiceCommand:
    service_name: str
    service_url: str
    description: str
    command_synopsis: str
    sha256_sign: str
    positional_args: List[str]
    required_flags: List[str]
    base_groups: List[str]
    base_commands: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)