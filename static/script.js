// Wait for the DOM to be fully loaded before attaching event handlers
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, initializing translation app');
    
    // Get form elements
    const textTranslationForm = document.getElementById('text-translation-form');
    const docTranslationForm = document.getElementById('doc-translation-form');
    
    // Set up text translation form
    if (textTranslationForm) {
        console.log('Text translation form found');
        textTranslationForm.onsubmit = handleTextTranslation;
    } else {
        console.error('Text translation form not found!');
    }
    
    // Set up document translation form
    if (docTranslationForm) {
        console.log('Document translation form found');
        docTranslationForm.onsubmit = handleDocTranslation;
    } else {
        console.error('Document translation form not found!');
    }
    
    // Function to handle text translation
    function handleTextTranslation(event) {
        event.preventDefault();
        console.log('Text translation form submitted');
        
        // Clear previous results and errors
        hideElement('text-result');
        hideElement('error-message');
        hideElement('debug-info');
        
        // Get form elements
        const textInputElement = document.getElementById('text-input');
        const sourceLangElement = document.getElementById('source-lang-text');
        const targetLangElement = document.getElementById('target-lang-text');
        const loadingElement = document.getElementById('text-loading');
        const debugElement = document.getElementById('debug-info');
        
        // Debug which elements were found
        let debug = 'Found elements: ';
        debug += textInputElement ? 'text-input ✓ ' : 'text-input ✗ ';
        debug += sourceLangElement ? 'source-lang-text ✓ ' : 'source-lang-text ✗ ';
        debug += targetLangElement ? 'target-lang-text ✓ ' : 'target-lang-text ✗ ';
        console.log(debug);
        
        // Show debug info
        if (debugElement) {
            debugElement.textContent = debug;
            debugElement.style.display = 'block';
        }
        
        // Check for missing elements
        if (!textInputElement || !sourceLangElement || !targetLangElement) {
            showError('One or more form elements are missing');
            return;
        }
        
        // Get text input
        const textInput = textInputElement.value ? textInputElement.value.trim() : '';
        if (!textInput) {
            showError('Please enter text to translate');
            return;
        }
        
        // Get language selections
        const sourceLang = sourceLangElement.value;
        const targetLang = targetLangElement.value;
        
        // Show loading indicator
        if (loadingElement) {
            loadingElement.style.display = 'block';
        }
        
        // Create request payload
        const payload = {
            text: textInput,
            source_lang: sourceLang, 
            target_lang: targetLang
        };
        
        // Make the API request
        fetch('/translate/text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.text();
        })
        .then(function(responseText) {
            // Show response in debug
            if (debugElement) {
                debugElement.textContent += '\n\nResponse: ' + responseText;
            }
            
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (error) {
                throw new Error('Invalid JSON response from server');
            }
            
            if (!data.translated_text && !data.success) {
                throw new Error(data.error || 'No translation returned');
            }
            
            // Show the result
            const resultBox = document.getElementById('text-result');
            const outputElement = document.getElementById('text-output');
            if (resultBox && outputElement) {
                outputElement.textContent = data.translated_text;
                resultBox.style.display = 'block';
            }
        })
        .catch(function(error) {
            showError(error.message);
            console.error('Translation error:', error);
        })
        .finally(function() {
            // Hide loading indicator
            if (loadingElement) {
                loadingElement.style.display = 'none';
            }
        });
    }
    
    // Function to handle document translation
    function handleDocTranslation(event) {
        event.preventDefault();
        console.log('Document translation form submitted');
        
        // Clear previous results and errors
        hideElement('doc-result');
        hideElement('error-message');
        
        // Get form elements
        const fileInput = document.getElementById('doc-input');
        const loadingIndicator = document.getElementById('doc-loading');
        
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            showError('Please select a document to upload');
            return;
        }
        
        // Show loading indicator
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
        
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
            const resultBox = document.getElementById('doc-result');
            const outputEl = document.getElementById('doc-output');
            const filenameEl = document.getElementById('doc-filename');
            const sourceLangEl = document.getElementById('doc-source-lang');
            
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
    }
    
    // Helper function to show errors
    function showError(message) {
        const errorDiv = document.getElementById('error-message');
        if (errorDiv) {
            errorDiv.textContent = 'Error: ' + message;
            errorDiv.style.display = 'block';
        }
        console.error('Error:', message);
    }
    
    // Helper function to hide elements
    function hideElement(id) {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = 'none';
        }
    }
});
