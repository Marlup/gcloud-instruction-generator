# ui/main_window.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ui.components import HeaderPanel
from ui.components import ActionsTreePanel
from ui.components import ParamsPanel
from ui.components import OutputPanel
from ui.components import ExecutionPanel
from ui.components import SequencePanel
from ui.dialogs.config import SettingsDialog
from ui.config.config import current_theme, config_manager

from backend.services.base_service import BaseGCloudService

import threading
from queue import Queue
from typing import Optional


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
        
        # Service loading state
        self.services_loaded = {}  # Track which services are loaded
        self.loading_queue = Queue()
        self.is_loading = False
        
        # Default parameters (project_id, region, location)
        # Load saved defaults asynchronously
        self.default_params = {}
        self._load_config_async()

        # --- Header ---
        self.header = HeaderPanel(
            self,
            on_tab_change=self.on_tab_change,
            on_theme_change=self.on_theme_change,
            on_settings_click=self.open_settings_dialog,
            services=container.list_services()
        )
        self.header.pack(side="top", fill="x", padx=10, pady=5)

        # --- Panel principal (izq/der) ---
        self.main_pane = ttk.Panedwindow(self, orient=HORIZONTAL)
        self.main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # Panel izquierdo (acciones)
        self.actions_tree_panel = ActionsTreePanel(self.main_pane, self.on_action_select)
        self.main_pane.add(self.actions_tree_panel, weight=1)

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

        # Loading indicator
        self.loading_label = ttk.Label(
            self.actions_tree_panel,
            text="⏳ Cargando...",
            font=("Segoe UI", 10, "italic"),
            bootstyle=INFO
        )

        # Atajos teclado
        self.bind("<Control-g>", lambda e: self.generate_command())
        self.bind("<Return>", lambda e: self.generate_command())
        self.bind("<Escape>", lambda e: self.focus_set())

        # Inicializar con primer servicio (async)
        if container.list_services():
            first = container.list_services()[0]
            self._load_service_async(first)

    # --------------------
    # Async Loading Methods
    # --------------------
    def _load_config_async(self):
        """Load configuration asynchronously."""
        def load_config():
            try:
                defaults = config_manager.load_default_params()
                # Schedule UI update on main thread
                self.after(0, lambda: self._on_config_loaded(defaults))
            except Exception as e:
                print(f"Error loading config: {e}")
                self.after(0, lambda: self._on_config_loaded({}))
        
        thread = threading.Thread(target=load_config, daemon=True)
        thread.start()
    
    def _on_config_loaded(self, defaults: dict):
        """Called when config is loaded (runs on main thread)."""
        self.default_params = defaults
    
    def _load_service_async(self, service_name: str):
        """Load a service asynchronously."""
        if service_name in self.services_loaded:
            # Service already loaded, just set it
            self.set_service(service_name)
            return
        
        # Show loading indicator
        self.is_loading = True
        self.loading_label.pack(pady=10)
        self.actions_tree_panel.header_label.config(
            text=f"⏳ Cargando {service_name}..."
        )
        
        def load_service():
            try:
                # Load service (this may take time)
                service = self.container.get(service_name)
                # Mark as loaded
                self.services_loaded[service_name] = True
                # Schedule UI update on main thread
                self.after(0, lambda: self._on_service_loaded(service_name, service))
            except Exception as e:
                print(f"Error loading service {service_name}: {e}")
                self.after(0, lambda: self._on_service_load_error(service_name, str(e)))
        
        thread = threading.Thread(target=load_service, daemon=True)
        thread.start()
    
    def _on_service_loaded(self, service_name: str, service: BaseGCloudService):
        """Called when a service finishes loading (runs on main thread)."""
        # Hide loading indicator
        self.loading_label.pack_forget()
        self.is_loading = False
        
        # Update current service
        self.current_service_name = service_name
        self.current_service = service
        
        # Update UI
        self.actions_tree_panel.header_label.config(
            text=f"Acciones de {service_name.capitalize()}"
        )
        self.actions_tree_panel.refresh(service.actions)
    
    def _on_service_load_error(self, service_name: str, error: str):
        """Called when service loading fails (runs on main thread)."""
        # Hide loading indicator
        self.loading_label.pack_forget()
        self.is_loading = False
        
        # Show error
        self.actions_tree_panel.header_label.config(
            text=f"❌ Error cargando {service_name}"
        )
        self._show_flash_message(f"Error: {error}", DANGER)

    # --------------------
    # Callbacks de UI
    # --------------------
    def on_tab_change(self, event):
        tab_id = self.header.notebook.select()
        tab_text = self.header.notebook.tab(tab_id, "text")
        self._load_service_async(tab_text)  # Use async loading

    def on_theme_change(self, event):
        new_theme = event.widget.get()
        current_theme = new_theme
        self.style.theme_use(current_theme)

    def on_params_change(self, values: tuple):
        """Callback cuando cambian parámetros en ParamsPanel."""
        self.generate_command(values)

    def on_action_select(self, action: str, resource: str, category: str):
        self.selected_action = action
        self.selected_resource = resource
        self.selected_category = category

        if isinstance(action, dict):
            # If action is already a dict (the definition), use it
            action_def = action
        else:
            # Legacy lookup
            action_def = self.current_service.get_action_def(resource, category, action)

        if not action_def:
            return

        self.selected_cmd = action_def["cmd"]
        self.selected_params = action_def["params"]

        params_def = {
            p: self.current_service.parameters.get(p, f"<{p}>")
            for p in self.selected_params
        }
        
        flags = action_def.get("flags", [])
        self.params_panel.show_params(action, params_def, flags=flags)
        
        self.generate_command()


    # --------------------
    # Lógica
    # --------------------
    def set_service(self, service_name: str):
        self.current_service_name = service_name
        self.current_service = self.container.get(service_name)

        # Título acciones
        self.actions_tree_panel.header_label.config(text=f"Acciones de {service_name.capitalize()}")

        # Refrescar árbol
        self.actions_tree_panel.refresh(self.current_service.actions)

    def generate_command(self, values: tuple = None):
        if not self.selected_action or not self.selected_cmd:
            self.output_panel.set_command("⚠️ Selecciona primero una acción en el árbol")
            return

        # Get params from UI or use provided values
        if values:
            params, flags = values
        else:
            params, flags = self.params_panel.get_values()
        
        # Merge with default params: use defaults for empty or placeholder values
        merged_params = params.copy()
        for key, default_value in self.default_params.items():
            if default_value:  # Only apply if default is not empty
                # Check if param exists and is empty or still a placeholder
                if key in merged_params:
                    param_value = merged_params[key]
                    if not param_value or param_value.startswith("<"):
                        merged_params[key] = default_value
                else:
                    # Add default if param doesn't exist
                    merged_params[key] = default_value
        
        cmd = self.current_service.build_command(self.selected_cmd, merged_params)
        
        # Append optional flags
        if flags:
            cmd += " " + " ".join(flags)
            
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
    
    def open_settings_dialog(self):
        """Open the settings dialog to configure default parameters."""
        dialog = SettingsDialog(
            self,
            current_defaults=self.default_params,
            on_save=self.on_settings_save
        )
        # Wait for dialog to close
        self.wait_window(dialog)
    
    def on_settings_save(self, new_defaults: dict):
        """Callback when settings are saved."""
        # Update in-memory defaults immediately
        self.default_params.update(new_defaults)
        
        # Save to file asynchronously
        def save_config():
            try:
                success = config_manager.save_default_params(self.default_params)
                # Schedule UI update on main thread
                self.after(0, lambda: self._on_config_saved(success))
            except Exception as e:
                print(f"Error saving config: {e}")
                self.after(0, lambda: self._on_config_saved(False))
        
        thread = threading.Thread(target=save_config, daemon=True)
        thread.start()
        
        # Regenerate current command immediately with new defaults
        if self.selected_action and self.selected_cmd:
            self.generate_command()
    
    def _on_config_saved(self, success: bool):
        """Called when config save completes (runs on main thread)."""
        # Show feedback message
        if success:
            self._show_flash_message("✅ Configuración guardada correctamente", SUCCESS)
        else:
            self._show_flash_message("⚠️ Error al guardar la configuración", WARNING)
    
    def _show_flash_message(self, message: str, style):
        """Show a temporary flash message on the screen."""
        lbl_msg = ttk.Label(self, text=message, bootstyle=style, font=("Segoe UI", 10, "bold"))
        lbl_msg.place(relx=0.5, rely=0.95, anchor="center")
        self.after(3000, lbl_msg.destroy)