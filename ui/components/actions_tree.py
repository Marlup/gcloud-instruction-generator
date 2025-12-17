from itertools import count
import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, PRIMARY, SECONDARY, DANGER
from backend.constants import category_colors, CATEGORY_ORDER
from ui.utils import (
    SERVICE_HEADER_FONT_STYLE,
    get_category_icon,
    strip_icon
)
from ui.dialogs.tooltip import InfoTooltip

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
        
        clear_search_btn = ttk.Button(
            search_row, 
            text="❌",
            bootstyle=DANGER, 
            command=self._on_clear_search,
            width=3
        )
        clear_search_btn.pack(side="left", padx=5)
        
        # --- treeview ---
        self.header_label = ttk.Label(
            self,
            text="Acciones",
            bootstyle=INFO,
            font=SERVICE_HEADER_FONT_STYLE
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
                    expanded_texts.add(strip_icon(item_text))
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
            item_text = values[0] if values else strip_icon(self.tree.item(item_id, "text"))
            
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
            category = parent_values[0] if parent_values else strip_icon(self.tree.item(parent_id, "text"))
            
            resource_values = self.tree.item(self.tree.parent(parent_id), "values")
            resource = resource_values[0] if resource_values else strip_icon(self.tree.item(self.tree.parent(parent_id), "text"))
            
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
