/* v0.7: Report localization shared by PDF preview, downloadable HTML and report dialog.
   Original public-data filenames and company names are retained as provenance. */
(() => {
  'use strict';
  const languages = ['ko','en','zh','ja'];
  const dictionary = {
    '수출 분석 보고서':['Export analysis report','出口分析报告','輸出分析レポート'],
    '수출 의사결정':['Export decision support','出口决策支持','輸出意思決定支援'],
    '분석 보고서':['Analysis report','分析报告','分析レポート'],
    '기업 분석기간':['Company analysis period','企业分析期间','企業分析期間'],
    '공개 통계 시점':['Public statistics as of','公开统计截至日期','公開統計の基準日'],
    '공개 통계 기준':['Public statistics as of','公开统计截至','公開統計の基準日'],
    '작성일':['Generated on','生成日期','作成日'],
    '정량 참고점수':['Indicative quantitative score','定量参考分数','定量参考スコア'],
    '시장 진입 여건':['Market-entry conditions','市场准入条件','市場参入条件'],
    '현재 확보된 영역별 점수 제공':['Available domain scores only','仅提供可用维度的分数','取得済み分野のスコアのみ表示'],
    '수출 실행 요건':['Export execution requirements','出口执行要求','輸出実行要件'],
    '전략물자 확인 필요':['Strategic-item review required','需核查战略物资','戦略物資の確認が必要'],
    '규제 상태':['Regulatory review status','监管核查状态','規制確認状況'],
    '규제 확인':['Regulatory screening','监管筛查','規制確認'],
    '점수에 사용한 데이터 구성':['Composition of scoring evidence','评分数据构成','採点データの構成'],
    '평가 영역':['Scored scope','评分范围','評価範囲'],
    '설정 가중치 합계':['Total configured weights','设定权重合计','設定ウェイト合計'],
    '회사 운영 실적 등':['Company operational data etc.','企业运营数据等','企業の運営実績など'],
    '관세·환율 대리지표':['Tariff/FX proxy indicators','关税及汇率替代指标','関税・為替の代替指標'],
    '과거 목적국 통계':['Historical destination statistics','目的国历史统计','輸出先の過去統計'],
    '근거':['Evidence','依据','根拠'],
    '출처':['Source','来源','出典'],
    '근거 미확보':['Insufficient evidence','缺少依据','根拠未取得'],
    '확보된 핵심 근거':['Key available evidence','现有关键依据','取得済みの主な根拠'],
    '사업성 지표와 규제 검토는 서로 독립적으로 해석':['Commercial indicators and regulatory checks must be interpreted independently','商业指标与监管审核应分别解读','事業性指標と規制確認は別々に解釈'],
    '목적국 시장성':['Destination market potential','目的国市场潜力','輸出先の市場性'],
    '시장성':['Market potential','市场潜力','市場性'],
    '과거 통계':['Historical statistics','历史统计','過去統計'],
    '가격 대리지표':['Pricing proxies','价格替代指标','価格の代替指標'],
    '가격 여건 / 수익성 별도':['Pricing conditions / profitability separate','价格条件／盈利能力另算','価格条件／収益性は別途'],
    '가격 여건':['Pricing conditions','价格条件','価格条件'],
    '가격 여건 (관세·환율)':['Pricing conditions (tariff/FX)','价格条件（关税／汇率）','価格条件（関税・為替）'],
    '물류 운영':['Logistics operations','物流运营','物流運営'],
    '거래 안정성':['Trading stability','交易稳定性','取引安定性'],
    '우선 확인할 사항':['Priority follow-up actions','优先核查事项','優先確認事項'],
    '분석 범위 및 평가 방법':['Analysis scope and methodology','分析范围与评估方法','分析範囲と評価方法'],
    '대상 국가 / 선택 HS':['Destination / selected HS','目的国／所选 HS','対象国／選択 HS'],
    '지표 수집 상태':['Indicator availability','指标数据收集情况','指標の取得状況'],
    '평가 기준':['Scoring criteria','评估标准','評価基準'],
    '평가 결과와 제외 사유':['Results and reasons for exclusion','评估结果与排除原因','評価結果と除外理由'],
    '영역':['Domain','维度','分野'],
    '결과':['Result','结果','結果'],
    '가중치':['Weight','权重','ウェイト'],
    '주요 근거 · 한계':['Evidence and limitations','主要依据及局限','主な根拠と限界'],
    '관문 / 비점수':['Gate / not scored','前置审核／不计分','ゲート／採点対象外'],
    '부분 분석':['Partial analysis','部分分析','部分分析'],
    '자료 부족':['Insufficient data','数据不足','データ不足'],
    '미확인':['Unverified','未核实','未確認'],
    '확인됨':['Available','已核实','確認済み'],
    '검색 결과 없음':['No match found','未找到匹配项','一致結果なし'],
    '검색 불가':['Search unavailable','无法检索','検索不可'],
    '점수 제외':['Not scored','不计分','採点対象外'],
    '품목 및 원본 데이터':['Products and source data','产品与原始数据','品目と原データ'],
    '선택 품목':['Selected product','所选产品','選択品目'],
    '기업 전체 등록 HS6':['All registered company HS6','企业登记的全部 HS6','企業の登録済み HS6'],
    '원본 파일':['Source file','原始文件','元ファイル'],
    '유효 행':['Valid rows','有效行','有効行'],
    '규제 검토 및 시장 분석':['Regulatory review and market analysis','监管核查与市场分析','規制確認と市場分析'],
    '통제번호 후보':['Possible control classification','可能的管制编码','規制番号候補'],
    '수입규제 검색':['Import-restriction search','进口限制查询','輸入規制の検索'],
    '제한 명단 검색':['Restricted-party screening','受限方名单筛查','制限対象リスト検索'],
    '목적국 수입시장 (선택 HS 기준)':['Destination imports (selected HS)','目的国进口市场（所选 HS）','輸出先の輸入市場（選択 HS）'],
    '지표':['Indicator','指标','指標'],
    '확인값':['Observed value','确认值','確認値'],
    '기간 및 범위':['Period and scope','期间与范围','期間と範囲'],
    '선택 HS 최근 12개월 수입액':['Selected HS imports, latest 12 months','所选 HS 最近12个月进口额','選択 HS の直近12か月輸入額'],
    '선택 HS 수입시장 전년 대비':['Selected HS import market, YoY','所选 HS 进口市场同比','選択 HS 輸入市場の前年比'],
    '시장성 참고점수':['Indicative market score','市场潜力参考分数','市場性参考スコア'],
    '공개자료 원본(품목 묶음)':['Original public data (combined products)','公开原始数据（产品组合）','公開原データ（品目合計）'],
    '관세·수익성·물류·거래 안정성':['Tariffs, profitability, logistics and trading stability','关税、盈利能力、物流及交易稳定性','関税・収益性・物流・取引安定性'],
    '가격 여건 점수':['Pricing-conditions score','价格条件分数','価格条件スコア'],
    '관세 참고':['Reference tariff','参考关税','参考関税'],
    '원자료 확인':['Source data available','原始数据已确认','原データ確認済み'],
    '전체 분석기간 납기 준수율':['On-time delivery, full period','全期间准时交付率','全分析期間の納期遵守率'],
    '전체 분석기간 수출액 변동계수':['Export-value CV, full period','全期间出口额变异系数','全期間の輸出額変動係数'],
    '평가 상태':['Assessment status','评估状态','評価状況'],
    '해석 및 기준':['Interpretation and basis','解读与依据','解釈と基準'],
    '관세·환율 여건':['Tariff and FX conditions','关税与汇率条件','関税・為替条件'],
    '가정 수익성·손익분기 원가 계산 (추가 입력 최소화)':['Profitability scenario and break-even cost (minimal input)','盈利情景与盈亏平衡成本（最少输入）','収益性シナリオと損益分岐原価（最小限の入力）'],
    '예상 판매단가 (USD/개)':['Expected selling price (USD/unit)','预计销售单价（美元/件）','想定販売単価（USD/個）'],
    '제품 단위원가 (USD/개, 선택)':['Unit product cost (USD/unit, optional)','单位产品成本（美元/件，可选）','製品単位原価（USD/個、任意）'],
    '기타 수출 부대비용 (USD/개)':['Other export expenses (USD/unit)','其他出口费用（美元/件）','その他輸出付帯費用（USD/個）'],
    '관세 시나리오 (%)':['Assumed tariff (%)','假设关税（%）','想定関税（%）'],
    '가정 수익성 계산':['Calculate scenario','计算情景盈利','シナリオ収益性を計算'],
    '추가 확인 항목':['Further checks','其他核查事项','追加確認事項'],
    '부록 · 전체 상세 지표와 산출 근거':['Appendix · Full indicators and calculations','附录：全部指标及计算依据','付録・全指標と算出根拠'],
    '항목 / 상태':['Indicator / status','指标／状态','項目／状態'],
    '표시값':['Displayed value','显示值','表示値'],
    '기간 / 기준일':['Period / as-of date','期间／基准日','期間／基準日'],
    '출처 / 계산 근거':['Source / calculation','来源／计算依据','出典／計算根拠'],
    '원본 파일의 결측·오류':['Missing or invalid source data','原始数据缺失或错误','原データの欠損・誤り'],
    '시트 / 열':['Sheet / column','工作表／列','シート／列'],
    '유형':['Type','类型','種類'],
    '건수':['Count','数量','件数'],
    '계산 영향':['Effect on calculation','对计算的影响','計算への影響'],
    '데이터와 방법론':['Data and methodology','数据与方法','データと算出方法'],
    '수익성 시나리오 (선택)':['Profitability scenario (optional)','盈利情景（可选）','収益性シナリオ（任意）'],
    '판매단가 (USD/개)':['Selling price (USD/unit)','销售单价（美元/件）','販売単価（USD/個）'],
    '원가 (선택)':['Cost (optional)','成本（可选）','原価（任意）'],
    '부대비용 (USD/개)':['Additional expenses (USD/unit)','附加费用（美元/件）','付帯費用（USD/個）'],
    '관세 가정 (%)':['Assumed tariff (%)','假设关税（%）','想定関税（%）'],
    '시나리오를 보고서에 반영':['Apply scenario to report','将情景应用于报告','シナリオをレポートに反映'],
    'HTML 다운로드':['Download HTML','下载 HTML','HTML をダウンロード'],
    '인쇄 창 열기 (PDF 저장 가능)':['Open print dialog (Save as PDF)','打开打印窗口（可保存为PDF）','印刷画面を開く（PDF保存可）'],
    '수출 의사결정 분석 보고서 미리보기':['Export analysis report preview','出口决策分析报告预览','輸出意思決定分析レポートのプレビュー'],
    '예: 100':['e.g. 100','例如：100','例：100'],
    '예: 12':['e.g. 12','例如：12','例：12'],
    '예: 0':['e.g. 0','例如：0','例：0'],
    '모르면 비워두기':['Leave blank if unknown','未知时留空','不明な場合は空欄'],
    '몰라도 손익분기 원가 계산 가능':['Optional: break-even cost is available','可留空：仍可计算盈亏平衡成本','未入力でも損益分岐原価を算出可能'],
    '직접 가정값 입력':['Enter assumption','输入假设值','想定値を入力'],
    '영역별 점수':['Domain scores','各维度分数','分野別スコア'],
    '닫기':['Close','关闭','閉じる'],
    '보고서를 만들지 못했습니다. 다시 시도해 주세요.':['Could not generate the report. Please try again.','无法生成报告，请重试。','レポートを作成できませんでした。再試行してください。'],
    '판매단가(0 초과), 부대비용, 관세 가정값을 올바르게 입력해 주세요. 원가는 선택 사항입니다.':['Enter a selling price above zero, nonnegative expenses and assumed tariff. Cost is optional.','请正确输入大于0的销售单价、附加费用和假设关税。成本可选。','販売単価（0超）、付帯費用、想定関税を正しく入力してください。原価は任意です。'],
    '제품 원가는 0 이상의 숫자로 입력해 주세요.':['Enter a nonnegative product cost.','请输入非负的产品成本。','製品原価は0以上の数値で入力してください。'],
    '시나리오를 반영했습니다. 지금 PDF로 저장하면 결과가 포함됩니다.':['Scenario applied. You can now save the updated report as PDF.','情景已应用。现在保存为PDF可包含更新结果。','シナリオを反映しました。PDFとして保存すると結果が含まれます。'],
    '보고서 미리보기를 먼저 생성해 주세요.':['Generate a report preview first.','请先生成报告预览。','先にレポートのプレビューを作成してください。'],
    '인쇄 창에서 ‘PDF로 저장’을 선택하면 PDF 파일로 저장됩니다.':['Choose Save as PDF in the print dialog to download a PDF file.','在打印窗口选择“另存为 PDF”即可保存PDF文件。','印刷画面で「PDFとして保存」を選ぶとPDFファイルを保存できます。'],
    '시나리오를 Report에 반영':['Apply scenario to report','将情景应用于报告','シナリオをレポートに反映'],
    'Report에 반영':['Apply to report','应用到报告','レポートに反映'],
    '보고서 미리보기를 먼저 생성해 주세요.':['Generate the report preview first.','请先生成报告预览。','先にレポートのプレビューを生成してください。'],
    '원가를 몰라도':['even without product cost','即使不知道成本','原価が不明でも'],
    '손익분기 원가':['break-even cost','盈亏平衡成本','損益分岐原価'],
    '한국어':['한국어','韩语','韓国語'],
    '보고서':['Report','报告','レポート'],
    '점수':['Score','分数','スコア'],
    '가상 데이터':['sample data','示例数据','サンプルデータ'],
    '중국':['China','中国','中国'],
    '미국':['United States','美国','米国'],
    '일본':['Japan','日本','日本'],
    '독일':['Germany','德国','ドイツ'],
    '베트남':['Vietnam','越南','ベトナム'],
    '인도':['India','印度','インド'],
    '수출통제 후보 (통제번호·품목명)':['Potential export controls (code/product)','潜在出口管制（编码／品名）','輸出管理候補（番号・品名）'],
    '목적국 수입규제 기록':['Destination import restrictions','目的国进口限制记录','輸出先の輸入規制履歴'],
    '거래처 CSL 검색':['Customer CSL screening','客户 CSL 筛查','取引先の CSL 検索'],
    '목적국 수입시장 규모 (연간·월별)':['Destination import market (annual/monthly)','目的国进口市场规模（年／月）','輸出先の輸入市場規模（年・月）'],
    '한국산 수입점유율':['Korean import share','韩国产品进口份额','韓国産の輸入シェア'],
    '성장률 · 전년 동기 대비':['Growth · YoY','增长率・同比','成長率・前年比'],
    '성장률 · 최근 3개월 전년 동기 대비':['Growth · latest 3 months YoY','最近三个月同比增长率','直近3か月の前年比成長率'],
    '성장률 · 3년 연평균(CAGR)':['Growth · 3-year CAGR','三年复合年增长率','3年 CAGR'],
    '한국의 해당국 수출액 (관세청)':['Korean exports to destination (Customs)','韩国对目的国出口额（海关）','韓国の対象国向け輸出額（税関）'],
    'WSTS 반도체 매출 (세계·권역별, 업황 참고)':['WSTS semiconductor sales (global/regional)','WSTS 半导体销售额（全球／地区）','WSTS 半導体売上（世界・地域別）'],
    '무역통계 kg당 단가 (한국 → 목적국 수출)':['Trade unit value per kg (Korea to destination)','贸易统计每公斤单价（韩国至目的国）','貿易統計のkg単価（韓国→対象国）'],
    '회사 자료 · kg당 단가 (제품별·연도별)':['Company unit value/kg (product/year)','企业每公斤单价（按产品／年度）','企業データkg単価（製品・年別）'],
    '기준 대비 단가 (한국 전체 수출단가 대비)':['Unit-value index vs Korea total','相对韩国总出口单价的指数','韓国全体の輸出単価に対する指数'],
    '관세 참고치 (WTO, HS6·조치일별)':['Reference tariff (WTO, HS6/date)','参考关税（WTO、HS6／生效日）','参考関税（WTO、HS6・措置日）'],
    '참고환율 (원/USD)':['Reference FX rate (KRW/USD)','参考汇率（韩元／美元）','参考為替レート（KRW/USD）'],
    '수출입물가지수 · 컴퓨터,전자및광학기기 (수출, 잠정)':['Export price index · computers/electronics/optics','出口物价指数・计算机／电子／光学','輸出物価指数・電子等'],
    '인천공항 화물편 일정':['Incheon cargo flight schedule','仁川机场货运航班计划','仁川空港貨物便ダイヤ'],
    '운항 횟수 (국가별 월간 출발·도착편, 화물기)':['Monthly cargo flights by country','各国每月货运航班数','国別月間貨物便数'],
    '선박 입출항 기록 (부산항 · 중국 전후 항로)':['Vessel calls (Busan / China routes)','船舶进出港（釜山／中国航线）','船舶入出港（釜山／中国航路）'],
    '회사 자료 · 납기 준수율 (실제 ≤ 예정 도착)':['Company on-time delivery rate','企业准时交付率','企業データ・納期遵守率'],
    '회사 자료 · 평균 리드타임 (선적일 → 실제 도착일)':['Company average lead time','企业平均交付周期','企業データ・平均リードタイム'],
    '회사 자료 · 운송비 비중 (운임 ÷ 수출금액)':['Company freight / export value','企业运费占出口额比例','企業データ・運賃対輸出額比'],
    '회사 자료 · 월별 선적 건수 (운송수단별)':['Company monthly shipments by mode','企业按运输方式月度出货量','企業データ・輸送手段別月間出荷数'],
    '회사 자료 · 최근 선적 기록':['Company recent shipping records','企业最近发货记录','企業データ・最近の出荷記録'],
    '목적국 월별 수입금액·전월비':['Destination monthly imports / MoM','目的国月度进口额及环比','輸出先の月別輸入額・前月比'],
    '변동계수 CV (목적국 수입액)':['CV (destination imports)','变异系数（目的国进口额）','変動係数（輸出先の輸入額）'],
    '급감 이력 (전월비 −20% 이하)':['Sharp drops (MoM −20% or less)','大幅下跌记录（环比≤−20%）','急減履歴（前月比−20%以下）'],
    '회사 자료 · 중국 월별 수출액 변동(보조)':['Company exports to China (supplementary)','企业对华月度出口波动（辅助）','企業データ・中国向け月別輸出変動'],
    '결제통화 환율 변동성 (원/CNY, 보조)':['Settlement FX volatility (KRW/CNY)','结算货币汇率波动（韩元／人民币）','決済通貨の為替変動（KRW/CNY）'],
    'WSTS 세계·권역별 매출 변동(보조)':['WSTS global/regional sales variability','WSTS 全球／地区销售波动','WSTS 世界・地域別売上変動'],
    '규제 관문 · 규제 기록 및 수출통제 후보':['Regulatory gate · controls and restrictions','监管门槛：管制候选与限制记录','規制ゲート・管理候補と規制履歴'],
    '시장성 · 수입시장 규모 및 성장성':['Market · import size and growth','市场：进口规模及增长','市場性・輸入市場規模と成長性'],
    '가격 여건 · 통계상 단가·관세 참고치·환율':['Pricing · trade unit value, tariff and FX','价格：统计单价、参考关税及汇率','価格条件・統計単価／参考関税／為替'],
    '물류 · 화물 항공편 및 선박 입출항 기록':['Logistics · flights and vessel movements','物流：货运航班与船舶进出港','物流・貨物便と船舶入出港'],
    '안정성 · 수입금액 변동성과 급감 이력':['Stability · import variability and downturns','稳定性：进口额波动和骤降','安定性・輸入額の変動と急減履歴'],
    '회사 자료':['Company data','企业数据','企業データ'],
    '과거 참고점수':['historical indicative score','历史参考分数','過去の参考スコア'],
    '실제 수익성이 아닙니다':['not actual profitability','并非实际盈利能力','実際の収益性ではありません'],
    '자료 없음':['Data unavailable','暂无数据','データなし'],
    '전체 기간':['full period','全部期间','全期間'],
    '기준':['as of','截至','基準'],
    '수집':['collected','采集','取得'],
    '제품':['products','产品','製品'],
    '개 지표':[' indicators','项指标','指標'],
    '개 확인':[' available','项已确认','件確認済み'],
    '원자료':['source data','原始数据','原データ'],
    '수출실적 시트':['export-record sheet','出口记录表','輸出実績シート'],
    '제품정보':['product information','产品信息','製品情報'],
    '물류 시트':['logistics sheet','物流工作表','物流シート'],
  };
  const extra = {
    '판매단가, 부대비용과 관세를 입력하면 원가를 몰라도 손익분기 원가를 계산합니다. 아래 ‘보고서에 반영’을 누르면 PDF 미리보기도 갱신됩니다.':[
      'Enter selling price, extra expenses and tariff to calculate the break-even cost even without product cost. Apply the scenario to refresh the report preview.',
      '输入销售单价、附加费用和关税，即使不知道产品成本也能计算盈亏平衡成本。应用情景后报告预览会更新。',
      '販売単価、付帯費用、関税を入力すると原価が不明でも損益分岐原価を計算できます。シナリオを反映するとプレビューが更新されます。'],
    '회사 원가를 자동 추정하지 않습니다. 입력값은 가정이며 관세 실제 납부 주체는 계약조건에 따라 달라집니다.':[
      'Company costs are not estimated automatically. Inputs are assumptions; who actually pays tariffs depends on the contract.',
      '系统不会自动估算企业成本。输入值仅为假设；关税的实际支付方取决于合同条件。',
      '会社原価の自動推定は行いません。入力値は仮定であり、関税の実際の負担者は契約条件によります。'],
    '현재 분석 조건과 자료 확인 상태를 반영합니다. 시장 진입 여건 점수와 별도의 규제 확인 상태를 보여줍니다. 수익성 입력은 선택 사항입니다.':[
      'Reflects the current filters and data availability. Shows a market-entry score and separate regulatory review. Profitability inputs are optional.',
      '根据当前筛选条件和数据情况显示市场准入评分与独立的监管核查结果。盈利情景输入为可选项。',
      '現在の分析条件とデータ取得状況を反映します。市場参入スコアと規制確認状況を別に表示します。収益性の入力は任意です。'],
    'PDF 버튼을 누른 뒤 프린터에서 ‘PDF로 저장’을 선택하세요.':[
      'Open the print dialog and select Save as PDF to create a PDF file.',
      '打开打印窗口后，选择“另存为 PDF”以生成文件。',
      '印刷画面を開き、「PDFとして保存」を選んでください。'],
  };
  Object.assign(dictionary, extra);
  Object.assign(dictionary, {
  "규제 확인은 정량 점수와 별도이며 높은 점수가 선적 승인을 뜻하지 않습니다.": [
    "Regulatory clearance is separate from the quantitative score. A high score does not authorize shipment.",
    "监管审核独立于定量评分。高分不代表已获准发货。",
    "規制確認は定量スコアとは別です。高スコアでも出荷承認を意味しません。"
  ],
  "4개 영역의 관측 및 참고 지표를 종합한 시연 점수입니다.": [
    "This demo score combines observed and reference indicators across four domains.",
    "本演示评分综合四个维度的观测及参考指标。",
    "このデモスコアは4分野の観測・参考指標を統合したものです。"
  ],
  "평가 범위": [
    "Scored coverage",
    "评估覆盖范围",
    "評価範囲"
  ],
  "그중 과거 통계": [
    "including historical statistics",
    "其中历史统计",
    "うち過去統計"
  ],
  "관세·환율 대리지표": [
    "tariff/FX proxies",
    "关税／汇率替代指标",
    "関税・為替の代替指標"
  ],
  "실제 이익률이나 수출 가능 여부를 뜻하지 않습니다.": [
    "This is neither an actual profit margin nor a determination of export eligibility.",
    "不代表实际利润率或出口合法性。",
    "実際の利益率や輸出可否を示すものではありません。"
  ],
  "네 정량 영역 모두 점수 산정에 포함됐습니다.": [
    "All four quantitative domains are scored.",
    "四个定量维度均纳入评分。",
    "4つの定量分野すべてを採点しました。"
  ],
  "단, 가격 영역은 원가 없이 계산한 관세·환율 여건 점수이고, 과거 통계의 시차가 존재합니다.": [
    "However, pricing is assessed using tariff and FX proxies without cost data, and historical statistics have a time lag.",
    "但价格分数仅依据关税和汇率、未包含成本，历史统计也存在时滞。",
    "ただし価格は原価を含まない関税・為替の代理指標で、過去統計には時差があります。"
  ],
  "제품 사양서로 전략물자 해당 여부를 확인하고 수출허가 필요성을 검토하세요.": [
    "Verify strategic-item classification against the technical specifications and check licensing requirements.",
    "请依据产品规格核查是否属于战略物资，并确认是否需要出口许可。",
    "製品仕様に基づき戦略物資への該当性と輸出許可の要否を確認してください。"
  ],
  "제품별 실제 판매단가와 원가를 입력해 손익분기 원가 및 예상 이익률을 확인하세요. 가격 여건 점수는 실제 수익성이 아닙니다.": [
    "Enter actual product prices and costs to calculate break-even costs and indicative margins. The pricing score does not measure profitability.",
    "请输入各产品实际售价和成本，以计算盈亏平衡成本及预计利润率。价格评分不代表实际盈利能力。",
    "製品別の実際の販売単価と原価を入力し、損益分岐原価と想定利益率を確認してください。価格スコアは実際の収益性ではありません。"
  ],
  "시장성에 과거 통계를 활용했습니다. 최신 목적국 수입실적을 확보하고 최근 한국의 대중국 수출 동향과 구분해 확인하세요.": [
    "Market potential uses historical data. Obtain more recent destination-country imports and review them separately from recent Korean exports.",
    "市场潜力采用历史统计。请获取目的国最新进口数据，并与韩国近期对华出口趋势分别核查。",
    "市場性には過去統計を使用しています。輸出先の最新輸入実績を入手し、韓国の最近の対中輸出動向とは分けて確認してください。"
  ],
  "시연용 가상 기업 자료와 날짜가 다른 공개 통계를 함께 사용합니다.": [
    "This demonstration combines fictional company records with public statistics from different dates.",
    "本演示结合虚构企业数据与不同日期的公开统计。",
    "このデモは架空の企業データと基準日が異なる公開統計を併用しています。"
  ],
  "특정 기준일의 검색 결과는 허가, 제재·전략물자 비해당 또는 운송 가능성을 증명하지 않습니다.": [
    "A screening result at a particular date does not establish licensing, exemption from restrictions or transport availability.",
    "某一日期的检索结果并不能证明已获得许可、不受制裁或可以运输。",
    "特定日の検索結果は許可、制裁・戦略物資の非該当性や輸送可能性を証明しません。"
  ],
  "은 의사결정 준비율이 아닙니다.": [
    "is not a measure of decision readiness.",
    "并非决策准备完成率。",
    "は意思決定の準備率ではありません。"
  ],
  "기업 내부 성과와 공개 통계의 기준일 및 품목 범위가 다를 수 있습니다. 시장 통계의 대상 HS를 반드시 확인하세요.": [
    "Company performance and public statistics may cover different periods or product groups. Always verify the HS scope of market statistics.",
    "企业内部业绩和公开统计的日期及商品范围可能不同。请务必核实市场统计的HS范围。",
    "企業実績と公開統計では基準日や品目範囲が異なる場合があります。市場統計の対象HSを必ず確認してください。"
  ],
  "선택 HS가 전체가 아닌 경우 시장통계·관세·기업 실적의 HS 범위가 서로 같은지 비교하며 서로 다른 범위의 값을 직접 비교하지 않습니다.": [
    "When a specific HS is selected, verify that market, tariff and company records cover compatible products; do not compare different scopes directly.",
    "选择特定HS后，请核对市场、关税与企业记录的商品范围是否一致，避免直接比较不同范围的数值。",
    "特定のHSを選択した場合、市場統計・関税・企業実績の品目範囲を確認し、範囲の異なる数値を直接比較しないでください。"
  ],
  "제한 명단 정확 일치 검색은 예비 확인이며 법률상 거래 가능 여부의 결론이 아닙니다.": [
    "Exact-name restricted-party screening is preliminary, not a legal determination that a transaction is permitted.",
    "受限名单的精确名称匹配仅为初步筛查，并非法定交易许可结论。",
    "制限対象リストの完全一致検索は予備確認であり、取引の適法性を確定するものではありません。"
  ],
  "HSK 연계표는 통제번호 후보 탐색용입니다. 거래처 법인명 정확 일치 검색의 한계로 별칭·현지어·최종사용자 및 최신 목록은 별도 확인해야 합니다.": [
    "The HSK crosswalk identifies possible control classifications only. Exact-name screening may miss aliases or local-language names; verify end users and current lists separately.",
    "HSK对应表仅用于查找潜在管制编码。精确名称匹配可能遗漏别名或当地语言名称；请另行核查最终用户及最新名单。",
    "HSK対応表は規制番号の候補検索用です。完全一致検索では別名・現地語名を見逃す可能性があるため、最終需要者と最新リストを別途確認してください。"
  ],
  "과거 통계 기반 참고점수; 최신 시장 매력도 판정 아님": [
    "Historical indicative score, not a current market-attractiveness judgment",
    "基于历史统计的参考分数，并非最新市场吸引力判断",
    "過去統計に基づく参考スコアであり、現在の市場魅力度の判定ではありません"
  ],
  "선택 HS 원자료로 계산했습니다.": [
    "calculated from source data for the selected HS.",
    "根据所选HS的原始数据计算。",
    "選択HSの原データから算出しました。"
  ],
  "선택 HS 수치와 직접 비교하지 마세요.": [
    "Do not compare these figures directly with those for the selected HS.",
    "请勿与所选HS的数据直接比较。",
    "選択HSの数値と直接比較しないでください。"
  ],
  "WSTS 세계 매출과 회사 자체 수출실적은 목적국 수입시장 성장률 점수에 합산하지 않습니다.": [
    "WSTS global sales and company exports are not included in the destination import-growth score.",
    "目的国进口增长评分不包含WSTS全球销售额或本企业出口额。",
    "輸出先の輸入成長スコアにはWSTSの世界売上や自社輸出実績を含めません。"
  ],
  "두 지표에 50:50 가중치를 적용한 내부 참고점수로, 판매가나 원가에 근거한 이익률이 아닙니다.": [
    "This internal reference score weights the two indicators equally; it is not a profit margin based on selling prices or costs.",
    "该内部参考分数对两项指标各赋予50%的权重，并非依据售价或成本计算的利润率。",
    "この社内参考スコアは2指標を50:50で加重したもので、販売価額や原価に基づく利益率ではありません。"
  ],
  "통계상 수출단가는 제품구성·기간 차이를 확인하세요.": [
    "Interpret statistical export unit values in light of product mix and period differences.",
    "解读统计出口单价时，请注意产品构成及统计期间差异。",
    "統計上の輸出単価は製品構成と期間の違いに注意してください。"
  ],
  "회사 가상 납기·운임, 과거 기록 기준": [
    "Based on historical, fictional company lead-time and freight records",
    "基于虚构企业的历史交期和运费记录",
    "架空企業の過去の納期・運賃実績に基づく"
  ],
  "회사 거래처 집중도·월별 실적 변동; 국가 신용도나 정치적 위험 점수 아님": [
    "Based on customer concentration and monthly company performance; not a sovereign or political-risk score",
    "基于企业客户集中度和月度业绩；并非国家信用或政治风险评分",
    "取引先集中度と月別企業実績に基づき、国の信用度や政治リスクは採点しません"
  ],
  "가정을 입력하지 않았습니다. 판매단가·부대비용·관세만 입력해도 감당 가능한 최대 제품원가를 계산할 수 있습니다.": [
    "No assumptions entered. Selling price, extra expenses and tariff are enough to calculate the maximum affordable product cost.",
    "尚未输入假设。只需输入售价、附加费用和关税，即可计算可承担的最高产品成本。",
    "仮定は未入力です。販売単価・付帯費用・関税を入力すると許容可能な最大製品原価を計算できます。"
  ],
  "예상 판매단가와 부대비용은 동일한 USD/개 단위로 입력해야 합니다.": [
    "Enter selling price and extra costs in matching USD-per-unit terms.",
    "请以相同的美元/件单位输入售价和附加费用。",
    "販売単価と付帯費用は同じUSD/個単位で入力してください。"
  ],
  "관세를 수출자가 부담한다는 가정으로만 계산하며 실제 계약 조건·Incoterms·환율·세금에 따라 달라집니다.": [
    "This assumes the exporter bears tariffs; results vary with the contract, Incoterms, exchange rates and taxes.",
    "计算假设关税由出口方承担；实际结果会因合同、Incoterms、汇率和税费而异。",
    "関税を輸出者が負担する仮定で計算しています。実際の結果は契約、インコタームズ、為替、税金によって異なります。"
  ],
  "입력한 값은 이 HTML에서만 계산되며 대시보드 점수에 자동 반영되지 않습니다. PDF에 포함하려면 계산한 뒤 인쇄하세요.": [
    "Inputs are calculated in this HTML only; dashboard scores are unchanged. Calculate before printing to include the result in the PDF.",
    "输入值仅在此HTML中计算，不会自动改变仪表盘评分。计算后再打印，结果才会包含在PDF中。",
    "入力値はこのHTMLでのみ計算し、ダッシュボードのスコアには反映されません。PDFに含める場合は計算後に印刷してください。"
  ],
  "기존 공개자료 및 기업 자료를 보존했습니다. 항목별 기준일·수록 HS·자료 상태를 먼저 확인하세요. 확인됨은 자료가 존재한다는 뜻이며 수출 가능성 확정을 의미하지 않습니다.": [
    "Original public and company data are retained. Verify each item’s date, HS scope and availability. Available data does not certify export eligibility.",
    "已保留原始公开数据和企业数据。请核查各项的基准日、HS范围及数据状态。有数据不等于已确认具备出口资格。",
    "元の公開データと企業データは保持しています。各項目の基準日、HS範囲、取得状況をご確認ください。データ取得済みでも輸出可能性を確定しません。"
  ],
  "기업 엑셀 가상 자료 및 각 상세 항목에 명시한 공공 데이터.": [
    "Fictional company Excel data and the public sources cited for each indicator.",
    "虚构企业Excel数据及各指标注明的公开来源。",
    "架空企業のExcelデータと各指標に記載した公開情報。"
  ],
  "사용자 입력 파일은 이 시연판에서 등록된 샘플과 일치할 때만 읽습니다.": [
    "This demo reads uploaded files only when they match registered samples.",
    "本演示仅识别与预置样本一致的上传文件。",
    "このデモは登録済みサンプルと一致するアップロードファイルのみ読み取ります。"
  ],
  "자료 수집일은 개별 항목의 기준일과 다릅니다.": [
    "Data collection dates differ from the as-of dates of individual indicators.",
    "数据采集日期可能与各指标的基准日不同。",
    "データ取得日は各指標の基準日と異なります。"
  ],
  "최신 규정의 확정적인 법률 해석·통관·허가 자문이 아닙니다.": [
    "This is not definitive legal, customs or licensing advice on current regulations.",
    "本报告不构成对现行法规的最终法律、通关或许可建议。",
    "現行規制に関する確定的な法的解釈、通関・許可の助言ではありません。"
  ],
  "납기 준수율": [
    "On-time delivery rate",
    "准时交付率",
    "納期遵守率"
  ],
  "거래처 집중도": [
    "Customer concentration",
    "客户集中度",
    "取引先集中度"
  ],
  "가중 관세 참고율": [
    "Weighted reference tariff",
    "加权参考关税率",
    "加重平均参考関税率"
  ],
  "원/USD 환율 평균 월변동폭": [
    "KRW/USD mean monthly FX change",
    "韩元／美元平均月度汇率波动",
    "KRW/USDの平均月次変動幅"
  ],
  "월별 수출액 변동계수": [
    "Monthly export value CV",
    "月度出口额变异系数",
    "月別輸出額の変動係数"
  ],
  "국가위험 아님": [
    "not sovereign risk",
    "并非国家风险",
    "国別リスクではありません"
  ],
  "실제 제품 경쟁가격과 마진은 미산정": [
    "Actual product competitive pricing and margin not evaluated",
    "未评估实际产品竞争价格和利润率",
    "実際の製品競争価格と利益率は未算出"
  ],
  "가중 관세": [
    "Weighted tariff",
    "加权关税",
    "加重平均関税"
  ],
  "환율 변동": [
    "FX variation",
    "汇率波动",
    "為替変動"
  ],
  "미산정": [
    "not calculated",
    "未计算",
    "未算出"
  ],
  "수출허가": [
    "export license",
    "出口许可",
    "輸出許可"
  ],
  "제품 사양에 따라 전략물자 확인 필요": [
    "Strategic-item assessment required based on technical specifications",
    "须按产品规格核查是否属于战略物资",
    "製品仕様に基づく戦略物資確認が必要"
  ],
  "판매단가": [
    "selling price",
    "销售单价",
    "販売単価"
  ],
  "부대비용": [
    "additional expenses",
    "附加费用",
    "付帯費用"
  ],
  "관세 가정": [
    "assumed tariff",
    "假设关税",
    "想定関税"
  ],
  "손익분기 최대 제품원가": [
    "maximum break-even product cost",
    "最高盈亏平衡产品成本",
    "損益分岐となる最大製品原価"
  ],
  "실제 원가 미입력으로 이익률은 미산정": [
    "Margin not calculated without actual cost",
    "未输入实际成本，利润率未计算",
    "実際の原価が未入力のため利益率は未算出"
  ],
  "제품별 계약조건에 따라 결과가 달라집니다.": [
    "Results depend on product-specific contract terms.",
    "结果取决于各产品的合同条款。",
    "結果は製品別の契約条件によって異なります。"
  ],
  "제품별 계약조건": [
    "product-specific contract terms",
    "产品合同条款",
    "製品別の契約条件"
  ],
  "실제 원가": [
    "actual cost",
    "实际成本",
    "実際の原価"
  ],
  "단위이익": [
    "unit profit",
    "单位利润",
    "単位利益"
  ],
  "이익률": [
    "profit margin",
    "利润率",
    "利益率"
  ]
});


  // Parameterized paragraphs are translated as complete units rather than word-by-word;
  // this prevents mixed-language grammar while retaining user-defined weights and values.
  Object.assign(dictionary, {
    '한빛반도체':['Hanbit Semiconductor','韩光半导体','ハンビット半導体'],
    '대성반도체':['Daesung Semiconductor','大成半导体','大成半導体'],
    '새벽반도체':['Saebyeok Semiconductor','晓光半导体','セビョク半導体'],
    '수입 전년 대비':['import growth, YoY','进口额同比','輸入額の前年比'],
    '자료 확인':['Data availability','资料核实','データ確認'],
    '품목 비중':['product share','产品占比','品目の比率'],
    '에 적용한 선택 HS 범위만 집계':['; only the HS scope used in scoring is aggregated','；仅汇总评分使用的所选HS范围','・採点に使用した選択HS範囲のみ集計'],
    'HS 묶음 원본으로 선택 HS 수치와 별개':['Original combined-HS data, separate from the selected-HS figures','原始HS组合数据，与所选HS数值分开','HS合計の原データであり、選択HSの数値とは別'],
    '가중 관세':['Weighted tariff','加权关税','加重平均関税'],
    '가중':['Weighted','加权','加重'],
    '평균 환율 변동':['Mean FX variation','平均汇率波动','平均為替変動'],
    '원/USD':['KRW/USD','韩元／美元','KRW/USD'],
    'USD/개':['USD/unit','美元/件','USD/個'],
  });
  Object.assign(dictionary, {"개 제품": [" products", "个产品", "製品"], "개": ["", "个", "件"], "연간": ["annual", "年度", "年次"], "회사 자료 · 중국 수출액 (연도별·월별)": ["Company data: exports to China (annual/monthly)", "企业对华出口额（年度／月度）", "企業の中国向け輸出額（年・月別）"], "회사 자료 · 미국 수출액 (연도별·월별)": ["Company data: exports to the United States (annual/monthly)", "企业对美出口额（年度／月度）", "企業の米国向け輸出額（年・月別）"], "운송비 참고 (해상수출·해상수입·항공수입 구분)": ["Transport-cost reference (sea export/import, air import)", "运费参考（海运出口／进口、航空进口）", "運送費の参考（海上輸出入・航空輸入別）"], "조회 조건(회사 자료)": ["Query conditions (company data)", "查询条件（企业数据）", "検索条件（企業データ）"], "관세청 품목별 국가별 수출입실적": ["Korea Customs trade data by HS and country", "韩国海关按品目及国家统计的进出口数据", "韓国税関・品目別国別輸出入実績"], "한국수출입은행 현재환율 (매매기준율)": ["Export–Import Bank of Korea reference exchange rate", "韩国进出口银行参考汇率", "韓国輸出入銀行の参考為替レート"], "인천국제공항공사 화물편 주간 운항 현황": ["Incheon Airport weekly cargo-flight schedules", "仁川国际机场每周货运航班计划", "仁川空港の週次貨物便運航状況"], "인천국제공항공사 국가별 항공 통계": ["Incheon Airport flight statistics by country", "仁川国际机场分国别航空统计", "仁川空港の国別航空統計"], "해양수산부 선박운항정보(선박입출항신고)": ["Ministry of Oceans and Fisheries vessel movement records", "韩国海洋水产部船舶出入港申报记录", "韓国海洋水産部の船舶入出港記録"], "한국수출입은행 현재환율": ["Export–Import Bank of Korea FX rate", "韩国进出口银行汇率", "韓国輸出入銀行の為替レート"], "매매기준율": ["reference rate", "买卖基准汇率", "売買基準レート"], "운송비 비중": ["freight expense ratio", "运费占比", "運賃比率"], "수출데이터": ["export_data", "出口数据", "輸出データ"], "기본분류": ["basic classification", "基本分类", "基本分類"], "수출입물가지수무역지수": ["trade_and_export_import_price_indices", "进出口价格及贸易指数", "輸出入物価・貿易指数"]});
  Object.assign(dictionary, {
    '전체 분석기간':['full analysis period','完整分析期间','全分析期間'],
    '추세':['trend','趋势','推移'],
    '수출 의사결정 분석 보고서':['Export decision-support analysis report','出口决策分析报告','輸出意思決定分析レポート'],
    '수출 보고서':['Export report','出口报告','輸出レポート'],
  });
  const entireParagraphs = {
    '회사 가상 시트의 운임 비중은 실제 견적, 운송수단, Incoterms 및 화물보험료와 검증 전까지 단순 참고로만 사용합니다. 항공·항만 운항 이력은 반도체 화물의 실제 선복 또는 직항·소요일을 보장하지 않습니다.': [
      'Freight ratios from the fictional company records are indicative until validated against actual quotes, shipping mode, Incoterms and cargo insurance. Flight and vessel records do not guarantee semiconductor cargo capacity, direct routes or transit times.',
      '虚构企业记录中的运费占比仅供参考，需结合实际报价、运输方式、Incoterms及货物保险进行验证。航班和船舶记录不保证半导体货物舱位、直达线路或运输时间。',
      '架空企業の運賃比率は、実際の見積、輸送手段、インコタームズ、貨物保険で検証するまでは参考値です。航空・船舶の運航記録は半導体貨物の積載枠、直行便や所要時間を保証しません。'
    ],
  };
  function entireTranslation(raw,code){
    if(code==='ko')return null;
    const t=raw.trim(), ix=languages.indexOf(code)-1;
    if(entireParagraphs[t])return entireParagraphs[t][ix];
    let m;
    if((m=t.match(/^4개 영역의 관측 및 참고 지표를 종합한 시연 점수입니다\. 평가 범위 ([\d.]+)%이며 그중 과거 통계 ([\d.]+)%p, 관세·환율 대리지표 ([\d.]+)%p입니다\. 실제 이익률이나 수출 가능 여부를 뜻하지 않습니다\.$/))){
      const [,coverage,historical,proxy]=m;
      return [
        `This illustrative score combines four domains of observed and reference indicators. Scored coverage is ${coverage}%, including ${historical} percentage points of historical statistics and ${proxy} percentage points of tariff/FX proxies. It does not represent actual profitability or legal export eligibility.`,
        `该演示分数综合四个维度的观测与参考指标。评分覆盖范围为${coverage}%，其中历史统计占${historical}个百分点、关税及汇率替代指标占${proxy}个百分点。它不代表实际盈利能力或法律意义上的出口资格。`,
        `このデモスコアは4分野の観測・参考指標を統合したものです。評価範囲は${coverage}%で、うち過去統計が${historical}ポイント、関税・為替の代替指標が${proxy}ポイントです。実際の収益性や法的な輸出可否を示すものではありません。`
      ][ix];
    }
    if((m=t.match(/^회사 가상 시트의 운임 비중(?:\(([^)]*)\))?은 실제 견적, 운송수단, Incoterms 및 화물보험료와 검증 전까지 단순 참고로만 사용합니다\. 항공·항만 운항 이력은 반도체 화물의 실제 선복 또는 직항·소요일을 보장하지 않습니다\.$/))){
      const detail=m[1]?` (${translate(m[1],code)})`:'';
      return [
        `Freight expense ratio from fictional company records${detail} is indicative until verified against quotes, shipping mode, Incoterms and cargo insurance. Flight and port records do not guarantee capacity, direct shipping or transit time for semiconductors.`,
        `虚构企业记录的运费占比${detail}仅供参考，须结合实际报价、运输方式、Incoterms及货物保险核实。航空和港口记录不保证半导体货物的运力、直达航线或运输时间。`,
        `架空企業データの運賃比率${detail}は、実際の見積、輸送手段、インコタームズ、貨物保険で検証するまで参考値です。航空・港湾の記録は半導体の輸送枠、直行経路や所要時間を保証しません。`
      ][ix];
    }
    if((m=t.match(/^기본 가중치: 시장성 (\d+(?:\.\d+)?)%, 가격 (\d+(?:\.\d+)?)%, 물류 (\d+(?:\.\d+)?)%, 거래 안정성 (\d+(?:\.\d+)?)%\./))){
      const [market,price,logistics,stability]=m.slice(1);
      return [
        `Base weights: market ${market}%, pricing ${price}%, logistics ${logistics}% and trading stability ${stability}%. Market scores use 24 comparable months of imports for the selected HS. Data lagging the company assessment month by 7–18 months are marked historical; data over 18 months old are not scored. The pricing score equally weights the weighted tariff rate and observed average monthly KRW/USD FX volatility up to the assessment month. The illustrative tariff score equals 100 − 5 × tariff rate (%); the FX score equals 100 − 12.5 × average absolute monthly FX change (%). Both are capped at 0–100; pricing is unscored if either input is missing. Coefficients are internal demo assumptions, not product pricing or profit margins. The indicative total is a weighted average across available domains; if coverage is below 35%, only domain results are shown. Regulatory checks and profitability scenarios remain separate.`,
        `基础权重：市场${market}%、价格${price}%、物流${logistics}%、交易稳定性${stability}%。市场评分使用所选HS连续可比的24个月进口数据。比企业评估月份滞后7至18个月的数据标注为历史参考；超过18个月不计分。价格评分将所选HS加权参考关税和截至评估月的韩元／美元平均月度汇率波动各占50%。示例关税分数＝100－5×关税率（%）；汇率分数＝100－12.5×平均月度绝对变动率（%），分数限定在0–100之间。缺少其中任一指标则暂停价格评分。系数仅为团队演示假设，不衡量实际竞争价格或利润率。综合参考分数仅对可评估维度加权平均，覆盖不足35%时只显示各维度结果。监管审核和盈利情景单独处理。`,
        `基本ウェイト：市場性${market}%、価格${price}%、物流${logistics}%、取引安定性${stability}%。市場性には選択HSの比較可能な24か月の輸入統計を使用します。企業評価月から7～18か月遅れたデータは過去の参考値とし、18か月を超える場合は採点から除外します。価格スコアは選択HSの加重参考関税率と評価月までのKRW/USD平均月次変動幅を50:50で加重します。デモ用関税スコアは100－5×関税率（%）、為替スコアは100－12.5×月次絶対変動率（%）で、いずれも0～100に制限します。どちらかが欠ける場合は価格を採点しません。係数は社内デモ用の仮定であり、実際の競争価格や利益率ではありません。総合参考スコアは評価可能分野の加重平均とし、カバー率35%未満では分野別結果のみ表示します。規制と収益性は別途確認します。`
      ][ix];
    }
    if((m=t.match(/^선택 HS (\d+)의 수입시장 규모·성장률·시장성 점수는 선택 HS 원자료로 계산했습니다\. 별도 표시한 공개자료 원본은 HS ([\d, ]+) 묶음 기준이므로 선택 HS 수치와 직접 비교하지 마세요\. WSTS 세계 매출과 회사 자체 수출실적은 목적국 수입시장 성장률 점수에 합산하지 않습니다\.$/))){
      const [,hs,all]=m;
      return [
        `Import size, growth and market score for HS ${hs} were calculated from data for that HS alone. The separately displayed source covers combined HS ${all}, so do not compare its values directly. WSTS global billings and company export sales are excluded from the destination import-growth score.`,
        `HS ${hs} 的进口规模、增长率和市场分数均以该HS原始数据计算。单独展示的公开源数据汇总了HS ${all}，两者不能直接比较。WSTS全球销售额和企业出口额不计入目的国进口增长评分。`,
        `HS ${hs} の輸入市場規模、成長率および市場スコアは同HSの原データから算出しています。別掲の公開データはHS ${all}の合計であり、直接比較できません。WSTS世界売上と自社輸出額は輸出先の輸入成長スコアに含めません。`
      ][ix];
    }
    if((m=t.match(/^선택 HS의 가중 관세 참고율 ([\d.]+)%; 원\/USD 환율의 관측기간 평균 월변동폭 ([\d.]+)% \(([^)]+)\)\./))){
      const [,tax,fx,period]=m;
      return [
        `Selected-HS weighted reference tariff: ${tax}%; observed average monthly KRW/USD FX variation: ${fx}% (${period}). This internal reference score equally weights the two inputs; it is not a margin derived from product prices or costs. Interpret statistical export unit values with attention to product mix and period.`,
        `所选HS加权参考关税：${tax}%；韩元／美元在${period}期间的平均月度汇率波动：${fx}%。内部参考分数对两项指标各赋予50%权重，不是基于售价或成本的利润率。解读统计出口单价时请注意产品结构和期间。`,
        `選択HSの加重参考関税率：${tax}%、KRW/USDの観測期間${period}における平均月次変動幅：${fx}%。2指標を50:50で加重した社内参考スコアであり、実際の販売価額と原価から求めた利益率ではありません。統計上の輸出単価は製品構成と期間差に注意してください。`
      ][ix];
    }
    if((m=t.match(/^가정 손익분기 최대 제품원가 ([\d.,-]+) USD\/개 \(판매단가 ([\d.,-]+), 부대비용 ([\d.,-]+), 관세 가정 ([\d.,-]+)%\)\. (.*) 제품별 계약조건에 따라 결과가 달라집니다\.$/))){
      const [,max,sale,expenses,tax,margin]=m;
      const end=/실제 원가 미입력/.test(margin)?[
        'Margin is not calculated because actual product cost was not entered.',
        '由于未输入实际产品成本，利润率未计算。',
        '実際の原価が未入力のため、利益率は算出していません。'
      ][ix]: dictionary['이익률'][ix]+': '+margin.replace(/[^\d.%-]/g,'');
      return [
        `Assumed maximum break-even product cost: ${max} USD/unit (selling price ${sale}, extra expenses ${expenses}, assumed tariff ${tax}%). ${end} Results depend on product-specific contract terms.`,
        `假设最高盈亏平衡产品成本：${max} 美元/件（售价${sale}，附加费用${expenses}，假设关税${tax}%）。${end} 结果取决于各产品合同条件。`,
        `想定損益分岐の最大製品原価：${max} USD/個（販売単価${sale}、付帯費用${expenses}、想定関税${tax}%）。${end} 結果は製品別の契約条件によって異なります。`
      ][ix];
    }
    return null;
  }
  function translate(input, lang) {
    const code = languages.includes(lang) ? lang : 'ko';
    if (code === 'ko' || !input) return String(input ?? '');
    const whole=entireTranslation(String(input),code);
    if(whole!==null)return whole;
    let output = String(input), idx = languages.indexOf(code)-1;
    const ordered = Object.entries(dictionary).sort((a,b)=>b[0].length-a[0].length);
    for (const [source, values] of ordered) if(output.includes(source)) output=output.split(source).join(values[idx]);
    // Existing site-wide phrases, including common status words and country labels.
    if (window.AXPI18n?.language === code) output=window.AXPI18n.t(output);
    return output;
  }
  function translateHTML(html, lang) {
    if (!lang || lang === 'ko') return html;
    const doc = new DOMParser().parseFromString(html,'text/html');
    doc.documentElement.lang = lang;
    const walker=doc.createTreeWalker(doc.documentElement, NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
    while(walker.nextNode()) {
      const node=walker.currentNode;
      if(node.nodeType === 3) {
        if(node.parentElement?.closest('script,style'))continue;
        const raw=node.nodeValue;
        if(/[가-힣]/.test(raw))node.nodeValue=translate(raw,lang);
      }else if(node.nodeType===1){
        for(const attr of ['placeholder','title','aria-label','alt']) {
          const raw=node.getAttribute(attr);
          if(raw && /[가-힣]/.test(raw))node.setAttribute(attr,translate(raw,lang));
        }
      }
    }
    const title=doc.querySelector('title');if(title)title.textContent=translate(title.textContent,lang);
    return '<!doctype html>\n'+doc.documentElement.outerHTML;
  }
  // (junhee) 2026-09-28 사전을 화면 전체 번역기(AXPI18n)에 등록하지 않는다: 기존 화면 문장의 부분 번역이 바뀌지 않게 보고서 안에서만 쓴다.
  const scenario = {
    ko: {missing:'판매단가, 기타 부대비용, 관세 가정값을 입력해 주세요. 제품 원가는 선택 사항입니다.',invalid:'판매단가는 0보다 크게, 나머지 값은 0 이상으로 입력해 주세요.',cost:'가정 손익분기 최대 제품원가 ',tariff:' (관세비용 ',unit:' USD/개',profit:' 입력한 원가 적용 시 단위이익 ',margin:', 이익률 ',noCost:' 실제 원가 미입력으로 이익률은 산정하지 않았습니다.',warning:' 경고: 입력한 판매가격은 부대비용과 관세 가정액도 충당하지 못합니다.',disclaimer:' 실제 마진이나 통관세액을 보장하지 않는 가정 계산입니다.'},
    en: {missing:'Enter selling price, additional expenses and assumed tariff. Product cost is optional.',invalid:'Selling price must be above zero and other inputs must be nonnegative.',cost:'Assumed maximum break-even product cost: ',tariff:' (tariff expense: ',unit:' USD/unit',profit:' With the entered cost, unit profit: ',margin:', margin: ',noCost:' Margin is not calculated without actual product cost.',warning:' Warning: selling price does not cover additional expenses and assumed tariff.',disclaimer:' This is a hypothetical estimate, not a guarantee of profit or customs duties.'},
    zh: {missing:'请输入销售单价、附加费用和假设关税。产品成本可选。',invalid:'销售单价必须大于0，其他输入不得为负。',cost:'假设盈亏平衡最高产品成本：',tariff:'（关税费用：',unit:' 美元/件',profit:' 根据输入的成本，单位利润：',margin:'，利润率：',noCost:' 未输入实际成本，无法计算利润率。',warning:' 警告：销售价格不足以覆盖附加费用和假设关税。',disclaimer:' 本结果仅为情景估算，不保证实际利润或关税金额。'},
    ja: {missing:'販売単価、付帯費用、想定関税を入力してください。製品原価は任意です。',invalid:'販売単価は0より大きく、その他の入力は0以上にしてください。',cost:'想定損益分岐の最大製品原価：',tariff:'（関税費用：',unit:' USD/個',profit:' 入力した原価による単位利益：',margin:'、利益率：',noCost:' 実際の原価が未入力のため利益率は算出しません。',warning:' 警告：販売価格では付帯費用と想定関税を賄えません。',disclaimer:' これは仮定に基づく計算であり、実際の利益や関税額を保証しません。'}
  };

  // Unlike the global page translator, the report dialog has a single Korean source
  // for every string. Text-node updates preserve the calculator inputs and user data.
  const dialogTextSources = new WeakMap();
  const dialogAttrSources = new WeakMap();
  const explicitPlaceholders = {
    'report-sale':'예: 100', 'report-cost':'모르면 비워두기',
    'report-extras':'예: 12', 'report-tax':'예: 0'
  };
  function localizeDialog() {
    const root=document.getElementById('report-dialog');
    if(!root)return;
    const lang=window.AXPI18n?.language||'ko';
    const desc=root.querySelector(':scope > .modal-description');
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
      const node=walker.currentNode;
      if(node.parentElement?.closest('script,style'))continue;
      let source=dialogTextSources.get(node);
      if(source === undefined){
        source = node.nodeValue; // (junhee) 2026-09-28 설명문은 대시보드가 넣은 현재 문구를 그대로 번역(원본은 v0.6 고정 문장으로 바꿈)
        dialogTextSources.set(node,source);
      }
      const localized=translate(source,lang);
      if(node.nodeValue!==localized)node.nodeValue=localized;
    }
    for(const el of root.querySelectorAll('[placeholder],[title],[aria-label]')){
      let sources=dialogAttrSources.get(el);
      if(!sources){sources={};dialogAttrSources.set(el,sources);}
      for(const attr of ['placeholder','title','aria-label']){
        if(!el.hasAttribute(attr))continue;
        if(!(attr in sources))sources[attr]=attr==='placeholder'&&explicitPlaceholders[el.id]||el.getAttribute(attr);
        const value=translate(sources[attr],lang);
        if(el.getAttribute(attr)!==value)el.setAttribute(attr,value);
      }
    }
    // The report title/description are intentionally controlled by formalChrome.
    // Keep the latest language choice across report preview regeneration.
  }

  // Localized methodological descriptions for every published data indicator.
  // Original Korean source notes remain untouched in the company JSON so the
  // technical team can independently audit the method and its exact sample counts.
  const itemNotes = {
    export_control_candidates:[
      'Match each product’s 10-digit HSK code to HSKCD in the crosswalk; split CNTRLNO into candidate control classifications. This is candidate screening, not a strategic-item determination.',
      '将各产品10位HSK编码与对应表HSKCD精确匹配，并按逗号拆分CNTRLNO形成管制编码候选清单。结果仅为候选筛查，不构成战略物资判定。',
      '製品の10桁HSKを対応表のHSKCDと照合し、CNTRLNOを候補番号に分割します。候補の抽出であり戦略物資の確定判定ではありません。'],
    import_regulation_records:[
      'Filter the destination country’s import-restriction records by matching the beginning of each HS code to the analyzed HS6 codes. No matching record does not prove absence of restrictions.',
      '按目的国及HS编码前缀筛选进口限制记录，并与所分析的HS6对应。无匹配记录并不证明不存在限制。',
      '対象国の輸入規制記録をHSコードの前方一致で選択HS6と照合します。一致記録がなくても規制がないとは限りません。'],
    csl_search:[
      'Normalize destination-country customer names to uppercase alphanumeric text and compare exactly with CSL primary and alternate names. Exact matching can miss aliases and does not clear a transaction.',
      '将目的国客户法人名称标准化为大写字母和数字，与CSL名称及别名精确匹配。精确匹配可能遗漏其他名称，不能作为准许交易的结论。',
      '取引先の法人名を英数字大文字に正規化し、CSLの名称・別名と完全一致で照合します。別表記を見落とす可能性があり、取引の許可判定にはなりません。'],
    destination_imports:[
      'Sum monthly imports reported by the destination from all partners for the selected HS codes over the latest available 12 months. Import statistics differ from Korean exports and WSTS billings; reporting may lag.',
      '按所选HS汇总目的国自全球伙伴进口的最新可得12个月数据。该进口统计不同于韩国出口和WSTS销售额，公布可能存在时滞。',
      '選択HSについて対象国が全取引相手から輸入した最新12か月の月別金額を集計します。韓国輸出・WSTS売上とは異なり、公表に遅延が生じます。'],
    korea_share:[
      'Import value from Korea divided by the destination’s imports from all partners over the same period, multiplied by 100.',
      '同一期间目的国自韩国进口额除以自全球进口总额，再乘以100。',
      '同期間の韓国産輸入額を全取引相手からの輸入総額で割り100倍します。'],
    growth_yoy:[
      'Latest comparable 12-month imports divided by the preceding 12-month imports, minus one; requires 24 months of comparable observations.',
      '最近可比12个月进口额除以前12个月进口额，减1；需要24个月的可比数据。',
      '比較可能な直近12か月の輸入額をその前の12か月で割り1を引きます。比較可能な24か月が必要です。'],
    growth_3m_yoy:[
      'Latest three months of imports divided by imports over the same three months one year earlier, minus one.',
      '最近三个月进口额除以去年同期三个月进口额，减1。',
      '直近3か月の輸入額を前年同3か月で割り1を引きます。'],
    cagr_3y:[
      'When complete monthly data are unavailable, use annual imports: (latest annual total / total three years earlier)^(1/3) − 1.',
      '月度数据不完整时使用年度进口额：（最新年度／三年前年度）^(1/3) − 1。',
      '月次データが不足する場合は年次輸入額を使用し、（最新年／3年前）^(1/3)−1を算出します。'],
    korea_exports_to_destination:[
      'Sum monthly Korean Customs exports to the destination for the analyzed HS10 codes within the selected HS6 group. Korean export statistics have different reporting conventions from destination-country imports.',
      '将所选HS6下各HS10的韩国对目的国月度出口额汇总。韩国出口与目的国进口统计的口径可能不同。',
      '選択HS6内のHS10について、韓国税関の対象国向け月別輸出額を合計します。相手国の輸入統計とは集計基準が異なります。'],
    wsts:[
      'Use the WSTS monthly billings sheet for global and regional semiconductor sales. The published series measures industry revenue, not the destination’s imports or the company’s export value.',
      '使用WSTS月度销售额工作表中的全球与区域半导体销售额。它衡量行业收入，而非目的国进口额或本企业出口额。',
      'WSTSの月別売上シートから世界・地域別の半導体売上を取得します。産業売上であり、輸出先の輸入額や自社輸出額ではありません。'],
    company_exports:[
      'Sum valid company export rows for the selected product and destination; exclude canceled, duplicate and incomplete records. Months without transactions remain missing, not zero. Fictional company data.',
      '按所选产品及目的国汇总有效企业出口记录，排除取消、重复及关键字段缺失的记录。无交易月份标记缺失，不计为零。虚构企业数据。',
      '選択製品・輸出先の有効な企業輸出行を合計し、取消・重複・必須項目欠損を除外します。取引のない月はゼロではなく欠損です。架空データ。'],
    trade_unit_price:[
      'Total export value divided by total export net weight in kg over the latest 12 months; monthly values use the same ratio. This statistical unit value is not a product selling price.',
      '最近12个月出口总额除以出口净重（公斤）；月度单价采用相同计算方法。统计单价不是实际产品售价。',
      '直近12か月の輸出総額を輸出正味重量（kg）で割ります。月別単価も同様です。統計単価は実際の製品販売価額ではありません。'],
    company_unit_price:[
      'For valid company rows with both value and net weight, divide export value by net weight. Exclude missing product IDs or weights. Fictional statistical unit values are not contracted selling prices.',
      '对出口额和净重齐全的有效企业记录，以金额除以净重。排除产品ID或重量缺失记录。虚构统计单价并非合同售价。',
      '金額と正味重量のある企業実績行について金額÷重量を計算し、製品IDや重量の欠損を除外します。架空統計単価であり契約販売価額ではありません。'],
    baseline_unit_price:[
      'For the same source, HS classification and 12-month period, divide destination export unit value by Korea’s all-destination export unit value and multiply by 100. Compare statistical values, not actual selling prices.',
      '在数据源、HS分类和12个月期间一致的前提下，以目的国出口单价除以韩国全球出口单价并乘以100。仅比较统计单价，而非实际售价。',
      '同じ出典・HS・12か月について対象国向け輸出単価÷韓国の全輸出先向け単価×100を計算します。実際の販売価額の比較ではありません。'],
    tariff_reference:[
      'Present WTO tariff measures by effective date and HS6, using the reported available rate as an indicative reference. It is not the confirmed tariff for a specific shipment.',
      '按生效日期和HS6展示WTO关税措施，以可得税率作为参考，不能视为具体货物的最终适用税率。',
      'WTOの関税措置を適用日・HS6別に表示し、利用可能な税率を参考値とします。個別貨物の確定税率ではありません。'],
    fx_reference:[
      'Show the Export–Import Bank of Korea reference rate; build the historical KRW/USD trend from Federal Reserve daily rates and monthly averages. The company’s actual settlement rate may differ.',
      '展示韩国进出口银行参考汇率；历史韩元／美元走势采用美联储日度汇率及月度平均值。企业实际结算汇率可能不同。',
      '韓国輸出入銀行の参考レートを表示し、FRBの日次レートからKRW/USDの月平均推移を作成します。実際の企業決済レートとは異なる場合があります。'],
    price_index:[
      'Use the published export price index for computers, electronic and optical products and its monthly and yearly changes. This broad index does not represent the price of an individual semiconductor.',
      '采用已发布的计算机、电子及光学产品出口价格指数及其环比、同比变化。该广义指数不代表单个半导体产品价格。',
      '公表されたコンピュータ・電子・光学製品の輸出物価指数と前月比・前年比を使用します。個別半導体の価格ではありません。'],
    freight_reference:[
      'Use published monthly sea-export, sea-import and air-import transport cost tables by destination route and stated units. Air-import costs are not quotes for Korean air exports.',
      '按目的国航线和公布单位使用海运出口、海运进口及航空进口运费月度表。航空进口费用不是韩国航空出口报价。',
      '公表された海上輸出・海上輸入・航空輸入の月別費用表を航路・単位別に使用します。航空輸入費用は韓国発航空輸出の見積ではありません。'],
    cargo_flights:[
      'Count weekly Incheon cargo flights whose paired airport is in the destination country, mapping airport codes to countries. Flight listings do not prove shipment capacity, a direct route or delivery time for semiconductors.',
      '统计每周仁川机场往返目的国机场的货运航班，并将机场代码映射到国家。航班列表不证明半导体运力、直达航线或交付时间。',
      '相手空港の国コードが輸出先と一致する仁川の週次貨物便を集計します。便の記録は半導体の輸送枠、直行便や納期の保証ではありません。'],
    flight_counts:[
      'Use Incheon Airport’s monthly country-level cargo-aircraft departures and arrivals. A month not listed is missing data, not zero flights.',
      '采用仁川机场按国家统计的货机月度起降次数。未列出的月份视为数据缺失，而非零航班。',
      '仁川空港の国別月間貨物機発着便数を使用します。統計にない月はゼロではなくデータ欠損です。'],
    vessel_records:[
      'Count Busan port reports where the prior or next port is in the destination country. Port movements do not establish cargo type or available transport capacity.',
      '统计釜山港申报中前一港或下一港位于目的国的船舶记录。港口动态不证明货物品类或实际可用运力。',
      '前港または次港が輸出先にある釜山港の入出港申告を集計します。港湾記録は貨物品目や輸送枠を確定しません。'],
    delivery_ontime:[
      'Among records with scheduled and actual arrival dates, count arrivals on or before schedule; exclude inconsistent dates. Historical fictional company performance is not a delivery guarantee.',
      '在预计及实际到达日期齐全的记录中，统计按时或提前到达的比例，排除日期异常记录。虚构企业历史业绩不保证未来交付。',
      '予定・実到着日のある記録から予定日以前の到着率を計算し、日付異常を除外します。架空企業の過去実績であり納期を保証しません。'],
    lead_time:[
      'For each transport mode, average actual arrival date minus shipment date and show observed minimum and maximum. Planned lead time is scheduled arrival minus shipment date; this is not a delivery forecast.',
      '按运输方式计算实际到达日减发货日的平均值及最小、最大值；计划交付周期为预计到达日减发货日。不是未来交期预测。',
      '輸送手段別に実到着日－出荷日の平均・最小・最大を算出します。計画リードタイムは予定到着日－出荷日であり、将来の納期予測ではありません。'],
    freight_ratio:[
      'Sum freight charges on matched shipment records and divide by linked export value; per-kg freight by mode is supplementary. Fictional charges are assumptions, not actual quotes.',
      '汇总与出口记录关联的运费，除以对应出口额；按运输方式计算的每公斤运费仅供辅助参考。虚构运费为假设，并非实际报价。',
      '輸出実績に対応する運賃合計を関連輸出額で割ります。輸送手段別kg運賃は補助指標です。架空運賃は仮定であり見積ではありません。'],
    shipments_monthly:[
      'Count valid export records linked to logistics rows by transaction ID, month and transport mode. Missing months are not filled with zero. Fictional company data.',
      '按交易ID关联有效出口与物流记录，并按月份和运输方式统计。缺失月份不填零。虚构企业数据。',
      '取引IDで有効な輸出実績と物流記録を結び付け、月・輸送手段別に数えます。欠損月をゼロで埋めません。架空企業データです。'],
    recent_shipments:[
      'Show the latest shipment records by shipping date, with status derived from actual versus scheduled arrival. This does not certify direct routes, transit time or capacity.',
      '按发货日期展示最近运输记录，根据实际与预计到达日期比较状态。不能据此保证直达航线、运输时间或舱位。',
      '出荷日順に最近の出荷記録を表示し、実到着日と予定到着日で状態を比較します。直行ルート、所要時間や積載枠は保証しません。'],
    query_conditions:[
      'Count matched valid shipping records by transport mode, origin code and destination code. Airports use IATA codes and ports use UN/LOCODE; counts do not guarantee actual routing or available transport.',
      '按运输方式、起点和终点代码统计关联的有效出货记录。机场采用IATA，港口采用UN/LOCODE；数量不保证实际线路或可用运力。',
      '対応する有効出荷記録を輸送手段・出発地・到着地コード別に集計します。空港はIATA、港湾はUN/LOCODEで、実際の経路や輸送枠の保証ではありません。'],
    destination_monthly_imports:[
      'Show destination-country monthly imports for the analyzed HS set; calculate month-on-month changes only where adjacent months both have observations.',
      '展示目的国所分析HS组合的月度进口额；仅在相邻两个月都有数据时计算环比。',
      '分析対象HSの輸出先月別輸入額を表示し、連続する2か月のデータが揃う場合のみ前月比を算出します。'],
    cv:[
      'Population standard deviation divided by the mean of monthly imports over the available 24-month window. Historical volatility is not a future loss or export-failure probability.',
      '最近可得24个月进口额的总体标准差除以平均值。历史波动不代表未来损失或出口失败概率。',
      '利用可能な24か月の月別輸入額について母標準偏差÷平均を計算します。過去変動は将来の損失や輸出失敗確率ではありません。'],
    sharp_drops:[
      'Count comparable consecutive months in which imports fell by at least 20% month on month during the selected observation window.',
      '在所选观察期内统计可比连续月份中进口额环比下降20%以上的次数。',
      '観測期間の比較可能な連続月について、輸入額が前月比20%以上減少した回数を数えます。'],
    company_export_volatility:[
      'Use the population standard deviation of observed monthly company export totals divided by the mean. Month-on-month changes require both months; missing months are excluded, not treated as zero. Fictional historical data.',
      '以企业有数据月份的月度出口额总体标准差除以均值。环比计算要求相邻两个月均有数据；缺失月份排除而非填零。虚构历史数据。',
      'データのある月の企業輸出総額について母標準偏差÷平均を算出します。前月比は両月の観測がある場合のみ計算し、欠損月をゼロ扱いしません。架空の過去データです。'],
    fx_volatility:[
      'Average the absolute month-on-month changes in monthly exchange-rate averages and compare with a rolling historical distribution. Past volatility is not a forecast.',
      '对月平均汇率的环比绝对变动率求平均，并与滚动历史分布比较。历史波动并非预测。',
      '月平均為替レートの前月比絶対値を平均し、過去の移動分布と比較します。過去の変動は予測ではありません。'],
    wsts_volatility:[
      'For global and regional WSTS billings, average absolute month-on-month changes across the recent 13 months and count declines of 20% or more. Industry sales are not destination imports.',
      '对最近13个月WSTS全球及区域销售额求环比绝对变动率平均值，并统计下降20%以上的次数。行业销售额不等于目的国进口额。',
      '直近13か月のWSTS世界・地域別売上について前月比絶対値を平均し、20%以上の減少回数を数えます。産業売上は輸出先の輸入額ではありません。']
  };
  function itemNote(it, lang){
    if(!lang || lang==='ko' || !itemNotes[it.key]) return [it.basis,it.note].filter(Boolean).join(' / ')||'—';
    const note=itemNotes[it.key][languages.indexOf(lang)-1];
    // Quantitative observations are already displayed in the value and date columns;
    // preserve source file and unique raw methodology in the unmodified JSON dataset.
    return note;
  }

  window.AXPORTReportL10n = Object.freeze({translate, translateHTML, localizeDialog, itemNote, scenario: (lang)=>scenario[lang]||scenario.ko, dictionary});
})();
