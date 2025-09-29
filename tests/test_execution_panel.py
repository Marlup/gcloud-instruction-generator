# tests/test_execution_panel.py
from ui.panels import ExecutionPanel

def test_execute_panel(tk_root):
    def fake_exec(): return "OK"
    panel = ExecutionPanel(tk_root, on_execute=fake_exec)
    panel._do_execute()
    assert "OK" in panel.text.text.get("1.0", "end")
