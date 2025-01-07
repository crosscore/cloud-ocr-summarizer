```
gcp-ocr-exp/
├── src/
│   ├── processors/
│   │   ├── __init__.py
│   │   └── vision_processor.py        # Google Cloud Vision APIの実装
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── gcp_utils.py              # GCP関連のユーティリティ関数
│   │   └── pdf_utils.py              # PDF処理用ユーティリティ
│   └── main.py                       # アプリケーションのエントリーポイント
├── tests/
│   ├── __init__.py
│   └── vision_test.py                # Vision API統合テスト
├── config/
│   └── settings.py                   # 設定ファイル (GCP認証情報、環境変数)
├── data/
│   ├── input/                        # 入力PDFファイル用
│   │   └── test.pdf                  # テスト用PDFファイル
│   └── output/                       # 処理結果出力用
│       ├── vision_results_*.json     # Vision API解析結果
│       └── audit_log.jsonl           # 監査ログ
├── logs/
│   └── app.log                       # アプリケーションログ
├── credentials/
│   └── gcp-service-account.json      # GCPサービスアカウントキー
├── requirements.txt                  # 依存パッケージリスト
├── README.md                         # プロジェクトの説明
├── .gitignore                        # Git除外設定
└── .env                              # 環境変数設定ファイル（非Git管理）
```
