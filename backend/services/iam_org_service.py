from typing import Any, Dict, List
import subprocess
from google.api_core.exceptions import NotFound, PermissionDenied

from google.cloud import (
    iam_admin_v1,
    iam_credentials_v1,
    iam_v3,
    resourcemanager_v3
)


from backend.infrastructure.exporters import to_shell, to_terraform, to_yaml
from backend.services.base_service import BaseGCloudService
from backend.core.types.enums import ExportFileFormat, GCPResource, GCPService, IAMPurpose
from backend.infrastructure.configuration_manager import ConfigurationManager

from enum import Enum

__all__ = ["IamOrgService", "IAMPurpose"]

class IamOrgService(BaseGCloudService):
    """
    Implementación concreta del servicio GCP IAM y Organization.
    Basada en BaseGCloudService.
    """

    service_name = GCPService.IAM_ORG

    def __init__(self, configuration: ConfigurationManager, on_concat_project_id: bool=False):
        self.configuration = configuration
        self.on_concat_project_id = on_concat_project_id
        self.actions = configuration.load_actions(self.service_name)
        self.parameters = configuration.load_parameters(self.service_name)

    def get_client(self, purpose: IAMPurpose):
        """
        Devuelve un cliente IAM según el propósito.
        """
        if purpose == IAMPurpose.ADMIN:
            return iam_admin_v1.IAMClient(credentials=self.configuration.client._credentials)
        elif purpose == IAMPurpose.CREDENTIALS:
            return iam_credentials_v1.IAMCredentialsClient(credentials=self.configuration.client._credentials)
        elif purpose == IAMPurpose.POLICIES:
            return iam_v3.PoliciesClient(credentials=self.configuration.client._credentials)
        elif purpose == IAMPurpose.RESOURCES:
            return resourcemanager_v3.ProjectsClient(credentials=self.configuration.client._credentials)
        else:
            raise ValueError(f"Propósito IAM no soportado: {purpose}")

    # -----------------------------
    # Implementación de la interfaz base
    # -----------------------------
    def validate(self, resource: str, **kwargs) -> bool:
        # TODO: implementar validación real IAM (ej. lookup policy)
        return True
    
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

    def list_actions(self) -> List[str]:
        actions = []
        for category, subcats in self.actions.items():
            for subcat, acts in subcats.items():
                actions.extend(acts.keys())
        return actions

    def ping(self) -> bool:
        return True  # TODO: implementar un test real (ej. listar policies)

    def execute(self, command: str) -> str:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"❌ Error:\n{result.stderr.strip()}"
        except Exception as e:
            return f"⚠️ Excepción ejecutando comando: {e}"

    # ========== Service Accounts ==========
    def service_account_exists(self, project_id: str, sa_email: str) -> bool:
        """
        Verifica si una service account existe en el proyecto.
        sa_email → formato: my-sa@project-id.iam.gserviceaccount.com
        """
        client = self.get_client(IAMPurpose.ADMIN)
        name = f"projects/{project_id}/serviceAccounts/{sa_email}"
        try:
            client.get_service_account(name=name)
            return True
        except NotFound:
            return False
    
    def role_exists(self, role_name: str) -> bool:
        """
        Verifica si un rol existe.
        role_name → 'roles/viewer' (predefinido) o 'projects/<project>/roles/<custom>'
        """
        try:
            self.get_client(IAMPurpose.ADMIN).get_role(name=role_name)
            return True
        except NotFound:
            return False
    
    def is_binding_duplicate(project_id: str, member: str, role: str) -> bool:
        """
        Comprueba si un binding IAM ya existe en la política del proyecto.
        """
        client = resourcemanager_v3.ProjectsClient()
        policy = client.get_iam_policy(resource=f"projects/{project_id}")
        for binding in policy.bindings:
            if binding.role == role and member in binding.members:
                return True
        return False

    # ========== ✅ Permisos efectivos ==========
    def test_permissions_on_project(self, project_id: str, permissions: list[str]) -> dict[str, bool]:
        """
        Ejecuta testIamPermissions sobre un proyecto.
        Devuelve un dict con permiso → True/False
        """
        resource = f"projects/{project_id}"
        try:
            response = self.get_client(IAMPurpose.RESOURCES).test_iam_permissions(
                request={"resource": resource, "permissions": permissions}
            )
            allowed = set(response.permissions)
            return {p: p in allowed for p in permissions}
        except PermissionDenied:
            return {p: False for p in permissions}