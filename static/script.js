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
        errorMessageDiv.textContent = `Error: ${message}`;
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
            const response = await fetch('/translate/text', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            textOutput.textContent = result.translated_text;
            textResultBox.style.display = 'block';
            // Optionally update language direction based on result if needed
            // textResultBox.dir = result.target_lang === 'ar' ? 'rtl' : 'ltr';

        } catch (error) {
            console.error('Text translation error:', error);
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
            displayError(error.message || 'An unexpected error occurred during document translation.');
        } finally {
            button.disabled = false;
            button.textContent = 'Translate Document';
            // Hide loading indicator
            docLoadingIndicator.style.display = 'none';
        }
    });
});
