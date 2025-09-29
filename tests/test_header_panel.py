# tests/test_header_panel.py
from ui.panels import HeaderPanel
import pytest

def test_theme_change(monkeypatch, tk_root):
    changed = {}

    def on_theme_change(event): changed["theme"] = True
    panel = HeaderPanel(tk_root, on_tab_change=lambda e: None, on_theme_change=on_theme_change, services=["storage"])
    panel.combo_theme.set("cosmo")
    panel.combo_theme.event_generate("<<ComboboxSelected>>")
    assert changed["theme"]
