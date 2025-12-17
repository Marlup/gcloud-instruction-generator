import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, DANGER

class InfoTooltip(ttk.Toplevel):
    """Floating tooltip panel that shows action/group descriptions."""
    
    def __init__(self, parent, text: str, x: int, y: int, pinned: bool = False):
        super().__init__(parent)
        
        self.pinned = pinned
        self.text_content = text
        
        # Remove window decorations
        self.overrideredirect(True)
        
        # Make it float on top
        self.attributes('-topmost', True)
        
        # Main frame with border
        main_frame = ttk.Frame(self, padding=10, bootstyle=INFO)
        main_frame.pack(fill="both", expand=True)
        
        # Header with close button (only if pinned)
        if pinned:
            header_frame = ttk.Frame(main_frame)
            header_frame.pack(fill="x", pady=(0, 5))
            
            ttk.Label(
                header_frame,
                text="ℹ️ Información",
                font=("Segoe UI", 10, "bold"),
                bootstyle=INFO
            ).pack(side="left")
            
            close_btn = ttk.Button(
                header_frame,
                text="✕",
                bootstyle=DANGER,
                command=self.destroy,
                width=3
            )
            close_btn.pack(side="right")
        
        # Description text with wrapping
        desc_label = ttk.Label(
            main_frame,
            text=text,
            wraplength=350,
            justify="left",
            font=("Segoe UI", 9)
        )
        desc_label.pack(fill="both", expand=True)
        
        # Position near cursor with offset
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Update to get actual size
        self.update_idletasks()
        tooltip_width = self.winfo_reqwidth()
        tooltip_height = self.winfo_reqheight()
        
        # Adjust position to keep tooltip on screen
        if x + tooltip_width + 10 > screen_width:
            x = screen_width - tooltip_width - 10
        if y + tooltip_height + 10 > screen_height:
            y = screen_height - tooltip_height - 10
        
        self.geometry(f"+{x+10}+{y+10}")
        
        # Auto-hide on mouse leave if not pinned
        if not pinned:
            self.bind("<Leave>", lambda e: self.destroy())
