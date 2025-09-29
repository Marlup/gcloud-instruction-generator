# tests/test_sequence_panel.py
from ui.panels import SequencePanel

def test_add_and_clear(tk_root):
    panel = SequencePanel(tk_root)
    panel.add_command("gcloud bucket create my-bucket")
    assert "my-bucket" in panel.get_all()
    panel.clear_commands()
    assert panel.get_all() == ""
