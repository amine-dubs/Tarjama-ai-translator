from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel
import os
import requests
import json
import traceback
import io
import concurrent.futures
import subprocess
import sys
import time

# Define the TranslationRequest model
class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

# Import transformers for local model inference
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import torch

# --- Configuration ---
# Determine the base directory of the main.py script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust paths to go one level up from backend to find templates/static
TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")

# --- Initialize FastAPI ---
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- Language mapping ---
LANGUAGE_MAP = {
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

# --- Set cache directory to a writeable location ---
# This is crucial for Hugging Face Spaces where /app/.cache is not writable
# Using /tmp which is typically writable in most environments
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
os.environ['HF_HOME'] = '/tmp/hf_home'
os.environ['XDG_CACHE_HOME'] = '/tmp/cache'

# --- Global model and tokenizer variables ---
translator = None
tokenizer = None
model = None
model_initialization_attempts = 0
max_model_initialization_attempts = 3
last_initialization_attempt = 0
initialization_cooldown = 300  # 5 minutes cooldown between retry attempts

# --- Model initialization function ---
def initialize_model():
    """Initialize the translation model and tokenizer."""
    global translator, tokenizer, model, model_initialization_attempts, last_initialization_attempt
    
    # Check if we've exceeded maximum attempts and if enough time has passed since last attempt
    current_time = time.time()
    if (model_initialization_attempts >= max_model_initialization_attempts and 
        current_time - last_initialization_attempt < initialization_cooldown):
        print(f"Maximum initialization attempts reached. Waiting for cooldown period.")
        return False
    
    # Update attempt counter and timestamp
    model_initialization_attempts += 1
    last_initialization_attempt = current_time
    
    try:
        print(f"Initializing model and tokenizer (attempt {model_initialization_attempts})...")
        
        # Use a better translation model that handles multilingual tasks well
        model_name = "facebook/nllb-200-distilled-600M"  # Better multilingual translation model
        
        # Check for available device - properly detect CPU/GPU
        device = "cpu"  # Default to CPU which is more reliable
        if torch.cuda.is_available():
            device = "cuda"
            print(f"CUDA is available: {torch.cuda.get_device_name(0)}")
        print(f"Device set to use: {device}")
        
        # Load the tokenizer with explicit cache directory
        print(f"Loading tokenizer from {model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            cache_dir="/tmp/transformers_cache",
            use_fast=True  # Use faster tokenizer when possible
        )
        if tokenizer is None:
            print("Failed to load tokenizer")
            return False
        print("Tokenizer loaded successfully")
        
        # Load the model with explicit device placement
        print(f"Loading model from {model_name}...")
        try:
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                cache_dir="/tmp/transformers_cache",
                low_cpu_mem_usage=True,  # Better memory usage
                torch_dtype=torch.float32  # Explicit dtype for better compatibility
            )
            # Move model to device after loading
            model = model.to(device)
            print(f"Model loaded with PyTorch and moved to {device}")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Model initialization failed")
            return False
        
        # Create a pipeline with the loaded model and tokenizer
        print("Creating translation pipeline...")
        try:
            # Create the pipeline with explicit model and tokenizer
            translator = pipeline(
                "translation",
                model=model,
                tokenizer=tokenizer,
                device=0 if device == "cuda" else -1,  # Proper device mapping
                framework="pt"  # Explicitly use PyTorch
            )
            
            if translator is None:
                print("Failed to create translator pipeline")
                return False
                
            # Test the model with a simple translation to verify it works
            # NLLB needs language codes in format like "eng_Latn" and "ara_Arab"
            test_result = translator("hello", src_lang="eng_Latn", tgt_lang="ara_Arab", max_length=128)
            print(f"Model test result: {test_result}")
            if not test_result or not isinstance(test_result, list) or len(test_result) == 0:
                print("Model test failed: Invalid output format")
                return False
            
            # Success - reset the attempt counter
            model_initialization_attempts = 0
            print(f"Model {model_name} successfully initialized and tested")
            return True
        except Exception as inner_e:
            print(f"Error creating translation pipeline: {inner_e}")
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"Critical error initializing model: {e}")
        traceback.print_exc()
        return False

# --- Translation Function ---
def translate_text(text, source_lang, target_lang):
    """Translate text using local model or fallback to online services."""
    global translator, tokenizer, model
    
    print(f"Translation Request - Source Lang: {source_lang}, Target Lang: {target_lang}")
    
    # Check if model is initialized, if not try to initialize it
    if not model or not tokenizer or not translator:
        success = initialize_model()
        if not success:
            print("Local model initialization failed, using fallback translation")
            return use_fallback_translation(text, source_lang, target_lang)
    
    try:
        # Get full language name for better prompt context
        source_lang_name = LANGUAGE_MAP.get(source_lang, source_lang)
        
        # Create a culturally-aware prompt with focus on Arabic eloquence (Balagha)
        if target_lang == "ar":
            prompt = f"""Translate the following {source_lang_name} text into Modern Standard Arabic (Fusha).
Focus on conveying the meaning elegantly using proper Balagha (Arabic eloquence).
Adapt any cultural references or idioms appropriately rather than translating literally.
Ensure the translation reads naturally to a native Arabic speaker.

Text to translate:
{text}"""
            print("Using culturally-aware prompt for Arabic translation with Balagha focus")
        else:
            # For non-Arabic target languages, use standard approach
            prompt = text
            
        # Prepare input with explicit instruction format for better results with NLLB
        src_lang_code = f"{source_lang}_Latn" if source_lang != "ar" else f"{source_lang}_Arab"
        tgt_lang_code = f"{target_lang}_Latn" if target_lang != "ar" else f"{target_lang}_Arab"
        
        # Use a more reliable timeout approach with concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: translator(
                    prompt,  # Using our enhanced prompt instead of raw text
                    src_lang=src_lang_code,
                    tgt_lang=tgt_lang_code,
                    max_length=768  # Increased max_length to accommodate longer prompt
                )[0]["translation_text"]
            )
            
            try:
                # Set a reasonable timeout (15 seconds instead of 10)
                result = future.result(timeout=15)
                
                # Post-process the result for Arabic cultural adaptation
                if target_lang == "ar":
                    result = culturally_adapt_arabic(result)
                
                return result
            except concurrent.futures.TimeoutError:
                print(f"Model inference timed out after 15 seconds, falling back to online translation")
                return use_fallback_translation(text, source_lang, target_lang)
            except Exception as e:
                print(f"Error during model inference: {e}")
                
                # If the model failed during inference, try to re-initialize it for next time
                # but use fallback for this request
                initialize_model()
                return use_fallback_translation(text, source_lang, target_lang)
    except Exception as e:
        print(f"Error using local model: {e}")
        traceback.print_exc()
        return use_fallback_translation(text, source_lang, target_lang)

def culturally_adapt_arabic(text: str) -> str:
    """Apply post-processing rules to enhance Arabic translation with cultural sensitivity."""
    # Replace Latin punctuation with Arabic ones
    text = text.replace('?', '؟').replace(';', '؛').replace(',', '،')
    
    # If the text starts with common translation artifacts like "Translation:" or the prompt instructions, remove them
    common_prefixes = [
        "الترجمة:", "ترجمة:", "النص المترجم:", 
        "Translation:", "Arabic translation:"
    ]
    for prefix in common_prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    
    # Additional cultural adaptations can be added here
    
    return text

# --- Function to check model status and trigger re-initialization if needed ---
def check_and_reinitialize_model():
    """Check if model needs to be reinitialized and do so if necessary"""
    global translator, model, tokenizer
    
    try:
        # If model isn't initialized yet, try to initialize it
        if not model or not tokenizer or not translator:
            print("Model not initialized. Attempting initialization...")
            return initialize_model()
            
        # Test the existing model with a simple translation
        test_text = "hello"
        result = translator(test_text, src_lang="eng_Latn", tgt_lang="fra_Latn", max_length=128)
        
        # If we got a valid result, model is working fine
        if result and isinstance(result, list) and len(result) > 0:
            print("Model check: Model is functioning correctly.")
            return True
        else:
            print("Model check: Model returned invalid result. Reinitializing...")
            return initialize_model()
    except Exception as e:
        print(f"Error checking model status: {e}")
        print("Model may be in a bad state. Attempting reinitialization...")
        return initialize_model()

def use_fallback_translation(text, source_lang, target_lang):
    """Use various fallback online translation services."""
    # List of LibreTranslate servers to try in order
    libre_servers = [
        "https://translate.terraprint.co/translate",
        "https://libretranslate.de/translate",
        "https://translate.argosopentech.com/translate",
        "https://translate.fedilab.app/translate"  # Added additional server
    ]
    
    # Try each LibreTranslate server
    for server in libre_servers:
        try:
            print(f"Attempting fallback translation using LibreTranslate: {server}")
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "q": text,
                "source": source_lang,
                "target": target_lang
            }
            
            # Use a shorter timeout for the request (5 seconds instead of 10)
            response = requests.post(server, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if "translatedText" in result:
                    return result["translatedText"]
        except Exception as e:
            print(f"Error with LibreTranslate {server}: {str(e)}")
            continue
    
    # If all LibreTranslate servers fail, try Google Translate API with a wrapper
    # that doesn't need an API key for limited usage
    try:
        print("Attempting fallback with Google Translate (no API key)")
        from googletrans import Translator
        google_translator = Translator()
        result = google_translator.translate(text, src=source_lang, dest=target_lang)
        return result.text
    except Exception as e:
        print(f"Error with Google Translate fallback: {str(e)}")
    
    # Final fallback - return original text with error message
    return f"[Translation failed] {text}"

# --- Helper Functions ---
async def extract_text_from_file(file: UploadFile) -> str:
    """Extracts text content from uploaded files without writing to disk."""
    content = await file.read()
    file_extension = os.path.splitext(file.filename)[1].lower()
    extracted_text = ""

    try:
        if file_extension == '.txt':
            # Process text file directly from bytes
            try:
                extracted_text = content.decode('utf-8')
            except UnicodeDecodeError:
                # Try other common encodings if UTF-8 fails
                for encoding in ['latin-1', 'cp1252', 'utf-16']:
                    try:
                        extracted_text = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
        elif file_extension == '.docx':
            try:
                import docx
                from io import BytesIO
                
                # Load DOCX from memory
                doc_stream = BytesIO(content)
                doc = docx.Document(doc_stream)
                extracted_text = '\n'.join([para.text for para in doc.paragraphs])
            except ImportError:
                raise HTTPException(status_code=501, detail="DOCX processing requires 'python-docx' library")
        elif file_extension == '.pdf':
            try:
                import fitz  # PyMuPDF
                from io import BytesIO
                
                # Load PDF from memory
                pdf_stream = BytesIO(content)
                doc = fitz.open(stream=pdf_stream, filetype="pdf")
                
                page_texts = []
                for page in doc:
                    page_texts.append(page.get_text())
                extracted_text = "\n".join(page_texts)
                doc.close()
            except ImportError:
                raise HTTPException(status_code=501, detail="PDF processing requires 'PyMuPDF' library")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        print(f"Extracted text length: {len(extracted_text)}")
        return extracted_text

    except Exception as e:
        print(f"Error processing file {file.filename}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/translate/text")
async def translate_text_endpoint(request: TranslationRequest):
    global translator, model, tokenizer
    
    print("[DEBUG] /translate/text endpoint called")
    try:
        # Explicitly extract fields from request to ensure they exist
        source_lang = request.source_lang
        target_lang = request.target_lang
        text = request.text
        
        print(f"[DEBUG] Received request: source_lang={source_lang}, target_lang={target_lang}, text={text[:50]}")
        
        # Call our culturally-aware translate_text function
        translation_result = translate_text(text, source_lang, target_lang)
        
        # Check for empty result
        if not translation_result or translation_result.strip() == "":
            print("[DEBUG] Empty translation result received")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Translation returned empty result"}
            )
            
        print(f"[DEBUG] Translation successful: {translation_result[:100]}...")
        return {"success": True, "translated_text": translation_result}
    
    except Exception as e:
        print(f"Critical error in translate_text_endpoint: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Translation failed: {str(e)}"}
        )

@app.post("/translate/document")
async def translate_document_endpoint(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form("ar")
):
    """Translates text extracted from an uploaded document."""
    try:
        # Extract text directly from the uploaded file
        extracted_text = await extract_text_from_file(file)
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="Could not extract any text from the document.")

        # Translate the extracted text
        translated_text = translate_text(extracted_text, source_lang, target_lang)

        return JSONResponse(content={
            "original_filename": file.filename,
            "detected_source_lang": source_lang,
            "translated_text": translated_text
        })

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Document translation error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Document translation error: {str(e)}")

# --- Run the server (for local development) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
