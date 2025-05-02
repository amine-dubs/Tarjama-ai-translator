document.addEventListener('DOMContentLoaded', () => {
    // Log when the page loads to confirm JavaScript is working
    console.log("Translation app initialized");
    
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
    
    // Check if all elements are found
    if (!textForm) console.error("ERROR: Text translation form not found!");
    if (!textResultBox) console.error("ERROR: Text result box not found!");
    if (!textOutput) console.error("ERROR: Text output element not found!");
    if (!errorMessageDiv) console.error("ERROR: Error message div not found!");
    
    // Create text loading indicator if it doesn't exist
    let textLoadingDiv = document.getElementById('text-loading');
    if (!textLoadingDiv) {
        console.log("Creating missing text loading indicator");
        textLoadingDiv = document.createElement('div');
        textLoadingDiv.id = 'text-loading';
        textLoadingDiv.className = 'loading-spinner';
        textLoadingDiv.textContent = 'Translating...';
        if (textForm) {
            textForm.appendChild(textLoadingDiv);
        }
    }
    
    // Helper function to display debug info
    function showDebug(message, data = null) {
        let debugText = typeof message === 'string' ? message : JSON.stringify(message);
        
        if (data) {
            debugText += '\n' + JSON.stringify(data, null, 2);
        }
        
        console.log("DEBUG:", message, data || '');
        if (debugInfoDiv) {
            debugInfoDiv.textContent = debugText;
            debugInfoDiv.style.display = 'block';
        } else {
            console.error("Debug div not found!");
        }
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
        if (errorMessageDiv) {
            errorMessageDiv.textContent = errorText;
            errorMessageDiv.style.display = 'block';
            
            // Hide result boxes on error
            if (textResultBox) textResultBox.style.display = 'none';
            if (docResultBox) docResultBox.style.display = 'none';
        } else {
            // If error div not found, use alert as fallback
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

    // Fix the text form submission handler
    if (textForm) {
        console.log("Adding submit event listener to text form");
        textForm.addEventListener('submit', async (e) => {
            console.log("Form submitted!");
            e.preventDefault();
            clearFeedback();
            
            // Show debug immediately to confirm the handler is working
            showDebug('Translation submission triggered');
            
            // Use correct field IDs matching the HTML
            const textInput = document.getElementById('text-input');
            const sourceLangSelect = document.getElementById('source-lang-text');
            const targetLangSelect = document.getElementById('target-lang-text');
            
            if (!textInput) {
                displayError('Text input element not found!');
                return;
            }
            if (!sourceLangSelect) {
                displayError('Source language select not found!');
                return;
            }
            if (!targetLangSelect) {
                displayError('Target language select not found!');
                return;
            }
            
            const sourceText = textInput.value.trim();
            const sourceLang = sourceLangSelect.value;
            const targetLang = targetLangSelect.value;
            
            if (!sourceText) {
                displayError('Please enter text to translate');
                return;
            }
            
            try {
                // Show loading state 
                if (textLoadingDiv) textLoadingDiv.style.display = 'block';
                
                // Log payload for debugging
                const payload = { 
                    text: sourceText, 
                    source_lang: sourceLang, 
                    target_lang: targetLang 
                };
                showDebug('Sending translation request', payload);
                
                // Check if API is available
                try {
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
                        showDebug('JSON parse error:', jsonError);
                        throw new Error(`Invalid JSON response: ${responseText}`);
                    }
                    
                    // Hide loading state
                    if (textLoadingDiv) textLoadingDiv.style.display = 'none';
                    
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
                    
                    if (textOutput) {
                        textOutput.textContent = data.translated_text;
                        if (textResultBox) textResultBox.style.display = 'block';
                    } else {
                        displayError('Text output element not found!');
                    }
                    
                } catch (fetchError) {
                    console.error('Fetch error:', fetchError);
                    displayError(`Network error: ${fetchError.message}. Make sure the backend server is running.`);
                }
            } catch (error) {
                console.error('General error:', error);
                displayError(`Error: ${error.message}`);
                
                // Hide loading
                if (textLoadingDiv) textLoadingDiv.style.display = 'none';
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
