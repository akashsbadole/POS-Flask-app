/**
 * Global Utility Functions for Restaurant POS Application
 * This file contains common utility functions used across the application
 */

// Make functions available globally
window.formatDateTime = formatDateTime;
window.formatTime = formatTime;
window.formatCurrency = formatCurrency;
window.formatNumber = formatNumber;
window.debounce = debounce;
window.generateOrderNumber = generateOrderNumber;
window.getStatusClass = getStatusClass;
window.showNotification = showNotification;

/**
 * Format a date string to a readable format
 * @param {string|Date} dateString - The date to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted date string
 */
function formatDateTime(dateString, options = {}) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            console.warn('Invalid date provided to formatDateTime:', dateString);
            return 'Invalid Date';
        }
        
        // Default formatting options for Indian locale
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        };
        
        // Merge with provided options
        const formatOptions = { ...defaultOptions, ...options };
        
        return date.toLocaleString('en-IN', formatOptions);
    } catch (error) {
        console.error('Error formatting date:', error);
        return 'Invalid Date';
    }
}

/**
 * Format time from a date string
 * @param {string|Date} dateString - The date to format
 * @param {Object} options - Formatting options
 * @returns {string} Formatted time string
 */
function formatTime(dateString, options = {}) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            console.warn('Invalid date provided to formatTime:', dateString);
            return 'Invalid Time';
        }
        
        // Default formatting options
        const defaultOptions = {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        };
        
        // Merge with provided options
        const formatOptions = { ...defaultOptions, ...options };
        
        return date.toLocaleTimeString('en-IN', formatOptions);
    } catch (error) {
        console.error('Error formatting time:', error);
        return 'Invalid Time';
    }
}

/**
 * Format currency amount with Indian Rupee symbol
 * @param {number} amount - The amount to format
 * @param {string} currency - Currency symbol (default: ₹)
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount, currency = '₹', decimals = 2) {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return `${currency}0.00`;
    }
    
    try {
        const formattedAmount = parseFloat(amount).toFixed(decimals);
        return `${currency}${formattedAmount}`;
    } catch (error) {
        console.error('Error formatting currency:', error);
        return `${currency}0.00`;
    }
}

/**
 * Format a number with specified decimal places
 * @param {number} number - The number to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted number string
 */
function formatNumber(number, decimals = 2) {
    if (number === null || number === undefined || isNaN(number)) {
        return '0';
    }
    
    try {
        return parseFloat(number).toFixed(decimals);
    } catch (error) {
        console.error('Error formatting number:', error);
        return '0';
    }
}

/**
 * Debounce function to limit function calls
 * @param {Function} func - The function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Generate a unique order number
 * @param {string} prefix - Order number prefix (default: ORD)
 * @returns {string} Generated order number
 */
function generateOrderNumber(prefix = 'ORD') {
    const now = new Date();
    const dateStr = 
        now.getFullYear() +
        String(now.getMonth() + 1).padStart(2, '0') +
        String(now.getDate()).padStart(2, '0');
    const timeStr = 
        String(now.getHours()).padStart(2, '0') +
        String(now.getMinutes()).padStart(2, '0') +
        String(now.getSeconds()).padStart(2, '0');
    const randomStr = Math.random().toString(36).substr(2, 4).toUpperCase();
    
    return `${prefix}${dateStr}${timeStr}${randomStr}`;
}

/**
 * Get Bootstrap badge class for order status
 * @param {string} status - Order status
 * @returns {string} Bootstrap badge class
 */
function getStatusClass(status) {
    const classes = {
        'New': 'bg-primary',
        'In Progress': 'bg-warning',
        'Ready': 'bg-info',
        'Completed': 'bg-success',
        'Cancelled': 'bg-danger',
        'Paid': 'bg-success',
        'Pending': 'bg-warning',
        'Refunded': 'bg-secondary'
    };
    
    return classes[status] || 'bg-secondary';
}

/**
 * Show a notification toast
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, error, warning, info)
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
function showNotification(message, type = 'info', duration = 3000) {
    try {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.style.minWidth = '250px';
        toast.setAttribute('role', 'alert');
        
        // Add icon based on type
        let icon = '';
        switch (type) {
            case 'success':
                icon = '<i class="bi bi-check-circle me-2"></i>';
                break;
            case 'error':
            case 'danger':
                icon = '<i class="bi bi-x-circle me-2"></i>';
                break;
            case 'warning':
                icon = '<i class="bi bi-exclamation-triangle me-2"></i>';
                break;
            default:
                icon = '<i class="bi bi-info-circle me-2"></i>';
        }
        
        toast.innerHTML = `${icon}${message}`;
        
        // Add close button
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        toast.appendChild(closeButton);
        
        // Add to document
        document.body.appendChild(toast);
        
        // Auto remove after duration
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, duration);
        
        // Handle manual close
        closeButton.addEventListener('click', () => {
            toast.remove();
        });
        
    } catch (error) {
        console.error('Error showing notification:', error);
        // Fallback to alert
        alert(message);
    }
}

/**
 * Calculate GST amounts
 * @param {number} amount - Base amount
 * @param {number} cgstRate - CGST rate percentage (default: 2.5)
 * @param {number} sgstRate - SGST rate percentage (default: 2.5)
 * @returns {Object} Object with CGST, SGST, and total amounts
 */
function calculateGST(amount, cgstRate = 2.5, sgstRate = 2.5) {
    if (!amount || isNaN(amount)) {
        return {
            subtotal: 0,
            cgstAmount: 0,
            sgstAmount: 0,
            totalTax: 0,
            total: 0
        };
    }
    
    const subtotal = parseFloat(amount);
    const cgstAmount = subtotal * (cgstRate / 100);
    const sgstAmount = subtotal * (sgstRate / 100);
    const totalTax = cgstAmount + sgstAmount;
    const total = subtotal + totalTax;
    
    return {
        subtotal,
        cgstAmount,
        sgstAmount,
        totalTax,
        total
    };
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid email
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Validate mobile number (Indian format)
 * @param {string|number} mobile - Mobile number to validate
 * @returns {boolean} True if valid mobile number
 */
function isValidMobile(mobile) {
    const mobileRegex = /^[6-9]\d{9}$/;
    return mobileRegex.test(mobile.toString());
}

/**
 * Parse and validate a date string
 * @param {string|Date} dateString - Date to parse
 * @returns {Date|null} Valid Date object or null
 */
function parseDate(dateString) {
    if (!dateString) return null;
    
    try {
        const date = new Date(dateString);
        return isNaN(date.getTime()) ? null : date;
    } catch (error) {
        console.error('Error parsing date:', error);
        return null;
    }
}

/**
 * Get relative time string (e.g., "2 hours ago")
 * @param {string|Date} dateString - Date to compare
 * @returns {string} Relative time string
 */
function getRelativeTime(dateString) {
    const date = parseDate(dateString);
    if (!date) return 'N/A';
    
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    // For older dates, return formatted date
    return formatDateTime(date, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatDateTime,
        formatTime,
        formatCurrency,
        formatNumber,
        debounce,
        generateOrderNumber,
        getStatusClass,
        showNotification,
        calculateGST,
        isValidEmail,
        isValidMobile,
        parseDate,
        getRelativeTime
    };
}