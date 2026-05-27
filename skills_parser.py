import shutil
import json
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from pathlib import Path
import asyncio
from pydantic import BaseModel


from .ai_enhancer import perform_skill_gap_analysis
from .workers import process_resume_batch
from .config import UPLOAD_DIR

router = APIRouter()

@router.post("/upload/resumes/")
async def upload_multiple_resumes(
    background_tasks: BackgroundTasks,
    resumes: List[UploadFile] = File(...)
):
    """Accepts multiple resume uploads and processes them as a single batch."""
    
    saved_file_paths = []
    for file in resumes:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Collect the path of each saved file
        saved_file_paths.append(file_path)

    timestamp = int(time.time())
    batch_filename = f"batch_{timestamp}.json"    

    # Start only ONE background task for the entire batch
    background_tasks.add_task(process_resume_batch, saved_file_paths, batch_filename)

    return {
        "message": f"Received {len(saved_file_paths)} resumes. Batch processing started in the background.",
        "batch_id": batch_filename
    }
class JobDescriptionRequest(BaseModel):
    job_description: str

@router.post("/analyze/{batch_filename}")
async def analyze_batch(batch_filename: str, request: JobDescriptionRequest):
    """
    Analyzes a processed batch of resumes against a job description.
    """
    batch_file_path = UPLOAD_DIR / batch_filename
    
    if not batch_file_path.exists():
        return {"error": "Batch file not found."}

    # Read the data from the batch JSON file
    with open(batch_file_path, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    print("skill_gap_analysis started") 

    if request.job_description.strip():
        # 1. Create a list of tasks (coroutines)
        # Also, keep a reference to which candidate each task is for
        tasks_to_run = []
        candidates_with_skills = [] # We'll store the candidates that need analysis

        for candidate in batch_data:
            if "skills" in candidate:
                # Add the coroutine object to the task list
                tasks_to_run.append(
                    perform_skill_gap_analysis(
                        candidate_skills=candidate["skills"],
                        job_description=request.job_description
                    )
                )
                # Add the candidate to our reference list
                candidates_with_skills.append(candidate)
        
        # 2. Run all tasks in parallel
        if tasks_to_run:
            print(f"Running analysis for {len(tasks_to_run)} candidates in parallel...")
            
            # This waits for all API calls to finish
            # all_results will be a list of dictionaries (the JSON results)
            all_results = await asyncio.gather(*tasks_to_run)
            
            # 3. Assign the results back to the correct candidates
            # all_results and candidates_with_skills are in the same order
            for i, candidate in enumerate(candidates_with_skills):
                # Assign the dictionary (the result), not the task
                candidate["skill_gap_analysis"] = all_results[i]
        
        # --- END OF CORRECTED LOGIC ---

    print("skill_gap_analysis completed")    
    # Optional: Overwrite the file with the new, enriched data
    with open(batch_file_path, "w", encoding="utf-8") as f:
        json.dump(batch_data, f, indent=4)

    return batch_data    