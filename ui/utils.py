import re

# Font styles
SERVICE_HEADER_FONT_STYLE = ("Segoe UI", 16, "bold")
RESOURCE_LABEL_FONT_STYLE = ("Segoe UI", 14, "bold")
CATEGORY_LABEL_FONT_STYLE = ("Segoe UI", 12, "bold")
ACTION_LABEL_FONT_STYLE = ("Segoe UI", 10, "bold")

# Category icons for visual identification
CATEGORY_ICONS = {
    "reading": "📖",        # Book - for reading/querying
    "creation": "➕",       # Plus - for creation
    "modification": "✏️",  # Pencil - for modification/editing
    "revoke": "🚫",        # Prohibited - for revoke/removal
    "assignment": "🔐",    # Lock - for assignment/permissions
}

def get_category_icon(category_name: str) -> str:
    """Get icon for a category based on its name."""
    category_lower = category_name.lower()
    for key, icon in CATEGORY_ICONS.items():
        if key in category_lower:
            return icon
    return "📋"  # Default clipboard icon

def strip_icon(text: str) -> str:
    """Remove icon emoji/symbols from text."""
    # Remove emoji (Unicode emoji range) at start followed by space
    text = re.sub(r'^[\U0001F300-\U0001F9FF]\s+', '', text)
    # Remove specific symbols we use (folder, bullet, etc.)
    text = re.sub(r'^[📁📖➕✏️🚫🔐📋▸]\s+', '', text)
    # Remove any other common symbols at start followed by space
    text = re.sub(r'^[\u2000-\u2BFF]\s+', '', text)
    return text.strip()