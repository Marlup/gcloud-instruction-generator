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
        self._all_actions = {}


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
            except:
                pass
        
        # Clear tree
        self.tree.delete(*self.tree.get_children())
        self._expanded_items.clear()
        
        # Repopulate
        for resource, subtree in actions.items():
            # Add folder icon to resources
            resource_display = f"📁 {resource}"
            
            # Start collapsed (open=False), restore if was expanded
            should_open = resource in expanded_texts
            
            # Insert Resource Node
            res_id = self.tree.insert("", "end", text=resource_display, open=should_open, values=(resource,))
            
            if should_open:
                self._expanded_items.add(res_id)
            
            # Recursive populate
            self._populate_recursive(subtree, res_id, expanded_texts)

    def _populate_recursive(self, current_level: dict, parent_id: str, expanded_texts: set):
        """
        Recursively populate the tree.
        current_level: dict that may contain nested commands or key "__action"
        """
        if "action" in current_level:
            # This logic might be slightly different: 
            # If the current node HAS an action, it might ALSO have children (sub-verbs)?
            # In our data structure:
            # jobs -> create (key) -> { __action: ..., app-engine: { ... } }
            # But the parent call created the node for 'create'.
            # Wait, no. The parent loop iterates keys.
            
            # Actually, the recursion should handle keys.
            pass

        # Sort keys to look nice, keeping normal commands together
        # We want to ignore __action during iteration, as it is property of current node (definitions)
        # But wait, Treeview items represent the KEY.
        # If 'create' has an __action, we want the TreeItem for 'create' to be selectable.
        # But we already created 'create' in the PREVIOUS step?
        # NO. We are INSIDE 'create' dict now.
        
        # This function receives the DICT content of a node, and the ID of that node.
        # If this dict has keys other than __action, they are children.
        
        child_keys = [k for k in current_level.keys() if k != "action"]
        child_keys.sort()
        
        for key in child_keys:
            val = current_level[key]
            
            # Determine display
            # If val has __action, it is a Command (Action).
            # It might also have children (Group).
            # So it can be both.
            
            is_action = "action" in val
            has_children = any(k != "action" for k in val.keys())
            
            # Icon selection
            if is_action:
                icon = "▸" # Action
            else:
                icon = "📂" # Group
                
            display = f"{icon} {key}"
            
            # Check expansion (using key as identifier is weak if dups exist across branches? 
            # The 'values' tuple stores uniqueness locally? 
            # Actually expanded_texts stored raw values[0].
            # Uniqueness is not guaranteed across branches but good enough for UI persistence context)
            should_open = key in expanded_texts
            
            node_id = self.tree.insert(parent_id, "end", text=display, open=should_open, values=(key,))
            
            if should_open:
                self._expanded_items.add(node_id)
            
            # Recurse
            self._populate_recursive(val, node_id, expanded_texts)

    def _on_search(self, event=None):
        text = self.entry_search.get().lower().strip()
        if not text:
            self._populate(self._all_actions)
            return
            
        # Recursive filter
        filtered = self._filter_recursive(self._all_actions, text)
        self._populate(filtered)

    def _filter_recursive(self, node: dict, term: str) -> dict:
        """Return a new dict containing only branches matching term."""
        result = {}
        
        # If this node has an action and it matches? 
        # But we search by keys mostly or action names?
        # The 'key' is the command name.
        
        for key, val in node.items():
            if key == "action":
                continue
            
            # Check if key matches
            match = term in key.lower()
            
            # Recurse
            filtered_subtree = self._filter_recursive(val, term)
            
            if match:
                # Keep whole subtree if key matches? Or just this node?
                # Usually if key matches, user wants to see it.
                # We can keep original val? Or filtered?
                # Let's keep original if key matches (showing all suboptions)
                result[key] = val
            elif filtered_subtree:
                # If children matched, keep this node and the filtered children
                # (preserve __action if present? Yes, usually)
                new_val = filtered_subtree.copy()
                if "action" in val:
                    new_val["action"] = val["action"]
                result[key] = new_val
                
        return result
    
    def _on_clear_search(self, event=None):
        self.entry_search.delete(0, 'end')
        self._on_search()

    def _on_select(self, event=None):
        item_id = self.tree.focus()
        if not item_id:
            return

        # 1. Reconstruct path from root to this item
        # 2. Traverse _all_actions to find the node
        # 3. If node has __action, trigger callback
        
        path_keys = []
        curr = item_id
        while curr:
            values = self.tree.item(curr, "values")
            if values:
                path_keys.insert(0, values[0])
            curr = self.tree.parent(curr)
            
        if not path_keys: 
            return

        # Navigate
        # path_keys[0] is Resource (e.g. jobs)
        # path_keys[1..] are keys in tree
        
        node = self._all_actions
        try:
            for k in path_keys:
                node = node[k]
        except KeyError:
            return
            
        if "action" in node:
            action_def = node["action"]
            # Callback signature: (action_name, resource, category)
            # Legacy signature is annoying. We should adapt.
            # action_name -> label or just key? Legacy used 'Create app engine'.
            # We have 'label' in action_def.
            
            # Resource -> path_keys[0]
            # Category -> path_keys[1] (maybe?)
            
            # Let's pass the ActionDefinition dict as "action" and handle it? 
            # Or construct a dummy string?
            # The "Forms" generation depends on this.
            # In panels.py, we might need to update how we receive data.
            
            # For now, let's pass the whole action_def as the first arg? 
            # Or change the signature. 
            # Let's assume on_action_select is smart enough or we check panels.py
            
            # Checking panels.py previously:
            # def update_details(self, action_name, resource, category):
            #     acts = self.actions[resource][category]
            #     action_def = acts[action_name]
            
            # It expects to do a lookup again! That is fragile with recursive structure.
            # We should pass the ACTION_DEF directly.
            
            self.on_action_select(action_def, path_keys[0], path_keys[-1])

    # ---------------------------------------------------
    # Info Tooltip Methods
    # ---------------------------------------------------
    
    def _get_item_description(self, item_id: str) -> str:
        """Get description for a tree item."""
        if not item_id: return ""
        
        path_keys = []
        curr = item_id
        while curr:
            values = self.tree.item(curr, "values")
            if values:
                path_keys.insert(0, values[0])
            curr = self.tree.parent(curr)
            
        if not path_keys: return ""
        
        # Lookup
        node = self._all_actions
        try:
            for k in path_keys:
                node = node.get(k, {})
        except:
            return ""

        if "action" in node:
            return node["action"].get("explanation", "")
            
        return f"Group: {' '.join(path_keys)}"

    def _on_mouse_motion(self, event):
        """Handle mouse motion over tree items."""
        if self._hover_after_id:
            self.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        
        if self._hover_tooltip:
            self._hover_tooltip.destroy()
            self._hover_tooltip = None
        
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        self._hover_after_id = self.after(
            500,
            lambda: self._show_hover_tooltip(item_id, event.x_root, event.y_root)
        )
    
    def _show_hover_tooltip(self, item_id: str, x: int, y: int):
        if self._pinned_tooltip: return
        
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
        if self._pinned_tooltip:
            self._pinned_tooltip.destroy()
            self._pinned_tooltip = None
        
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
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
        if self._hover_after_id:
            self.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        if self._hover_tooltip:
            self._hover_tooltip.destroy()
            self._hover_tooltip = None
    
    def _on_tree_open(self, event=None):
        item_id = self.tree.focus()
        if item_id: self._expanded_items.add(item_id)
    
    def _on_tree_close(self, event=None):
        item_id = self.tree.focus()
        if item_id: self._expanded_items.discard(item_id)
