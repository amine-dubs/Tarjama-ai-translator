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
    
    // Get quick phrases elements
    const quickPhrasesContainer = document.getElementById('quick-phrases');
    const quickPhraseButtons = document.querySelectorAll('.quick-phrase');
    
    // Control buttons
    const swapLangBtn = document.getElementById('swap-lang-btn');
    const copyTextBtn = document.getElementById('copy-text-btn');
    const clearTextBtn = document.getElementById('clear-text-btn');
    
    // RTL language handling - list of languages that use RTL
    const rtlLanguages = ['ar', 'he'];
    
    // Tab navigation
    if (textTabLink && docTabLink && textSection && docSection) {
        textTabLink.addEventListener('click', function(e) {
            e.preventDefault();
            docSection.style.display = 'none';
            textSection.style.display = 'block';
            textTabLink.parentElement.classList.add('active');
            docTabLink.parentElement.classList.remove('active');
        });
        
        docTabLink.addEventListener('click', function(e) {
            e.preventDefault();
            textSection.style.display = 'none';
            docSection.style.display = 'block';
            docTabLink.parentElement.classList.add('active');
            textTabLink.parentElement.classList.remove('active');
        });
    }
    
    // Character count
    if (textInput && charCountElement) {
        textInput.addEventListener('input', function() {
            const charCount = textInput.value.length;
            charCountElement.textContent = `${charCount}`;
            
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
    if (quickPhraseButtons && quickPhraseButtons.length > 0) {
        quickPhraseButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const phrase = this.getAttribute('data-phrase');
                
                if (phrase && textInput) {
                    // Insert the phrase at cursor position, or append to end
                    if (typeof textInput.selectionStart === 'number') {
                        const startPos = textInput.selectionStart;
                        const endPos = textInput.selectionEnd;
                        const currentValue = textInput.value;
                        const spaceChar = currentValue && currentValue[startPos - 1] !== ' ' ? ' ' : '';
                        
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
                        const spaceChar = currentValue && currentValue[currentValue.length - 1] !== ' ' ? ' ' : '';
                        textInput.value += spaceChar + phrase;
                    }
                    
                    // Trigger input event to update character count
                    const inputEvent = new Event('input', { bubbles: true });
                    textInput.dispatchEvent(inputEvent);
                    
                    // Focus back on the input
                    textInput.focus();
                }
            });
        });
    }
    
    // Language swap functionality
    if (swapLangBtn && sourceLangText && targetLangText) {
        swapLangBtn.addEventListener('click', function(e) {
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
                const clickEvent = new Event('click');
                document.querySelector('#translate-text-btn').dispatchEvent(clickEvent);
            }
            
            // Apply RTL styling as needed
            applyRtlStyling(sourceLangText.value, textInput);
            applyRtlStyling(targetLangText.value, textOutput);
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
    if (copyTextBtn) {
        copyTextBtn.addEventListener('click', function() {
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
    
    // Clear text functionality
    if (clearTextBtn) {
        clearTextBtn.addEventListener('click', function() {
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
            
            const fileInput = document.getElementById('doc-input');
            if (!fileInput.files || fileInput.files.length === 0) {
                showNotification('Please select a document to translate.');
                return;
            }
            
            const file = fileInput.files[0];
            const sourceLang = sourceLangDoc.value;
            const targetLang = targetLangDoc.value;
            
            translateDocument(file, sourceLang, targetLang);
        });
    }
    
    // File drag and drop 
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('doc-input');
    
    if (dropZone && fileInput) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropZone.classList.add('highlight');
        }
        
        function unhighlight() {
            dropZone.classList.remove('highlight');
        }
        
        dropZone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files && files.length > 0) {
                fileInput.files = files;
                const fileName = files[0].name;
                fileNameDisplay.textContent = fileName;
                fileNameDisplay.style.display = 'block';
                docFilename.value = fileName;
            }
        }
        
        // Handle file selection through the input
        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                const fileName = this.files[0].name;
                fileNameDisplay.textContent = fileName;
                fileNameDisplay.style.display = 'block';
                docFilename.value = fileName;
            } else {
                fileNameDisplay.textContent = '';
                fileNameDisplay.style.display = 'none';
                docFilename.value = '';
            }
        });
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
                
                // Enable copy button
                if (copyTextBtn) copyTextBtn.disabled = false;
                
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
            if (errorMessageElement) {
                errorMessageElement.style.display = 'block';
                errorMessageElement.textContent = `Translation error: ${error.message}`;
            }
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
            }
            // Update filename and detected language
            if (docFilename) docFilename.textContent = data.original_filename || '';
            if (docSourceLang) docSourceLang.textContent = (data.detected_source_lang ? getLanguageName(data.detected_source_lang) : getLanguageName(sourceLang));
        })
        .catch(error => {
            console.error('Error during document translation:', error);
            
            if (docLoadingIndicator) docLoadingIndicator.style.display = 'none';
            
            // Show error message
            if (errorMessageElement) {
                errorMessageElement.style.display = 'block';
                errorMessageElement.textContent = `Document translation error: ${error.message}`;
            }
        });
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
    
    // Initialize by applying RTL styling based on initial language selection
    handleLanguageChange();
};
