function kotDisplay() {
  return {
    activeOrders: window.activeOrders || [],
    filterStatus: "all",
    autoRefresh: true,
    soundEnabled: true,
    lastOrderCount: window.activeOrdersCount || 0,

    init: function () {
      // Start auto refresh if enabled
      if (this.autoRefresh) {
        this.startAutoRefresh();
      }
    },

    startAutoRefresh: function () {
      setInterval(
        function () {
          if (this.autoRefresh) {
            this.refreshOrders();
          }
        }.bind(this),
        10000
      ); // Refresh every 10 seconds
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

    toggleSound: function () {
      this.soundEnabled = !this.soundEnabled;
      this.showNotification(
        this.soundEnabled ? "Sound enabled" : "Sound disabled",
        "info"
      );
    },

    playNotificationSound: function () {
      var audio = document.getElementById("notificationSound");
      if (audio) {
        audio.play().catch(function (e) {
          console.log("Could not play sound:", e);
        });
      }
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
  Alpine.data("kotDisplay", kotDisplay);
});
