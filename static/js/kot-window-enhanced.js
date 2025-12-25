function kotWindow() {
  return {
    orders: (typeof window.activeOrders !== 'undefined') ? window.activeOrders : [],
    recentOrders: (typeof window.recentOrders !== 'undefined') ? window.recentOrders : [],
    currentFilter: 'all',
    autoRefresh: true,
    soundEnabled: true,
    lastOrderCount: (typeof window.activeOrders !== 'undefined' && window.activeOrders) ? window.activeOrders.length : 0,
    showBulkActions: false,
    selectedOrders: new Set(),
    refreshInterval: null,
    timeUpdateInterval: null,
    
    init() {
      // Start auto refresh if enabled
      if (this.autoRefresh) {
        this.startAutoRefresh();
      }
      
      // Start time updates
      this.startTimeUpdates();
      
      // Set up keyboard shortcuts
      this.setupKeyboardShortcuts();
      
      // Initial load
      this.refreshOrders();
      
      // Set up visibility change handler to pause/resume refresh when tab is not visible
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          this.stopAutoRefresh();
          this.stopTimeUpdates();
        } else {
          if (this.autoRefresh) {
            this.startAutoRefresh();
          }
          this.startTimeUpdates();
        }
      });
    },
    
    startAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
      }
      
      this.refreshInterval = setInterval(() => {
        if (this.autoRefresh && !document.hidden) {
          this.refreshOrders();
        }
      }, 10000); // Refresh every 10 seconds
    },
    
    stopAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
        this.refreshInterval = null;
      }
    },
    
    startTimeUpdates() {
      if (this.timeUpdateInterval) {
        clearInterval(this.timeUpdateInterval);
      }
      
      this.timeUpdateInterval = setInterval(() => {
        // Force Alpine.js to recompute time-based properties
        this.$el && this.$el._x_data && this.$el._x_data.update && this.$el._x_data.update();
      }, 1000); // Update every second
    },

    stopTimeUpdates() {
      if (this.timeUpdateInterval) {
        clearInterval(this.timeUpdateInterval);
        this.timeUpdateInterval = null;
      }
    },
    
    toggleAutoRefresh() {
      this.autoRefresh = !this.autoRefresh;
      if (this.autoRefresh) {
        this.startAutoRefresh();
        this.showNotification('Auto-refresh enabled', 'success');
      } else {
        this.stopAutoRefresh();
        this.showNotification('Auto-refresh disabled', 'info');
      }
    },
    
    toggleSound() {
      this.soundEnabled = !this.soundEnabled;
      this.showNotification(
        this.soundEnabled ? 'Sound enabled' : 'Sound disabled',
        'info'
      );
    },
    
    setFilter(filter) {
      this.currentFilter = filter;
    },
    
    async refreshOrders() {
      try {
        const response = await fetch('/kot/api/orders');
        const data = await response.json();
        
        if (data.success) {
          const previousOrders = [...this.orders];
          this.orders = data.orders;
          
          // Check for new orders and play sound
          if (this.soundEnabled) {
            this.checkForNewOrders(previousOrders, this.orders);
          }
          
          // Update last order count
          this.lastOrderCount = this.orders.length;
        }
      } catch (error) {
        console.error('Error refreshing orders:', error);
        this.showNotification('Failed to refresh orders', 'error');
      }
    },
    
    checkForNewOrders(previousOrders, currentOrders) {
      if (previousOrders.length === 0) return;
      
      const previousOrderIds = new Set(previousOrders.map(o => o.id));
      const newOrders = currentOrders.filter(o => !previousOrderIds.has(o.id));
      
      if (newOrders.length > 0) {
        // Check if any new orders are urgent
        const urgentOrders = newOrders.filter(o => this.getUrgencyLevel(o) === 'high');
        
        if (urgentOrders.length > 0) {
          this.playUrgentSound();
          this.showNotification(`${urgentOrders.length} urgent order(s) received!`, 'error');
        } else {
          this.playNotificationSound();
          this.showNotification(`${newOrders.length} new order(s) received`, 'success');
        }
      }
    },
    
    getFilteredOrders(status) {
      if (this.currentFilter === 'all') {
        return this.orders.filter(order => {
          if (status === 'new') return order.status === 'New';
          if (status === 'progress') return order.status === 'In Progress';
          if (status === 'ready') return order.status === 'Ready';
          if (status === 'completed') return order.status === 'Completed';
          return false;
        });
      } else {
        return this.orders.filter(order => order.status === this.getStatusFilterName(this.currentFilter));
      }
    },
    
    getStatusFilterName(filter) {
      const statusMap = {
        'new': 'New',
        'progress': 'In Progress',
        'ready': 'Ready',
        'completed': 'Completed'
      };
      return statusMap[filter] || filter;
    },
    
    getOrderCount(status) {
      return this.getFilteredOrders(status).length;
    },
    
    // Time-based functions
    getOrderAge(order) {
      if (!order.created_at) return '0:00';
      
      const now = new Date();
      const created = new Date(order.created_at);
      const diffMs = now - created;
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 60) {
        return `${diffMins}m`;
      } else {
        const hours = Math.floor(diffMins / 60);
        const mins = diffMins % 60;
        return `${hours}h ${mins}m`;
      }
    },

    getUrgencyLevel(order) {
      if (!order.created_at) return 'normal';
      
      const now = new Date();
      const created = new Date(order.created_at);
      const diffMins = Math.floor((now - created) / 60000);
      
      if (diffMins > 20) return 'high';
      if (diffMins > 10) return 'medium';
      return 'normal';
    },

    getTimeStatus(order) {
      if (!order.created_at) return 'Unknown';
      
      const now = new Date();
      const created = new Date(order.created_at);
      const diffMins = Math.floor((now - created) / 60000);
      
      if (diffMins > 20) return 'DELAYED';
      if (diffMins > 10) return 'ATTENTION';
      return 'ON TIME';
    },

    getTimeIndicatorClass(order) {
      const urgency = this.getUrgencyLevel(order);
      return `time-${urgency === 'high' ? 'urgent' : urgency === 'medium' ? 'attention' : 'normal'}`;
    },
    
    formatTime(timeString) {
      if (!timeString) return '';
      const date = new Date(timeString);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    },
    
    hasSpecialInstructions(order) {
      return order.items && order.items.some(item => item.special_instructions);
    },
    
    getSpecialInstructions(order) {
      const instructions = order.items
        .filter(item => item.special_instructions)
        .map(item => item.special_instructions)
        .join('; ');
      return instructions || '';
    },
    
    getNextStatus(currentStatus) {
      const statusFlow = {
        'Pending': 'In Progress',
        'In Progress': 'Ready',
        'Ready': 'Completed',
        'Completed': 'Pending'
      };
      return statusFlow[currentStatus] || 'Pending';
    },
    
    async updateItemStatus(itemId, newStatus) {
      try {
        const response = await fetch('/kot/api/update_item_status', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            item_id: itemId,
            status: newStatus
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          this.showNotification(`Item status updated to ${newStatus}`, 'success');
          // Refresh orders to update UI
          setTimeout(() => this.refreshOrders(), 500);
        } else {
          this.showNotification(result.message || 'Failed to update item', 'error');
        }
      } catch (error) {
        console.error('Error updating item status:', error);
        this.showNotification('Error updating item status', 'error');
      }
    },
    
    async startOrder(orderId) {
      try {
        const response = await fetch('/kot/api/update_order_status', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            order_id: orderId,
            status: 'In Progress'
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          this.showNotification('Order started', 'success');
          setTimeout(() => this.refreshOrders(), 500);
        } else {
          this.showNotification(result.message || 'Failed to start order', 'error');
        }
      } catch (error) {
        console.error('Error starting order:', error);
        this.showNotification('Error starting order', 'error');
      }
    },
    
    async markReady(orderId) {
      try {
        const response = await fetch('/kot/api/update_order_status', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            order_id: orderId,
            status: 'Ready'
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          this.showNotification('Order marked as ready', 'success');
          setTimeout(() => this.refreshOrders(), 500);
        } else {
          this.showNotification(result.message || 'Failed to mark order as ready', 'error');
        }
      } catch (error) {
        console.error('Error marking order as ready:', error);
        this.showNotification('Error marking order as ready', 'error');
      }
    },
    
    async completeOrder(orderId) {
      try {
        const response = await fetch('/kot/api/update_order_status', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            order_id: orderId,
            status: 'Completed'
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          this.showNotification('Order completed', 'success');
          setTimeout(() => this.refreshOrders(), 500);
        } else {
          this.showNotification(result.message || 'Failed to complete order', 'error');
        }
      } catch (error) {
        console.error('Error completing order:', error);
        this.showNotification('Error completing order', 'error');
      }
    },
    
    async printKOT(orderId) {
      try {
        window.open(`/kot/print/${orderId}`, '_blank', 'width=400,height=600');
      } catch (error) {
        console.error('Error printing KOT:', error);
        this.showNotification('Error printing KOT', 'error');
      }
    },
    
    async printAllPending() {
      const pendingOrders = this.orders.filter(order => order.status === 'New');
      
      if (pendingOrders.length === 0) {
        this.showNotification('No pending orders to print', 'info');
        return;
      }
      
      for (const order of pendingOrders) {
        await this.printKOT(order.id);
        // Small delay between prints to avoid overwhelming the printer
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      this.showNotification(`Printed ${pendingOrders.length} KOTs`, 'success');
    },
    
    selectOrder(order) {
      // Toggle selection for bulk actions
      if (this.selectedOrders.has(order.id)) {
        this.selectedOrders.delete(order.id);
      } else {
        this.selectedOrders.add(order.id);
      }
    },
    
    openBulkActions() {
      this.showBulkActions = true;
    },
    
    closeBulkActions() {
      this.showBulkActions = false;
    },
    
    toggleSelectAll() {
      const visibleOrders = this.getFilteredOrders(this.currentFilter === 'all' ? 'new' : this.currentFilter);
      
      if (this.selectedOrders.size === visibleOrders.length) {
        // Deselect all
        this.selectedOrders.clear();
      } else {
        // Select all visible
        visibleOrders.forEach(order => this.selectedOrders.add(order.id));
      }
    },
    
    get allSelected() {
      const visibleOrders = this.getFilteredOrders(this.currentFilter === 'all' ? 'new' : this.currentFilter);
      return visibleOrders.length > 0 && visibleOrders.every(order => this.selectedOrders.has(order.id));
    },
    
    async bulkUpdateStatus(status) {
      if (this.selectedOrders.size === 0) {
        this.showNotification('No orders selected', 'warning');
        return;
      }
      
      try {
        const response = await fetch('/kot/api/bulk_update', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            item_ids: Array.from(this.selectedOrders),
            status: status
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          this.showNotification(result.message, 'success');
          this.selectedOrders.clear();
          this.closeBulkActions();
          setTimeout(() => this.refreshOrders(), 500);
        } else {
          this.showNotification(result.message || 'Failed to update orders', 'error');
        }
      } catch (error) {
        console.error('Error updating orders:', error);
        this.showNotification('Error updating orders', 'error');
      }
    },
    
    playNotificationSound() {
      const audio = document.getElementById('notificationSound');
      if (audio && this.soundEnabled) {
        audio.play().catch(e => console.log('Could not play sound:', e));
      }
    },
    
    playUrgentSound() {
      const audio = document.getElementById('urgentSound');
      if (audio && this.soundEnabled) {
        audio.play().catch(e => console.log('Could not play urgent sound:', e));
      }
    },
    
    showNotification(message, type = 'info') {
      const container = document.getElementById('notificationContainer');
      const toast = document.createElement('div');
      toast.className = `notification-toast notification-${type}`;
      toast.textContent = message;
      
      container.appendChild(toast);
      
      // Auto remove after 3 seconds
      setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    },
    
    setupKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        // Only process shortcuts when not typing in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
          return;
        }
        
        switch(e.key) {
          case 'r':
          case 'R':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.refreshOrders();
            }
            break;
          case 's':
          case 'S':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.toggleSound();
            }
            break;
          case 'a':
          case 'A':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.toggleAutoRefresh();
            }
            break;
          case 'b':
          case 'B':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.openBulkActions();
            }
            break;
          case 'p':
          case 'P':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.printAllPending();
            }
            break;
          case '1':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.setFilter('all');
            }
            break;
          case '2':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.setFilter('new');
            }
            break;
          case '3':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.setFilter('progress');
            }
            break;
          case '4':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.setFilter('ready');
            }
            break;
          case '5':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.setFilter('completed');
            }
            break;
          case 'Escape':
            if (this.showBulkActions) {
              e.preventDefault();
              this.closeBulkActions();
            }
            break;
        }
      });
    }
  };
}

// Initialize Alpine.js when DOM is ready
document.addEventListener("alpine:init", function () {
  Alpine.data("kotWindow", kotWindow);
});