# tests/test_actions_panel.py
from ui.panels import ActionsPanel
import pytest

def test_populate_and_select(tk_root):
    selected = {}
    def on_action_select(action, res, cat): selected.update(action=action, res=res, cat=cat)

    panel = ActionsPanel(tk_root, on_action_select)
    actions = {
        "Buckets": {
            "📤 Creación": {"Crear bucket": {"cmd": "gcloud ...", "params": ["bucket"]}}
        }
    }
    panel.refresh(actions)
    # simulate selection
    item = panel.tree.get_children()[0]  # resource
    cat = panel.tree.get_children(item)[0]
    act = panel.tree.get_children(cat)[0]
    panel.tree.selection_set(act)
    panel.tree.event_generate("<<TreeviewSelect>>")

    assert selected["action"] == "Crear bucket"
    assert selected["res"] == "Buckets"
