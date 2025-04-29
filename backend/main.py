from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import os
import requests
import json
import traceback
import io
import concurrent.futures

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

# --- Model initialization function ---
def initialize_model():
    """Initialize the translation model and tokenizer."""
    global translator, tokenizer, model
    
    try:
        print("Initializing model and tokenizer...")
        
        # Use a smaller model that works well for instruction-based translation
        model_name = "google/flan-t5-small"
        
        # Check for available device - properly detect CPU/GPU
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Device set to use {device}")
        
        # Load the tokenizer with explicit cache directory
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            cache_dir="/tmp/transformers_cache"
        )
        
        # Load the model with PyTorch approach which is more reliable
        try:
            print("Loading model with PyTorch backend...")
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                cache_dir="/tmp/transformers_cache",
                low_cpu_mem_usage=True,  # Add this for better memory usage
                device_map="auto"  # Let the library decide optimal device mapping
            )
        except Exception as e:
            print(f"PyTorch loading failed: {e}")
            print("Attempting to load with TensorFlow...")
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                from_tf=True,
                cache_dir="/tmp/transformers_cache"
            )
        
        # Create a pipeline with the loaded model and tokenizer
        print("Creating pipeline with pre-loaded model...")
        translator = pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer,
            device=device,  # Use detected device instead of hardcoding -1
            max_length=512
        )
        
        print(f"Model {model_name} successfully initialized")
        return True
    except Exception as e:
        print(f"Error initializing model: {e}")
        traceback.print_exc()
        return False

# --- Translation Function ---
def translate_text(text, source_lang, target_lang):
    """Translate text using local model or fallback to online services."""
    global translator, tokenizer, model
    
    print(f"Translation Request - Source Lang: {source_lang}, Target Lang: {target_lang}")
    
    if not model or not tokenizer:
        success = initialize_model()
        if not success:
            return use_fallback_translation(text, source_lang, target_lang)
    
    try:
        # Prepare input with explicit instruction format for better results with flan-t5
        input_text = f"Translate from {source_lang} to {target_lang}: {text}"
        
        # Use a more reliable timeout approach with concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: translator(
                    input_text, 
                    max_length=512,
                    num_beams=4,  # Increase beam search for better quality
                    no_repeat_ngram_size=2
                )[0]["generated_text"]
            )
            
            try:
                # Set a reasonable timeout (15 seconds instead of 10)
                result = future.result(timeout=15)
                
                # Clean up result (remove any instruction preamble if present)
                if ':' in result and len(result.split(':', 1)) > 1:
                    result = result.split(':', 1)[1].strip()
                
                return result
            except concurrent.futures.TimeoutError:
                print(f"Model inference timed out after 15 seconds, falling back to online translation")
                return use_fallback_translation(text, source_lang, target_lang)
    except Exception as e:
        print(f"Error using local model: {e}")
        traceback.print_exc()
        return use_fallback_translation(text, source_lang, target_lang)

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

def culturally_adapt_arabic(text: str) -> str:
    """Apply post-processing rules to enhance Arabic translation with cultural sensitivity."""
    # Replace any Latin punctuation with Arabic ones
    text = text.replace('?', '؟').replace(';', '؛').replace(',', '،')
    return text

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
async def translate_text_endpoint(
    text: str = Form(...),
    source_lang: str = Form(...),
    target_lang: str = Form("ar")
):
    """Translates direct text input."""
    if not text:
        raise HTTPException(status_code=400, detail="No text provided for translation.")
    
    try:
        translated_text = translate_text(text, source_lang, target_lang)
        return JSONResponse(content={"translated_text": translated_text, "source_lang": source_lang})
    except Exception as e:
        print(f"Translation error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

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
