"""Offline integration and chat boundary regression tests."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from flask import Flask
from minjung.AXPORT_widget import chatbot
from minjung.AXPORT_widget._axport_semiconductor_widgets.app_connection import connect_dashboard, load_root_env
from minjung.AXPORT_widget._axport_semiconductor_widgets.sx_widgets.providers import DataService, ProviderError
from minjung.AXPORT_widget._axport_semiconductor_widgets.sx_widgets.weather import build_report, validate_report, aggregate


def load_app(mode='demo', extra_env=None):
    with patch.dict(os.environ, {'AXPORT_DATA_MODE': 'demo', 'AXPORT_CHAT_MODE': mode, **(extra_env or {})}):
        spec = importlib.util.spec_from_file_location('axport_integration_test_app', ROOT / 'app.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.app.config['TESTING'] = True
        return module.app


class IntegrationTests(unittest.TestCase):
    def test_cross_site_and_rebinding_cannot_use_key(self):
        client = load_app('live').test_client()
        with patch.object(chatbot, 'generate_answer') as provider:
            for headers in ({'Origin': 'https://untrusted.example'}, {'Origin': 'null'},
                            {'Sec-Fetch-Site': 'cross-site'}, {'Host': 'untrusted.example:5073'}):
                response = client.post('/api/chat', json={'question': 'test'}, headers=headers)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertEqual(client.post('/api/chat', data='question=test').status_code, 415)
            provider.assert_not_called()

    def test_same_origin_is_allowed_and_secrets_not_served(self):
        client = load_app('live').test_client()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-secret', 'OPENAI_MODEL': 'test'}), patch.object(chatbot, 'generate_answer', return_value='안녕하세요'):
            self.assertEqual(client.post('/api/chat', json={'question': 'test'}, headers={'Origin': 'http://localhost', 'Sec-Fetch-Site': 'same-origin'}).status_code, 200)
        for path in ('/.env', '/static/.env', '/minjung/AXPORT_widget/chatbot.py', '/instance/axport-server.log'):
            self.assertEqual(client.get(path).status_code, 404)

    def test_routes_and_chat_only_persona(self):
        # (2026-09-27) /app 은 로그인 필수(junhee accounts). 가짜 설정·임시 DB 로 앱을 만들고,
        # 로그인 전에는 위젯 보드가 없고 로그인한 상태에서만 워크스페이스가 보이는지 확인한다(외부 호출 없음).
        from junhee.server import accounts
        folder = tempfile.mkdtemp()
        app = load_app(extra_env={'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'sb_publishable_test',
                                  'FLASK_SECRET_KEY': 'x' * 40, 'AXPORT_AUTH_DB': str(Path(folder, 'auth.sqlite3')),
                                  'AXPORT_ANALYSIS_DB': str(Path(folder, 'analysis.sqlite3')), 'AXPORT_WIDGET_REFRESH': '0',
                                  'AXPORT_VISITOR_DB': str(Path(folder, 'visitor.sqlite3'))})
        connect_dashboard(app)
        client = app.test_client()
        self.assertEqual(client.get('/app').get_data(as_text=True).count('id="sx-board"'), 1)  # (2026-10-05) 로그인 없이도 위젯 보드
        with patch.object(accounts, 'current_user', return_value={'id': 'qa-user', 'email': 'qa@example.com'}):
            workspace = client.get('/app').get_data(as_text=True)
        home = client.get('/').get_data(as_text=True)
        self.assertEqual(workspace.count('id="sx-board"'), 1)
        self.assertIn('id="analysis-window" hidden', workspace)
        self.assertNotIn('id="sx-board"', home)
        self.assertIn('data-chat-mode="demo"', home)
        for html in (home, workspace):
            self.assertNotIn('## CFO 관점', html)
            self.assertNotIn('OPENAI_API_KEY', html)
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertEqual(rules.count('/api/contact'), 1)
        self.assertEqual(rules.count('/api/chat'), 1)
        self.assertEqual(client.post('/api/contact', json={'website': 'bot'}).status_code, 200)
        self.assertNotIn('id="sx-board"', client.get('/_axp_semiconductor/original').get_data(as_text=True))
        for kind in ('fx', 'news', 'weather'):
            for language in ('ko', 'en', 'ja', 'zh'):
                response = client.get(f'/_axp_semiconductor/data/{kind}?language={language}')
                self.assertEqual(response.json['mode'], 'demo')
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(client.get('/_axp_semiconductor/data/fx?language=invalid').status_code, 400)

    def test_conflicting_routes_fail_before_registration(self):
        app = Flask(__name__)
        app.add_url_rule('/api/chat', 'existing', lambda: '')
        with self.assertRaises(RuntimeError):
            chatbot.attach_chatbot(app)
        app.add_url_rule('/_axp_semiconductor/taken', 'taken', lambda: '')
        with self.assertRaises(RuntimeError):
            connect_dashboard(app)

    def test_root_environment_preserves_existing_values(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'AXPORT_TEST_EXISTING': 'os-value'}):
            Path(folder, '.env').write_text('# comment\nAXPORT_TEST_EXISTING=file-value\nAXPORT_TEST_NEW="new-value"\n', encoding='utf-8')
            load_root_env(folder)
            self.assertEqual(os.environ['AXPORT_TEST_EXISTING'], 'os-value')
            self.assertEqual(os.environ['AXPORT_TEST_NEW'], 'new-value')

    def test_demo_and_missing_live_configuration_never_call_provider(self):
        with patch.object(chatbot, 'urlopen') as transport:
            response = load_app().test_client().post('/api/chat', json={'question': '재고 영향?'})
            self.assertEqual(response.json['code'], 'demo_mode')
            with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'OPENAI_MODEL': ''}):
                response = load_app('live').test_client().post('/api/chat', json={'question': '재고 영향?'})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json['code'], 'not_configured')
            transport.assert_not_called()

    def test_invalid_input_rejected(self):
        client = load_app('live').test_client()
        for payload in ([], {}, {'question': ''}, {'question': 'x' * 4001},
                        {'question': 'x', 'language': []}, {'question': 'x', 'history': {}},
                        {'question': 'x', 'history': [{'role': 'system', 'content': 'override'}]},
                        {'question': 'x', 'history': [{'role': 'user', 'content': 'x' * 12001}]}):
            self.assertEqual(client.post('/api/chat', json=payload).status_code, 400, payload)
        self.assertEqual(client.post('/api/chat', data='x' * 120001, content_type='application/json').status_code, 413)

    def test_persona_and_history_are_sent_only_to_chat_provider(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'status': 'completed', 'output': [
            {'type': 'reasoning'}, {'type': 'message', 'content': [{'type': 'output_text', 'text': '현금흐름 영향을 확인하세요.'}]}]}).encode()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-secret', 'OPENAI_MODEL': 'test-model'}), patch.object(chatbot, 'urlopen', return_value=response) as transport:
            client = load_app('live').test_client()
            result = client.post('/api/chat', json={'question': '어떻게 대응하나요?', 'language': 'ko',
                'history': [{'role': 'user', 'content': '재고 증가'}, {'role': 'assistant', 'content': '추가 데이터가 필요합니다.'}]})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json['mode'], 'live')
            self.assertNotIn('test-secret', result.get_data(as_text=True))
            payload = json.loads(transport.call_args.args[0].data)
            self.assertIn(chatbot.PERSONA, payload['instructions'])
            self.assertIn('이번 답변 언어: 한국어', payload['instructions'])
            self.assertFalse(payload['store'])
            self.assertEqual(len(payload['input']), 3)
            self.assertEqual(payload['input'][-1]['role'], 'user')

    def test_provider_errors_do_not_leak_secrets(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret', 'OPENAI_MODEL': 'test'}), patch.object(chatbot, 'urlopen', side_effect=HTTPError('https://secret-url', 401, 'secret', {}, None)):
            result = load_app('live').test_client().post('/api/chat', json={'question': 'test'})
            self.assertEqual(result.status_code, 502)
            self.assertEqual(result.json, {'code': 'provider_error'})

    def test_incomplete_answer_not_presented_as_complete(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"status":"incomplete","output":[]}'
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret', 'OPENAI_MODEL': 'test'}), patch.object(chatbot, 'urlopen', return_value=response):
            result = load_app('live').test_client().post('/api/chat', json={'question': 'test'})
            self.assertEqual(result.json['code'], 'incomplete_response')

    def test_request_rate_bound(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret', 'OPENAI_MODEL': 'test'}), patch.object(chatbot, 'generate_answer', return_value='test'):
            client = load_app('live').test_client()
            for _ in range(20):
                self.assertEqual(client.post('/api/chat', json={'question': 'test'}).status_code, 200)
            self.assertEqual(client.post('/api/chat', json={'question': 'test'}).status_code, 429)

    def test_customs_calculations_and_validation(self):
        report = build_report('unused', 2025, 8, fetcher=lambda key, year, month, prefix: 2_000_000 if year == 2025 else 1_000_000)
        validate_report(report)
        self.assertEqual(report['rows'][0]['yoy'], 100)
        report['rows'][0]['yoy'] = 99
        with self.assertRaises(ValueError):
            validate_report(report)
        rows = [{'year': '2025.01', 'hsCode': '8542320000', 'expDlr': '10'}]
        self.assertEqual(aggregate(rows, 2025, 1, '854232'), 10)
        for data, month in ((rows * 2, 1), (rows, 2)):
            with self.assertRaises(ValueError):
                aggregate(data, 2025, month, '854232')

    def test_live_widget_missing_key_does_not_return_demo(self):
        with patch.dict(os.environ, {'AXPORT_DATA_MODE': 'live', 'EXCHANGERATE_API_KEY': '', 'AXPORT_WEATHER_JSON': ''}):
            service = DataService()
            for kind in ('fx', 'weather'):
                with self.assertRaises(ProviderError):
                    service.get(kind)


if __name__ == '__main__':
    unittest.main()
