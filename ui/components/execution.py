import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, SUCCESS, WARNING, PRIMARY, SECONDARY
from ttkbootstrap.scrolled import ScrolledText
from tkinter import filedialog
from datetime import datetime

class OutputPanel(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Comando seleccionado")
        self.pack(fill="x", pady=5)

        # Internal buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        ttk.Button(
            btn_frame,
            text="📋 Copiar",
            bootstyle=INFO,
            command=self.copy_to_clipboard
        ).pack(side="left", padx=5)

        # Cuadro de salida
        self.panel_text = ScrolledText(self, width=80, height=5, wrap="word")
        self.panel_text.pack(fill="both", expand=True)
        self.panel_text.text.config(state="normal")


        self._root = self.winfo_toplevel()

    def set_command(self, cmd: str):
        # Usar el widget de texto interno
        self.panel_text.text.config(state="normal")
        self.panel_text.text.delete("1.0", "end")
        self.panel_text.text.insert("end", cmd)
        self.panel_text.text.config(state="disabled")
        
    def get_command(self) -> str:
        return self.panel_text.text.get("1.0", "end").strip()

    def copy_to_clipboard(self):
        content = self.get_command()
        if content:
            self._root.clipboard_clear()
            self._root.clipboard_append(content)
            self._root.update()
            self._flash_message("Comando copiado ✅", SUCCESS)
        else:
            self._flash_message("No copiado: vacío", WARNING)

    def _flash_message(self, message, style):
        lbl_msg = ttk.Label(self._root, text=message, bootstyle=style)
        lbl_msg.place(relx=0.5, rely=0.95, anchor="center")
        self._root.after(2000, lbl_msg.destroy)


class ExecutionPanel(ttk.Frame):
    def __init__(self, parent, on_execute):
        super().__init__(parent, padding=10)
        self.pack(fill="both", expand=True, pady=5)

        # Botón ejecutar
        ttk.Button(
            self,
            text="▶ Ejecutar",
            bootstyle=PRIMARY,
            command=self._do_execute
        ).pack(side="top", padx=5, pady=5)

        # Panel salida
        self.text = ScrolledText(self, width=45, height=12, wrap="word", bootstyle=SECONDARY)
        self.text.pack(fill="both", expand=True, pady=5)
        self.text.text.config(state="disabled")

        self.on_execute = on_execute

    def _do_execute(self):
        if not self.on_execute:
            return
        output = self.on_execute()
        self.set_output(output)

    def set_output(self, output: str):
        self.text.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", output)
        self.text.text.config(state="disabled")

