# gcp-ocr-exp

## Directory Structure

```
gcp-ocr-exp/
├── src/
│   ├── processors/
│   │   ├── __init__.py
│   │   └── vision_processor.py       # Google Cloud Vision API
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── gcp_utils.py              # GCP初期化用
│   │   ├── aws_utils.py              # AWS初期化用
│   │   └── pdf_utils.py              # PDF処理用
│   ├── generative/                   # 生成AI関連
│   │   ├── base/
│   │   │   ├── __init__.py
│   │   │   └── llm_base.py           # 基底クラス（共通）
│   │   ├── gcp/
│   │   │   ├── __init__.py
│   │   │   ├── gemini.py             # Gemini実装クラス
│   │   │   ├── vertex_utils.py       # VertexAI関連のユーティリティ
│   │   │   └── prompt_utils.py       # Gemini最適化プロンプト
│   │   ├── aws/
│   │   │   ├── __init__.py
│   │   │   ├── claude.py             # Claude実装クラス
│   │   │   ├── bedrock_utils.py      # Bedrock関連のユーティリティ
│   │   │   └── prompt_utils.py       # Claude最適化プロンプト
│   │   └── factory.py                # LLMファクトリー
│   └── main.py                       # エントリーポイント
├── config/
│   └── settings.py                   # 環境変数の設定
├── data/
│   ├── input/                        # 入力PDFファイル用
│   │   └── test.pdf                  # テスト用PDFファイル
│   └── output/                       # 処理結果出力用
│       ├── vision/
│       │   └── vision_results_*.json # Vision API出力結果
│       ├── gemini/
│       │   └── gemini_summary_*.json # Gemini 要約結果
│       └── audit_log.jsonl
├── logs/
│   └── app.log                       # アプリケーションログ
├── test_vision_api.py                # Vision APIテスト実行ファイル
├── test_gemini.py                    # Vertex AI APIテスト実行ファイル
├── requirements.txt
├── .env                              # 環境変数設定ファイル
├── .gitignore
└── README.md                         # This file
```
