// Main JavaScript for Job Fraud Detector

document.addEventListener('DOMContentLoaded', function() {
    initializeForm();
    initializeCharCounters();
    initializeFormValidation();
    initializeDynamicFields();
    initializeScoreProgress();
});

// Form Initialization

function initializeForm() {
    const form = document.getElementById('predictionForm');
    if (!form) return;

    form.addEventListener('submit', handleFormSubmit);
    form.addEventListener('reset', handleFormReset);
    
    // Handle checkbox values for form submission
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (!this.checked) {
                // Create a hidden input with value 0 when unchecked
                const hiddenInput = document.createElement('input');
                hiddenInput.type = 'hidden';
                hiddenInput.name = this.name;
                hiddenInput.value = '0';
                this.parentNode.appendChild(hiddenInput);
            } else {
                // Remove hidden input when checked
                const hiddenInput = this.parentNode.querySelector(`input[type="hidden"][name="${this.name}"]`);
                if (hiddenInput) {
                    hiddenInput.remove();
                }
            }
        });
    });
}

function handleFormReset(event) {
    // Reset dynamic fields back to dropdowns
    const dynamicWrappers = document.querySelectorAll('.dynamic-field-wrapper');
    dynamicWrappers.forEach(wrapper => {
        const select = wrapper.querySelector('.dynamic-select');
        const textInput = wrapper.querySelector('.dynamic-input');
        
        // Reset to select
        select.style.display = 'block';
        select.disabled = false;
        select.name = wrapper.getAttribute('data-field-name');
        
        // Hide and clear text input
        textInput.style.display = 'none';
        textInput.disabled = true;
        textInput.value = '';
        textInput.name = '';
        
        // Reset select value if it was set to __OTHER__
        if (select.value === '__OTHER__') {
            select.value = select.querySelector('option:not([value="__OTHER__"])').value;
        }
    });
}

// Character Counters

function initializeCharCounters() {
    const textareas = {
        'description': 'desc-count',
        'requirements': 'req-count',
        'company_profile': 'profile-count',
        'benefits': 'benefits-count'
    };

    Object.keys(textareas).forEach(textareaId => {
        const textarea = document.getElementById(textareaId);
        const counter = document.getElementById(textareas[textareaId]);
        
        if (textarea && counter) {
            updateCharCount(textarea, counter);
            textarea.addEventListener('input', function() {
                updateCharCount(this, counter);
            });
        }
    });
}

function updateCharCount(textarea, counterElement) {
    const count = textarea.value.length;
    counterElement.textContent = count.toLocaleString();
    
    // Add visual feedback for character count
    if (count < 50) {
        counterElement.style.color = 'var(--error)';
    } else if (count < 100) {
        counterElement.style.color = 'var(--warning)';
    } else {
        counterElement.style.color = 'var(--text-tertiary)';
    }
}

// Form Validation

function initializeFormValidation() {
    const form = document.getElementById('predictionForm');
    if (!form) return;

    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        field.addEventListener('blur', validateField);
        field.addEventListener('input', clearFieldError);
    });
}

function validateField(event) {
    const field = event.target;
    const value = field.value.trim();
    
    // Remove existing error styling
    clearFieldError(event);
    
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, 'This field is required');
        return false;
    }
    
    // Additional validation for text fields
    if (field.type === 'textarea' && value.length < 30) {
        showFieldError(field, 'Please provide more detailed information (at least 30 characters)');
        return false;
    }
    
    return true;
}

function showFieldError(field, message) {
    field.style.borderColor = 'var(--error)';
    field.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
    
    // Remove existing error message
    const existingError = field.parentNode.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // Add error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.color = 'var(--error)';
    errorDiv.style.fontSize = 'var(--font-size-xs)';
    errorDiv.style.marginTop = 'var(--spacing-xs)';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(event) {
    const field = event.target;
    field.style.borderColor = '';
    field.style.boxShadow = '';
    
    const errorMessage = field.parentNode.querySelector('.error-message');
    if (errorMessage) {
        errorMessage.remove();
    }
}

// Form Submission Handler

function handleFormSubmit(event) {
    const form = event.target;
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    
    // Validate form
    if (!validateForm(form)) {
        event.preventDefault();
        return false;
    }
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-flex';
    form.classList.add('loading');
    
    // Ensure checkboxes have correct values before submission
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        // Remove any existing hidden inputs
        const existingHidden = form.querySelector(`input[type="hidden"][name="${checkbox.name}"]`);
        if (existingHidden) {
            existingHidden.remove();
        }
        
        // If unchecked, add hidden input with value 0
        if (!checkbox.checked) {
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = checkbox.name;
            hiddenInput.value = '0';
            form.appendChild(hiddenInput);
        }
    });
    
    // Handle dynamic fields (dropdown/text conversion)
    const dynamicWrappers = form.querySelectorAll('.dynamic-field-wrapper');
    dynamicWrappers.forEach(wrapper => {
        const select = wrapper.querySelector('.dynamic-select');
        const textInput = wrapper.querySelector('.dynamic-input');
        const fieldName = wrapper.getAttribute('data-field-name');
        
        // If text input is visible (Other was selected), use its value
        if (textInput.style.display !== 'none' && textInput.value.trim() !== '') {
            select.name = '';
            textInput.name = fieldName;
        } else {
            textInput.disabled = true;
            textInput.name = '';
            select.disabled = false;
            select.name = fieldName;
        }
    });
    
    return true;
}

function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        const value = field.value.trim();
        if (!value) {
            showFieldError(field, 'This field is required');
            isValid = false;
        }
    });
    
    // Validate minimum text length for description
    const description = form.querySelector('#description');
    if (description && description.value.trim().length < 30) {
        showFieldError(description, 'Description must be at least 30 characters long');
        isValid = false;
    }
    
    return isValid;
}

function resetSubmitButton(submitBtn, btnText, btnLoader) {
    submitBtn.disabled = false;
    btnText.style.display = 'inline';
    btnLoader.style.display = 'none';
    document.getElementById('predictionForm').classList.remove('loading');
}

function showError(message) {
    // Create error notification
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-notification';
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--error);
        color: white;
        padding: var(--spacing-md) var(--spacing-lg);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    `;
    errorDiv.textContent = message;
    
    document.body.appendChild(errorDiv);
    
    // Remove after 5 seconds
    setTimeout(() => {
        errorDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => errorDiv.remove(), 300);
    }, 5000);
}

// Dynamic Field Conversion (Dropdown to Text)

function initializeDynamicFields() {
    const dynamicSelects = document.querySelectorAll('.dynamic-select');
    
    dynamicSelects.forEach(select => {
        select.addEventListener('change', handleDynamicFieldChange);
        
        // Check if "Other" is already selected on page load
        if (select.value === '__OTHER__') {
            convertToTextInput(select);
        }
    });
}

function handleDynamicFieldChange(event) {
    const select = event.target;
    const value = select.value;
    
    if (value === '__OTHER__') {
        convertToTextInput(select);
    } else {
        convertToSelect(select);
    }
}

function convertToTextInput(select) {
    const wrapper = select.closest('.dynamic-field-wrapper');
    const textInput = wrapper.querySelector('.dynamic-input');
    const fieldName = wrapper.getAttribute('data-field-name');
    
    // Hide select, show text input
    select.style.display = 'none';
    select.disabled = true;
    
    // Show and focus text input
    textInput.style.display = 'block';
    textInput.disabled = false;
    textInput.required = select.required;
    
    // Add animation class
    textInput.classList.add('field-appear');
    
    // Focus the input after a short delay for smooth transition
    setTimeout(() => {
        textInput.focus();
    }, 100);
    
    // Clear any existing value in text input if switching from another option
    if (textInput.value === '') {
        textInput.placeholder = `Enter ${fieldName.replace('_', ' ')}`;
    }
}

function convertToSelect(select) {
    const wrapper = select.closest('.dynamic-field-wrapper');
    const textInput = wrapper.querySelector('.dynamic-input');
    
    // Hide text input, show select
    textInput.style.display = 'none';
    textInput.disabled = true;
    textInput.value = '';
    
    // Show select
    select.style.display = 'block';
    select.disabled = false;
    
    // Add animation class
    select.classList.add('field-appear');
}

// Utility Functions

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Score Progress Animation

function initializeScoreProgress() {
    const progressRings = document.querySelectorAll('.circular-progress');
    
    progressRings.forEach(ring => {
        const score = parseFloat(ring.getAttribute('data-score')) || 0;
        const progressCircle = ring.querySelector('.progress-ring-progress');
        
        if (!progressCircle) return;
        
        // Calculate circumference (2 * π * radius)
        const radius = 45;
        const circumference = 2 * Math.PI * radius;
        
        // Calculate stroke-dashoffset based on score (0-100)
        const offset = circumference - (score / 100) * circumference;
        
        // Set initial state
        progressCircle.style.strokeDasharray = circumference;
        progressCircle.style.strokeDashoffset = circumference;
        
        // Animate to target offset
        setTimeout(() => {
            progressCircle.style.strokeDashoffset = offset;
        }, 100);
    });
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

