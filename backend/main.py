from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import shutil
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, MarianMTModel, MarianTokenizer
import torch
import traceback
import time  # For retries
import os
import requests # For direct API access as final fallback

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

# --- Model Loading Strategy ---
# Define model options in order of preference
MODEL_OPTIONS = [
    {"name": "google/flan-t5-small", "type": "flan-t5"},
    {"name": "Helsinki-NLP/opus-mt-en-ar", "type": "marian"},
    {"name": "t5-small", "type": "t5-fallback"}  # Smaller, more commonly available model
]

CACHE_DIR = "/app/.cache"
model = None
tokenizer = None

# Set environment variables for cache locations
os.environ["TRANSFORMERS_CACHE"] = CACHE_DIR
os.environ["HF_HOME"] = CACHE_DIR
print(f"Cache directories set to: {CACHE_DIR}")
print(f"Environment TRANSFORMERS_CACHE: {os.environ.get('TRANSFORMERS_CACHE')}")
print(f"Environment HF_HOME: {os.environ.get('HF_HOME')}")

# Create cache directory with explicit permissions
try:
    os.makedirs(CACHE_DIR, exist_ok=True)
    # Ensure the cache directory is writeable - set permissive permissions
    os.chmod(CACHE_DIR, 0o777)  # Read/write/execute for all
    print(f"Cache directory {CACHE_DIR} created with full permissions")
except Exception as e:
    print(f"Warning: Could not set permissions on cache dir: {e}")

# Try each model in order until one loads successfully
for model_option in MODEL_OPTIONS:
    MODEL_NAME = model_option["name"]
    MODEL_TYPE = model_option["type"]
    
    print(f"--- Attempting to load model: {MODEL_NAME} (Type: {MODEL_TYPE}) ---")
    
    # Try to load with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if MODEL_TYPE == "flan-t5" or MODEL_TYPE == "t5-fallback":
                print(f"Loading with AutoTokenizer/AutoModelForSeq2SeqLM (Attempt {attempt+1}/{max_retries})")
                tokenizer = AutoTokenizer.from_pretrained(
                    MODEL_NAME, 
                    cache_dir=CACHE_DIR,
                    local_files_only=False,  # Force online download
                    resume_download=True     # Resume if download was interrupted
                )
                
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    MODEL_NAME, 
                    cache_dir=CACHE_DIR,
                    local_files_only=False,  # Force online download
                    resume_download=True     # Resume if download was interrupted
                )
            elif MODEL_TYPE == "marian":
                print(f"Loading with MarianTokenizer/MarianMTModel (Attempt {attempt+1}/{max_retries})")
                tokenizer = MarianTokenizer.from_pretrained(
                    MODEL_NAME, 
                    cache_dir=CACHE_DIR,
                    local_files_only=False,
                    resume_download=True
                )
                
                model = MarianMTModel.from_pretrained(
                    MODEL_NAME, 
                    cache_dir=CACHE_DIR,
                    local_files_only=False,
                    resume_download=True
                )
            
            print(f"--- Successfully loaded model: {MODEL_NAME} ---")
            break  # Break out of retry loop if successful
            
        except Exception as e:
            print(f"Error loading model {MODEL_NAME} (Attempt {attempt+1}): {e}")
            traceback.print_exc()
            
            if attempt < max_retries - 1:
                wait_time = 2 * (attempt + 1)  # Exponential backoff
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"Failed to load model {MODEL_NAME} after {max_retries} attempts.")
    
    if model is not None and tokenizer is not None:
        # If we successfully loaded a model, break out of the model options loop
        break

# --- Fallback Translation Logic ---
# If we couldn't load any model, we'll set up a simple fallback system

# Define a simple dictionary for common phrases (just as a last resort)
FALLBACK_PHRASES = {
    "hello": "مرحبا",
    "thank you": "شكرا لك",
    "goodbye": "مع السلامة",
    "welcome": "أهلا وسهلا",
}

def fallback_translate(text, source_lang):
    """Last resort fallback translation if all models fail to load."""
    print("Using emergency fallback translation (very limited capability)")
    
    # For longer text, try direct API call to a free translation service
    try:
        # Try to use LibreTranslate API as fallback (no API key needed for some instances)
        url = "https://translate.terraprint.co/translate"
        
        payload = {
            "q": text,
            "source": source_lang if source_lang != "auto" else "auto",
            "target": "ar",
            "format": "text"
        }
        
        headers = {"Content-Type": "application/json"}
        
        print("Attempting LibreTranslate API call...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("LibreTranslate API call successful")
            return result.get("translatedText", f"[Translation Error: {response.text}]")
    
    except Exception as e:
        print(f"LibreTranslate API call failed: {e}")
    
    # If that fails too, use our minimal dictionary
    if text.lower() in FALLBACK_PHRASES:
        return FALLBACK_PHRASES[text.lower()]
    
    # For unknown text, return a message in Arabic explaining the issue
    return "عذراً، لم نتمكن من تحميل نموذج الترجمة. هذه ترجمة محدودة جداً."  # "Sorry, we couldn't load the translation model. This is a very limited translation."

# --- Helper Functions ---
def translate_text_internal(text: str, source_lang: str, target_lang: str = "ar") -> str:
    """Internal function to handle text translation using the loaded model or fallbacks."""
    
    # Check if we successfully loaded a model
    if model is None or tokenizer is None:
        # No model available, use fallback
        return fallback_translate(text, source_lang)
    
    # --- Enhanced Prompt Engineering --- 
    # Map source language codes to full language names for better model understanding
    language_map = {
        "en": "English",
        "fr": "French",
        "es": "Spanish",
        "de": "German",
        "zh": "Chinese",
        "ru": "Russian",
        "ja": "Japanese",
        "hi": "Hindi",
        "pt": "Portuguese",
        "tr": "Turkish",
        "ko": "Korean",
        "it": "Italian"
        # Add more languages as needed
    }
    
    # Get the full language name, or use the code if not in our map
    source_lang_name = language_map.get(source_lang, source_lang)
    
    # Craft a more detailed prompt that emphasizes meaning over literal translation
    # and focuses on eloquence and cultural sensitivity
    prompt = f"""Translate the following {source_lang_name} text into Modern Standard Arabic (Fusha).
Focus on conveying the meaning elegantly using proper Balagha (Arabic eloquence).
Adapt any cultural references or idioms appropriately rather than translating literally.
Ensure the translation reads naturally to a native Arabic speaker.

Text to translate:
{text}"""
    
    print(f"Translation Request - Source Lang: {source_lang} ({source_lang_name}), Target Lang: {target_lang}")
    print(f"Using Enhanced Prompt for Balagha and Cultural Sensitivity")

    # --- Model-specific translation logic ---
    try:
        if MODEL_TYPE in ["flan-t5", "t5-fallback"]:
            # Use prompt-based approach for T5 models
            # Tokenize the prompt
            inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)

            # Generate the translation with parameters tuned for quality
            outputs = model.generate(
                **inputs,
                max_length=512,  # Adjust based on expected output length
                num_beams=5,     # Increased for better quality
                length_penalty=1.0, # Encourage slightly longer outputs for natural flow
                top_k=50,        # More diverse word choices
                top_p=0.95,      # Sample from higher probability tokens for fluency
                early_stopping=True
            )

            # Decode the generated tokens
            translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
        elif MODEL_TYPE == "marian":
            # Direct translation for Marian model (specialized for translation)
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            
            outputs = model.generate(
                **inputs,
                max_length=512,
                num_beams=5,
                length_penalty=1.0,
                early_stopping=True
            )
            
            translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        else:
            # Unknown model type, use fallback
            return fallback_translate(text, source_lang)

        print(f"Raw Translation Output: {translated_text}")
        return translated_text

    except Exception as e:
        print(f"Error during model generation: {e}")
        traceback.print_exc()
        
        # If translation fails, use fallback
        return fallback_translate(text, source_lang)

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
