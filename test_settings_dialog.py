#!/usr/bin/env python3
"""
Test script to verify the SettingsDialog displays correctly with visible buttons.
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ui.panels import SettingsDialog

def test_settings_dialog():
    """Test the settings dialog display."""
    root = ttk.Window(themename="cyborg")
    root.title("Test Settings Dialog")
    root.geometry("400x300")
    
    # Test defaults
    test_defaults = {
        "project_id": "test-project-123",
        "region": "us-west1",
        "location": "us"
    }
    
    def on_save(values):
        print("✅ Save button clicked!")
        print(f"Received values: {values}")
        root.quit()
    
    def open_dialog():
        print("Opening settings dialog...")
        dialog = SettingsDialog(
            root,
            current_defaults=test_defaults,
            on_save=on_save
        )
        root.wait_window(dialog)
        
        if dialog.result:
            print(f"Dialog result: {dialog.result}")
        else:
            print("Dialog was cancelled")
    
    # Button to open dialog
    ttk.Button(
        root,
        text="🔧 Open Settings Dialog",
        bootstyle=INFO,
        command=open_dialog
    ).pack(expand=True, pady=50)
    
    ttk.Label(
        root,
        text="Click the button to test the settings dialog.\nCheck that both buttons are visible!",
        justify="center"
    ).pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    print("=" * 60)
    print("Settings Dialog Test")
    print("=" * 60)
    print("This test will open a settings dialog.")
    print("Please verify:")
    print("  ✓ Both buttons are visible (Save and Cancel)")
    print("  ✓ Enter key saves")
    print("  ✓ Escape key cancels")
    print("=" * 60)
    print()
    
    test_settings_dialog()
