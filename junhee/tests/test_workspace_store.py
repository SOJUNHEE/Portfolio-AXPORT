# -*- coding: utf-8 -*-
"""(junhee) 계정별 바탕화면 저장 API. Supabase 는 메모리 저장소로 대신한다.

실행: python -m unittest junhee.tests.test_workspace_store -v
"""
import copy
import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from junhee.tests.test_accounts import ENV, TOKENS, USER, csrf, load_app  # noqa: E402

OTHER = {'id': '00000000-0000-0000-0000-000000000002', 'email': 'other@example.com'}


class MemoryRepo:
    """save_axport_workspace RPC 와 같은 규칙(revision 비교, 사용자별 한 행)."""

    def __init__(self):
        self.rows = {}

    def load(self, user_id, token):
        row = self.rows.get(user_id)
        return copy.deepcopy(row) if row else None

    def save(self, user_id, token, state, revision):
        ws = sys.modules['junhee.server.workspace_store']
        row = self.rows.get(user_id)
        if (revision == 0 and row) or (revision and (not row or row['revision'] != revision)):
            raise ws.WorkspaceError('conflict', 409)
        new = {'user_id': user_id, 'revision': revision + 1, 'state': copy.deepcopy(state)}
        self.rows[user_id] = new
        return copy.deepcopy(new)


def state(*items, last=None):
    s = {'v': 1, 'items': list(items), 'system': {'analysis': 0, 'trash': 2, 'upload': 5}}
    if last:
        s['last'] = last
    return s


FOLDER = {'id': 'f1', 'kind': 'folder', 'name': '미국 거래처', 'cell': 6, 'trash': False}
FILE = {'id': 'sample-hanbit', 'kind': 'file', 'name': '한빛_이름변경.xlsx', 'source_name': '한빛반도체_수출데이터_v0.3.xlsx',
        'parent_id': 'f1', 'cell': 1, 'trash': False, 'sample': True, 'size': 0, 'analyzed': True, 'company_id': 'hanbit',
        'conditions': {'company': '한빛반도체', 'hs': 'all', 'country': '미국', 'file': '한빛_이름변경.xlsx', 'fileId': 'sample-hanbit'}}


class Validate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_app(ENV)
        cls.ws = sys.modules['junhee.server.workspace_store']

    def test_keeps_allowed_fields_only(self):
        raw = dict(FILE, raw={'x': 1}, token='secret')
        clean = self.ws.validate_state(state(FOLDER, raw))
        self.assertNotIn('raw', clean['items'][1])
        self.assertNotIn('token', clean['items'][1])
        self.assertEqual(clean['items'][1]['parent_id'], 'f1')

    def test_rejects_bad_names_and_structure(self):
        E = self.ws.WorkspaceError
        for bad in ('', '   ', 'a/b', 'CON', 'x' * 121, 'ends.'):
            with self.assertRaises(E):
                self.ws.validate_state(state(dict(FOLDER, name=bad)))
        # 같은 이름의 파일은 허용(같은 파일을 다시 올리는 junhee 기존 동작). 중복 방지는 이름 바꾸기·새 폴더 화면에서.
        self.ws.validate_state(state(dict(FILE, parent_id=None), dict(FILE, id='file-2', parent_id=None)))
        with self.assertRaises(E):  # 없는 폴더를 가리킴
            self.ws.validate_state(state(dict(FILE, parent_id='nope')))
        with self.assertRaises(E):  # 폴더 안 폴더
            self.ws.validate_state(state(FOLDER, dict(FOLDER, id='f2', name='하위', parent_id='f1')))
        with self.assertRaises(E):  # 시스템 아이콘 id 사용 불가
            self.ws.validate_state(state(dict(FOLDER, id='trash')))
        with self.assertRaises(E):
            self.ws.validate_state(state(dict(FILE, parent_id=None, conditions={'evil': 'x'})))
        # 휴지통에 있는 항목끼리는 이름이 같아도 된다
        self.ws.validate_state(state(FOLDER, dict(FOLDER, id='f2', trash=True, trash_batch='b1')))


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app(ENV)

    def setUp(self):
        self.repo = MemoryRepo()
        self.app.extensions['junhee_workspace'] = self.repo
        self.provider = mock.MagicMock()
        self.provider.get_user.return_value = USER
        self.provider.sign_in.return_value = dict(TOKENS)
        self.app.extensions['junhee_accounts']['provider'] = self.provider
        self.c = self.app.test_client()
        t = csrf(self.c.get('/app').get_data(as_text=True))
        self.c.post('/auth/login', data={'csrf_token': t, 'email': USER['email'], 'password': 'pw'})
        self.token = re.search(r'data-csrf="([^"]+)"', self.c.get('/app').get_data(as_text=True)).group(1)

    def put(self, body, token=None):
        return self.c.put('/api/workspace', json=body, headers={'X-CSRF-Token': token or self.token})

    def test_first_login_then_save_and_reload(self):
        self.assertEqual(self.c.get('/api/workspace').get_json(), {'revision': 0, 'state': None})
        r = self.put({'revision': 0, 'state': state(FOLDER, FILE, last={'fileId': 'sample-hanbit', 'country': '미국', 'hs': 'all'})})
        self.assertEqual(r.get_json(), {'revision': 1})
        # 로그아웃 후 다시 로그인해도 그대로
        self.c.post('/auth/logout', data={'csrf_token': self.token})
        self.assertEqual(self.c.get('/api/workspace').get_json(), {'revision': 0, 'state': None})  # (2026-10-05) 로그아웃하면 방문자 바탕화면
        t = csrf(self.c.get('/app').get_data(as_text=True))
        self.c.post('/auth/login', data={'csrf_token': t, 'email': USER['email'], 'password': 'pw'})
        got = self.c.get('/api/workspace').get_json()
        self.assertEqual(got['revision'], 1)
        self.assertEqual([i['name'] for i in got['state']['items']], ['미국 거래처', '한빛_이름변경.xlsx'])
        self.assertEqual(got['state']['last']['fileId'], 'sample-hanbit')

    def test_stale_tab_gets_conflict_with_latest(self):
        self.put({'revision': 0, 'state': state(FOLDER)})
        self.put({'revision': 1, 'state': state(dict(FOLDER, name='새 이름'))})
        r = self.put({'revision': 1, 'state': state(dict(FOLDER, name='오래된 탭'))})
        self.assertEqual(r.status_code, 409)
        body = r.get_json()
        self.assertEqual((body['error'], body['revision'], body['state']['items'][0]['name']), ('conflict', 2, '새 이름'))

    def test_csrf_and_validation(self):
        self.assertEqual(self.put({'revision': 0, 'state': state(FOLDER)}, token='wrong').status_code, 403)
        self.assertEqual(self.put({'revision': 0, 'state': state(dict(FOLDER, name='a:b'))}).status_code, 400)
        self.assertEqual(self.put({'revision': -1, 'state': state()}).status_code, 400)
        self.assertEqual(self.repo.rows, {})

    def test_accounts_are_separate(self):
        self.put({'revision': 0, 'state': state(FOLDER)})
        self.provider.get_user.return_value = OTHER  # 다른 계정으로 확인되는 세션
        self.provider.sign_in.return_value = dict(TOKENS, user=OTHER)
        c2 = self.app.test_client()
        t = csrf(c2.get('/app').get_data(as_text=True))
        c2.post('/auth/login', data={'csrf_token': t, 'email': OTHER['email'], 'password': 'pw'})
        self.assertEqual(c2.get('/api/workspace').get_json(), {'revision': 0, 'state': None})


if __name__ == '__main__':
    unittest.main()
