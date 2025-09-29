# tests/test_output_panel.py
from ui.panels import OutputPanel

def test_set_and_get_command(tk_root):
    panel = OutputPanel(tk_root)
    panel.set_command("gcloud test cmd")
    assert "gcloud test cmd" in panel.get_command()
