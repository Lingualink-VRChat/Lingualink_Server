import fastapi
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool # For running sync I/O-bound code
import os
import tempfile
from werkzeug.utils import secure_filename # Still useful for filename sanitization
from typing import Optional, List
import logging

# Import from omni_llm_service (assuming it's in the same directory or PYTHONPATH)
from omni_llm_service import process_audio_with_omni, generate_system_prompt, DEFAULT_USER_QUERY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

MAX_UPLOAD_SIZE = 16 * 1024 * 1024  # 16 MB upload limit
ALLOWED_EXTENSIONS = {'wav'} # Add more if your omni model supports them

def allowed_file(filename: str) -> bool:
    """Checks if the filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.post("/translate_audio")
async def translate_audio_endpoint(
    audio_file: UploadFile = File(...),
    user_prompt: str = Form(DEFAULT_USER_QUERY), # Changed Optional[str] to str with default, matches Flask's get with default
    target_languages: Optional[List[str]] = Form(None) # e.g., client sends target_languages=英文&target_languages=日文
):
    # FastAPI's File(...) ensures 'audio_file' part exists.
    logger.info(f"Received request params: filename={audio_file.filename}, user_prompt={user_prompt}, target_languages={target_languages}")
    # We need to check if a file was actually selected (filename is not empty).
    if not audio_file.filename:
        # This case handles if an empty file part is sent, though FastAPI might catch some earlier.
        # Original Flask returned: {"status": "error", "message": "No selected file"}, 400
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "No selected file"}
        )

    if not allowed_file(audio_file.filename):
        # Original Flask returned: {"status": "error", "message": "File type not allowed"}, 400
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "File type not allowed"}
        )

    filename = secure_filename(audio_file.filename) # Good practice
    temp_file_path: Optional[str] = None # Initialize to ensure it exists in finally block

    try:
        # Read file content and check size
        contents = await audio_file.read()
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413, # Request Entity Too Large
                detail={"status": "error", "message": f"File too large. Maximum {MAX_UPLOAD_SIZE // (1024*1024)}MB allowed."}
            )

        # Save uploaded content to a temporary file
        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="upload_") as temp_f:
            temp_f.write(contents)
            temp_file_path = temp_f.name
        
        logger.info(f"Audio file saved temporarily to: {temp_file_path}")

        # --- Process target languages from form data ---
        # target_languages is now Optional[List[str]] directly from the Form.
        # We should clean it up: strip whitespace and filter out any empty or non-string entries.
        final_target_languages: Optional[List[str]] = None
        if target_languages:
            cleaned_languages = [
                lang.strip() for lang in target_languages 
                if isinstance(lang, str) and lang.strip()
            ]
            if cleaned_languages: # If list is not empty after cleaning
                final_target_languages = cleaned_languages
        
        # Generate system prompt based on target languages (or default if none provided/empty after clean)
        system_prompt = generate_system_prompt(final_target_languages)
        logger.info(f"Using system prompt: {system_prompt}")
        
        # Process the audio file using the synchronous function in a thread pool
        result = await run_in_threadpool(
            process_audio_with_omni,
            temp_file_path,
            system_prompt,
            user_prompt
        )
        
        # The original Flask app returned the 'result' dict directly from process_audio_with_omni,
        # which means an HTTP 200 OK even if result["status"] == "error".
        # We replicate this behavior.
        if isinstance(result, dict) and result.get("status") == "error":
            logger.warning(
                f"omni_llm_service reported an error: {result.get('message')}. "
                f"Details: {result.get('details')}"
            )
        
        # FastAPI automatically converts dicts to JSONResponse with a 200 status code by default.
        logger.info(f"Response to client: {result}")
        return result

    except HTTPException as http_exc:
        # Re-raise HTTPException so FastAPI handles it
        logger.info(f"Response to client (HTTPException): {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # This catches unexpected errors in the endpoint logic itself.
        logger.error(f"Error processing file: {e}", exc_info=True)
        error_content = {"status": "error", "message": f"Internal server error: {str(e)}"}
        logger.info(f"Response to client (internal error): {error_content}")
        return JSONResponse(
            status_code=500,
            content=error_content
        )
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary file {temp_file_path} deleted.")
            except Exception as e_del:
                logger.error(f"Error deleting temporary file {temp_file_path}: {e_del}", exc_info=True)
        
        # It's good practice to close the UploadFile object
        if audio_file:
            await audio_file.close()

# To run this FastAPI application:
# 1. Make sure you have FastAPI and Uvicorn installed:
#    pip install fastapi uvicorn[standard] python-multipart werkzeug
# 2. Save this code as app.py in your project directory.
# 3. Run from the terminal in your project directory:
#    uvicorn app:app --reload --host 0.0.0.0 --port 5000
#
# The `omni_llm_service.py` file should be in the same directory or accessible via PYTHONPATH.