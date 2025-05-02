// Wait for the DOM to be fully loaded before attaching event handlers
window.onload = function() {
    console.log('Window fully loaded, initializing translation app');
    
    // Get form elements using direct form access instead of getElementById
    const textTranslationForm = document.querySelector('#text-translation-form');
    const docTranslationForm = document.querySelector('#doc-translation-form');
    
    // Set up text translation form
    if (textTranslationForm) {
        console.log('Text translation form found');
        
        // Use standard form submit event
        textTranslationForm.addEventListener('submit', function(event) {
            event.preventDefault();
            console.log('Text translation form submitted');
            
            // Clear previous results and errors
            document.querySelectorAll('#text-result, #error-message, #debug-info').forEach(el => {
                if (el) el.style.display = 'none';
            });
            
            // Get form elements directly from the form itself
            const textInput = textTranslationForm.querySelector('#text-input');
            const sourceLang = textTranslationForm.querySelector('#source-lang-text');
            const targetLang = textTranslationForm.querySelector('#target-lang-text');
            const loadingElement = document.querySelector('#text-loading');
            const debugElement = document.querySelector('#debug-info');
            
            // Log which elements were found
            console.log('Elements found:', {
                textInput: !!textInput,
                sourceLang: !!sourceLang,
                targetLang: !!targetLang
            });
            
            // Show debug info
            if (debugElement) {
                debugElement.textContent = `Form elements found: 
                    text-input: ${!!textInput}
                    source-lang-text: ${!!sourceLang}
                    target-lang-text: ${!!targetLang}`;
                debugElement.style.display = 'block';
            }
            
            // Check for missing elements
            if (!textInput || !sourceLang || !targetLang) {
                showError('Form elements not found. Please check the HTML structure.');
                return;
            }
            
            // Get values
            const text = textInput.value ? textInput.value.trim() : '';
            if (!text) {
                showError('Please enter text to translate');
                return;
            }
            
            // Get language selections
            const sourceLangValue = sourceLang.value;
            const targetLangValue = targetLang.value;
            
            // Show loading indicator
            if (loadingElement) loadingElement.style.display = 'block';
            
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
            .then(function(response) {
                if (!response.ok) throw new Error('Server error: ' + response.status);
                return response.text();
            })
            .then(function(responseText) {
                console.log('Response received:', responseText);
                
                // Try to parse JSON
                let data;
                try {
                    data = JSON.parse(responseText);
                } catch (error) {
                    throw new Error('Invalid response from server');
                }
                
                // Check for translation
                if (!data.translated_text) {
                    throw new Error('No translation returned');
                }
                
                // Show result
                const resultBox = document.querySelector('#text-result');
                const outputElement = document.querySelector('#text-output');
                
                if (resultBox && outputElement) {
                    outputElement.textContent = data.translated_text;
                    resultBox.style.display = 'block';
                }
            })
            .catch(function(error) {
                showError(error.message || 'Translation failed');
                console.error('Error:', error);
            })
            .finally(function() {
                if (loadingElement) loadingElement.style.display = 'none';
            });
        });
    } else {
        console.error('Text translation form not found in the document!');
    }
    
    // Document translation handler
    if (docTranslationForm) {
        console.log('Document translation form found');
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
        console.error('Document translation form not found in the document!');
    }
    
    // Helper function to show errors
    function showError(message) {
        const errorDiv = document.querySelector('#error-message');
        if (errorDiv) {
            errorDiv.textContent = 'Error: ' + message;
            errorDiv.style.display = 'block';
        }
        console.error('Error:', message);
    }
};
