function dashboardData() {
  return {
    stats: window.dashboardStats || {},

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
    },
  };
}

// Initialize Alpine.js when DOM is ready
document.addEventListener("alpine:init", () => {
  Alpine.data("dashboardData", dashboardData);
});
