from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict, Any
import os
import requests
import json
import traceback
import io

# --- Configuration ---
# Determine the base directory of the main.py script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust paths to go one level up from backend to find templates/static
TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")

# Hugging Face API configurations
HF_API_URL = "https://api-inference.huggingface.co/models/t5-base"
HF_HEADERS = {"Authorization": "Bearer hf_api_key_placeholder"}  # Replace with your API key or remove if using a free model

app = FastAPI()

# --- Mount Static Files and Templates ---
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
    Translate text using Hugging Face Inference API with prompt engineering.
    """
    if not text.strip():
        return ""
        
    print(f"Translation Request - Source Lang: {source_lang}, Target Lang: {target_lang}")
    
    # For very short text, check our dictionary first
    if len(text.strip()) < 20 and text.lower().strip() in FALLBACK_PHRASES:
        return FALLBACK_PHRASES[text.lower().strip()]
    
    # Get full language name if available
    source_lang_name = LANGUAGE_MAP.get(source_lang, source_lang)
    
    # Construct our prompt with instructions for eloquent Arabic translation
    prompt = f"""Translate the following {source_lang_name} text into Modern Standard Arabic (Fusha).
Focus on conveying the meaning elegantly using proper Balagha (Arabic eloquence).
Adapt any cultural references or idioms appropriately rather than translating literally.
Ensure the translation reads naturally to a native Arabic speaker.

Text to translate:
{text}"""

    # Try multiple models in order of preference
    models_to_try = [
        "Helsinki-NLP/opus-mt-en-ar",  # specialized English-Arabic translator
        "facebook/nllb-200-distilled-600M",  # multilingual model
        "t5-base",  # general-purpose model that can follow instructions
        "google/mt5-small"  # small multilingual model
    ]
    
    for model in models_to_try:
        try:
            print(f"Attempting translation using Hugging Face model: {model}")
            
            # Update API URL for current model
            api_url = f"https://api-inference.huggingface.co/models/{model}"
            
            # Prepare request payload based on model type
            if "opus-mt" in model:
                # Helsinki NMT models use direct input
                payload = {"inputs": text}
            elif "nllb" in model:
                # NLLB models need language tags
                src_lang_code = source_lang if source_lang != "auto" else "eng_Latn"
                payload = {
                    "inputs": text,
                    "parameters": {
                        "source_lang": src_lang_code,
                        "target_lang": "arb_Arab"
                    }
                }
            else:
                # T5 and other instruction-following models use our prompt
                payload = {"inputs": prompt}
            
            # Make the API call
            response = requests.post(api_url, headers=HF_HEADERS, json=payload, timeout=30)
            
            # Handle different response formats based on model
            if response.status_code == 200:
                result = response.json()
                
                # Extract translated text based on response structure
                translated_text = None
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and "generated_text" in result[0]:
                        translated_text = result[0]["generated_text"]
                    elif isinstance(result[0], dict) and "translation_text" in result[0]:
                        translated_text = result[0]["translation_text"]
                    else:
                        translated_text = str(result[0])
                elif isinstance(result, dict) and "generated_text" in result:
                    translated_text = result["generated_text"]
                    
                if translated_text:
                    print(f"Translation successful using {model}")
                    # Apply post-processing
                    return culturally_adapt_arabic(translated_text)
                else:
                    print(f"Unexpected response format: {response.text}")
                    continue  # Try next model
            else:
                print(f"API error: {response.status_code}, {response.text}")
                continue  # Try next model
                
        except Exception as e:
            print(f"Error with model {model}: {e}")
            continue  # Try next model
    
    # If all models failed, try LibreTranslate as a backup
    try:
        print("Attempting LibreTranslate API as backup")
        libre_api = "https://translate.terraprint.co/translate"
        payload = {
            "q": text,
            "source": source_lang if source_lang != "auto" else "auto",
            "target": target_lang,
            "format": "text"
        }
        
        response = requests.post(libre_api, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            translated_text = result.get("translatedText")
            if translated_text:
                return culturally_adapt_arabic(translated_text)
    except Exception as e:
        print(f"LibreTranslate backup failed: {e}")
    
    # All translation attempts failed, use fallback
    fallback_text = FALLBACK_PHRASES.get(text.lower().strip()) if len(text.strip()) < 20 else None
    
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
    """Extracts text content from uploaded files without writing to disk."""
    content = await file.read()  # Read file content into memory
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
                raise HTTPException(status_code=501, detail="DOCX processing requires 'python-docx' library, which is not installed.")
                
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
                raise HTTPException(status_code=501, detail="PDF processing requires 'PyMuPDF' library, which is not installed.")
                
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        print(f"Extracted text length: {len(extracted_text)}")
        return extracted_text

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error processing file {file.filename}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred processing the document: {e}")

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    if not os.path.exists(TEMPLATE_DIR):
         raise HTTPException(status_code=500, detail=f"Template directory not found at {TEMPLATE_DIR}")
    if not os.path.exists(os.path.join(TEMPLATE_DIR, "index.html")):
         raise HTTPException(status_code=500, detail=f"index.html not found in {TEMPLATE_DIR}")
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
    
    if target_lang != "ar":
         raise HTTPException(status_code=400, detail="Currently, only translation to Arabic (ar) is supported via this endpoint.")

    try:
        translated_text = translate_text_internal(text, source_lang, target_lang)
        return JSONResponse(content={"translated_text": translated_text, "source_lang": source_lang})
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in /translate/text: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during text translation: {e}")

@app.post("/translate/document")
async def translate_document_endpoint(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form("ar")
):
    """Translates text extracted from an uploaded document without saving to disk."""
    if target_lang != "ar":
         raise HTTPException(status_code=400, detail="Currently, only document translation to Arabic (ar) is supported.")

    try:
        # Extract text directly from the uploaded file
        extracted_text = await extract_text_from_file(file)
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="Could not extract any text from the document.")

        # Translate the extracted text
        translated_text = translate_text_internal(extracted_text, source_lang, target_lang)

        return JSONResponse(content={
            "original_filename": file.filename,
            "detected_source_lang": source_lang,
            "translated_text": translated_text
        })

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred processing the document: {e}")

# --- Run the server (for local development) ---
if __name__ == "__main__":
    import uvicorn
    print(f"Template Directory: {TEMPLATE_DIR}")
    print(f"Static Directory: {STATIC_DIR}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
