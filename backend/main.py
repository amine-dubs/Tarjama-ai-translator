from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import shutil
import os
import requests
import json
import traceback
import time

# --- Configuration ---
# Determine the base directory of the main.py script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust paths to go one level up from backend to find templates/static
TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
UPLOAD_DIR = "/app/uploads"  # Ensure this matches Dockerfile WORKDIR + uploads

# LibreTranslate API URLs - trying multiple endpoints in case one is down
TRANSLATION_APIS = [
    "https://translate.terraprint.co/translate",  # Primary endpoint
    "https://libretranslate.de/translate",        # Backup endpoint 1
    "https://translate.argosopentech.com/translate" # Backup endpoint 2
]

app = FastAPI()

# --- Mount Static Files and Templates ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- Fallback dictionary for common phrases ---
FALLBACK_PHRASES = {
    "hello": "مرحبا",
    "thank you": "شكرا لك",
    "goodbye": "مع السلامة",
    "welcome": "أهلا وسهلا",
    "yes": "نعم",
    "no": "لا",
    "please": "من فضلك",
    "sorry": "آسف",
}

# --- Translation Function ---
def translate_text_internal(text: str, source_lang: str, target_lang: str = "ar") -> str:
    """
    Translate text using LibreTranslate API with fallbacks and cultural adaptation.
    """
    print(f"Translation Request - Source Lang: {source_lang}, Target Lang: {target_lang}")
    
    # Map source language codes to full language names
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
    }
    
    # For very short text, check our dictionary first
    if len(text.strip()) < 30 and text.lower().strip() in FALLBACK_PHRASES:
        return FALLBACK_PHRASES[text.lower().strip()]
    
    # Try each API endpoint until one works
    for api_url in TRANSLATION_APIS:
        try:
            print(f"Attempting translation using API: {api_url}")
            
            # Basic payload for standard translation
            payload = {
                "q": text,
                "source": source_lang if source_lang != "auto" else "auto",
                "target": target_lang,
                "format": "text"
            }
            
            headers = {"Content-Type": "application/json"}
            
            # Make the API call
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result.get("translatedText")
                
                if translated_text:
                    print(f"Translation successful using {api_url}")
                    
                    # For Arabic translations, apply post-processing
                    if target_lang == "ar":
                        translated_text = culturally_adapt_arabic(translated_text)
                    
                    return translated_text
                else:
                    print(f"Translation API returned empty result: {response.text}")
                    continue  # Try next API
            else:
                print(f"Translation API returned error: {response.status_code}")
                continue  # Try next API
                
        except Exception as e:
            print(f"Error with translation API {api_url}: {e}")
            continue  # Try next API
    
    # If all APIs failed, use a polite message
    fallback_text = FALLBACK_PHRASES.get(text.lower().strip()) if len(text.strip()) < 30 else None
    
    if fallback_text:
        return fallback_text
    else:
        return "عذراً، لم نتمكن من ترجمة النص. خدمة الترجمة غير متاحة حالياً."

def culturally_adapt_arabic(text: str) -> str:
    """Apply post-processing rules to enhance Arabic translation with cultural sensitivity."""
    # Replace any Latin punctuation with Arabic ones
    text = text.replace('?', '؟').replace(';', '؛').replace(',', '،')
    return text

# --- Helper Functions ---
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
