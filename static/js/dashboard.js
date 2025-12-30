function dashboardData() {
  return {
    stats: {
      today: {
        orders: 0,
        revenue: 0
      },
      week: {
        orders: 0,
        revenue: 0
      },
      month: {
        orders: 0,
        revenue: 0
      },
      orders: {
        new: 0,
        in_progress: 0,
        ready: 0,
        completed: 0,
        cancelled: 0
      },
      menu: {
        items: 0,
        categories: 0
      },
      tables: {
        total: 0,
        available: 0
      },
      low_stock_count: 0
    },

    refreshStats() {
      fetch("/dashboard/stats")
        .then((response) => response.json())
        .then((data) => {
          this.stats = data;
        })
        .catch((error) => {
          console.error("Error refreshing stats:", error);
        });
    },

    init() {
      // Auto-refresh stats every 30 seconds
      setInterval(() => {
        this.refreshStats();
      }, 30000);
      
      // Initial load
      this.refreshStats();
    },
  };
}

// Initialize Alpine.js when DOM is ready
document.addEventListener("alpine:init", () => {
  Alpine.data("dashboardData", dashboardData);
});
