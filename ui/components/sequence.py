import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, SUCCESS, WARNING, PRIMARY, SECONDARY
from ttkbootstrap.scrolled import ScrolledText
from tkinter import filedialog
from datetime import datetime


class SequencePanel(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Secuencia de comandos")

        # Internal buttons
        btns = ttk.Frame(self)
        btns.pack(fill="x")

        ttk.Button(btns, text="🗑 Limpiar", bootstyle="danger",
                   command=self.clear_commands).pack(side="left", padx=5)
        ttk.Button(btns, text="💾 Exportar", bootstyle="info",
                   command=self.export_sequence).pack(side="left", padx=5)

        # Área de texto con scroll
        self.text = ScrolledText(self, width=80, height=10, wrap="word")
        self.text.pack(fill="x", expand=False, pady=(0,5))

    # --- API pública ---
    def add_command(self, cmd: str):
        """Añade un comando a la secuencia."""
        self.text.text.insert("end", cmd + "\n")

    def clear_commands(self):
        """Borra todos los comandos."""
        self.text.text.delete("1.0", "end")

    def get_all(self) -> str:
        """Devuelve todo el contenido actual."""
        return self.text.text.get("1.0", "end").strip()

    def export_sequence(self, filename: str = "sequence", ext: str = ".sh"):
        """Exporta la secuencia a un fichero elegido por el usuario."""
        content = self.get_all()
        if not content:
            return
        
        ts = int(datetime.now().timestamp())
        filename_ts = filename + f"_{ts}"

        # Abrir diálogo de guardar
        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=filename_ts,
            filetypes=[("Shell script", "*.sh"), ("Texto", "*.txt"), ("Todos", "*.*")]
        )

        if not filepath:  # Usuario canceló
            return

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
