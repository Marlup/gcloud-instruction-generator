import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class ConfigDialog(ttk.Toplevel):
    """Main configuration dialog."""
    
    def __init__(self, parent, on_theme_change, on_open_defaults):
        super().__init__(parent)
        self.title("Configuración")
        self.geometry("300x300")
        self.resizable(False, False)
        
        # Center the dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (300 // 2)
        y = (self.winfo_screenheight() // 2) - (300 // 2)
        self.geometry(f"+{x}+{y}")
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Container
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(
            frame, 
            text="Configuración", 
            font=("Segoe UI", 12, "bold"),
            bootstyle=INFO
        ).pack(pady=(0, 20))
        
        # Theme Selection Group
        theme_frame = ttk.LabelFrame(frame, text="Tema", padding=10)
        theme_frame.pack(fill="x", pady=10)
        
        self.combo_theme = ttk.Combobox(
            theme_frame, 
            values=parent.style.theme_names(),
            state="readonly", 
            bootstyle=PRIMARY
        )
        self.combo_theme.set(parent.style.theme_use())
        self.combo_theme.pack(fill="x")
        
        # Bind theme change
        def _on_theme_select(event):
            on_theme_change(event)
            # Update local reference if needed
        self.combo_theme.bind("<<ComboboxSelected>>", _on_theme_select)
        
        # Default Params Button
        ttk.Button(
            frame,
            text="⚙️ Valores por defecto",
            bootstyle=OUTLINE,
            command=lambda: [self.destroy(), on_open_defaults()]
        ).pack(fill="x", pady=10)
        
        # Close
        ttk.Button(
            frame,
            text="Cerrar",
            bootstyle=SECONDARY,
            command=self.destroy
        ).pack(side="bottom", fill="x")


class SettingsDialog(ttk.Toplevel):
    """Dialog to set default values for project_id, region, and location."""
    
    def __init__(self, parent, current_defaults: dict, on_save):
        super().__init__(parent)
        
        self.on_save = on_save
        self.result = None
        
        self.title("Configuración por defecto")
        self.geometry("550x450")  # Increased height to ensure buttons are visible
        self.resizable(False, False)
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (550 // 2)
        y = (self.winfo_screenheight() // 2) - (450 // 2)
        self.geometry(f"+{x}+{y}")
        
        # Main frame with scrollbar support
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        ttk.Label(
            main_frame,
            text="Configuración de Parámetros por Defecto",
            font=("Segoe UI", 14, "bold"),
            bootstyle=INFO
        ).pack(pady=(0, 10))
        
        # Description
        ttk.Label(
            main_frame,
            text="Estos valores se usarán automáticamente en todos los comandos cuando apliquen:",
            wraplength=500
        ).pack(pady=(0, 20))
        
        # Input fields frame
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill="both", expand=False, pady=(0, 10))
        
        # Input fields
        self.entries = {}
        
        # Project ID
        self._create_field(
            fields_frame,
            "Project ID:",
            "project_id",
            current_defaults.get("project_id", ""),
            "Ej: my-gcp-project"
        )
        
        # Region
        self._create_field(
            fields_frame,
            "Region:",
            "region",
            current_defaults.get("region", ""),
            "Ej: us-central1"
        )
        
        # Location
        self._create_field(
            fields_frame,
            "Location:",
            "location",
            current_defaults.get("location", ""),
            "Ej: us"
        )
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # Buttons frame - ensure it's always visible
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        # Save button
        save_btn = ttk.Button(
            btn_frame,
            text="💾 Guardar (Enter)",
            bootstyle=SUCCESS,
            command=self._save_and_close,
            width=20
        )
        save_btn.pack(side="left", padx=5, expand=True, fill="x")
        
        # Cancel button
        cancel_btn = ttk.Button(
            btn_frame,
            text="❌ Cancelar (Esc)",
            bootstyle=DANGER,
            command=self._cancel_and_close,
            width=20
        )
        cancel_btn.pack(side="left", padx=5, expand=True, fill="x")
        
        # Keyboard shortcuts
        self.bind("<Return>", lambda e: self._save_and_close())
        self.bind("<Escape>", lambda e: self._cancel_and_close())
    
    def _create_field(self, parent, label_text, field_name, default_value, placeholder):
        """Create a labeled input field."""
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5)
        
        ttk.Label(row, text=label_text, width=12).pack(side="left", padx=(0, 10))
        
        entry = ttk.Entry(row, bootstyle=PRIMARY)
        entry.insert(0, default_value)
        entry.pack(side="left", fill="x", expand=True)
        
        # Placeholder label
        ttk.Label(row, text=placeholder, font=("Segoe UI", 8), foreground="gray").pack(side="left", padx=(10, 0))
        
        self.entries[field_name] = entry
    
    def _save_and_close(self):
        """Save the values and close the dialog."""
        self.result = {
            key: entry.get().strip()
            for key, entry in self.entries.items()
        }
        
        if self.on_save:
            self.on_save(self.result)
        
        self.destroy()
    
    def _cancel_and_close(self):
        """Cancel and close the dialog without saving."""
        self.result = None
        self.destroy()
