# ui/main_window.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ui.panels import HeaderPanel
from ui.panels import ActionsPanel
from ui.panels import ParamsPanel
from ui.panels import OutputPanel
from ui.panels import ExecutionPanel
from ui.panels import SequencePanel

from backend.services.base_service import BaseGCloudService


class MainWindow(ttk.Window):
    def __init__(self, container):
        super().__init__(themename="flatly")
        self.container = container
        self.title("Generador gcloud")
        self.geometry("1100x700")

        # Estado actual
        self.current_service_name = None
        self.current_service: BaseGCloudService = None
        self.selected_action = None
        self.selected_resource = None
        self.selected_category = None
        self.selected_cmd = None
        self.selected_params = None

        # --- Header ---
        self.header = HeaderPanel(
            self,
            on_tab_change=self.on_tab_change,
            on_theme_change=self.on_theme_change,
            services=container.list_services()
        )
        self.header.pack(side="top", fill="x", padx=10, pady=5)

        # --- Panel principal (izq/der) ---
        self.main_pane = ttk.Panedwindow(self, orient=HORIZONTAL)
        self.main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # Panel izquierdo (acciones)
        self.actions_panel = ActionsPanel(self.main_pane, self.on_action_select)
        self.main_pane.add(self.actions_panel, weight=1)

        # Panel derecho (params + output + exec + sequence)
        self.right_frame = ttk.Frame(self.main_pane, padding=10)
        self.main_pane.add(self.right_frame, weight=3)

        self.params_panel = ParamsPanel(self.right_frame, self.on_params_change)
        self.output_panel = OutputPanel(self.right_frame)

        # Botón externo que conecta OutputPanel -> SequencePanel
        ttk.Button(
            self.right_frame,
            text="➕ Añadir a secuencia",
            bootstyle="success",
            command=self.add_to_sequence_from_output
        ).pack(anchor="w", pady=5)

        self.sequence_panel = SequencePanel(self.right_frame)
        self.sequence_panel.pack(fill="both", expand=True, pady=5)
        self.execution_panel = ExecutionPanel(self.right_frame, self.execute_command)

        # Atajos teclado
        self.bind("<Control-g>", lambda e: self.generate_command())
        self.bind("<Return>", lambda e: self.generate_command())
        self.bind("<Escape>", lambda e: self.focus_set())

        # Inicializar con primer servicio
        if container.list_services():
            first = container.list_services()[0]
            self.set_service(first)

    # --------------------
    # Callbacks de UI
    # --------------------
    def on_tab_change(self, event):
        tab_id = self.header.notebook.select()
        tab_text = self.header.notebook.tab(tab_id, "text")
        self.set_service(tab_text)

    def on_theme_change(self, event):
        nuevo_tema = self.header.combo_theme.get()
        self.style.theme_use(nuevo_tema)

    def on_params_change(self, values: dict):
        """Callback cuando cambian parámetros en ParamsPanel."""
        self.generate_command(values)

    def on_action_select(self, action: str, resource: str, category: str):
        self.selected_action = action
        self.selected_resource = resource
        self.selected_category = category

        action_def = self.current_service.get_action_def(resource, category, action)
        if not action_def:
            return

        self.selected_cmd = action_def["cmd"]
        self.selected_params = action_def["params"]

        params_def = {
            p: self.current_service.parameters.get(p, f"<{p}>")
            for p in self.selected_params
        }
        self.params_panel.show_params(action, params_def)
        self.generate_command()


    # --------------------
    # Lógica
    # --------------------
    def set_service(self, service_name: str):
        self.current_service_name = service_name
        self.current_service = self.container.get(service_name)

        # Título acciones
        self.actions_panel.lbl.config(text=f"Acciones de {service_name.capitalize()}")

        # Refrescar árbol
        self.actions_panel.refresh(self.current_service.actions)

    def generate_command(self, values: dict = None):
        if not self.selected_action or not self.selected_cmd:
            self.output_panel.set_command("⚠️ Selecciona primero una acción en el árbol")
            return

        params = values or self.params_panel.get_values()
        cmd = self.current_service.build_command(self.selected_cmd, params)
        self.output_panel.set_command(cmd)

    def execute_command(self):
        cmd = self.output_panel.get_command()
        if not cmd:
            return "⚠️ No hay comando para ejecutar"
        return self.current_service.execute(cmd)

    def add_to_sequence_from_output(self):
        cmd = self.output_panel.get_command().strip()
        if cmd:
            self.sequence_panel.add_command(cmd)