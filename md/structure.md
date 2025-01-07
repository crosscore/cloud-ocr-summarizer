```
gcp-ocr-exp/
├── src/
│   ├── processors/
│   │   ├── __init__.py
│   │   └── vision_processor.py     # Google Cloud Vision API
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── gcp_utils.py            # GCP関連のユーティリティ
│   │   └── pdf_utils.py            # PDF処理用ユーティリティ
│   └── main.py                     # エントリーポイント
├── tests/
│   ├── __init__.py
│   └── vision_test.py              # Vision API統合テスト
├── config/
│   └── settings.py                 # 設定 - GCP認証情報/環境変数
├── data/
│   ├── input/                      # 入力PDFファイル用
│   │   └── test.pdf                # テスト用PDFファイル
│   └── output/                     # 処理結果出力用
│       ├── vision_results_*.json   # Vision API解析結果
│       └── audit_log.jsonl         # 監査ログ
├── logs/
│   └── app.log                     # アプリケーションログ
├── vision_api_test.py              # Vision APIテスト実行ファイル
├── requirements.txt
├── README.md
├── .gitignore
└── .env                            # 環境変数設定ファイル
```
