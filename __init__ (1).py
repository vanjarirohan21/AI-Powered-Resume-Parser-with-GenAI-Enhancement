import json
from pathlib import Path
from typing import List
import pymupdf

from .parsers import parse_resume_text
from .config import UPLOAD_DIR

def _process_single_resume(file_path: Path) -> dict:
    """
    Helper function to process one resume file.
    """
    try:
        # 1. Extract text
        text = ""
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text += page.get_text()

        # 2. Parse for structured data (name, email)
        structured_data = parse_resume_text(text)

        print(f"✅ Successfully processed {file_path.name}")
        return structured_data

    except Exception as e:
        print(f"❌ Failed to process {file_path.name}. Error: {e}")
        return {"filename": file_path.name, "error": str(e)}


def process_resume_batch(file_paths: List[Path], output_filename: str):
    """
    This is our new background worker. It processes a list of resumes
    and saves all results into a single JSON file.
    """
    print(f"⚙️  Processing a batch of {len(file_paths)} resumes...")
    
    all_results = []
    for file_path in file_paths:
        # Call the helper function for each file
        result = _process_single_resume(file_path)
        all_results.append(result)
        

    output_path = UPLOAD_DIR / output_filename

    # Save the list of all results to one file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)
        
    print(f" Batch processing complete. Results saved to {output_filename}")
