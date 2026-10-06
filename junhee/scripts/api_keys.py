"""API 키 로더 (junhee, 2026-09-26).

키 값은 저장소에 두지 않는다. 각자 발급받은 키를 환경변수나 루트 .env 에 넣는다(복사·출력·기록 금지).
  - 찾는 순서: 환경변수 → 루트 .env → (선택) AXPORT_KEY_FILE 로 지정한 키 파일
  - (2026-09-30 조원 배포) 다른 사람의 개인 키 파일을 기본 경로로 자동으로 읽지 않는다. 키 파일은 AXPORT_KEY_FILE 을 직접 지정할 때만 쓴다
  - 설정 방법: TEAM_SETUP.md
사용: from api_keys import get_key; key = get_key("DATA_GO_KR")
공개 이름: DATA_GO_KR(공공데이터포털 공통 서비스키) · UN_COMTRADE_API_KEY · WTO_API_KEY · ECOS_API_KEY · KOREAEXIM_API_KEY · OPENAI_API_KEY
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 키 파일의 이름(왼쪽) → 공개 이름. 공공데이터포털 서비스들은 같은 계정 서비스키를 쓴다.
ALIASES = [
    (re.compile(r"관세청|인천국제공항공사|해양수산부|대한무역투자진흥공사"), "DATA_GO_KR"),
    (re.compile(r"UN_COMTRADE", re.I), "UN_COMTRADE_API_KEY"),
    (re.compile(r"WTO", re.I), "WTO_API_KEY"),
    (re.compile(r"ECOS", re.I), "ECOS_API_KEY"),
    (re.compile(r"KOREAEXIM|수출입은행", re.I), "KOREAEXIM_API_KEY"),
    (re.compile(r"OPENAI_API_KEY", re.I), "OPENAI_API_KEY"),
    (re.compile(r"국가법령"), "LAW_API_KEY"),
]


class MissingKey(RuntimeError):
    pass


def _load_file():
    out = {}
    name = os.environ.get("AXPORT_KEY_FILE", "").strip()
    path = Path(name) if name else None
    if path is None or not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip().strip("\"'")
        if not value:
            continue
        for pattern, canon in ALIASES:
            if pattern.search(name):
                out.setdefault(canon, value)
                break
    return out


_cache = None
_env_cache = None
# (2026-09-27) 같은 공공데이터포털 서비스키를 코드마다 다른 이름으로 부른다: 스크립트 DATA_GO_KR, 분석 엔진 KCS_TRADE_API_KEY,
# minjung 수출기상도 CUSTOMS_API_KEY. 이름이 달라 키가 있는데도 못 찾는 일이 없게 서로 대신 찾는다.
SAME_KEY = {
    "DATA_GO_KR": ("KCS_TRADE_API_KEY", "CUSTOMS_API_KEY"),
    "KCS_TRADE_API_KEY": ("DATA_GO_KR", "CUSTOMS_API_KEY"),
    "CUSTOMS_API_KEY": ("KCS_TRADE_API_KEY", "DATA_GO_KR"),
}


def _root_env():
    """루트 .env (git 제외) 를 읽는다. 앱(junhee/server/accounts.py)과 같은 파일. 값은 돌려주기만 하고 출력하지 않는다."""
    global _env_cache
    if _env_cache is None:
        _env_cache = {}
        path = ROOT / ".env"
        if path.is_file():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                value = value.strip().strip("\"'")
                if value:
                    _env_cache[name.strip()] = value
    return _env_cache


def _lookup(name):
    global _cache
    value = os.environ.get(name, "").strip() or _root_env().get(name, "")
    if value:
        return value
    if _cache is None:
        _cache = _load_file()
    return _cache.get(name, "")


def get_key(name):
    """환경변수 → 루트 .env → 키 파일 순으로 찾고, 같은 키의 다른 이름(SAME_KEY)도 찾는다.
    없으면 MissingKey (메시지에 값은 넣지 않는다)."""
    for candidate in (name,) + SAME_KEY.get(name, ()):
        value = _lookup(candidate)
        if value:
            return value
    raise MissingKey(f"{name} 키를 찾지 못했습니다 (환경변수·루트 .env·AXPORT_KEY_FILE 확인)")


def available():
    """어떤 키가 있는지 이름만 돌려준다 (값은 돌려주지 않는다)."""
    global _cache
    if _cache is None:
        _cache = _load_file()
    names = set(_cache) | {n for _, n in ALIASES if os.environ.get(n, "").strip()} | set(_root_env())
    names |= {n for n, alts in SAME_KEY.items() if any(a in names for a in alts)}
    return sorted(n for n in names if n.endswith("_KEY") or n == "DATA_GO_KR")


def scrub(text, *keys):
    """오류 메시지·URL 에 키가 섞여 있으면 가린다."""
    text = str(text)
    for k in keys:
        if k:
            text = text.replace(k, "***")
    return text
