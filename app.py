from typing import Dict
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
import tkinter.font as tkfont

# Backend
from backend.constants import subresource_colors
from backend.infrastructure.utils import get_frame_parameters
from backend.infrastructure.configuration_manager import ConfigurationManager
from backend.infrastructure.di_container import DIContainer
from backend.services.base_service import BaseGCloudService

# --- Configuración e Inyector ---
config = ConfigurationManager().load_configuration("config/.config")
container = DIContainer(config)

# --- Initial State ---
current_service_name = "storage"
current_service: BaseGCloudService = container.get(current_service_name)

param_entries = {}
selected_action = None
action_cmd = None
action_params = None

# --- Functions ---
def mostrar_parametros(action: str, action_definition: Dict[str, str]):
    global selected_action, action_cmd, action_params

    for widget in frame_params.winfo_children():
        widget.destroy()
    param_entries.clear()

    selected_action = action
    action_cmd = action_definition["cmd"]
    action_params = action_definition["params"]

    if not action_params:
        return
    
    ttk.Label(frame_params, text=f"Parámetros para {action}:").pack(anchor="w", pady=5)

    net_parameters = get_frame_parameters(current_service.parameters, action_params)
    #print("\nShow parameters\n----------------")
    for param_key, param_values in net_parameters.items():
        #print(f"param_key -> {param_key}")
        row = ttk.Frame(frame_params)
        row.pack(fill="x", pady=2)

        make_parameter_entry(row, param_key, param_values)

def make_parameter_entry(parent_row, name, values):
    print(f"<{name}>: ")
    if isinstance(values, (list, tuple)):
        ttk.Label(parent_row, text=f"<{name}>: ", width=15).pack(side="left")

        entry = ttk.Combobox(parent_row, values=values, width=30, bootstyle=PRIMARY)
        entry.set(f"<{name}>")
        entry.pack(side="left", expand=True, fill="x")
        param_entries[name] = entry
        entry.bind("<<ComboboxSelected>>", lambda e: generate_command())
    else:
        entry = ttk.Entry(parent_row, bootstyle=SECONDARY)
        entry.insert(0, f"<{name}>")
        entry.pack(side="left", expand=True, fill="x")
        param_entries[name] = entry
        entry.bind("<KeyRelease>", lambda e: generate_command())

def generate_command():
    global selected_action, action_cmd, action_params
    if not selected_action or not action_cmd:
        query_output_panel.delete("1.0", "end")
        query_output_panel.insert("end", "⚠️ Selecciona primero una acción en el árbol")
        return

    params = {k: e.get() for k, e in param_entries.items()}
    #print(params)
    comando = current_service.build_command(action_cmd, params)
    query_output_panel.delete("1.0", "end")
    query_output_panel.insert("end", comando)

def copiar_comando():
    content = query_output_panel.get("1.0", "end").strip()

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
    category = tree.item(parent_id, "text")
    cat_id = tree.parent(parent_id)
    resource = tree.item(cat_id, "text")
    if resource:
        action_definition = current_service.get_action_def(resource, category, action)
        mostrar_parametros(action, action_definition)
    
    generate_command()


def cambiar_tema(event=None):
    nuevo_tema = combo_theme.get()
    root.style.theme_use(nuevo_tema)


def exit_focus(event=None):
    root.focus_set()


def execute_command():
    #query_output_panel.text.config(state="normal")
    content = query_output_panel.get("1.0", "end").strip()
    #query_output_panel.text.config(state="disabled")

    if not content:
        lbl_msg = ttk.Label(root, text="⚠️ No hay comando para ejecutar", bootstyle=WARNING)
        lbl_msg.place(relx=0.5, rely=0.95, anchor="center")
        root.after(2000, lbl_msg.destroy)
        return

    output = current_service.execute(content)

    execution_output_panel.text.config(state="normal")
    execution_output_panel.delete("1.0", "end")
    execution_output_panel.insert("end", output)
    execution_output_panel.text.config(state="disabled")


def on_tab_change(event):
    global current_service_name, current_service, tree

    tab_id = notebook.select()
    tab_text = notebook.tab(tab_id, "text")

    current_service_name = tab_text
    current_service = container.get(current_service_name)

    lbl_acciones.config(text=f"Acciones de {tab_text.capitalize()}")

    for item in tree.get_children():
        tree.delete(item)
    
    refresh_tree()

def refresh_tree():
    c = 0
    for resource, categories in current_service.actions.items():
        cat_id = tree.insert("", "end", text=resource, open=True)
        for category, actions in categories.items():
            category_name = category.split(" ", 1)[-1]
            sub_id = tree.insert(cat_id, "end", text=category, open=True, tags=(category_name,))
            if category_name in subresource_colors:
                tree.tag_configure(category_name, **subresource_colors[category_name])
            for action in actions:
                tree.insert(sub_id, "end", id=f"tree-action-label-{c}", text=action)
                c += 1


# -------------------------- UI --------------------------
root = ttk.Window(themename="flatly")
root.title("Generador gcloud")
root.geometry("1100x700")

root.bind("<Control-g>", lambda e: generate_command())
root.bind("<Return>", lambda e: generate_command())
root.bind("<Escape>", exit_focus)

default_font = tkfont.nametofont("TkDefaultFont")
default_font.configure(size=12)
root.style.configure("TButton", font=("Segoe UI", 12, "bold"))
root.style.configure("Treeview", font=("Consolas", 11))

# Frame superior con tema + notebook
frame_header = ttk.Frame(root)
frame_header.pack(side="top", fill="x", padx=10, pady=5)

# --- selector de temas ---
ttk.Label(frame_header, text="Tema:", bootstyle=INFO).pack(side="left", padx=5)
combo_theme = ttk.Combobox(frame_header, values=root.style.theme_names(),
                           state="readonly", width=15, bootstyle=PRIMARY)
combo_theme.set("flatly")
combo_theme.pack(side="left")
combo_theme.bind("<<ComboboxSelected>>", cambiar_tema)

# --- notebook tabs ---
notebook = ttk.Notebook(frame_header, bootstyle=PRIMARY)
notebook.pack(side="left", fill="x", expand=True, padx=20)

for svc in container.list_services():
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=svc)

notebook.bind("<<NotebookTabChanged>>", on_tab_change)

# Panel principal (izq/der)
main_pane = ttk.Panedwindow(root, orient=HORIZONTAL)
main_pane.pack(fill="both", expand=True, padx=10, pady=10)

# Panel izquierdo
frame_left = ttk.Frame(main_pane, padding=10)
main_pane.add(frame_left, weight=1)

lbl_acciones = ttk.Label(frame_left, text="Acciones de Storage",
                         bootstyle=INFO, font=("Segoe UI", 13, "bold"))
lbl_acciones.pack(anchor="w", pady=(0, 5))

tree = ttk.Treeview(frame_left, bootstyle=PRIMARY)
tree.pack(fill="both", expand=True)
tree.bind("<<TreeviewSelect>>", on_tree_select)

refresh_tree()

# Panel derecho
frame_right = ttk.Frame(main_pane, padding=10)
main_pane.add(frame_right, weight=3)

frame_params = ttk.LabelFrame(frame_right, text="Parámetros")
frame_params.pack(fill="x", pady=5)

# query_output_panel = comando generado (readonly)
query_output_panel = ScrolledText(frame_right, width=45, height=14, wrap="word", bootstyle=LIGHT)
query_output_panel.pack(fill="both", expand=False, pady=5)
query_output_panel.text.config(state="normal")

btn_frame = ttk.Frame(frame_right, padding=20)
btn_frame.pack(pady=5)

ttk.Button(
    frame_right, 
    text="📋 Copiar", 
    bootstyle=INFO,
    command=copiar_comando
    ).pack(side="left", padx=5)
ttk.Button(
    frame_right,
    text="▶ Ejecutar", 
    bootstyle=PRIMARY,
    command=execute_command
    ).pack(side="left", padx=5)

# execution_output_panel = ejecución comando (readonly)
execution_output_panel = ScrolledText(frame_right, width=45, height=12, wrap="word", bootstyle=SECONDARY)
execution_output_panel.pack(fill="both", expand=False, pady=5)
execution_output_panel.text.config(state="disabled")

root.mainloop()
