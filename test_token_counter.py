from src.utils.token_counter import TokenCounter

json_file_path = "./data/output/vision/vision_results_20250109_051748.json"

# JSONデータのトークン数カウント
tokens = TokenCounter.count_json_tokens(json_file_path)

# JSONファイルの詳細分析
stats = TokenCounter.count_json_file(json_file_path)

print(f"Total tokens in JSON data: {tokens}")
print(f"Token statistics: {stats}")
