/**
 * Mobile Kitchen Display
 * Optimized for tablets and mobile devices with touch interactions
 */

class MobileKitchenDisplay {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.orders = new Map();
    this.isOnline = navigator.onLine;
    this.pendingActions = [];
    this.displayConfig = this.loadDisplayConfig();
    
    // Mobile-specific features
    this.touchGestures = new TouchGestures();
    this.swipeThreshold = 50;
    this.isFullscreen = false;
    this.vibrationEnabled = true;
    
    // Performance optimization
    this.renderQueue = [];
    this.isRendering = false;
    this.lastRenderTime = 0;
    this.minRenderInterval = 100; // Minimum time between renders
    
    this.init();
  }
  
  init() {
    this.setupMobileUI();
    this.setupEventListeners();
    this.setupOfflineSupport();
    this.connectWebSocket();
    this.startPeriodicSync();
    
    // Setup PWA features
    this.setupPWAFeatures();
    
    console.log('Mobile Kitchen Display initialized');
  }
  
  setupMobileUI() {
    // Create mobile-optimized layout
    this.createMobileLayout();
    
    // Setup touch interactions
    this.setupTouchInteractions();
    
    // Initialize swipe gestures
    this.touchGestures.onSwipeLeft = () => this.showNextStatusFilter();
    this.touchGestures.onSwipeRight = () => this.showPreviousStatusFilter();
    this.touchGestures.onSwipeUp = () => this.scrollToTop();
    this.touchGestures.onSwipeDown = () => this.scrollToBottom();
    
    // Add mobile-specific CSS classes
    document.body.classList.add('mobile-kitchen-display');
    
    // Setup responsive breakpoints
    this.handleResize();
    window.addEventListener('resize', () => this.handleResize());
  }
  
  createMobileLayout() {
    const container = document.getElementById('app');
    
    // Create mobile header
    const mobileHeader = this.createMobileHeader();
    container.insertBefore(mobileHeader, container.firstChild);
    
    // Create mobile navigation
    const mobileNav = this.createMobileNavigation();
    container.appendChild(mobileNav);
    
    // Create connection status bar
    const statusBar = this.createConnectionStatusBar();
    container.appendChild(statusBar);
  }
  
  createMobileHeader() {
    const header = document.createElement('div');
    header.className = 'mobile-header';
    header.innerHTML = `
      <div class="header-content">
        <div class="header-left">
          <button class="menu-btn" id="menuBtn">
            <i class="fas fa-bars"></i>
          </button>
          <h1 class="header-title">Kitchen Display</h1>
        </div>
        
        <div class="header-right">
          <button class="status-btn" id="connectionStatusBtn">
            <div class="status-indicator status-connecting"></div>
          </button>
          <button class="fullscreen-btn" id="fullscreenBtn">
            <i class="fas fa-expand"></i>
          </button>
        </div>
      </div>
      
      <div class="mobile-toolbar" id="mobileToolbar" style="display: none;">
        <button class="toolbar-btn active" data-filter="all">
          <i class="fas fa-list"></i>
          <span>All</span>
        </button>
        <button class="toolbar-btn" data-filter="new">
          <i class="fas fa-clock"></i>
          <span>New</span>
        </button>
        <button class="toolbar-btn" data-filter="progress">
          <i class="fas fa-fire"></i>
          <span>Cooking</span>
        </button>
        <button class="toolbar-btn" data-filter="ready">
          <i class="fas fa-check"></i>
          <span>Ready</span>
        </button>
      </div>
    `;
    
    return header;
  }
  
  createMobileNavigation() {
    const nav = document.createElement('div');
    nav.className = 'mobile-nav';
    nav.innerHTML = `
      <div class="nav-overlay" id="navOverlay"></div>
      <div class="nav-drawer" id="navDrawer">
        <div class="nav-header">
          <h3>Menu</h3>
          <button class="nav-close" id="navClose">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="nav-content">
          <div class="nav-section">
            <h4>Display Settings</h4>
            <div class="setting-item">
              <label>Auto Refresh</label>
              <input type="checkbox" id="autoRefreshToggle" checked>
            </div>
            <div class="setting-item">
              <label>Sound Alerts</label>
              <input type="checkbox" id="soundToggle" checked>
            </div>
            <div class="setting-item">
              <label>Vibration</label>
              <input type="checkbox" id="vibrationToggle" checked>
            </div>
          </div>
          
          <div class="nav-section">
            <h4>Filters</h4>
            <div class="filter-group">
              <label>Urgency Level</label>
              <select id="urgencyFilter">
                <option value="all">All Orders</option>
                <option value="high">High Priority</option>
                <option value="normal">Normal Only</option>
              </select>
            </div>
          </div>
          
          <div class="nav-section">
            <h4>Actions</h4>
            <button class="nav-action" id="refreshBtn">
              <i class="fas fa-sync"></i>
              Refresh Orders
            </button>
            <button class="nav-action" id="printBtn">
              <i class="fas fa-print"></i>
              Print All
            </button>
            <button class="nav-action" id="settingsBtn">
              <i class="fas fa-cog"></i>
              Settings
            </button>
          </div>
        </div>
      </div>
    `;
    
    return nav;
  }
  
  createConnectionStatusBar() {
    const statusBar = document.createElement('div');
    statusBar.className = 'connection-status-bar';
    statusBar.innerHTML = `
      <div class="status-content">
        <div class="status-info">
          <span class="status-text" id="statusText">Connecting...</span>
          <span class="order-count" id="orderCount">0 orders</span>
        </div>
        <div class="status-actions">
          <button class="action-btn" id="syncBtn" title="Sync">
            <i class="fas fa-sync"></i>
          </button>
          <button class="action-btn" id="alertBtn" title="Alert" style="display: none;">
            <i class="fas fa-exclamation-triangle"></i>
          </button>
        </div>
      </div>
    `;
    
    return statusBar;
  }
  
  setupTouchInteractions() {
    // Enable pull-to-refresh
    let startY = 0;
    let pullDistance = 0;
    const pullThreshold = 100;
    
    document.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1 && window.scrollY === 0) {
        startY = e.touches[0].clientY;
      }
    });
    
    document.addEventListener('touchmove', (e) => {
      if (startY > 0 && window.scrollY === 0) {
        pullDistance = e.touches[0].clientY - startY;
        if (pullDistance > 0 && pullDistance < pullThreshold) {
          this.showPullToRefreshIndicator(pullDistance / pullThreshold);
        }
      }
    });
    
    document.addEventListener('touchend', (e) => {
      if (pullDistance >= pullThreshold) {
        this.refreshOrders();
      }
      startY = 0;
      pullDistance = 0;
      this.hidePullToRefreshIndicator();
    });
    
    // Setup gesture recognition
    this.touchGestures.init();
  }
  
  setupEventListeners() {
    // Header buttons
    document.getElementById('menuBtn').addEventListener('click', () => this.toggleNavigation());
    document.getElementById('fullscreenBtn').addEventListener('click', () => this.toggleFullscreen());
    document.getElementById('connectionStatusBtn').addEventListener('click', () => this.showConnectionInfo());
    
    // Navigation
    document.getElementById('navClose').addEventListener('click', () => this.closeNavigation());
    document.getElementById('navOverlay').addEventListener('click', () => this.closeNavigation());
    
    // Toolbar filters
    document.querySelectorAll('.toolbar-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.setActiveFilter(e.currentTarget.dataset.filter);
      });
    });
    
    // Settings toggles
    document.getElementById('autoRefreshToggle').addEventListener('change', (e) => {
      this.displayConfig.autoRefresh = e.target.checked;
      this.saveDisplayConfig();
    });
    
    document.getElementById('soundToggle').addEventListener('change', (e) => {
      this.displayConfig.soundEnabled = e.target.checked;
      this.saveDisplayConfig();
    });
    
    document.getElementById('vibrationToggle').addEventListener('change', (e) => {
      this.vibrationEnabled = e.target.checked;
      this.saveDisplayConfig();
    });
    
    // Action buttons
    document.getElementById('syncBtn').addEventListener('click', () => this.manualSync());
    document.getElementById('refreshBtn').addEventListener('click', () => this.refreshOrders());
    
    // Filter controls
    document.getElementById('urgencyFilter').addEventListener('change', (e) => {
      this.displayConfig.urgencyFilter = e.target.value;
      this.renderOrders();
      this.saveDisplayConfig();
    });
    
    // Network status
    window.addEventListener('online', () => this.handleOnlineStatus(true));
    window.addEventListener('offline', () => this.handleOnlineStatus(false));
    
    // Prevent zoom on double-tap
    let lastTouchEnd = 0;
    document.addEventListener('touchend', (e) => {
      const now = (new Date()).getTime();
      if (now - lastTouchEnd <= 300) {
        e.preventDefault();
      }
      lastTouchEnd = now;
    }, false);
  }
  
  setupOfflineSupport() {
    // Service Worker registration
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then((registration) => {
          console.log('Service Worker registered:', registration);
        })
        .catch((error) => {
          console.log('Service Worker registration failed:', error);
        });
    }
    
    // Cache order data for offline viewing
    this.setupOfflineCache();
    
    // Handle offline queue for actions
    this.setupOfflineQueue();
  }
  
  setupOfflineCache() {
    // Cache recent orders for offline viewing
    this.orderCache = {
      maxSize: 50,
      orders: new Map(),
      timestamp: null
    };
  }
  
  setupOfflineQueue() {
    // Queue actions for when connection is restored
    this.offlineQueue = [];
    
    // Listen for online event to process queue
    window.addEventListener('online', () => {
      this.processOfflineQueue();
    });
  }
  
  setupPWAFeatures() {
    // PWA manifest handling
    this.setupAppManifest();
    
    // Install prompt
    this.setupInstallPrompt();
    
    // Push notifications (if supported)
    this.setupPushNotifications();
  }
  
  setupAppManifest() {
    // Create app manifest for PWA
    const manifest = {
      name: "Kitchen Display",
      short_name: "Kitchen",
      description: "Real-time kitchen order display",
      start_url: "/kot/display",
      display: "standalone",
      orientation: "landscape",
      theme_color: "#1e3c72",
      background_color: "#1e3c72",
      icons: [
        {
          src: "/static/images/icon-192.png",
          sizes: "192x192",
          type: "image/png"
        },
        {
          src: "/static/images/icon-512.png",
          sizes: "512x512",
          type: "image/png"
        }
      ]
    };
    
    // Update manifest dynamically
    const manifestScript = document.createElement('script');
    manifestScript.type = 'application/manifest+json';
    manifestScript.textContent = JSON.stringify(manifest);
    document.head.appendChild(manifestScript);
  }
  
  setupInstallPrompt() {
    let deferredPrompt;
    
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      
      // Show install button
      this.showInstallButton();
    });
    
    // Handle install button click
    document.addEventListener('click', (e) => {
      if (e.target && e.target.id === 'installAppBtn') {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('User accepted the install prompt');
          }
          deferredPrompt = null;
          this.hideInstallButton();
        });
      }
    });
  }
  
  setupPushNotifications() {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      // Request notification permission
      Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
          this.subscribeToPushNotifications();
        }
      });
    }
  }
  
  subscribeToPushNotifications() {
    navigator.serviceWorker.ready.then((registration) => {
      return registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(this.getVapidPublicKey())
      });
    }).then((subscription) => {
      console.log('Push subscription successful:', subscription);
      // Send subscription to server
      this.sendSubscriptionToServer(subscription);
    });
  }
  
  connectWebSocket() {
    if (!this.isOnline) {
      this.showOfflineMessage();
      return;
    }
    
    try {
      // Use mobile-optimized Socket.IO connection
      this.socket = io('/ws', {
        auth: {
          token: this.getAuthToken()
        },
        query: {
          display_name: this.displayConfig.displayName,
          station_type: this.displayConfig.stationType,
          kitchen_role: this.displayConfig.kitchenRole,
          mobile: true,
          platform: this.getMobilePlatform()
        },
        transports: ['websocket', 'polling'],
        upgrade: true,
        rememberUpgrade: true
      });
      
      this.setupMobileSocketEvents();
      
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.showConnectionError();
    }
  }
  
  setupMobileSocketEvents() {
    // Connection events with mobile-specific handling
    this.socket.on('connect', () => {
      this.connected = true;
      this.updateConnectionStatus('Connected', 'connected');
      this.hideOfflineMessage();
      this.vibrate([100]);
    });
    
    this.socket.on('disconnect', () => {
      this.connected = false;
      this.updateConnectionStatus('Disconnected', 'disconnected');
      this.vibrate([200, 100, 200]);
    });
    
    this.socket.on('connect_error', (error) => {
      this.connected = false;
      this.updateConnectionStatus('Connection Error', 'error');
      console.error('Connection error:', error);
    });
    
    // Mobile-optimized order events
    this.socket.on('order_event', (data) => {
      this.handleOrderEvent(data);
    });
    
    this.socket.on('orders_sync', (data) => {
      this.loadOrders(data.orders);
    });
    
    // Kitchen alerts with vibration
    this.socket.on('kitchen_alert', (data) => {
      this.handleKitchenAlert(data);
    });
    
    // Mobile-specific events
    this.socket.on('mobile_notification', (data) => {
      this.showMobileNotification(data);
    });
  }
  
  handleOrderEvent(data) {
    const { type, data: eventData } = data;
    
    // Throttle updates for mobile performance
    this.queueRender(() => {
      switch (type) {
        case 'new_order':
          this.addOrder(eventData);
          if (this.vibrationEnabled) {
            this.vibrate([100, 50, 100]);
          }
          this.showNewOrderNotification(eventData);
          break;
          
        case 'order_update':
          this.updateOrder(eventData);
          break;
          
        case 'item_update':
          this.updateOrderItem(eventData);
          break;
          
        case 'order_complete':
          this.removeOrder(eventData.order_id);
          this.vibrate([100]);
          break;
      }
    });
  }
  
  showNewOrderNotification(orderData) {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('New Order', {
        body: `Order #${orderData.order_number} - ${orderData.order_type}`,
        icon: '/static/images/icon-192.png',
        tag: `order-${orderData.order_id}`,
        requireInteraction: true
      });
    }
  }
  
  handleKitchenAlert(data) {
    const { type, message } = data;
    
    // Mobile-specific alert handling
    if (type === 'urgent') {
      this.vibrate([300, 100, 300, 100, 300]);
      this.showUrgentAlert(message);
    } else {
      this.vibrate([200]);
    }
    
    // Show in-app notification
    this.showInAppNotification(message, type);
  }
  
  showInAppNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `mobile-notification mobile-notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <i class="fas fa-${this.getNotificationIcon(type)}"></i>
        <span class="notification-message">${message}</span>
        <button class="notification-close">&times;</button>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      notification.remove();
    }, 5000);
    
    // Close button
    notification.querySelector('.notification-close').addEventListener('click', () => {
      notification.remove();
    });
  }
  
  getNotificationIcon(type) {
    const icons = {
      'info': 'info-circle',
      'success': 'check-circle',
      'warning': 'exclamation-triangle',
      'error': 'times-circle',
      'urgent': 'exclamation-triangle'
    };
    return icons[type] || 'info-circle';
  }
  
  queueRender(renderFunction) {
    this.renderQueue.push(renderFunction);
    this.processRenderQueue();
  }
  
  async processRenderQueue() {
    if (this.isRendering) return;
    
    const now = Date.now();
    if (now - this.lastRenderTime < this.minRenderInterval) {
      setTimeout(() => this.processRenderQueue(), this.minRenderInterval);
      return;
    }
    
    this.isRendering = true;
    
    while (this.renderQueue.length > 0) {
      const renderFunction = this.renderQueue.shift();
      try {
        renderFunction();
      } catch (error) {
        console.error('Render error:', error);
      }
    }
    
    this.isRendering = false;
    this.lastRenderTime = Date.now();
  }
  
  renderOrders() {
    const grid = document.getElementById('ordersGrid');
    if (!grid) return;
    
    if (this.orders.size === 0) {
      grid.innerHTML = this.createEmptyStateHTML();
      return;
    }
    
    // Sort orders by priority and creation time
    const sortedOrders = Array.from(this.orders.values()).sort((a, b) => {
      const priorityOrder = { 'critical': 4, 'high': 3, 'medium': 2, 'normal': 1 };
      const aPriority = priorityOrder[a.priority?.level] || 1;
      const bPriority = priorityOrder[b.priority?.level] || 1;
      
      if (aPriority !== bPriority) {
        return bPriority - aPriority;
      }
      
      return new Date(a.created_at) - new Date(b.created_at);
    });
    
    // Apply current filter
    const filteredOrders = this.applyOrderFilters(sortedOrders);
    
    // Render with mobile-optimized cards
    grid.innerHTML = filteredOrders.map(order => this.createMobileOrderCard(order)).join('');
    
    // Add touch event listeners
    this.addMobileCardEventListeners();
  }
  
  createMobileOrderCard(order) {
    const ageMinutes = this.calculateOrderAge(order.created_at);
    const urgencyClass = order.priority?.level === 'critical' ? 'urgent' : '';
    const timerClass = ageMinutes > 20 ? 'urgent' : '';
    
    return `
      <div class="mobile-order-card ${urgencyClass}" data-order-id="${order.id}">
        <div class="card-header">
          <div class="order-info">
            <div class="order-number">#${order.order_number}</div>
            <div class="order-time">${this.formatTime(order.created_at)}</div>
          </div>
          <div class="order-meta">
            ${order.table_number ? `<span class="table-badge">T${order.table_number}</span>` : ''}
            <span class="type-badge">${order.order_type}</span>
          </div>
        </div>
        
        <div class="card-timer">
          <i class="fas fa-clock"></i>
          <span class="timer-text ${timerClass}">${ageMinutes}m</span>
          ${order.priority?.level === 'critical' ? '<span class="urgent-indicator">!</span>' : ''}
        </div>
        
        <div class="card-items">
          ${order.items.map(item => `
            <div class="item-row">
              <div class="item-info">
                <span class="item-name">${item.item_name}</span>
                <span class="item-quantity">x${item.quantity}</span>
              </div>
              <button class="item-status-btn status-${item.status.toLowerCase().replace(' ', '-')}" 
                      onclick="mobileKitchenDisplay.updateItemStatus(${item.id}, '${this.getNextStatus(item.status)}')">
                ${item.status}
              </button>
            </div>
          `).join('')}
        </div>
        
        ${order.special_instructions ? `
          <div class="special-instructions">
            <i class="fas fa-info-circle"></i>
            <span>${order.special_instructions}</span>
          </div>
        ` : ''}
        
        <div class="card-actions">
          ${order.status === 'New' ? `
            <button class="action-btn start" onclick="mobileKitchenDisplay.updateOrderStatus(${order.id}, 'In Progress')">
              <i class="fas fa-play"></i>
              Start
            </button>
          ` : ''}
          
          ${order.status === 'In Progress' ? `
            <button class="action-btn ready" onclick="mobileKitchenDisplay.updateOrderStatus(${order.id}, 'Ready')">
              <i class="fas fa-check"></i>
              Ready
            </button>
          ` : ''}
          
          ${order.status === 'Ready' ? `
            <button class="action-btn complete" onclick="mobileKitchenDisplay.updateOrderStatus(${order.id}, 'Completed')">
              <i class="fas fa-check-double"></i>
              Complete
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }
  
  addMobileCardEventListeners() {
    // Swipe gestures for order cards
    document.querySelectorAll('.mobile-order-card').forEach(card => {
      let startX = 0;
      let startY = 0;
      
      card.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      });
      
      card.addEventListener('touchend', (e) => {
        const endX = e.changedTouches[0].clientX;
        const endY = e.changedTouches[0].clientY;
        const diffX = startX - endX;
        const diffY = startY - endY;
        
        // Horizontal swipe
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > this.swipeThreshold) {
          const orderId = card.dataset.orderId;
          
          if (diffX > 0) {
            // Swipe left - mark as ready
            this.updateOrderStatus(orderId, 'Ready');
          } else {
            // Swipe right - mark as in progress
            this.updateOrderStatus(orderId, 'In Progress');
          }
        }
      });
    });
  }
  
  // Utility methods
  vibrate(pattern) {
    if (this.vibrationEnabled && 'vibrate' in navigator) {
      navigator.vibrate(pattern);
    }
  }
  
  showPullToRefreshIndicator(progress) {
    let indicator = document.getElementById('pullRefreshIndicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'pullRefreshIndicator';
      indicator.className = 'pull-refresh-indicator';
      indicator.innerHTML = `
        <div class="refresh-icon">
          <i class="fas fa-arrow-down"></i>
        </div>
        <div class="refresh-text">Pull to refresh</div>
      `;
      document.body.appendChild(indicator);
    }
    
    indicator.style.transform = `translateY(${Math.min(progress * 60, 60)}px)`;
    indicator.style.opacity = progress;
  }
  
  hidePullToRefreshIndicator() {
    const indicator = document.getElementById('pullRefreshIndicator');
    if (indicator) {
      indicator.style.transform = 'translateY(-100px)';
      indicator.style.opacity = '0';
    }
  }
  
  handleOnlineStatus(isOnline) {
    this.isOnline = isOnline;
    
    if (isOnline) {
      this.updateConnectionStatus('Online', 'connected');
      this.connectWebSocket();
      this.processOfflineQueue();
    } else {
      this.updateConnectionStatus('Offline', 'disconnected');
      this.showOfflineMessage();
    }
  }
  
  showOfflineMessage() {
    this.showInAppNotification('Working offline - some features may be limited', 'warning');
  }
  
  getMobilePlatform() {
    const userAgent = navigator.userAgent.toLowerCase();
    if (userAgent.includes('android')) return 'android';
    if (userAgent.includes('iphone') || userAgent.includes('ipad')) return 'ios';
    return 'other';
  }
  
  getAuthToken() {
    return localStorage.getItem('auth_token') || '';
  }
  
  loadDisplayConfig() {
    const defaultConfig = {
      displayName: 'Mobile Kitchen Display',
      stationType: 'general',
      kitchenRole: 'kitchen_staff',
      autoRefresh: true,
      soundEnabled: true,
      urgencyFilter: 'all'
    };
    
    try {
      const saved = localStorage.getItem('mobileKitchenDisplayConfig');
      return saved ? { ...defaultConfig, ...JSON.parse(saved) } : defaultConfig;
    } catch {
      return defaultConfig;
    }
  }
  
  saveDisplayConfig() {
    localStorage.setItem('mobileKitchenDisplayConfig', JSON.stringify(this.displayConfig));
  }
  
  // Event handlers
  toggleNavigation() {
    const drawer = document.getElementById('navDrawer');
    const overlay = document.getElementById('navOverlay');
    drawer.classList.toggle('open');
    overlay.classList.toggle('show');
  }
  
  closeNavigation() {
    const drawer = document.getElementById('navDrawer');
    const overlay = document.getElementById('navOverlay');
    drawer.classList.remove('open');
    overlay.classList.remove('show');
  }
  
  toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      this.isFullscreen = true;
    } else {
      document.exitFullscreen();
      this.isFullscreen = false;
    }
  }
  
  setActiveFilter(filter) {
    // Update toolbar
    document.querySelectorAll('.toolbar-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    
    this.displayConfig.activeFilter = filter;
    this.renderOrders();
    this.saveDisplayConfig();
  }
  
  applyOrderFilters(orders) {
    let filtered = orders;
    
    // Status filter
    if (this.displayConfig.activeFilter && this.displayConfig.activeFilter !== 'all') {
      filtered = filtered.filter(order => order.status.toLowerCase() === this.displayConfig.activeFilter);
    }
    
    // Urgency filter
    if (this.displayConfig.urgencyFilter && this.displayConfig.urgencyFilter !== 'all') {
      filtered = filtered.filter(order => order.priority?.level === this.displayConfig.urgencyFilter);
    }
    
    return filtered;
  }
  
  handleResize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    // Update body classes for responsive design
    document.body.classList.toggle('mobile-portrait', width < height && width < 768);
    document.body.classList.toggle('mobile-landscape', width > height && width < 1024);
    document.body.classList.toggle('tablet', width >= 768 && width < 1024);
    document.body.classList.toggle('desktop', width >= 1024);
  }
  
  showInstallButton() {
    const installBtn = document.createElement('button');
    installBtn.id = 'installAppBtn';
    installBtn.className = 'install-app-btn';
    installBtn.innerHTML = '<i class="fas fa-download"></i> Install App';
    document.body.appendChild(installBtn);
  }
  
  hideInstallButton() {
    const installBtn = document.getElementById('installAppBtn');
    if (installBtn) {
      installBtn.remove();
    }
  }
  
  // Utility functions (delegated to parent class or external functions)
  calculateOrderAge(createdAt) {
    const now = new Date();
    const created = new Date(createdAt);
    return Math.floor((now - created) / 1000 / 60);
  }
  
  formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  }
  
  getNextStatus(currentStatus) {
    const statusFlow = {
      'Pending': 'In Progress',
      'In Progress': 'Ready',
      'Ready': 'Completed'
    };
    return statusFlow[currentStatus] || currentStatus;
  }
  
  updateOrderStatus(orderId, newStatus) {
    if (!this.connected) {
      this.queueOfflineAction('updateOrderStatus', { orderId, newStatus });
      return;
    }
    
    this.socket.emit('update_order_status', {
      order_id: orderId,
      status: newStatus,
      reason: 'Updated via mobile display'
    });
  }
  
  updateItemStatus(itemId, newStatus) {
    if (!this.connected) {
      this.queueOfflineAction('updateItemStatus', { itemId, newStatus });
      return;
    }
    
    this.socket.emit('update_item_status', {
      item_id: itemId,
      status: newStatus
    });
  }
  
  queueOfflineAction(action, data) {
    this.offlineQueue.push({ action, data, timestamp: Date.now() });
    this.showInAppNotification('Action queued for sync when online', 'info');
  }
  
  processOfflineQueue() {
    while (this.offlineQueue.length > 0) {
      const { action, data } = this.offlineQueue.shift();
      if (action === 'updateOrderStatus') {
        this.updateOrderStatus(data.orderId, data.newStatus);
      } else if (action === 'updateItemStatus') {
        this.updateItemStatus(data.itemId, data.newStatus);
      }
    }
  }
  
  manualSync() {
    if (this.connected) {
      this.socket.emit('request_orders', {
        filters: this.getCurrentFilters()
      });
      this.showInAppNotification('Syncing orders...', 'info');
    } else {
      this.showInAppNotification('Not connected to server', 'error');
    }
  }
  
  refreshOrders() {
    if (this.connected) {
      this.socket.emit('request_orders', {
        filters: this.getCurrentFilters()
      });
    } else {
      // Load from cache
      this.loadOrdersFromCache();
    }
  }
  
  getCurrentFilters() {
    return {
      status_filter: this.displayConfig.activeFilter || 'all',
      urgency_filter: this.displayConfig.urgencyFilter || 'all',
      station_type: this.displayConfig.stationType
    };
  }
}

// Touch Gestures Helper Class
class TouchGestures {
  constructor() {
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.touchEndX = 0;
    this.touchEndY = 0;
    
    this.minSwipeDistance = 50;
    this.maxSwipeTime = 500;
    
    this.onSwipeLeft = null;
    this.onSwipeRight = null;
    this.onSwipeUp = null;
    this.onSwipeDown = null;
  }
  
  init() {
    document.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
    document.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });
  }
  
  handleTouchStart(e) {
    this.touchStartX = e.changedTouches[0].screenX;
    this.touchStartY = e.changedTouches[0].screenY;
    this.touchStartTime = Date.now();
  }
  
  handleTouchEnd(e) {
    this.touchEndX = e.changedTouches[0].screenX;
    this.touchEndY = e.changedTouches[0].screenY;
    this.handleGesture();
  }
  
  handleGesture() {
    const deltaX = this.touchStartX - this.touchEndX;
    const deltaY = this.touchStartY - this.touchEndY;
    const deltaTime = Date.now() - this.touchStartTime;
    
    // Check if gesture is valid
    if (deltaTime > this.maxSwipeTime) return;
    
    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);
    
    // Determine swipe direction
    if (absX > absY && absX > this.minSwipeDistance) {
      // Horizontal swipe
      if (deltaX > 0) {
        this.onSwipeLeft && this.onSwipeLeft();
      } else {
        this.onSwipeRight && this.onSwipeRight();
      }
    } else if (absY > absX && absY > this.minSwipeDistance) {
      // Vertical swipe
      if (deltaY > 0) {
        this.onSwipeUp && this.onSwipeUp();
      } else {
        this.onSwipeDown && this.onSwipeDown();
      }
    }
  }
}

// Initialize mobile kitchen display
document.addEventListener('DOMContentLoaded', () => {
  window.mobileKitchenDisplay = new MobileKitchenDisplay();
});