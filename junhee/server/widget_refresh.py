# -*- coding: utf-8 -*-
"""(junhee) 2026-09-27 바탕화면 위젯 공식 자료(static/data/widgets/widgets.json) 자동 갱신.

지금까지는 run_live.py 로 띄울 때만 갱신됐다. 배포 서버(gunicorn app:app)에서도 같은 스크립트
(junhee/scripts/fetch_widget_data.py: 한국은행 ECOS 환율 · 관세청 반도체 수출(수출기상도) · 뉴스 RSS)를 주기적으로 돌린다.
  - 켜짐: Render(RENDER 환경변수)에서 기본으로 켜짐. 그 밖에는 AXPORT_WIDGET_REFRESH=1 일 때만 (로컬 테스트는 외부 호출 없음)
  - 주기: 환율·뉴스 1시간, 수출기상도 하루. gunicorn 워커가 여러 개여도 잠금 파일로 한 번만 돈다
  - 키: 환경변수(ECOS_API_KEY, KCS_TRADE_API_KEY=공공데이터포털 키, 선택 KOREAEXIM_API_KEY). 출력·오류는 로그에 남기지 않는다(키 노출 방지)
"""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'junhee' / 'scripts' / 'fetch_widget_data.py'
STATE = ROOT / 'instance'
LOCK = STATE / 'widget-refresh.lock'
STAMP = STATE / 'widget-refresh.stamp'
WEATHER_STAMP = STATE / 'widget-refresh-weather.stamp'
HOUR, DAY = 3600, 86400
_started = False


def enabled():
    value = os.environ.get('AXPORT_WIDGET_REFRESH', '').strip()
    return value == '1' if value in ('0', '1') else bool(os.environ.get('RENDER'))


def _due(stamp, every):
    try:
        return time.time() - stamp.stat().st_mtime >= every
    except OSError:
        return True


def _claim():
    """여러 워커 중 하나만 갱신한다. 30분 넘게 남은 잠금은 죽은 작업으로 보고 지운다."""
    try:
        if LOCK.exists() and time.time() - LOCK.stat().st_mtime > 1800:
            LOCK.unlink()
    except OSError:
        pass
    try:
        os.close(os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except OSError:
        return False


def refresh_once():
    if not _due(STAMP, HOUR) or not _claim():
        return False
    try:
        weather = _due(WEATHER_STAMP, DAY)
        done = subprocess.run([sys.executable, '-B', str(SCRIPT), '--only', 'fx,news' + (',weather' if weather else '')],
                              cwd=str(ROOT), timeout=900, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        STAMP.touch()
        if done.returncode != 0:  # (2026-09-27 배포 QA) 실패하면 1시간이 아니라 15분 뒤에 다시 시도한다
            retry_at = time.time() - HOUR + 900
            os.utime(STAMP, (retry_at, retry_at))
            return False
        if weather:
            WEATHER_STAMP.touch()
        return True
    except Exception:  # 갱신 실패는 기존 widgets.json 을 그대로 쓴다
        return False
    finally:
        try:
            LOCK.unlink()
        except OSError:
            pass


def _loop():
    while True:
        refresh_once()
        time.sleep(300)


def start():
    """attach_accounts 가 부른다. 조건이 맞을 때 한 번만 백그라운드 스레드를 띄운다."""
    global _started
    if _started or not enabled() or not SCRIPT.is_file():
        return False
    _started = True
    STATE.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=_loop, name='junhee-widget-refresh', daemon=True).start()
    return True
