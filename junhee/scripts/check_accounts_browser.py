# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 계정·폴더 기능 브라우저 점검. Supabase 만 가짜(메모리)로 두고 실제 앱을 127.0.0.1:5098 에 띄운다.

검사: 회원가입 → 인증 메일 링크 → 로그인 → 우클릭 새 폴더 → 파일을 폴더로 끌기 → 폴더 열기 → 이름 바꾸기 → 삭제(확인 창) →
      샘플 분석 → 로그아웃 → 다시 로그인 시 폴더·파일·휴지통·분석이 그대로인지 → JavaScript 오류 0.
실행: python junhee/scripts/check_accounts_browser.py   (앱을 따로 띄우지 않는다)
"""
import copy
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'junhee' / 'test-results'
OUT.mkdir(exist_ok=True)
os.environ.update({'SUPABASE_URL': 'https://fake-project.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'sb_publishable_fake',
                   'FLASK_SECRET_KEY': 'k' * 48, 'SESSION_COOKIE_SECURE': 'false',
                   'AXPORT_AUTH_DB': str(Path(tempfile.mkdtemp()) / 'auth.sqlite3'),
                   'AXPORT_ANALYSIS_DB': str(Path(tempfile.mkdtemp()) / 'analysis.sqlite3'),
                   'UN_COMTRADE_API_KEY': '', 'KCS_TRADE_API_KEY': '', 'ECOS_API_KEY': '', 'LAW_API_KEY': '',  # 외부 호출 없이
                   'AXPORT_DATA_MODE': 'demo', 'AXPORT_CHAT_MODE': 'demo'})

from app import app  # noqa: E402
from junhee.server.auth_core import AuthError  # noqa: E402
from junhee.server.workspace_store import WorkspaceError  # noqa: E402

EMAIL, PASSWORD = 'tester@example.com', 'Passw0rd!x'
NEW_PASSWORD = 'NewPassw0rd!y'  # (2026-09-29) 계정 창 비밀번호 변경 뒤 로그인에 씀
STATE = {'password': PASSWORD}


class FakeSupabase:
    def __init__(self):
        self.users, self.mails = {}, []

    def sign_up(self, email, password, redirect_to):
        self.users[email] = {'id': '00000000-0000-0000-0000-00000000000%d' % (len(self.users) + 1), 'email': email,
                             'password': password, 'confirmed': False}
        self.mails.append((email, redirect_to + '?token_hash=' + 'ab' * 20 + '&type=email'))
        return {'id': self.users[email]['id']}

    def resend_signup(self, email, redirect_to):
        return {}

    def confirm_email(self, token_hash):
        email = self.mails[-1][0]
        self.users[email]['confirmed'] = True
        return {'user': {'id': self.users[email]['id'], 'email': email, 'email_confirmed_at': 'now'}, 'access_token': 'verify'}

    def sign_in(self, email, password):
        u = self.users.get(email)
        if not u or u['password'] != password or not u['confirmed']:
            raise AuthError('invalid_credentials', 401)
        return {'access_token': 'tok:' + email, 'refresh_token': 'r', 'expires_in': 3600}

    def get_user(self, token):
        u = self.users.get(token.split(':', 1)[1]) if token.startswith('tok:') else None
        if not u:
            raise AuthError('invalid_credentials', 401)
        return {'id': u['id'], 'email': u['email']}

    def sign_out(self, token):
        return None

    def update_password(self, token, password):
        u = self.users.get(token.split(':', 1)[1]) if token.startswith('tok:') else None
        if not u:
            raise AuthError('invalid_session', 401)
        if u['password'] == password:
            raise AuthError('same_password', 400)
        u['password'] = password
        return {'id': u['id'], 'email': u['email']}


class MemoryRepo:
    def __init__(self):
        self.rows = {}

    def load(self, user_id, token):
        return copy.deepcopy(self.rows.get(user_id))

    def save(self, user_id, token, state, revision):
        row = self.rows.get(user_id)
        if (revision == 0 and row) or (revision and (not row or row['revision'] != revision)):
            raise WorkspaceError('conflict', 409)
        self.rows[user_id] = {'user_id': user_id, 'revision': revision + 1, 'state': copy.deepcopy(state)}
        return copy.deepcopy(self.rows[user_id])


class MemoryAssessments:
    def __init__(self):
        self.docs = {}

    def save(self, user_id, token, aid, doc):
        self.docs[(user_id, aid)] = copy.deepcopy(doc)

    def load(self, user_id, token, aid):
        return copy.deepcopy(self.docs.get((user_id, aid)))

    def delete(self, user_id, token, aid):
        self.docs.pop((user_id, aid), None)


fake, repo, assessments = FakeSupabase(), MemoryRepo(), MemoryAssessments()
app.extensions['junhee_accounts']['provider'] = fake
app.extensions['junhee_workspace'] = repo
app.extensions['junhee_analysis'].repository = assessments
EXAMPLE = ROOT / 'static' / 'samples' / '기업데이터_예시1_한울메모리.xlsx'

from werkzeug.serving import make_server  # noqa: E402
server = make_server('127.0.0.1', 5098, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:5098'

from playwright.sync_api import sync_playwright  # noqa: E402

results = []


def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print(('PASS ' if ok else 'FAIL ') + name + (' · ' + str(detail) if detail else ''))


def launch(p):
    for ch in ('msedge', 'chrome'):
        try:
            return p.chromium.launch(channel=ch, headless=True)
        except Exception:
            continue
    return p.chromium.launch(headless=True)


def icon_center(page, item_id):
    box = page.locator(f'#desktop-icons [data-id="{item_id}"]').bounding_box()
    return box['x'] + box['width'] / 2, box['y'] + box['height'] / 2


def blank_point(page):
    return page.evaluate("""() => {
      const r = document.getElementById('desktop').getBoundingClientRect();
      for (let x = r.left + 40; x < r.left + 700; x += 37) for (let y = r.top + 40; y < r.bottom - 40; y += 29) {
        const el = document.elementFromPoint(x, y);
        if (el && ['desktop-icons', 'desktop', 'sx-canvas'].includes(el.id)) return [x, y];
      }
      return null; }""")


def login(page):
    page.goto(BASE + '/app')
    page.fill('#login-dialog input[name=email]', EMAIL)
    page.fill('#login-dialog input[name=password]', STATE['password'])
    page.click('#login-dialog button[type=submit]')
    page.wait_for_selector('#desktop-icons .desktop-icon')
    page.wait_for_function('window.JunheeFiles && window.AXWorkspace')


def main():
    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='ko-KR')
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and 'Failed to load resource' not in m.text and errors.append(m.text))  # 인증 전 로그인 401 은 의도한 응답

        # 1) 로그인 필수 화면
        page.goto(BASE + '/app')
        check('비로그인 /app → 로그인 창', page.is_visible('#login-dialog form[action="/auth/login"]'))
        check('비로그인 /app 에 분석 창 없음', page.locator('#analysis-window').count() == 0)
        page.screenshot(path=str(OUT / 'accounts-01-login.png'))

        # 2) 회원가입 → 인증 메일
        page.click('[data-auth-tab-link="signup"]')
        page.fill('#signup-form input[name=email]', EMAIL)
        page.fill('#signup-password', PASSWORD)
        page.fill('#signup-password-confirm', PASSWORD)
        page.click('#signup-form button[type=submit]')
        page.wait_for_selector('#signup-confirmation-title')
        check('가입 → 인증 메일 안내', '인증 메일을 보냈습니다' in page.inner_text('#login-dialog'))
        check('인증 메일 링크 주소', fake.mails and fake.mails[-1][1].startswith(BASE + '/auth/confirm?token_hash='), fake.mails[-1][1] if fake.mails else '')
        check('재발송 버튼 60초 대기', page.is_disabled('#resend-button'))
        page.screenshot(path=str(OUT / 'accounts-02-signup-pending.png'))
        # 인증 전 로그인 실패
        page.goto(BASE + '/app')
        page.fill('#login-dialog input[name=email]', EMAIL)
        page.fill('#login-dialog input[name=password]', PASSWORD)
        page.click('#login-dialog button[type=submit]')
        check('인증 전 로그인 거부', page.is_visible('#login-dialog .form-error'))
        # 메일의 링크 클릭
        page.goto(fake.mails[-1][1])
        check('인증 링크 → 인증 완료 안내', '이메일 인증이 완료되었습니다' in page.inner_text('#login-dialog'))
        page.screenshot(path=str(OUT / 'accounts-03-confirmed.png'))

        # 3) 로그인 — 인증 완료 화면에서 바로(실제 사용자 흐름)
        page.fill('#login-dialog input[name=email]', EMAIL)
        page.fill('#login-dialog input[name=password]', PASSWORD)
        page.click('#login-dialog button[type=submit]')
        page.wait_for_selector('#desktop-icons .desktop-icon')
        page.wait_for_function('window.JunheeFiles && window.AXWorkspace')
        check('로그인 → 워크스페이스', page.locator('#analysis-window').count() == 1 and page.locator('#desktop-icons .desktop-icon').count() >= 5)
        check('계정 버튼에 이메일', page.get_attribute('#profile-btn', 'title') == EMAIL)
        page.wait_for_timeout(1500)
        user_id = fake.users[EMAIL]['id']
        pos = page.evaluate("Object.fromEntries([...document.querySelectorAll('#desktop-icons .desktop-icon')].map(b => [b.dataset.id, [b.offsetLeft, b.offsetTop]]))")
        files_ = sorted([k for k in pos if k.startswith('sample-')])
        check('바탕화면: 쓰는 회사 파일 3개만', files_ == ['sample-gaon', 'sample-mirinae', 'sample-nuri'], files_)
        sys_col = {pos[k][0] for k in ('analysis', 'upload', 'company-file', 'trash')}
        names_order = page.evaluate("[...document.querySelectorAll('#desktop-icons .desktop-icon')].filter(b => b.dataset.id.startsWith('sample-')).sort((a, b) => a.offsetLeft - b.offsetLeft || a.offsetTop - b.offsetTop).map(b => b.innerText.trim())")
        check('바탕화면 정렬(기본 아이콘 한 줄 · 파일 이름순 다음 줄)', len(sys_col) == 1 and all(pos[k][0] > min(sys_col) for k in files_) and names_order == sorted(names_order), names_order)
        with page.expect_download() as dl:
            page.locator('#desktop-icons [data-id="sample-gaon"]').dblclick()
        check('파일 더블클릭 → 엑셀 파일 열기(내려받기)', dl.value.suggested_filename == '기업데이터_가상_가온반도체.xlsx', dl.value.suggested_filename)
        check('더블클릭은 업로드 창을 열지 않음', page.locator('#upload-dialog[open]').count() == 0)
        check('첫 로그인 기본 바탕화면 저장', user_id in repo.rows, repo.rows.get(user_id, {}).get('revision'))

        # 4) 우클릭 → 새 폴더
        x, y = blank_point(page)
        page.mouse.click(x, y, button='right')
        page.wait_for_selector('#junhee-menu[open]')
        page.screenshot(path=str(OUT / 'accounts-04-context-menu.png'))
        page.click('#junhee-menu [data-menu="new-folder"]')
        page.wait_for_selector('#junhee-rename[open]')
        check('새 폴더 이름 기본값', page.input_value('#junhee-rename-input') == '새 폴더')
        page.fill('#junhee-rename-input', '미국 거래처')
        page.click('#junhee-rename button[type=submit]')
        folder_id = page.evaluate("JunheeFiles.folders()[0] && JunheeFiles.folders()[0].id")
        check('우클릭 새 폴더 생성', folder_id and page.locator(f'#desktop-icons [data-id="{folder_id}"]').inner_text().strip() == '미국 거래처')

        # 5) 파일을 폴더로 끌기
        sx, sy = icon_center(page, 'sample-nuri')
        fx, fy = icon_center(page, folder_id)
        page.mouse.move(sx, sy)
        page.mouse.down()
        for i in range(1, 16):
            page.mouse.move(sx + (fx - sx) * i / 15, sy + (fy - sy) * i / 15)
        page.mouse.up()
        page.wait_for_timeout(200)
        check('파일을 폴더로 이동', page.locator('#desktop-icons [data-id="sample-nuri"]').count() == 0)
        page.locator(f'#desktop-icons [data-id="{folder_id}"]').dblclick()
        page.wait_for_selector('#files-dialog[open]')
        check('폴더 열기 → 안의 파일', '누리하이테크' in page.inner_text('#files-list'))
        page.screenshot(path=str(OUT / 'accounts-05-folder-open.png'))
        page.click('#files-dialog .modal-close')

        # 6) 이름 바꾸기 (폴더·파일)
        fx, fy = icon_center(page, folder_id)
        page.mouse.click(fx, fy, button='right')
        page.click('#junhee-menu [data-menu="rename"]')
        page.fill('#junhee-rename-input', '미국 바이어')
        page.click('#junhee-rename button[type=submit]')
        check('폴더 이름 바꾸기', page.locator(f'#desktop-icons [data-id="{folder_id}"]').inner_text().strip() == '미국 바이어')
        hx, hy = icon_center(page, 'sample-gaon')
        page.mouse.click(hx, hy, button='right')
        page.click('#junhee-menu [data-menu="rename"]')
        page.fill('#junhee-rename-input', 'bad/name')
        page.click('#junhee-rename button[type=submit]')
        check('쓸 수 없는 이름 거부', page.inner_text('#junhee-rename-error') != '')
        page.fill('#junhee-rename-input', '가온_미국용.xlsx')
        page.click('#junhee-rename button[type=submit]')
        check('파일 이름 바꾸기', page.locator('#desktop-icons [data-id="sample-gaon"]').inner_text().strip() == '가온_미국용.xlsx')

        # 7) 삭제 (확인 창)
        nx, ny = icon_center(page, 'sample-mirinae')
        page.mouse.click(nx, ny, button='right')
        page.click('#junhee-menu [data-menu="delete"]')
        page.wait_for_selector('#jd-confirm-dialog[open]')
        page.screenshot(path=str(OUT / 'accounts-06-delete-confirm.png'))
        page.click('#jd-confirm-dialog button:has-text("취소")') if page.locator('#jd-confirm-dialog button:has-text("취소")').count() else page.keyboard.press('Escape')
        page.wait_for_timeout(150)
        check('삭제 취소 → 그대로', page.locator('#desktop-icons [data-id="sample-mirinae"]').count() == 1)
        page.mouse.click(nx, ny, button='right')
        page.click('#junhee-menu [data-menu="delete"]')
        page.wait_for_selector('#jd-confirm-dialog[open]')
        page.click('#jd-confirm-dialog button:has-text("삭제")')
        page.wait_for_timeout(150)
        check('삭제 확인 → 휴지통', page.locator('#desktop-icons [data-id="sample-mirinae"]').count() == 0
              and page.evaluate("AXWorkspace.files().find(f => f.id === 'sample-mirinae').trash"))

        # 8) 이름을 바꾼 샘플 파일 분석
        gx, gy = icon_center(page, 'sample-gaon')
        page.mouse.click(gx, gy, button='right')
        page.click('#junhee-menu [data-menu="analyze"]')
        page.wait_for_selector('#upload-dialog[open]')
        page.click('#analysis-form button[type=submit]')
        try:  # 샘플도 엔진으로 계산(백그라운드 작업 + 1.5초 간격 확인)
            page.wait_for_function("document.getElementById('company-context').textContent !== '미선택'", timeout=120000)
        except Exception:
            print('upload-error:', page.inner_text('#upload-error'))
            raise
        company = page.inner_text('#company-context')
        check('이름 바꾼 샘플 분석(엔진)', company == '가온반도체' and page.evaluate("JunheeDashboard.current().score_source") == 'engine', company)
        page.wait_for_timeout(1500)  # 저장 대기

        # 8-1) (2026-09-29) 계정 창에서 비밀번호 변경 → 메일 인증 없이 바로 바뀜
        page.click('#profile-btn')
        page.wait_for_selector('#account-dialog[open]')
        page.fill('#new-password', NEW_PASSWORD)
        page.fill('#new-password-confirm', 'Mismatch0!')
        page.click('#password-submit')
        check('비밀번호 변경: 확인 불일치 안내', '일치하지 않습니다' in page.inner_text('#password-status'))
        page.fill('#new-password-confirm', NEW_PASSWORD)
        page.click('#password-submit')
        page.wait_for_selector('#password-status.demo-notice')
        check('비밀번호 변경: 바로 적용', fake.users[EMAIL]['password'] == NEW_PASSWORD and '바꿨습니다' in page.inner_text('#password-status'))
        check('비밀번호 변경: 입력칸 비움', page.input_value('#new-password') == '' and page.input_value('#new-password-confirm') == '')
        page.screenshot(path=str(OUT / 'accounts-06b-password-changed.png'))
        STATE['password'] = NEW_PASSWORD

        # 9) 로그아웃 → 다시 로그인(새 비밀번호)
        page.wait_for_selector('#account-dialog[open]')
        page.click('#account-dialog form[action="/auth/logout"] button[type=submit]')
        page.wait_for_selector('#login-dialog')
        check('로그아웃 → 로그인 화면', '로그아웃되었습니다' in page.inner_text('#login-dialog'))
        login(page)
        page.wait_for_function("document.getElementById('company-context').textContent !== '미선택'", timeout=60000)
        page.wait_for_timeout(300)
        names = page.evaluate("[...document.querySelectorAll('#desktop-icons .desktop-icon')].map(b => b.innerText.trim())")
        check('재로그인: 폴더 유지', '미국 바이어' in names, names)
        check('재로그인: 파일 이름 유지', '가온_미국용.xlsx' in names)
        check('재로그인: 폴더 안 파일 유지', page.evaluate("AXWorkspace.files().find(f => f.id === 'sample-nuri').parent_id") == folder_id)
        check('재로그인: 휴지통 유지', page.evaluate("AXWorkspace.files().find(f => f.id === 'sample-mirinae').trash"))
        check('재로그인: 분석 복원', page.inner_text('#company-context') == company and page.evaluate("JunheeDashboard.current().score_source") == 'engine', page.inner_text('#company-context'))
        page.click('#desktop-icons [data-id="analysis"]', click_count=2)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / 'accounts-07-relogin-restored.png'))

        # 10) 휴지통 → 폴더 삭제·복원
        page.click('#close-window-btn')  # 분석 창이 바탕화면 아이콘을 가리지 않게
        page.wait_for_timeout(200)
        fx, fy = icon_center(page, folder_id)
        page.mouse.click(fx, fy, button='right')
        page.click('#junhee-menu [data-menu="delete"]')
        page.wait_for_selector('#jd-confirm-dialog[open]')
        msg = page.inner_text('#jd-confirm-dialog')
        page.click('#jd-confirm-dialog button:has-text("삭제")')
        page.wait_for_timeout(150)
        check('폴더 삭제 확인 문구(안의 파일 수)', '안의 파일 1개' in msg, msg.replace('\n', ' ')[:80])
        # 휴지통 아이콘 한 번 클릭은 minjung 위젯의 휴지통(#sx-trash-dialog)을 먼저 열어 더블클릭이 막힌다 → 우클릭 메뉴 '열기'
        tx, ty = icon_center(page, 'trash')
        page.mouse.click(tx, ty, button='right')
        page.click('#junhee-menu [data-menu="open"]')
        page.wait_for_selector('#files-dialog[open]')
        check('휴지통에 폴더 표시', '미국 바이어' in page.inner_text('#files-list'))
        page.click(f'[data-folder-action="restore"][data-folder-id="{folder_id}"]')
        page.wait_for_timeout(150)
        page.click('#files-dialog .modal-close')
        check('폴더 복원(안의 파일 포함)', page.locator(f'#desktop-icons [data-id="{folder_id}"]').count() == 1
              and page.evaluate("!AXWorkspace.files().find(f => f.id === 'sample-nuri').trash"))


        # 11) 새 간편입력 양식 → 위젯 '기업 데이터 업로드'(바탕화면 업로드 아이콘과 연동) → 서버 분석 엔진 → 대시보드
        page.locator('#desktop-icons [data-id="upload"]').dblclick()
        page.wait_for_timeout(400)
        check('업로드 아이콘 → 위젯으로 이동(업로드 창 아님)', not page.evaluate("document.getElementById('upload-dialog').open")
              and page.evaluate("document.querySelector('[data-sx-widget=upload]').classList.contains('jd-drop-card')"))
        href = page.get_attribute('[data-sx-widget="upload"] a.jd-sx-btn', 'href') or ''
        with page.expect_download() as dl:
            page.click('[data-sx-widget="upload"] a.jd-sx-btn')
        saved = OUT / 'template-download-check.xlsx'
        dl.value.save_as(saved)
        import openpyxl
        wb = openpyxl.load_workbook(saved, read_only=True)
        check('양식 다운로드 = sanghyeob 간편입력 v2', href == '/static/templates/company-data-template.xlsx' and '간편입력' in wb.sheetnames, href)
        wb.close()
        page.evaluate("JunheeDashboard.openGuide()")
        page.wait_for_selector('#jd-guide-dialog[open]')
        g = page.inner_text('#jd-guide-dialog')
        check('업로드 가이드: 6개 절 · 대상국 5개 · 샘플 3개 · 내부 이름 없음',
              all(t in g for t in ('1. 올리는 방법', '2. 입력 항목', '3. 분석할 수 있는 대상국', '4. 판단 기준', '5. 빈 칸(결측) 처리', '6. 바탕화면 샘플 파일', '대상국 5개', '미리내전자'))
              and 'sanghyeob' not in g and '한빛' not in g and page.get_attribute('#jd-guide-dialog a.jd-guide-dl', 'href') == href, g[:60])
        page.click('#jd-guide-dialog .jd-close')
        page.set_input_files('#sx-file', str(EXAMPLE))
        page.wait_for_timeout(500)
        page.fill('#sx-company', '한울메모리')
        page.click('#sx-form .sx-primary')
        page.wait_for_function("document.getElementById('company-context').textContent === '한울메모리'", timeout=120000)
        check('새 양식 파일 엔진 분석 → 대시보드', page.evaluate("JunheeDashboard.current().score_source") == 'engine')
        page.wait_for_timeout(1200)
        ov = page.inner_text('#tab-content')
        check('종합 탭: 엔진 점수·등급 표시', '54.5' in ov and '판단 근거 부족' in ov, ov.replace(chr(10), ' ')[:160])
        check('종합 탭: 근거 없는 요인은 자료 부족', '자료' in ov)
        page.screenshot(path=str(OUT / 'accounts-08-engine-overview.png'))
        for tab in ('regulation', 'market', 'price', 'logistics', 'stability', 'overview'):
            page.click(f'#tab-{tab}')
            page.wait_for_timeout(400)
        check('상세 탭 5개 열기(엔진 문서)', page.inner_text('#tab-content').strip() != '')
        drawn = {}
        for tab in ('regulation', 'market', 'price', 'logistics', 'stability'):
            page.click(f'#tab-{tab}')
            page.wait_for_timeout(500)
            drawn[tab] = page.evaluate("[...document.querySelectorAll('#tab-content canvas.jd-detail-chart')].filter(cv => window.Chart && Chart.getChart(cv)).length")
        check('세부 탭 메인 차트(엔진 문서)', all(v >= 1 for v in drawn.values()), drawn)
        for lang in ('en', 'zh', 'ja', 'ko'):
            page.select_option('#axp-language', lang)
            page.wait_for_timeout(400)
            over = page.evaluate("[...document.querySelectorAll('#window-sidebar .side-link')].filter(b => b.scrollWidth > b.clientWidth + 1).map(b => b.innerText.trim())")
            if over:
                break
        check('언어 변경 시 사이드바 글자 넘침 없음', not over, over)
        hdr_hits = []
        for lang in ('en', 'ja', 'zh', 'ko'):
            page.select_option('#axp-language', lang)
            page.wait_for_timeout(500)
            hit = page.evaluate("""() => { const R = (e) => e.getBoundingClientRect(), tb = document.getElementById('sx-toolbar'), lc = document.querySelector('.workspace-language-control');
              if (!tb || !lc) return false; const a = R(tb), b = R(lc); return Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1; }""")
            if hit: hdr_hits.append(lang)
        check('언어 변경 시 머리글 도구 막대·언어 선택 겹침 없음', not hdr_hits, hdr_hits)
        page.click('#tab-overview')
        page.click('#tab-regulation'); page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / 'accounts-09-engine-regulation.png'))
        page.click('#tab-overview')
        page.click('.side-link[data-action="report"]')
        page.wait_for_selector('#report-dialog[open]')
        page.wait_for_timeout(600)
        rep = page.frame_locator('#report-preview').locator('body').inner_text()
        check('보고서(엔진 문서)', '한울메모리' in rep, rep[:80].replace(chr(10), ' '))
        page.click('#report-dialog .modal-close')
        eng_file = page.evaluate("AXWorkspace.context().fileId")
        page.wait_for_timeout(1500)
        page.click('#profile-btn')
        page.wait_for_selector('#account-dialog[open]')
        page.click('#account-dialog form[action="/auth/logout"] button[type=submit]')
        page.wait_for_selector('#login-dialog')
        login(page)
        page.wait_for_function("document.getElementById('company-context').textContent === '한울메모리'", timeout=20000)
        check('재로그인: 엔진 분석 복원', page.evaluate("JunheeDashboard.current().score_source") == 'engine'
              and page.evaluate(f"AXWorkspace.files().find(f => f.id === '{eng_file}').assessment_id") is not None)

        # 12) 결측 파일을 위젯에 끌어 놓기 → 결측 확인 창 → 그래도 진행 → 결측 표시, 중복 아이콘 없음
        if page.evaluate("!document.getElementById('analysis-window').hidden"):
            page.click('#close-window-btn')
        page.wait_for_timeout(200)
        # 7번에서 휴지통으로 보낸 결측 파일을 복원(우클릭 → 휴지통 열기 → 복원)
        tx, ty = icon_center(page, 'trash')
        page.mouse.click(tx, ty, button='right')
        page.click('#junhee-menu [data-menu="open"]')
        page.wait_for_selector('#files-dialog[open]')
        page.click('[data-file-action="restore"][data-file-id="sample-mirinae"]')
        page.wait_for_timeout(200)
        page.click('#files-dialog .modal-close')
        check('휴지통에서 파일 복원', page.locator('#desktop-icons [data-id="sample-mirinae"]').count() == 1)
        before = page.evaluate("document.querySelectorAll('#desktop-icons .desktop-icon').length")
        mx, my = icon_center(page, 'sample-mirinae')
        dz = page.locator('#sx-drop').bounding_box()
        page.mouse.move(mx, my)
        page.mouse.down()
        for i in range(1, 21):
            page.mouse.move(mx + (dz['x'] + dz['width'] / 2 - mx) * i / 20, my + (dz['y'] + dz['height'] / 2 - my) * i / 20)
        page.mouse.up()
        page.wait_for_timeout(1200)
        check('위젯에 파일 값 채움', page.input_value('#sx-company') == '미리내전자' and page.input_value('#sx-country') == 'US', page.input_value('#sx-company'))
        page.click('#sx-form .sx-primary')
        page.wait_for_selector('#jd-confirm-dialog[open]', timeout=20000)
        mc = page.inner_text('#jd-confirm-dialog')
        check('결측 확인 창(빈 셀·점수 영향)', '결측치가 있는 파일' in mc and '간편입력!B13' in mc and '점수에 영향 8건' in mc)
        page.click('#jd-confirm-dialog button:has-text("그래도 진행")')
        page.wait_for_function("document.getElementById('company-context').textContent === '미리내전자'", timeout=120000)
        after = page.evaluate("document.querySelectorAll('#desktop-icons .desktop-icon').length")
        page.wait_for_timeout(800)
        check('위젯 분석: 바탕화면 파일을 그대로 분석(중복 아이콘 없음)', after == before, (before, after))
        check('종합 탭 입력 결측 표시', '입력 결측' in page.inner_text('#tab-content'))
        page.click('#tab-price')
        page.wait_for_timeout(500)
        check('가격 탭 입력 결측 목록', '입력 결측' in page.inner_text('#tab-content') and '간편입력!B13' in page.inner_text('#tab-content'))
        page.click('#tab-overview')

        # 13) 바탕화면 '기업 파일 업로드' → 작업 데이터 폴더(junhee/data/samples/uploads)에 저장 → 아이콘 추가
        #     → 대시보드 '기업 데이터' 목록의 '종합 적합도' → 내려받기 없이 바로 종합 수출적합도
        from junhee.server import analysis as _an
        upload_dir = _an.COMPANY_FILE_DIR
        before_files = set(upload_dir.glob('*')) if upload_dir.exists() else set()
        if page.evaluate("!document.getElementById('analysis-window').hidden"):
            page.click('#close-window-btn')
        page.wait_for_timeout(200)
        labels = page.evaluate("Object.fromEntries(['upload', 'company-file'].map(id => [id, document.querySelector(`#desktop-icons [data-id='${id}']`).innerText.trim()]))")
        check('아이콘 이름: 기업 분석 데이터 업로드 · 기업 파일 업로드', labels == {'upload': '기업 분석 데이터 업로드', 'company-file': '기업 파일 업로드'}, labels)
        with page.expect_file_chooser() as fc:
            page.locator('#desktop-icons [data-id="company-file"]').dblclick()
        n0 = page.evaluate("AXWorkspace.files().length")
        fc.value.set_files(str(ROOT / 'static' / 'samples' / '기업데이터_가상_누리하이테크.xlsx'))
        page.wait_for_function(f"AXWorkspace.files().length > {n0}", timeout=30000)
        new_files = sorted(set(upload_dir.glob('*')) - before_files)
        added = page.evaluate("AXWorkspace.files().slice(-1)[0]")
        check('기업 파일 업로드 → 작업 데이터 폴더에 저장', len(new_files) == 1 and new_files[0].read_bytes() == (ROOT / 'static' / 'samples' / '기업데이터_가상_누리하이테크.xlsx').read_bytes(), [x.name for x in new_files])
        check('기업 파일 업로드 → 바탕화면 아이콘 추가', added['name'] == new_files[0].name if new_files else False, added.get('name'))
        check('저장 경로 안내', 'junhee/data/samples/uploads/' in page.inner_text('body'))
        page.wait_for_timeout(400)
        page.locator('#desktop-icons [data-id="analysis"]').dblclick()
        page.wait_for_timeout(400)
        page.click('.side-link[data-action="files"]')
        page.wait_for_selector('#files-dialog[open]')
        row_btn = f'#files-list [data-file-action="open"][data-file-id="{added["id"]}"]'
        check('기업 데이터 목록 버튼 = 종합 적합도', page.inner_text(row_btn).strip() == '종합 적합도')
        page.click(row_btn)
        stem = added['name'].rsplit('.', 1)[0]
        page.wait_for_function(f"document.getElementById('company-context').textContent === {stem!r}", timeout=120000)
        page.wait_for_timeout(800)
        check('종합 적합도 바로 계산(엔진) → 종합 탭', page.evaluate("JunheeDashboard.current().score_source") == 'engine'
              and page.evaluate("document.querySelector('#tab-overview').classList.contains('active') || document.querySelector('#tab-overview').getAttribute('aria-selected') === 'true'"))
        for x in new_files:  # 점검용으로 올린 파일은 지운다
            x.unlink()

        # 14) 사이드바: 기간 없음 · 엔진 지원 대상국 5개·HS6 20개 · 바꾸면 같은 파일로 다시 계산 · '세부사항 (항목 전체 보기)'
        side = page.inner_text('#window-sidebar .jd-side-analysis')
        check('사이드바에 기간 선택 없음', page.locator('#window-sidebar [data-jd="period"]').count() == 0 and '기간' not in side, side.replace(chr(10), ' ')[:80])
        c_opts = page.eval_on_selector_all('[data-jd="engine-country"] option', 'os => os.map(o => o.value)')
        h_opts = page.eval_on_selector_all('[data-jd="engine-hs"] option', 'os => os.map(o => o.value)')
        check('사이드바 대상국 = 엔진 지원 5개국', c_opts == ['US', 'CN', 'JP', 'DE', 'VN'], c_opts)
        check('사이드바 HS = 엔진 지원 HS6 20개', len(h_opts) == 20 and {'854231', '854232', '854110', '848620'} <= set(h_opts), len(h_opts))
        page.select_option('[data-jd="engine-country"]', 'JP')
        page.wait_for_function("JunheeDashboard.current().common.countries[0].iso2 === 'JP'", timeout=120000)
        page.wait_for_timeout(500)
        check('대상국 변경 → 다시 계산(일본)', page.input_value('[data-jd="engine-country"]') == 'JP' and not page.is_disabled('[data-jd="engine-country"]'))
        page.select_option('[data-jd="engine-hs"]', '854231')
        page.wait_for_function("String(JunheeDashboard.current().engine.hs) === '854231'", timeout=120000)
        page.wait_for_timeout(500)
        check('HS 변경 → 다시 계산(8542.31)', page.input_value('[data-jd="engine-hs"]') == '854231' and page.evaluate("AXWorkspace.files().find(f => f.analyzed).conditions.hs") == '854231')
        page.click('.side-link[data-action="items"]')
        page.wait_for_selector('#tab-content [data-key="items"]')
        secs = page.eval_on_selector_all('#tab-content [data-key="items"] section.jd-item', 'ss => ss.map(x => [x.dataset.key, x.querySelectorAll("tbody tr").length])')
        check('세부사항(항목 전체 보기): 다섯 영역 모두', [k for k, _ in secs] == ['regulation', 'market', 'price', 'logistics', 'stability'] and all(n > 0 for _, n in secs), secs)
        check('세부사항 화면에서 북마크 탭 선택 없음', page.locator('.bookmark-tabs button.selected').count() == 0)
        page.screenshot(path=str(OUT / 'accounts-09-all-items.png'))
        page.click('#tab-content [data-open-tab="market"]')
        page.wait_for_timeout(400)
        check('영역 버튼 → 해당 상세 탭', page.get_attribute('#tab-market', 'aria-selected') == 'true')
        check('오른쪽 아래 항목 전체 보기 버튼 없음(사이드바 세부사항으로 이동)', page.locator('#tab-content [data-jd="toggle-items"]').count() == 0)
        for tab in ('regulation', 'market', 'price', 'logistics', 'stability'):
            page.click(f'#tab-{tab}')
            page.wait_for_timeout(250)
            if page.locator('#tab-content .jd-items-head').count():  # 이전에 켜 둔 상태면 끈다
                page.click('.side-link[data-action="items"]')
                page.wait_for_timeout(250)
            page.click('.side-link[data-action="items"]')
            page.wait_for_timeout(400)
            rows = page.eval_on_selector_all(f'#tab-content .jd-items section.jd-item[data-key="{tab}"] tbody tr', 'r => r.length')
            badge = page.get_attribute('.side-link[data-action="items"]', 'title') or ''
            check(f'{tab} 탭: 사이드바 세부사항 → 이 파트 항목 전체', rows > 0 and page.get_attribute('.side-link[data-action="items"]', 'aria-pressed') == 'true'
                  and '/' in badge, (rows, badge))
        page.screenshot(path=str(OUT / 'accounts-10-part-items.png'))
        page.click('.side-link[data-action="items"]')
        page.wait_for_timeout(300)
        check('세부사항 다시 누르면 접힘', page.locator('#tab-content .jd-items-head').count() == 0
              and page.get_attribute('.side-link[data-action="items"]', 'aria-pressed') == 'false')
        w_hs = page.eval_on_selector_all('#jd-sx-hs option', 'os => os.length')
        w_ct = page.eval_on_selector_all('#sx-country option', 'os => os.map(o => o.value)')
        check('위젯 HS·대상국 = 엔진 지원 목록', w_hs >= 20 and 'TW' not in w_ct and set(w_ct) <= {'US', 'CN', 'JP', 'DE', 'VN'}, (w_hs, w_ct))

        check('JavaScript 오류 0', not errors, errors[:3])
        browser.close()



if __name__ == '__main__':
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    main()
    server.shutdown()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    sys.exit(1 if failed else 0)
