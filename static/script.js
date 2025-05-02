document.addEventListener('DOMContentLoaded', () => {
    // Log when the page loads to confirm JavaScript is working
    console.log("Translation app initialized");
    
    // Safely get DOM elements with error handling
    function safeGetElement(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.error(`Element not found: #${id}`);
        }
        return element;
    }
    
    const textForm = safeGetElement('text-translation-form');
    const docForm = safeGetElement('doc-translation-form');
    const textResultBox = safeGetElement('text-result');
    const textOutput = safeGetElement('text-output');
    const docResultBox = safeGetElement('doc-result');
    const docOutput = safeGetElement('doc-output');
    const docFilename = safeGetElement('doc-filename');
    const docSourceLang = safeGetElement('doc-source-lang');
    const errorMessageDiv = safeGetElement('error-message');
    const docLoadingIndicator = safeGetElement('doc-loading');
    const debugInfoDiv = safeGetElement('debug-info');
    
    // Create text loading indicator if it doesn't exist
    let textLoadingDiv = safeGetElement('text-loading');
    if (!textLoadingDiv && textForm) {
        console.log("Creating missing text loading indicator");
        textLoadingDiv = document.createElement('div');
        textLoadingDiv.id = 'text-loading';
        textLoadingDiv.className = 'loading-spinner';
        textLoadingDiv.textContent = 'Translating...';
        textForm.appendChild(textLoadingDiv);
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
            
            // Use correct field IDs matching the HTML and check if they exist
            const textInput = safeGetElement('text-input');
            const sourceLangSelect = safeGetElement('source-lang-text');
            const targetLangSelect = safeGetElement('target-lang-text');
            
            // Check all required elements exist before proceeding
            if (!textInput || !sourceLangSelect || !targetLangSelect) {
                displayError('One or more required form elements are missing. Check your HTML structure.');
                console.error('Missing elements:', 
                    !textInput ? 'text-input' : '', 
                    !sourceLangSelect ? 'source-lang-text' : '',
                    !targetLangSelect ? 'target-lang-text' : ''
                );
                return;
            }
            
            // Safely extract values
            const sourceText = textInput.value ? textInput.value.trim() : '';
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
            const fileInput = safeGetElement('doc-input');
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
        console.error("Document translation form not found in the document!");
    }
});
