import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
import tkinter.font as tkfont

# 👉 ahora importamos del SDK, no de infraestructure local
from sdk.services.storage_service import StorageService
from sdk.utils import subcategory_colors

# --- Inicializar servicio desde SDK ---
storage_service = StorageService()

# --- Functions ---
def mostrar_parametros(action, params_def):
    global selected_action, selected_cmd, selected_params
    
    for widget in frame_params.winfo_children():
        widget.destroy()
    param_entries.clear()

    selected_action = action
    selected_cmd = params_def["cmd"]
    selected_params = params_def["params"]

    if selected_params:
        ttk.Label(frame_params, text=f"Parámetros para {action}:").pack(anchor="w", pady=5)

        for key in selected_params:
            row = ttk.Frame(frame_params)
            row.pack(fill="x", pady=2)

            ttk.Label(row, text=f"{key}: ", width=15).pack(side="left")

            if key == "region":
                entry = ttk.Combobox(row, values=storage_service.regions, width=30, bootstyle=PRIMARY)
                entry.set(f"<{key}>")
                entry.pack(side="left", expand=True, fill="x")
                param_entries[key] = entry
                entry.bind("<<ComboboxSelected>>", lambda e: generate_command())
            elif key == "storage_class":
                entry = ttk.Combobox(row, values=storage_service.storage_classes,
                                     state="readonly", width=30, bootstyle=INFO)
                entry.set(storage_service.storage_classes[0])
                entry.pack(side="left", expand=True, fill="x")
                param_entries[key] = entry
                entry.bind("<<ComboboxSelected>>", lambda e: generate_command())
            else:
                entry = ttk.Entry(row, bootstyle=SECONDARY)
                entry.insert(0, f"<{key}>")
                entry.pack(side="left", expand=True, fill="x")
                param_entries[key] = entry
                entry.bind("<KeyRelease>", lambda e: generate_command())

def generate_command():
    global selected_action, selected_cmd, selected_params
    if not selected_action or not selected_cmd:
        salida.delete("1.0", "end")
        salida.insert("end", "⚠️ Selecciona primero una acción en el árbol")
        return

    params = {k: e.get() for k, e in param_entries.items()}
    comando = storage_service.build_command(selected_cmd, params)
    salida.delete("1.0", "end")
    salida.insert("end", comando)

def copiar_comando():
    content = salida.get("1.0", "end").strip()
    if content:
        root.clipboard_clear()
        root.clipboard_append(content)
        root.update()
        message = "Comando copiado ✅"
    else:
        message = "No copiado: el contenido está vacío"

    lbl_msg = ttk.Label(root, text=message, bootstyle=SUCCESS)
    lbl_msg.place(relx=0.5, rely=0.95, anchor="center")
    root.after(2000, lbl_msg.destroy)

def on_tree_select(event):
    tree = event.widget
    item_id = tree.focus()
    action = tree.item(item_id, "text")
    parent_id = tree.parent(item_id)
    if not parent_id:
        return
    subcat = tree.item(parent_id, "text")
    cat_id = tree.parent(parent_id)
    category = tree.item(cat_id, "text")
    if category:
        params_def = storage_service.get_action_def(category, subcat, action)
        mostrar_parametros(action, params_def)

def cambiar_tema(event=None):
    nuevo_tema = combo_theme.get()
    root.style.theme_use(nuevo_tema)

def exit_focus(event=None):
    root.focus_set()   # mueve el foco al root

def generate_command_in_action_label(event=None):
    generate_command()

def execute_command():
    content = salida.get("1.0", "end").strip()
    if not content:
        lbl_msg = ttk.Label(root, text="⚠️ No hay comando para ejecutar", bootstyle=WARNING)
        lbl_msg.place(relx=0.5, rely=0.95, anchor="center")
        root.after(2000, lbl_msg.destroy)
        return
    
    output = storage_service.execute(content)

    resultado.delete("1.0", "end")
    resultado.insert("end", output)


# --- State ---
param_entries = {}
selected_action = None
selected_cmd = None
selected_params = None

# --- UI principal ---
root = ttk.Window(themename="flatly")

# Keyboard bindings
root.bind("<Control-g>", lambda e: generate_command())
root.bind("<Return>", lambda e: generate_command_in_action_label())
root.bind("<Escape>", exit_focus)

root.title("Generador gcloud storage")
root.geometry("1100x700")

# Fuente global
default_font = tkfont.nametofont("TkDefaultFont")
default_font.configure(size=12)
root.style.configure("TButton", font=("Segoe UI", 12, "bold"))
root.style.configure("Treeview", font=("Consolas", 11))

# Desplegable de temas
frame_top = ttk.Frame(root)
frame_top.pack(side="top", anchor="ne", pady=5, padx=10)
ttk.Label(frame_top, text="Tema:", bootstyle=INFO).pack(side="left", padx=5)
combo_theme = ttk.Combobox(frame_top, values=root.style.theme_names(),
                           state="readonly", width=15, bootstyle=PRIMARY)
combo_theme.set("flatly")
combo_theme.pack(side="left")
combo_theme.bind("<<ComboboxSelected>>", cambiar_tema)

# --- Paned principal (izq/der) ---
main_pane = ttk.Panedwindow(root, orient=HORIZONTAL)
main_pane.pack(fill="both", expand=True, padx=10, pady=10)

# Panel izquierdo (árbol categorías)
frame_left = ttk.Frame(main_pane, padding=10)
main_pane.add(frame_left, weight=1)

ttk.Label(frame_left, text="Acciones de Storage",
          bootstyle=INFO, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0,5))

tree = ttk.Treeview(frame_left, bootstyle=PRIMARY)
tree.pack(fill="both", expand=True)

c = 0
for category, subcats in storage_service.actions.items():
    cat_id = tree.insert("", "end", text=category, open=True)
    for subcat, actions in subcats.items():
        subcat_name = subcat.split(" ", 1)[-1]
        sub_id = tree.insert(cat_id, "end", text=subcat, open=True, tags=(subcat_name,))
        if subcat_name in subcategory_colors:
            tree.tag_configure(subcat_name, **subcategory_colors[subcat_name])
        for action in actions.keys():
            tree.insert(sub_id, "end", id=f"tree-action-label-{c}", text=action)
            c += 1

tree.bind("<<TreeviewSelect>>", on_tree_select)

# Panel derecho (parametros + salida + botones)
frame_right = ttk.Frame(main_pane, padding=10)
main_pane.add(frame_right, weight=3)

frame_params = ttk.LabelFrame(frame_right, text="Parámetros")
frame_params.pack(fill="x", pady=5)

salida = ScrolledText(frame_right, width=45, height=14, wrap="word", bootstyle=LIGHT)
salida.pack(fill="both", expand=False, pady=5)

resultado = ScrolledText(frame_right, width=45, height=12, wrap="word", bootstyle=SECONDARY)
resultado.pack(fill="both", expand=True, pady=5)

btn_frame = ttk.Frame(frame_right)
btn_frame.pack(pady=5)
ttk.Button(btn_frame, text="✅ Generar comando\n             (ctrl + g)",
           bootstyle=SUCCESS, command=generate_command).pack(side="left", padx=5)
ttk.Button(btn_frame, text="📋 Copiar", bootstyle=INFO,
           command=copiar_comando).pack(side="left", padx=5)
ttk.Button(btn_frame, text="▶ Ejecutar", bootstyle=PRIMARY,
           command=execute_command).pack(side="left", padx=5)

root.mainloop()
