import ttkbootstrap as ttk
from ttkbootstrap.constants import PRIMARY, SECONDARY
from ttkbootstrap.scrolled import ScrolledFrame

class ParamsPanel(ttk.LabelFrame):
    def __init__(self, parent, on_param_change):
        super().__init__(parent, text="Parámetros")
        self.pack(fill="x", pady=5)  # Fixed height (scrollable), only fill horizontal

        # Create scrollable container
        self.scroll_frame = ScrolledFrame(self, height=250, autohide=True)
        self.scroll_frame.pack(fill="both", expand=False, padx=2, pady=2)

        self.param_entries = {}
        self.on_param_change = on_param_change

    def clear(self):
        # Clear children of the scroll frame
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.param_entries.clear()
        self.flag_vars = {}
        self.flag_entries = {}

    def show_params(self, action: str, param_defs: dict, flags: list = None):
        """Construye inputs dinámicos según param_defs y flags opcionales"""
        self.clear()

        # --- Required Parameters ---
        if param_defs:
            ttk.Label(self.scroll_frame, text=f"Parámetros requeridos:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5, 5))

            for name, values in param_defs.items():
                row = ttk.Frame(self.scroll_frame)
                row.pack(fill="x", pady=2)

                if isinstance(values, (list, tuple)):
                    ttk.Label(row, text=f"<{name}>: ", width=15).pack(side="left")
                    entry = ttk.Combobox(row, values=values, width=30, bootstyle=PRIMARY)
                    entry.set(f"<{name}>")
                    entry.pack(side="left", expand=True, fill="x")
                    entry.bind("<<ComboboxSelected>>", lambda e: self._trigger_change())
                else:
                    entry = ttk.Entry(row, bootstyle=SECONDARY)
                    entry.insert(0, f"<{name}>")
                    entry.pack(side="left", expand=True, fill="x")
                    entry.bind("<KeyRelease>", lambda e: self._trigger_change())

                self.param_entries[name] = entry

        # --- Optional Flags ---
        if flags:
            ttk.Separator(self.scroll_frame, orient="horizontal").pack(fill="x", pady=10)
            ttk.Label(self.scroll_frame, text=f"Opciones adicionales:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))

            for flag in flags:
                # flag is dict: {"name": "--flagname", "placeholder": "VALUE"}
                flag_name = flag.get("name", "")
                placeholder = flag.get("placeholder", "")
                
                row = ttk.Frame(self.scroll_frame)
                row.pack(fill="x", pady=2)
                
                # Checkbox
                var = ttk.BooleanVar(value=False)
                self.flag_vars[flag_name] = var
                
                chk = ttk.Checkbutton(
                    row, 
                    text=flag_name, 
                    variable=var, 
                    bootstyle="round-toggle",
                    command=self._trigger_change
                )
                chk.pack(side="left")
                
                # Entry for value if placeholder exists
                if placeholder:
                    entry = ttk.Entry(row, bootstyle=SECONDARY)
                    entry.insert(0, f"<{placeholder}>")
                    entry.pack(side="left", padx=(5, 0), expand=True, fill="x")
                    entry.bind("<KeyRelease>", lambda e: self._trigger_change())
                    self.flag_entries[flag_name] = entry
                else:
                    self.flag_entries[flag_name] = None

    def get_values(self):
        # Return tuple: (params_dict, flags_list)
        params = {k: e.get() for k, e in self.param_entries.items()}
        
        flags = []
        for flag_name, var in self.flag_vars.items():
            if var.get():
                entry = self.flag_entries.get(flag_name)
                if entry:
                    val = entry.get()
                    flags.append(f"{flag_name}={val}")
                else:
                    flags.append(flag_name)
        
        return params, flags

    def _trigger_change(self):
        if self.on_param_change:
            self.on_param_change(self.get_values())
