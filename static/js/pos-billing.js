function posBillingManager() {
  return {
    // Data
    activeOrders: {},
    currentOrderId: null,
    categories: [],
    menuItems: [],
    tables: [],
    
    // Filters
    searchQuery: '',
    selectedCategory: null,
    
    // Settings
    nextOrderId: 1,
    
    init: function() {
      // Load data from global variables
      if (typeof window.posData !== 'undefined') {
        this.categories = window.posData.categories || [];
        this.menuItems = window.posData.menuItems || [];
        this.tables = window.posData.tables || [];
      }
      
      // Create first order
      this.addNewOrder();
    },
    
    // Computed Properties
    get currentOrder() {
      return this.activeOrders[this.currentOrderId];
    },
    
    get availableTables() {
      return this.tables.filter(table => table.is_available);
    },
    
    get filteredMenuItems() {
      let items = this.menuItems;
      
      // Filter by category
      if (this.selectedCategory !== null) {
        items = items.filter(item => item.category_id === this.selectedCategory);
      }
      
      // Filter by search query
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        items = items.filter(item => 
          item.name.toLowerCase().includes(query) ||
          (item.description && item.description.toLowerCase().includes(query))
        );
      }
      
      return items;
    },
    
    // Order Management
    addNewOrder: function() {
      const orderId = 'order_' + this.nextOrderId++;
      this.activeOrders[orderId] = {
        id: orderId,
        orderNumber: this.generateOrderNumber(),
        orderType: 'Dine-in',
        tableId: null,
        customerName: '',
        customerMobile: '',
        specialInstructions: '',
        items: [],
        subtotal: 0,
        cgst: 0,
        sgst: 0,
        discount: 0,
        grandTotal: 0
      };
      
      this.currentOrderId = orderId;
    },
    
    switchToOrder: function(orderId) {
      this.currentOrderId = orderId;
    },
    
    closeOrder: function(orderId) {
      if (this.currentOrderId === orderId) {
        // Switch to another order if available
        const remainingOrders = Object.keys(this.activeOrders);
        if (remainingOrders.length > 1) {
          const otherOrderId = remainingOrders.find(id => id !== orderId);
          if (otherOrderId) {
            this.currentOrderId = otherOrderId;
          }
        } else {
          // Create new order if this was only one
          this.addNewOrder();
        }
      }
      
      // Remove order
      delete this.activeOrders[orderId];
    },
    
    generateOrderNumber: function() {
      // Use global generateOrderNumber function from utils.js
      return window.generateOrderNumber();
    },
    
    // Menu Management
    selectCategory: function(categoryId) {
      this.selectedCategory = categoryId;
    },
    
    filterMenuItems: function() {
      // Filter is handled by computed property
    },
    
    addToCurrentOrder: function(menuItem) {
      if (!this.currentOrder) return;
      
      const currentOrder = this.currentOrder;
      
      // Check if item already exists
      const existingItemIndex = currentOrder.items.findIndex(item => item.menuItemId === menuItem.id);
      
      if (existingItemIndex !== -1) {
        // Update quantity
        currentOrder.items[existingItemIndex].quantity += 1;
      } else {
        // Add new item
        currentOrder.items.push({
          menuItemId: menuItem.id,
          name: menuItem.name,
          price: menuItem.price,
          quantity: 1,
          specialInstructions: ''
        });
      }
      
      this.recalculateTotals();
      this.showNotification(menuItem.name + ' added to order', 'success');
    },
    
    isInCurrentOrder: function(menuItemId) {
      if (!this.currentOrder) return false;
      return this.currentOrder.items.some(item => item.menuItemId === menuItemId);
    },
    
    removeFromOrder: function(itemIndex) {
      if (!this.currentOrder) return;
      
      const currentOrder = this.currentOrder;
      const item = currentOrder.items[itemIndex];
      
      currentOrder.items.splice(itemIndex, 1);
      this.recalculateTotals();
      this.showNotification(item.name + ' removed from order', 'info');
    },
    
    updateItemQuantity: function(itemIndex, newQuantity) {
      if (!this.currentOrder || newQuantity < 1) return;
      
      const currentOrder = this.currentOrder;
      currentOrder.items[itemIndex].quantity = parseInt(newQuantity);
      this.recalculateTotals();
    },
    
    recalculateTotals: function() {
      if (!this.currentOrder) return;
      
      const currentOrder = this.currentOrder;
      let subtotal = 0;
      
      currentOrder.items.forEach(item => {
        subtotal += item.price * item.quantity;
      });
      
      currentOrder.subtotal = subtotal;
      currentOrder.cgst = subtotal * 0.025; // 2.5%
      currentOrder.sgst = subtotal * 0.025; // 2.5%
      currentOrder.grandTotal = subtotal + currentOrder.cgst + currentOrder.sgst - currentOrder.discount;
    },
    
    // Order Actions
    saveOrder: function() {
      if (!this.currentOrder || this.currentOrder.items.length === 0) {
        this.showNotification('No items to save', 'error');
        return;
      }
      
      // Save order to server
      fetch('/orders/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          order_type: this.currentOrder.orderType,
          table_id: this.currentOrder.tableId,
          customer_name: this.currentOrder.customerName,
          customer_mobile: this.currentOrder.customerMobile,
          special_instructions: this.currentOrder.specialInstructions,
          items: this.currentOrder.items.map(item => ({
            menu_item_id: item.menuItemId,
            quantity: item.quantity,
            special_instructions: item.specialInstructions
          })),
          discount_amount: this.currentOrder.discount
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          this.showNotification('Order saved successfully', 'success');
          this.updateOrderInTab(data.order_id, data.order_number);
        } else {
          this.showNotification(data.message || 'Failed to save order', 'error');
        }
      })
      .catch(error => {
        console.error('Error saving order:', error);
        this.showNotification('Error saving order', 'error');
      });
    },
    
    updateOrderInTab: function(orderId, orderNumber) {
      const order = this.activeOrders[this.currentOrderId];
      if (order) {
        order.id = orderId;
        order.orderNumber = orderNumber;
        order.saved = true;
      }
    },
    
    printKOT: function() {
      if (!this.currentOrder || this.currentOrder.items.length === 0) {
        this.showNotification('No items to print', 'error');
        return;
      }
      
      // Print KOT
      const printWindow = window.open('/kot/print/' + this.currentOrder.id, '_blank');
      if (printWindow) {
        printWindow.onload = function() {
          printWindow.print();
        };
      }
    },
    
    proceedToPayment: function() {
      if (!this.currentOrder || this.currentOrder.items.length === 0) {
        this.showNotification('No items to process', 'error');
        return;
      }
      
      // Navigate to payment page
      window.location.href = '/orders/payment/' + this.currentOrderId;
    },
    
    clearOrder: function() {
      if (!this.currentOrder) return;
      
      if (confirm('Are you sure you want to clear this order?')) {
        const currentOrder = this.currentOrder;
        currentOrder.items = [];
        currentOrder.subtotal = 0;
        currentOrder.cgst = 0;
        currentOrder.sgst = 0;
        currentOrder.grandTotal = 0;
        currentOrder.customerName = '';
        currentOrder.customerMobile = '';
        currentOrder.specialInstructions = '';
        
        this.showNotification('Order cleared', 'info');
      }
    },
    
    // Notifications
    showNotification: function(message, type) {
      // Use global showNotification function from utils.js
      return window.showNotification(message, type);
    }
  };
}