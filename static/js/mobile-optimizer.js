/**
 * Mobile Optimization JavaScript for Flask POS Application
 * Handles touch interactions, performance optimizations, and mobile-specific features
 */

class MobileOptimizer {
    constructor() {
        this.isMobile = this.detectMobile();
        this.isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        this.viewportWidth = window.innerWidth;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.isSwiping = false;
        
        this.init();
    }
    
    detectMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               window.innerWidth <= 768;
    }
    
    init() {
        if (this.isMobile || this.isTouch) {
            this.setupTouchOptimizations();
            this.setupPerformanceOptimizations();
            this.setupMobileNavigation();
            this.setupSwipeGestures();
            this.setupMobileSpecificFeatures();
            this.optimizeForms();
            this.setupResponsiveBehaviors();
        }
        
        // Setup resize handler
        window.addEventListener('resize', this.debounce(() => {
            this.handleResize();
        }, 250));
        
        // Setup orientation change handler
        window.addEventListener('orientationchange', this.debounce(() => {
            this.handleOrientationChange();
        }, 100));
    }
    
    setupTouchOptimizations() {
        // Prevent default touch behaviors on interactive elements
        document.addEventListener('touchstart', (e) => {
            if (e.target.closest('.touch-action')) {
                // Allow touch action on designated elements
                return;
            }
            
            // Prevent double-tap zoom on buttons
            if (e.target.closest('button, .btn, a')) {
                e.preventDefault();
            }
        }, { passive: false });
        
        // Handle touch end for buttons
        document.addEventListener('touchend', (e) => {
            const target = e.target.closest('button, .btn, a');
            if (target && !this.isSwiping) {
                e.preventDefault();
                target.click();
            }
        }, { passive: false });
        
        // Add active states for touch
        document.addEventListener('touchstart', (e) => {
            const target = e.target.closest('button, .btn, .menu-item-card, .table-card');
            if (target) {
                target.classList.add('touch-active');
            }
        });
        
        document.addEventListener('touchend', (e) => {
            const target = e.target.closest('button, .btn, .menu-item-card, .table-card');
            if (target) {
                setTimeout(() => {
                    target.classList.remove('touch-active');
                }, 150);
            }
        });
        
        // Prevent scrolling on modals
        document.addEventListener('touchmove', (e) => {
            if (e.target.closest('.modal')) {
                const modalBody = e.target.closest('.modal-body');
                if (modalBody) {
                    const { scrollTop, scrollHeight, clientHeight } = modalBody;
                    if (scrollTop === 0 && e.touches[0].clientY > e.touches[0].clientY) {
                        e.preventDefault();
                    }
                    if (scrollTop + clientHeight >= scrollHeight && e.touches[0].clientY < e.touches[0].clientY) {
                        e.preventDefault();
                    }
                } else {
                    e.preventDefault();
                }
            }
        }, { passive: false });
    }
    
    setupPerformanceOptimizations() {
        // Lazy load images
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.classList.remove('lazy');
                            imageObserver.unobserve(img);
                        }
                    }
                });
            });
            
            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
        
        // Debounce scroll events
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
            scrollTimeout = setTimeout(() => {
                this.handleScroll();
            }, 100);
        }, { passive: true });
        
        // Optimize animations
        this.reduceMotionForPerformance();
    }
    
    setupMobileNavigation() {
        // Mobile navigation toggle
        const navToggle = document.querySelector('.mobile-nav-toggle');
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (navToggle && sidebar) {
            navToggle.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
                this.updateNavIcon(navToggle, sidebar.classList.contains('collapsed'));
            });
            
            // Close sidebar when clicking outside
            document.addEventListener('click', (e) => {
                if (!sidebar.contains(e.target) && !navToggle.contains(e.target)) {
                    sidebar.classList.add('collapsed');
                    this.updateNavIcon(navToggle, true);
                }
            });
        }
        
        // Add swipe to close sidebar
        if (sidebar) {
            this.addSwipeGesture(sidebar, (direction) => {
                if (direction === 'left' && !sidebar.classList.contains('collapsed')) {
                    sidebar.classList.add('collapsed');
                }
                if (direction === 'right' && sidebar.classList.contains('collapsed')) {
                    sidebar.classList.remove('collapsed');
                }
            });
        }
    }
    
    setupSwipeGestures() {
        // Swipe gestures for order tabs
        const orderTabs = document.querySelector('.order-tabs');
        if (orderTabs) {
            this.addSwipeGesture(orderTabs, (direction) => {
                const activeTab = orderTabs.querySelector('.order-tab.active');
                if (!activeTab) return;
                
                if (direction === 'left') {
                    const nextTab = activeTab.nextElementSibling;
                    if (nextTab && nextTab.classList.contains('order-tab')) {
                        nextTab.click();
                    }
                } else if (direction === 'right') {
                    const prevTab = activeTab.previousElementSibling;
                    if (prevTab && prevTab.classList.contains('order-tab')) {
                        prevTab.click();
                    }
                }
            });
        }
        
        // Swipe for table cards
        document.querySelectorAll('.table-card').forEach(card => {
            this.addSwipeGesture(card, (direction) => {
                if (direction === 'left') {
                    this.showTableActions(card);
                }
            });
        });
    }
    
    setupMobileSpecificFeatures() {
        // Virtual keyboard handling
        this.handleVirtualKeyboard();
        
        // Pull-to-refresh
        this.setupPullToRefresh();
        
        // Haptic feedback
        this.setupHapticFeedback();
        
        // Orientation-specific optimizations
        this.applyOrientationOptimizations();
    }
    
    optimizeForms() {
        // Prevent zoom on input focus
        const inputs = document.querySelectorAll('input[type="text"], input[type="number"], textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                if (this.isMobile) {
                    document.querySelector('meta[name="viewport"]').setAttribute('content', 
                        'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0');
                }
            });
            
            input.addEventListener('blur', () => {
                document.querySelector('meta[name="viewport"]').setAttribute('content', 
                    'width=device-width, initial-scale=1.0');
            });
        });
        
        // Auto-advance fields
        this.setupFieldAutoAdvance();
        
        // Mobile-friendly date inputs
        this.optimizeDateInputs();
    }
    
    setupResponsiveBehaviors() {
        // Handle responsive tables
        document.querySelectorAll('.data-table').forEach(table => {
            this.makeTableResponsive(table);
        });
        
        // Optimize modals for mobile
        document.querySelectorAll('.modal').forEach(modal => {
            this.optimizeModalForMobile(modal);
        });
        
        // Setup mobile-specific shortcuts
        this.setupMobileShortcuts();
    }
    
    addSwipeGesture(element, callback) {
        let startX = 0;
        let startY = 0;
        let startTime = 0;
        
        element.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            startTime = Date.now();
            this.isSwiping = false;
        }, { passive: true });
        
        element.addEventListener('touchmove', (e) => {
            if (!startX || !startY) return;
            
            const currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            const diffX = startX - currentX;
            const diffY = startY - currentY;
            
            // Check if this is a horizontal swipe
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                this.isSwiping = true;
            }
        }, { passive: true });
        
        element.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const diffX = startX - endX;
            const diffY = startY - endY;
            const endTime = Date.now();
            
            // Reset values
            startX = 0;
            startY = 0;
            
            // Check if this was a valid swipe
            const timeDiff = endTime - startTime;
            const swipeDistance = Math.abs(diffX);
            
            if (timeDiff < 500 && swipeDistance > 50 && Math.abs(diffY) < 100) {
                const direction = diffX > 0 ? 'right' : 'left';
                callback(direction);
            }
            
            setTimeout(() => {
                this.isSwiping = false;
            }, 100);
        }, { passive: true });
    }
    
    handleVirtualKeyboard() {
        // Detect virtual keyboard appearance
        const initialViewportHeight = window.visualViewport?.height || window.innerHeight;
        
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', () => {
                const currentHeight = window.visualViewport.height;
                const heightDiff = initialViewportHeight - currentHeight;
                
                if (heightDiff > 150) {
                    // Keyboard is visible
                    document.body.classList.add('keyboard-visible');
                    this.adjustForKeyboard(true);
                } else {
                    // Keyboard is hidden
                    document.body.classList.remove('keyboard-visible');
                    this.adjustForKeyboard(false);
                }
            });
        }
    }
    
    adjustForKeyboard(isVisible) {
        const activeElement = document.activeElement;
        if (!activeElement) return;
        
        if (isVisible) {
            // Scroll active element into view
            setTimeout(() => {
                activeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
        }
    }
    
    setupPullToRefresh() {
        let startY = 0;
        let isPulling = false;
        
        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].clientY;
                isPulling = false;
            }
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            if (startY === 0) return;
            
            const currentY = e.touches[0].clientY;
            const pullDistance = currentY - startY;
            
            if (pullDistance > 0 && window.scrollY === 0) {
                isPulling = true;
                this.showPullIndicator(pullDistance);
                e.preventDefault();
            }
        }, { passive: false });
        
        document.addEventListener('touchend', () => {
            if (isPulling) {
                this.hidePullIndicator();
                startY = 0;
                isPulling = false;
            }
        }, { passive: true });
    }
    
    showPullIndicator(distance) {
        let indicator = document.getElementById('pull-to-refresh');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'pull-to-refresh';
            indicator.innerHTML = '<div class="spinner"></div><span>Pull to refresh...</span>';
            indicator.style.cssText = `
                position: fixed;
                top: -60px;
                left: 50%;
                transform: translateX(-50%);
                background: white;
                padding: 10px 20px;
                border-radius: 0 0 20px 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 1000;
                transition: top 0.3s ease;
            `;
            document.body.appendChild(indicator);
        }
        
        if (distance > 100) {
            indicator.style.top = '0px';
        }
    }
    
    hidePullIndicator() {
        const indicator = document.getElementById('pull-to-refresh');
        if (indicator) {
            indicator.style.top = '-60px';
        }
    }
    
    setupHapticFeedback() {
        // Add haptic feedback to buttons
        document.querySelectorAll('button, .btn').forEach(button => {
            button.addEventListener('touchstart', () => {
                if ('vibrate' in navigator) {
                    navigator.vibrate(10);
                }
            }, { passive: true });
        });
    }
    
    makeTableResponsive(table) {
        if (!this.isMobile) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
        
        // Add horizontal scroll indicators
        this.addScrollIndicators(wrapper);
    }
    
    optimizeModalForMobile(modal) {
        if (!this.isMobile) return;
        
        const modalDialog = modal.querySelector('.modal-dialog');
        const modalBody = modal.querySelector('.modal-body');
        
        // Make modal full-screen on mobile
        if (window.innerWidth <= 768) {
            modalDialog.style.maxWidth = '100%';
            modalDialog.style.margin = '0';
            modalDialog.style.height = '100vh';
            
            modalBody.style.maxHeight = 'calc(100vh - 140px)';
        }
        
        // Add swipe to close
        this.addSwipeGesture(modal, (direction) => {
            if (direction === 'down') {
                // Close modal on swipe down
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }
        });
    }
    
    setupMobileShortcuts() {
        // Add long press for additional actions
        document.querySelectorAll('.menu-item-card, .table-card').forEach(card => {
            let pressTimer;
            
            card.addEventListener('touchstart', () => {
                pressTimer = setTimeout(() => {
                    this.showContextMenu(card);
                }, 500);
            }, { passive: true });
            
            card.addEventListener('touchend', () => {
                clearTimeout(pressTimer);
            }, { passive: true });
        });
    }
    
    showContextMenu(element) {
        // Implement context menu for long press
        console.log('Long press detected on:', element);
        // This could show a modal with additional options
    }
    
    updateNavIcon(toggle, isCollapsed) {
        const icon = toggle.querySelector('i') || toggle;
        if (isCollapsed) {
            icon.innerHTML = '☰'; // Hamburger menu
        } else {
            icon.innerHTML = '✕'; // Close icon
        }
    }
    
    handleResize() {
        const newViewportWidth = window.innerWidth;
        const widthChanged = Math.abs(newViewportWidth - this.viewportWidth) > 50;
        
        if (widthChanged) {
            this.viewportWidth = newViewportWidth;
            this.applyOrientationOptimizations();
        }
    }
    
    handleOrientationChange() {
        setTimeout(() => {
            this.applyOrientationOptimizations();
            
            // Adjust scroll position
            if (document.activeElement) {
                document.activeElement.scrollIntoView({ behavior: 'smooth' });
            }
        }, 100);
    }
    
    applyOrientationOptimizations() {
        const isLandscape = window.innerWidth > window.innerHeight;
        const isTablet = window.innerWidth >= 768 && window.innerWidth <= 1024;
        
        document.body.classList.toggle('landscape', isLandscape);
        document.body.classList.toggle('portrait', !isLandscape);
        document.body.classList.toggle('tablet', isTablet);
        
        // Adjust layouts based on orientation
        if (isLandscape && this.isMobile) {
            this.optimizeForLandscape();
        } else {
            this.optimizeForPortrait();
        }
    }
    
    optimizeForLandscape() {
        // Show side-by-side layouts in landscape
        document.querySelectorAll('.kot-container').forEach(container => {
            container.style.display = 'grid';
            container.style.gridTemplateColumns = 'repeat(2, 1fr)';
        });
    }
    
    optimizeForPortrait() {
        // Show stacked layouts in portrait
        document.querySelectorAll('.kot-container').forEach(container => {
            container.style.display = 'block';
            container.style.gridTemplateColumns = 'none';
        });
    }
    
    handleScroll() {
        // Add scroll-based optimizations
        const scrollTop = window.pageYOffset;
        
        // Hide/show navigation based on scroll direction
        const nav = document.querySelector('.navbar');
        if (nav) {
            if (scrollTop > 100) {
                nav.classList.add('navbar-hidden');
            } else {
                nav.classList.remove('navbar-hidden');
            }
        }
    }
    
    reduceMotionForPerformance() {
        // Reduce animations on low-end devices
        const isLowEnd = this.detectLowEndDevice();
        
        if (isLowEnd) {
            document.body.classList.add('reduced-motion');
            
            // Disable complex animations
            const style = document.createElement('style');
            style.textContent = `
                * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
                .modal.fade { transition: none !important; }
                .carousel-item { transition: none !important; }
            `;
            document.head.appendChild(style);
        }
    }
    
    detectLowEndDevice() {
        // Simple heuristic to detect low-end devices
        const memory = navigator.deviceMemory || 4;
        const cores = navigator.hardwareConcurrency || 4;
        
        return memory < 2 || cores < 4;
    }
    
    setupFieldAutoAdvance() {
        document.querySelectorAll('input[maxlength]').forEach(input => {
            input.addEventListener('input', () => {
                if (input.value.length >= input.maxLength) {
                    const nextInput = this.findNextInput(input);
                    if (nextInput) {
                        nextInput.focus();
                    }
                }
            });
        });
    }
    
    findNextInput(currentInput) {
        const inputs = Array.from(document.querySelectorAll('input:not([disabled])'));
        const currentIndex = inputs.indexOf(currentInput);
        return inputs[currentIndex + 1];
    }
    
    optimizeDateInputs() {
        document.querySelectorAll('input[type="date"]').forEach(input => {
            input.setAttribute('inputmode', 'none');
            input.setAttribute('readonly', 'readonly');
            
            input.addEventListener('click', () => {
                // Use mobile-friendly date picker
                if ('showPicker' in input) {
                    input.showPicker();
                }
            });
        });
    }
    
    addScrollIndicators(container) {
        const leftIndicator = document.createElement('div');
        const rightIndicator = document.createElement('div');
        
        leftIndicator.className = 'scroll-indicator scroll-left';
        rightIndicator.className = 'scroll-indicator scroll-right';
        
        leftIndicator.innerHTML = '◀';
        rightIndicator.innerHTML = '▶';
        
        Object.assign(leftIndicator.style, {
            position: 'absolute',
            left: '5px',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'rgba(0,0,0,0.7)',
            color: 'white',
            padding: '5px',
            borderRadius: '50%',
            cursor: 'pointer',
            display: 'none'
        });
        
        Object.assign(rightIndicator.style, {
            position: 'absolute',
            right: '5px',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'rgba(0,0,0,0.7)',
            color: 'white',
            padding: '5px',
            borderRadius: '50%',
            cursor: 'pointer',
            display: 'none'
        });
        
        container.style.position = 'relative';
        container.appendChild(leftIndicator);
        container.appendChild(rightIndicator);
        
        // Show/hide indicators based on scroll position
        container.addEventListener('scroll', () => {
            leftIndicator.style.display = container.scrollLeft > 0 ? 'block' : 'none';
            rightIndicator.style.display = 
                container.scrollLeft < container.scrollWidth - container.clientWidth ? 'block' : 'none';
        });
        
        // Scroll on click
        leftIndicator.addEventListener('click', () => {
            container.scrollBy({ left: -200, behavior: 'smooth' });
        });
        
        rightIndicator.addEventListener('click', () => {
            container.scrollBy({ left: 200, behavior: 'smooth' });
        });
    }
    
    showTableActions(tableCard) {
        // Show swipe actions for table
        console.log('Show actions for table:', tableCard);
        // This could show a modal with table actions
    }
    
    debounce(func, wait) {
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
}

// Add CSS for mobile optimizations
const mobileCSS = `
    .touch-active {
        opacity: 0.7;
        transform: scale(0.95);
    }
    
    .navbar-hidden {
        transform: translateY(-100%);
        transition: transform 0.3s ease;
    }
    
    .keyboard-visible {
        padding-bottom: 200px;
    }
    
    .scroll-indicator {
        z-index: 10;
        font-size: 12px;
        user-select: none;
    }
    
    .reduced-motion * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
    
    .landscape .modal-dialog {
        max-width: 90%;
        margin: 1rem auto;
    }
    
    .tablet .sidebar {
        width: 200px;
    }
    
    .mobile-only {
        display: none;
    }
    
    @media (max-width: 768px) {
        .mobile-only {
            display: block;
        }
        
        .desktop-only {
            display: none;
        }
    }
`;

// Initialize mobile optimizer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Inject mobile CSS
    const style = document.createElement('style');
    style.textContent = mobileCSS;
    document.head.appendChild(style);
    
    // Initialize mobile optimizer
    window.mobileOptimizer = new MobileOptimizer();
    
    // Add global mobile utilities
    window.showMobileNotification = (message, type = 'info') => {
        const notification = document.createElement('div');
        notification.className = `mobile-notification mobile-notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 9999;
            animation: slideDown 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideUp 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    };
    
    // Add animation keyframes
    const animationCSS = document.createElement('style');
    animationCSS.textContent = `
        @keyframes slideDown {
            from { transform: translate(-50%, -100%); opacity: 0; }
            to { transform: translate(-50%, 0); opacity: 1; }
        }
        
        @keyframes slideUp {
            from { transform: translate(-50%, 0); opacity: 1; }
            to { transform: translate(-50%, -100%); opacity: 0; }
        }
    `;
    document.head.appendChild(animationCSS);
});

// Export for global use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileOptimizer;
}
