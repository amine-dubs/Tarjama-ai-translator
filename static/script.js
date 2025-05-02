// Wait for the DOM to be fully loaded before attaching event handlers
window.onload = function() {
    console.log('Window fully loaded, initializing translation app');
    
    // Get form elements ONCE after load
    const textTranslationForm = document.querySelector('#text-translation-form');
    const docTranslationForm = document.querySelector('#doc-translation-form');
    
    // Get text form INPUT elements ONCE
    const textInput = document.getElementById('text-input');
    const sourceLangText = document.getElementById('source-lang-text');
    const targetLangText = document.getElementById('target-lang-text');
    const textLoadingElement = document.getElementById('text-loading');
    const debugElement = document.getElementById('debug-info');
    const errorElement = document.getElementById('error-message');
    const textResultBox = document.getElementById('text-result');
    const textOutputElement = document.getElementById('text-output');

    // Check if essential text elements were found on load
    if (!textTranslationForm || !textInput || !sourceLangText || !targetLangText) {
        console.error('CRITICAL: Essential text form elements not found on window load!', {
            form: !!textTranslationForm,
            input: !!textInput,
            source: !!sourceLangText,
            target: !!targetLangText
        });
        if (errorElement) {
            errorElement.textContent = 'Error: Could not find essential text translation form elements. Check HTML IDs.';
            errorElement.style.display = 'block';
        }
        // Optionally disable the form if elements are missing
        if (textTranslationForm) textTranslationForm.style.opacity = '0.5'; 
        return; // Stop further initialization if critical elements missing
    }
    
    // Set up text translation form
    console.log('Text translation form and elements found on load');
    textTranslationForm.addEventListener('submit', function(event) {
        event.preventDefault();
        console.log('Text translation form submitted');
        
        // Hide previous results/errors
        if (textResultBox) textResultBox.style.display = 'none';
        if (errorElement) errorElement.style.display = 'none';
        if (debugElement) debugElement.style.display = 'none';
        
        // **Crucial Check:** Verify elements still exist before use
        if (!textInput || !sourceLangText || !targetLangText) {
             console.error('ERROR: Text form elements became null before accessing value!');
             showError('Internal error: Form elements missing unexpectedly.');
             return;
        }
        
        // Get values
        const text = textInput.value ? textInput.value.trim() : '';
        if (!text) {
            showError('Please enter text to translate');
            return;
        }
        
        const sourceLangValue = sourceLangText.value;
        const targetLangValue = targetLangText.value;
        
        // Show loading indicator
        if (textLoadingElement) textLoadingElement.style.display = 'block';
        
        // Create payload
        const payload = {
            text: text,
            source_lang: sourceLangValue,
            target_lang: targetLangValue
        };
        
        console.log('Sending payload:', payload);
        
        // Send API request
        fetch('/translate/text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) throw new Error('Server error: ' + response.status);
            return response.text(); // Get raw text first
        })
        .then(responseText => {
            console.log('Response received:', responseText);
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (error) {
                console.error("Failed to parse JSON:", responseText);
                throw new Error('Invalid response format from server');
            }
            
            if (!data.success || !data.translated_text) {
                throw new Error(data.error || 'No translation returned or success flag false');
            }
            
            // Show result
            if (textResultBox && textOutputElement) {
                textOutputElement.textContent = data.translated_text;
                textResultBox.style.display = 'block';
            }
        })
        .catch(error => {
            showError(error.message || 'Translation failed');
            console.error('Error:', error);
        })
        .finally(() => {
            if (textLoadingElement) textLoadingElement.style.display = 'none';
        });
    });
    
    // Document translation handler
    if (docTranslationForm) {
        console.log('Document translation form found on load');
        docTranslationForm.addEventListener('submit', function(event) {
            event.preventDefault();
            console.log('Document translation form submitted');
            
            // Clear previous results and errors
            document.querySelectorAll('#doc-result, #error-message').forEach(el => {
                if (el) el.style.display = 'none';
            });
            
            // Get form elements
            const fileInput = docTranslationForm.querySelector('#doc-input');
            const loadingIndicator = document.querySelector('#doc-loading');
            
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                showError('Please select a document to upload');
                return;
            }
            
            // Show loading indicator
            if (loadingIndicator) loadingIndicator.style.display = 'block';
            
            // Create form data
            const formData = new FormData(docTranslationForm);
            
            // Make API request
            fetch('/translate/document', {
                method: 'POST',
                body: formData
            })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}`);
                }
                return response.json();
            })
            .then(function(data) {
                if (!data.translated_text) {
                    throw new Error('No translation returned');
                }
                
                // Display result
                const resultBox = document.querySelector('#doc-result');
                const outputEl = document.querySelector('#doc-output');
                const filenameEl = document.querySelector('#doc-filename');
                const sourceLangEl = document.querySelector('#doc-source-lang');
                
                if (resultBox && outputEl) {
                    if (filenameEl) filenameEl.textContent = data.original_filename || 'N/A';
                    if (sourceLangEl) sourceLangEl.textContent = data.detected_source_lang || 'N/A';
                    outputEl.textContent = data.translated_text;
                    resultBox.style.display = 'block';
                }
            })
            .catch(function(error) {
                showError(error.message);
            })
            .finally(function() {
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
            });
        });
    } else {
        console.error('Document translation form not found on load!');
    }
    
    // Helper function to show errors
    function showError(message) {
        if (errorElement) {
            errorElement.textContent = 'Error: ' + message;
            errorElement.style.display = 'block';
        }
        console.error('Error displayed:', message);
    }
};
