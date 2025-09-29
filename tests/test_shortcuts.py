def test_shortcuts(window):
    # Insert a fake action + cmd
    window.selected_action = "Crear bucket"
    window.selected_cmd = "gcloud storage buckets create {bucket}"
    window.selected_params = ["bucket"]
    window.params_panel.show_params("Crear bucket", {"bucket": "test-bucket"})

    window.event_generate("<Control-g>")
    cmd = window.output_panel.get_command()
    assert "gcloud storage buckets create" in cmd
