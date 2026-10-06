# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 API 연결 점검: 같은 공공데이터포털 키의 이름 불일치, 위젯 자동 갱신 켜짐 조건. 실제 키 값은 쓰지 않는다."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'junhee' / 'scripts'))

import api_keys  # noqa: E402
from junhee.server import widget_refresh  # noqa: E402


class KeyNames(unittest.TestCase):
    def setUp(self):
        self.p = [mock.patch.object(api_keys, '_env_cache', {}), mock.patch.object(api_keys, '_cache', {})]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def test_data_go_kr_falls_back_to_engine_key(self):
        env = {k: '' for k in ('DATA_GO_KR', 'CUSTOMS_API_KEY', 'KCS_TRADE_API_KEY')}
        with mock.patch.dict(os.environ, {**env, 'KCS_TRADE_API_KEY': 'fake-kcs'}):
            self.assertEqual(api_keys.get_key('DATA_GO_KR'), 'fake-kcs')  # 스크립트 이름
            self.assertEqual(api_keys.get_key('CUSTOMS_API_KEY'), 'fake-kcs')  # 수출기상도 이름
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(api_keys.MissingKey) as cm:
                api_keys.get_key('DATA_GO_KR')
            self.assertNotIn('fake', str(cm.exception))

    def test_root_env_is_read(self):
        with mock.patch.dict(os.environ, {'ECOS_API_KEY': ''}), mock.patch.object(api_keys, '_env_cache', {'ECOS_API_KEY': 'fake-ecos'}):
            self.assertEqual(api_keys.get_key('ECOS_API_KEY'), 'fake-ecos')


class WidgetRefresh(unittest.TestCase):
    def test_enabled_rules(self):
        with mock.patch.dict(os.environ, {'AXPORT_WIDGET_REFRESH': '', 'RENDER': ''}):
            self.assertFalse(widget_refresh.enabled())  # 로컬 기본: 외부 호출 없음
        with mock.patch.dict(os.environ, {'AXPORT_WIDGET_REFRESH': '', 'RENDER': 'true'}):
            self.assertTrue(widget_refresh.enabled())  # Render 기본 켜짐
        with mock.patch.dict(os.environ, {'AXPORT_WIDGET_REFRESH': '0', 'RENDER': 'true'}):
            self.assertFalse(widget_refresh.enabled())
        with mock.patch.dict(os.environ, {'AXPORT_WIDGET_REFRESH': '1', 'RENDER': ''}):
            self.assertTrue(widget_refresh.enabled())


if __name__ == '__main__':
    unittest.main()
