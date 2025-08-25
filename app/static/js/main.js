// Main JavaScript file for e-learning system

// Global variables
let currentLessonType = 'video';
let ckEditorInstance = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeLessonForm();
    initializeCKEditor();
    initializeTooltips();
    initializeFormValidation();
});

// Initialize lesson form functionality
function initializeLessonForm() {
    const lessonTypeSelect = document.getElementById('lesson_type');
    if (lessonTypeSelect) {
        lessonTypeSelect.addEventListener('change', handleLessonTypeChange);
        handleLessonTypeChange(); // Initial call
    }
}

// Handle lesson type change
function handleLessonTypeChange() {
    const lessonType = document.getElementById('lesson_type')?.value?.toLowerCase() || 'video';
    currentLessonType = lessonType;
    
    // Hide all content groups
    const contentGroups = [
        'content_url_group',
        'video_file_group',
        'quiz_builder_group',
        'assignment_builder_group',
        'text_editor_group',
        'content_data_group'
    ];
    
    contentGroups.forEach(groupId => {
        const group = document.getElementById(groupId);
        if (group) {
            group.style.display = 'none';
        }
    });
    
    // Show relevant groups based on type
    switch (lessonType) {
        case 'video':
            showGroups(['content_url_group', 'video_file_group']);
            break;
        case 'text':
            showGroups(['text_editor_group']);
            break;
        case 'quiz':
            showGroups(['quiz_builder_group']);
            break;
        case 'assignment':
            showGroups(['assignment_builder_group']);
            break;
        default:
            showGroups(['content_url_group', 'video_file_group', 'quiz_builder_group', 'assignment_builder_group', 'text_editor_group', 'content_data_group']);
    }
}

// Show specific groups
function showGroups(groupIds) {
    groupIds.forEach(groupId => {
        const group = document.getElementById(groupId);
        if (group) {
            group.style.display = 'block';
        }
    });
}

// Initialize CKEditor
function initializeCKEditor() {
    const editorElement = document.getElementById('ckeditor');
    if (!editorElement) return;
    
    // Check if CKEditor is already loaded
    if (typeof ClassicEditor === 'undefined') {
        console.warn('CKEditor not loaded yet, retrying in 1 second...');
        setTimeout(initializeCKEditor, 1000);
        return;
    }
    
    ClassicEditor
        .create(editorElement, {
            toolbar: {
                items: [
                    'heading',
                    '|',
                    'bold',
                    'italic',
                    'underline',
                    'strikethrough',
                    '|',
                    'fontSize',
                    'fontFamily',
                    'fontColor',
                    'fontBackgroundColor',
                    '|',
                    'alignment',
                    '|',
                    'numberedList',
                    'bulletedList',
                    '|',
                    'indent',
                    'outdent',
                    '|',
                    'link',
                    'blockQuote',
                    'insertTable',
                    'mediaEmbed',
                    '|',
                    'undo',
                    'redo',
                    '|',
                    'code',
                    'codeBlock',
                    '|',
                    'removeFormat'
                ]
            },
            language: 'vi',
            table: {
                contentToolbar: [
                    'tableColumn',
                    'tableRow',
                    'mergeTableCells',
                    'tableCellProperties',
                    'tableProperties'
                ]
            },
            mediaEmbed: {
                previewsInData: true
            },
            link: {
                addTargetToExternalLinks: true,
                defaultProtocol: 'https://'
            },
            placeholder: 'Nhập nội dung bài học ở đây...'
        })
        .then(editor => {
            ckEditorInstance = editor;
            window.__ckeditor = editor;
            
            // Load existing content if available
            loadExistingContent(editor);
            
            // Auto-save content changes
            editor.model.document.on('change:data', () => {
                autoSaveContent(editor);
            });
            
            // Add custom event listeners
            editor.ui.focusTracker.on('change:isFocused', (evt, data, isFocused) => {
                if (isFocused) {
                    editor.element.classList.add('ck-focused');
                } else {
                    editor.element.classList.remove('ck-focused');
                }
            });
            
            console.log('CKEditor initialized successfully');
        })
        .catch(error => {
            console.error('CKEditor initialization failed:', error);
            showNotification('Không thể khởi tạo trình soạn thảo. Vui lòng tải lại trang.', 'error');
        });
}

// Load existing content into editor
function loadExistingContent(editor) {
    try {
        const textarea = document.querySelector('textarea[name="content_data"]');
        if (textarea && textarea.value) {
            const data = JSON.parse(textarea.value);
            if (data && (data.html || data.text)) {
                editor.setData(data.html || data.text);
                console.log('Existing content loaded into CKEditor');
            }
        }
    } catch (error) {
        console.log('No existing content to load or invalid format');
    }
}

// Auto-save content changes
function autoSaveContent(editor) {
    if (currentLessonType === 'text') {
        const html = editor.getData();
        const textarea = document.querySelector('textarea[name="content_data"]');
        if (textarea) {
            const obj = { html: html };
            textarea.value = JSON.stringify(obj, null, 2);
        }
    }
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Utility function to get lesson type
function getCurrentLessonType() {
    return currentLessonType;
}

// Utility function to get CKEditor instance
function getCKEditorInstance() {
    return ckEditorInstance;
}

// Export functions for global use
window.eLearningSystem = {
    getCurrentLessonType,
    getCKEditorInstance,
    showNotification,
    handleLessonTypeChange
};
