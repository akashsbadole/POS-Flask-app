function inventoryManagement() {
  return {
    searchQuery: "",
    selectedCategory: "",
    stockFilter: "all",
    editingItem: false,
    stockData: {
      id: null,
      item_name: "",
      current_stock: 0,
      update_type: "add",
      quantity: 0,
      reason: "",
    },

    init: function () {
      // Initialize
    },

    filterItems: function () {
      var items = document.querySelectorAll(".inventory-item");
      var query = this.searchQuery.toLowerCase();
      var category = this.selectedCategory;
      var stock = this.stockFilter;

      items.forEach(
        function (item) {
          var itemCategory = item.dataset.category;
          var itemName = item.dataset.name;
          var itemStock = item.dataset.stock;

          var categoryMatch = !category || itemCategory === category;
          var nameMatch = !query || itemName.includes(query);
          var stockMatch = stock === "all";

          if (stock === "in_stock") {
            stockMatch = itemStock === "in_stock";
          } else if (stock === "low_stock") {
            stockMatch = itemStock === "low_stock";
          } else if (stock === "out_of_stock") {
            stockMatch = itemStock === "out_of_stock";
          }

          item.style.display =
            categoryMatch && nameMatch && stockMatch ? "" : "none";
        }.bind(this)
      );
    },

    updateStock: function (itemId) {
      // This would fetch item data and populate form
      this.stockData.id = itemId;
      this.stockData.item_name = "Item Name " + itemId; // Placeholder
      this.stockData.current_stock = 50; // Placeholder
      this.stockData.update_type = "add";
      this.stockData.quantity = 0;
      this.stockData.reason = "";

      var modal = new bootstrap.Modal(document.getElementById("stockModal"));
      modal.show();
    },

    editItem: function (itemId) {
      // This would open edit modal
      this.showNotification("Edit functionality coming soon", "info");
    },

    saveStockUpdate: function () {
      if (!this.stockData.quantity || this.stockData.quantity <= 0) {
        this.showNotification("Please enter a valid quantity", "error");
        return;
      }

      // This would submit the stock update
      this.showNotification("Stock updated successfully", "success");
      var modal = bootstrap.Modal.getInstance(
        document.getElementById("stockModal")
      );
      modal.hide();
    },

    exportData: function () {
      // Export functionality
      this.showNotification("Export feature coming soon", "info");
    },

    refreshData: function () {
      // Refresh data
      this.showNotification("Data refreshed", "success");
      window.location.reload();
    },

    showNotification: function (message, type) {
      type = type || "info";
      var toast = document.createElement("div");
      toast.className =
        "alert alert-" + type + " position-fixed top-0 end-0 m-3";
      toast.style.zIndex = "9999";
      toast.textContent = message;

      document.body.appendChild(toast);

      setTimeout(function () {
        toast.remove();
      }, 3000);
    },
  };
}

// Initialize Alpine.js when DOM is ready
document.addEventListener("alpine:init", function () {
  Alpine.data("inventoryManagement", inventoryManagement);
});
