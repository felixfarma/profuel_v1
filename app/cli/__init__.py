# app/cli/__init__.py
from .seed import seed_group
from .export import export_group  # ← nuevo

def register_cli(app):
    """Registra los grupos y comandos CLI de la app."""
    app.cli.add_command(seed_group)
    app.cli.add_command(export_group)  # ← nuevo
