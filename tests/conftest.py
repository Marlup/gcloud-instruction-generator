# tests/conftest.py
import pytest
import tkinter as tk

@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()  # hide the main window during tests
    yield root
    root.destroy()
