"""Read-only integration checks against the actual team application."""
import argparse
import hashlib
from pathlib import Path
from run_preview import create_app

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[3])
    root=parser.parse_args().project_root.resolve()
    original_paths=[root/'app.py',root/'templates/workspace.html',root/'static/js/workspace.js',root/'static/css/workspace.css',root/'static/js/junhee-dashboard.js',root/'static/js/chatbot.js']
    before={path:hashlib.sha256(path.read_bytes()).hexdigest() for path in original_paths}
    app=create_app(root)
    client=app.test_client()
    original=client.get('/_axp_semiconductor/original')
    assert original.status_code==200
    preview=client.get('/app')
    assert preview.status_code==200
    html=preview.get_data(as_text=True)
    assert 'id="analysis-window" hidden' in html
    assert 'id="sx-board"' in html
    for script in ('workspace.js','junhee-dashboard.js','axport-i18n.js','chatbot.js'):
        assert script in html
        with client.get('/static/js/'+script) as response:
            assert response.status_code==200
            assert response.data==(root/'static/js'/script).read_bytes()
    assert client.get('/').status_code==200
    for name in ('widgets.css','widgets.js','widget-text.js'):
        with client.get('/_axp_semiconductor/assets/'+name) as response:
            assert response.status_code==200
    assert client.get('/_axp_semiconductor/data/news?language=unknown').status_code==400
    assert client.get('/_axp_semiconductor/data/unknown').status_code==404
    assert 'id="sx-board"' not in original.get_data(as_text=True)
    for path,digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    print('PASS: original home, original workspace, closed initial analysis, team JS bytes unchanged, new assets, request validation, no source writes.')
