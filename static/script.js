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
    }

    // Handle Text Translation Form Submission
    textForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        clearFeedback();

        const formData = new FormData(textForm);
        const button = textForm.querySelector('button');
        const textInput = document.getElementById('text-input');
        
        // Validation check
        if (!textInput.value.trim()) {
            displayError('Please enter text to translate');
            return;
        }
        
        button.disabled = true;
        button.textContent = 'Translating...';

        try {
            console.log('Sending translation request...');
            
            // Create JSON payload from FormData
            const payload = {
                text: formData.get('text'),
                source_lang: formData.get('source_lang'),
                target_lang: formData.get('target_lang')
            };
            
            console.log('Payload:', payload);
            
            const response = await fetch('/translate/text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            console.log('Response status:', response.status, response.statusText);
            
            // Get response data as text first for debugging
            const responseText = await response.text();
            console.log('Raw response:', responseText);
            
            // Try to parse as JSON
            let data;
            try {
                data = responseText ? JSON.parse(responseText) : null;
            } catch (parseError) {
                console.error('Error parsing JSON response:', parseError);
                throw new Error(`Failed to parse server response: ${responseText}`);
            }
            
            if (!data) {
                throw new Error('Server returned empty response');
            }
            
            // Check if the response indicates an error
            if (!response.ok) {
                const errorMsg = data.error || data.detail || 'Unknown server error';
                throw new Error(errorMsg);
            }
            
            // Check if we have actual translated text
            if (data.success === false || !data.translated_text) {
                throw new Error(data.error || 'No translation returned from server');
            }
            
            // Display the translation results
            textOutput.textContent = data.translated_text;
            textResultBox.style.display = 'block';
            
        } catch (error) {
            console.error('Translation error:', error);
            displayError(error);
        } finally {
            button.disabled = false;
            button.textContent = 'Translate';
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

            // Get response as text first for debugging
            const responseText = await response.text();
            console.log('Raw document response:', responseText);
            
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
            
            console.log('Document translation response:', result);
            
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
});
