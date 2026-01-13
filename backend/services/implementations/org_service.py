from typing import Any, Dict, List
import subprocess

from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService, IAMPurpose
from backend.infrastructure.configuration_manager import ConfigurationManager

from enum import Enum

__all__ = ["OrganizationsService", "IAMPurpose"]

class OrganizationsService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP Organization.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.ORGANIZATIONS
    def __init__(self, configuration: ConfigurationManager, on_reset_client=False , on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)

    def export(self, format: ExportFileFormat, config: Dict[str, Any]) -> str:
        if format == ExportFileFormat.SHELL:
            return to_shell([self.build_command("Ver IAM", config)])
        elif format == ExportFileFormat.TERRAFORM:
            return to_terraform(config)
        elif format == ExportFileFormat.YAML:
            return to_yaml(config)
        else:
            raise ValueError(f"Formato no soportado: {format}")

    def explain(self, action: str) -> str:
        explanations = {
            "Ver IAM": "Obtiene la política IAM de un recurso de organización, proyecto o carpeta.",
            "Asignar rol": "Añade un binding de rol a un miembro en la política IAM."
        }
        return explanations.get(action, "Explicación no disponible aún.")

    def load_actions(self) -> List[str]:
        actions = []
        for category, subcats in self.actions.items():
            for subcat, acts in subcats.items():
                actions.extend(acts.keys())
        return actions
