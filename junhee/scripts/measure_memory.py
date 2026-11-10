# -*- coding: utf-8 -*-
"""한국은행 가격 원표를 외부 링크 포함(keep_links=True, 수정 전) / 제외(keep_links=False, 현재 코드)로 읽을 때
예시 기업 1건 분석의 프로세스 최대 메모리를 비교한다. (2026-10-06 커밋 575c887 의 수치를 다시 확인하는 용도)

실행 (Portfolio AXPORT 폴더에서):  python junhee/scripts/measure_memory.py
- 모드마다 새 Python 프로세스를 띄워 같은 시나리오를 한 번씩 실행한다(캐시 영향 없음).
- 시나리오: 테스트와 같은 방식(외부 API 키 없음, 임시 DB, 분석 기준일 2026-10-06 고정)으로
  예시 파일 '기업데이터_예시1_한울메모리.xlsx'(HS 854232, 미국)를 업로드·분석한다.
- 측정값: Windows PeakWorkingSetSize(프로세스 최대 물리 메모리). Render(리눅스) 수치와 측정 방식이 달라 절대값은 같지 않다.
- 두 모드의 분석 결과(handoff 문서의 국가별 항목·점수)가 같은지 해시로 비교한다.
"""
import ctypes
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def peak_working_set():
    class PMC(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong), ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t)]
    pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
    if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
        raise OSError('GetProcessMemoryInfo failed')
    return pmc.PeakWorkingSetSize, pmc.WorkingSetSize


def child(mode):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    import openpyxl
    if mode == 'keep_links':  # 수정 전 동작 재현: 외부 링크 XML 까지 읽음
        original = openpyxl.load_workbook
        openpyxl.load_workbook = lambda *a, **k: original(*a, **{**k, 'keep_links': True})
    from junhee.tests import test_analysis as T
    import unittest

    out = {}

    class Run(T.EngineFlow):
        def runTest(self):
            out['before_peak'], _ = peak_working_set()
            with T.pinned_today(T.IN_WINDOW):
                st = self.analyze(T.EXAMPLE)
            doc = self.c.get(f"/api/analysis/assessments/{st['assessment_id']}/handoff").get_json()
            out['peak'], out['current'] = peak_working_set()
            out['status'] = st['status']
            out['result_hash'] = hashlib.sha256(json.dumps([doc['per_country'], doc['score']['per_country']],
                                                           ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    Run.setUpClass()
    unittest.TextTestRunner(stream=open(os.devnull, 'w')).run(Run())
    print(json.dumps(out))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        child(sys.argv[1])
        sys.exit()
    rows = {}
    for mode in ('keep_links', 'current'):
        p = subprocess.run([sys.executable, __file__, mode], capture_output=True, text=True, cwd=ROOT)
        line = [l for l in p.stdout.splitlines() if l.startswith('{')]
        rows[mode] = json.loads(line[-1]) if line else {'error': p.stderr[-500:]}
    mb = lambda b: f'{b / 1024 / 1024:.0f}MB'
    for mode, r in rows.items():
        if 'error' in r:
            print(mode, 'ERROR', r['error']); continue
        print(f"{mode:10} 분석 전 최대 {mb(r['before_peak'])} → 분석 후 최대 {mb(r['peak'])} · 상태 {r['status']} · 결과 해시 {r['result_hash']}")
    if all('result_hash' in r for r in rows.values()):
        print('분석 결과 동일:', rows['keep_links']['result_hash'] == rows['current']['result_hash'])
