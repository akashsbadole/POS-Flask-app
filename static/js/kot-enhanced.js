function kotDisplay() {
  return {
    activeOrders: (typeof window.activeOrders !== 'undefined') ? window.activeOrders : [],
    filterStatus: "all",
    autoRefresh: true,
    soundEnabled: true,
    lastOrderCount: (typeof window.activeOrdersCount !== 'undefined') ? window.activeOrdersCount : 0,
    showBulkActions: false,
    selectedOrders: new Set(),
    refreshInterval: null,
    timeUpdateInterval: null,

    init: function () {
      // Start auto refresh if enabled
      if (this.autoRefresh) {
        this.startAutoRefresh();
      }
      
      // Start time updates
      this.startTimeUpdates();
      
      // Set up keyboard shortcuts
      this.setupKeyboardShortcuts();
      
      // Set up visibility change handler
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

    startAutoRefresh: function () {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
      }
      
      this.refreshInterval = setInterval(
        function () {
          if (this.autoRefresh && !document.hidden) {
            this.refreshOrders();
          }
        }.bind(this),
        10000
      ); // Refresh every 10 seconds
    },

    stopAutoRefresh: function () {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
        this.refreshInterval = null;
      }
    },

    startTimeUpdates: function () {
      if (this.timeUpdateInterval) {
        clearInterval(this.timeUpdateInterval);
      }
      
      this.timeUpdateInterval = setInterval(() => {
        // Force Alpine.js to recompute time-based properties
        this.$el && this.$el._x_data && this.$el._x_data.update && this.$el._x_data.update();
      }, 1000); // Update every second
    },

    stopTimeUpdates: function () {
      if (this.timeUpdateInterval) {
        clearInterval(this.timeUpdateInterval);
        this.timeUpdateInterval = null;
      }
    },

    toggleAutoRefresh: function () {
      this.autoRefresh = !this.autoRefresh;
      if (this.autoRefresh) {
        this.startAutoRefresh();
        this.showNotification('Auto-refresh enabled', 'success');
      } else {
        this.stopAutoRefresh();
        this.showNotification('Auto-refresh disabled', 'info');
      }
    },

    toggleSound: function () {
      this.soundEnabled = !this.soundEnabled;
      this.showNotification(
        this.soundEnabled ? 'Sound enabled' : 'Sound disabled',
        'info'
      );
    },

    refreshOrders: async function () {
      try {
        var response = await fetch("/kot/active");
        var data = await response.json();

        if (data.success) {
          this.activeOrders = data.orders;
          this.checkNewOrders();
        }
      } catch (error) {
        console.error("Error refreshing orders:", error);
      }
    },

    checkNewOrders: function () {
      var currentCount = this.activeOrders.length;

      if (currentCount > this.lastOrderCount && this.soundEnabled) {
        this.playNotificationSound();
      }

      this.lastOrderCount = currentCount;
    },

    // Time-based functions
    getOrderAge: function (order) {
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

    getUrgencyLevel: function (order) {
      if (!order.created_at) return 'normal';
      
      const now = new Date();
      const created = new Date(order.created_at);
      const diffMins = Math.floor((now - created) / 60000);
      
      if (diffMins > 20) return 'high';
      if (diffMins > 10) return 'medium';
      return 'normal';
    },

    getTimeStatus: function (order) {
      if (!order.created_at) return 'Unknown';
      
      const now = new Date();
      const created = new Date(order.created_at);
      const diffMins = Math.floor((now - created) / 60000);
      
      if (diffMins > 20) return 'DELAYED';
      if (diffMins > 10) return 'ATTENTION';
      return 'ON TIME';
    },

    getTimeIndicatorClass: function (order) {
      const urgency = this.getUrgencyLevel(order);
      return `time-${urgency === 'high' ? 'urgent' : urgency === 'medium' ? 'attention' : 'normal'}`;
    },

    getTimeBasedClass: function (order) {
      const urgency = this.getUrgencyLevel(order);
      return `time-${urgency === 'high' ? 'urgent' : urgency === 'medium' ? 'attention' : 'normal'} ${urgency}-urgency`;
    },

    formatTime: function (timeString) {
      if (!timeString) return '';
      const date = new Date(timeString);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    },

    hasSpecialInstructions: function (order) {
      return order.items && order.items.some(item => item.special_instructions);
    },

    getSpecialInstructions: function (order) {
      const instructions = order.items
        .filter(item => item.special_instructions)
        .map(item => item.special_instructions)
        .join('; ');
      return instructions || '';
    },

    getNextStatus: function (currentStatus) {
      const statusFlow = {
        'Pending': 'In Progress',
        'In Progress': 'Ready',
        'Ready': 'Completed',
        'Completed': 'Pending'
      };
      return statusFlow[currentStatus] || 'Pending';
    },

    getFilteredOrders: function (status) {
      if (this.filterStatus === 'all') {
        return this.activeOrders.filter(order => {
          if (status === 'new') return order.status === 'New';
          if (status === 'progress') return order.status === 'In Progress';
          if (status === 'ready') return order.status === 'Ready';
          return false;
        });
      } else {
        return this.activeOrders.filter(order => {
          if (this.filterStatus === 'new') return order.status === 'New';
          if (this.filterStatus === 'progress') return order.status === 'In Progress';
          if (this.filterStatus === 'ready') return order.status === 'Ready';
          return false;
        });
      }
    },

    getOrderCount: function (status) {
      return this.getFilteredOrders(status).length;
    },

    updateItemStatus: async function (itemId, status) {
      try {
        var response = await fetch("/kot/update_item_status", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            item_id: itemId,
            status: status,
          }),
        });

        var result = await response.json();

        if (result.success) {
          this.showNotification("Item status updated to " + status, "success");
          // Refresh orders to update UI
          setTimeout(
            function () {
              this.refreshOrders();
            }.bind(this),
            500
          );
        } else {
          this.showNotification(
            result.message || "Failed to update item",
            "error"
          );
        }
      } catch (error) {
        console.error("Error updating item status:", error);
        this.showNotification("Error updating item status", "error");
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
      const pendingOrders = this.activeOrders.filter(order => order.status === 'New');
      
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
      const visibleOrders = this.getFilteredOrders(this.filterStatus === 'all' ? 'new' : this.filterStatus);
      
      if (this.selectedOrders.size === visibleOrders.length) {
        // Deselect all
        this.selectedOrders.clear();
      } else {
        // Select all visible
        visibleOrders.forEach(order => this.selectedOrders.add(order.id));
      }
    },

    get allSelected() {
      const visibleOrders = this.getFilteredOrders(this.filterStatus === 'all' ? 'new' : this.filterStatus);
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

    playNotificationSound: function () {
      const audio = document.getElementById("notificationSound");
      if (audio && this.soundEnabled) {
        audio.play().catch(function (e) {
          console.log("Could not play sound:", e);
        });
      }
    },

    playUrgentSound: function () {
      const audio = document.getElementById("urgentSound");
      if (audio && this.soundEnabled) {
        audio.play().catch(e => console.log('Could not play urgent sound:', e));
      }
    },

    showNotification: function (message, type) {
      type = type || "info";
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

    setupKeyboardShortcuts: function () {
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
              this.filterStatus = 'all';
            }
            break;
          case '2':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.filterStatus = 'new';
            }
            break;
          case '3':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.filterStatus = 'progress';
            }
            break;
          case '4':
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault();
              this.filterStatus = 'ready';
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
  Alpine.data("kotDisplay", kotDisplay);
});