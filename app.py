# app.py
from backend.infrastructure.configuration_manager import ConfigurationManager
from backend.infrastructure.di_container import DIContainer
from ui.main_window import MainWindow

def main():
    # --- Configuración e inyector ---
    config = ConfigurationManager().load_configuration("config/.config")
    container = DIContainer(config)

    # --- Lanzar ventana principal ---
    app = MainWindow(container)
    app.mainloop()

if __name__ == "__main__":
    main()
