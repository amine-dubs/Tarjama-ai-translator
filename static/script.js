// Wait for the DOM to be fully loaded before attaching event handlers
window.onload = function() {
    console.log('Window fully loaded, initializing Tarjama app');
    
    // Get navigation elements
    const textTabLink = document.querySelector('nav ul li a[href="#text-translation"]');
    const docTabLink = document.querySelector('nav ul li a[href="#document-translation"]');
    const textSection = document.getElementById('text-translation');
    const docSection = document.getElementById('document-translation');
    
    // Get form elements
    const textTranslationForm = document.getElementById('text-translation-form');
    const docTranslationForm = document.getElementById('doc-translation-form');
    
    // UI elements
    const textInput = document.getElementById('text-input');
    const textResult = document.getElementById('text-result');
    const docResult = document.getElementById('doc-result');
    const textOutput = document.getElementById('text-output');
    const docOutput = document.getElementById('doc-output');
    const docInputText = document.getElementById('doc-input-text');
    const textLoadingIndicator = document.getElementById('text-loading');
    const docLoadingIndicator = document.getElementById('doc-loading');
    const errorMessageElement = document.getElementById('error-message');
    const notificationElement = document.getElementById('notification');
    const charCountElement = document.getElementById('char-count');
    const fileNameDisplay = document.getElementById('file-name-display');
    const docFilename = document.getElementById('doc-filename');
    const docSourceLang = document.getElementById('doc-source-lang');
    
    // Language selectors
    const sourceLangText = document.getElementById('source-lang-text');
    const targetLangText = document.getElementById('target-lang-text');
    const sourceLangDoc = document.getElementById('source-lang-doc');
    const targetLangDoc = document.getElementById('target-lang-doc');
    
    // Control buttons
    const swapLanguages = document.getElementById('swap-languages');
    const swapLanguagesDoc = document.getElementById('swap-languages-doc');
    const copyTranslation = document.getElementById('copy-translation');
    const copyDocTranslation = document.getElementById('copy-doc-translation');
    const clearSource = document.getElementById('clear-source');
    
    // Get quick phrases elements
    const phraseButtons = document.querySelectorAll('.phrase-btn');
    
    // RTL language handling - list of languages that use RTL
    const rtlLanguages = ['ar', 'he'];
    
    // Tab navigation
    if (textTabLink && docTabLink && textSection && docSection) {
        textTabLink.addEventListener('click', function(e) {
            e.preventDefault();
            docSection.classList.add('hidden');
            textSection.classList.remove('hidden');
            textTabLink.parentElement.classList.add('active');
            docTabLink.parentElement.classList.remove('active');
        });
        
        docTabLink.addEventListener('click', function(e) {
            e.preventDefault();
            textSection.classList.add('hidden');
            docSection.classList.remove('hidden');
            docTabLink.parentElement.classList.add('active');
            textTabLink.parentElement.classList.remove('active');
        });
    }
    
    // Character count
    if (textInput && charCountElement) {
        textInput.addEventListener('input', function() {
            const charCount = textInput.value.length;
            charCountElement.textContent = charCount;
            
            // Add warning class if approaching or exceeding character limit
            if (charCount > 3000) {
                charCountElement.className = 'char-count-warning';
            } else if (charCount > 2000) {
                charCountElement.className = 'char-count-approaching';
            } else {
                charCountElement.className = '';
            }
        });
    }
    
    // Quick phrases implementation
    if (phraseButtons && phraseButtons.length > 0) {
        console.log('Found phrase buttons:', phraseButtons.length);
        phraseButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Phrase button clicked');
                const phrase = this.getAttribute('data-text') || this.getAttribute('data-phrase');
                
                if (phrase && textInput) {
                    console.log('Using phrase:', phrase);
                    // First ensure text section is visible
                    if (textSection.classList.contains('hidden')) {
                        console.log('Switching to text tab');
                        docSection.classList.add('hidden');
                        textSection.classList.remove('hidden');
                        textTabLink.parentElement.classList.add('active');
                        docTabLink.parentElement.classList.remove('active');
                    }
                    
                    // Insert the phrase at cursor position, or append to end
                    if (typeof textInput.selectionStart === 'number') {
                        const startPos = textInput.selectionStart;
                        const endPos = textInput.selectionEnd;
                        const currentValue = textInput.value;
                        const spaceChar = currentValue && currentValue[startPos - 1] !== ' ' && startPos > 0 ? ' ' : '';
                        
                        // Insert phrase at cursor position with space if needed
                        textInput.value = currentValue.substring(0, startPos) + 
                                          spaceChar + phrase + 
                                          currentValue.substring(endPos);
                                          
                        // Move cursor after inserted phrase
                        textInput.selectionStart = startPos + phrase.length + spaceChar.length;
                        textInput.selectionEnd = textInput.selectionStart;
                    } else {
                        // Fallback for browsers that don't support selection
                        const currentValue = textInput.value;
                        const spaceChar = currentValue && currentValue.length > 0 && currentValue[currentValue.length - 1] !== ' ' ? ' ' : '';
                        textInput.value += spaceChar + phrase;
                    }
                    
                    // Trigger input event to update character count
                    const inputEvent = new Event('input', { bubbles: true });
                    textInput.dispatchEvent(inputEvent);
                    
                    // Focus back on the input
                    textInput.focus();
                    
                    // Auto translate if needed
                    const autoTranslate = this.getAttribute('data-auto-translate') === 'true';
                    if (autoTranslate && textTranslationForm) {
                        textTranslationForm.dispatchEvent(new Event('submit'));
                    }
                }
            });
        });
    }
    
    // Language swap functionality
    if (swapLanguages && sourceLangText && targetLangText) {
        swapLanguages.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Don't swap if source is "auto" (language detection)
            if (sourceLangText.value === 'auto') {
                showNotification('Cannot swap when source language is set to auto-detect.');
                return;
            }
            
            // Store the current values
            const sourceValue = sourceLangText.value;
            const targetValue = targetLangText.value;
            
            // Swap the values
            sourceLangText.value = targetValue;
            targetLangText.value = sourceValue;
            
            // If we have translated text, trigger a new translation in the opposite direction
            if (textOutput.textContent.trim() !== '') {
                // Update the input with the current output
                textInput.value = textOutput.textContent;
                
                // Update the character count 
                const inputEvent = new Event('input', { bubbles: true });
                textInput.dispatchEvent(inputEvent);
                
                // Trigger translation
                if (textTranslationForm) {
                    textTranslationForm.dispatchEvent(new Event('submit'));
                }
            }
            
            // Apply RTL styling as needed
            applyRtlStyling(sourceLangText.value, textInput);
            applyRtlStyling(targetLangText.value, textOutput);
        });
    }
    
    // Document language swap functionality
    if (swapLanguagesDoc && sourceLangDoc && targetLangDoc) {
        swapLanguagesDoc.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Don't swap if source is "auto" (language detection)
            if (sourceLangDoc.value === 'auto') {
                showNotification('Cannot swap when source language is set to auto-detect.');
                return;
            }
            
            // Store the current values
            const sourceValue = sourceLangDoc.value;
            const targetValue = targetLangDoc.value;
            
            // Swap the values
            sourceLangDoc.value = targetValue;
            targetLangDoc.value = sourceValue;
        });
    }
    
    // Apply RTL styling based on language
    function applyRtlStyling(langCode, element) {
        if (element) {
            if (rtlLanguages.includes(langCode)) {
                element.style.direction = 'rtl';
                element.style.textAlign = 'right';
            } else {
                element.style.direction = 'ltr';
                element.style.textAlign = 'left';
            }
        }
    }
    
    // Handle language change for proper text direction
    function handleLanguageChange() {
        // Set text direction based on selected source language
        if (sourceLangText && textInput) {
            applyRtlStyling(sourceLangText.value, textInput);
        }
        
        // Set text direction based on selected target language
        if (targetLangText && textOutput) {
            applyRtlStyling(targetLangText.value, textOutput);
        }
        
        if (sourceLangDoc && docInputText) {
            applyRtlStyling(sourceLangDoc.value, docInputText);
        }
        
        if (targetLangDoc && docOutput) {
            applyRtlStyling(targetLangDoc.value, docOutput);
        }
    }
    
    // Add event listeners for language changes
    if (sourceLangText) sourceLangText.addEventListener('change', handleLanguageChange);
    if (targetLangText) targetLangText.addEventListener('change', handleLanguageChange);
    if (sourceLangDoc) sourceLangDoc.addEventListener('change', handleLanguageChange);
    if (targetLangDoc) targetLangDoc.addEventListener('change', handleLanguageChange);
    
    // Copy translation to clipboard functionality
    if (copyTranslation) {
        copyTranslation.addEventListener('click', function() {
            if (textOutput && textOutput.textContent.trim() !== '') {
                navigator.clipboard.writeText(textOutput.textContent)
                    .then(() => {
                        showNotification('Translation copied to clipboard!');
                    })
                    .catch(err => {
                        console.error('Error copying text: ', err);
                        showNotification('Failed to copy text. Please try again.');
                    });
            }
        });
    }
    
    // Copy document translation to clipboard
    if (copyDocTranslation) {
        copyDocTranslation.addEventListener('click', function() {
            if (docOutput && docOutput.textContent.trim() !== '') {
                navigator.clipboard.writeText(docOutput.textContent)
                    .then(() => {
                        showNotification('Document translation copied to clipboard!');
                    })
                    .catch(err => {
                        console.error('Error copying document: ', err);
                        showNotification('Failed to copy document. Please try again.');
                    });
            }
        });
    }
    
    // Clear text functionality
    if (clearSource) {
        clearSource.addEventListener('click', function() {
            if (textInput) {
                textInput.value = '';
                textOutput.textContent = '';
                
                // Update character count
                const inputEvent = new Event('input', { bubbles: true });
                textInput.dispatchEvent(inputEvent);
                
                // Focus back on the input
                textInput.focus();
            }
        });
    }
    
    // File input handler - Update UI when file is selected
    const fileInput = document.getElementById('doc-input');
    const translateDocumentBtn = document.querySelector('#doc-translation-form .translate-button');
    
    if (fileInput && fileNameDisplay && translateDocumentBtn) {
        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                const fileName = this.files[0].name;
                fileNameDisplay.textContent = `File selected: ${fileName}`;
                fileNameDisplay.style.display = 'block';
                
                // Make translate button colored
                translateDocumentBtn.classList.add('active-button');
                
                showNotification('Document uploaded successfully!');
            } else {
                fileNameDisplay.textContent = '';
                fileNameDisplay.style.display = 'none';
                
                // Make translate button transparent
                translateDocumentBtn.classList.remove('active-button');
            }
        });
    }
    
    // Text translation form submission
    if (textTranslationForm) {
        textTranslationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const text = textInput.value.trim();
            if (!text) {
                showNotification('Please enter text to translate.');
                return;
            }
            
            const sourceLang = sourceLangText.value;
            const targetLang = targetLangText.value;
            
            translateText(text, sourceLang, targetLang);
        });
    }
    
    // Document translation form submission
    if (docTranslationForm) {
        docTranslationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const file = document.getElementById('doc-input').files[0];
            if (!file) {
                showError('Please select a document to translate.');
                return;
            }
            
            const sourceLang = document.getElementById('doc-source-lang').value;
            const targetLang = document.getElementById('doc-target-lang').value;
            
            translateDocument(file, sourceLang, targetLang);
        });
    } else {
        console.error('Document translation form not found.');
    }
    
    // File drag and drop 
    const fileUploadArea = document.querySelector('.file-upload-area');
    
    if (fileUploadArea && fileInput) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            fileUploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            fileUploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            fileUploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            fileUploadArea.classList.add('highlight');
        }
        
        function unhighlight() {
            fileUploadArea.classList.remove('highlight');
        }
        
        fileUploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files && files.length > 0) {
                fileInput.files = files;
                const fileName = files[0].name;
                fileNameDisplay.textContent = `File selected: ${fileName}`;
                fileNameDisplay.style.display = 'block';
                
                // Make translate button colored
                if (translateDocumentBtn) {
                    translateDocumentBtn.classList.add('active-button');
                }
                
                showNotification('Document uploaded successfully!');
            }
        }
    }
    
    // Text translation function
    function translateText(text, sourceLang, targetLang) {
        if (textLoadingIndicator) textLoadingIndicator.style.display = 'block';
        if (errorMessageElement) errorMessageElement.style.display = 'none';
        
        // Call the API
        fetch('/translate/text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                source_lang: sourceLang,
                target_lang: targetLang
            }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (textLoadingIndicator) textLoadingIndicator.style.display = 'none';
            
            if (data.success === false) {
                throw new Error(data.error || 'Translation failed with an unknown error');
            }
            
            // Handle language detection result if present
            if (data.detected_source_lang && sourceLang === 'auto') {
                showNotification(`Detected language: ${getLanguageName(data.detected_source_lang)}`);
                
                // Optionally update the source language dropdown to show the detected language
                if (sourceLangText && data.detected_source_lang) {
                    // Just for UI feedback - no need to change the actual value since 
                    // we want to keep 'auto' selected for future translations
                    const detectedOption = Array.from(sourceLangText.options).find(
                        option => option.value === data.detected_source_lang
                    );
                    
                    if (detectedOption) {
                        // Visual indication of detected language
                        sourceLangText.parentElement.setAttribute('data-detected', 
                            `Detected: ${detectedOption.text}`);
                    }
                }
            }
            
            // Show translation result
            if (textOutput) {
                textOutput.textContent = data.translated_text;
                
                // Apply RTL styling based on target language
                applyRtlStyling(targetLang, textOutput);
            }
            
            // Show the text result container if it was hidden
            if (textResult) textResult.style.display = 'block';
        })
        .catch(error => {
            console.error('Error during translation:', error);
            
            if (textLoadingIndicator) textLoadingIndicator.style.display = 'none';
            
            // Show error message
            showError(`Translation error: ${error.message}`);
        });
    }
    
    // Document translation function
    function translateDocument(file, sourceLang, targetLang) {
        if (docLoadingIndicator) docLoadingIndicator.style.display = 'block';
        if (errorMessageElement) errorMessageElement.style.display = 'none';
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('source_lang', sourceLang);
        formData.append('target_lang', targetLang);
        
        fetch('/translate/document', {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (docLoadingIndicator) docLoadingIndicator.style.display = 'none';
            
            if (data.success === false) {
                throw new Error(data.error || 'Document translation failed');
            }
            
            // Handle language detection result if present
            if (data.detected_source_lang && sourceLang === 'auto') {
                showNotification(`Detected document language: ${getLanguageName(data.detected_source_lang)}`);
            }
            
            // Show the original text
            if (docInputText) {
                docInputText.textContent = data.original_text;
                // Apply RTL styling based on source language
                if (data.detected_source_lang && sourceLang === 'auto') {
                    applyRtlStyling(data.detected_source_lang, docInputText);
                } else {
                    applyRtlStyling(sourceLang, docInputText);
                }
            }

            // Show the translated text
            if (docOutput) {
                docOutput.textContent = data.translated_text;
                // Apply RTL styling based on target language
                applyRtlStyling(targetLang, docOutput);
            }

            // Show the document result container
            if (docResult) {
                docResult.classList.remove('hidden');
                docResult.style.display = 'flex'; // Ensure the result is visible
            }
            
            // Update filename and detected language
            if (docFilename) docFilename.textContent = data.original_filename || file.name;
            if (docSourceLang) docSourceLang.textContent = (data.detected_source_lang ? getLanguageName(data.detected_source_lang) : getLanguageName(sourceLang));
            
            // Add download button
            const resultArea = document.querySelector('.document-result-area');
            if (resultArea) {
                // Remove existing download button if there was one
                const existingDownloadBtn = document.getElementById('download-translated-doc');
                if (existingDownloadBtn) {
                    existingDownloadBtn.remove();
                }
                
                // Create download button
                const downloadBtn = document.createElement('button');
                downloadBtn.id = 'download-translated-doc';
                downloadBtn.className = 'download-button';
                downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Translation';
                
                // Add event listener for download
                downloadBtn.addEventListener('click', function() {
                    downloadTranslatedDocument(data.translated_text, file.name, file.type);
                });
                
                // Append to result area
                resultArea.appendChild(downloadBtn);
            }
        })
        .catch(error => {
            console.error('Error during document translation:', error);
            
            if (docLoadingIndicator) docLoadingIndicator.style.display = 'none';
            
            // Show error message
            showError(`Document translation error: ${error.message}`);
        });
    }
    
    // Function to download translated document
    function downloadTranslatedDocument(content, fileName, fileType) {
        // Determine file extension
        let extension = fileName.endsWith('.pdf') ? '.pdf' : 
                        fileName.endsWith('.docx') ? '.docx' : '.txt';
        
        // Create translated filename
        const baseName = fileName.substring(0, fileName.lastIndexOf('.'));
        const translatedFileName = `${baseName}_translated${extension}`;
        
        // For PDF files, try the browser's native PDF generation when it contains Arabic
        if (extension === '.pdf' && /[\u0600-\u06FF]/.test(content)) {
            console.log('Using browser PDF generation for Arabic content');
            
            // Create HTML for printing
            const printWindow = window.open('', '_blank');
            
            if (printWindow) {
                // Create a document with RTL support for Arabic
                printWindow.document.write(`
                    <!DOCTYPE html>
                    <html dir="rtl">
                    <head>
                        <meta charset="UTF-8">
                        <title>${translatedFileName}</title>
                        <style>
                            @page { margin: 1.5cm; }
                            body {
                                font-family: 'Arial', 'Segoe UI', 'Tahoma', sans-serif;
                                line-height: 1.5;
                                direction: rtl;
                                text-align: right;
                                padding: 20px;
                                font-size: 14pt;
                            }
                            .content {
                                white-space: pre-wrap;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="content">${content}</div>
                        <script>
                            // Auto-print and close when done
                            window.onload = function() {
                                setTimeout(function() {
                                    window.print();
                                    // Wait for print dialog to close
                                    setTimeout(function() {
                                        window.close();
                                    }, 500);
                                }, 500);
                            };
                        </script>
                    </body>
                    </html>
                `);
                
                // Show a notification
                showNotification('Print dialog will open. Select "Save as PDF" option to download your translation.');
                return;
            } else {
                // Fallback if popup is blocked
                showError('Popup blocked. Please allow popups and try again.');
            }
        }
        
        if (extension === '.txt') {
            // Direct browser download for text files
            const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            triggerDownload(url, translatedFileName);
        } else {
            // Server-side processing for complex formats
            fetch('/download/translated-document', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    filename: translatedFileName,
                    original_type: fileType
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                triggerDownload(url, translatedFileName);
            })
            .catch(error => {
                showError(`Error downloading file: ${error.message}`);
            });
        }
    }
    
    function triggerDownload(url, filename) {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    // Helper function to get language name from code
    function getLanguageName(code) {
        // Hard-coded mapping for common languages
        const langMap = {
            'ar': 'Arabic',
            'en': 'English', 
            'fr': 'French',
            'es': 'Spanish',
            'de': 'German',
            'zh': 'Chinese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'hi': 'Hindi',
            'auto': 'Auto-detect'
        };
        
        // Try to get from our map
        if (langMap[code]) {
            return langMap[code];
        }
        
        // Try to get from the select option text
        if (sourceLangText) {
            const option = Array.from(sourceLangText.options).find(opt => opt.value === code);
            if (option) {
                return option.text;
            }
        }
        
        // Fallback to code
        return code;
    }
    
    // Display notification
    function showNotification(message) {
        if (notificationElement) {
            notificationElement.textContent = message;
            notificationElement.style.display = 'block';
            notificationElement.classList.add('show');
            
            // Hide after 3 seconds
            setTimeout(() => {
                notificationElement.classList.remove('show');
                setTimeout(() => {
                    notificationElement.style.display = 'none';
                }, 300);
            }, 3000);
        }
    }
    
    // Display error message
    function showError(message) {
        if (errorMessageElement) {
            errorMessageElement.textContent = message;
            errorMessageElement.style.display = 'block';
            
            // Hide after 5 seconds
            setTimeout(() => {
                errorMessageElement.style.display = 'none';
            }, 5000);
        }
    }
    
    // Initialize by applying RTL styling based on initial language selection
    handleLanguageChange();
};
