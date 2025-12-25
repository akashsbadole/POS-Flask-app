function orderScreen() {
  return {
    orders: [
      {
        id: null,
        order_type: "Dine-in",
        table_id: null,
        customer_name: "",
        customer_mobile: "",
        items: [],
        subtotal: 0,
        cgst: 0,
        sgst: 0,
        discount: 0,
        total: 0,
      },
    ],
    currentOrderIndex: 0,
    selectedCategory: null,
    searchQuery: "",
    selectedMenuItem: null,
    itemQuantity: 1,
    itemInstructions: "",
    menuItems: window.menuItems || [],
    tables: window.tables || [],

    get currentOrder() {
      return this.orders[this.currentOrderIndex];
    },

    init() {
      // Initialize with empty order
      this.calculateTotals();
    },

    // Order management
    addNewOrder() {
      const newOrder = {
        id: null,
        order_type: "Dine-in",
        table_id: null,
        customer_name: "",
        customer_mobile: "",
        items: [],
        subtotal: 0,
        cgst: 0,
        sgst: 0,
        discount: 0,
        total: 0,
      };
      this.orders.push(newOrder);
      this.currentOrderIndex = this.orders.length - 1;
    },

    removeOrder(index) {
      if (this.orders.length > 1) {
        this.orders.splice(index, 1);
        if (this.currentOrderIndex >= this.orders.length) {
          this.currentOrderIndex = this.orders.length - 1;
        }
      }
    },

    // Menu item management
    addToOrder(itemId) {
      const menuItem = this.menuItems.find((item) => item.id === itemId);
      if (!menuItem || menuItem.is_out_of_stock) {
        this.showNotification("Item not available", "error");
        return;
      }

      this.selectedMenuItem = menuItem;
      this.itemQuantity = 1;
      this.itemInstructions = "";

      // Show modal for quantity and instructions
      const modal = new bootstrap.Modal(document.getElementById("itemModal"));
      modal.show();
    },

    confirmAddItem() {
      const menuItem = this.selectedMenuItem;
      if (!menuItem) return;

      // Check if item already exists in order
      const existingItem = this.currentOrder.items.find(
        (item) => item.menu_item_id === menuItem.id
      );

      if (existingItem) {
        existingItem.quantity += this.itemQuantity;
      } else {
        const orderItem = {
          id: Date.now(), // Temporary ID
          menu_item_id: menuItem.id,
          name: menuItem.name,
          price: menuItem.price,
          quantity: this.itemQuantity,
          special_instructions: this.itemInstructions,
        };
        this.currentOrder.items.push(orderItem);
      }

      this.calculateTotals();

      // Close modal
      const modal = bootstrap.Modal.getInstance(
        document.getElementById("itemModal")
      );
      modal.hide();

      this.showNotification("Item added to order", "success");
    },

    updateQuantity(itemId, newQuantity) {
      if (newQuantity <= 0) {
        this.removeItem(itemId);
        return;
      }

      const item = this.currentOrder.items.find((item) => item.id === itemId);
      if (item) {
        item.quantity = newQuantity;
        this.calculateTotals();
      }
    },

    removeItem(itemId) {
      const index = this.currentOrder.items.findIndex(
        (item) => item.id === itemId
      );
      if (index !== -1) {
        this.currentOrder.items.splice(index, 1);
        this.calculateTotals();
      }
    },

    // Calculations
    calculateTotals() {
      const order = this.currentOrder;

      // Calculate subtotal
      order.subtotal = order.items.reduce((sum, item) => {
        return sum + item.price * item.quantity;
      }, 0);

      // Calculate GST (2.5% each for CGST and SGST)
      order.cgst = order.subtotal * 0.025;
      order.sgst = order.subtotal * 0.025;

      // Calculate total
      order.total = order.subtotal + order.cgst + order.sgst - order.discount;
    },

    // UI helpers
    filterMenuItems() {
      const items = document.querySelectorAll(".menu-item");
      const query = this.searchQuery.toLowerCase();

      items.forEach((item) => {
        const category = item.dataset.category;
        const name = item.dataset.name;
        const categoryMatch =
          this.selectedCategory === null ||
          category === this.selectedCategory.toString();
        const nameMatch = !query || name.includes(query);

        item.style.display = categoryMatch && nameMatch ? "" : "none";
      });
    },

    getTableNumber(tableId) {
      if (!tableId) return "N/A";
      const table = this.tables.find((t) => t.id === tableId);
      return table ? table.table_number : "N/A";
    },

    // Order operations
    async saveOrder() {
      if (this.currentOrder.items.length === 0) {
        this.showNotification("Please add items to the order", "error");
        return false;
      }

      try {
        const orderData = {
          order_id: this.currentOrder.id,
          customer_name: this.currentOrder.customer_name,
          customer_mobile: this.currentOrder.customer_mobile,
          order_type: this.currentOrder.order_type,
          table_id: this.currentOrder.table_id,
          discount_amount: this.currentOrder.discount,
          items: this.currentOrder.items.map((item) => ({
            menu_item_id: item.menu_item_id,
            quantity: item.quantity,
            special_instructions: item.special_instructions,
          })),
        };

        const response = await fetch("/orders/save", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(orderData),
        });

        const result = await response.json();

        if (result.success) {
          this.currentOrder.id = result.order_id;
          this.showNotification("Order saved successfully", "success");
          return true;
        } else {
          this.showNotification(
            result.message || "Failed to save order",
            "error"
          );
          return false;
        }
      } catch (error) {
        console.error("Error saving order:", error);
        this.showNotification("Error saving order", "error");
        return false;
      }
    },

    async proceedToPayment() {
      if (this.currentOrder.items.length === 0) {
        this.showNotification("Please add items to the order", "error");
        return;
      }

      try {
        // First save the order
        const saveResult = await this.saveOrder();

        if (saveResult) {
          // Redirect to payment page
          window.location.href = `/orders/payment/${this.currentOrder.id}`;
        }
      } catch (error) {
        console.error("Error proceeding to payment:", error);
        this.showNotification("Failed to proceed to payment", "error");
      }
    },

    // Notifications
    showNotification(message, type = "info") {
      // Create toast notification
      const toast = document.createElement("div");
      toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
      toast.style.zIndex = "9999";
      toast.textContent = message;

      document.body.appendChild(toast);

      setTimeout(() => {
        toast.remove();
      }, 3000);
    },

    // Watch for changes
    watch: {
      selectedCategory() {
        this.filterMenuItems();
      },
    },
  };
}

// Initialize Alpine.js when DOM is ready
document.addEventListener("alpine:init", () => {
  Alpine.data("orderScreen", orderScreen);
});
