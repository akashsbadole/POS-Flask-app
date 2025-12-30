/**
 * Restaurant POS Mobile Optimizer
 * Provides PWA features, touch optimizations, and mobile-first functionality
 */

(function() {
    'use strict';

    // Mobile Optimizer Object
    const MobileOptimizer = {
        // Configuration
        config: {
            touchThreshold: 22, // Minimum touch target size (WCAG 2.1)
            swipeThreshold: 50, // Minimum swipe distance
            tapDelay: 300, // Delay to distinguish tap from double-tap
            animationDuration: 300,
            pwaInstallDelay: 30000, // Show PWA install prompt after 30 seconds
        },

        // State
        state: {
            isMobile: false,
            isTablet: false,
            isDesktop: false,
            isLandscape: false,
            touchStartX: 0,
            touchStartY: 0,
            touchStartTime: 0,
            swipeDirection: null,
            lastTap: 0,
            pwaInstallEvent: null,
            deferredPrompt: null,
            isInstalled: false,
            isOnline: navigator.onLine,
            installPromptShown: false,
        },

        // Initialize mobile optimizer
        init() {
            this.detectDevice();
            this.setupEventListeners();
            this.initializePWA();
            this.optimizeTouchTargets();
            this.setupGestureSupport();
            this.initializeOfflineSupport();
            this.setupPerformanceOptimizations();
            this.setupAccessibilityEnhancements();
            
            console.log('Mobile Optimizer initialized');
        },

        // Device detection
        detectDevice() {
            const userAgent = navigator.userAgent.toLowerCase();
            const width = window.innerWidth;
            const height = window.innerHeight;

            // Detect mobile device
            this.state.isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent) ||
                                 width <= 768;

            // Detect tablet
            this.state.isTablet = /ipad|android(?!.*mobile)/i.test(userAgent) ||
                                 (width > 768 && width <= 1024);

            // Detect desktop
            this.state.isDesktop = !this.state.isMobile && !this.state.isTablet;

            // Detect orientation
            this.state.isLandscape = width > height;

            // Add device classes to body
            document.body.classList.toggle('mobile-device', this.state.isMobile);
            document.body.classList.toggle('tablet-device', this.state.isTablet);
            document.body.classList.toggle('desktop-device', this.state.isDesktop);
            document.body.classList.toggle('landscape-mode', this.state.isLandscape);

            // Set viewport meta tag for iOS zoom prevention
            if (this.state.isMobile) {
                this.preventiOSZoom();
            }
        },

        // Prevent iOS zoom on input focus
        preventiOSZoom() {
            const inputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], textarea, select');
            
            inputs.forEach(input => {
                input.addEventListener('focus', function() {
                    if (window.innerWidth < 768) {
                        this.style.fontSize = '16px';
                    }
                });

                input.addEventListener('blur', function() {
                    this.style.fontSize = '';
                });
            });
        },

        // Setup event listeners
        setupEventListeners() {
            // Window resize event
            window.addEventListener('resize', this.throttle(() => {
                this.detectDevice();
                this.adjustLayoutForDevice();
            }, 250));

            // Orientation change event
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    this.detectDevice();
                    this.adjustLayoutForDevice();
                }, 100);
            });

            // Online/Offline events
            window.addEventListener('online', () => {
                this.state.isOnline = true;
                this.showOnlineNotification();
                this.syncOfflineData();
            });

            window.addEventListener('offline', () => {
                this.state.isOnline = false;
                this.showOfflineNotification();
            });

            // Touch events for gesture support
            document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
            document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
            document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });

            // Click event optimization
            document.addEventListener('click', this.handleClick.bind(this));

            // PWA install event
            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                this.state.deferredPrompt = e;
                this.showPWAInstallPrompt();
            });

            // App installed event
            window.addEventListener('appinstalled', () => {
                this.state.isInstalled = true;
                this.hidePWAInstallPrompt();
                this.showInstallSuccess();
            });

            // Keyboard events for mobile
            document.addEventListener('keydown', this.handleKeyboard.bind(this));
        },

        // PWA initialization
        initializePWA() {
            // Check if app is already installed
            this.state.isInstalled = window.matchMedia('(display-mode: standalone)').matches ||
                                   window.navigator.standalone ||
                                   document.referrer.includes('android-app://');

            if (this.state.isInstalled) {
                document.body.classList.add('pwa-installed');
            }

            // Show install prompt after delay
            if (!this.state.isInstalled && this.state.deferredPrompt) {
                setTimeout(() => {
                    if (!this.state.installPromptShown) {
                        this.showPWAInstallPrompt();
                    }
                }, this.config.pwaInstallDelay);
            }
        },

        // Show PWA install prompt
        showPWAInstallPrompt() {
            const prompt = document.getElementById('pwa-install-prompt');
            if (prompt) {
                prompt.style.display = 'block';
                this.state.installPromptShown = true;

                // Add install button event listener
                const installBtn = document.getElementById('pwa-install-btn');
                if (installBtn) {
                    installBtn.addEventListener('click', this.installPWA.bind(this));
                }

                // Add dismiss button event listener
                const dismissBtn = document.getElementById('pwa-dismiss-btn');
                if (dismissBtn) {
                    dismissBtn.addEventListener('click', this.hidePWAInstallPrompt.bind(this));
                }
            }
        },

        // Hide PWA install prompt
        hidePWAInstallPrompt() {
            const prompt = document.getElementById('pwa-install-prompt');
            if (prompt) {
                prompt.style.display = 'none';
            }
        },

        // Install PWA
        installPWA() {
            if (this.state.deferredPrompt) {
                this.state.deferredPrompt.prompt();
                
                this.state.deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('User accepted PWA install');
                    } else {
                        console.log('User dismissed PWA install');
                    }
                    this.state.deferredPrompt = null;
                    this.hidePWAInstallPrompt();
                });
            }
        },

        // Show install success notification
        showInstallSuccess() {
            this.showToast('App installed successfully!', 'success');
        },

        // Optimize touch targets
        optimizeTouchTargets() {
            const interactiveElements = document.querySelectorAll(
                'button, a, input[type="button"], input[type="submit"], input[type="reset"], [role="button"], [tabindex]:not([tabindex="-1"])'
            );

            interactiveElements.forEach(element => {
                // Ensure minimum touch target size
                const rect = element.getBoundingClientRect();
                if (rect.width < this.config.touchThreshold || rect.height < this.config.touchThreshold) {
                    element.style.minWidth = this.config.touchThreshold + 'px';
                    element.style.minHeight = this.config.touchThreshold + 'px';
                    element.classList.add('touch-optimized');
                }

                // Add touch feedback
                element.addEventListener('touchstart', (e) => {
                    this.addTouchRipple(e.target, e);
                }, { passive: true });

                // Prevent double-tap zoom
                element.addEventListener('touchend', this.preventDoubleTapZoom.bind(this));
            });
        },

        // Add touch ripple effect
        addTouchRipple(element, event) {
            const ripple = document.createElement('span');
            const rect = element.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = event.touches[0].clientX - rect.left - size / 2;
            const y = event.touches[0].clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.6);
                transform: scale(0);
                animation: ripple 600ms linear;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                pointer-events: none;
            `;

            element.style.position = 'relative';
            element.style.overflow = 'hidden';
            element.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        },

        // Prevent double-tap zoom
        preventDoubleTapZoom(event) {
            const now = Date.now();
            if (now - this.state.lastTap <= this.config.tapDelay) {
                event.preventDefault();
            }
            this.state.lastTap = now;
        },

        // Setup gesture support
        setupGestureSupport() {
            // Swipe gestures for navigation
            const swipeableElements = document.querySelectorAll('.swipeable');
            swipeableElements.forEach(element => {
                this.addSwipeGestures(element);
            });

            // Pull to refresh
            const refreshableElements = document.querySelectorAll('.pull-to-refresh');
            refreshableElements.forEach(element => {
                this.addPullToRefresh(element);
            });

            // Pinch to zoom for images
            const zoomableImages = document.querySelectorAll('.zoomable');
            zoomableImages.forEach(image => {
                this.addPinchToZoom(image);
            });
        },

        // Add swipe gestures
        addSwipeGestures(element) {
            let startX, startY, startTime;

            element.addEventListener('touchstart', (e) => {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
                startTime = Date.now();
            }, { passive: true });

            element.addEventListener('touchend', (e) => {
                const endX = e.changedTouches[0].clientX;
                const endY = e.changedTouches[0].clientY;
                const endTime = Date.now();

                const deltaX = endX - startX;
                const deltaY = endY - startY;
                const deltaTime = endTime - startTime;

                // Check if it's a valid swipe
                if (Math.abs(deltaX) > this.config.swipeThreshold && 
                    Math.abs(deltaY) < 100 && 
                    deltaTime < 500) {
                    
                    const direction = deltaX > 0 ? 'right' : 'left';
                    this.handleSwipe(element, direction);
                }
            }, { passive: true });
        },

        // Handle swipe gesture
        handleSwipe(element, direction) {
            const swipeEvent = new CustomEvent('swipe', {
                detail: { direction, element }
            });
            element.dispatchEvent(swipeEvent);
        },

        // Add pull to refresh
        addPullToRefresh(element) {
            let startY, currentY, startTime;
            const threshold = 80;

            element.addEventListener('touchstart', (e) => {
                if (element.scrollTop === 0) {
                    startY = e.touches[0].clientY;
                    startTime = Date.now();
                }
            }, { passive: true });

            element.addEventListener('touchmove', (e) => {
                if (startY !== undefined && element.scrollTop === 0) {
                    currentY = e.touches[0].clientY;
                    const deltaY = currentY - startY;

                    if (deltaY > 0) {
                        e.preventDefault();
                        element.style.transform = `translateY(${Math.min(deltaY, threshold)}px)`;
                        element.classList.toggle('pulling', deltaY > 20);
                    }
                }
            }, { passive: false });

            element.addEventListener('touchend', () => {
                if (startY !== undefined) {
                    const deltaY = currentY - startY;
                    
                    if (deltaY > threshold) {
                        this.handlePullToRefresh(element);
                    }
                    
                    element.style.transform = '';
                    element.classList.remove('pulling');
                    startY = undefined;
                }
            }, { passive: true });
        },

        // Handle pull to refresh
        handlePullToRefresh(element) {
            const refreshEvent = new CustomEvent('pullrefresh', {
                detail: { element }
            });
            element.dispatchEvent(refreshEvent);

            // Show loading indicator
            element.classList.add('refreshing');
            
            // Simulate refresh (replace with actual refresh logic)
            setTimeout(() => {
                element.classList.remove('refreshing');
                const refreshCompleteEvent = new CustomEvent('refreshcomplete');
                element.dispatchEvent(refreshCompleteEvent);
            }, 2000);
        },

        // Add pinch to zoom
        addPinchToZoom(image) {
            let initialDistance = 0;
            let currentScale = 1;

            image.addEventListener('touchstart', (e) => {
                if (e.touches.length === 2) {
                    initialDistance = this.getTouchDistance(e.touches);
                    e.preventDefault();
                }
            }, { passive: false });

            image.addEventListener('touchmove', (e) => {
                if (e.touches.length === 2) {
                    e.preventDefault();
                    const currentDistance = this.getTouchDistance(e.touches);
                    const scale = currentDistance / initialDistance;
                    
                    currentScale = Math.max(0.5, Math.min(3, currentScale * scale));
                    image.style.transform = `scale(${currentScale})`;
                }
            }, { passive: false });

            image.addEventListener('touchend', () => {
                if (currentScale === 1) {
                    image.style.transform = '';
                }
            });
        },

        // Get distance between two touch points
        getTouchDistance(touches) {
            const dx = touches[0].clientX - touches[1].clientX;
            const dy = touches[0].clientY - touches[1].clientY;
            return Math.sqrt(dx * dx + dy * dy);
        },

        // Touch event handlers
        handleTouchStart(event) {
            this.state.touchStartX = event.touches[0].clientX;
            this.state.touchStartY = event.touches[0].clientY;
            this.state.touchStartTime = Date.now();
        },

        handleTouchMove(event) {
            // Prevent default for scrollable containers
            if (event.target.closest('.scrollable')) {
                event.preventDefault();
            }
        },

        handleTouchEnd(event) {
            const touchEndX = event.changedTouches[0].clientX;
            const touchEndY = event.changedTouches[0].clientY;
            const touchEndTime = Date.now();

            const deltaX = touchEndX - this.state.touchStartX;
            const deltaY = touchEndY - this.state.touchStartY;
            const deltaTime = touchEndTime - this.state.touchStartTime;

            // Detect swipe gestures
            if (Math.abs(deltaX) > this.config.swipeThreshold && 
                Math.abs(deltaY) < 100 && 
                deltaTime < 500) {
                
                this.state.swipeDirection = deltaX > 0 ? 'right' : 'left';
                this.handleGlobalSwipe(this.state.swipeDirection);
            }
        },

        // Handle global swipe gestures
        handleGlobalSwipe(direction) {
            // Handle sidebar toggle on mobile
            if (this.state.isMobile) {
                const sidebar = document.querySelector('.mobile-sidebar');
                if (sidebar) {
                    if (direction === 'right' && !sidebar.classList.contains('open')) {
                        sidebar.classList.add('open');
                    } else if (direction === 'left' && sidebar.classList.contains('open')) {
                        sidebar.classList.remove('open');
                    }
                }
            }
        },

        // Click event handler
        handleClick(event) {
            // Add haptic feedback for important actions
            if (event.target.matches('.btn-primary, .btn-success, .btn-danger')) {
                this.addHapticFeedback();
            }

            // Close mobile menu when clicking outside
            if (this.state.isMobile) {
                const sidebar = document.querySelector('.mobile-sidebar');
                const menuToggle = document.querySelector('.mobile-menu-toggle');
                
                if (sidebar && sidebar.classList.contains('open') && 
                    !sidebar.contains(event.target) && 
                    !menuToggle.contains(event.target)) {
                    sidebar.classList.remove('open');
                }
            }
        },

        // Keyboard event handler
        handleKeyboard(event) {
            // Handle escape key to close modals and menus
            if (event.key === 'Escape') {
                this.closeAllOverlays();
            }

            // Handle Enter key on mobile
            if (event.key === 'Enter' && this.state.isMobile) {
                const activeElement = document.activeElement;
                if (activeElement && activeElement.type !== 'submit') {
                    event.preventDefault();
                    activeElement.blur();
                }
            }
        },

        // Close all overlays
        closeAllOverlays() {
            const overlays = document.querySelectorAll('.mobile-sidebar, .modal.show, .dropdown-menu.show');
            overlays.forEach(overlay => {
                overlay.classList.remove('show', 'open');
            });
        },

        // Add haptic feedback
        addHapticFeedback() {
            if ('vibrate' in navigator) {
                navigator.vibrate(50); // 50ms vibration
            }
        },

        // Offline support
        initializeOfflineSupport() {
            // Store data in IndexedDB for offline access
            this.setupIndexedDB();
            
            // Sync data when back online
            this.setupDataSync();
        },

        // Setup IndexedDB for offline storage
        setupIndexedDB() {
            const request = indexedDB.open('RestaurantPOS', 1);

            request.onerror = () => {
                console.error('IndexedDB error:', request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Create object stores
                if (!db.objectStoreNames.contains('orders')) {
                    const orderStore = db.createObjectStore('orders', { keyPath: 'id' });
                    orderStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                if (!db.objectStoreNames.contains('offlineActions')) {
                    const actionStore = db.createObjectStore('offlineActions', { keyPath: 'id', autoIncrement: true });
                    actionStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                if (!db.objectStoreNames.contains('cachedData')) {
                    const cacheStore = db.createObjectStore('cachedData', { keyPath: 'key' });
                    cacheStore.createIndex('expiry', 'expiry', { unique: false });
                }
            };
        },

        // Store data offline
        storeOfflineData(storeName, data) {
            if (!this.db) return Promise.resolve();

            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([storeName], 'readwrite');
                const store = transaction.objectStore(storeName);
                
                data.timestamp = Date.now();
                const request = store.put(data);
                
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        },

        // Get offline data
        getOfflineData(storeName, key) {
            if (!this.db) return Promise.resolve(null);

            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                const request = key ? store.get(key) : store.getAll();
                
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        },

        // Setup data synchronization
        setupDataSync() {
            if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
                navigator.serviceWorker.ready.then(registration => {
                    return registration.sync.register('background-sync');
                });
            }
        },

        // Sync offline data
        async syncOfflineData() {
            if (!this.state.isOnline) return;

            try {
                const offlineActions = await this.getOfflineData('offlineActions');
                if (offlineActions) {
                    // Process offline actions
                    for (const action of offlineActions) {
                        await this.processOfflineAction(action);
                    }
                }
            } catch (error) {
                console.error('Data sync failed:', error);
            }
        },

        // Process offline action
        async processOfflineAction(action) {
            try {
                const response = await fetch(action.url, {
                    method: action.method,
                    headers: action.headers,
                    body: action.data
                });

                if (response.ok) {
                    // Remove from offline storage
                    await this.removeOfflineAction(action.id);
                }
            } catch (error) {
                console.error('Failed to process offline action:', error);
            }
        },

        // Remove offline action
        removeOfflineAction(actionId) {
            if (!this.db) return Promise.resolve();

            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction(['offlineActions'], 'readwrite');
                const store = transaction.objectStore('offlineActions');
                const request = store.delete(actionId);
                
                request.onsuccess = () => resolve();
                request.onerror = () => reject(request.error);
            });
        },

        // Show online notification
        showOnlineNotification() {
            this.showToast('Connection restored', 'success');
        },

        // Show offline notification
        showOfflineNotification() {
            this.showToast('Working offline', 'warning');
        },

        // Performance optimizations
        setupPerformanceOptimizations() {
            // Lazy load images
            this.setupLazyLoading();
            
            // Optimize animations
            this.optimizeAnimations();
            
            // Preload critical resources
            this.preloadResources();
        },

        // Setup lazy loading
        setupLazyLoading() {
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.classList.remove('lazy-load');
                            observer.unobserve(img);
                        }
                    });
                });

                document.querySelectorAll('img[data-src]').forEach(img => {
                    imageObserver.observe(img);
                });
            }
        },

        // Optimize animations
        optimizeAnimations() {
            // Use CSS transforms instead of changing layout properties
            const animatedElements = document.querySelectorAll('.animate');
            animatedElements.forEach(element => {
                element.style.willChange = 'transform, opacity';
            });

            // Pause animations when not visible
            if ('IntersectionObserver' in window) {
                const animationObserver = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            entry.target.style.animationPlayState = 'running';
                        } else {
                            entry.target.style.animationPlayState = 'paused';
                        }
                    });
                });

                animatedElements.forEach(element => {
                    animationObserver.observe(element);
                });
            }
        },

        // Preload critical resources
        preloadResources() {
            const criticalResources = [
                '/static/css/mobile-responsive.css',
                '/static/js/mobile-optimizer.js',
                '/static/js/pos.js'
            ];

            criticalResources.forEach(resource => {
                const link = document.createElement('link');
                link.rel = 'preload';
                link.href = resource;
                link.as = resource.endsWith('.css') ? 'style' : 'script';
                document.head.appendChild(link);
            });
        },

        // Accessibility enhancements
        setupAccessibilityEnhancements() {
            // Add ARIA labels to interactive elements
            this.addAriaLabels();
            
            // Setup focus management
            this.setupFocusManagement();
            
            // Add keyboard navigation
            this.setupKeyboardNavigation();
        },

        // Add ARIA labels
        addAriaLabels() {
            const interactiveElements = document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])');
            interactiveElements.forEach(element => {
                const text = element.textContent.trim() || element.title;
                if (text) {
                    element.setAttribute('aria-label', text);
                }
            });
        },

        // Setup focus management
        setupFocusManagement() {
            // Trap focus in modals
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    const modal = document.querySelector('.modal.show');
                    if (modal) {
                        this.trapFocus(e, modal);
                    }
                }
            });
        },

        // Trap focus in element
        trapFocus(event, element) {
            const focusableElements = element.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            if (event.shiftKey) {
                if (document.activeElement === firstElement) {
                    event.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    event.preventDefault();
                    firstElement.focus();
                }
            }
        },

        // Setup keyboard navigation
        setupKeyboardNavigation() {
            // Add skip links
            this.addSkipLinks();
            
            // Setup roving tabindex
            this.setupRovingTabindex();
        },

        // Add skip links
        addSkipLinks() {
            const skipLink = document.querySelector('.skip-link');
            if (skipLink) {
                skipLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    const target = document.querySelector(skipLink.getAttribute('href'));
                    if (target) {
                        target.focus();
                        target.scrollIntoView();
                    }
                });
            }
        },

        // Setup roving tabindex
        setupRovingTabindex() {
            const rovingGroups = document.querySelectorAll('[role="tablist"]');
            rovingGroups.forEach(group => {
                const tabs = group.querySelectorAll('[role="tab"]');
                tabs.forEach((tab, index) => {
                    tab.setAttribute('tabindex', index === 0 ? '0' : '-1');
                    
                    tab.addEventListener('keydown', (e) => {
                        let newIndex = index;
                        
                        switch (e.key) {
                            case 'ArrowRight':
                            case 'ArrowDown':
                                newIndex = (index + 1) % tabs.length;
                                break;
                            case 'ArrowLeft':
                            case 'ArrowUp':
                                newIndex = (index - 1 + tabs.length) % tabs.length;
                                break;
                            case 'Home':
                                newIndex = 0;
                                break;
                            case 'End':
                                newIndex = tabs.length - 1;
                                break;
                        }
                        
                        if (newIndex !== index) {
                            e.preventDefault();
                            tabs.forEach(t => t.setAttribute('tabindex', '-1'));
                            tabs[newIndex].setAttribute('tabindex', '0');
                            tabs[newIndex].focus();
                        }
                    });
                });
            });
        },

        // Adjust layout for device
        adjustLayoutForDevice() {
            // Adjust sidebar behavior
            const sidebar = document.querySelector('.mobile-sidebar');
            if (sidebar) {
                if (this.state.isDesktop) {
                    sidebar.classList.remove('open');
                }
            }

            // Adjust bottom navigation
            const bottomNav = document.querySelector('.mobile-bottom-nav');
            if (bottomNav) {
                bottomNav.style.display = this.state.isMobile ? 'flex' : 'none';
            }

            // Adjust modal layout
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                if (modal.classList.contains('show')) {
                    this.adjustModalForDevice(modal);
                }
            });
        },

        // Adjust modal for device
        adjustModalForDevice(modal) {
            if (this.state.isMobile) {
                modal.classList.add('mobile-modal');
            } else {
                modal.classList.remove('mobile-modal');
            }
        },

        // Utility functions
        throttle(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },

        debounce(func, delay) {
            let timeoutId;
            return function() {
                const args = arguments;
                const context = this;
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => func.apply(context, args), delay);
            };
        },

        // Show toast notification
        showToast(message, type = 'info', duration = 3000) {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `
                <div class="toast-content">
                    <i class="bi bi-${this.getToastIcon(type)}"></i>
                    <span>${message}</span>
                </div>
            `;

            document.body.appendChild(toast);
            
            setTimeout(() => toast.classList.add('show'), 100);
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        },

        // Get toast icon
        getToastIcon(type) {
            const icons = {
                success: 'check-circle',
                warning: 'exclamation-triangle',
                error: 'x-circle',
                info: 'info-circle'
            };
            return icons[type] || 'info-circle';
        },

        // Public API
        api: {
            // Show PWA install prompt
            showInstallPrompt() {
                MobileOptimizer.showPWAInstallPrompt();
            },

            // Hide PWA install prompt
            hideInstallPrompt() {
                MobileOptimizer.hidePWAInstallPrompt();
            },

            // Store data offline
            storeOffline(storeName, data) {
                return MobileOptimizer.storeOfflineData(storeName, data);
            },

            // Get offline data
            getOffline(storeName, key) {
                return MobileOptimizer.getOfflineData(storeName, key);
            },

            // Sync data
            sync() {
                return MobileOptimizer.syncOfflineData();
            },

            // Show toast
            toast(message, type, duration) {
                MobileOptimizer.showToast(message, type, duration);
            },

            // Get device info
            getDeviceInfo() {
                return {
                    isMobile: MobileOptimizer.state.isMobile,
                    isTablet: MobileOptimizer.state.isTablet,
                    isDesktop: MobileOptimizer.state.isDesktop,
                    isLandscape: MobileOptimizer.state.isLandscape,
                    isOnline: MobileOptimizer.state.isOnline,
                    isInstalled: MobileOptimizer.state.isInstalled
                };
            }
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => MobileOptimizer.init());
    } else {
        MobileOptimizer.init();
    }

    // Export to global scope
    window.MobileOptimizer = MobileOptimizer;

})();