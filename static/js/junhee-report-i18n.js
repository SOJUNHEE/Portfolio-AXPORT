/* (junhee) 2026-09-28 보고서 번역: 분석 엔진이 만든 한국어 문구(항목 이름·단위·출처·계산 근거·비고·부족 근거)를 영어·중국어·일본어로 옮긴다.
   junhee/scratchpad 생성기(gen_i18n.py)로 만든 표. 키는 원문의 숫자를 # 로 바꾼 것이고 번역문의 {0}{1}.. 에 원래 숫자를 되돌린다.
   표에 없는 문장은 원문(한국어) 그대로 둔다 — 낱말 치환으로 섞인 문장을 만들지 않는다.
   2026-09-28: 종합 대시보드·상세 5개 탭 문구 추가, 화면 번역기(axport-i18n.js t())에서도 먼저 이 표를 쓴다. */
(() => {
  "use strict";
  const D = {
"#개월 월간 수입 변동계수": [
"{0}-month monthly import coefficient of variation",
"{0}个月月度进口变异系数",
"{0}か月の月次輸入変動係数"
],
"HSK 통제번호 연결 후보": [
"HSK control-number candidates",
"HSK管制编号关联候选",
"HSK統制番号の候補"
],
"KRW 직접 환산 기준": [
"KRW direct conversion basis",
"韩元直接换算基准",
"KRW直接換算の基準"
],
"KRW 직접 환산 변동성": [
"KRW direct conversion volatility",
"韩元直接换算波动性",
"KRW直接換算の変動性"
],
"USD #거래일 환율 변동성": [
"USD {0}-trading-day FX volatility",
"美元{0}个交易日汇率波动性",
"USD {0}営業日の為替変動性"
],
"USD 최근 #개 관측간격 로그변화 표준편차(참고)": [
"USD std. dev. of log changes over the last {0} observation intervals (reference)",
"美元最近{0}个观测间隔对数变化标准差（参考）",
"USD 直近{0}観測間隔の対数変化の標準偏差（参考）"
],
"USD 최신 공표 참고환율": [
"USD latest published reference rate",
"美元最新公布参考汇率",
"USD 最新公表参考レート"
],
"거래별 실제 적용 관세": [
"Actual tariff applied per transaction",
"按交易实际适用关税",
"取引別の実際の適用関税"
],
"거래처·최종사용자 이름 일치 후보": [
"Counterparty/end-user name matches",
"交易方·最终用户名称匹配候选",
"取引先・最終需要者の名称一致候補"
],
"결제통화 환율 변동성": [
"Settlement-currency FX volatility",
"结算货币汇率波动性",
"決済通貨の為替変動性"
],
"공식 조회 고시의 시행일": [
"Effective date of the official notice consulted",
"所查询官方公告的施行日",
"照会した公式告示の施行日"
],
"급감 계산에 유효한 인접 월 쌍": [
"Adjacent month pairs valid for drop calculation",
"可用于骤降计算的相邻月份对",
"急減計算に有効な隣接月ペア"
],
"급감 빈도(유효 쌍 기준)": [
"Sharp-drop frequency (valid pairs)",
"骤降频率（按有效月份对）",
"急減頻度（有効ペア基準）"
],
"기업 기재 전체 배송 소요일(동일 그룹 평균)": [
"Company-reported door-to-door days (same-group average)",
"企业填报全程配送天数（同组平均）",
"企業記載の全配送日数（同一グループ平均）"
],
"기업 배송시각·인수참조 기재 완성도": [
"Completeness of company delivery times and receipt references",
"企业配送时间·签收参照填报完整度",
"企業の配送時刻・受領参照の記載完成度"
],
"기준일까지 도착 확인된 물류 기록": [
"Logistics records with arrival confirmed by the reference date",
"截至基准日已确认到达的物流记录",
"基準日までに到着確認された物流記録"
],
"대상에 연결된 기업 증빙목록 참조": [
"Company evidence list linked to the target",
"与对象关联的企业证明清单",
"対象に紐づく企業証憑リスト参照"
],
"대세계 연간 수입시장 규모": [
"Annual world import market size",
"全球年度进口市场规模",
"対世界年間輸入市場規模"
],
"목적국 월별 수입금액·전월비": [
"Destination monthly imports · month-on-month",
"目的国月度进口额·环比",
"輸出先の月別輸入額・前月比"
],
"목적국·HS 수입규제 후보": [
"Destination/HS import-restriction candidates",
"目的国·HS进口限制候选",
"輸出先・HS輸入規制の候補"
],
"미완료·도착 미기재 기록": [
"Incomplete records / arrival not recorded",
"未完成·未填到达的记录",
"未完了・到着未記載の記録"
],
"선택 거래의 기재 통화": [
"Currency recorded for the selected transactions",
"所选交易填报的货币",
"選択取引の記載通貨"
],
"선택 제품·목적국 기업 실적 단가": [
"Company actual unit price for the selected product and destination",
"所选产品·目的国企业实绩单价",
"選択製品・輸出先の企業実績単価"
],
"세계 반도체 산업 매출(국가·HS 시장과 별도)": [
"Global semiconductor sales (separate from country/HS market)",
"全球半导体行业销售额（与国家·HS市场分开）",
"世界半導体産業売上（国・HS市場とは別）"
],
"수입액 #년 CAGR": [
"{0}-year import CAGR",
"进口额{0}年CAGR",
"輸入額{0}年CAGR"
],
"수입액 누계 전년동기 증가율": [
"Year-to-date import growth (YoY)",
"进口额累计同比增长率",
"輸入額累計の前年同期比"
],
"수출 통계 단가 전년 동기간 변화율": [
"Year-on-year change in export statistical unit value",
"出口统计单价同比变化率",
"輸出統計単価の前年同期比変化率"
],
"시각·POD참조가 있는 기업 기재 거래": [
"Company-reported transactions with times and POD reference",
"含时间·POD参照的企业填报交易",
"時刻・POD参照のある企業記載取引"
],
"완료 기록의 예정 도착 준수율": [
"On-time arrival rate of completed records",
"已完成记录的按期到达率",
"完了記録の予定到着遵守率"
],
"월간 수입 관측 범위": [
"Monthly import observation coverage",
"月度进口观测范围",
"月次輸入の観測範囲"
],
"유효기한이 남은 USD 운임 기재": [
"Valid (unexpired) USD freight entries",
"仍在有效期内的美元运费填报",
"有効期限内のUSD運賃記載"
],
"전월 대비 #% 이상 감소": [
"Drops of {0}% or more month-on-month",
"环比下降{0}%以上",
"前月比{0}%以上の減少"
],
"전체 목적지 대비 해당국 통계 단가 수준": [
"Destination unit value relative to all destinations",
"该国统计单价相对全部目的地的水平",
"全輸出先に対する対象国の統計単価水準"
],
"직항·무환적 출발 빈도": [
"Direct / no-transshipment departure frequency",
"直航·无转运出发频率",
"直行・積替なし出発頻度"
],
"최근 #개월 수입액 전년동기 증가율": [
"Last {0} months import growth (YoY)",
"最近{0}个月进口额同比增长率",
"直近{0}か月輸入額の前年同期比"
],
"컴퓨터·전자·광학기기 수출물가지수(산업 배경)": [
"Computer, electronic & optical export price index (industry background)",
"计算机·电子·光学设备出口价格指数（行业背景）",
"コンピュータ・電子・光学機器輸出物価指数（産業背景）"
],
"한국 전체 목적지 수출 통계 기준단가": [
"Korea's all-destination export statistical unit value",
"韩国全部目的地出口统计基准单价",
"韓国の全輸出先向け輸出統計基準単価"
],
"한국산 HS# 관세 참고 세율": [
"Reference tariff rate on Korean HS{0}",
"韩国产HS{0}关税参考税率",
"韓国産HS{0}関税の参考税率"
],
"한국의 해당국 수출 통계 단가": [
"Korea's export statistical unit value to the destination",
"韩国对该国出口统计单价",
"韓国の対象国向け輸出統計単価"
],
"한국의 해당국 연간 수출액": [
"Korea's annual exports to the destination",
"韩国对该国年度出口额",
"韓国の対象国向け年間輸出額"
],
"해당국 통계 단가 금액 포괄률": [
"Value coverage of the destination unit-value sample",
"该国统计单价金额覆盖率",
"対象国統計単価の金額カバー率"
],
"대세계 수입시장 규모": [
"World import market size",
"全球进口市场规模",
"対世界輸入市場規模"
],
"한국의 해당국 수출규모": [
"Korea's exports to the destination",
"韩国对该国出口规模",
"韓国の対象国向け輸出規模"
],
"수입 누계 성장": [
"Year-to-date import growth",
"进口累计增长",
"輸入累計成長"
],
"수입 #년 성장": [
"{0}-year import growth",
"进口{0}年增长",
"輸入{0}年成長"
],
"최근 #개월 수입 성장": [
"Last {0} months import growth",
"最近{0}个月进口增长",
"直近{0}か月輸入成長"
],
"희망가격의 제품원가 차감 여지": [
"Cost headroom in target price",
"目标售价扣除产品成本的空间",
"希望価格の製品原価控除余地"
],
"#일 희망물량 충족": [
"{0}-day target volume coverage",
"{0}天目标数量满足度",
"{0}日希望数量の充足"
],
"출고 준비기간": [
"Dispatch lead time",
"出货准备期",
"出荷準備期間"
],
"국제운송 실행조건": [
"International transport conditions",
"国际运输执行条件",
"国際輸送の実行条件"
],
"수입 변동성": [
"Import volatility",
"进口波动性",
"輸入変動性"
],
"수입 급감 빈도": [
"Frequency of sharp import drops",
"进口骤降频率",
"輸入急減頻度"
],
"% (HS# 최신 조치)": [
"% (latest HS{0} measure)",
"%（HS{0}最新措施）",
"%（HS{0}最新措置）"
],
"USD (최근 월)": [
"USD (latest month)",
"USD（最近月份）",
"USD（直近月）"
],
"USD/개": [
"USD/unit",
"美元/件",
"USD/個"
],
"개월/#개월": [
"months / {0} months",
"个月/{0}个月",
"か月/{0}か月"
],
"건": [
"case(s)",
"件",
"件"
],
"배": [
"×",
"倍",
"倍"
],
"비율": [
"ratio",
"比率",
"比率"
],
"쌍/#쌍": [
"pairs / {0} pairs",
"对/{0}对",
"ペア/{0}ペア"
],
"일": [
"day(s)",
"天",
"日"
],
"종류": [
"type(s)",
"种",
"種類"
],
"천원/#TEU": [
"KRW thousand/{0}TEU",
"千韩元/{0}TEU",
"千ウォン/{0}TEU"
],
"회": [
"time(s)",
"次",
"回"
],
"회/주": [
"per week",
"次/周",
"回/週"
],
"후보 HSK 수 (통제번호 #개)": [
"candidate HSK (control numbers: {0})",
"候选HSK数（管制编号{0}个）",
"候補HSK数（統制番号{0}件）"
],
"개월": [
"months",
"个月",
"か月"
],
"UN Comtrade (엔진 수집)": [
"UN Comtrade (engine retrieval)",
"UN Comtrade（引擎采集）",
"UN Comtrade（エンジン収集）"
],
"관세청": [
"Korea Customs Service",
"韩国关税厅",
"韓国関税庁"
],
"관세청 품목별 전체 수출": [
"KCS exports by item (all destinations)",
"关税厅按品目全部出口",
"関税庁 品目別全体輸出"
],
"관세청 운송비용 HWPX 보유 원표": [
"KCS freight-cost source table (HWPX)",
"关税厅运输费用HWPX原表",
"関税庁 運送費用HWPX原表"
],
"국가법령정보센터": [
"Korea Law Information Center",
"国家法令信息中心",
"国家法令情報センター"
],
"기업 업로드": [
"Company upload",
"企业上传",
"企業アップロード"
],
"한국은행 ECOS": [
"Bank of Korea ECOS",
"韩国银行 ECOS",
"韓国銀行 ECOS"
],
"한국은행": [
"Bank of Korea",
"韩国银行",
"韓国銀行"
],
"전략물자 HSK 연계표": [
"Strategic-item HSK crosswalk",
"战略物资HSK对照表",
"戦略物資HSK対応表"
],
"(수입액(Y)/수입액(Y−#))^(#/#) − #": [
"(imports(Y)/imports(Y−{0}))^({1}/{2}) − {3}",
"(进口额(Y)/进口额(Y−{0}))^({1}/{2}) − {3}",
"(輸入額(Y)/輸入額(Y−{0}))^({1}/{2}) − {3}"
],
"#월~선택 기준월 수입액 합 / 전년 같은 기간 합 − #": [
"Imports from month {0} to the reference month / same period of the prior year − {1}",
"{0}月至所选基准月进口额合计 / 上年同期合计 − {1}",
"{0}月〜選択基準月の輸入額合計 / 前年同期間の合計 − {1}"
],
"#% 이상 감소 횟수 / 유효한 인접 월 쌍 수": [
"Number of drops of {0}% or more / number of valid adjacent month pairs",
"下降{0}%以上的次数 / 有效相邻月份对数",
"{0}%以上減少の回数 / 有効な隣接月ペア数"
],
"#개 수준·#개 일별 로그변화 및 기대 공표일 완전성 검증 필요": [
"{0} levels and {1} daily log changes; completeness against expected publication dates must be verified",
"需{0}个水平值·{1}个日对数变化及预期公布日完整性验证",
"{0}個の水準・{1}個の日次対数変化と公表予定日の完全性の検証が必要"
],
"#개 환율 수준 → ln(e[i]/e[i-#]) #개 → 표본표준편차(ddof=#), 비연율화": [
"{0} FX levels → {2} values of ln(e[i]/e[i-{1}]) → sample std. dev. (ddof={3}), not annualized",
"{0}个汇率水平 → {2}个 ln(e[i]/e[i-{1}]) → 样本标准差(ddof={3})，未年化",
"{0}個の為替水準 → ln(e[i]/e[i-{1}]) {2}個 → 標本標準偏差(ddof={3})、非年率化"
],
"WSTS Worldwide 월별 원값 × #": [
"WSTS Worldwide monthly raw value × {0}",
"WSTS Worldwide 月度原值 × {0}",
"WSTS Worldwide 月次原値 × {0}"
],
"관세청 품목별 전체 수출의 같은 #개월 유효 금액 합 / 순중량 합": [
"Valid value / net weight over the same {0} months of KCS all-destination exports by item",
"关税厅按品目全部出口同{0}个月有效金额合计 / 净重合计",
"関税庁 品目別全体輸出の同じ{0}か月の有効金額合計 / 正味重量合計"
],
"금액 합 / 수량 합": [
"Sum of value / sum of quantity",
"金额合计 / 数量合计",
"金額合計 / 数量合計"
],
"금액·양의 순중량이 함께 있는 표본의 expDlr 합 / expWgt 합": [
"Sum of expDlr / sum of expWgt for samples with both value and positive net weight",
"同时有金额和正净重的样本 expDlr 合计 / expWgt 合计",
"金額と正の正味重量がある標本のexpDlr合計 / expWgt合計"
],
"대세계 월간 수입액 · 누락 월을 #으로 채우지 않음": [
"Monthly world imports · missing months not filled with {0}",
"全球月度进口额 · 缺失月份不以{0}填补",
"対世界月次輸入額・欠損月を{0}で埋めない"
],
"동일 국가·HS#·HS#·연간·수입·대세계 primaryValue": [
"Same country · HS{0} · HS{1} · annual · imports · world primaryValue",
"同一国家·HS{0}·HS{1}·年度·进口·全球 primaryValue",
"同一国・HS{0}・HS{1}・年間・輸入・対世界 primaryValue"
],
"동일 그룹 거래별 (최종인수UTC − 운송인인계UTC) / #초의 산술평균": [
"Arithmetic mean per same-group transaction of (final receipt UTC − carrier handover UTC) / {0} s",
"同组各交易（最终签收UTC − 承运人交接UTC）/ {0}秒的算术平均",
"同一グループ取引別（最終受領UTC − 運送人引渡UTC）/ {0}秒の算術平均"
],
"분석 기준일 이전의 가장 최근 조치행 best_avlbl / #; 최신 공란은 유지": [
"Latest measure row before the analysis date: best_avlbl / {0}; latest blanks are kept",
"分析基准日之前最近的措施行 best_avlbl / {0}；最新空白保持不变",
"分析基準日以前の最新措置行 best_avlbl / {0}；最新の空欄は維持"
],
"선택 HSK# 정확 일치 또는 HS# 하위 HSK의 고유 통제번호 수": [
"Unique control numbers for an exact match of the selected HSK{0} or HSK codes under HS{1}",
"所选HSK{0}精确匹配或HS{1}下级HSK的唯一管制编号数",
"選択HSK{0}の完全一致またはHS{1}下位HSKの固有統制番号数"
],
"선택 기준월까지 #개월 금액 합 / 전년 같은 #개월 금액 합 − #": [
"Sum of {0} months to the reference month / same {1} months of the prior year − {2}",
"截至所选基准月{0}个月金额合计 / 上年同{1}个月金额合计 − {2}",
"選択基準月までの{0}か月の金額合計 / 前年同じ{1}か月の金額合計 − {2}"
],
"선택 제품·목적국 거래의 제공 단가; 여러 모델·거래를 평균하지 않음": [
"Unit price given for the selected product/destination deal; models and deals are not averaged",
"所选产品·目的国交易的提供单价；不对多个型号·交易取平均",
"選択製品・輸出先取引の提示単価；複数モデル・取引を平均しない"
],
"실제도착일≤예정도착일인 완료 기록 / 기준일까지 도착 확인된 기록 ×#": [
"Completed records with actual arrival ≤ scheduled arrival / records with arrival confirmed by the reference date ×{0}",
"实际到达日≤预计到达日的已完成记录 / 截至基准日已确认到达的记录 ×{0}",
"実到着日≤予定到着日の完了記録 / 基準日までに到着確認された記録 ×{0}"
],
"원 고시환율 / 고시통화량": [
"Posted KRW rate / posted currency unit",
"韩元公告汇率 / 公告货币单位",
"ウォン告示レート / 告示通貨量"
],
"원화 기준 원표 지수; 개별 제품 가격으로 환산하지 않음": [
"KRW-based source index; not converted to individual product prices",
"以韩元计的原表指数；不换算为单个产品价格",
"ウォン基準の原表指数；個別製品価格に換算しない"
],
"유효시각·POD참조 거래 수 / 선택 범위의 수출예정·유효실적 고유 거래ID 수": [
"Transactions with valid times and POD reference / unique transaction IDs of planned and valid exports in scope",
"有效时间·POD参照的交易数 / 所选范围内出口计划·有效实绩的唯一交易ID数",
"有効時刻・POD参照の取引数 / 選択範囲の輸出予定・有効実績の固有取引ID数"
],
"유효한 인계·최종 인수 시각과 POD참조를 가진 서로 다른 거래ID 수": [
"Distinct transaction IDs with valid handover and final receipt times and a POD reference",
"具有有效交接·最终签收时间和POD参照的不同交易ID数",
"有効な引渡・最終受領時刻とPOD参照を持つ異なる取引ID数"
],
"이전 달 수입액>#이고 두 인접 달이 모두 관측된 경우": [
"Where the previous month's imports > {0} and both adjacent months are observed",
"上月进口额>{0}且相邻两个月均有观测时",
"前月の輸入額>{0}かつ隣接する2か月がともに観測された場合"
],
"적용 원문·거래조건 검증 전 미산출": [
"Not calculated until the applicable text and deal terms are verified",
"在核实适用原文·交易条件前不计算",
"適用原文・取引条件の検証前は未算出"
],
"중량이 확인된 관측의 금액 합 / 전체 수출금액 합; 총금액 #이면 정의하지 않음": [
"Value of observations with confirmed weight / total export value; undefined if the total is {0}",
"已确认重量观测的金额合计 / 全部出口金额合计；总金额为{0}时不定义",
"重量確認済み観測の金額合計 / 全輸出金額合計；総額が{0}なら定義しない"
],
"총계·중복 소계를 제외한 #개월 expDlr 합계": [
"Sum of expDlr over {0} months excluding totals and duplicate subtotals",
"剔除总计·重复小计后的{0}个月 expDlr 合计",
"総計・重複小計を除いた{0}か月のexpDlr合計"
],
"최근 완결 #개월 합계단가 / 전년 같은 #개월 합계단가 − #": [
"Unit value of the latest complete {0} months / same {1} months of the prior year − {2}",
"最近完整{0}个月合计单价 / 上年同{1}个月合计单价 − {2}",
"直近完結{0}か月の合計単価 / 前年同じ{1}か月の合計単価 − {2}"
],
"표본표준편차(ddof=#) / #개월 평균 수입액": [
"Sample std. dev. (ddof={0}) / {1}-month average imports",
"样本标准差(ddof={0}) / {1}个月平均进口额",
"標本標準偏差(ddof={0}) / {1}か月平均輸入額"
],
"해당국 USD/kg 통계 단가 / 한국 전체 목적지 USD/kg 통계 단가": [
"Destination USD/kg unit value / Korea all-destination USD/kg unit value",
"该国 USD/kg 统计单价 / 韩国全部目的地 USD/kg 统计单价",
"対象国USD/kg統計単価 / 韓国全輸出先USD/kg統計単価"
],
"현재 달≤이전 달×#; 두 관측값이 인접하며 이전 달>#": [
"Current month ≤ previous month × {0}; the two observations are adjacent and the previous month > {1}",
"当月≤上月×{0}；两个观测相邻且上月>{1}",
"当月≤前月×{0}；2つの観測が隣接し前月>{1}"
],
"#개월/#쌍이 완비되어야 전체 기간 지표로 해석할 수 있습니다.": [
"It can be read as a full-period indicator only when {0} months / {1} pairs are complete.",
"需{0}个月/{1}对完备才能解读为全期指标。",
"{0}か月/{1}ペアがそろって初めて全期間の指標として解釈できます。"
],
"#개 관측으로 계산한 참고값입니다.": [
"Reference value calculated from {0} observations.",
"基于{0}个观测计算的参考值。",
"{0}個の観測から算出した参考値です。"
],
"공표 달력이 없어 #거래일 완전성은 확인하지 못했습니다.": [
"Without a publication calendar, {0}-trading-day completeness could not be confirmed.",
"由于没有公布日历，无法确认{0}个交易日的完整性。",
"公表カレンダーがないため{0}営業日の完全性は確認できませんでした。"
],
"계열별 기대 공표일을 검증하기 전까지 확정 지표를 산출하지 않습니다.": [
"No final indicator is produced until expected publication dates per series are verified.",
"在验证各序列预期公布日之前不计算确定指标。",
"系列ごとの公表予定日を検証するまで確定指標を算出しません。"
],
"기업 입력 견적입니다.": [
"This is a company-entered quote.",
"这是企业输入的报价。",
"企業が入力した見積です。"
],
"통계 USD/kg과 직접 비교하지 않으며 실제 체결·수익을 보증하지 않습니다.": [
"It is not compared directly with statistical USD/kg and does not guarantee an actual deal or profit.",
"不与统计 USD/kg 直接比较，也不保证实际成交或收益。",
"統計USD/kgと直接比較せず、実際の成約・収益を保証しません。"
],
"문서 진위가 검증된 배송 완료 건수가 아닙니다.": [
"Not a count of deliveries with verified documents.",
"并非经文件真伪验证的配送完成件数。",
"文書の真正性が検証された配送完了件数ではありません。"
],
"예정 거래와 미기재 거래도 분모에 포함한 자료 완성도이며 운송 성공률이 아닙니다.": [
"Data completeness with planned and unrecorded deals in the denominator; not a transport success rate.",
"分母包含计划交易和未填交易的资料完整度，并非运输成功率。",
"予定取引と未記載取引も分母に含めた資料完成度であり、輸送成功率ではありません。"
],
"선택 거래의 실제 결제통화를 입력해 주세요.": [
"Enter the actual settlement currency of the selected deals.",
"请输入所选交易的实际结算货币。",
"選択取引の実際の決済通貨を入力してください。"
],
"비교 #개월의 수출금액 관측이 모두 확인되지 않았습니다.": [
"Export value observations for all {0} comparison months were not confirmed.",
"未能确认全部{0}个比较月份的出口金额观测。",
"比較{0}か月の輸出金額の観測がすべては確認できませんでした。"
],
"앞선 요청에서 서비스 접근·인증 오류가 확인되어 같은 서비스의 후속 요청을 보류했습니다.": [
"An access/authentication error in an earlier request put later requests to the same service on hold.",
"先前请求出现服务访问·认证错误，已暂停对同一服务的后续请求。",
"先行リクエストでサービスのアクセス・認証エラーが確認されたため、同じサービスへの後続リクエストを保留しました。"
],
"원화 직접 환산 관계입니다.": [
"Direct KRW conversion relationship.",
"这是韩元直接换算关系。",
"ウォンの直接換算関係です。"
],
"수입원가 등 간접 환율 노출이 없다는 뜻은 아닙니다.": [
"It does not mean there is no indirect FX exposure such as import costs.",
"并不表示不存在进口成本等间接汇率敞口。",
"輸入原価などの間接的な為替エクスポージャーがないという意味ではありません。"
],
"#개 연속 관측값과 양수 평균이 필요합니다.": [
"{0} consecutive observations and a positive mean are required.",
"需要{0}个连续观测值和正的平均值。",
"{0}個の連続観測値と正の平均が必要です。"
],
"명확한 거래 연결, 인계·최종 인수 시각과 각 시간대, POD참조가 모두 필요합니다.": [
"A clear transaction link, handover and final receipt times with time zones, and a POD reference are all required.",
"需要明确的交易关联、交接·最终签收时间及各自时区，以及POD参照。",
"明確な取引の紐付け、引渡・最終受領時刻と各タイムゾーン、POD参照がすべて必要です。"
],
"선택 거래의 거래처/최종사용자 이름이 필요합니다.": [
"Counterparty/end-user names for the selected deals are required.",
"需要所选交易的交易方/最终用户名称。",
"選択取引の取引先/最終需要者名が必要です。"
],
"일자 단위 표본 관측입니다.": [
"Day-level sample observation.",
"这是以日为单位的样本观测。",
"日単位の標本観測です。"
],
"미완료/미기재 기록을 제외하므로 향후 납기 확률이 아닙니다.": [
"Incomplete/unrecorded records are excluded, so this is not a future on-time probability.",
"由于排除了未完成/未填记录，并非未来交期概率。",
"未完了/未記載の記録を除外するため、将来の納期確率ではありません。"
],
"출발/도착 허브, 확정 화물 운항표, 환적 여부 및 조회기간 자료가 필요합니다.": [
"Departure/arrival hubs, a confirmed cargo schedule, transshipment status and query-period data are required.",
"需要出发/到达枢纽、确定的货运航班表、是否转运及查询期间资料。",
"出発/到着ハブ、確定貨物運航表、積替の有無と照会期間の資料が必要です。"
],
"같은 범위의 비교기간 자료가 모두 확인되지 않았습니다.": [
"Comparison-period data for the same scope were not all confirmed.",
"未能全部确认同一范围的比较期间资料。",
"同じ範囲の比較期間の資料がすべては確認できませんでした。"
],
"같은 범위의 현재·전년 비교자료가 필요합니다.": [
"Current and prior-year comparison data for the same scope are required.",
"需要同一范围的本期·上年比较资料。",
"同じ範囲の当期・前年比較資料が必要です。"
],
"선택 제품·목적국에 유효한 동일 단위·통화의 수출실적이 없습니다.": [
"No valid export records in the same unit and currency for the selected product and destination.",
"所选产品·目的国没有同一单位·货币的有效出口实绩。",
"選択製品・輸出先に同一単位・通貨の有効な輸出実績がありません。"
],
"해당 기간의 관측이 없습니다.": [
"No observations for the period.",
"该期间没有观测。",
"該当期間の観測がありません。"
],
"#으로 채우지 않습니다.": [
"Not filled with {0}.",
"不以{0}填补。",
"{0}で埋めません。"
],
"해당국과 전체 목적지의 같은 기간 완전 표본 단가가 모두 확인되어야 합니다.": [
"Complete-sample unit values for the destination and all destinations over the same period must both be confirmed.",
"需确认该国与全部目的地同一期间的完整样本单价。",
"対象国と全輸出先の同期間の完全標本単価がともに確認される必要があります。"
],
"원화 직접 환산을 외화 시장 변동성이나 무위험으로 평가하지 않습니다.": [
"Direct KRW conversion is not assessed as FX market volatility or as risk-free.",
"不将韩元直接换算评估为外汇市场波动或无风险。",
"ウォンの直接換算を外為市場の変動性や無リスクとして評価しません。"
],
"목적국 세부세번·원산지·특혜·추가조치 검증이 필요합니다.": [
"Destination tariff subheadings, origin, preferences and additional measures must be verified.",
"需要核实目的国细分税号·原产地·优惠·附加措施。",
"輸出先の細分税番・原産地・特恵・追加措置の検証が必要です。"
],
"보유 WTO 파일에 해당 목적국·HS# 참고치가 없습니다.": [
"The held WTO file has no reference value for this destination and HS{0}.",
"现有WTO文件中没有该目的国·HS{0}的参考值。",
"保有するWTOファイルに当該輸出先・HS{0}の参考値がありません。"
],
"유효한 월 쌍만 센 관측 횟수입니다.": [
"Observation count using valid month pairs only.",
"仅计算有效月份对的观测次数。",
"有効な月ペアのみを数えた観測回数です。"
],
"누락·이전 달 #은 비급감으로 처리하지 않습니다.": [
"Missing months or a previous month of {0} are not treated as non-drops.",
"缺失或上月为{0}的情况不视为非骤降。",
"欠損・前月{0}は非急減として扱いません。"
],
"금액·중량이 모두 #인 #행은 원본에 보존하며 합계에 기여하지 않습니다.": [
"{1} rows with both value and weight of {0} are kept in the source and do not contribute to totals.",
"金额·重量均为{0}的{1}行保留在原始数据中，不计入合计。",
"金額・重量がともに{0}の{1}行は原本に保存し、合計に寄与しません。"
],
"중량이 확인된 표본만 사용했습니다.": [
"Only samples with confirmed weight were used.",
"仅使用已确认重量的样本。",
"重量が確認された標本のみを使用しました。"
],
"전체 수출의 단가가 아니며 제외 금액을 추정 보충하지 않습니다.": [
"This is not the unit value of all exports, and excluded amounts are not estimated or filled in.",
"并非全部出口的单价，也不估算补充被排除的金额。",
"全輸出の単価ではなく、除外金額を推定で補いません。"
],
"비기여 #금액·#중량 행 #개; 중량을 확인할 수 없어 제외한 금액 # USD.": [
"Non-contributing rows with value {0} and weight {1}: {2}; value excluded because weight could not be confirmed: {3} USD.",
"非贡献的{0}金额·{1}重量行{2}个；因无法确认重量而排除的金额 {3} USD。",
"非寄与の{0}金額・{1}重量の行 {2}件；重量を確認できず除外した金額 {3} USD。"
],
"조회 시점의 현행 고시 판본 정보입니다.": [
"Information on the current notice version at query time.",
"这是查询时现行公告版本信息。",
"照会時点の現行告示版の情報です。"
],
"해당 제품·거래의 통제 해당 여부와 허가·적합성을 확정하지 않습니다.": [
"It does not determine whether the product or deal is controlled, or its licensing and eligibility.",
"并不确定该产品·交易是否受管制及许可·适合性。",
"当該製品・取引の統制該当有無と許可・適合性を確定しません。"
],
"HS·기업 개별 화물과 무관한 국가/지역별 총운송비용 잠정 통계.": [
"Provisional country/region total freight statistics unrelated to the HS code or the company's shipments.",
"与HS·企业个别货物无关的国家/地区总运输费用暂定统计。",
"HS・企業の個別貨物と無関係な国/地域別総運送費用の暫定統計。"
],
"#피트 컨테이너(#TEU) 기준입니다.": [
"Based on a {0}-foot container ({1}TEU).",
"以{0}英尺集装箱（{1}TEU）为准。",
"{0}フィートコンテナ（{1}TEU）基準です。"
],
"#개여도 비전략물자 판정이 아닙니다.": [
"Even {0} candidates do not mean a non-strategic-item determination.",
"即使为{0}个也不代表判定为非战略物资。",
"{0}件でも非戦略物資の判定ではありません。"
],
"사양·용도·최종사용자 검토가 필요합니다.": [
"Specifications, end use and end users must be reviewed.",
"需要审查规格·用途·最终用户。",
"仕様・用途・最終需要者の検討が必要です。"
],
"원산지·기업별 예외·현행 효력은 미판정.": [
"Origin, company-specific exceptions and current validity are not determined.",
"原产地·企业别例外·现行效力尚未判定。",
"原産地・企業別例外・現行効力は未判定。"
],
"한국대상 N인 항목도 원문 후보로만 보존합니다.": [
"Items with Korea-target N are kept only as source candidates.",
"韩国对象为N的项目也仅作为原文候选保留。",
"韓国対象Nの項目も原文候補としてのみ保存します。"
],
"제품 공통 참고와 거래별 참조를 구분합니다.": [
"Product-wide references and per-transaction references are distinguished.",
"区分产品通用参考与按交易参照。",
"製品共通の参考と取引別の参照を区別します。"
],
"목록의 기재 상태만 확인하며 실제 첨부·진위·법적 적용성은 검증하지 않았습니다.": [
"Only the list entries were checked; actual attachments, authenticity and legal applicability were not verified.",
"仅确认清单的填报状态，未验证实际附件·真伪·法律适用性。",
"リストの記載状態のみ確認し、実際の添付・真正性・法的適用性は検証していません。"
],
"계절성·추세를 제거하지 않은 원시 월간 수입액의 변동성입니다.": [
"Volatility of raw monthly imports without removing seasonality or trend.",
"未剔除季节性·趋势的原始月度进口额波动性。",
"季節性・トレンドを除去していない原系列の月次輸入額の変動性です。"
],
"동일 HS#·목적국·USD의 완료된 달만 포함.": [
"Only completed months with the same HS{0}, destination and USD are included.",
"仅包含同一HS{0}·目的国·USD的已完成月份。",
"同一HS{0}・輸出先・USDの完了した月のみ含む。"
],
"누락 월을 #으로 채우지 않습니다.": [
"Missing months are not filled with {0}.",
"缺失月份不以{0}填补。",
"欠損月を{0}で埋めません。"
],
"서로 다른 화물·노선의 운임을 평균 또는 합산하지 않습니다.": [
"Freight for different cargo or routes is not averaged or summed.",
"不对不同货物·航线的运费取平均或合计。",
"異なる貨物・航路の運賃を平均または合算しません。"
],
"운송사 확정·포함 비용은 미검증.": [
"Carrier confirmation and included costs are unverified.",
"承运人确认·包含费用未经核实。",
"運送会社の確定・含まれる費用は未検証。"
],
"실제 관측일의 참고환율이며 은행 체결환율·수수료를 대신하지 않습니다.": [
"Reference rate on the actual observation date; it does not replace bank execution rates or fees.",
"为实际观测日的参考汇率，不能替代银行成交汇率·手续费。",
"実際の観測日の参考レートであり、銀行の約定レート・手数料の代わりにはなりません。"
],
"통화가 기재된 선택 거래가 없습니다.": [
"No selected deal has a currency recorded.",
"没有填写货币的所选交易。",
"通貨が記載された選択取引がありません。"
],
"필요한 기업 기재값이 없어 정책 기준 #점을 적용했습니다.": [
"A required company entry is missing, so the policy midpoint of {0} was applied.",
"缺少所需企业填报值，已适用政策基准 {0} 分。",
"必要な企業記載値がないため政策基準の{0}点を適用しました。"
],
"유효한 기간·단위·출처의 원지표가 없어 정책 기준 #점을 적용했습니다.": [
"No source indicator with a valid period, unit and source, so the policy midpoint of {0} was applied.",
"缺少期间·单位·出处有效的原始指标，已适用政策基准 {0} 分。",
"有効な期間・単位・出典の原指標がないため政策基準の{0}点を適用しました。"
],
"경로·화물 수용·운임·최종 인도기한이 확인되지 않았습니다.": [
"Route, cargo acceptance, freight and the final delivery deadline were not confirmed.",
"路线·货物承运·运费·最终交付期限未确认。",
"経路・貨物受入・運賃・最終引渡期限が確認されていません。"
],
"준비기간을 국제배송시간으로 사용하지 않습니다.": [
"Preparation time is not used as international delivery time.",
"不将准备期作为国际配送时间。",
"準備期間を国際配送時間として使用しません。"
],
"기업이 기재한 사건 시각과 POD참조의 관측입니다.": [
"Observation of company-entered event times and POD references.",
"这是企业填报的事件时间和POD参照的观测。",
"企業が記載したイベント時刻とPOD参照の観測です。"
],
"실제 문서·최종 인수자·진위는 확인하지 않았습니다.": [
"Actual documents, final recipients and authenticity were not checked.",
"未确认实际文件·最终签收人·真伪。",
"実際の文書・最終受領者・真正性は確認していません。"
],
"동일 제품·노선 그룹도 포장·중량·취급조건이 같다고 확인된 것은 아닙니다.": [
"Even within the same product/route group, packaging, weight and handling conditions are not confirmed to be the same.",
"即使同一产品·航线组，也未确认包装·重量·处理条件相同。",
"同一製品・航路グループでも、梱包・重量・取扱条件が同じと確認されたわけではありません。"
],
"표본평균은 미래 배송시간·성공률 또는 물류 점수가 아닙니다.": [
"The sample mean is not a future delivery time, success rate or logistics score.",
"样本均值并非未来配送时间·成功率或物流分数。",
"標本平均は将来の配送時間・成功率または物流点数ではありません。"
],
"#일 공급가능수량": [
"{0}-day supply capacity",
"{0}天可供数量",
"{0}日供給可能数量"
],
"단위원가": [
"Unit cost",
"单位成本",
"単位原価"
],
"단위원가 통화": [
"Unit cost currency",
"单位成本货币",
"単位原価の通貨"
],
"보유 인증·시험자료": [
"Certifications and test data held",
"持有的认证·测试资料",
"保有する認証・試験資料"
],
"사양서 파일명": [
"Spec sheet file name",
"规格书文件名",
"仕様書ファイル名"
],
"제조국": [
"Country of manufacture",
"制造国",
"製造国"
],
"출고준비기간(일)": [
"Dispatch lead time (days)",
"出货准备期（天）",
"出荷準備期間（日）"
],
"판매단위": [
"Sales unit",
"销售单位",
"販売単位"
],
"희망거래조건": [
"Preferred trade terms",
"期望交易条件",
"希望取引条件"
],
"희망수출수량": [
"Target export quantity",
"期望出口数量",
"希望輸出数量"
],
"희망판매단가": [
"Target selling price",
"期望销售单价",
"希望販売単価"
],
"희망판매단가 통화": [
"Target selling price currency",
"期望销售单价货币",
"希望販売単価の通貨"
],
"거래처": [
"Counterparties",
"交易方",
"取引先"
],
"물류": [
"Logistics",
"物流",
"物流"
],
"수출실적": [
"Export records",
"出口实绩",
"輸出実績"
],
"제품정보": [
"Product info",
"产品信息",
"製品情報"
],
"수출예정": [
"Planned exports",
"出口计划",
"輸出予定"
],
"증빙목록": [
"Evidence list",
"证明清单",
"証憑リスト"
],
"기업정보": [
"Company info",
"企业信息",
"企業情報"
],
"수출예정거래": [
"Planned export deals",
"出口计划交易",
"輸出予定取引"
],
"원가·비용": [
"Costs and expenses",
"成本·费用",
"原価・費用"
],
"재고·생산": [
"Inventory and production",
"库存·生产",
"在庫・生産"
],
"규제 관문 · 확인 후보": [
"Regulatory gate · review candidates",
"监管关口 · 核查候选",
"規制ゲート · 確認候補"
],
"시장성 · 수입시장 규모와 성장": [
"Market · import size and growth",
"市场性 · 进口市场规模与增长",
"市場性 · 輸入市場の規模と成長"
],
"가격 · 제품원가 여지와 환율": [
"Price · cost headroom and FX",
"价格 · 产品成本空间与汇率",
"価格 · 製品原価の余地と為替"
],
"물류 · 공급·출고 준비": [
"Logistics · supply and dispatch readiness",
"物流 · 供货与出货准备",
"物流 · 供給・出荷準備"
],
"안정성 · 수입 변동성과 급감": [
"Stability · import volatility and sharp drops",
"稳定性 · 进口波动与骤降",
"安定性 · 輸入の変動と急減"
],
"통제번호·수입규제·거래 상대 이름 후보를 보여 줍니다.": [
"Shows control-number, import-restriction and counterparty-name candidates.",
"显示管制编号·进口限制·交易对象名称候选。",
"統制番号・輸入規制・取引相手名の候補を表示します。"
],
"후보는 판정이 아니며 규제는 점수에 더하지 않는 별도 관문입니다.": [
"Candidates are not determinations, and regulation is a separate gate not added to the score.",
"候选并非判定，监管是不计入分数的单独关口。",
"候補は判定ではなく、規制は点数に加えない別のゲートです。"
],
"대세계 수입액·한국 수출·성장률을 배점 #으로 평가합니다.": [
"Assesses world imports, Korea's exports and growth for {0} points.",
"以{0}分配分评估全球进口额·韩国出口·增长率。",
"対世界輸入額・韓国輸出・成長率を配点{0}で評価します。"
],
"누락 월은 #으로 채우지 않습니다.": [
"Missing months are not filled with {0}.",
"缺失月份不以{0}填补。",
"欠損月は{0}で埋めません。"
],
"희망판매가에서 제품원가를 뺀 여지를 배점 #으로 평가합니다.": [
"Assesses the headroom of target price minus product cost for {0} points.",
"以{0}分配分评估目标售价减去产品成本的空间。",
"希望販売価格から製品原価を引いた余地を配点{0}で評価します。"
],
"통계 단가·관세는 참고치입니다.": [
"Statistical unit values and tariffs are references.",
"统计单价·关税为参考值。",
"統計単価・関税は参考値です。"
],
"#일 공급가능량·출고 준비기간·국제운송 조건을 배점 #으로 평가합니다.": [
"Assesses {0}-day supply capacity, dispatch lead time and international transport conditions for {1} points.",
"以{1}分配分评估{0}天可供量·出货准备期·国际运输条件。",
"{0}日供給可能量・出荷準備期間・国際輸送条件を配点{1}で評価します。"
],
"운송비는 관세청 보도자료 참고치입니다.": [
"Freight is a Korea Customs press-release reference.",
"运费为关税厅新闻稿参考值。",
"運送費は関税庁報道資料の参考値です。"
],
"#개월 월간 수입의 변동계수·급감 빈도를 배점 #으로 평가합니다.": [
"Assesses the coefficient of variation and sharp-drop frequency of {0}-month monthly imports for {1} points.",
"以{1}分配分评估{0}个月月度进口的变异系数·骤降频率。",
"{0}か月の月次輸入の変動係数・急減頻度を配点{1}で評価します。"
],
"과거 변동이며 미래 손실 확률이 아닙니다.": [
"This is past volatility, not a probability of future loss.",
"为历史波动，并非未来损失概率。",
"過去の変動であり将来の損失確率ではありません。"
],
"종합 수출적합도": [
"Overall export suitability",
"综合出口适合度",
"総合輸出適合度"
],
"시장성·가격·물류·안정성 #개 영역의 참고 적합도입니다.": [
"Reference suitability across {0} areas: market, price, logistics and stability.",
"市场性·价格·物流·稳定性{0}个领域的参考适合度。",
"市場性・価格・物流・安定性の{0}分野の参考適合度です。"
],
"규제는 별도 관문이며 수출 성공확률이 아닙니다.": [
"Regulation is a separate gate; this is not a probability of export success.",
"监管为单独关口，并非出口成功概率。",
"規制は別のゲートであり、輸出成功確率ではありません。"
],
"종합 점수 # / #": [
"Overall score {0} / {1}",
"综合分 {0} / {1}",
"総合点数 {0} / {1}"
],
"참고 등급": [
"Reference grade",
"参考等级",
"参考等級"
],
"요인별 점수": [
"Scores by factor",
"各因素分数",
"要因別の点数"
],
"핵심 포인트": [
"Key points",
"要点",
"主なポイント"
],
"상세 리포트 보기 →": [
"View detailed report →",
"查看详细报告 →",
"詳細レポートを見る →"
],
"더보기 →": [
"More →",
"更多 →",
"詳細 →"
],
"전월 대비 –": [
"MoM –",
"环比 –",
"前月比 –"
],
"근거 반영률 #%": [
"Evidence coverage {0}%",
"依据反映率 {0}%",
"根拠反映率 {0}%"
],
"근거 반영률 -#%": [
"Evidence coverage -{0}%",
"依据反映率 -{0}%",
"根拠反映率 -{0}%"
],
"관문 · 종합 점수 제외": [
"Gate · excluded from overall score",
"关口 · 不计入综合分",
"ゲート · 総合点数から除外"
],
"엔진 배점 #/#": [
"Engine points {0}/{1}",
"引擎配分 {0}/{1}",
"エンジン配点 {0}/{1}"
],
"엔진 배점 시장성 #·가격 #·물류 #·안정성 # (근거 없는 항목은 정책 기준 #점)": [
"Engine points: market {0}, price {1}, logistics {2}, stability {3} (items without evidence use the policy midpoint {4})",
"引擎配分 市场性{0}·价格{1}·物流{2}·稳定性{3}（无依据项目按政策基准{4}分）",
"エンジン配点 市場性{0}・価格{1}・物流{2}・安定性{3}（根拠のない項目は政策基準{4}点）"
],
"생성 #-#-#": [
"Generated {0}-{1}-{2}",
"生成 {0}-{1}-{2}",
"生成 {0}-{1}-{2}"
],
"판단 기준 참고 적합도 v#(분석 엔진) · 규제는 별도 관문 · 등급: 근거 배점 # 미만 판단 근거 부족 · # 이상 조건부 검토 유망 · # 이상 조건부 검토 · # 미만 준비 보완 필요 · 수출 성공확률 아님": [
"Basis: reference suitability v{0} (analysis engine) · regulation is a separate gate · grades: evidence points under {1} = insufficient evidence · {2}+ promising, subject to review · {3}+ conditional review · under {4} preparation needed · not a probability of export success",
"判断基准 参考适合度 v{0}（分析引擎）· 监管为单独关口 · 等级：依据配分不足{1} 判断依据不足 · {2}以上 有条件审查·前景良好 · {3}以上 有条件审查 · 不足{4} 需补充准备 · 并非出口成功概率",
"判断基準 参考適合度 v{0}（分析エンジン）· 規制は別ゲート · 等級：根拠配点{1}未満 判断根拠不足 · {2}以上 条件付き検討・有望 · {3}以上 条件付き検討 · {4}未満 準備の補完が必要 · 輸出成功確率ではない"
],
"가상 샘플": [
"Fictional sample",
"虚构样本",
"架空サンプル"
],
"샘플 기업 (가상)": [
"Sample company (fictional)",
"样本企业（虚构）",
"サンプル企業（架空）"
],
"외부 근거 연계": [
"Linked to external evidence",
"关联外部依据",
"外部根拠と連携"
],
"제품": [
"Products",
"产品",
"製品"
],
"현재 대시보드에 표시 중인 엑셀 파일": [
"Excel file currently shown on the dashboard",
"当前仪表盘显示的Excel文件",
"現在ダッシュボードに表示中のExcelファイル"
],
"수출 적합도 참고 평가": [
"Export suitability reference",
"出口适合度参考评估",
"輸出適合度の参考評価"
],
"참고 적합도 v#": [
"Reference suitability v{0}",
"参考适合度 v{0}",
"参考適合度 v{0}"
],
"분석 엔진": [
"Analysis engine",
"分析引擎",
"分析エンジン"
],
"분석 엔진(참고 적합도 v#)": [
"Analysis engine (reference suitability v{0})",
"分析引擎（参考适合度 v{0}）",
"分析エンジン（参考適合度 v{0}）"
],
"자료 없음·조회 실패는 값을 채우지 않고 상태로 표시": [
"No data or failed queries are shown as a status, not filled with values",
"无资料·查询失败不填补数值，以状态显示",
"資料なし・照会失敗は値を補わず状態で表示"
],
"수출 성공확률이 아님": [
"Not a probability of export success",
"并非出口成功概率",
"輸出成功確率ではない"
],
"사이드바 접기": [
"Collapse sidebar",
"收起侧栏",
"サイドバーを折りたたむ"
],
"목적국 (분석 엔진 지원국)": [
"Destination (engine-supported countries)",
"目的国（分析引擎支持国家）",
"輸出先（分析エンジン対応国）"
],
"분석 HS 코드 (분석 엔진 지원 HS#)": [
"Analysis HS code (engine-supported HS{0})",
"分析HS编码（分析引擎支持的HS{0}）",
"分析HSコード（分析エンジン対応HS{0}）"
],
"바꾸면 다시 계산": [
"Recalculates on change",
"更改后重新计算",
"変更すると再計算"
],
"확인됨 #/#": [
"Available {0}/{1}",
"已确认 {0}/{1}",
"確認済み {0}/{1}"
],
"미국": [
"United States",
"美国",
"米国"
],
"중국": [
"China",
"中国",
"中国"
],
"일본": [
"Japan",
"日本",
"日本"
],
"독일": [
"Germany",
"德国",
"ドイツ"
],
"베트남": [
"Vietnam",
"越南",
"ベトナム"
],
"시장성": [
"Market",
"市场性",
"市場性"
],
"가격": [
"Price",
"价格",
"価格"
],
"안정성": [
"Stability",
"稳定性",
"安定性"
],
"규제 관문": [
"Regulatory gate",
"监管关口",
"規制ゲート"
],
"확인됨": [
"Available",
"已确认",
"確認済み"
],
"자료 부족": [
"Insufficient data",
"资料不足",
"資料不足"
],
"자료 없음": [
"No data",
"无资料",
"資料なし"
],
"검색 불가": [
"Search unavailable",
"无法检索",
"検索不可"
],
"검토 필요": [
"Review required",
"需要审查",
"要確認"
],
"계산값": [
"Calculated",
"计算值",
"計算値"
],
"계산됨": [
"Calculated",
"已计算",
"計算済み"
],
"기업 기재·미확인": [
"Company entry · unconfirmed",
"企业填报·未确认",
"企業記載・未確認"
],
"기재 누락": [
"Entry missing",
"填报缺失",
"記載漏れ"
],
"달력 미확인": [
"Calendar unconfirmed",
"日历未确认",
"カレンダー未確認"
],
"비교 불가": [
"Not comparable",
"无法比较",
"比較不可"
],
"산식 보류": [
"Formula on hold",
"公式暂缓",
"算式保留"
],
"원문 읽음": [
"Source read",
"已读原文",
"原文読込済み"
],
"일부": [
"Partial",
"部分",
"一部"
],
"자료 목록 없음": [
"No data list",
"无资料清单",
"資料リストなし"
],
"값": [
"Value",
"值",
"値"
],
"상태": [
"Status",
"状态",
"状態"
],
"자료": [
"Data",
"资料",
"資料"
],
"점수": [
"Score",
"分数",
"点数"
],
"제공기관": [
"Provider",
"提供机构",
"提供機関"
],
"조회일": [
"Retrieved",
"查询日",
"照会日"
],
"항목": [
"Item",
"项目",
"項目"
],
"배점 → 기여": [
"Points → contribution",
"配分 → 贡献",
"配点 → 寄与"
],
"기타": [
"Other",
"其他",
"その他"
],
"#~#점 · 회색은 정책 기준 #점(근거 없음)": [
"{0}–{1} pts · grey = policy midpoint {2} (no evidence)",
"{0}~{1}分 · 灰色为政策基准{2}分（无依据）",
"{0}〜{1}点 · 灰色は政策基準{2}点（根拠なし）"
],
"#개월 월간 수입액": [
"{0}-month monthly imports",
"{0}个月月度进口额",
"{0}か月の月次輸入額"
],
"#개월 월간 수입액 (USD)": [
"{0}-month monthly imports (USD)",
"{0}个月月度进口额（USD）",
"{0}か月の月次輸入額（USD）"
],
"#개 HSK": [
"{0} HSK",
"{0}个HSK",
"HSK {0}件"
],
"후보이며 해당 판정 아님": [
"Candidates, not a determination",
"为候选，并非判定",
"候補であり該当判定ではない"
],
"HSK 연계표": [
"HSK crosswalk",
"HSK对照表",
"HSK対応表"
],
"KOTRA 수입규제": [
"KOTRA import restrictions",
"KOTRA进口限制",
"KOTRA輸入規制"
],
"기업 증빙 목록": [
"Company evidence list",
"企业证明清单",
"企業証憑リスト"
],
"#개월 중 #개월 관측": [
"{1} of {0} months observed",
"{0}个月中观测到{1}个月",
"{0}か月中{1}か月を観測"
],
"−#% 이하 급감 달은 진하게 표시": [
"Months with drops of −{0}% or more are shown darker",
"下降−{0}%以下的月份加深显示",
"−{0}%以下の急減月は濃く表示"
],
"관세청 보도자료": [
"Korea Customs press release",
"关税厅新闻稿",
"関税庁報道資料"
],
"참고치": [
"Reference",
"参考值",
"参考値"
],
"규제 검토에 필요한 확인": [
"Checks needed for regulatory review",
"监管审查所需核查",
"規制検討に必要な確認"
],
"규제 관문 검토 필요": [
"Regulatory gate: review required",
"监管关口 需要审查",
"規制ゲート 要確認"
],
"규제 확인 후보 수": [
"Regulatory review candidates",
"监管核查候选数",
"規制確認候補数"
],
"규제 후보를 읽을 때": [
"Reading regulatory candidates",
"解读监管候选时",
"規制候補を読むとき"
],
"누계 전년동기": [
"YTD YoY",
"累计同比",
"累計前年同期比"
],
"최근 #개월 전년동기": [
"Last {0} months YoY",
"最近{0}个月同比",
"直近{0}か月前年同期比"
],
"#년 CAGR": [
"{0}-year CAGR",
"{0}年CAGR",
"{0}年CAGR"
],
"노선별 해상 수출 운송비": [
"Sea-export freight by route",
"按航线海运出口运费",
"航路別の海上輸出運送費"
],
"해상 수출 운송비 (노선별)": [
"Sea-export freight (by route)",
"海运出口运费（按航线）",
"海上輸出運送費（航路別）"
],
"배점 # 중 #점": [
"{1} of {0} points",
"配分{0}中{1}分",
"配点{0}中{1}点"
],
"행에 마우스를 올리면 산식": [
"Hover a row for the formula",
"鼠标悬停行可查看公式",
"行にマウスを置くと算式"
],
"변동계수·급감 계산 기간": [
"CV / sharp-drop calculation period",
"变异系数·骤降计算期间",
"変動係数・急減の計算期間"
],
"빈 달은 자료 없음": [
"Empty months = no data",
"空月份为无资料",
"空の月は資料なし"
],
"보유 원문": [
"Held source",
"持有原文",
"保有原文"
],
"보유 원문·공식 조회": [
"Held sources and official queries",
"持有原文·官方查询",
"保有原文・公式照会"
],
"조회일 기준": [
"As of query date",
"以查询日为准",
"照会日基準"
],
"분석 엔진이 남긴 근거": [
"Evidence left by the analysis engine",
"分析引擎留下的依据",
"分析エンジンが残した根拠"
],
"수입 성장률": [
"Import growth",
"进口增长率",
"輸入成長率"
],
"원/달러 환율": [
"KRW/USD exchange rate",
"韩元/美元汇率",
"ウォン/ドル為替レート"
],
"원/달러 환율 (매매기준율)": [
"KRW/USD rate (base rate)",
"韩元/美元汇率（基准汇率）",
"ウォン/ドル為替レート（売買基準率）"
],
"원/달러 환율 추이": [
"KRW/USD rate trend",
"韩元/美元汇率走势",
"ウォン/ドル為替レートの推移"
],
"월간 대세계 수입액 (USD)": [
"Monthly world imports (USD)",
"月度全球进口额（USD）",
"月次対世界輸入額（USD）"
],
"월간 대세계 수입액 추이": [
"Monthly world imports trend",
"月度全球进口额走势",
"月次対世界輸入額の推移"
],
"적합도 항목": [
"Suitability items",
"适合度项目",
"適合度項目"
],
"참고점수 #/#": [
"Reference score {0}/{1}",
"参考分 {0}/{1}",
"参考点数 {0}/{1}"
],
"참고점수 #": [
"Reference score {0}",
"参考分 {0}",
"参考点数 {0}"
],
"반영률 #%": [
"coverage {0}%",
"反映率 {0}%",
"反映率 {0}%"
],
"적합도 항목별 점수": [
"Scores by suitability item",
"各适合度项目分数",
"適合度項目別の点数"
],
"전월 대비 변화율": [
"Month-on-month change",
"环比变化率",
"前月比変化率"
],
"전월 대비 수입 변화율": [
"Month-on-month import change",
"进口环比变化率",
"輸入の前月比変化率"
],
"출처 #건": [
"Sources: {0}",
"出处 {0}条",
"出典 {0}件"
],
"확인 항목 #건": [
"Check items: {0}",
"核查项目 {0}项",
"確認項目 {0}件"
],
"확인 항목": [
"Check items",
"核查项目",
"確認項目"
],
"유의사항": [
"Notes",
"注意事项",
"留意事項"
],
"해석 시 유의사항": [
"Notes for interpretation",
"解读注意事项",
"解釈時の留意事項"
],
"한국은행 ECOS 일별": [
"Bank of Korea ECOS daily",
"韩国银行 ECOS 日度",
"韓国銀行ECOS 日次"
],
"#일": [
"{0} days",
"{0}天",
"{0}日"
],
"환율 관측이 없습니다 (ECOS API 키 확인)": [
"No FX observations (check ECOS API key)",
"没有汇率观测（请检查ECOS API密钥）",
"為替の観測がありません（ECOS APIキーを確認）"
],
"#-# 수입 자료 확인": [
"{0}-{1} import data confirmed",
"{0}-{1} 进口资料已确认",
"{0}-{1} 輸入資料を確認"
],
"#-#~#-#, 유효 월 #/#, 유효 인접 쌍 #/#": [
"{0}-{1}~{2}-{3}, valid months {4}/{5}, valid adjacent pairs {6}/{7}",
"{0}-{1}~{2}-{3}，有效月份 {4}/{5}，有效相邻月份对 {6}/{7}",
"{0}-{1}〜{2}-{3}、有効月 {4}/{5}、有効隣接ペア {6}/{7}"
],
"기간 #-#~#-#": [
"Period {0}-{1}~{2}-{3}",
"期间 {0}-{1}~{2}-{3}",
"期間 {0}-{1}〜{2}-{3}"
],
"HSK 통제번호 연결 후보 #개": [
"HSK control-number candidates: {0}",
"HSK管制编号关联候选 {0}个",
"HSK統制番号の候補 {0}件"
],
"목적국·HS 수입규제 후보 #건": [
"Destination/HS import-restriction candidates: {0}",
"目的国·HS进口限制候选 {0}件",
"輸出先・HS輸入規制の候補 {0}件"
],
"거래처·최종사용자 이름 일치 후보 미확인": [
"Counterparty/end-user name matches: unconfirmed",
"交易方·最终用户名称匹配候选 未确认",
"取引先・最終需要者の名称一致候補 未確認"
],
"선택 HS# #에 연결된 제품 #개": [
"{2} product(s) linked to the selected HS{0} {1}",
"与所选HS{0} {1}关联的产品{2}个",
"選択HS{0} {1}に紐づく製品{2}件"
],
"증빙목록 #행 기재 확인": [
"Evidence list: {0} rows recorded",
"证明清单 {0}行已填写",
"証憑リスト {0}行の記載を確認"
],
"# × (# − min(#개월 변동계수, #))": [
"{0} × ({1} − min({2}-month coefficient of variation, {3}))",
"{0} × ({1} − min({2}个月变异系数, {3}))",
"{0} × ({1} − min({2}か月変動係数, {3}))"
],
"# × (# − min(급감 빈도 / #, #))": [
"{0} × ({1} − min(sharp-drop frequency / {2}, {3}))",
"{0} × ({1} − min(骤降频率 / {2}, {3}))",
"{0} × ({1} − min(急減頻度 / {2}, {3}))"
],
"#일 공급가능량 / 희망수출수량 × #; #점 상한": [
"{0}-day supply capacity / target export quantity × {1}; capped at {2} pts",
"{0}天可供量 / 期望出口数量 × {1}；上限{2}分",
"{0}日供給可能量 / 希望輸出数量 × {1}；上限{2}点"
],
"#일 이하→#점, #일 이상→#점; 사이 구간 선형 보간": [
"≤{0} days→{1} pts, ≥{2} days→{3} pts; linear in between",
"≤{0}天→{1}分，≥{2}天→{3}分；中间线性插值",
"{0}日以下→{1}点、{2}日以上→{3}点；間は線形補間"
],
"USD #→#점, #만→#점, #천만→#점, #억→#점, #억→#점, #억→#점; 로그 보간": [
"USD 0→0 pts, 1M→20, 10M→40, 100M→60, 1B→80, 10B→100 pts; log interpolation",
"USD 0→0分，100万→20，1千万→40，1亿→60，10亿→80，100亿→100分；对数插值",
"USD 0→0点、100万→20、1千万→40、1億→60、10億→80、100億→100点；対数補間"
],
"USD #→#점, #만→#점, #만→#점, #천만→#점, #억→#점, #억→#점; 로그 보간": [
"USD 0→0 pts, 100k→20, 1M→40, 10M→60, 100M→80, 1B→100 pts; log interpolation",
"USD 0→0分，10万→20，100万→40，1千万→60，1亿→80，10亿→100分；对数插值",
"USD 0→0点、10万→20、100万→40、1千万→60、1億→80、10億→100点；対数補間"
],
"국제운송 경로·비용·인도기한 미평가: 정책 기준 #점": [
"International route, cost and delivery deadline not assessed: policy midpoint {0}",
"国际运输路线·费用·交付期限未评估：政策基准{0}分",
"国際輸送の経路・費用・引渡期限は未評価：政策基準{0}点"
],
"원값=(희망판매가−제품원가)/희망판매가 (동일 통화 환산); #% 이하→#점, #%→#점, #% 이상→#점": [
"Raw = (target price − product cost) / target price (same currency); ≤{0}%→{1} pts, {2}%→{3} pts, ≥{4}%→{5} pts",
"原值=(目标售价−产品成本)/目标售价（同币种换算）；≤{0}%→{1}分，{2}%→{3}分，≥{4}%→{5}分",
"原値=(希望販売価格−製品原価)/希望販売価格（同一通貨換算）；{0}%以下→{1}点、{2}%→{3}点、{4}%以上→{5}点"
],
"증가율 -#%→#점, #%→#점, +#%→#점; 선형 보간·범위 제한": [
"Growth -{0}%→{1} pts, {2}%→{3} pts, +{4}%→{5} pts; linear interpolation, clamped",
"增长率 -{0}%→{1}分，{2}%→{3}分，+{4}%→{5}分；线性插值·范围限制",
"増加率 -{0}%→{1}点、{2}%→{3}点、+{4}%→{5}点；線形補間・範囲制限"
],
"#거래일 공표 완전성": [
"{0}-trading-day publication completeness",
"{0}个交易日公布完整性",
"{0}営業日の公表完全性"
],
"개별 제품·거래 적용성": [
"Applicability to individual products/deals",
"对个别产品·交易的适用性",
"個別製品・取引への適用性"
],
"공통기간 비교 가능 여부": [
"Comparability over the common period",
"公共期间可比性",
"共通期間の比較可否"
],
"기업 물류 연결": [
"Company logistics link",
"企业物流关联",
"企業物流の連結"
],
"기업 배송 시각 기준": [
"Company delivery time basis",
"企业配送时间基准",
"企業配送時刻の基準"
],
"기업 제품 연결": [
"Company product link",
"企业产品关联",
"企業製品の連結"
],
"기업 최종 인수 근거": [
"Company final receipt evidence",
"企业最终签收依据",
"企業の最終受領根拠"
],
"목적국 수입규제·인증": [
"Destination import restrictions and certification",
"目的国进口限制·认证",
"輸出先の輸入規制・認証"
],
"미국 수출관리·제재": [
"US export controls and sanctions",
"美国出口管制·制裁",
"米国の輸出管理・制裁"
],
"상대 참고지수 산식": [
"Relative reference index formula",
"相对参考指数公式",
"相対参考指数の算式"
],
"점수 산식": [
"Score formula",
"分数公式",
"点数算式"
],
"선택 거래의 통화": [
"Currency of selected deals",
"所选交易的货币",
"選択取引の通貨"
],
"시장 안정성 관측 완결성": [
"Market stability observation completeness",
"市场稳定性观测完整性",
"市場安定性の観測完結性"
],
"원문 효력": [
"Legal effect of source text",
"原文效力",
"原文の効力"
],
"한국 전략물자·상황허가": [
"Korea strategic items / catch-all license",
"韩国战略物资·情况许可",
"韓国の戦略物資・状況許可"
],
"현행 고시 원문 확보": [
"Current notice text obtained",
"已获取现行公告原文",
"現行告示原文の確保"
],
"KOTRA 국별 대세계 수입규제 보유 CSV": [
"KOTRA import restrictions by country (held CSV)",
"KOTRA 各国进口限制（持有CSV）",
"KOTRA 国別輸入規制（保有CSV）"
],
"미국 ITA CSL 보유 CSV": [
"US ITA CSL (held CSV)",
"美国 ITA CSL（持有CSV）",
"米国 ITA CSL（保有CSV）"
],
"보유 전략물자 고시/개정안 원문": [
"Held strategic-item notice/amendment texts",
"持有的战略物资公告/修正案原文",
"保有する戦略物資告示/改正案原文"
],
"디램": [
"DRAM",
"DRAM",
"DRAM"
],
"에스램": [
"SRAM",
"SRAM",
"SRAM"
],
"플래시 메모리": [
"Flash memory",
"闪存",
"フラッシュメモリ"
],
"복합구조칩 집적회로": [
"Multi-chip integrated circuits",
"多芯片集成电路",
"マルチチップ集積回路"
],
"복합부품 집적회로(MCOs)": [
"Multi-component integrated circuits (MCOs)",
"多元件集成电路（MCOs）",
"マルチコンポーネント集積回路（MCOs）"
],
"하이브리드 집적회로": [
"Hybrid integrated circuits",
"混合集成电路",
"ハイブリッド集積回路"
],
"#개월 월간 수입통계 (UN Comtrade API 키)": [
"{0}-month monthly import statistics (UN Comtrade API key)",
"{0}个月月度进口统计（UN Comtrade API 密钥）",
"{0}か月の月次輸入統計（UN Comtrade APIキー）"
],
"간편입력 #일 공급가능수량·출고준비기간": [
"Simple-form {0}-day supply capacity and dispatch lead time",
"简易输入 {0}天可供数量·出货准备期",
"簡易入力 {0}日供給可能数量・出荷準備期間"
],
"간편입력 원가·희망판매단가 + 환율 (ECOS API 키)": [
"Simple-form cost and target price + FX (ECOS API key)",
"简易输入 成本·期望销售单价 + 汇率（ECOS API 密钥）",
"簡易入力 原価・希望販売単価 + 為替（ECOS APIキー）"
],
"규제는 점수 없이 관문으로 봅니다 (HSK 연계표·KOTRA·CSL 대조)": [
"Regulation is a gate without a score (HSK crosswalk, KOTRA, CSL check)",
"监管不计分，作为关口（对照HSK对照表·KOTRA·CSL）",
"規制は点数なしのゲートとして扱います（HSK対応表・KOTRA・CSL照合）"
],
"참고 적합도 #/# · 판단 근거 부족.": [
"Reference suitability {0}/{1} · Insufficient evidence.",
"参考适合度 {0}/{1} · 判断依据不足。",
"参考適合度 {0}/{1} · 判断根拠不足。"
],
"참고 적합도 #/# · 조건부 검토.": [
"Reference suitability {0}/{1} · Conditional review.",
"参考适合度 {0}/{1} · 有条件审查。",
"参考適合度 {0}/{1} · 条件付き検討。"
],
"참고 적합도 #/# · 조건부 검토 유망.": [
"Reference suitability {0}/{1} · Promising, subject to review.",
"参考适合度 {0}/{1} · 有条件审查·前景良好。",
"参考適合度 {0}/{1} · 条件付き検討・有望。"
],
"참고 적합도 #/# · 준비 보완 필요.": [
"Reference suitability {0}/{1} · Preparation needed.",
"参考适合度 {0}/{1} · 需补充准备。",
"参考適合度 {0}/{1} · 準備の補完が必要。"
],
"참고 적합도 #/# · 규제상 진행 제한.": [
"Reference suitability {0}/{1} · Restricted by regulation.",
"参考适合度 {0}/{1} · 受监管限制。",
"参考適合度 {0}/{1} · 規制上の進行制限。"
],
"참고 적합도 #/# · 규제 요건 확인 필요.": [
"Reference suitability {0}/{1} · Regulatory requirements to confirm.",
"参考适合度 {0}/{1} · 需确认监管要件。",
"参考適合度 {0}/{1} · 規制要件の確認が必要。"
],
"참고 적합도 #/#": [
"Reference suitability {0}/{1}",
"参考适合度 {0}/{1}",
"参考適合度 {0}/{1}"
],
"배점 #/#에 근거가 반영됐고 나머지는 정책 기준 #점입니다.": [
"Evidence covers {0}/{1} points; the rest use the policy midpoint of {2}.",
"配分{0}/{1}已反映依据，其余按政策基准{2}分。",
"配点{0}/{1}に根拠が反映され、残りは政策基準{2}点です。"
],
"규제 검토는 별도입니다.": [
"Regulatory review is separate.",
"监管审查另行进行。",
"規制検討は別です。"
],
"(근거 반영률 (기업 기재 포함) #% · 미평가 배점은 정책 기준 #점)": [
"(Evidence coverage (incl. company entries) {0}% · unassessed points use the policy midpoint {1})",
"（依据反映率（含企业填报）{0}% · 未评估配分按政策基准{1}分）",
"（根拠反映率（企業記載を含む）{0}% · 未評価の配点は政策基準{1}点）"
],
"기업의 희망가격과 기재 제품원가 기준입니다.": [
"Based on the company's target price and recorded product cost.",
"基于企业的目标售价和填报的产品成本。",
"企業の希望価格と記載製品原価に基づきます。"
],
"미확인 운임·보험·관세·수수료 차감 전이며 순이익률이 아닙니다.": [
"Before deducting unconfirmed freight, insurance, tariffs and fees; not a net margin.",
"为扣除未确认运费·保险·关税·手续费之前的数值，并非净利润率。",
"未確認の運賃・保険・関税・手数料の控除前であり、純利益率ではありません。"
],
"분석일 이전 #일 이내 공표환율로 환산한 시나리오입니다.": [
"A scenario converted at an FX rate published within {0} days before the analysis date.",
"为按分析日前{0}天内公布汇率换算的情景。",
"分析日前{0}日以内の公表レートで換算したシナリオです。"
],
"확인된 원지표에 고정된 서비스 참고기준을 적용했습니다.": [
"Applied a fixed service reference scale to the confirmed raw indicator.",
"对已确认的原始指标适用固定的服务参考基准。",
"確認された原指標に固定のサービス参考基準を適用しました。"
],
"국가 간 상대순위와 별개의 점수입니다.": [
"This score is separate from cross-country rankings.",
"该分数与国家间相对排名无关。",
"国家間の相対順位とは別の点数です。"
],
"기업 기재 #일 공급량 #개 / 희망수출량 #개.": [
"Company-reported {0}-day supply {1} units / target export {2} units.",
"企业填报{0}天供应量{1}个 / 期望出口量{2}个。",
"企業記載の{0}日供給量{1}個 / 希望輸出量{2}個。"
],
"희망물량 대비 #개 부족합니다.": [
"Short of the target volume by {0} units.",
"比期望数量少{0}个。",
"希望数量に対して{0}個不足しています。"
],
"희망물량을 충족합니다.": [
"Meets the target volume.",
"满足期望数量。",
"希望数量を満たします。"
],
"확정 주문·예약·실제 생산능력 검증은 아닙니다.": [
"This is not a verification of firm orders, bookings or actual capacity.",
"并非对确定订单·预订·实际产能的验证。",
"確定注文・予約・実際の生産能力の検証ではありません。"
],
"주문 후 생산·검사·포장의 기재 준비기간입니다.": [
"Recorded lead time for production, inspection and packing after order.",
"为订单后生产·检验·包装的填报准备期。",
"受注後の生産・検査・梱包の記載準備期間です。"
],
"해외 운송·통관시간과 약정 납기 충족 여부는 포함하지 않습니다.": [
"Overseas transport, customs time and meeting agreed delivery dates are not included.",
"不包括海外运输·通关时间及是否满足约定交期。",
"海外輸送・通関時間と約定納期の充足可否は含みません。"
],
"같은 지표의 관측 근거에서 CIF·FOB 평가기준 단절이 확인되어 미평가했습니다.": [
"Not assessed because a CIF/FOB valuation break was found in the indicator's evidence.",
"因该指标观测依据中发现CIF·FOB计价基准中断，未评估。",
"同一指標の観測根拠でCIF・FOB評価基準の断絶が確認されたため未評価としました。"
],
"계산 결과가 표시 가능한 숫자 범위를 벗어나 해당 항목을 미평가했습니다.": [
"Not assessed because the result was outside the displayable numeric range.",
"计算结果超出可显示的数值范围，未评估该项目。",
"計算結果が表示可能な数値範囲を外れたため未評価としました。"
],
"기업 제품과 선택 HS·분류판이 유일하게 연결되지 않았습니다.": [
"The company product is not uniquely linked to the selected HS/edition.",
"企业产品未与所选HS·分类版唯一关联。",
"企業製品と選択HS・分類版が一意に紐づいていません。"
],
"기존 상세양식의 개별 지표는 유지합니다.": [
"Individual indicators from the existing detailed form are kept.",
"保留原有详细表格的个别指标。",
"既存の詳細様式の個別指標は維持します。"
],
"이번 기업 계획 참고평가는 간편양식의 한 제품에 적용합니다.": [
"This company-plan reference assessment applies to one product in the simple form.",
"本次企业计划参考评估适用于简易表格中的一个产品。",
"今回の企業計画の参考評価は簡易様式の1製品に適用します。"
],
"수출계획의 대상국이 선택 국가와 다릅니다.": [
"The export plan's destination differs from the selected country.",
"出口计划的对象国与所选国家不同。",
"輸出計画の対象国が選択国と異なります。"
],
"연속 #개월·유효 #쌍의 안정성 근거가 완비되지 않았습니다.": [
"Stability evidence of {0} consecutive months and {1} valid pairs is not complete.",
"连续{0}个月·有效{1}对的稳定性依据不完整。",
"連続{0}か月・有効{1}ペアの安定性根拠がそろっていません。"
],
"원가와 희망가격의 통화·판매단위를 확인할 수 없어 미평가했습니다.": [
"Not assessed because the currency/sales unit of cost and target price could not be confirmed.",
"无法确认成本与目标售价的货币·销售单位，未评估。",
"原価と希望価格の通貨・販売単位を確認できないため未評価としました。"
],
"원지표 기간이 허용 범위 밖이거나 미래 기간이어서 미평가했습니다.": [
"Not assessed because the indicator period is out of range or in the future.",
"原始指标期间超出允许范围或为未来期间，未评估。",
"原指標の期間が許容範囲外または将来のため未評価としました。"
],
"원지표의 국가·품목·분류판·기준일이 분석 조건과 다릅니다.": [
"The indicator's country, item, edition or reference date differs from the analysis conditions.",
"原始指标的国家·品目·分类版·基准日与分析条件不同。",
"原指標の国・品目・分類版・基準日が分析条件と異なります。"
],
"작성기준일이 미래이거나 작성 후 #일 적용기간이 지나 기업 계획을 미평가했습니다.": [
"The company plan was not assessed because its preparation date is in the future or the {0}-day validity has passed.",
"编制基准日为未来或已超过编制后{0}天适用期，未评估企业计划。",
"作成基準日が将来であるか作成後{0}日の適用期間を過ぎたため、企業計画を未評価としました。"
],
"제품별 계획·원가·공급 기록이 중복되거나 연결되지 않았습니다.": [
"Product plan, cost or supply records are duplicated or not linked.",
"各产品的计划·成本·供应记录重复或未关联。",
"製品別の計画・原価・供給記録が重複しているか紐づいていません。"
],
"통화가 다르지만 같은 관측일의 최근 양수 환율이 없어 원가·희망가격 비교를 미평가했습니다.": [
"Currencies differ and no recent positive FX rate on the same date exists, so the cost/target price comparison was not assessed.",
"货币不同且无同一观测日的最近正汇率，未评估成本·目标售价比较。",
"通貨が異なり同じ観測日の直近の正の為替レートがないため、原価・希望価格の比較を未評価としました。"
],
"희망수출수량이 #이므로 공급 충족률을 계산할 수 없습니다.": [
"Target export quantity is {0}, so supply coverage cannot be calculated.",
"期望出口数量为{0}，无法计算供应满足率。",
"希望輸出数量が{0}のため供給充足率を計算できません。"
],
"희망판매단가가 #이므로 원가 차감 비율을 계산할 수 없습니다.": [
"Target selling price is {0}, so the cost headroom ratio cannot be calculated.",
"期望销售单价为{0}，无法计算成本扣除比率。",
"希望販売単価が{0}のため原価控除比率を計算できません。"
],
"평가할 원지표가 없어 모든 항목에 정책 기준 #점을 적용했습니다.": [
"No raw indicators to assess, so all items use the policy midpoint of {0}.",
"没有可评估的原始指标，所有项目适用政策基准{0}分。",
"評価できる原指標がないため全項目に政策基準{0}点を適用しました。"
],
"기업의 적합성을 확인한 결과가 아닙니다.": [
"This is not a confirmation of the company's suitability.",
"并非确认企业适合性的结果。",
"企業の適合性を確認した結果ではありません。"
],
"#개 관측간격 참고값과 #거래일 완결 지표를 구분합니다.": [
"Separates the {0}-interval reference value from the complete {1}-trading-day indicator.",
"区分{0}个观测间隔参考值与{1}个交易日完整指标。",
"{0}観測間隔の参考値と{1}営業日の完結指標を区別します。"
],
"결측 보간·휴일 환율 생성·연율화는 하지 않습니다.": [
"No interpolation of gaps, holiday rate generation or annualization.",
"不进行缺失值插补·节假日汇率生成·年化。",
"欠損補間・休日レート生成・年率化は行いません。"
],
"CSL 이름 후보만 확인.": [
"Only CSL name candidates checked.",
"仅确认CSL名称候选。",
"CSL名称候補のみ確認。"
],
"미국산 함량·ECCN·FDPR·최종사용자/용도 및 거래 구조 검토 필요": [
"US content, ECCN, FDPR, end user/use and deal structure need review",
"需审查美国成分·ECCN·FDPR·最终用户/用途及交易结构",
"米国産含有率・ECCN・FDPR・最終需要者/用途と取引構造の検討が必要"
],
"Comtrade 수입 primaryValue의 CIF/FOB 평가기준은 미확인입니다.": [
"The CIF/FOB valuation basis of Comtrade import primaryValue is unconfirmed.",
"Comtrade 进口 primaryValue 的 CIF/FOB 计价基准未确认。",
"Comtrade輸入primaryValueのCIF/FOB評価基準は未確認です。"
],
"HSK는 후보 연계입니다.": [
"HSK is a candidate link.",
"HSK为候选关联。",
"HSKは候補の紐付けです。"
],
"기술사양과 현행 고시 전체 조건 확인이 필요합니다.": [
"Technical specifications and all conditions of the current notice must be checked.",
"需确认技术规格及现行公告的全部条件。",
"技術仕様と現行告示の全条件の確認が必要です。"
],
"KOTRA 보유 CSV는 참고자료입니다.": [
"The held KOTRA CSV is reference material.",
"持有的KOTRA CSV为参考资料。",
"保有KOTRA CSVは参考資料です。"
],
"현행 법령·원산지·규격·인증 적용성 확인 필요": [
"Current law, origin, standards and certification applicability need checking",
"需确认现行法令·原产地·规格·认证适用性",
"現行法令・原産地・規格・認証の適用性確認が必要"
],
"POD참조는 기업 기재 목록이며 실제 문서의 진위를 검증하지 않았습니다.": [
"POD references are company-entered lists; the authenticity of actual documents was not verified.",
"POD参照为企业填报清单，未验证实际文件真伪。",
"POD参照は企業記載のリストであり、実際の文書の真正性は検証していません。"
],
"WSTS는 전체 반도체 산업 배경이며 국가·HS# 시장 또는 점수에 합산하지 않습니다.": [
"WSTS is whole-industry background and is not added to the country/HS{0} market or the score.",
"WSTS为整个半导体行业背景，不计入国家·HS{0}市场或分数。",
"WSTSは半導体産業全体の背景であり、国・HS{0}市場や点数に合算しません。"
],
"WTO 값은 한국산 HS# 추정 참고 세율입니다.": [
"The WTO value is an estimated reference rate for Korean HS{0}.",
"WTO值为韩国产HS{0}的估计参考税率。",
"WTO値は韓国産HS{0}の推定参考税率です。"
],
"세부세번·원산지·특혜·추가조치가 검증된 실제 적용세율이 아닙니다.": [
"It is not an applied rate verified for subheading, origin, preferences and additional measures.",
"并非经细分税号·原产地·优惠·附加措施核实的实际适用税率。",
"細分税番・原産地・特恵・追加措置が検証された実際の適用税率ではありません。"
],
"건수는 제출 목록 및 기재 상태 개수이며 인증 보유율이나 규제 충족률이 아닙니다.": [
"Counts are the number of submitted list entries and statuses, not a certification holding rate or regulatory compliance rate.",
"件数为提交清单及填报状态的数量，并非认证持有率或监管合规率。",
"件数は提出リストと記載状態の数であり、認証保有率や規制充足率ではありません。"
],
"계열별 공표 달력은 미확인입니다.": [
"Publication calendars per series are unconfirmed.",
"各序列公布日历未确认。",
"系列別の公表カレンダーは未確認です。"
],
"#개 값 확보만으로 연속 #거래일이라고 표시하지 않습니다.": [
"Having {0} values alone is not shown as {1} consecutive trading days.",
"仅获得{0}个值并不表示连续{1}个交易日。",
"{0}個の値の確保だけで連続{1}営業日とは表示しません。"
],
"고정 비교군·공통기간의 원관측으로 산출한 상대 참고지수입니다.": [
"Relative reference index calculated from raw observations of a fixed peer group over a common period.",
"基于固定比较组·公共期间原始观测计算的相对参考指数。",
"固定比較群・共通期間の原観測から算出した相対参考指数です。"
],
"공통 #개월 중 #개월이 누락·오류·중복입니다.": [
"{1} of the common {0} months are missing, erroneous or duplicated.",
"公共{0}个月中有{1}个月缺失·错误·重复。",
"共通{0}か月のうち{1}か月が欠損・誤り・重複です。"
],
"공통 안정성 평가 종료월 #-#, 최근 완료월 대비 #개월 지연.": [
"Common stability window ends {0}-{1}, {2} month(s) behind the latest completed month.",
"公共稳定性评估截止月 {0}-{1}，比最近完成月晚{2}个月。",
"共通の安定性評価終了月 {0}-{1}、直近完了月から{2}か月遅れ。"
],
"선택국은 이 공통기간의 비교 자료요건 미충족.": [
"The selected country does not meet the comparison data requirement for this common period.",
"所选国家未满足该公共期间的比较资料要求。",
"選択国はこの共通期間の比較資料要件を満たしていません。"
],
"선택국의 비교 자료요건 충족.": [
"The selected country meets the comparison data requirement.",
"所选国家满足比较资料要求。",
"選択国は比較資料要件を満たしています。"
],
"관련제품만 확인한 문서는 해당 목적국 또는 특정 거래의 적용 증빙으로 해석할 수 없습니다.": [
"Documents confirmed only for related products cannot be read as evidence for this destination or a specific deal.",
"仅确认相关产品的文件不能解读为该目的国或特定交易的适用证明。",
"関連製品のみ確認した文書は、当該輸出先や特定取引の適用証憑として解釈できません。"
],
"관세 파일의 imports는 가중치용 참고금액입니다.": [
"Imports in the tariff file are reference amounts for weighting.",
"关税文件中的 imports 为加权用参考金额。",
"関税ファイルのimportsは加重用の参考金額です。"
],
"조치일의 시장규모나 성장률로 사용하지 않습니다.": [
"They are not used as market size or growth on the measure date.",
"不作为措施日的市场规模或增长率使用。",
"措置日の市場規模や成長率として使用しません。"
],
"관세는 분석 기준일의 파일 내 참고치입니다.": [
"The tariff is a reference value in the file as of the analysis date.",
"关税为分析基准日文件中的参考值。",
"関税は分析基準日時点のファイル内参考値です。"
],
"예정거래의 미래 적용세율을 확정하지 않습니다.": [
"It does not fix the future applied rate for planned deals.",
"并不确定计划交易的未来适用税率。",
"予定取引の将来の適用税率を確定しません。"
],
"급감 빈도 분모는 #쌍 중 #쌍입니다.": [
"The sharp-drop denominator is {1} of {0} pairs.",
"骤降频率分母为{0}对中的{1}对。",
"急減頻度の分母は{0}ペア中{1}ペアです。"
],
"# 기준값 또는 결측을 건너뛰어 연결하지 않습니다.": [
"Base values of {0} or gaps are not skipped over to link months.",
"不跳过{0}基准值或缺失进行连接。",
"{0}の基準値や欠損を飛ばして連結しません。"
],
"공통 비교 자료요건 또는 최소 #개국 요건 미충족.": [
"Common comparison data requirement or minimum {0}-country requirement not met.",
"未满足公共比较资料要求或至少{0}国要求。",
"共通比較資料要件または最低{0}か国要件を満たしていません。"
],
"관측값은 개별 참고이며 점수는 보류합니다.": [
"Observations are individual references and the score is on hold.",
"观测值仅为个别参考，分数暂缓。",
"観測値は個別の参考であり、点数は保留します。"
],
"비교 자료요건 충족; 원지표와 상대 참고지수의 근거를 별도로 표시합니다.": [
"Comparison data requirement met; the basis of raw indicators and the relative reference index is shown separately.",
"满足比较资料要求；原始指标与相对参考指数的依据分别显示。",
"比較資料要件を充足；原指標と相対参考指数の根拠を別途表示します。"
],
"기업 거래 및 간편양식 제품원가에 기재된 통화만 확인합니다.": [
"Only currencies recorded in company deals and simple-form product costs are checked.",
"仅确认企业交易及简易表格产品成本中填报的货币。",
"企業取引と簡易様式の製品原価に記載された通貨のみ確認します。"
],
"목적국 통화로 추정하지 않으며 실제 순노출·헤지·손익을 판정하지 않습니다.": [
"It does not assume the destination currency or judge actual net exposure, hedging or P&L.",
"不推定为目的国货币，也不判定实际净敞口·对冲·损益。",
"輸出先通貨と推定せず、実際の純エクスポージャー・ヘッジ・損益を判定しません。"
],
"기준일 이전 기간을 현재 조회한 수정 통계입니다.": [
"Revised statistics for periods before the reference date, retrieved now.",
"对基准日之前期间当前查询的修订统计。",
"基準日以前の期間を現在照会した修正統計です。"
],
"당시 공표 자료만 사용한 역사적 재현은 아닙니다.": [
"It is not a historical reproduction using only data published at the time.",
"并非仅使用当时公布资料的历史重现。",
"当時公表の資料のみを用いた歴史的再現ではありません。"
],
"누락·실패는 #이 아닙니다.": [
"Missing or failed values are not {0}.",
"缺失·失败不等于{0}。",
"欠損・失敗は{0}ではありません。"
],
"국가별 원지표는 별도 승인된 상대 비교 산식의 입력이며 성공확률이 아닙니다.": [
"Raw country indicators are inputs to a separately approved relative comparison formula, not success probabilities.",
"各国原始指标为另行批准的相对比较公式的输入，并非成功概率。",
"国別原指標は別途承認された相対比較算式の入力であり、成功確率ではありません。"
],
"데이터셋 등록·공표 이력은 해당 HS# 수입 관측이 아닙니다.": [
"Dataset registration/publication history is not an HS{0} import observation.",
"数据集登记·公布记录并非该HS{0}进口观测。",
"データセットの登録・公表履歴は当該HS{0}の輸入観測ではありません。"
],
"결측을 무역 #·미공표·비밀처리로 판정하지 않습니다.": [
"Gaps are not judged as trade of {0}, unpublished or confidential.",
"不将缺失判定为贸易为{0}·未公布·保密处理。",
"欠損を貿易{0}・未公表・秘匿処理と判定しません。"
],
"현재 조회 결과이며 기준일 당시의 제공 상태를 재현하지 않습니다.": [
"This is the current query result and does not reproduce availability as of the reference date.",
"为当前查询结果，不重现基准日当时的提供状态。",
"現在の照会結果であり、基準日当時の提供状態を再現しません。"
],
"문서번호가 기재되지 않았습니다.": [
"No document number recorded.",
"未填写文件编号。",
"文書番号が記載されていません。"
],
"발행일이 기재되지 않았습니다.": [
"No issue date recorded.",
"未填写发行日期。",
"発行日が記載されていません。"
],
"날짜·무기한 유효를 추정하지 않습니다.": [
"Dates or indefinite validity are not assumed.",
"不推定日期·无限期有效。",
"日付・無期限の有効性を推定しません。"
],
"만료일이 기재되지 않았습니다.": [
"No expiry date recorded.",
"未填写到期日。",
"有効期限が記載されていません。"
],
"제품 범위 참고입니다.": [
"Product-scope reference.",
"为产品范围参考。",
"製品範囲の参考です。"
],
"목적국·거래별 적용 여부는 확인하지 않았습니다.": [
"Applicability per destination/deal was not checked.",
"未确认按目的国·交易的适用情况。",
"輸出先・取引別の適用可否は確認していません。"
],
"보유 일부개정안·행정예고를 시행 중인 최종 법령으로 취급하지 않습니다.": [
"Held partial amendments and administrative notices are not treated as final laws in force.",
"不将持有的部分修正案·行政预告视为施行中的最终法令。",
"保有する一部改正案・行政予告を施行中の最終法令として扱いません。"
],
"보유 항공 운송비 통계는 수입 방향이므로 항공 수출 견적으로 사용하지 않았습니다.": [
"Held air freight statistics are for imports, so they were not used as air export quotes.",
"持有的航空运费统计为进口方向，因此未用作航空出口报价。",
"保有する航空運送費統計は輸入方向のため、航空輸出の見積として使用していません。"
],
"선택 거래 #건 중 #건은 식별·시각·POD참조 요건을 충족하지 못했습니다.": [
"{1} of {0} selected deal(s) did not meet the identification, time and POD reference requirements.",
"所选交易{0}件中有{1}件未满足识别·时间·POD参照要求。",
"選択取引{0}件中{1}件は識別・時刻・POD参照の要件を満たしていません。"
],
"사유를 거래별로 보존했습니다.": [
"Reasons are kept per deal.",
"已按交易保留原因。",
"理由を取引別に保存しました。"
],
"선택 목적국 KOTRA 자료 중 #개 레코드에 누락·복합/과학표기 HS가 있어 해당 셀의 자동 비교를 보류했습니다.": [
"{0} records in the selected destination's KOTRA data have missing, compound or scientific-notation HS codes, so automatic comparison of those cells was put on hold.",
"所选目的国KOTRA资料中有{0}条记录的HS缺失·复合/科学计数，已暂缓对这些单元格的自动比较。",
"選択輸出先のKOTRA資料のうち{0}件のレコードでHSが欠損・複合/指数表記のため、該当セルの自動比較を保留しました。"
],
"수입은 목적국의 대세계 통계, 한국 수출은 한국 신고 FOB 통계입니다.": [
"Imports are the destination's world statistics; Korea's exports are Korean declared FOB statistics.",
"进口为目的国全球统计，韩国出口为韩国申报FOB统计。",
"輸入は輸出先の対世界統計、韓国輸出は韓国申告のFOB統計です。"
],
"둘을 나눠 점유율을 만들지 않습니다.": [
"The two are not divided to create a market share.",
"不将两者相除计算份额。",
"両者を割ってシェアを作りません。"
],
"시각마다 명시적 UTC offset을 사용합니다.": [
"Each time uses an explicit UTC offset.",
"每个时间都使用明确的UTC偏移。",
"各時刻に明示的なUTCオフセットを使用します。"
],
"IANA 이름과 공통 시간대의 자동 추정은 지원하지 않습니다.": [
"Automatic inference of IANA names and common time zones is not supported.",
"不支持IANA名称和通用时区的自动推断。",
"IANA名と共通タイムゾーンの自動推定には対応していません。"
],
"실제 결제통화가 확인되지 않았습니다.": [
"The actual settlement currency was not confirmed.",
"未确认实际结算货币。",
"実際の決済通貨が確認されていません。"
],
"연속 #개월·양수 평균·#개 인접 월 비교를 확인했습니다.": [
"Confirmed {0} consecutive months, a positive mean and {1} adjacent-month comparisons.",
"已确认连续{0}个月·正平均值·{1}个相邻月份比较。",
"連続{0}か月・正の平均・{1}個の隣接月比較を確認しました。"
],
"원값·비교기간·결측을 표시하며 성공확률이나 임의 점수로 변환하지 않습니다.": [
"Shows raw values, comparison periods and gaps; not converted to success probabilities or arbitrary scores.",
"显示原值·比较期间·缺失，不转换为成功概率或任意分数。",
"原値・比較期間・欠損を表示し、成功確率や任意の点数に変換しません。"
],
"이번 조회의 등록 목록·공표 이력에서 같은 국가·월·HS# 데이터셋을 찾지 못했습니다.": [
"No dataset for the same country, month and HS{0} was found in this query's registry/publication history.",
"在本次查询的登记清单·公布记录中未找到同一国家·月份·HS{0}的数据集。",
"今回の照会の登録リスト・公表履歴に、同じ国・月・HS{0}のデータセットが見つかりませんでした。"
],
"일부 수입 관측의 CIF/FOB 평가기준을 확인하지 못했습니다.": [
"The CIF/FOB valuation basis of some import observations could not be confirmed.",
"未能确认部分进口观测的CIF/FOB计价基准。",
"一部の輸入観測のCIF/FOB評価基準を確認できませんでした。"
],
"원기관 신고액의 상대 참고값입니다.": [
"Relative reference value of amounts reported by the source agency.",
"为原机构申报额的相对参考值。",
"原機関の申告額の相対参考値です。"
],
"전 목적지 수출은 별도 Itemtrade 서비스입니다.": [
"All-destination exports come from a separate Itemtrade service.",
"全部目的地出口为单独的Itemtrade服务。",
"全輸出先向け輸出は別のItemtradeサービスです。"
],
"#개 후보국의 합계가 아닙니다.": [
"It is not the sum of the {0} candidate countries.",
"并非{0}个候选国的合计。",
"{0}候補国の合計ではありません。"
],
"제출 목록의 기재 상태만 확인합니다.": [
"Only the entry status of the submitted list is checked.",
"仅确认提交清单的填报状态。",
"提出リストの記載状態のみ確認します。"
],
"문서 진위·첨부 실체·법적 적용·인증 보유·수출 허용을 판정하지 않습니다.": [
"Document authenticity, attachments, legal applicability, certification or export permission are not judged.",
"不判定文件真伪·附件实体·法律适用·认证持有·出口许可。",
"文書の真正性・添付の実体・法的適用・認証保有・輸出許可を判定しません。"
],
"조회 시점의 현행 판본입니다.": [
"Current edition at query time.",
"为查询时的现行版本。",
"照会時点の現行版です。"
],
"과거 기준일 당시의 법령·공표 상태를 재현한 자료가 아닙니다.": [
"It does not reproduce laws or publication status as of past reference dates.",
"并非重现过去基准日当时法令·公布状态的资料。",
"過去の基準日当時の法令・公表状態を再現した資料ではありません。"
],
"증빙목록 시트가 확인되지 않았습니다.": [
"The evidence-list sheet was not found.",
"未找到证明清单工作表。",
"証憑リストのシートが確認されませんでした。"
],
"문서·인증을 보유하지 않았다는 뜻이 아닙니다.": [
"This does not mean documents or certifications are not held.",
"并不表示未持有文件·认证。",
"文書・認証を保有していないという意味ではありません。"
],
"첨부참조는 기업이 적은 문자열입니다.": [
"Attachment references are strings entered by the company.",
"附件参照为企业填写的字符串。",
"添付参照は企業が記入した文字列です。"
],
"파일·URL을 열거나 다운로드하지 않았습니다.": [
"Files or URLs were not opened or downloaded.",
"未打开或下载文件·URL。",
"ファイル・URLを開いたりダウンロードしたりしていません。"
],
"최근 완료월 대비 #개월 이내의 월별 관측을 확인하지 못했습니다.": [
"No monthly observation within {0} months of the latest completed month was confirmed.",
"未能确认距最近完成月{0}个月以内的月度观测。",
"直近完了月から{0}か月以内の月次観測を確認できませんでした。"
],
"통계 USD/kg 단가는 제품구성과 규격의 영향을 받습니다.": [
"Statistical USD/kg unit values are affected by product mix and specifications.",
"统计 USD/kg 单价受产品构成与规格影响。",
"統計のUSD/kg単価は製品構成と規格の影響を受けます。"
],
"기업의 개당 견적·마진·경쟁력을 뜻하지 않습니다.": [
"They do not indicate the company's per-unit quote, margin or competitiveness.",
"并不代表企业的单件报价·利润·竞争力。",
"企業の1個あたり見積・マージン・競争力を意味しません。"
],
"통제번호 후보·수입규제·거래 상대 이름 확인이 필요합니다.": [
"Control-number candidates, import restrictions and counterparty names need review.",
"需要核查管制编号候选·进口限制·交易对象名称。",
"統制番号候補・輸入規制・取引相手名の確認が必要です。"
],
"규제는 점수에 더하지 않는 별도 관문입니다.": [
"Regulation is a separate gate and is not added to the score.",
"监管是不计入分数的单独关口。",
"規制は点数に加えない別のゲートです。"
],
"판매자·바이어 부담 및 청구가격·원가 포함 여부가 미확인된 비용은 #으로 처리하지 않습니다.": [
"Costs whose seller/buyer burden or inclusion in invoice price/cost is unconfirmed are not treated as {0}.",
"卖方·买方负担及是否计入发票价格·成本未确认的费用不按{0}处理。",
"売手・買手負担や請求価格・原価への算入有無が未確認の費用は{0}として扱いません。"
],
"판본 일치·본문·별표 메타데이터를 확인했습니다.": [
"Edition match, body text and annex metadata were checked.",
"已确认版本一致·正文·附表元数据。",
"版の一致・本文・別表のメタデータを確認しました。"
],
"현행 고시 원문 확보는 개별 제품·모델의 통제 해당 여부나 수출허가를 뜻하지 않습니다.": [
"Having the current notice text does not mean an individual product/model is controlled or licensed for export.",
"获取现行公告原文并不表示个别产品·型号是否受管制或获得出口许可。",
"現行告示原文の確保は個別製品・モデルの統制該当や輸出許可を意味しません。"
],
"기술사양·최종용도·거래처·목적국·허가 증빙을 별도로 검토해야 합니다.": [
"Technical specifications, end use, counterparties, destination and license evidence must be reviewed separately.",
"需另行审查技术规格·最终用途·交易方·目的国·许可证明。",
"技術仕様・最終用途・取引先・輸出先・許可証憑を別途検討する必要があります。"
],
"표시 기간 #-#~#-#의 #개월 중 #개월이 누락/오류/중복되어 #개월 CV를 보류했습니다.": [
"{5} of {4} months in the shown period {0}-{1}~{2}-{3} are missing/erroneous/duplicated, so the {6}-month CV is on hold.",
"显示期间{0}-{1}~{2}-{3}的{4}个月中有{5}个月缺失/错误/重复，暂缓{6}个月CV。",
"表示期間{0}-{1}〜{2}-{3}の{4}か月中{5}か月が欠損/誤り/重複のため、{6}か月CVを保留しました。"
],
"조건부 검토 유망": [
"Promising, subject to review",
"有条件审查·前景良好",
"条件付き検討・有望"
],
"조건부 검토": [
"Conditional review",
"有条件审查",
"条件付き検討"
],
"준비 보완 필요": [
"Preparation needed",
"需补充准备",
"準備の補完が必要"
],
"판단 근거 부족": [
"Insufficient evidence",
"判断依据不足",
"判断根拠不足"
],
"규제상 진행 제한": [
"Restricted by regulation",
"受监管限制",
"規制上の進行制限"
],
"규제 요건 확인 필요": [
"Regulatory requirements to confirm",
"需确认监管要件",
"規制要件の確認が必要"
],
"관측": [
"Observed",
"观测",
"観測"
],
"관측(#)": [
"Observed (0)",
"观测（0）",
"観測（0）"
],
"기업 기재": [
"Company entry",
"企业填报",
"企業記載"
],
"정책 기준 #점": [
"Policy midpoint {0}",
"政策基准{0}分",
"政策基準{0}点"
],
"보류": [
"On hold",
"暂缓",
"保留"
],
"판정 보류": [
"Verdict on hold",
"暂缓判定",
"判定保留"
],
"대세계 수입액 (USD M)": [
"World imports (USD M)",
"全球进口额（USD M）",
"対世界輸入額（USD M）"
],
"원/달러": [
"KRW/USD",
"韩元/美元",
"ウォン/ドル"
],
"성장률 %": [
"Growth %",
"增长率 %",
"成長率 %"
],
"전월 대비 %": [
"MoM %",
"环比 %",
"前月比 %"
],
"후보 수": [
"Candidates",
"候选数",
"候補数"
],
"항목 점수 (#~#)": [
"Item score ({0}–{1})",
"项目分数（{0}~{1}）",
"項目点数（{0}〜{1}）"
],
"미국동부": [
"US East Coast",
"美国东部",
"米国東部"
],
"미국서부": [
"US West Coast",
"美国西部",
"米国西部"
],
"유럽연합": [
"European Union",
"欧盟",
"欧州連合"
],
"유럽연합(EU)": [
"European Union (EU)",
"欧盟（EU）",
"欧州連合（EU）"
],
"메일이 보이지 않으면 스팸함(정크 메일함)도 확인해 주세요. 도착까지 몇 분 걸릴 수 있습니다.": [
"If you can't find the email, please check your spam (junk) folder. It may take a few minutes to arrive.",
"如果没有看到邮件，请同时检查垃圾邮件箱。邮件可能需要几分钟才能送达。",
"メールが見当たらない場合は、迷惑メールフォルダもご確認ください。届くまで数分かかることがあります。"
],
"인증 메일이 오지 않으면 스팸함(정크 메일함)도 확인해 주세요.": [
"If the verification email doesn't arrive, please check your spam (junk) folder.",
"如果没有收到验证邮件，请同时检查垃圾邮件箱。",
"認証メールが届かない場合は、迷惑メールフォルダもご確認ください。"
]
};
  const REGION = {"미국동부": ["US East Coast", "美国东部", "米国東部"], "미국서부": ["US West Coast", "美国西部", "米国西部"], "베트남": ["Vietnam", "越南", "ベトナム"], "일본": ["Japan", "日本", "日本"], "중국": ["China", "中国", "中国"], "유럽연합": ["European Union", "欧盟", "欧州連合"], "유럽연합(EU)": ["European Union (EU)", "欧盟（EU）", "欧州連合（EU）"], "EU": ["EU", "EU", "EU"]};
  const LANGS = ["en", "zh", "ja"];
  const NUM = /\d+(?:[.,]\d+)*/g;
  const FILE = /\.(xlsx|xls|hwpx|hwp|csv|pdf|json)$/i;
  const fill = (tpl, ns) => tpl.replace(/\{(\d+)\}/g, (_, i) => (ns[+i] != null ? ns[+i] : ""));
  function one(s, ix) {
    const t = String(s).trim();
    if (!t) return t;
    const v = D[t.replace(NUM, "#")];
    return v ? fill(v[ix], t.match(NUM) || []) : null;
  }
  // 형태 규칙: [정규식, (일치, 언어 번호) => 번역문]
  const PAT = [
    [/^\((.+) 외\)$/, (m, ix) => [`(${m[1]}, etc.)`, `（${m[1]} 等）`, `（${m[1]} ほか）`][ix]],
    [/^(.+) 외 (\d+)$/, (m, ix) => [`${m[1]} and ${m[2]} more`, `${m[1]} 等另${m[2]}项`, `${m[1]} ほか${m[2]}件`][ix]],
    [/^HS(\d+) (\d+) \/ ([A-Z]{2})의 물류 (\d+)건 연결$/, (m, ix) => [`HS${m[1]} ${m[2]} / ${m[3]}: ${m[4]} logistics record(s) linked`, `HS${m[1]} ${m[2]} / ${m[3]} 的物流关联 ${m[4]} 件`, `HS${m[1]} ${m[2]} / ${m[3]} の物流連結 ${m[4]}件`][ix]],
    [/^공통창 (.+)$/, (m, ix) => [`Common window ${m[1]}`, `公共窗口 ${m[1]}`, `共通ウィンドウ ${m[1]}`][ix]],
    [/^기간정책 (.+)$/, (m, ix) => [`Period policy ${m[1]}`, `期间政策 ${m[1]}`, `期間ポリシー ${m[1]}`][ix]],
    [/^점수 대신 관문으로 봅니다 \(([A-Z_]+)\)\.?$/, (m, ix) => [`Treated as a gate, not a score (${m[1]}).`, `作为关口而非分数处理（${m[1]}）。`, `点数ではなくゲートとして扱います（${m[1]}）。`][ix]],
  ];
  const PTS = [" pts", "分", "点"];
  function tx(s, lang) {
    const ix = LANGS.indexOf(lang);
    if (ix < 0 || s == null || !/[가-힣]/.test(String(s))) return s;
    const src = String(s).trim(), direct = one(src, ix);
    if (direct != null) return direct;
    let m;
    for (const [re, f] of PAT) { m = src.match(re); if (m) return f(m, ix); }
    m = src.match(/^\[엔진 상태 ([A-Z_]+)\]\s*([\s\S]*)$/);
    if (m) return ["[Engine status ", "[引擎状态 ", "[エンジン状態 "][ix] + m[1] + "] " + (m[2] ? tx(m[2], lang) : "");
    m = src.match(/^필요 자료: ([\s\S]+)$/);
    if (m) return ["Required: ", "所需资料：", "必要資料："][ix] + tx(m[1], lang);
    m = src.match(/^자료 부족 \(근거 반영률 (\d+)%\): (.+)$/);
    if (m) return [`Insufficient data (evidence ${m[1]}%): `, `资料不足（依据反映率${m[1]}%）：`, `資料不足（根拠反映率${m[1]}%）：`][ix] + m[2].split("·").map((x) => tx(x, lang)).join(ix ? "·" : ", ");
    const sentences = src.split(/(?<=[.。])\s+/);
    if (sentences.length > 1) return sentences.map((x) => tx(x, lang)).join(ix ? "" : " "); // 중국어·일본어는 문장 사이 공백 없이
    m = src.match(/^(.+?): ([\d.]+)점 — ([\s\S]+)$/);
    if (m) return tx(m[1], lang) + (ix ? "：" : ": ") + m[2] + PTS[ix] + " — " + tx(m[3], lang);
    if (src.includes(" · ")) return src.split(" · ").map((p) => (FILE.test(p.trim()) ? p : tx(p, lang))).join(" · ");
    m = src.match(/^(.+?) 해상 수출 비용 참고$/);
    if (m && REGION[m[1]]) return [`${REGION[m[1]][0]} sea-export freight reference`, `${REGION[m[1]][1]}海运出口运费参考`, `${REGION[m[1]][2]} 海上輸出費用の参考`][ix];
    m = src.match(/^(.+) 예정거래 견적 단가$/);
    if (m) { const p = m[1].replace("(가상 사양)", ["(fictional spec)", "（虚构规格）", "（架空仕様）"][ix]); return [`${p} planned-deal quoted unit price`, `${p} 计划交易报价单价`, `${p} 予定取引の見積単価`][ix]; }
    if (src.includes(" / ") && !/[.。]$/.test(src)) { const parts = src.split(" / "); if (parts.length > 1 && parts.every((p) => one(p, ix) != null)) return parts.map((p) => one(p, ix)).join(" / "); }
    m = src.match(/^(.+) (\d+(?:\.\d+)?)점\((.+)\)$/); // 항목 50점(정책 기준 50점)
    if (m && one(m[1], ix) != null) return `${one(m[1], ix)} ${m[2]}${PTS[ix]} (${tx(m[3], lang)})`;
    m = src.match(/^(-?[\d.,]+) (\D[\s\S]*)$/); // 값 + 단위
    if (m) { const u = tx(m[2], lang); if (u !== m[2]) return m[1] + " " + u; }
    m = src.match(/^([^:：]{2,40}): ([\s\S]+)$/);
    if (m && one(m[1], ix) != null) return one(m[1], ix) + (ix ? "：" : ": ") + tx(m[2], lang);
    return src;
  }
  // 화면 번역기(AXPI18n)가 이 표를 쓰도록 연결된 뒤 늦게 로드되므로, 한국어가 아니면 한 번 더 번역한다
  try { if (window.AXPI18n && AXPI18n.language !== "ko" && typeof AXPI18n.translateDOM === "function") AXPI18n.translateDOM(); } catch (e) {}
  window.JunheeReportI18n = Object.freeze({ tx, has: (s) => one(s, 0) != null });
})();
