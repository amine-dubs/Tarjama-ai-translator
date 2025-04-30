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
    
    // Helper function to display errors
    function displayError(message) {
        let errorText = 'Error: ';
        
        if (message === undefined || message === null) {
            errorText += 'Unknown error occurred';
        } else if (typeof message === 'object') {
            // Better error object handling
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
    }

    // Handle Text Translation Form Submission
    textForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        clearFeedback();

        const formData = new FormData(textForm);
        const button = textForm.querySelector('button');
        button.disabled = true;
        button.textContent = 'Translating...';

        try {
            console.log('Sending translation request...');
            
            // Create JSON payload from FormData instead of sending FormData directly
            const payload = {
                text: formData.get('text'),
                source_lang: formData.get('source_lang'),
                target_lang: formData.get('target_lang')
            };
            
            const response = await fetch('/translate/text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            console.log('Response received:', response.status, response.statusText);

            if (!response.ok) {
                let errorMessage;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || `HTTP error! status: ${response.status}`;
                } catch (jsonError) {
                    errorMessage = `HTTP error! status: ${response.status}. Failed to parse error response.`;
                }
                throw new Error(errorMessage);
            }

            console.log('Processing response...');
            const result = await response.json();
            console.log('Parsed JSON result:', result);

            if (!result.translated_text) {
                console.error('Missing translated_text in response:', result);
                throw new Error('Server response missing translated text');
            }

            textOutput.textContent = result.translated_text;
            textResultBox.style.display = 'block';
            // Set text direction for Arabic
            textOutput.dir = 'rtl';

        } catch (error) {
            console.error('Text translation error:', error);
            // Always pass error.message instead of the error object
            displayError(error.message || 'An unexpected error occurred during text translation.');
        } finally {
            button.disabled = false;
            button.textContent = 'Translate Text';
        }
    });

    // Handle Document Translation Form Submission
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

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('Document translation response:', result); // Added debug logging
            
            // Check if result contains the expected fields
            if (!result.translated_text) {
                throw new Error('Translation response is missing translated text');
            }
            
            docFilename.textContent = result.original_filename || 'N/A';
            docSourceLang.textContent = result.detected_source_lang || 'N/A';
            docOutput.textContent = result.translated_text;
            docResultBox.style.display = 'block';

        } catch (error) {
            console.error('Document translation error:', error);
            // Always pass error.message instead of the error object
            displayError(error.message || 'An unexpected error occurred during document translation.');
        } finally {
            button.disabled = false;
            button.textContent = 'Translate Document';
            // Hide loading indicator
            docLoadingIndicator.style.display = 'none';
        }
    });
});
