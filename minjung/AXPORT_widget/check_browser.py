"""Browser regression against an isolated local server with mocked LLM only."""
import json
import logging
import os
from pathlib import Path
import sys
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from minjung.AXPORT_widget.test_integration import load_app
from minjung.AXPORT_widget import chatbot

OUT = ROOT / 'minjung' / 'AXPORT_widget' / 'test-results'
OUT.mkdir(exist_ok=True)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
calls = []


def fake_answer(messages, language):
    calls.append({'messages': messages, 'language': language})
    return f'검증용 AI 응답 ({language}): 현황 → 원인 → 영향 → 대응방안\n<img src=x onerror=alert(1)>'


with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-test', 'OPENAI_MODEL': 'offline-test'}), patch.object(chatbot, 'generate_answer', side_effect=fake_answer):
    app = load_app('live')
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url + '/app')
            page.wait_for_function('window.JunheeDashboard?.ready()')
            expect(page.locator('#sx-board')).to_be_visible()
            expect(page.locator('#analysis-window')).to_be_hidden()
            expect(page.locator('#sx-fx-rows .sx-rate')).to_have_count(3)
            expect(page.locator('#sx-fx-badge')).to_have_text('예시 데이터')
            expect(page.locator('#sx-weather-rows tr')).to_have_count(4)
            expect(page.locator('#sx-clocks time').first).not_to_have_text('--:--:--')
            ids = page.locator('[id]').evaluate_all('nodes => nodes.map(node => node.id)')
            assert len(ids) == len(set(ids)), 'Duplicate DOM IDs'
            page.screenshot(path=str(OUT / 'desktop.png'), full_page=True)

            # New upload card must still use the team sample and analysis gate.
            page.locator('#sx-sample').click()
            page.locator('#sx-form button[type="submit"]').click()
            page.wait_for_function('JunheeDashboard.current() !== null')
            expect(page.locator('#analysis-window')).to_be_visible()
            page.locator('#close-window-btn').click()
            page.locator('.desktop-icon[data-id="analysis"]').click()
            expect(page.locator('#analysis-window')).to_be_visible()
            page.locator('#close-window-btn').click()

            # Widget state persists and restores independently from file trash.
            page.locator('[data-sx-delete="fx"]').click()
            page.reload()
            expect(page.locator('[data-sx-widget="fx"]')).to_be_hidden()
            page.locator('.desktop-icon[data-id="trash"]').click()
            page.locator('#sx-restore-all').click()
            page.locator('#sx-trash-close').click()
            expect(page.locator('[data-sx-widget="fx"]')).to_be_visible()
            handle = page.locator('[data-sx-widget="news"] .sx-handle')
            if page.locator('#sx-edit').get_attribute('aria-pressed') != 'true':
                page.locator('#sx-edit').click()
            handle.focus()
            handle.press('ArrowDown')
            assert page.evaluate("JSON.parse(localStorage.getItem('axsx.team.widgets.v1')).positions.news.y >= 0")
            page.locator('#sx-reset').click()
            page.select_option('#axp-language', 'en')
            expect(page.locator('#sx-fx-title')).to_have_text('Foreign exchange')
            page.select_option('#axp-language', 'ko')

            # Real frontend -> local API -> mocked provider, with history and safe text.
            page.locator('.axchat-launcher').click()
            page.locator('.axchat-form textarea').fill('반도체 재고가 증가하면 현금흐름은?')
            page.locator('.axchat-form button').click()
            expect(page.locator('.axchat-answer')).to_contain_text('검증용 AI 응답')
            expect(page.locator('.axchat-answer img')).to_have_count(0)
            page.locator('.axchat-form textarea').fill('다음 대응은?')
            page.locator('.axchat-form button').click()
            expect(page.locator('.axchat-answer').last).to_contain_text('검증용 AI 응답')
            assert len(calls[-1]['messages']) == 3
            page.select_option('#axp-language', 'en')
            expect(page.locator('.axchat-answer').first).to_contain_text('(ko)')
            page.locator('.axchat-form textarea').fill('What should the CFO do?')
            page.locator('.axchat-form button').click()
            expect(page.locator('.axchat-answer').last).to_contain_text('(en)')
            page.screenshot(path=str(OUT / 'chat.png'))

            # Failure stays an error, retries, and never changes old AI answers.
            page.route('**/api/chat', lambda route: route.fulfill(status=503, content_type='application/json', body='{"code":"not_configured"}'))
            page.locator('.axchat-form textarea').fill('Retry test')
            page.locator('.axchat-form button').click()
            expect(page.locator('.axchat-answer').last).to_contain_text('AI is not configured')
            page.unroute('**/api/chat')
            page.locator('.axchat-retry').click()
            expect(page.locator('.axchat-answer').last).to_contain_text('검증용 AI 응답')
            page.locator('.axchat-close').click()
            page.locator('.axchat-launcher').click()
            page.locator('.axchat-form textarea').fill('New conversation')
            page.locator('.axchat-form button').click()
            expect(page.locator('.axchat-answer')).to_contain_text('검증용 AI 응답')
            assert len(calls[-1]['messages']) == 1
            page.locator('.axchat-close').click()

            # Mobile and home integration.
            page.set_viewport_size({'width': 390, 'height': 844})
            page.reload()
            expect(page.locator('#sx-board')).to_be_visible()
            page.screenshot(path=str(OUT / 'mobile.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.goto(url + '/')
            expect(page.locator('#sx-board')).to_have_count(0)
            page.locator('.axchat-launcher').click()
            expect(page.locator('#axchat-panel')).to_be_visible()
            page.locator('.axchat-form textarea').fill('반도체 공급망 위험은?')
            page.locator('.axchat-form button').click()
            expect(page.locator('.axchat-answer')).to_contain_text('검증용 AI 응답')
            assert not errors, errors
            (OUT / 'browser-check.json').write_text(json.dumps({'status': 'passed', 'javascript_errors': errors, 'mock_chat_calls': len(calls), 'screenshots': ['desktop.png', 'chat.png', 'mobile.png']}, ensure_ascii=False, indent=2), encoding='utf-8')
            print('PASS: widgets, demo labels, sample analysis, restore, keyboard move, languages, chat history/retry/reset, mobile and home; no JS errors. LLM mocked.')
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
