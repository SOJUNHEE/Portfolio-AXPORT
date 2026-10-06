"""Local browser regression check for the dashboard (index3 structure, v5 · 2026-09-26).

앱을 먼저 띄운다: python app.py  (http://127.0.0.1:5073)
검사: 업로드 양식 다운로드 · 새벽 샘플 업로드 결측 확인(취소/진행) · 3개 회사 × 상세 탭 5개의 index3 KPI 칸 이름·차트 id·값 ·
      어댑터 toIndex3Data 구조 · 사이드바 'ANALYSIS · 분석 조건'(목적국·HS·기간 → 재렌더) · 사이드바 접기 막대 ·
      전체 화면(Fullscreen API) 진입·해제 · 실제 기업명 미노출 · JavaScript 오류 0 · 검증 JSON 조회 실패 시 분석 중단.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "junhee" / "test-results"
OUT.mkdir(exist_ok=True)
URL = "http://127.0.0.1:5073/app"
# JH2/index3.html 의 KPI 칸 이름 (탭별 4칸, 순서 그대로)
KPI_LABELS = {
    "regulation": ["통제번호 후보", "수입규제 기록", "거래처 CSL 검색", "검토 상태"],
    "market": ["수입시장 규모", "한국 수출액", "YoY 성장률", "한국산 점유율"],
    "price": ["통계상 단가", "관세 참고율", "참고환율", "산업 가격지수"],
    "logistics": ["화물편 수", "출발편", "도착편", "선박 기록"],
    "stability": ["변동계수 CV", "급감 횟수", "급감 빈도", "환율 변동성"],
}
CHART_IDS = {"market": ["marketTrendChart", "marketGrowthChart"], "price": ["fxChart"], "logistics": ["logFlightChart"], "stability": ["stabilityChart"], "regulation": []}
TITLES = {"regulation": "규제 기록 및 수출통제 후보", "market": "수입시장 규모 및 성장성", "price": "통계상 단가·관세 참고치·환율", "logistics": "화물 항공편 및 선박 입출항 기록", "stability": "수입금액 변동성과 급감 이력"}


def launch(p):
    for ch in ("msedge", "chrome"):
        try:
            return p.chromium.launch(channel=ch, headless=True)
        except Exception:
            continue
    return p.chromium.launch(headless=True)


with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(URL)
    page.wait_for_function("window.JunheeDashboard?.ready()")
    # 업로드 양식 다운로드
    page.locator('.desktop-icon[data-id="upload"]').dblclick()
    with page.expect_download() as dl:
        page.locator(".jd-tpl-btn").click()
    downloaded = OUT / "download-check.xlsx"
    dl.value.save_as(downloaded)
    import openpyxl
    wb = openpyxl.load_workbook(downloaded, read_only=True)
    assert "간편입력" in wb.sheetnames  # (junhee) 2026-09-27 양식 다운로드를 sanghyeob 간편입력 v2 로 변경 (기존 v1 은 업로드 가이드에서 내려받음)
    wb.close()
    # 새벽 샘플 업로드 → 결측 확인 창 (취소 → 진행)
    sample = next((ROOT / "static" / "samples").glob("새벽*.xlsx"))
    page.locator("#excel-input").set_input_files(sample)
    page.wait_for_function("document.querySelector('#file-label').textContent.includes('등록된 샘플')")
    page.locator('#analysis-form button[type="submit"]').click()
    gate = page.locator("#jd-confirm-dialog")
    gate.wait_for(state="visible")
    assert "그래도 진행하시겠습니까" in gate.inner_text()
    assert "엑셀 행" in gate.inner_text()
    gate.screenshot(path=str(OUT / "quality.png"))
    gate.locator(".modal-actions .jd-cancel").click()
    assert page.evaluate("JunheeDashboard.current()") is None
    page.locator('#analysis-form button[type="submit"]').click()
    gate.locator(".jd-ok").click()
    page.wait_for_function("JunheeDashboard.current()?.company_id === 'saebyeok'")
    # 정보 막대에는 조건 선택 칸이 없고, 사이드바에 ANALYSIS · 분석 조건이 있다
    assert page.locator(".jd-infobar select").count() == 0
    side = page.locator(".jd-side-analysis")
    assert "ANALYSIS" in side.inner_text()
    assert side.locator('select[data-jd="country"]').count() == 1 and side.locator('select[data-jd="hs"]').count() == 1 and side.locator('select[data-jd="period"]').count() == 1
    results = {}
    for company in ["saebyeok", "hanbit", "daesung"]:
        page.evaluate("id => JunheeDashboard.select(id)", company)
        # 어댑터 구조 (index3 AXPORT_DATA)
        shape = page.evaluate("""() => { const v = JunheeDashboard.toIndex3Data(JunheeDashboard.current(), {country: JunheeDashboard.country()});
            return { keys: Object.keys(v).sort(), reg: Object.keys(v.regulation), mkt: Object.keys(v.market), prc: Object.keys(v.price), log: Object.keys(v.logistics), stb: Object.keys(v.stability),
                     fx: v.price.fx, fxInfo: v.price.info.fx, flights: v.logistics.flightCount, flightStatus: v.logistics.info.flightCount.status }; }""")
        assert shape["keys"] == ["logistics", "market", "meta", "overview", "price", "regulation", "stability"], shape["keys"]
        for area, need in [("reg", ["status", "controls", "measures", "cslMatches"]), ("mkt", ["period", "importValue", "koreaExport", "yoy", "koreaShare", "monthly", "growth"]),
                           ("prc", ["unitPrice", "tariff", "fx", "index", "fxSeries", "references"]), ("log", ["period", "flightCount", "departures", "arrivals", "vesselCount", "monthly", "flights"]),
                           ("stb", ["status", "cv", "dropCount", "dropRate", "fxVol", "monthly"])]:
            assert set(need).issubset(shape[area]), (company, area, shape[area])
        assert shape["flightStatus"] in ("확인됨", "미확인", "자료 부족"), shape  # 공개 API 수집 후 확인됨 (fetch_public_apis.py)
        if shape["flightStatus"] == "확인됨":
            assert isinstance(shape["flights"], int), shape
        if company == "saebyeok":
            assert shape["fx"] is None and shape["fxInfo"]["note"] == "결제통화 미기재", shape
        for tab in ["regulation", "market", "price", "logistics", "stability"]:
            page.locator(f'[data-tab="{tab}"]').click()
            page.wait_for_timeout(900)
            assert page.locator(".jd-head h2").inner_text() == TITLES[tab]
            labels = page.evaluate("() => [...document.querySelectorAll('.jd-kpis .jd-kpi > span')].map(s => s.childNodes[0].textContent.trim())")
            assert labels == KPI_LABELS[tab], (company, tab, labels)
            charts = page.evaluate("""() => [...document.querySelectorAll('canvas.jd-detail-chart')].map(c => {
                const chart = Chart.getChart(c);
                return {id: c.id, width: c.width, datasets: chart?.data.datasets.length, values: chart?.data.datasets.some(d => d.data.some(v => v !== null))};
            })""")
            assert all(c["width"] > 0 and c["datasets"] and c["values"] for c in charts), (company, tab, charts)
            expect = [i for i in CHART_IDS[tab] if not (company == "saebyeok" and i == "fxChart")]
            assert [c["id"] for c in charts] == expect, (company, tab, charts)
            if company == "saebyeok" and tab == "price":
                assert "자료 부족 — 결제통화 미기재" in page.locator(".jd-chart-empty").inner_text()
            if tab == "logistics":
                assert page.locator("#logFlightChart").count() == 1 or page.locator(".jd-tr-unknown").count() == 1  # 공개 운항 통계 또는 미확인 표시
                assert page.locator(".jd-subtable tbody tr").count() >= 1
            if company == "hanbit" and tab == "price":
                assert page.locator(".jd-kpi strong .jd-cnt").first.evaluate("e=>parseFloat(getComputedStyle(e).fontSize)>=20")
                page.screenshot(path=str(OUT / "price.png"))
            results[f"{company}/{tab}"] = charts
    # 사이드바 조건 변경 → 모든 탭 재렌더 (목적국·HS·기간)
    page.locator('[data-tab="overview"]').click()
    page.select_option('.jd-side-analysis select[data-jd="country"]', "중국")
    page.wait_for_function("JunheeDashboard.country() === '중국' && document.querySelector('#country-context').textContent.includes('중국')")
    page.select_option('.jd-side-analysis select[data-jd="hs"]', "854231")
    page.select_option('.jd-side-analysis select[data-jd="period"]', "2025")
    page.wait_for_function("document.querySelector('.jd-side-applied').textContent.includes('2025-01~2025-12 · HS 8542.31 · 중국')")
    page.locator('[data-tab="stability"]').click()
    assert page.locator(".jd-status-box b").inner_text() in ("목적국 수입통계 계산값", "회사 자료 계산값") or "2025-01~2025-12" in page.locator(".jd-status-box b").inner_text()
    # 사이드바 접기 → 44px 막대 → 열기 (aria-expanded 동기화)
    page.locator("#sidebar-collapse").click()
    st = page.evaluate("[document.querySelector('#window-sidebar').hidden, document.querySelector('#sidebar-rail').offsetWidth, ...['#sidebar-toggle','#sidebar-collapse','#sidebar-open'].map(s=>document.querySelector(s).getAttribute('aria-expanded'))]")
    assert st == [True, 44, "false", "false", "false"], st
    page.locator("#sidebar-open").click()
    st = page.evaluate("[document.querySelector('#window-sidebar').hidden, document.querySelector('#sidebar-rail').hidden, ...['#sidebar-toggle','#sidebar-collapse','#sidebar-open'].map(s=>document.querySelector(s).getAttribute('aria-expanded'))]")
    assert st == [False, True, "true", "true", "true"], st
    # 전체 화면 진입 → 해제 (fullscreenchange 에서 이전 크기·위치 복원)
    geo = "(() => { const w = document.querySelector('#analysis-window'); return [w.offsetLeft, w.offsetTop, w.offsetWidth, w.offsetHeight]; })()"
    g0 = page.evaluate(geo)
    page.locator("#maximize-btn").click()
    page.wait_for_function("document.querySelector('#analysis-window').classList.contains('maximized')")
    full = page.evaluate("!!document.fullscreenElement")
    if full:
        assert page.locator("#maximize-btn i").get_attribute("class") == "ph ph-corners-in"
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        if page.evaluate("!!document.fullscreenElement"):  # 헤드리스는 Esc 를 브라우저 UI 가 처리하지 않을 수 있다
            page.evaluate("document.exitFullscreen()")
        page.wait_for_function("!document.querySelector('#analysis-window').classList.contains('maximized')")
    else:  # Fullscreen API 가 막힌 환경: 창 최대화로 대체 + 토스트
        assert "창 최대화" in page.locator("#toast").inner_text()
        page.locator("#maximize-btn").click()
    assert page.evaluate(geo) == g0, (g0, page.evaluate(geo))
    assert page.locator("#maximize-btn i").get_attribute("class") == "ph ph-corners-out"
    assert not page.evaluate("/삼성|하이닉스|Samsung|Hynix/i.test(document.body.innerText)")
    assert not errors, errors
    # 검증 JSON 조회 실패 시 분석 중단
    page.evaluate("() => { window.gateResult = null; void JunheeDashboard.qualityGate('missing-test-company').then(v => window.gateResult = v); }")
    gate.wait_for(state="visible")
    assert "불러오지 못했습니다" in gate.inner_text()
    gate.locator(".jd-ok").click()
    page.wait_for_function("window.gateResult === false")
    (OUT / "browser-check.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS: sample upload, cancel/continue, Excel download, 15 detail views (index3 KPI labels · chart ids), adapter shape, sidebar conditions, sidebar rail, fullscreen {'(Fullscreen API)' if full else '(fallback maximize)'}, no real names, JS errors 0")
    browser.close()
