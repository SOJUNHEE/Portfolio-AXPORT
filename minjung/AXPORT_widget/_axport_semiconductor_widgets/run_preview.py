"""Read the real team app; add widgets only in this isolated preview process."""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def create_app(project_root):
    root = Path(project_root).resolve()
    source = root / 'app.py'
    if not source.is_file():
        raise ValueError('Specify the team project folder containing app.py')
    # ONE .env, at the real project root. Never read/create a nested .env.
    env = root / '.env'
    if env.is_file():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            name, sep, value = line.partition('=')
            if sep and name.strip().isidentifier():
                os.environ.setdefault(name.strip(), value.strip().strip('\"\''))
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('axsx_team_app', source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not module.app.extensions.get('axsx_widgets_attached'):
        from sx_widgets import attach
        attach(module.app)
    return module.app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--port', type=int, default=5075)
    args = parser.parse_args()
    create_app(args.project_root).run(host='127.0.0.1', port=args.port, debug=False, load_dotenv=False)
