# gcp-rag-exp

## Directory Structure
```
gcp-rag-exp/
├── src/
│   ├── processors/
│   │   ├── __init__.py
│   │   └── vision_processor.py     # Google Cloud Vision API
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── gcp_utils.py            # GCP初期化用
│   │   └── pdf_utils.py            # PDF処理用
│   └── main.py                     # エントリーポイント
├── tests/
│   ├── __init__.py
│   └── vision_test.py              # Vision API統合テスト
├── config/
│   └── settings.py                 # 環境変数の設定
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
├── .env                            # 環境変数設定ファイル
├── .gitignore
└── README.md                       # This file
```
