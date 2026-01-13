from itertools import count
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter.filedialog as fd
from ttkbootstrap.scrolled import ScrolledText, ScrolledFrame
from backend.constants import category_colors, CATEGORY_ORDER
from ui.config.config import current_theme
from tkinter import filedialog
from datetime import datetime

# ---------------------------------------------------
# ------------------- Header & Actions panels -------
# ---------------------------------------------------

service_header_font_style = ("Segoe UI", 16, "bold")
resource_label_font_style = ("Segoe UI", 14, "bold")
category_label_font_style = ("Segoe UI", 12, "bold")
action_label_font_style = ("Segoe UI", 10, "bold")

# Category icons for visual identification
CATEGORY_ICONS = {
    "reading": "📖",        # Book - for reading/querying
    "creation": "➕",       # Plus - for creation
    "modification": "✏️",  # Pencil - for modification/editing
    "revoke": "🚫",        # Prohibited - for revoke/removal
    "assignment": "🔐",    # Lock - for assignment/permissions
}

def get_category_icon(category_name: str) -> str:
    """Get icon for a category based on its name."""
    category_lower = category_name.lower()
    for key, icon in CATEGORY_ICONS.items():
        if key in category_lower:
            return icon
    return "📋"  # Default clipboard icon


# ---------------------------------------------------
# ------------------- Info Tooltip ------------------
# ---------------------------------------------------

class InfoTooltip(ttk.Toplevel):
    """Floating tooltip panel that shows action/group descriptions."""
    
    def __init__(self, parent, text: str, x: int, y: int, pinned: bool = False):
        super().__init__(parent)
        
        self.pinned = pinned
        self.text_content = text
        
        # Remove window decorations
        self.overrideredirect(True)
        
        # Make it float on top
        self.attributes('-topmost', True)
        
        # Main frame with border
        main_frame = ttk.Frame(self, padding=10, bootstyle=INFO)
        main_frame.pack(fill="both", expand=True)
        
        # Header with close button (only if pinned)
        if pinned:
            header_frame = ttk.Frame(main_frame)
            header_frame.pack(fill="x", pady=(0, 5))
            
            ttk.Label(
                header_frame,
                text="ℹ️ Información",
                font=("Segoe UI", 10, "bold"),
                bootstyle=INFO
            ).pack(side="left")
            
            close_btn = ttk.Button(
                header_frame,
                text="✕",
                bootstyle=DANGER,
                command=self.destroy,
                width=3
            )
            close_btn.pack(side="right")
        
        # Description text with wrapping
        desc_label = ttk.Label(
            main_frame,
            text=text,
            wraplength=350,
            justify="left",
            font=("Segoe UI", 9)
        )
        desc_label.pack(fill="both", expand=True)
        
        # Position near cursor with offset
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Update to get actual size
        self.update_idletasks()
        tooltip_width = self.winfo_reqwidth()
        tooltip_height = self.winfo_reqheight()
        
        # Adjust position to keep tooltip on screen
        if x + tooltip_width + 10 > screen_width:
            x = screen_width - tooltip_width - 10
        if y + tooltip_height + 10 > screen_height:
            y = screen_height - tooltip_height - 10
        
        self.geometry(f"+{x+10}+{y+10}")
        
        # Auto-hide on mouse leave if not pinned
        if not pinned:
            self.bind("<Leave>", lambda e: self.destroy())



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


class ActionsTreePanel(ttk.Frame):
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
        
        # Track expansion state
        self._expanded_items = set()  # Store IDs of expanded items
        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        self.tree.bind("<<TreeviewClose>>", self._on_tree_close)
        
        # Info tooltip functionality
        self._hover_tooltip = None  # Current hover tooltip
        self._pinned_tooltip = None  # Pinned tooltip
        self._hover_after_id = None  # Delayed hover timer
        self.tree.bind("<Motion>", self._on_mouse_motion)
        self.tree.bind("<Button-3>", self._on_right_click)  # Right-click to pin
        self.tree.bind("<Leave>", self._on_mouse_leave)

        self.on_action_select = on_action_select


    def refresh(self, actions: dict):
        """Recibe las acciones y refresca árbol + cachea."""
        self._all_actions = actions
        self._populate(actions)
    
    def _strip_icon(self, text: str) -> str:
        """Remove icon emoji/symbols from text."""
        import re
        # Remove emoji (Unicode emoji range) at start followed by space
        text = re.sub(r'^[\U0001F300-\U0001F9FF]\s+', '', text)
        # Remove specific symbols we use (folder, bullet, etc.)
        text = re.sub(r'^[📁📖➕✏️🚫🔐📋▸]\s+', '', text)
        # Remove any other common symbols at start followed by space
        text = re.sub(r'^[\u2000-\u2BFF]\s+', '', text)
        return text.strip()

    def _populate(self, actions: dict):
        """Clear and repopulate the tree."""
        # Save current expansion state by RAW item text (from values)
        expanded_texts = set()
        for item_id in self._expanded_items:
            try:
                # Use values[0] which contains the raw text
                values = self.tree.item(item_id, "values")
                if values:
                    expanded_texts.add(values[0])
                else:
                    # Fallback for legacy items (shouldn't happen after refresh)
                    item_text = self.tree.item(item_id, "text")
                    expanded_texts.add(self._strip_icon(item_text))
            except:
                pass
        
        # Clear tree
        self.tree.delete(*self.tree.get_children())
        self._expanded_items.clear()
        
        # Repopulate
        counter = count()  # sequential IDs
        for resource, categories in actions.items():
            # Add folder icon to resources
            resource_display = f"📁 {resource}"
            
            # Start collapsed (open=False), restore if was expanded
            should_open = resource in expanded_texts
            # Store RAW resource name in values[0]
            res_id = self.tree.insert("", "end", text=resource_display, open=should_open, values=(resource,))
            if should_open:
                self._expanded_items.add(res_id)
            self._populate_category(categories, res_id, counter, expanded_texts)

    def _populate_category_old(self, categories: dict[str, dict], res_id: str, counter):
        for category, acts in categories.items():
            category_name = category.split(" ", 1)[-1]
            sub_id = self.tree.insert(
                res_id, "end", text=category, open=True, tags=(category_name,)
            )
            self._populate_action(category_name, acts, sub_id, counter)


    def _populate_category(self, categories: dict[str, dict], res_id: str, counter, expanded_texts: set):
        def category_sort_key(cat):
            try:
                key_cat = cat.split(" ")
                return CATEGORY_ORDER.index(key_cat)
            except ValueError:
                return len(CATEGORY_ORDER)  # push unknown categories to the end

        for category in sorted(categories.keys(), key=category_sort_key):
            acts = categories[category]
            category_name = category.split(" ", 1)[-1]
            
            # Add icon to category display
            icon = get_category_icon(category)
            category_display = f"{icon} {category}"
            
            # Start collapsed, restore if was expanded
            # Use original category text for state tracking (without icon)
            should_open = category in expanded_texts
            # Store RAW category name in values[0]
            sub_id = self.tree.insert(
                res_id, "end", text=category_display, open=should_open, tags=(category_name,), values=(category,)
            )
            if should_open:
                self._expanded_items.add(sub_id)
            self._populate_action(category_name, acts, sub_id, counter)


    def _populate_action(self, category_name: str, acts: list[str], sub_id: str, counter):
        if category_name in category_colors:
            self.tree.tag_configure(category_name, **category_colors[category_name])
        for action in acts:
            # Add bullet point icon to actions
            action_display = f"▸ {action}"
            # Store RAW action name in values[0]
            self.tree.insert(
                sub_id, "end", iid=f"tree-action-{next(counter)}", text=action_display, values=(action,)
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

        # Use RAW keys from values (safer than stripping icons)
        try:
            values = self.tree.item(item_id, "values")
            if not values: return
            action = values[0]
            
            parent_id = self.tree.parent(item_id)
            if not parent_id: return
            category = self.tree.item(parent_id, "values")[0]
            
            resource_id = self.tree.parent(parent_id)
            if not resource_id: return
            resource = self.tree.item(resource_id, "values")[0]
            
            self.on_action_select(action, resource, category)
        except (IndexError, AttributeError):
            pass
    
    def _on_tree_open(self, event=None):
        """Track when user expands a tree item."""
        item_id = self.tree.focus()
        if item_id:
            self._expanded_items.add(item_id)
    
    def _on_tree_close(self, event=None):
        """Track when user collapses a tree item."""
        item_id = self.tree.focus()
        if item_id and item_id in self._expanded_items:
            self._expanded_items.discard(item_id)
    
    # ---------------------------------------------------
    # Info Tooltip Methods
    # ---------------------------------------------------
    
    def _get_item_description(self, item_id: str) -> str:
        """Get description for a tree item (action/group)."""
        if not item_id:
            return ""
        
        try:
            # Use values if available (raw keys)
            values = self.tree.item(item_id, "values")
            item_text = values[0] if values else self._strip_icon(self.tree.item(item_id, "text"))
            
            parent_id = self.tree.parent(item_id)
            if not parent_id:
                # Top-level resource
                return f"Recurso: {item_text}"
            
            category_id = self.tree.parent(parent_id)
            if not category_id:
                # Category level
                return f"Categoría: {item_text}"
            
            # Action level - get from _all_actions
            # Get parent values safely
            parent_values = self.tree.item(parent_id, "values")
            category = parent_values[0] if parent_values else self._strip_icon(self.tree.item(parent_id, "text"))
            
            resource_values = self.tree.item(self.tree.parent(parent_id), "values")
            resource = resource_values[0] if resource_values else self._strip_icon(self.tree.item(self.tree.parent(parent_id), "text"))
            
            action = item_text
            
            if hasattr(self, '_all_actions') and resource in self._all_actions:
                if category in self._all_actions[resource]:
                    if action in self._all_actions[resource][category]:
                        action_data = self._all_actions[resource][category][action]
                        return action_data.get("explanation", "Sin descripción disponible")
            
            return f"Acción: {action}"
        except Exception as e:
            return "Información no disponible"
    
    def _on_mouse_motion(self, event):
        """Handle mouse motion over tree items."""
        # Cancel any pending hover tooltip
        if self._hover_after_id:
            self.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        
        # Close existing hover tooltip
        if self._hover_tooltip:
            self._hover_tooltip.destroy()
            self._hover_tooltip = None
        
        # Get item under cursor
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        # Schedule tooltip to appear after delay (500ms)
        self._hover_after_id = self.after(
            500,
            lambda: self._show_hover_tooltip(item_id, event.x_root, event.y_root)
        )
    
    def _show_hover_tooltip(self, item_id: str, x: int, y: int):
        """Show hover tooltip for an item."""
        if self._pinned_tooltip:
            # Don't show hover tooltip if there's a pinned one
            return
        
        description = self._get_item_description(item_id)
        if description:
            self._hover_tooltip = InfoTooltip(
                self.winfo_toplevel(),
                description,
                x,
                y,
                pinned=False
            )
    
    def _on_right_click(self, event):
        """Handle right-click to pin tooltip."""
        # Close existing pinned tooltip
        if self._pinned_tooltip:
            self._pinned_tooltip.destroy()
            self._pinned_tooltip = None
        
        # Get item under cursor
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        description = self._get_item_description(item_id)
        if description:
            self._pinned_tooltip = InfoTooltip(
                self.winfo_toplevel(),
                description,
                event.x_root,
                event.y_root,
                pinned=True
            )
    
    def _on_mouse_leave(self, event):
        """Clean up tooltips when mouse leaves tree."""
        # Cancel pending hover
        if self._hover_after_id:
            self.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        
        # Close hover tooltip
        if self._hover_tooltip:
            self._hover_tooltip.destroy()
            self._hover_tooltip = None


# ---------------------------------------------------
# ------------------- Params panels -----------------
# ---------------------------------------------------

class ParamsPanel(ttk.LabelFrame):
    def __init__(self, parent, on_param_change):
        super().__init__(parent, text="Parámetros")
        self.pack(fill="x", pady=5)  # Fixed height (scrollable), only fill horizontal

        # Create scrollable container
        self.scroll_frame = ScrolledFrame(self, height=250, autohide=True)
        self.scroll_frame.pack(fill="both", expand=True, padx=2, pady=2)

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
                    # Just to keep track avoiding key errors
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
                    # User requested format: --flag=value
                    # If flag_name contains --flag=, it might be duplicated?
                    # No, flag_name from list is like "--filter".
                    # Actually wait, in build_actions.py we saw:
                    # full_flag = m.group(1) # --flag
                    # So flag_name is key.
                    flags.append(f"{flag_name}={val}")
                else:
                    flags.append(flag_name)
        
        return params, flags

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

        ttk.Button(btns, text="🗑 Limpiar", bootstyle="danger",
                   command=self.clear_commands).pack(side="left", padx=5)
        ttk.Button(btns, text="💾 Exportar", bootstyle="info",
                   command=self.export_sequence).pack(side="left", padx=5)

        # Botones internos
        btns = ttk.Frame(self)
        btns.pack(fill="x")

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

# ---------------------------------------------------
# ------------------- Settings Dialog ---------------
# ---------------------------------------------------

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
        theme_frame = ttk.LabelFrame(frame, text="Tema")
        theme_frame.pack(fill="x", pady=10)
        
        self.combo_theme = ttk.Combobox(
            theme_frame, 
            values=parent.style.theme_names(),
            state="readonly", 
            bootstyle=PRIMARY
        )
        self.combo_theme.set(parent.style.theme_use())
        self.combo_theme.pack(fill="x", padx=10, pady=10)
        
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

