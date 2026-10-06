"""공개 API 키를 넣어 서버 실행 (junhee, 2026-09-26).

.env 를 수정하지 않고, api_keys.py 가 환경변수·루트 .env·(선택) AXPORT_KEY_FILE 에서 읽은 본인 키를 이 프로세스의 환경변수로만 넣은 뒤 app.py 를 띄운다.
- 챗봇: AXPORT_CHAT_MODE=live, OPENAI_API_KEY, OPENAI_MODEL(없으면 gpt-4.1-mini — 2026-09-26 한 번 호출해 동작 확인)
- 위젯(환율·뉴스·수출기상도): minjung 위젯 서버는 ExchangeRate-API·TheNewsAPI 키가 없어 예시 모드 그대로 두고
  (AXPORT_DATA_MODE=live 로 바꾸면 '키 없음' 오류), 대신 fetch_widget_data.py 가 공식 자료(한국은행 ECOS 환율 · 관세청 반도체 수출 · 뉴스 RSS)를
  static/data/widgets/widgets.json 으로 만들고 junhee-widgets-bridge.js 가 위젯 칸에 넣는다. 이 실행기는 그 파일을 주기적으로 갱신한다
  (끄려면 AXPORT_WIDGET_REFRESH=0). ECOS 키는 환경변수 ECOS_API_KEY 또는 루트 .env 값을 쓴다
- 대시보드 공개 통계는 서버가 아니라 fetch_public_apis.py → build_company_items.py → publish_static.py 로 미리 만든다
사용: python junhee/scripts/run_live.py
"""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_keys import MissingKey, get_key  # noqa: E402

try:
    os.environ["OPENAI_API_KEY"] = get_key("OPENAI_API_KEY")
    os.environ.setdefault("OPENAI_MODEL", "gpt-4.1-mini")
    os.environ["AXPORT_CHAT_MODE"] = "live"
    print(f"챗봇: live (모델 {os.environ['OPENAI_MODEL']})")
except MissingKey as e:
    print(f"챗봇: 예시 모드 유지 ({e})")
try:
    os.environ.setdefault("CUSTOMS_API_KEY", get_key("DATA_GO_KR"))  # make_weather_json.py 로 수출기상도 JSON 을 만들 때 사용
except MissingKey:
    pass
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


# 위젯 자료(static/data/widgets/widgets.json) 자동 갱신: 환율·뉴스 1시간, 수출기상도 하루 (브리지가 30분마다 파일을 다시 읽음)
def _refresh_widgets():
    import subprocess
    import threading
    import time
    script = str(Path(__file__).resolve().parent / "fetch_widget_data.py")

    def run(only):
        try:
            subprocess.run([sys.executable, "-B", script, "--only", only], cwd=str(ROOT), timeout=900,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # 출력(오류 메시지 포함)은 로그에 남기지 않는다
        except Exception:
            pass

    def loop():
        run("fx,news,weather")
        last_weather = time.time()
        while True:
            time.sleep(3600)
            run("fx,news,weather" if time.time() - last_weather > 86400 else "fx,news")
            if time.time() - last_weather > 86400:
                last_weather = time.time()
    threading.Thread(target=loop, name="widget-refresh", daemon=True).start()
    print("위젯 자료: 공식 환율(한국은행 ECOS)·반도체 수출(관세청)·뉴스(RSS) 자동 갱신")


if os.environ.get("AXPORT_WIDGET_REFRESH", "1") != "0":
    _refresh_widgets()
runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
