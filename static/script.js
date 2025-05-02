document.addEventListener('DOMContentLoaded', () => {
    // Log when the page loads to confirm JavaScript is working
    console.log("Translation app initialized");
    
    // Get references to main form elements
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
    
    // Helper function for debugging
    function showDebug(message, data = null) {
        let debugText = typeof message === 'string' ? message : JSON.stringify(message);
        if (data) {
            debugText += '\n' + JSON.stringify(data, null, 2);
        }
        console.log("DEBUG:", message, data || '');
        if (debugInfoDiv) {
            debugInfoDiv.textContent = debugText;
            debugInfoDiv.style.display = 'block';
        }
    }
    
    // Helper function to display errors
    function displayError(message) {
        let errorText = 'Error: ';
        if (message === undefined || message === null) {
            errorText += 'Unknown error occurred';
        } else if (typeof message === 'object') {
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
        if (errorMessageDiv) {
            errorMessageDiv.textContent = errorText;
            errorMessageDiv.style.display = 'block';
            if (textResultBox) textResultBox.style.display = 'none';
            if (docResultBox) docResultBox.style.display = 'none';
        } else {
            alert("Error: " + errorText);
        }
    }

    // Helper function to clear errors and results
    function clearFeedback() {
        if (errorMessageDiv) {
            errorMessageDiv.style.display = 'none';
            errorMessageDiv.textContent = '';
        }
        if (textResultBox) {
            textResultBox.style.display = 'none';
            if (textOutput) textOutput.textContent = '';
        }
        if (docResultBox) {
            docResultBox.style.display = 'none';
            if (docOutput) docOutput.textContent = '';
            if (docFilename) docFilename.textContent = '';
            if (docSourceLang) docSourceLang.textContent = '';
        }
        if (docLoadingIndicator) docLoadingIndicator.style.display = 'none';
        if (debugInfoDiv) {
            debugInfoDiv.style.display = 'none';
            debugInfoDiv.textContent = '';
        }
    }

    // Text translation form handler
    if (textForm) {
        textForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            clearFeedback();
            showDebug('Translation form submitted');
            
            try {
                // IMPORTANT: Get the input elements directly by their IDs inside this function
                // This ensures the elements are found at the time the form is submitted
                const textInput = document.getElementById('text-input');
                const sourceLangSelect = document.getElementById('source-lang-text');
                const targetLangSelect = document.getElementById('target-lang-text');
                
                if (!textInput) {
                    throw new Error('Text input element not found');
                }
                if (!sourceLangSelect) {
                    throw new Error('Source language select not found');
                }
                if (!targetLangSelect) {
                    throw new Error('Target language select not found');
                }
                
                const sourceText = textInput.value ? textInput.value.trim() : '';
                if (!sourceText) {
                    displayError('Please enter text to translate');
                    return;
                }
                
                const sourceLang = sourceLangSelect.value;
                const targetLang = targetLangSelect.value;
                
                showDebug('Form values:', {
                    text: sourceText,
                    sourceLang: sourceLang,
                    targetLang: targetLang
                });
                
                // Show loading indication
                if (textLoadingDiv) {
                    textLoadingDiv.style.display = 'block';
                }
                
                // Prepare payload
                const payload = { 
                    text: sourceText, 
                    source_lang: sourceLang, 
                    target_lang: targetLang 
                };
                showDebug('Sending translation request', payload);
                
                // Send API request
                const response = await fetch('/translate/text', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                // Get and process response
                const responseText = await response.text();
                showDebug('Raw response:', responseText);
                let data;
                
                try {
                    data = JSON.parse(responseText);
                } catch (error) {
                    throw new Error(`Invalid JSON response: ${responseText}`);
                }
                
                if (!response.ok) {
                    if (data && data.error) {
                        throw new Error(data.error);
                    } else {
                        throw new Error(`Server error: ${response.status}`);
                    }
                }
                
                if (!data.success && data.error) {
                    throw new Error(data.error);
                }
                
                if (!data.translated_text) {
                    throw new Error('Translation returned empty text');
                }
                
                // Display result
                if (textOutput && textResultBox) {
                    textOutput.textContent = data.translated_text;
                    textResultBox.style.display = 'block';
                } else {
                    throw new Error('Result display elements not found');
                }
                
            } catch (error) {
                console.error('Translation error:', error);
                displayError(error.message || 'An unexpected error occurred');
            } finally {
                if (textLoadingDiv) {
                    textLoadingDiv.style.display = 'none';
                }
            }
        });
    } else {
        console.error("Text translation form not found!");
    }

    // Document translation form handler - similar approach
    if (docForm) {
        docForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearFeedback();

            const formData = new FormData(docForm);
            const fileInput = document.getElementById('doc-input');
            const button = docForm.querySelector('button');

            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
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
        console.error("Document translation form not found!");
    }
});
