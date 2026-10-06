"""Check the running local chat; never print credentials or raw errors."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:5073'


def main():
    lines = (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines()
    settings = dict(line.split('=', 1) for line in lines if '=' in line and not line.startswith('#'))
    secret = settings.get('OPENAI_API_KEY', '').strip()
    if not secret:
        print('FAIL: server key is not configured')
        return 1
    # Scan only tracked files, public assets, and app logs; print paths, not lines.
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    candidates = {ROOT / name for name in tracked if name}
    candidates.update((ROOT / 'static').rglob('*'))
    candidates.update((ROOT / 'instance').glob('*.log'))
    candidates.update((ROOT / 'minjung' / 'AXPORT_widget').rglob('*'))
    leaked = [str(path.relative_to(ROOT)) for path in candidates if path.is_file() and secret.encode() in path.read_bytes()]
    if leaked:
        print('FAIL: credential found outside root .env in', ', '.join(leaked))
        return 1
    ignored = subprocess.run(['git', 'check-ignore', '-q', '.env'], cwd=ROOT).returncode == 0
    if not ignored or '.env' in tracked:
        print('FAIL: .env Git exclusion')
        return 1
    for path in ('/', '/app', '/static/js/chatbot.js'):
        with urlopen(BASE + path, timeout=10) as response:
            body = response.read().decode('utf-8')
        if secret in body:
            print('FAIL: secret in public response')
            return 1
        if path == '/app' and ('data-chat-mode="live"' not in body or 'sx-board' not in body):
            print('FAIL: running server lacks live chat or widgets')
            return 1
    for path in ('/.env', '/static/.env', '/instance/axport-server.log'):
        try:
            with urlopen(BASE + path, timeout=10):
                print('FAIL: private path is accessible')
                return 1
        except HTTPError as error:
            if error.code != 404:
                print('FAIL: unexpected private-path status', error.code)
                return 1
    payload = json.dumps({'question': '반도체 산업 전문 어드바이저로서 어떤 도움을 줄 수 있나요? 한국어로 두 문장만 답하세요.', 'language': 'ko', 'history': []}).encode()
    request = Request(BASE + '/api/chat', data=payload, headers={'Content-Type': 'application/json', 'Origin': BASE}, method='POST')
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        result = json.loads(error.read())
        code = result.get('code', 'unknown')
        print('Live chat failed:', error.code, code if isinstance(code, str) and len(code) < 60 and secret not in code else 'redacted')
        return 1
    except (URLError, TimeoutError):
        print('Live chat failed: connection/timeout')
        return 1
    answer = result.get('answer', '')
    if result.get('mode') != 'live' or not answer or secret in answer:
        print('FAIL: invalid live response')
        return 1
    print('PASS: live AI response, widgets, private-path denial, Git exclusion, no key in source/assets/logs/public responses.')
    print('Model:', settings.get('OPENAI_MODEL', 'configured'))
    print('Reply:', answer[:600])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
