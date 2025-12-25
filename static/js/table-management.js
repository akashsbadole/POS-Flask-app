function tableManagement() {
  return {
    editingTable: false,
    formData: {
      id: null,
      table_number: "",
      capacity: "",
      location: "",
      description: "",
    },

    init: function () {
      // Initialize
    },

    getTableClass: function (status) {
      switch (status) {
        case "Available":
          return "border-success";
        case "Occupied":
          return "border-warning";
        case "Reserved":
          return "border-info";
        case "Maintenance":
          return "border-danger";
        default:
          return "border-secondary";
      }
    },

    showAddModal: function () {
      this.editingTable = false;
      this.resetForm();
      var modal = new bootstrap.Modal(document.getElementById("tableModal"));
      modal.show();
    },

    editTable: function (tableId) {
      // This would fetch table data and populate form
      this.editingTable = true;
      this.formData.id = tableId;
      this.formData.table_number = "Table " + tableId; // Placeholder
      this.formData.capacity = "4"; // Placeholder
      this.formData.location = "Main Hall"; // Placeholder
      this.formData.description = ""; // Placeholder

      var modal = new bootstrap.Modal(document.getElementById("tableModal"));
      modal.show();
    },

    resetForm: function () {
      this.formData = {
        id: null,
        table_number: "",
        capacity: "",
        location: "",
        description: "",
      };
    },

    saveTable: function () {
      if (!this.formData.table_number || !this.formData.capacity) {
        this.showNotification("Please fill in required fields", "error");
        return;
      }

      // This would submit the form data
      this.showNotification(
        this.editingTable
          ? "Table updated successfully"
          : "Table added successfully",
        "success"
      );
      var modal = bootstrap.Modal.getInstance(
        document.getElementById("tableModal")
      );
      modal.hide();
    },

    occupyTable: function (tableId) {
      // This would mark table as occupied
      this.showNotification("Table occupied successfully", "success");
      // In real app, this would redirect to order creation
      setTimeout(function () {
        window.location.href = "/orders/new?table=" + tableId;
      }, 1000);
    },

    releaseTable: function (tableId) {
      // This would mark table as available
      this.showNotification("Table released successfully", "success");
      setTimeout(function () {
        location.reload();
      }, 1000);
    },

    toggleTableStatus: function (tableId) {
      // This would toggle table active/inactive status
      this.showNotification("Table status updated", "success");
      setTimeout(function () {
        location.reload();
      }, 1000);
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
  Alpine.data("tableManagement", tableManagement);
});
