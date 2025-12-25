// Restaurant POS JavaScript

// Global POS object for managing state and interactions
window.POS = {
  currentOrder: null,
  menuItems: [],
  categories: [],
  tables: [],

  // Initialize POS system
  init: function () {
    this.setupEventListeners();
    this.loadData();
    this.startRealTimeUpdates();
  },

  // Setup event listeners
  setupEventListeners: function () {
    // Search functionality
    const searchInput = document.getElementById("itemSearch");
    if (searchInput) {
      searchInput.addEventListener(
        "input",
        this.debounce((e) => {
          this.searchItems(e.target.value);
        }, 300)
      );
    }

    // Category filter
    const categorySelect = document.getElementById("categoryFilter");
    if (categorySelect) {
      categorySelect.addEventListener("change", (e) => {
        this.filterByCategory(e.target.value);
      });
    }

    // Keyboard shortcuts
    document.addEventListener(
      "keydown",
      this.handleKeyboardShortcuts.bind(this)
    );
  },

  // Load initial data
  loadData: async function () {
    try {
      await this.loadMenuItems();
      await this.loadCategories();
      await this.loadTables();
    } catch (error) {
      console.error("Error loading data:", error);
      this.showAlert("Error loading data", "error");
    }
  },

  // Load menu items
  loadMenuItems: async function () {
    const response = await fetch("/api/menu/items");
    if (response.ok) {
      this.menuItems = await response.json();
      this.renderMenuItems();
    }
  },

  // Load categories
  loadCategories: async function () {
    const response = await fetch("/api/menu/categories");
    if (response.ok) {
      this.categories = await response.json();
      this.renderCategories();
    }
  },

  // Load tables
  loadTables: async function () {
    const response = await fetch("/api/tables");
    if (response.ok) {
      this.tables = await response.json();
      this.renderTables();
    }
  },

  // Search menu items
  searchItems: function (query) {
    const filtered = this.menuItems.filter(
      (item) =>
        item.name.toLowerCase().includes(query.toLowerCase()) ||
        item.description?.toLowerCase().includes(query.toLowerCase())
    );
    this.renderMenuItems(filtered);
  },

  // Filter by category
  filterByCategory: function (categoryId) {
    const filtered = categoryId
      ? this.menuItems.filter((item) => item.category_id == categoryId)
      : this.menuItems;
    this.renderMenuItems(filtered);
  },

  // Render menu items
  renderMenuItems: function (items = this.menuItems) {
    const container = document.getElementById("menuItemsGrid");
    if (!container) return;

    container.innerHTML = items
      .map(
        (item) => `
            <div class="menu-item-card" onclick="POS.addToCart(${item.id})">
                <div class="menu-item-image">
                    ${
                      item.image_path
                        ? `<img src="${item.image_path}" alt="${item.name}">`
                        : '<div class="no-image"><i class="bi bi-image"></i></div>'
                    }
                </div>
                <div class="menu-item-details">
                    <h6 class="menu-item-name">${item.name}</h6>
                    <p class="menu-item-price">${this.formatCurrency(
                      item.price
                    )}</p>
                    ${
                      item.is_out_of_stock
                        ? '<span class="badge bg-danger">Out of Stock</span>'
                        : ""
                    }
                    ${
                      item.is_low_stock
                        ? '<span class="badge bg-warning">Low Stock</span>'
                        : ""
                    }
                </div>
            </div>
        `
      )
      .join("");
  },

  // Render categories
  renderCategories: function () {
    const select = document.getElementById("categoryFilter");
    if (!select) return;

    select.innerHTML =
      '<option value="">All Categories</option>' +
      this.categories
        .map(
          (cat) => `
                <option value="${cat.id}">${cat.name}</option>
            `
        )
        .join("");
  },

  // Render tables
  renderTables: function () {
    const select = document.getElementById("tableSelect");
    if (!select) return;

    select.innerHTML =
      '<option value="">Select Table</option>' +
      this.tables
        .filter((table) => table.is_available)
        .map(
          (table) => `
                <option value="${table.id}">${table.table_number} (Capacity: ${table.capacity})</option>
            `
        )
        .join("");
  },

  // Add item to cart
  addToCart: async function (itemId) {
    try {
      const item = this.menuItems.find((i) => i.id === itemId);
      if (!item || item.is_out_of_stock) {
        this.showAlert("Item is out of stock", "warning");
        return;
      }

      // Add to current order via API
      const response = await fetch("/api/orders/add_item", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          order_id: this.getCurrentOrderId(),
          menu_item_id: itemId,
          quantity: 1,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        this.updateCurrentOrder(result.order);
        this.renderCart();
        this.showAlert("Item added to cart", "success");
      } else {
        const error = await response.json();
        this.showAlert(error.message || "Error adding item", "error");
      }
    } catch (error) {
      console.error("Error adding item to cart:", error);
      this.showAlert("Error adding item", "error");
    }
  },

  // Update item quantity
  updateQuantity: async function (itemId, newQuantity) {
    if (newQuantity < 1) {
      this.removeFromCart(itemId);
      return;
    }

    try {
      const response = await fetch("/api/orders/update_quantity", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          order_id: this.getCurrentOrderId(),
          item_id: itemId,
          quantity: newQuantity,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        this.updateCurrentOrder(result.order);
        this.renderCart();
      } else {
        const error = await response.json();
        this.showAlert(error.message || "Error updating quantity", "error");
      }
    } catch (error) {
      console.error("Error updating quantity:", error);
      this.showAlert("Error updating quantity", "error");
    }
  },

  // Remove item from cart
  removeFromCart: async function (itemId) {
    if (!confirm("Remove this item from the order?")) return;

    try {
      const response = await fetch("/api/orders/remove_item", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          order_id: this.getCurrentOrderId(),
          item_id: itemId,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        this.updateCurrentOrder(result.order);
        this.renderCart();
        this.showAlert("Item removed from cart", "info");
      } else {
        const error = await response.json();
        this.showAlert(error.message || "Error removing item", "error");
      }
    } catch (error) {
      console.error("Error removing item:", error);
      this.showAlert("Error removing item", "error");
    }
  },

  // Render cart
  renderCart: function () {
    const cartContainer = document.getElementById("cartItems");
    if (!cartContainer) return;

    const items = this.currentOrder?.items || [];

    if (items.length === 0) {
      cartContainer.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-cart-x" style="font-size: 3rem;"></i>
                    <p class="mt-2">Cart is empty</p>
                </div>
            `;
    } else {
      cartContainer.innerHTML = `
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Price</th>
                            <th>Qty</th>
                            <th>Total</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${items
                          .map(
                            (item) => `
                            <tr>
                                <td>
                                    <div>
                                        <strong>${item.item_name}</strong>
                                        ${
                                          item.special_instructions
                                            ? `<br><small class="text-muted">${item.special_instructions}</small>`
                                            : ""
                                        }
                                    </div>
                                </td>
                                <td>${this.formatCurrency(item.price)}</td>
                                <td>
                                    <div class="quantity-control">
                                        <button onclick="POS.updateQuantity(${
                                          item.id
                                        }, ${item.quantity - 1})">-</button>
                                        <input type="text" value="${
                                          item.quantity
                                        }" readonly>
                                        <button onclick="POS.updateQuantity(${
                                          item.id
                                        }, ${item.quantity + 1})">+</button>
                                    </div>
                                </td>
                                <td>${this.formatCurrency(item.total)}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-danger" 
                                            onclick="POS.removeFromCart(${
                                              item.id
                                            })">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `
                          )
                          .join("")}
                    </tbody>
                </table>
            `;
    }

    this.renderTotals();
  },

  // Render totals
  renderTotals: function () {
    const order = this.currentOrder;
    if (!order) return;

    // Update cart info bar
    const cartInfo = document.getElementById("cartInfoBar");
    if (cartInfo) {
      cartInfo.innerHTML = `
                <span>Items: ${order.item_count || 0}</span>
                <span>Subtotal: ${this.formatCurrency(
                  order.subtotal || 0
                )}</span>
            `;
    }

    // Update GST breakdown
    const gstBreakdown = document.getElementById("gstBreakdown");
    if (gstBreakdown) {
      gstBreakdown.innerHTML = `
                <div class="gst-line">
                    <span>Subtotal:</span>
                    <span>${this.formatCurrency(order.subtotal || 0)}</span>
                </div>
                ${
                  order.discount_amount > 0
                    ? `
                    <div class="gst-line discount">
                        <span>Discount (${order.discount_type}):</span>
                        <span>-${this.formatCurrency(
                          order.discount_amount
                        )}</span>
                    </div>
                `
                    : ""
                }
                <div class="gst-line">
                    <span>CGST (2.5%):</span>
                    <span>${this.formatCurrency(order.cgst_amount || 0)}</span>
                </div>
                <div class="gst-line">
                    <span>SGST (2.5%):</span>
                    <span>${this.formatCurrency(order.sgst_amount || 0)}</span>
                </div>
                <div class="gst-line total">
                    <span>Total:</span>
                    <span>${this.formatCurrency(order.grand_total || 0)}</span>
                </div>
            `;
    }
  },

  // Update current order
  updateCurrentOrder: function (order) {
    this.currentOrder = order;

    // Update order details in form
    const orderNumber = document.getElementById("orderNumber");
    if (orderNumber && order.order_number) {
      orderNumber.value = order.order_number;
    }

    const customerName = document.getElementById("customerName");
    if (customerName && order.customer_name) {
      customerName.value = order.customer_name;
    }

    const customerMobile = document.getElementById("customerMobile");
    if (customerMobile && order.customer_mobile) {
      customerMobile.value = order.customer_mobile;
    }

    const tableSelect = document.getElementById("tableSelect");
    if (tableSelect && order.table_id) {
      tableSelect.value = order.table_id;
    }

    // Update status buttons
    this.updateStatusButtons(order.status);
  },

  // Update status buttons
  updateStatusButtons: function (status) {
    const statusButtons = document.querySelectorAll(".status-btn");
    statusButtons.forEach((btn) => {
      btn.classList.remove("active");
      if (btn.classList.contains(status.toLowerCase().replace(" ", "-"))) {
        btn.classList.add("active");
      }
    });
  },

  // Handle keyboard shortcuts
  handleKeyboardShortcuts: function (e) {
    // Ctrl/Cmd + N: New order
    if ((e.ctrlKey || e.metaKey) && e.key === "n") {
      e.preventDefault();
      if (typeof this.createNewOrder === "function") {
        this.createNewOrder();
      }
    }

    // Ctrl/Cmd + S: Save order
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      this.saveCurrentOrder();
    }

    // F1-F5: Quick status changes
    if (e.key >= "F1" && e.key <= "F5") {
      e.preventDefault();
      const statusMap = {
        F1: "new",
        F2: "progress",
        F3: "ready",
        F4: "completed",
        F5: "cancelled",
      };
      this.changeOrderStatus(statusMap[e.key]);
    }
  },

  // Change order status
  changeOrderStatus: async function (status) {
    try {
      const response = await fetch("/api/orders/update_status", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          order_id: this.getCurrentOrderId(),
          status: status,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        this.updateCurrentOrder(result.order);
        this.showAlert(`Order status changed to ${status}`, "success");
      } else {
        const error = await response.json();
        this.showAlert(error.message || "Error updating status", "error");
      }
    } catch (error) {
      console.error("Error updating status:", error);
      this.showAlert("Error updating status", "error");
    }
  },

  // Get current order ID
  getCurrentOrderId: function () {
    return this.currentOrder?.id || null;
  },

  // Format currency
  formatCurrency: function (amount) {
    // Use global formatCurrency function from utils.js
    return window.formatCurrency(amount);
  },

  // Show alert message
  showAlert: function (message, type = "info") {
    // Create alert element
    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

    // Add to flash messages container
    const flashContainer = document.querySelector(".flash-messages");
    if (flashContainer) {
      flashContainer.appendChild(alert);

      // Auto remove after 5 seconds
      setTimeout(() => {
        if (alert.parentNode) {
          alert.remove();
        }
      }, 5000);

      // Initialize Bootstrap alert
      const bsAlert = new bootstrap.Alert(alert);
    }
  },

  // Debounce function
  debounce: function (func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Start real-time updates
  startRealTimeUpdates: function () {
    // Update KOT every 30 seconds
    setInterval(() => {
      this.updateKOT();
    }, 30000);

    // Update stock levels every minute
    setInterval(() => {
      this.updateStockLevels();
    }, 60000);
  },

  // Update KOT display
  updateKOT: async function () {
    try {
      const response = await fetch("/api/kot/active");
      if (response.ok) {
        const kotData = await response.json();
        this.renderKOT(kotData);
      }
    } catch (error) {
      console.error("Error updating KOT:", error);
    }
  },

  // Render KOT
  renderKOT: function (kotData) {
    const kotContainer = document.getElementById("kotDisplay");
    if (!kotContainer) return;

    if (kotData.length === 0) {
      kotContainer.innerHTML = '<p class="text-muted">No active orders</p>';
      return;
    }

    kotContainer.innerHTML = kotData
      .map(
        (order) => `
            <div class="kot-order-item">
                <div class="kot-header">
                    <strong>${order.order_number}</strong>
                    <span class="badge bg-${this.getStatusColor(
                      order.status
                    )}">${order.status}</span>
                </div>
                <div class="kot-items">
                    ${order.items
                      .map(
                        (item) => `
                        <div class="kot-item">
                            <span>${item.item_name} x${item.quantity}</span>
                            <span class="badge bg-${this.getItemStatusColor(
                              item.status
                            )}">${item.status}</span>
                        </div>
                    `
                      )
                      .join("")}
                </div>
                <div class="kot-footer">
                    <small>Table: ${order.table_number || "N/A"}</small>
                    <small>${new Date(
                      order.created_at
                    ).toLocaleTimeString()}</small>
                </div>
            </div>
        `
      )
      .join("");
  },

  // Get status color
  getStatusColor: function (status) {
    const colors = {
      new: "secondary",
      progress: "warning",
      ready: "success",
      completed: "primary",
      cancelled: "danger",
    };
    return colors[status] || "secondary";
  },

  // Get item status color
  getItemStatusColor: function (status) {
    const colors = {
      pending: "warning",
      progress: "info",
      ready: "success",
      completed: "primary",
      cancelled: "danger",
    };
    return colors[status] || "secondary";
  },

  // Update stock levels
  updateStockLevels: async function () {
    try {
      const response = await fetch("/api/inventory/low_stock");
      if (response.ok) {
        const lowStock = await response.json();
        if (lowStock.length > 0) {
          this.showAlert(
            `${lowStock.length} items are running low on stock`,
            "warning"
          );
        }
      }
    } catch (error) {
      console.error("Error checking stock levels:", error);
    }
  },
};

// Initialize POS when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  if (typeof window.POS !== "undefined") {
    window.POS.init();
  }
});

// Export for global access
window.POS = POS;
