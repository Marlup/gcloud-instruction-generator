def build_command(template: str, params: dict) -> str:
    """
    Construye un comando a partir de una plantilla y parámetros.
    - template: str con placeholders {param}
    - params: dict con los valores a insertar
    """
    return template.format(**params)
