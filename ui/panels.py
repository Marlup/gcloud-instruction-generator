from itertools import count
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter.filedialog as fd
from ttkbootstrap.scrolled import ScrolledText
from backend.constants import category_colors
from tkinter import filedialog
from datetime import datetime

# ---------------------------------------------------
# ------------------- Header & Actions panels -------
# ---------------------------------------------------

service_header_font_style = ("Segoe UI", 16, "bold")
resource_label_font_style = ("Segoe UI", 14, "bold")
category_label_font_style = ("Segoe UI", 12, "bold")
action_label_font_style = ("Segoe UI", 10, "bold")

class HeaderPanel(ttk.Frame):
    def __init__(self, parent, on_tab_change, on_theme_change, services: list[str]):
        super().__init__(parent)
        
        ttk.Label(self, text="Tema:", bootstyle=INFO).pack(side="left", padx=5)
        self.combo_theme = ttk.Combobox(
            self, values=parent.style.theme_names(),
            state="readonly", width=15, bootstyle=PRIMARY
        )
        self.combo_theme.set("flatly")
        self.combo_theme.pack(side="left")
        self.combo_theme.bind("<<ComboboxSelected>>", on_theme_change)

        self.notebook = ttk.Notebook(self, bootstyle=PRIMARY)
        self.notebook.pack(side="left", fill="x", expand=True, padx=20)
        for svc in services:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=svc)
        self.notebook.bind("<<NotebookTabChanged>>", on_tab_change)


class ActionsPanel(ttk.Frame):
    def __init__(self, parent, on_action_select):
        super().__init__(parent, padding=10)

        # --- search bar ---
        search_row = ttk.Frame(self)
        search_row.pack(fill="x", pady=(0,5))
        ttk.Label(search_row, text="🔎 Search:").pack(side="left", padx=5)
        self.entry_search = ttk.Entry(search_row, bootstyle=SECONDARY)
        self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", self._on_search)
        self.entry_search
        clear_search_btn = ttk.Button(
            search_row, 
            text="❌",
            bootstyle="danger", 
            command=self._on_clear_search,
            width=3
        )
        clear_search_btn.pack(side="left", padx=5)
        
        # --- treeview ---
        self.header_label = ttk.Label(
            self,
            text="Acciones",
            bootstyle=INFO,
            font=service_header_font_style
        )
        self.header_label.pack(anchor="w", pady=(0, 5))

        self.tree = ttk.Treeview(self, bootstyle=PRIMARY)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.on_action_select = on_action_select


    def refresh(self, actions: dict):
        """Recibe las acciones y refresca árbol + cachea."""
        self._all_actions = actions
        self._populate(actions)

    def _populate(self, actions: dict):
            """Clear and repopulate the tree."""
            self.tree.delete(*self.tree.get_children())
            counter = count()  # sequential IDs
            for resource, categories in actions.items():
                res_id = self.tree.insert("", "end", text=resource, open=True)
                self._populate_category(categories, res_id, counter)

    def _populate_category(self, categories: dict[str, dict], res_id: str, counter):
        for category, acts in categories.items():
            category_name = category.split(" ", 1)[-1]
            sub_id = self.tree.insert(
                res_id, "end", text=category, open=True, tags=(category_name,)
            )
            self._populate_action(category_name, acts, sub_id, counter)

    def _populate_action(self, category_name: str, acts: list[str], sub_id: str, counter):
        if category_name in category_colors:
            self.tree.tag_configure(category_name, **category_colors[category_name])
        for action in acts:
            self.tree.insert(
                sub_id, "end", iid=f"tree-action-{next(counter)}", text=action
            )

    def _on_search(self, event=None):
        text = self.entry_search.get().lower().strip()
        if not text:
            self._populate(self._all_actions)
            return
        # filtrar por recurso, categoría o acción
        filtered = {}
        for res, cats in self._all_actions.items():
            if text in res.lower():
                filtered[res] = cats
                continue
            for cat, acts in cats.items():
                if text in cat.lower():
                    filtered.setdefault(res, {})[cat] = acts
                    continue
                for act in acts:
                    if text in act.lower():
                        filtered.setdefault(res, {}).setdefault(cat, {})[act] = acts[act]
        self._populate(filtered)
    
    def _on_clear_search(self, event=None):
        self.entry_search.delete(0, 'end')
        self._on_search()

    def _on_select(self, event=None):
        item_id = self.tree.focus()
        if not item_id:
            return

        action = self.tree.item(item_id, "text")
        parent_id = self.tree.parent(item_id)
        if not parent_id:
            return

        category = self.tree.item(parent_id, "text")
        resource_id = self.tree.parent(parent_id)
        if not resource_id:
            return

        resource = self.tree.item(resource_id, "text")
        self.on_action_select(action, resource, category)


# ---------------------------------------------------
# ------------------- Params panels -----------------
# ---------------------------------------------------

class ParamsPanel(ttk.LabelFrame):
    def __init__(self, parent, on_param_change):
        super().__init__(parent, text="Parámetros")
        self.pack(fill="x", pady=5)

        self.param_entries = {}
        self.on_param_change = on_param_change

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.param_entries.clear()

    def show_params(self, action: str, param_defs: dict):
        """Construye inputs dinámicos según param_defs {nombre: valores}"""
        self.clear()

        if not param_defs:
            return

        ttk.Label(self, text=f"Parámetros para {action}:").pack(anchor="w", pady=5)

        for name, values in param_defs.items():
            row = ttk.Frame(self)
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

    def get_values(self) -> dict:
        return {k: e.get() for k, e in self.param_entries.items()}

    def _trigger_change(self):
        if self.on_param_change:
            self.on_param_change(self.get_values())


# ---------------------------------------------------
# ------------------- Output panels -----------------
# ---------------------------------------------------

class OutputPanel(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Comando seleccionado")
        self.pack(fill="x", pady=5)

        # Cuadro de salida
        self.panel_text = ScrolledText(self, width=80, height=5, wrap="word")
        self.panel_text.pack(fill="both", expand=True)
        self.panel_text.text.config(state="normal")

        # Botones
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        ttk.Button(
            btn_frame,
            text="📋 Copiar",
            bootstyle=INFO,
            command=self.copy_to_clipboard
        ).pack(side="left", padx=5)

        self._root = self.winfo_toplevel()

    def set_command(self, cmd: str):
        # Usar el widget de texto interno
        self.panel_text.text.config(state="normal")
        self.panel_text.text.delete("1.0", "end")
        self.panel_text.text.insert("end", cmd)
        self.panel_text.text.config(state="disabled")
        
    def get_command(self) -> str:
        return self.panel_text.text.get("1.0", "end").strip()

    def copy_to_clipboard(self):
        content = self.get_command()
        if content:
            self._root.clipboard_clear()
            self._root.clipboard_append(content)
            self._root.update()
            self._flash_message("Comando copiado ✅", SUCCESS)
        else:
            self._flash_message("No copiado: vacío", WARNING)

    def _flash_message(self, message, style):
        lbl_msg = ttk.Label(self._root, text=message, bootstyle=style)
        lbl_msg.place(relx=0.5, rely=0.95, anchor="center")
        self._root.after(2000, lbl_msg.destroy)

# ---------------------------------------------------
# ------------------- Execution panel ---------------
# ---------------------------------------------------

class ExecutionPanel(ttk.Frame):
    def __init__(self, parent, on_execute):
        super().__init__(parent, padding=10)
        self.pack(fill="both", expand=True, pady=5)

        # Botón ejecutar
        ttk.Button(
            self,
            text="▶ Ejecutar",
            bootstyle=PRIMARY,
            command=self._do_execute
        ).pack(side="top", padx=5, pady=5)

        # Panel salida
        self.text = ScrolledText(self, width=45, height=12, wrap="word", bootstyle=SECONDARY)
        self.text.pack(fill="both", expand=True, pady=5)
        self.text.text.config(state="disabled")

        self.on_execute = on_execute

    def _do_execute(self):
        if not self.on_execute:
            return
        output = self.on_execute()
        self.set_output(output)

    def set_output(self, output: str):
        self.text.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", output)
        self.text.text.config(state="disabled")

# ---------------------------------------------------
# ------------------- Sequence panel ----------------
# --------------------------------------------------- 

class SequencePanel(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Secuencia de comandos")

        # Área de texto con scroll
        self.text = ScrolledText(self, width=80, height=10, wrap="word")
        self.text.pack(fill="both", expand=True, pady=(0,5))

        # Botones internos
        btns = ttk.Frame(self)
        btns.pack(fill="x")

        ttk.Button(btns, text="🗑 Limpiar", bootstyle="danger",
                   command=self.clear_commands).pack(side="left", padx=5)
        ttk.Button(btns, text="💾 Exportar", bootstyle="info",
                   command=self.export_sequence).pack(side="left", padx=5)

    # --- API pública ---
    def add_command(self, cmd: str):
        """Añade un comando a la secuencia."""
        self.text.text.insert("end", cmd + "\n")

    def clear_commands(self):
        """Borra todos los comandos."""
        self.text.text.delete("1.0", "end")

    def get_all(self) -> str:
        """Devuelve todo el contenido actual."""
        return self.text.text.get("1.0", "end").strip()

    def export_sequence(self, filename: str = "sequence", ext: str = ".sh"):
        """Exporta la secuencia a un fichero elegido por el usuario."""
        content = self.get_all()
        if not content:
            return
        
        ts = int(datetime.now().timestamp())
        filename_ts = filename + f"_{ts}"

        # Abrir diálogo de guardar
        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=filename_ts,
            filetypes=[("Shell script", "*.sh"), ("Texto", "*.txt"), ("Todos", "*.*")]
        )

        if not filepath:  # Usuario canceló
            return

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
