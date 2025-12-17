import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, PRIMARY, SECONDARY, OUTLINE
from ui.dialogs.config import ConfigDialog

class HeaderPanel(ttk.Frame):
    def __init__(self, parent, on_tab_change, on_theme_change, on_settings_click, services: list[str]):
        super().__init__(parent)
        
        # Configuration Button (replaces Theme combo and Settings button)
        ttk.Button(
            self,
            text="⚙️ Configuración",
            bootstyle=SECONDARY,
            command=lambda: self._open_config(parent, on_theme_change, on_settings_click)
        ).pack(side="left", padx=10)

        self.notebook = ttk.Notebook(self, bootstyle=PRIMARY)
        self.notebook.pack(side="left", fill="x", expand=True, padx=20)
        for svc in services:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=svc)
        self.notebook.bind("<<NotebookTabChanged>>", on_tab_change)

    def _open_config(self, parent, on_theme_change, on_open_defaults):
        ConfigDialog(parent, on_theme_change, on_open_defaults)
