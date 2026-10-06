"""AXPORT workspace with optional market widgets and server-side AI chat."""
from flask import Flask, render_template
# (junhee) 2026-09-26 Contact Us 접수 라우트용 — Flask 기본 기능만 사용
import json as _json
import os as _os
import re as _re
import threading as _threading
import time as _time
from collections import deque as _deque
from datetime import datetime as _datetime, timezone as _timezone
from flask import jsonify, request

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.get('/')
def home():
    return render_template('home.html')

@app.get('/app')
def workspace():
    return render_template('workspace.html')


# (junhee) 2026-09-26 Contact Us 접수: instance/contact_messages.jsonl 에 한 줄씩 저장 (시연용, Render 무료 환경은 재배포 시 사라짐)
_CONTACT_TYPES = ("의견", "건의", "오류 제보", "기타")
_CONTACT_FIELDS = ("", "반도체 제조", "무역·수출", "물류·포워딩", "기타")
_CONTACT_EMAIL = _re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_contact_hits = {}
_contact_lock = _threading.Lock()


def _contact_limited(ip, limit=3, window=60):
    """같은 IP 에서 window 초 안에 limit 회를 넘기면 True."""
    now = _time.time()
    with _contact_lock:
        if len(_contact_hits) > 5000:  # (2026-09-27 배포 QA) 오래된 IP 기록 정리(메모리 상한)
            for key in [k for k, v in _contact_hits.items() if not v or now - v[-1] > window]:
                _contact_hits.pop(key, None)
        q = _contact_hits.setdefault(ip, _deque())
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        return False


@app.post('/api/contact')
def contact():
    ip = request.remote_addr or 'unknown'  # (2026-09-27 배포 QA) 클라이언트가 바꿀 수 있는 X-Forwarded-For 첫 값 대신(Render 는 ProxyFix 적용)
    if _contact_limited(ip):
        return jsonify(ok=False, error='too_many', message='같은 곳에서 1분에 3회까지만 보낼 수 있습니다. 잠시 후 다시 시도해 주세요.'), 429
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error='invalid', message='JSON 본문이 필요합니다.'), 400
    text = lambda k, n: str(data.get(k) or '')[:n].strip()
    if text('website', 200):  # honeypot: 봇이면 성공처럼 응답하고 저장하지 않는다
        return jsonify(ok=True)
    kind, field, name, email, message = text('type', 40), text('field', 40), text('name', 200), text('email', 320), str(data.get('message') or '').strip()
    consent = bool(data.get('consent'))
    errors = []
    if kind not in _CONTACT_TYPES:
        errors.append('의견 유형을 선택해 주세요.')
    if field not in _CONTACT_FIELDS:
        errors.append('소속 분야 값이 올바르지 않습니다.')
    if len(name) > 40:
        errors.append('이름 또는 닉네임은 40자 이내여야 합니다.')
    if email and not _CONTACT_EMAIL.match(email):
        errors.append('이메일 형식을 확인해 주세요.')
    if not 10 <= len(message) <= 1000:
        errors.append('내용은 10자 이상 1000자 이하여야 합니다.')
    if email and not consent:
        errors.append('이메일을 적은 경우 개인정보 수집·이용 동의가 필요합니다.')
    if errors:
        return jsonify(ok=False, error='invalid', message=' '.join(errors)), 400
    record = {'ts': _datetime.now(_timezone.utc).isoformat(timespec='seconds'), 'type': kind, 'field': field, 'name': name, 'email': email, 'message': message}
    _os.makedirs(app.instance_path, exist_ok=True)
    with open(_os.path.join(app.instance_path, 'contact_messages.jsonl'), 'a', encoding='utf-8') as fh:
        fh.write(_json.dumps(record, ensure_ascii=False) + '\n')
    return jsonify(ok=True)  # 저장 내용은 되돌려 주지 않는다

# Register for both python app.py and WSGI imports; keep team routes intact.
from minjung.AXPORT_widget._axport_semiconductor_widgets.app_connection import connect_dashboard
from minjung.AXPORT_widget.chatbot import attach_chatbot

connect_dashboard(app)
attach_chatbot(app)

# (junhee) 2026-09-27 회원가입·로그인(/app 로그인 필수). 코드는 junhee/server/ 에 있음
from junhee.server.accounts import attach_accounts
attach_accounts(app)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5073, debug=False, load_dotenv=False)
