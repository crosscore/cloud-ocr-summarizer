import glob
import os
from datetime import datetime

from src.utils.token_counter import TokenCounter

def find_latest_vision_results_file(folder_path):
    """
    Finds the latest JSON file starting with 'vision_results' in the specified folder.

    Args:
        folder_path (str): The path to the folder to search.

    Returns:
        str or None: The path to the latest JSON file, or None if not found.
    """
    files = glob.glob(os.path.join(folder_path, "vision_results*.json"))
    print(f"Found files matching pattern: {files}")
    if not files:
        return None

    latest_file = None
    latest_datetime = None

    for file in files:
        try:
            base_name = os.path.splitext(os.path.basename(file))[0]
            date_str = base_name.split("_")[2:4]

            if len(date_str) != 2:
                print(f"Skipping file due to invalid date format: {file}")
                continue

            date_time = datetime.strptime("_".join(date_str), "%Y%m%d_%H%M%S")

            if latest_datetime is None or date_time > latest_datetime:
                latest_datetime = date_time
                latest_file = file

        except (ValueError, IndexError) as e:
            print(f"Error extracting date from file: {file}")
            print(f"  Exception: {e}")
            print(f"  Date string: {'_'.join(date_str if 'date_str' in locals() else [])}")
            continue

    return latest_file

folder_path = "./data/output/vision"

latest_json_file_path = find_latest_vision_results_file(folder_path)

if latest_json_file_path:
    tokens = TokenCounter.count_json_tokens(latest_json_file_path)
    stats = TokenCounter.count_json_file(latest_json_file_path)

    print(f"Latest JSON file: {latest_json_file_path}")
    print(f"Total tokens in JSON data: {tokens}")
    print(f"Token statistics: {stats}")
else:
    print(f"No 'vision_results*.json' file found in '{folder_path}'.")
    print("Files in the folder:")
    for file in glob.glob(os.path.join(folder_path, "*")):
        print(file)
