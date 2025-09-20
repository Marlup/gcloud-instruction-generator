from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseGCloudService():
    """
    Interfaz base para todos los servicios gcloud.
    Define los métodos mínimos que cada servicio debe implementar.
    """

    def __init__(self):
        self.actions: Dict = {}
        self.parameters: Dict = {}
        self.on_concat_project_id = False

    # Validaciones en vivo
    # -----------------------------
    @abstractmethod
    def validate(self, resource: str, **kwargs) -> bool:
        """
        Verifica si un recurso existe o es válido en GCP.
        - resource: nombre del recurso principal (bucket, dataset, topic, etc.)
        - kwargs: parámetros adicionales (ej. objeto dentro de bucket)
        """
        pass

    # -----------------------------
    # Generación de comandos
    # -----------------------------
    @abstractmethod
    def build_command(self, base_command: str, params: Dict[str, Any]) -> str:
        """
        Construye un comando a partir de una plantilla y parámetros.
        - template: str con placeholders {param}
        - params: dict con los valores a insertar
        """
        command_params = params.copy()
        if self.on_concat_project_id and "project" not in command_params:
            command_params["project"] = self.configuration.project

        command = base_command + "".format(**command_params)
        return command.format(**command_params)

    # -----------------------------
    # Exportación IaC
    # -----------------------------
    @abstractmethod
    def export(self, format: str, config: Dict[str, Any]) -> str:
        """
        Exporta una configuración a distintos formatos (shell, terraform, yaml).
        - format: "shell" | "terraform" | "yaml".
        - config: diccionario con la configuración del recurso.
        """
        pass

    # -----------------------------
    # Explicaciones educativas
    # -----------------------------
    @abstractmethod
    def explain(self, action: str) -> str:
        """
        Devuelve una explicación en texto del comando/acción.
        - action: nombre de la acción.
        """
        pass

    # -----------------------------
    # Listado de acciones soportadas
    # -----------------------------
    @abstractmethod
    def list_actions(self, on_categories: bool = True) -> List[str] | Dict[str, List[str]]:
        """
        Devuelve una lista de acciones soportadas por el servicio.
        Ejemplo: ["Crear bucket", "Listar buckets", "Borrar bucket"]
        """
        if on_categories:
            result = {}
        else:
            result = []
        for category, subcats in self.actions.items():
            if on_categories:
                actions_by_subcat = {}
            for subcat, actions in subcats.items():
                if on_categories:
                    actions_by_subcat[subcat] = list(actions.keys())
                else:
                    result.extend(actions.keys())
            if on_categories:
                result[category] = actions_by_subcat
        return result

    # -----------------------------
    # Comprobación de conectividad
    # -----------------------------
    @abstractmethod
    def ping(self) -> bool:
        """
        Devuelve true si el ping a Google Cloud Console fue exitoso.
        """
        pass

    # -----------------------------
    # Ejecución directa
    # -----------------------------
    @abstractmethod
    def execute(self, command: str) -> str:
        """
        Ejecuta un comando gcloud completo en el sistema.
        - command: string del comando ya construido.
        - return: salida stdout o stderr.
        """
        pass


    # -----------------------------
    # Ejecución directa
    # -----------------------------
    @abstractmethod
    def reset_client(self) -> str:
        """
        Initialize the client.
        """
        pass
    
    @abstractmethod
    def get_action_def(self, category: str, subcategory: str, action: str) -> Dict[str, Any]:
        """
        Devuelve la definición de una acción concreta (cmd y params).
        - category: nombre de la categoría (ej. 'Buckets')
        - subcategory: nombre de la subcategoría (ej. '📤 Creación')
        - action: nombre de la acción (ej. 'Crear bucket')
        """
        #print(f"self.actions[category][subcategory] -> {self.actions}")
        try:
            return self.actions[category][subcategory][action]
        except KeyError as e:
            raise ValueError(f"Acción no encontrada: {category} > {subcategory} > {action}") from e