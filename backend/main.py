from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import List, Optional
import shutil

# Placeholder for translation logic
# from transformers import pipeline # Uncomment when implementing translation

# --- Configuration ---
# Determine the base directory of the main.py script
# This helps in locating templates and static files correctly, especially in Docker
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust paths to go one level up from backend to find templates/static
TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), "templates")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")
UPLOAD_DIR = os.path.join(os.path.dirname(BASE_DIR), "uploads") # Place uploads outside backend

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
# translator = pipeline("translation", model="Helsinki-NLP/opus-mt-en-ar") # Example model

# --- Helper Functions ---
def translate_text_internal(text: str, source_lang: str, target_lang: str = "ar") -> str:
    """Internal function to handle text translation using the loaded model."""
    # Refined Prompt based on user request
    prompt = f"""Translate the following text from {source_lang} to Arabic (Modern Standard Arabic - Fusha) precisely. Do not provide a literal translation; focus on conveying the meaning accurately while respecting Arabic eloquence (balagha) by rephrasing if necessary:

{text}"""

    # --- Actual Translation Logic (using Hugging Face pipeline) ---
    # This part needs to be implemented based on the chosen model's API
    # Example using a generic pipeline (replace with actual model call):
    # try:
    #     # Note: Standard pipelines might not directly support complex prompts like this.
    #     # You might need custom model loading and generation logic.
    #     # result = translator(prompt, src_lang=source_lang, tgt_lang=target_lang) # Adjust based on model
    #     # translated_text = result[0]['translation_text']
    #     # --- Placeholder ---
    #     print(f"Simulating translation for prompt: {prompt}") # Log the prompt being used
    #     translated_text = f"Translated: {text} (from {source_lang} to {target_lang})" # Replace with actual translation
    #     return translated_text
    # except Exception as e:
    #     print(f"Error during translation: {e}")
    #     raise HTTPException(status_code=500, detail=f"Translation failed: {e}")
    # --- End Placeholder ---

    # --- Simplified Placeholder ---
    print(f"Using Prompt: {prompt}")
    # Simulate translation for now
    return f"[Simulated Translation of '{text}' from {source_lang} to MSA Arabic, focusing on meaning and eloquence]"
    # --- End Simplified Placeholder ---


def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extracts text from various document types."""
    text = ""
    try:
        if file_type == "application/pdf":
            import fitz  # PyMuPDF
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from docx import Document
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            import openpyxl
            workbook = openpyxl.load_workbook(file_path)
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value:
                            text += str(cell.value) + " "
                    text += "\n" # Newline after each row
        elif file_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            from pptx import Presentation
            prs = Presentation(file_path)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
        # Add handling for plain text files
        elif file_type.startswith("text/"):
             with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                 text = f.read()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}. Cannot extract text.")

    except ImportError as ie:
         print(f"Import error for {file_type}: {ie}. Make sure the required library is installed.")
         # Ensure temp file is cleaned up even if import fails
         if os.path.exists(file_path):
             os.remove(file_path)
         raise HTTPException(status_code=501, detail=f"Text extraction for {file_type} requires an additional library: {ie.name}. Please install it (check requirements.txt). The file was not processed.")
    except Exception as e:
        print(f"Error extracting text from {file_path} ({file_type}): {e}")
        # Ensure temp file is cleaned up on extraction error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to extract text from file: {e}")

    # Do not remove the file here; let the calling function handle cleanup after translation
    return text

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
        extracted_text = extract_text_from_file(temp_file_path, file.content_type)
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
