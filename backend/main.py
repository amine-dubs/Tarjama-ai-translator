from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict
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
UPLOADS_DIR = os.path.join(os.path.dirname(BASE_DIR), "uploads")

# Ensure uploads directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)

# --- Initialize FastAPI ---
app = FastAPI(title="Tarjama Translation API")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- Language mapping ---
LANGUAGE_MAP = {
    "ar": "Arabic",
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
    "it": "Italian",
    "nl": "Dutch",
    "sv": "Swedish",
    "fi": "Finnish",
    "pl": "Polish",
    "he": "Hebrew",
    "id": "Indonesian",
    "uk": "Ukrainian",
    "cs": "Czech",
    "auto": "Detect Language"
}

# --- Set cache directory to a writeable location ---
# This is crucial for Hugging Face Spaces where /app/.cache is not writable
# Using /tmp which is typically writable in most environments
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
os.environ['HF_HOME'] = '/tmp/hf_home'
os.environ['XDG_CACHE_HOME'] = '/tmp/cache'

# --- Global model variables ---
# Store multiple translation models to support various language pairs
translation_models: Dict[str, Dict] = {
    "en-ar": {
        "model": None,
        "tokenizer": None,
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-en-ar",
    },
    "ar-en": {
        "model": None,
        "tokenizer": None, 
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-ar-en",
    },
    # Add more language pair models
    "en-fr": {
        "model": None,
        "tokenizer": None,
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-en-fr",
    },
    "fr-en": {
        "model": None,
        "tokenizer": None,
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-fr-en",
    },
    "en-es": {
        "model": None,
        "tokenizer": None,
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-en-es",
    },
    "es-en": {
        "model": None,
        "tokenizer": None,
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-es-en",
    },
    "en-de": {
        "model": None,
        "tokenizer": None,
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-en-de",
    },
    "de-en": {
        "model": None,
        "tokenizer": None,
        "translator": None,
        "model_name": "Helsinki-NLP/opus-mt-de-en",
    },
    # Can add more language pairs here as needed
}

model_initialization_attempts = 0
max_model_initialization_attempts = 3
last_initialization_attempt = 0
initialization_cooldown = 300  # 5 minutes cooldown between retry attempts

# --- Model initialization function ---
def initialize_model(language_pair: str):
    """Initialize a specific translation model and tokenizer for a language pair."""
    global translation_models, model_initialization_attempts, last_initialization_attempt
    
    # If language pair doesn't exist, return False
    if language_pair not in translation_models:
        print(f"Unsupported language pair: {language_pair}")
        return False
    
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
        model_info = translation_models[language_pair]
        model_name = model_info["model_name"]
        
        print(f"Initializing model and tokenizer for {language_pair} using {model_name} (attempt {model_initialization_attempts})...")
        
        # Check for available device - properly detect CPU/GPU
        device = "cpu"  # Default to CPU which is more reliable
        if torch.cuda.is_available():
            device = "cuda"
            print(f"CUDA is available: {torch.cuda.get_device_name(0)}")
        print(f"Device set to use: {device}")
        
        # Load the tokenizer with explicit cache directory
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                cache_dir="/tmp/transformers_cache",
                use_fast=True,
                local_files_only=False
            )
            if tokenizer is None:
                print(f"Failed to load tokenizer for {language_pair}")
                return False
            print(f"Tokenizer for {language_pair} loaded successfully")
            translation_models[language_pair]["tokenizer"] = tokenizer
        except Exception as e:
            print(f"Error loading tokenizer for {language_pair}: {e}")
            return False
        
        # Load the model with explicit device placement
        try:
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                cache_dir="/tmp/transformers_cache",
                low_cpu_mem_usage=True,  # Better memory usage
                torch_dtype=torch.float32  # Explicit dtype for better compatibility
            )
            # Move model to device after loading
            model = model.to(device)
            print(f"Model for {language_pair} loaded with PyTorch and moved to {device}")
            translation_models[language_pair]["model"] = model
        except Exception as e:
            print(f"Error loading model for {language_pair}: {e}")
            print(f"Model initialization for {language_pair} failed")
            return False
        
        # Create a pipeline with the loaded model and tokenizer
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
                print(f"Failed to create translator pipeline for {language_pair}")
                return False
                
            # Test the model with a simple translation to verify it works
            source_lang, target_lang = language_pair.split('-')
            test_text = "hello world" if source_lang == "en" else "مرحبا بالعالم"
            test_result = translator(test_text, max_length=128)
            print(f"Model test result for {language_pair}: {test_result}")
            if not test_result or not isinstance(test_result, list) or len(test_result) == 0:
                print(f"Model test for {language_pair} failed: Invalid output format")
                return False
            
            translation_models[language_pair]["translator"] = translator
            
            # Success - reset the attempt counter
            model_initialization_attempts = 0
            print(f"Model {model_name} for {language_pair} successfully initialized and tested")
            return True
        except Exception as inner_e:
            print(f"Error creating translation pipeline for {language_pair}: {inner_e}")
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"Critical error initializing model for {language_pair}: {e}")
        traceback.print_exc()
        return False

# --- Get appropriate language pair for translation ---
def get_language_pair(source_lang: str, target_lang: str):
    """Determine the appropriate language pair and direction for translation."""
    # Handle auto-detection case (fallback to online services)
    if source_lang == "auto":
        return None
    
    # Check if we have a direct model for this language pair
    pair_key = f"{source_lang}-{target_lang}"
    if pair_key in translation_models:
        return pair_key
        
    # No direct model available
    return None

# --- Language detection function ---
def detect_language(text: str) -> str:
    """Detect the language of the input text and return the language code."""
    try:
        # Try to use langdetect library if available
        from langdetect import detect
        
        try:
            detected_lang = detect(text)
            print(f"Language detected using langdetect: {detected_lang}")
            
            # Map langdetect specific codes to our standard codes
            lang_map = {
                "ar": "ar", "en": "en", "fr": "fr", "es": "es", "de": "de",
                "zh-cn": "zh", "zh-tw": "zh", "ru": "ru", "ja": "ja", 
                "hi": "hi", "pt": "pt", "tr": "tr", "ko": "ko",
                "it": "it", "nl": "nl", "sv": "sv", "fi": "fi",
                "pl": "pl", "he": "he", "id": "id", "uk": "uk", "cs": "cs"
            }
            
            # Return the mapped language or default to English if not in our supported languages
            return lang_map.get(detected_lang, "en")
        except Exception as e:
            print(f"Error with langdetect: {e}")
            # Fall back to basic detection
    except ImportError:
        print("langdetect library not available, using basic detection")
    
    # Basic fallback detection based on character ranges
    if len(text) < 10:  # Need reasonable amount of text
        return "en"  # Default to English for very short texts
    
    # Count characters in different Unicode ranges
    arabic_count = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    japanese_count = sum(1 for c in text if '\u3040' <= c <= '\u30ff')
    cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    hebrew_count = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
    
    # Determine ratios
    text_len = len(text)
    arabic_ratio = arabic_count / text_len
    chinese_ratio = chinese_count / text_len
    japanese_ratio = japanese_count / text_len
    cyrillic_ratio = cyrillic_count / text_len
    hebrew_ratio = hebrew_count / text_len
    
    # Make decision based on highest ratio
    if arabic_ratio > 0.3:
        return "ar"
    elif chinese_ratio > 0.3:
        return "zh"
    elif japanese_ratio > 0.3:
        return "ja"
    elif cyrillic_ratio > 0.3:
        return "ru"
    elif hebrew_ratio > 0.3:
        return "he"
    
    # Default to English for Latin scripts (could be any European language)
    return "en"

# --- Translation Function ---
def translate_text(text, source_lang, target_lang):
    """Translate text using local model or fallback to online services."""
    if not text:
        return ""
    
    print(f"Translation Request - Source Lang: {source_lang}, Target Lang: {target_lang}")
    
    # Get the appropriate language pair for local translation
    language_pair = get_language_pair(source_lang, target_lang)
    
    # If we have a supported local model for this language pair
    if language_pair and language_pair in translation_models:
        model_info = translation_models[language_pair]
        translator = model_info["translator"]
        
        # Check if model is initialized, if not try to initialize it
        if not translator:
            success = initialize_model(language_pair)
            if not success:
                print(f"Local model initialization for {language_pair} failed, using fallback translation")
                return use_fallback_translation(text, source_lang, target_lang)
            # Get the translator after initialization
            translator = translation_models[language_pair]["translator"]
        
        try:
            # Ensure only the raw text is sent to the model
            text_to_translate = text 
            print(f"Translating text with local model (first 50 chars): {text_to_translate[:50]}...") 
            
            # Use a more reliable timeout approach with concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: translator(
                        text_to_translate,
                        max_length=768
                    )[0]["translation_text"]
                )
                
                try:
                    # Set a reasonable timeout
                    result = future.result(timeout=15)
                    
                    # Post-process the result for cultural adaptation if needed
                    if target_lang == "ar":
                        result = culturally_adapt_arabic(result)
                    
                    print(f"Translation successful (first 50 chars): {result[:50]}...")
                    return result
                except concurrent.futures.TimeoutError:
                    print(f"Model inference timed out after 15 seconds, falling back to online translation")
                    return use_fallback_translation(text, source_lang, target_lang)
                except Exception as e:
                    print(f"Error during model inference: {e}")
                    # If the model failed during inference, try to re-initialize it for next time
                    # but use fallback for this request
                    initialize_model(language_pair)
                    return use_fallback_translation(text, source_lang, target_lang)
        except Exception as e:
            print(f"Error using local model for {language_pair}: {e}")
            traceback.print_exc()
            return use_fallback_translation(text, source_lang, target_lang)
    else:
        # No local model for this language pair, use online services
        print(f"No local model for {source_lang} to {target_lang}, using fallback translation")
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
def check_and_reinitialize_model(language_pair: str):
    """Check if model needs to be reinitialized and do so if necessary"""
    global translation_models
    
    if language_pair not in translation_models:
        print(f"Unsupported language pair: {language_pair}")
        return False
    
    model_info = translation_models[language_pair]
    translator = model_info["translator"]
    
    try:
        # If model isn't initialized yet, try to initialize it
        if not translator:
            print(f"Model for {language_pair} not initialized. Attempting initialization...")
            return initialize_model(language_pair)
            
        # Test the existing model with a simple translation
        source_lang, target_lang = language_pair.split('-')
        test_text = "hello" if source_lang == "en" else "مرحبا"
        result = translator(test_text, max_length=128)
        
        # If we got a valid result, model is working fine
        if result and isinstance(result, list) and len(result) > 0:
            print(f"Model check for {language_pair}: Model is functioning correctly.")
            return True
        else:
            print(f"Model check for {language_pair}: Model returned invalid result. Reinitializing...")
            return initialize_model(language_pair)
    except Exception as e:
        print(f"Error checking model status for {language_pair}: {e}")
        print("Model may be in a bad state. Attempting reinitialization...")
        return initialize_model(language_pair)

def use_fallback_translation(text, source_lang, target_lang):
    """Use various fallback online translation services."""
    print("Using fallback translation...")
    
    # Try Google Translate API with a wrapper first (most reliable)
    try:
        print("Attempting fallback with Google Translate (no API key)")
        from googletrans import Translator
        google_translator = Translator(service_urls=['translate.google.com', 'translate.google.co.kr'])
        result = google_translator.translate(text, src=source_lang, dest=target_lang)
        if result and result.text:
            print("Google Translate successful!")
            return result.text
    except Exception as e:
        print(f"Error with Google Translate fallback: {str(e)}")
    
    # List of LibreTranslate servers to try with increased timeout
    libre_servers = [
        "https://translate.terraprint.co/translate",
        "https://libretranslate.de/translate",
        "https://translate.argosopentech.com/translate",
        "https://translate.fedilab.app/translate",
        "https://trans.zillyhuhn.com/translate"
    ]
    
    # Try each LibreTranslate server with increased timeout
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
            
            # Use a longer timeout for the request
            response = requests.post(server, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if "translatedText" in result:
                    print(f"LibreTranslate successful using {server}")
                    return result["translatedText"]
        except Exception as e:
            print(f"Error with LibreTranslate {server}: {str(e)}")
            continue
    
    # Try MyMemory as another fallback
    try:
        print("Attempting fallback with MyMemory Translation API")
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"{source_lang}|{target_lang}",
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and data.get("responseData") and data["responseData"].get("translatedText"):
                print("MyMemory translation successful!")
                return data["responseData"]["translatedText"]
    except Exception as e:
        print(f"Error with MyMemory fallback: {str(e)}")
    
    # Final fallback - return original text with error message
    print("All translation services failed. Returning error message.")
    return f"[Translation services unavailable] {text}"

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

@app.get("/api/languages")
async def get_languages():
    """Return the list of supported languages."""
    return {"languages": LANGUAGE_MAP}

@app.post("/translate/text")
async def translate_text_endpoint(request: TranslationRequest):
    print("[DEBUG] /translate/text endpoint called")
    try:
        # Explicitly extract fields from request to ensure they exist
        source_lang = request.source_lang
        target_lang = request.target_lang
        text = request.text
        
        print(f"[DEBUG] Received request: source_lang={source_lang}, target_lang={target_lang}, text={text[:50]}")
        
        # Handle automatic language detection
        detected_source_lang = None
        if source_lang == "auto":
            detected_source_lang = detect_language(text)
            print(f"[DEBUG] Detected language: {detected_source_lang}")
            source_lang = detected_source_lang
        
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
        
        # Include detected language in response if auto-detection was used
        response_data = {
            "success": True,
            "translated_text": translation_result
        }
        
        if detected_source_lang:
            response_data["detected_source_lang"] = detected_source_lang
            
        return response_data
    
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
    print("[DEBUG] /translate/document endpoint called") 
    try:
        # Extract text directly from the uploaded file
        print(f"[DEBUG] Processing file: {file.filename}, Source: {source_lang}, Target: {target_lang}")
        
        # Extract text from document
        extracted_text = await extract_text_from_file(file)
        if not extracted_text or extracted_text.strip() == "":
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Could not extract text from document"}
            )
            
        # Handle automatic language detection
        detected_source_lang = None
        if source_lang == "auto":
            detected_source_lang = detect_language(extracted_text)
            print(f"[DEBUG] Detected document language: {detected_source_lang}")
            source_lang = detected_source_lang

        # Translate the extracted text
        translated_text = translate_text(extracted_text, source_lang, target_lang)
        
        # Prepare response
        response = {
            "success": True,
            "original_filename": file.filename,
            "original_text": extracted_text[:2000] + ("..." if len(extracted_text) > 2000 else ""),
            "translated_text": translated_text
        }
        
        # Include detected language in response if auto-detection was used
        if detected_source_lang:
            response["detected_source_lang"] = detected_source_lang
            
        return response
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        print(f"Error in document translation: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Document translation failed: {str(e)}"}
        )

# Initialize models during startup
@app.on_event("startup")
async def startup_event():
    """Initialize models during application startup."""
    # Initial model loading for the most common language pairs
    # We load them asynchronously to not block the startup
    try:
        # Try to initialize English-to-Arabic model
        initialize_model("en-ar")
    except Exception as e:
        print(f"Error initializing en-ar model at startup: {e}")
    
    try:
        # Try to initialize Arabic-to-English model 
        initialize_model("ar-en")
    except Exception as e:
        print(f"Error initializing ar-en model at startup: {e}")
        
    # Initialize additional models for common language pairs
    # These will be initialized in the background without blocking startup
    common_pairs = ["en-fr", "fr-en", "en-es", "es-en"]
    for pair in common_pairs:
        try:
            initialize_model(pair)
        except Exception as e:
            print(f"Error initializing {pair} model at startup: {e}")

# --- Run the server (for local development) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
