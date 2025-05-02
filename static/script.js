document.addEventListener('DOMContentLoaded', () => {
    console.log("Translation app initialized");
    
    // Get form elements - only get the base forms on page load
    const textForm = document.getElementById('text-translation-form');
    const docForm = document.getElementById('doc-translation-form');
    
    // Simple function to show errors
    function showError(message) {
        const errorDiv = document.getElementById('error-message');
        if (errorDiv) {
            errorDiv.textContent = "Error: " + message;
            errorDiv.style.display = 'block';
            console.error("Error:", message);
        } else {
            alert("Error: " + message);
            console.error("Error div not found. Error:", message);
        }
    }
    
    // Simple function to show debug information
    function showDebug(message) {
        console.log("DEBUG:", message);
        const debugDiv = document.getElementById('debug-info');
        if (debugDiv) {
            debugDiv.textContent = typeof message === 'string' ? message : JSON.stringify(message, null, 2);
            debugDiv.style.display = 'block';
        }
    }
    
    // Clear all feedback elements
    function clearFeedback() {
        const elements = ['error-message', 'debug-info', 'text-result'];
        elements.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.style.display = 'none';
                if (id !== 'text-result') el.textContent = '';
            }
        });
    }
    
    // Add text form submission handler
    if (textForm) {
        textForm.addEventListener('submit', function(e) {
            e.preventDefault();
            clearFeedback();
            
            try {
                // Find form elements when needed, not earlier
                const textInput = document.getElementById('text-input');
                const sourceLang = document.getElementById('source-lang-text');
                const targetLang = document.getElementById('target-lang-text');
                const textLoading = document.getElementById('text-loading');
                
                // Debug which elements were found/not found
                const foundElements = {
                    textInput: !!textInput,
                    sourceLang: !!sourceLang,
                    targetLang: !!targetLang,
                    textLoading: !!textLoading
                };
                showDebug("Found elements: " + JSON.stringify(foundElements));
                
                // Check if elements exist
                if (!textInput || !sourceLang || !targetLang) {
                    showError("Required form elements not found");
                    return;
                }
                
                // Get values safely
                const text = textInput.value ? textInput.value.trim() : '';
                if (!text) {
                    showError("Please enter text to translate");
                    return;
                }
                
                // Show loading state if element exists
                if (textLoading) textLoading.style.display = 'block';
                
                // Prepare request data
                const requestData = {
                    text: text,
                    source_lang: sourceLang.value,
                    target_lang: targetLang.value
                };
                
                // Debug the request data
                showDebug("Sending request: " + JSON.stringify(requestData));
                
                // Use simple promise then/catch for better browser compatibility
                fetch('/translate/text', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                })
                .then(response => {
                    // First check if response is ok
                    if (!response.ok) {
                        throw new Error('Server returned ' + response.status);
                    }
                    return response.text();
                })
                .then(responseText => {
                    // Parse the response text
                    showDebug("Got response: " + responseText);
                    
                    let data;
                    try {
                        data = JSON.parse(responseText);
                    } catch (err) {
                        throw new Error('Invalid JSON response');
                    }
                    
                    // Check for translation result
                    if (data && data.translated_text) {
                        // Display the result
                        const resultBox = document.getElementById('text-result');
                        const outputEl = document.getElementById('text-output');
                        
                        if (resultBox && outputEl) {
                            outputEl.textContent = data.translated_text;
                            resultBox.style.display = 'block';
                        } else {
                            throw new Error('Result display elements not found');
                        }
                    } else {
                        throw new Error(data.error || 'No translation result returned');
                    }
                })
                .catch(error => {
                    showError(error.message || "Translation failed");
                    console.error("Translation error:", error);
                })
                .finally(() => {
                    // Hide loading indicator
                    if (textLoading) textLoading.style.display = 'none';
                });
                
            } catch (error) {
                showError(error.message || "An unexpected error occurred");
                console.error("General error:", error);
                
                // Ensure loading indicator is hidden
                const textLoading = document.getElementById('text-loading');
                if (textLoading) textLoading.style.display = 'none';
            }
        });
    } else {
        console.error("Text translation form not found!");
    }

    // Document translation handler with similar approach
    if (docForm) {
        docForm.addEventListener('submit', function(e) {
            e.preventDefault();
            clearFeedback();
            
            try {
                const fileInput = document.getElementById('doc-input');
                const loadingIndicator = document.getElementById('doc-loading');
                
                if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                    showError("Please select a document to upload");
                    return;
                }
                
                if (loadingIndicator) loadingIndicator.style.display = 'block';
                
                // Create form data
                const formData = new FormData(docForm);
                
                fetch('/translate/document', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) throw new Error('Server returned ' + response.status);
                    return response.text();
                })
                .then(responseText => {
                    showDebug("Document response: " + responseText);
                    
                    let data;
                    try {
                        data = JSON.parse(responseText);
                    } catch (err) {
                        throw new Error('Invalid JSON response');
                    }
                    
                    if (!data || !data.translated_text) {
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
                    } else {
                        throw new Error('Result display elements not found');
                    }
                })
                .catch(error => {
                    showError(error.message || "Document translation failed");
                })
                .finally(() => {
                    if (loadingIndicator) loadingIndicator.style.display = 'none';
                    const button = docForm.querySelector('button');
                    if (button) {
                        button.disabled = false;
                        button.textContent = 'Translate Document';
                    }
                });
                
            } catch (error) {
                showError(error.message || "An unexpected error occurred");
                console.error("Document error:", error);
                
                const loadingIndicator = document.getElementById('doc-loading');
                if (loadingIndicator) loadingIndicator.style.display = 'none';
            }
        });
    } else {
        console.error("Document translation form not found!");
    }
});
