"""Connect widgets when the team's original app.py is run directly."""
import os
from pathlib import Path
from .sx_widgets import attach


def load_root_env(root):
    """Read only root .env; existing OS environment values take precedence."""
    env_path = Path(root) / '.env'
    if env_path.is_file():
        for line in env_path.read_text(encoding='utf-8-sig').splitlines():
            name, separator, value = line.partition('=')
            if separator and name.strip().isidentifier():
                os.environ.setdefault(name.strip(), value.strip().strip('\"\''))


def connect_dashboard(app):
    """Connect once, including when the preview imports the integrated app."""
    if app.extensions.get('axsx_widgets_attached'):
        return
    load_root_env(app.root_path)
    attach(app)
