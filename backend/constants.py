ACTIONS_FILENAME = "actions.json"
PARAMETERS_FILENAME = "params.json"
GCP_CREDENTIALS_FILENAME = "igen-bknd-001-dev-f73009db89a8.json"

emoji_map = {
    "🔎": ":magnifying_glass_tilted_left:",
    "📤": ":outbox_tray:",
    "📝": ":memo:",
    "❌": ":cross_mark:",
    "🔐": ":locked:",
    "⚙️": ":gear:",
    "➕": ":heavy_plus_sign:",
    "➖": ":heavy_minus_sign:",
    "📋": ":clipboard:",
    "✅": ":check_mark_button:",
}

# --- Colores por subcategoría ---
subcategory_colors = {
    "Consulta":      {"foreground": "#1E90FF"},  # azul
    "Creación":      {"foreground": "#2E8B57"},  # verde
    "Modificación":  {"foreground": "#FF8C00"},  # naranja
    "Eliminación":   {"foreground": "#DC143C"},  # rojo
    "Seguridad":     {"foreground": "#8B008B"},  # morado
    "Configuración": {"foreground": "#4682B4"},  # azul acero
    "Transferencia": {"foreground": "#008B8B"},  # cian oscuro
    "Recuperación":  {"foreground": "#556B2F"},  # verde oliva
    "Control":       {"foreground": "#B8860B"},  # dorado
    "Revocación":    {"foreground": "#A52A2A"},  # marrón
    "Asignación":    {"foreground": "#800000"},  # burdeos
    "Gestión":       {"foreground": "#2F4F4F"}   # gris pizarra oscuro
}