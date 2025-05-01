document.addEventListener('DOMContentLoaded', () => {
    const textForm = document.getElementById('text-translation-form');
    const docForm = document.getElementById('doc-translation-form');
    const textResultBox = document.getElementById('text-result');
    const textOutput = document.getElementById('text-output');
    const docResultBox = document.getElementById('doc-result');
    const docOutput = document.getElementById('doc-output');
    const docFilename = document.getElementById('doc-filename');
    const docSourceLang = document.getElementById('doc-source-lang');
    const errorMessageDiv = document.getElementById('error-message');
    const docLoadingIndicator = document.getElementById('doc-loading');
    const debugInfoDiv = document.getElementById('debug-info');
    const textLoadingDiv = document.getElementById('text-loading');
    
    // Helper function to display debug info
    function showDebug(message, data = null) {
        let debugText = typeof message === 'string' ? message : JSON.stringify(message);
        
        if (data) {
            debugText += '\n' + JSON.stringify(data, null, 2);
        }
        
        console.log("DEBUG:", message, data || '');
        debugInfoDiv.textContent = debugText;
        debugInfoDiv.style.display = 'block';
    }
    
    // Helper function to display errors
    function displayError(message) {
        let errorText = 'Error: ';
        
        if (message === undefined || message === null) {
            errorText += 'Unknown error occurred';
        } else if (typeof message === 'object') {
            // Improved error object handling
            if (message.message) {
                errorText += message.message;
            } else if (message.detail) {
                errorText += message.detail;
            } else if (message.error) {
                errorText += message.error;
            } else {
                try {
                    errorText += JSON.stringify(message);
                } catch (e) {
                    errorText += 'Unable to display error details';
                }
            }
        } else {
            errorText += message;
        }
        
        console.error("Error details:", message);
        errorMessageDiv.textContent = errorText;
        errorMessageDiv.style.display = 'block';
        
        // Hide result boxes on error
        textResultBox.style.display = 'none';
        docResultBox.style.display = 'none';
    }

    // Helper function to clear errors and results
    function clearFeedback() {
        errorMessageDiv.style.display = 'none';
        errorMessageDiv.textContent = '';
        textResultBox.style.display = 'none';
        textOutput.textContent = '';
        docResultBox.style.display = 'none';
        docOutput.textContent = '';
        docFilename.textContent = '';
        docSourceLang.textContent = '';
        docLoadingIndicator.style.display = 'none';
        debugInfoDiv.style.display = 'none';
        debugInfoDiv.textContent = '';
    }

    // Fix the text form submission handler
    if (textForm) {
        textForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearFeedback();
            
            // Use correct field IDs matching the HTML
            const sourceText = document.getElementById('text-input').value.trim();
            const sourceLang = document.getElementById('source-lang-text').value;
            const targetLang = document.getElementById('target-lang-text').value;
            
            if (!sourceText) {
                displayError('Please enter text to translate');
                return;
            }
            
            try {
                // Show loading state 
                textLoadingDiv.style.display = 'block';
                
                // Log payload for debugging
                const payload = { 
                    text: sourceText, 
                    source_lang: sourceLang, 
                    target_lang: targetLang 
                };
                showDebug('Sending translation request', payload);
                
                const response = await fetch('/translate/text', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                // Log response status
                showDebug(`Response status: ${response.status}`);
                
                // Get the raw response text first for debugging
                const responseText = await response.text();
                showDebug('Raw response:', responseText);
                
                // Then parse it as JSON
                let data;
                try {
                    data = JSON.parse(responseText);
                } catch (jsonError) {
                    throw new Error(`Invalid JSON response: ${responseText}`);
                }
                
                // Hide loading state
                textLoadingDiv.style.display = 'none';
                
                if (!response.ok) {
                    if (data && data.error) {
                        displayError(data.error);
                    } else {
                        displayError(`Server error: ${response.status}`);
                    }
                    return;
                }
                
                if (!data.success && data.error) {
                    displayError(data.error);
                    return;
                }
                
                if (!data.translated_text) {
                    displayError('Translation returned empty text');
                    return;
                }
                
                textOutput.textContent = data.translated_text;
                textResultBox.style.display = 'block';
                
            } catch (error) {
                console.error('Error:', error);
                displayError(`Network error: ${error.message}`);
                
                // Hide loading
                textLoadingDiv.style.display = 'none';
            }
        });
    } else {
        console.error("Text translation form not found in the document!");
    }

    // Handle Document Translation Form Submission
    if (docForm) {
        docForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearFeedback();

            const formData = new FormData(docForm);
            const fileInput = document.getElementById('doc-input');
            const button = docForm.querySelector('button');

            if (!fileInput.files || fileInput.files.length === 0) {
                displayError('Please select a document to upload.');
                return;
            }

            button.disabled = true;
            button.textContent = 'Translating...';
            // Show loading indicator
            docLoadingIndicator.style.display = 'block';

            try {
                const response = await fetch('/translate/document', {
                    method: 'POST',
                    body: formData // FormData handles multipart/form-data automatically
                });

                // Get response as text first for debugging
                const responseText = await response.text();
                showDebug('Raw document response:', responseText);
                
                // Try to parse as JSON
                let result;
                try {
                    result = JSON.parse(responseText);
                } catch (jsonError) {
                    throw new Error(`Failed to parse server response: ${responseText}`);
                }

                if (!response.ok) {
                    const errorMessage = result.error || result.detail || `HTTP error! status: ${response.status}`;
                    throw new Error(errorMessage);
                }
                
                showDebug('Document translation response:', result);
                
                // Check if result contains the expected fields
                if (!result.translated_text) {
                    throw new Error('Translation response is missing translated text');
                }
                
                docFilename.textContent = result.original_filename || 'N/A';
                docSourceLang.textContent = result.detected_source_lang || 'N/A';
                docOutput.textContent = result.translated_text;
                docResultBox.style.display = 'block';
                
                // Set text direction based on target language (document always goes to Arabic)
                docOutput.dir = 'rtl';

            } catch (error) {
                console.error('Document translation error:', error);
                displayError(error.message || 'An unexpected error occurred during document translation.');
            } finally {
                button.disabled = false;
                button.textContent = 'Translate Document';
                // Hide loading indicator
                docLoadingIndicator.style.display = 'none';
            }
        });
    } else {
        console.error("Document translation form not found in the document!");
    }
});
