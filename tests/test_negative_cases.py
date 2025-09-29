def test_no_action_selected(window):
    window.selected_action = None
    window.selected_cmd = None
    window.generate_command()
    assert "Selecciona primero" in window.output_panel.get_command()
