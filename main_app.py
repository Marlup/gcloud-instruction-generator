# app.py
import logging

from backend.infrastructure.configuration_manager import ConfigurationManager
from backend.infrastructure.di_container import DIContainer
from ui.main_window import MainWindow

logging.basicConfig(
   level=logging.INFO,
   filename="data/ui-app-run.log",
   filemode="a",        # "a" = append, "w" = overwrite
   format="%(asctime)s [%(levelname)s] %(message)s"
)

def main():
    # --- Configuration and injector ========
    config = ConfigurationManager().load_configuration("backend/config/.config")
    container = DIContainer(config)

    # --- Lanzar ventana principal ---
    app = MainWindow(container)
    app.mainloop()

if __name__ == "__main__":
    main()
