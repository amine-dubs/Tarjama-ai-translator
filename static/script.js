// Wait for the DOM to be fully loaded before attaching event handlers
window.onload = function() {
    console.log('Window fully loaded, initializing translation app');
    
    // Get form elements ONCE after load
    const textTranslationForm = document.querySelector('#text-translation-form');
    const docTranslationForm = document.querySelector('#doc-translation-form');
    
    // Get text form OUTPUT elements ONCE
    const textLoadingElement = document.getElementById('text-loading');
    const debugElement = document.getElementById('debug-info');
    const errorElement = document.getElementById('error-message');
    const textResultBox = document.getElementById('text-result');
    const textOutputElement = document.getElementById('text-output');

    // Check if essential text elements were found on load (excluding inputs used via FormData)
    if (!textTranslationForm) { // Only check form itself now
        console.error('CRITICAL: Text translation form not found on window load!');
        if (errorElement) {
            errorElement.textContent = 'Error: Could not find the text translation form element. Check HTML ID.';
            errorElement.style.display = 'block';
        }
        return; 
    }
    
    // Set up text translation form
    console.log('Text translation form found on load');
    textTranslationForm.addEventListener('submit', function(event) {
        event.preventDefault();
        console.log('Text translation form submitted');
        
        // Hide previous results/errors
        if (textResultBox) textResultBox.style.display = 'none';
        if (errorElement) errorElement.style.display = 'none';
        if (debugElement) debugElement.style.display = 'none';
        
        // --- Use FormData Approach --- 
        try {
            const formData = new FormData(event.target); // event.target is the form
            
            // Get values using the 'name' attributes from the HTML
            const text = formData.get('text') ? formData.get('text').trim() : '';
            const sourceLangValue = formData.get('source_lang');
            const targetLangValue = formData.get('target_lang');
            
            console.log('[DEBUG] FormData values - Text:', text, 'Source:', sourceLangValue, 'Target:', targetLangValue);

            if (!text) {
                showError('Please enter text to translate');
                return;
            }
            
            if (!sourceLangValue || !targetLangValue) {
                console.error('Could not read language values from FormData!');
                showError('Internal error: Language selection missing.');
                return;
            }
            
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

        } catch (e) {
            console.error('FATAL: Error processing form data or submitting:', e);
            showError('Internal error processing form submission. Check console.');
        }
        // --- End FormData Approach ---
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
