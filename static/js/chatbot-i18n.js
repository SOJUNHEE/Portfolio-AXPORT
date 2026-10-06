// Chat-only language resources. Chinese uses Simplified Chinese.
(() => {
  const catalog = {
  "ko": {
    "ui": {
      "preview": "예시 응답 · AI 미연결",
      "greeting": "안녕하세요! AXPORT AI입니다.",
      "help": "무엇을 도와드릴까요?",
      "hint": "이용 방법과 분석 결과, 궁금한 점을 물어보세요.",
      "minimize": "대화 유지하고 접기",
      "close": "대화 종료 및 초기화",
      "open": "AXPORT AI 대화 열기",
      "restore": "AXPORT AI 대화 복원",
      "resize": "대화창 크기 조절: 방향키 사용",
      "resizeHint": "드래그 또는 방향키로 크기 조절",
      "body": "대화 내용",
      "suggestions": "추천 질문",
      "input": "질문 입력",
      "placeholder": "궁금한 점을 입력하세요",
      "send": "전송",
      "sendLabel": "질문 전송",
      "loading": "답변을 준비하고 있어요",
      "error": "답변을 불러오지 못했어요. 다시 시도해 주세요.",
      "retry": "다시 시도",
      "replyLabel": "AXPORT AI · 예시 응답",
      "failed": "답변 오류. 다시 시도할 수 있습니다.",
      "arrived": "예시 답변이 도착했습니다.",
      "latest": "새 답변 보기 ↓",
      "badge": "새 답변",
      "language": "대화 언어"
    },
    "questions": {
      "home": [
        "AXPORT는 어떤 서비스인가요?",
        "AXPORT는 어떻게 이용하나요?",
        "AXPORT를 어떻게 활용할 수 있나요?"
      ],
      "workspace": [
        "5개 평가 영역은 각각 무엇을 의미하나요?",
        "가중치는 어떻게 변경하나요?",
        "분석 결과의 근거는 어디서 확인하나요?"
      ]
    },
    "answers": [
      "AXPORT는 기업 데이터와 HS 코드를 바탕으로 수출적합도와 판단 근거를 살펴보도록 기획된 서비스입니다. 현재는 홈과 데스크톱형 대시보드의 사용 흐름을 확인하는 프로토타입입니다. 실제 엑셀 분석이나 수출 판정은 연결되지 않았습니다.",
      "1. 홈의 ‘대시보드 시작’으로 작업공간을 여세요.\n2. ‘새 분석 만들기’ 또는 Dock의 + 버튼에서 파일을 선택하거나 샘플 파일을 사용하세요.\n3. 기업명·HS 코드·대상국을 입력하고 ‘분석 화면 보기’를 누르세요.\n4. 5개 영역 요약과 책갈피 탭을 둘러보세요.\n현재 파일명·크기만 사용하며 파일 내용은 읽거나 서버에 전송하지 않습니다. 결과는 예시입니다.",
      "수출 검토에 필요한 정보를 어떤 관점으로 정리할지 살펴보거나, 팀과 함께 시장성·가격·물류·안정성의 중요도를 논의하는 화면 시연에 활용할 수 있습니다. 탭별 근거와 보고서 구성을 미리 검토하는 용도로도 사용할 수 있습니다. 현재 예시 점수는 실제 수출 의사결정이나 규제 판단의 근거로 사용할 수 없습니다.",
      "규제: 수출규제·허가 등 필수 조건을 검토하는 별도 관문입니다.\n시장성: 시장규모와 성장률입니다.\n가격: 관세와 환율입니다.\n물류: 운송 조건입니다.\n안정성: 지표의 변동률입니다.\n현재 수치와 차트는 UI 예시이며 세부 채점 기준과 실제 자료는 연결되지 않았습니다. 규제 관문은 다른 영역의 가중치로 해제되지 않습니다.",
      "분석 창의 ‘가중치 설정’을 열어 항목별 비율을 조절한 뒤 ‘설정 적용’을 누르세요. 합계는 100%여야 하며 ‘기본값 복원’으로 되돌릴 수 있습니다. 규제 관문은 별도입니다. 현재 가중치는 UI 예시이며 변경해도 예시 점수가 재계산되지는 않습니다.",
      "분석 창 오른쪽 책갈피에서 규제·시장성·가격·물류·안정성을 선택하세요. 좁은 화면에서는 하단 탭으로 전환됩니다. 각 화면의 차트·표·설명을 확인할 수 있지만 현재는 예시 자료입니다. ‘보고서 내보내기’에서 예시 보고서를 미리 보거나 HTML로 다운로드할 수 있습니다. 실제 법령·관세 출처와 판정 근거는 미연결입니다."
    ],
    "fallback": "현재는 실제 AI가 연결되지 않은 프론트엔드 예시입니다. 질문은 외부로 전송되지 않으며 실제 분석 데이터 조회나 개별 질문에 대한 AI 답변은 제공하지 않습니다. 서비스 소개, 이용 절차, 평가 영역과 가중치·근거 화면 안내를 확인할 수 있습니다."
  },
  "en": {
    "ui": {
      "preview": "Demo responses · AI not connected",
      "greeting": "Hello! I’m AXPORT AI.",
      "help": "How can I help you?",
      "hint": "Ask about using AXPORT or understanding analysis results.",
      "minimize": "Minimize and keep conversation",
      "close": "End and reset conversation",
      "open": "Open AXPORT AI chat",
      "restore": "Restore AXPORT AI chat",
      "resize": "Resize chat: use arrow keys",
      "resizeHint": "Drag or use arrow keys to resize",
      "body": "Conversation",
      "suggestions": "Suggested questions",
      "input": "Your question",
      "placeholder": "Type your question",
      "send": "Send",
      "sendLabel": "Send question",
      "loading": "Preparing your response",
      "error": "Could not load the response. Please try again.",
      "retry": "Try again",
      "replyLabel": "AXPORT AI · Demo response",
      "failed": "Response failed. You can try again.",
      "arrived": "A demo response has arrived.",
      "latest": "View new response ↓",
      "badge": "New reply",
      "language": "Chat language"
    },
    "questions": {
      "home": [
        "What is AXPORT?",
        "How do I use AXPORT?",
        "What can I use AXPORT for?"
      ],
      "workspace": [
        "What do the five assessment areas mean?",
        "How do I change the weights?",
        "Where can I find the supporting evidence?"
      ]
    },
    "answers": [
      "AXPORT is designed to help companies review export suitability and supporting evidence using company data and HS codes. The current version is a prototype of the home page and desktop-style dashboard. Actual Excel analysis and export assessments are not connected.",
      "1. Open the workspace using “Open AXPORT” on the home page.\n2. Choose “New analysis” or the + button in the Dock to select a file or use the sample file.\n3. Enter a company name, HS code and destination, then select “View analysis”.\n4. Explore the five-area summary and evidence tabs.\nThe current prototype only uses file names and sizes. It does not read or upload file contents. Results are examples.",
      "Use the prototype to explore how export-review information can be organized, discuss the relative importance of market potential, pricing, logistics and stability with your team, or review the evidence tabs and report layout. The example scores cannot support real export decisions or regulatory assessments.",
      "Regulation: a separate gate for mandatory export-control and licensing conditions.\nMarket potential: market size and growth.\nPricing: tariffs and exchange rates.\nLogistics: transport conditions.\nStability: variability of indicators.\nCurrent numbers and charts are UI examples. Detailed scoring rules and real data are not connected. Changing other weights cannot remove the regulatory gate.",
      "Open “Set weights” in the analysis window, adjust the percentages and choose “Apply settings”. The total must be 100%. “Restore defaults” restores the defaults. Regulation is a separate gate. These weights are UI examples; changing them does not recalculate the example scores.",
      "Use the tabs on the right of the analysis window to select regulation, market potential, pricing, logistics or stability. On narrow screens, the tabs move to the bottom. Charts, tables and explanations currently contain examples. “Export report” opens the example report preview and HTML download. Actual legal and tariff sources and assessment evidence are not connected."
    ],
    "fallback": "This is a frontend demo with no AI connected. Your question is not sent externally. Actual analysis data and AI-generated answers are not available. You can preview guidance about the service, its workflow, assessment areas, weights and evidence screens."
  },
  "zh-CN": {
    "ui": {
      "preview": "示例回复 · 未连接 AI",
      "greeting": "您好！我是 AXPORT AI。",
      "help": "有什么可以帮您？",
      "hint": "欢迎咨询使用方法和分析结果。",
      "minimize": "最小化并保留对话",
      "close": "结束并重置对话",
      "open": "打开 AXPORT AI 对话",
      "restore": "恢复 AXPORT AI 对话",
      "resize": "调整对话窗口大小：使用方向键",
      "resizeHint": "拖动或使用方向键调整大小",
      "body": "对话内容",
      "suggestions": "推荐问题",
      "input": "输入问题",
      "placeholder": "请输入您的问题",
      "send": "发送",
      "sendLabel": "发送问题",
      "loading": "正在准备回复",
      "error": "无法加载回复，请重试。",
      "retry": "重试",
      "replyLabel": "AXPORT AI · 示例回复",
      "failed": "回复失败，您可以重试。",
      "arrived": "收到一条示例回复。",
      "latest": "查看新回复 ↓",
      "badge": "新回复",
      "language": "对话语言"
    },
    "questions": {
      "home": [
        "AXPORT 是什么服务？",
        "如何使用 AXPORT？",
        "AXPORT 可以用于哪些场景？"
      ],
      "workspace": [
        "五个评估领域分别代表什么？",
        "如何调整权重？",
        "在哪里查看分析结果的依据？"
      ]
    },
    "answers": [
      "AXPORT 旨在帮助企业根据企业数据和 HS 编码查看出口适合度及判断依据。目前是展示首页和桌面式仪表板操作流程的原型，尚未连接实际 Excel 内容分析或出口评估功能。",
      "1. 在首页点击“打开 AXPORT”，进入工作区。\n2. 点击“新建分析”或 Dock 中的 + 按钮，选择文件或使用示例文件。\n3. 输入企业名称、HS 编码和目的国，点击“查看分析”。\n4. 浏览五个领域的概览和依据标签页。\n目前只使用文件名和大小，不读取或上传文件内容。结果均为示例。",
      "您可以通过原型了解如何整理出口审查信息，与团队讨论市场、价格、物流和稳定性的重要程度，或预览依据标签页与报告布局。目前的示例分数不能作为实际出口决策或监管判断的依据。",
      "监管：出口管制、许可等必要条件的独立关卡。\n市场：市场规模和增长率。\n价格：关税和汇率。\n物流：运输条件。\n稳定性：指标的波动情况。\n当前数值和图表均为界面示例，详细评分规则与实际数据尚未连接。调整其他领域的权重不能解除监管关卡。",
      "在分析窗口打开“设置权重”，调整各项比例后点击“应用设置”。合计必须为 100%，点击“恢复默认值”可恢复默认值。监管关卡独立处理。目前权重仅用于界面演示，修改后不会重新计算示例分数。",
      "在分析窗口右侧的标签页中选择监管、市场、价格、物流或稳定性。窄屏时标签页位于底部。可以查看图表、表格和说明，但目前均为示例。点击“导出报告”可预览示例报告或下载 HTML。实际法规、关税来源和评估依据尚未连接。"
    ],
    "fallback": "这是尚未连接实际 AI 的前端示例。您的问题不会发送到外部，也不会查询实际分析数据或生成 AI 回答。您可以预览服务介绍、使用流程、评估领域、权重与依据页面的说明。"
  },
  "ja": {
    "ui": {
      "preview": "サンプル回答 · AI未接続",
      "greeting": "こんにちは！AXPORT AIです。",
      "help": "どのようなご用件でしょうか？",
      "hint": "使い方や分析結果について、お気軽にご質問ください。",
      "minimize": "会話を保持して最小化",
      "close": "会話を終了してリセット",
      "open": "AXPORT AIのチャットを開く",
      "restore": "AXPORT AIのチャットを再表示",
      "resize": "チャットのサイズ変更：矢印キーを使用",
      "resizeHint": "ドラッグまたは矢印キーでサイズ変更",
      "body": "会話内容",
      "suggestions": "おすすめの質問",
      "input": "質問を入力",
      "placeholder": "質問を入力してください",
      "send": "送信",
      "sendLabel": "質問を送信",
      "loading": "回答を準備しています",
      "error": "回答を読み込めませんでした。もう一度お試しください。",
      "retry": "再試行",
      "replyLabel": "AXPORT AI · サンプル回答",
      "failed": "回答に失敗しました。再試行できます。",
      "arrived": "サンプル回答が届きました。",
      "latest": "新しい回答を見る ↓",
      "badge": "新着回答",
      "language": "会話の言語"
    },
    "questions": {
      "home": [
        "AXPORTはどのようなサービスですか？",
        "AXPORTの使い方を教えてください。",
        "AXPORTはどのような場面で活用できますか？"
      ],
      "workspace": [
        "5つの評価分野はそれぞれ何を意味しますか？",
        "重み付けはどこで変更できますか？",
        "分析結果の根拠はどこで確認できますか？"
      ]
    },
    "answers": [
      "AXPORTは、企業データとHSコードをもとに輸出適合度と判断根拠を確認するためのサービスとして企画されています。現在はホーム画面とデスクトップ型ダッシュボードの操作を確認するプロトタイプです。実際のExcel分析や輸出判定は接続されていません。",
      "1. ホームの「AXPORT を開く」からワークスペースを開きます。\n2. 「新規分析」またはDockの＋ボタンでファイルを選ぶか、サンプルを使用します。\n3. 企業名・HSコード・仕向国を入力し、「分析画面を見る」を押します。\n4. 5分野の概要と根拠タブを確認します。\n現在はファイル名とサイズのみを使用し、内容の読み取りやアップロードは行いません。結果はサンプルです。",
      "輸出検討に必要な情報の整理方法を確認したり、市場性・価格・物流・安定性の重要度をチームで話し合ったりする画面デモに活用できます。根拠タブやレポート構成の事前確認にも使えます。サンプルの点数は、実際の輸出判断や規制判定の根拠にはできません。",
      "規制：輸出規制・許可などの必須条件を確認する独立した関門です。\n市場性：市場規模と成長率です。\n価格：関税と為替です。\n物流：輸送条件です。\n安定性：指標の変動です。\n現在の数値やグラフはUI用のサンプルで、詳細な採点基準と実データは未接続です。他分野の重みを変えても規制の関門は解除されません。",
      "分析ウィンドウの「重みを設定」で各項目の割合を調整し、「設定を適用」を押します。合計は100%にする必要があります。「初期値に戻す」で初期値に戻せます。規制の関門は別扱いです。現在の重みはUI用のサンプルで、変更してもサンプルの点数は再計算されません。",
      "分析ウィンドウ右側のタブで規制・市場性・価格・物流・安定性を選んでください。狭い画面では下部タブに切り替わります。グラフ・表・説明は現在サンプルです。「レポートを出力」からサンプルレポートのプレビューやHTMLのダウンロードができます。実際の法令・関税の出典や判定根拠は未接続です。"
    ],
    "fallback": "現在はAI未接続のフロントエンドデモです。質問は外部に送信されず、実際の分析データの参照やAI回答の生成も行いません。サービス概要、利用手順、評価分野、重み付けや根拠画面の案内を確認できます。"
  }
};
  function normalize(value) {
    const language = String(value || '').toLowerCase().replaceAll('_', '-').split('-')[0];
    return {ko:'ko', en:'en', zh:'zh-CN', ja:'ja'}[language] || 'ko';
  }
  window.AXPORTChatI18n = Object.freeze({ catalog, normalize });
})();
