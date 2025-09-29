# tests/test_params_panel.py
from ui.panels import ParamsPanel

def test_param_entry_and_values(tk_root):
    panel = ParamsPanel(tk_root, on_param_change=None)
    defs = {"bucket": "<bucket>", "region": ["us-east1", "europe-west1"]}
    panel.show_params("Crear bucket", defs)

    entries = panel.get_values()
    assert "bucket" in entries and "region" in entries
