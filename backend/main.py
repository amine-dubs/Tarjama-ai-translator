from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import shutil
import os
from transformers import pipeline, MarianMTModel, MarianTokenizer
import traceback # Ensure traceback is imported

# --- Configuration ---
# Determine the base directory of the main.py script
# This helps in locating templates and static files correctly, especially in Docker
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust paths to go one level up from backend to find templates/static
TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
UPLOAD_DIR = "/app/uploads" # Ensure this matches Dockerfile WORKDIR + uploads

app = FastAPI()

# --- Mount Static Files and Templates ---
# Ensure the static directory exists (FastAPI doesn't create it)
# We'll create it manually or via Docker later
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Ensure the templates directory exists (FastAPI doesn't create it)
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- Placeholder for Model Loading ---
# Initialize the translation pipeline (load the model)
# Consider loading the model on startup to avoid delays during requests

# Define model name
MODEL_NAME = "Helsinki-NLP/opus-mt-en-ar"
translator = None # Initialize translator as None

try:
    print("--- Loading Model ---") # Add a clear marker
    print(f"Loading tokenizer for {MODEL_NAME} using MarianTokenizer...")
    # Use MarianTokenizer directly
    tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
    print(f"Loading model for {MODEL_NAME} using MarianMTModel...")
    # Use MarianMTModel directly
    model = MarianMTModel.from_pretrained(MODEL_NAME)
    print(f"Initializing translation pipeline for {MODEL_NAME}...")
    # Pass the loaded objects to the pipeline
    translator = pipeline("translation", model=model, tokenizer=tokenizer)
    print("--- Model Loaded Successfully ---")
except Exception as e:
    print(f"--- ERROR Loading Model ---")
    print(f"Error loading model or tokenizer {MODEL_NAME}: {e}")
    traceback.print_exc() # Print full traceback for loading error
    # Keep translator as None

# --- Helper Functions ---
def translate_text_internal(text: str, source_lang: str, target_lang: str = "ar") -> str:
    """Internal function to handle text translation using the loaded model."""
    if translator is None:
        # If the model failed to load, raise an error instead of returning a placeholder
        raise HTTPException(status_code=503, detail="Translation service is unavailable (model not loaded).")

    # Log the request details
    print(f"Translation Request - Source Lang: {source_lang}, Target Lang: {target_lang}")
    print(f"Input Text: {text}")

    # --- Actual Translation Logic (using Hugging Face pipeline) ---
    try:
        # The Helsinki model expects the text directly
        result = translator(text)

        if result and isinstance(result, list) and 'translation_text' in result[0]:
            translated_text = result[0]['translation_text']
            print(f"Raw Translation Output: {translated_text}")
            # Return the actual translated text
            return translated_text
        else:
            print(f"Unexpected translation result format: {result}")
            raise HTTPException(status_code=500, detail="Translation failed: Unexpected model output format.")

    except Exception as e:
        print(f"Error during translation pipeline: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

# --- Function to extract text ---
async def extract_text_from_file(file: UploadFile) -> str:
    """Extracts text content from various file types."""
    # Ensure upload directory exists (though Dockerfile should create it)
    # Use os.makedirs for robustness
    os.makedirs(UPLOAD_DIR, exist_ok=True) # Ensure directory exists

    # Secure filename and define path
    # Use a temporary filename to avoid collisions and complex sanitization
    # Make sure the filename is safe for the filesystem
    safe_filename = os.path.basename(file.filename) # Basic safety
    temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{safe_filename}")
    print(f"Attempting to save uploaded file to: {temp_file_path}")
    extracted_text = "" # Initialize extracted_text

    try:
        # Save the uploaded file temporarily
        # Use async file writing if possible with a library like aiofiles,
        # but standard file I/O is often sufficient here.
        with open(temp_file_path, "wb") as buffer:
            content = await file.read() # Read content
            buffer.write(content) # Write to file
        print(f"File saved successfully to: {temp_file_path}")

        # Determine file type and extract text
        file_extension = os.path.splitext(safe_filename)[1].lower()

        if file_extension == '.txt':
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()
        elif file_extension == '.docx':
            try:
                import docx
                doc = docx.Document(temp_file_path)
                extracted_text = '\\n'.join([para.text for para in doc.paragraphs])
            except ImportError:
                raise HTTPException(status_code=501, detail="DOCX processing requires 'python-docx' library, which is not installed.")
            except Exception as e:
                 raise HTTPException(status_code=500, detail=f"Error reading DOCX file: {e}")
        elif file_extension == '.pdf':
            try:
                import fitz # PyMuPDF
                doc = fitz.open(temp_file_path)
                extracted_text = ""
                for page in doc:
                    extracted_text += page.get_text()
                doc.close()
            except ImportError:
                 raise HTTPException(status_code=501, detail="PDF processing requires 'PyMuPDF' library, which is not installed.")
            except Exception as e:
                 raise HTTPException(status_code=500, detail=f"Error reading PDF file: {e}")
        # Add support for other types (pptx, xlsx) similarly if needed
        # elif file_extension == '.pptx': ...
        # elif file_extension == '.xlsx': ...
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        print(f"Extracted text length: {len(extracted_text)}")
        return extracted_text # Return the extracted text

    except IOError as e:
        print(f"IOError saving/reading file {temp_file_path}: {e}")
        # Check permissions specifically
        if e.errno == 13: # Permission denied
             raise HTTPException(status_code=500, detail=f"Permission denied writing to {temp_file_path}. Check container permissions for {UPLOAD_DIR}.")
        raise HTTPException(status_code=500, detail=f"Error saving/accessing uploaded file: {e}")
    except HTTPException as e:
        # Re-raise HTTPExceptions directly
        raise e
    except Exception as e:
        print(f"Error processing file {file.filename}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred processing the document: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"Temporary file removed: {temp_file_path}")
            except OSError as e:
                # Log error but don't crash the request if cleanup fails
                print(f"Error removing temporary file {temp_file_path}: {e}")

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    # Ensure templates directory exists before trying to render
    if not os.path.exists(TEMPLATE_DIR):
         raise HTTPException(status_code=500, detail=f"Template directory not found at {TEMPLATE_DIR}")
    if not os.path.exists(os.path.join(TEMPLATE_DIR, "index.html")):
         raise HTTPException(status_code=500, detail=f"index.html not found in {TEMPLATE_DIR}")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/translate/text")
async def translate_text_endpoint(
    text: str = Form(...),
    source_lang: str = Form(...), # e.g., 'en', 'fr', 'auto'
    target_lang: str = Form("ar") # Default to Arabic
):
    """Translates direct text input."""
    if not text:
        raise HTTPException(status_code=400, detail="No text provided for translation.")
    # Allow translation to Arabic or from Arabic
    # if target_lang != "ar" and source_lang != "ar":
    #      raise HTTPException(status_code=400, detail="Translation must involve Arabic (either as source or target). Specify 'ar' in source_lang or target_lang.")

    # Simplified: For now, stick to the primary goal: other -> Arabic
    if target_lang != "ar":
         raise HTTPException(status_code=400, detail="Currently, only translation to Arabic (ar) is supported via this endpoint.")

    try:
        # Determine actual source language if 'auto' is selected (requires model/library support)
        actual_source_lang = source_lang # Placeholder
        # if source_lang == 'auto':
            # actual_source_lang = detect_language(text) # Needs implementation

        translated_text = translate_text_internal(text, actual_source_lang, target_lang)
        return JSONResponse(content={"translated_text": translated_text, "source_lang": actual_source_lang})
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions from internal functions
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in /translate/text: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during text translation: {e}")


@app.post("/translate/document")
async def translate_document_endpoint(
    file: UploadFile = File(...),
    source_lang: str = Form(...), # e.g., 'en', 'fr', 'auto'
    target_lang: str = Form("ar") # Default to Arabic
):
    """Translates text extracted from an uploaded document."""
    # Allow translation to Arabic or from Arabic
    # if target_lang != "ar" and source_lang != "ar":
    #      raise HTTPException(status_code=400, detail="Document translation must involve Arabic (either as source or target). Specify 'ar' in source_lang or target_lang.")

    # Simplified: For now, stick to the primary goal: other -> Arabic
    if target_lang != "ar":
         raise HTTPException(status_code=400, detail="Currently, only document translation to Arabic (ar) is supported.")

    # Ensure upload directory exists
    if not os.path.exists(UPLOAD_DIR):
        try:
            os.makedirs(UPLOAD_DIR)
        except OSError as e:
             raise HTTPException(status_code=500, detail=f"Could not create upload directory: {e}")

    # Create a safe temporary file path
    temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")

    try:
        # Save the uploaded file temporarily
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract text based on content type
        extracted_text = await extract_text_from_file(file)
        # Note: extract_text_from_file now raises HTTPException on errors or unsupported types

        if not extracted_text:
            # This case might be less likely if extract_text_from_file handles errors robustly
            # but keep it as a safeguard.
            if os.path.exists(temp_file_path):
                 os.remove(temp_file_path)
            raise HTTPException(status_code=400, detail="Could not extract any text from the document.")

        # Determine actual source language if 'auto' (requires model/library support)
        actual_source_lang = source_lang # Placeholder
        # if source_lang == 'auto':
            # actual_source_lang = detect_language(extracted_text) # Needs implementation

        # Translate the extracted text
        translated_text = translate_text_internal(extracted_text, actual_source_lang, target_lang)

        # Clean up the temporary file *after* successful processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return JSONResponse(content={
            "original_filename": file.filename,
            "detected_source_lang": actual_source_lang,
            "translated_text": translated_text
        })

    except HTTPException as http_exc:
        # Clean up temp file if it exists on known errors
        if os.path.exists(temp_file_path):
             try: 
                 os.remove(temp_file_path)
             except:
                 pass
        raise http_exc # Re-raise the exception
    except Exception as e:
        # Clean up temp file on unexpected errors
        if os.path.exists(temp_file_path):
             try:
                 os.remove(temp_file_path)
             except:
                 pass
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred processing the document: {e}")

# --- Optional: Add endpoint for reverse translation (Arabic to other) ---
# @app.post("/translate/reverse")
# async def translate_reverse_endpoint(text: str = Form(...), target_lang: str = Form(...)):
#     # Implement logic similar to translate_text_endpoint but with source="ar"
#     # You'll need a model capable of ar -> target_lang translation
#     pass

# --- Run the server (for local development) ---
if __name__ == "__main__":
    import uvicorn
    # Make sure to install PyMuPDF, python-docx etc. if testing locally:
    # pip install -r requirements.txt (from backend directory)
    print(f"Template Directory: {TEMPLATE_DIR}")
    print(f"Static Directory: {STATIC_DIR}")
    print(f"Upload Directory: {UPLOAD_DIR}")
    # Ensure necessary directories exist for local run
    if not os.path.exists(TEMPLATE_DIR): os.makedirs(TEMPLATE_DIR)
    if not os.path.exists(STATIC_DIR): os.makedirs(STATIC_DIR)
    if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
    # Create dummy index.html if it doesn't exist for local run
    if not os.path.exists(os.path.join(TEMPLATE_DIR, "index.html")):
        with open(os.path.join(TEMPLATE_DIR, "index.html"), "w") as f:
            f.write("<html><body><h1>Placeholder Frontend</h1></body></html>")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
