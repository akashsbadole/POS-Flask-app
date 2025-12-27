/**
 * Inventory Analytics Dashboard JavaScript
 * Advanced inventory management with real-time tracking and alerts
 */

function inventoryAnalyticsDashboard() {
  return {
    // Data properties
    inventoryData: {
      totalItems: 0,
      lowStockCount: 0,
      outOfStockCount: 0,
      totalValue: 0,
      healthPercentage: 0,
      valueGrowth: 0
    },
    lowStockItems: [],
    recentMovements: [],
    alerts: [],
    analysisData: {
      abc: {
        categoryA: { count: 0 },
        categoryB: { count: 0 },
        categoryC: { count: 0 }
      },
      fastMoving: [],
      slowMoving: [],
      valueByCategory: []
    },
    
    // UI state
    isLoading: false,
    movementFilter: 'all',
    
    // Configuration
    charts: {
      stockView: 'current',
      stockChart: null,
      distributionChart: null,
      categoryChart: null,
      turnoverChart: null
    },
    
    chartInstances: {},
    
    init() {
      this.loadInventoryData();
      this.initializeCharts();
      this.initializeTables();
      this.setupEventListeners();
      this.loadAlerts();
      
      // Auto-refresh every 30 seconds
      setInterval(() => {
        this.refreshData();
      }, 30000);
    },
    
    async loadInventoryData() {
      this.isLoading = true;
      
      try {
        const response = await fetch('/dynamic-reports/api/inventory/analytics');
        const result = await response.json();
        
        if (result.success) {
          this.inventoryData = result.data;
          this.lowStockItems = result.data.low_stock || [];
          this.alerts = result.alerts || [];
          this.updateCharts();
          this.updateTables();
          this.updateAnalysis();
        } else {
          this.showNotification('Failed to load inventory data', 'error');
        }
      } catch (error) {
        console.error('Error loading inventory data:', error);
        this.showNotification('Error loading inventory data', 'error');
      } finally {
        this.isLoading = false;
      }
    },
    
    initializeCharts() {
      this.initializeStockChart();
      this.initializeDistributionChart();
      this.initializeCategoryChart();
      this.initializeTurnoverChart();
    },
    
    initializeStockChart() {
      const ctx = document.getElementById('stockChart').getContext('2d');
      
      this.chartInstances.stock = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Current Stock',
              data: [],
              backgroundColor: 'rgba(237, 137, 54, 0.6)',
              borderColor: '#ED8936',
              borderWidth: 1
            },
            {
              label: 'Min Stock Level',
              data: [],
              backgroundColor: 'rgba(245, 101, 101, 0.6)',
              borderColor: '#F56565',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top'
            },
            tooltip: {
              mode: 'index',
              intersect: false
            }
          },
          scales: {
            x: {
              display: true,
              title: {
                display: true,
                text: 'Items'
              }
            },
            y: {
              display: true,
              title: {
                display: true,
                text: 'Quantity'
              },
              beginAtZero: true
            }
          }
        }
      });
    },
    
    initializeDistributionChart() {
      const ctx = document.getElementById('distributionChart').getContext('2d');
      
      this.chartInstances.distribution = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Healthy Stock', 'Low Stock', 'Out of Stock'],
          datasets: [{
            data: [],
            backgroundColor: [
              '#48BB78',
              '#ED8936',
              '#F56565'
            ],
            borderWidth: 2,
            borderColor: '#fff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding: 20,
                usePointStyle: true
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const label = context.label || '';
                  const value = context.parsed;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = ((value / total) * 100).toFixed(1);
                  return `${label}: ${value} items (${percentage}%)`;
                }
              }
            }
          }
        }
      });
    },
    
    initializeCategoryChart() {
      const ctx = document.getElementById('categoryChart').getContext('2d');
      
      this.chartInstances.category = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: [],
          datasets: [{
            label: 'Stock Levels',
            data: [],
            backgroundColor: 'rgba(102, 126, 234, 0.2)',
            borderColor: '#667EEA',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            }
          },
          scales: {
            r: {
              beginAtZero: true,
              max: 100
            }
          }
        }
      });
    },
    
    initializeTurnoverChart() {
      const ctx = document.getElementById('turnoverChart').getContext('2d');
      
      this.chartInstances.turnover = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: 'Turnover Rate',
            data: [],
            borderColor: '#38B2AC',
            backgroundColor: 'rgba(56, 178, 172, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            }
          },
          scales: {
            x: {
              display: true,
              title: {
                display: true,
                text: 'Time Period'
              }
            },
            y: {
              display: true,
              title: {
                display: true,
                text: 'Turnover Rate'
              },
              beginAtZero: true
            }
          }
        }
      });
    },
    
    updateCharts() {
      this.updateStockChart();
      this.updateDistributionChart();
      this.updateCategoryChart();
      this.updateTurnoverChart();
    },
    
    updateStockChart() {
      if (!this.chartInstances.stock) return;
      
      // Simulate stock data for low stock items
      const labels = this.lowStockItems.slice(0, 10).map(item => item.name);
      const currentStock = this.lowStockItems.slice(0, 10).map(item => item.currentStock);
      const minStock = this.lowStockItems.slice(0, 10).map(item => item.minStock);
      
      this.chartInstances.stock.data.labels = labels;
      this.chartInstances.stock.data.datasets[0].data = currentStock;
      this.chartInstances.stock.data.datasets[1].data = minStock;
      this.chartInstances.stock.update('active');
    },
    
    updateDistributionChart() {
      if (!this.chartInstances.distribution) return;
      
      const healthyCount = this.inventoryData.totalItems - this.inventoryData.lowStockCount - this.inventoryData.outOfStockCount;
      
      this.chartInstances.distribution.data.datasets[0].data = [
        healthyCount,
        this.inventoryData.lowStockCount,
        this.inventoryData.outOfStockCount
      ];
      this.chartInstances.distribution.update('active');
    },
    
    updateCategoryChart() {
      if (!this.chartInstances.category) return;
      
      // Simulate category performance data
      const categories = ['Appetizers', 'Mains', 'Desserts', 'Beverages', 'Indian', 'Breads'];
      const performance = [85, 92, 78, 88, 95, 82];
      
      this.chartInstances.category.data.labels = categories;
      this.chartInstances.category.data.datasets[0].data = performance;
      this.chartInstances.category.update('active');
    },
    
    updateTurnoverChart() {
      if (!this.chartInstances.turnover) return;
      
      // Simulate turnover rate data
      const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
      const rates = [2.1, 2.3, 2.8, 2.5, 2.9, 3.1];
      
      this.chartInstances.turnover.data.labels = labels;
      this.chartInstances.turnover.data.datasets[0].data = rates;
      this.chartInstances.turnover.update('active');
    },
    
    initializeTables() {
      this.updateMovements();
    },
    
    updateMovements() {
      // Simulate inventory movements
      const allMovements = [
        {
          id: 1,
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          itemName: 'Butter Chicken',
          type: 'out',
          quantity: -5,
          reference: 'Order #1234',
          user: 'Chef John'
        },
        {
          id: 2,
          timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          itemName: 'Rice',
          type: 'in',
          quantity: 50,
          reference: 'Purchase Order #567',
          user: 'Manager'
        },
        {
          id: 3,
          timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
          itemName: 'Dal',
          type: 'adjustment',
          quantity: 2,
          reference: 'Stock Count',
          user: 'Inventory Clerk'
        }
      ];
      
      if (this.movementFilter === 'all') {
        this.recentMovements = allMovements;
      } else {
        this.recentMovements = allMovements.filter(m => m.type === this.movementFilter);
      }
      
      // Reinitialize DataTable
      setTimeout(() => {
        if ($.fn.DataTable.isDataTable('#movementsTable')) {
          $('#movementsTable').DataTable().destroy();
        }
        
        $('#movementsTable').DataTable({
          paging: false,
          searching: false,
          info: false,
          order: [[0, 'desc']],
          columnDefs: [
            { orderable: false, targets: [2, 3, 4, 5] }
          ]
        });
      }, 100);
    },
    
    updateAnalysis() {
      // Simulate ABC analysis
      this.analysisData.abc = {
        categoryA: { count: 12 },
        categoryB: { count: 28 },
        categoryC: { count: 45 }
      };
      
      // Simulate fast moving items
      this.analysisData.fastMoving = [
        { id: 1, name: 'Naan Bread', turnoverRate: 15.2 },
        { id: 2, name: 'Butter Chicken', turnoverRate: 12.8 },
        { id: 3, name: 'Biryani', turnoverRate: 11.5 }
      ];
      
      // Simulate slow moving items
      this.analysisData.slowMoving = [
        { id: 1, name: 'Rare Spice Mix', daysSinceMovement: 45 },
        { id: 2, name: 'Exotic Dessert', daysSinceMovement: 38 },
        { id: 3, name: 'Special Sauce', daysSinceMovement: 32 }
      ];
      
      // Simulate value distribution
      this.analysisData.valueByCategory = [
        { name: 'Indian Curries', value: 45000, percentage: 35 },
        { name: 'Rice Dishes', value: 32000, percentage: 25 },
        { name: 'Beverages', value: 28000, percentage: 22 },
        { name: 'Breads', value: 23000, percentage: 18 }
      ];
    },
    
    loadAlerts() {
      this.alerts = [
        {
          id: 1,
          type: 'warning',
          title: 'Low Stock Alert',
          message: '5 items are running low on stock',
          timestamp: new Date().toLocaleString()
        },
        {
          id: 2,
          type: 'error',
          title: 'Out of Stock',
          message: '2 items are completely out of stock',
          timestamp: new Date().toLocaleString()
        }
      ];
    },
    
    setupEventListeners() {
      // Listen for window resize
      window.addEventListener('resize', () => {
        Object.values(this.chartInstances).forEach(chart => {
          if (chart) chart.resize();
        });
      });
    },
    
    // UI Actions
    async refreshData() {
      await this.loadInventoryData();
      this.showNotification('Inventory data refreshed', 'success');
    },
    
    triggerRestockAlert() {
      this.showNotification('Restock alert sent to suppliers', 'info');
    },
    
    refreshLowStock() {
      this.updateTables();
      this.showNotification('Low stock items refreshed', 'success');
    },
    
    generatePurchaseOrder() {
      const lowStockItems = this.lowStockItems.filter(item => item.currentStock <= item.minStock);
      if (lowStockItems.length === 0) {
        this.showNotification('No items need reordering', 'info');
        return;
      }
      
      this.showNotification(`Purchase order generated for ${lowStockItems.length} items`, 'success');
    },
    
    restockItem(itemId) {
      const item = this.lowStockItems.find(i => i.id === itemId);
      if (item) {
        item.currentStock = item.minStock * 2; // Simulate restocking
        this.updateCharts();
        this.showNotification(`${item.name} restocked successfully`, 'success');
      }
    },
    
    editItem(itemId) {
      this.showNotification('Edit functionality coming soon', 'info');
    },
    
    updateReorderQty(itemId, quantity) {
      const item = this.lowStockItems.find(i => i.id === itemId);
      if (item) {
        item.reorderQuantity = parseInt(quantity) || 0;
        this.showNotification('Reorder quantity updated', 'success');
      }
    },
    
    dismissAlert(alertId) {
      this.alerts = this.alerts.filter(alert => alert.id !== alertId);
    },
    
    updateStockChart() {
      if (this.charts.stockView === 'current') {
        this.updateCurrentStockChart();
      } else if (this.charts.stockView === 'trend') {
        this.updateStockTrendChart();
      } else {
        this.updateCategoryStockChart();
      }
    },
    
    updateCurrentStockChart() {
      this.chartInstances.stock.config.type = 'bar';
      this.updateStockChart(); // Recursive call with current logic
    },
    
    updateStockTrendChart() {
      this.chartInstances.stock.config.type = 'line';
      // Implementation for trend view
    },
    
    updateCategoryStockChart() {
      this.chartInstances.stock.config.type = 'bar';
      // Implementation for category view
    },
    
    // Export functions
    async exportData(format) {
      try {
        const params = new URLSearchParams({
          type: 'inventory',
          format: format
        });
        
        const response = await fetch(`/dynamic-reports/api/export?${params}`);
        
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `inventory_report_${new Date().toISOString().split('T')[0]}.${format}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          
          this.showNotification(`Inventory data exported as ${format.toUpperCase()}`, 'success');
        } else {
          throw new Error('Export failed');
        }
      } catch (error) {
        console.error('Export error:', error);
        this.showNotification('Failed to export data', 'error');
      }
    },
    
    exportChart(chartId) {
      const chartMap = {
        'stockChart': 'stock',
        'distributionChart': 'distribution',
        'categoryChart': 'category',
        'turnoverChart': 'turnover'
      };
      
      const chartKey = chartMap[chartId];
      if (this.chartInstances[chartKey]) {
        const chart = this.chartInstances[chartKey];
        const url = chart.toBase64Image();
        const a = document.createElement('a');
        a.href = url;
        a.download = `${chartId}_${new Date().toISOString().split('T')[0]}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        this.showNotification('Chart exported', 'success');
      }
    },
    
    // Utility functions
    formatCurrency(amount) {
      return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
      }).format(amount || 0);
    },
    
    formatDateTime(timestamp) {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    },
    
    getAlertIcon(type) {
      switch (type) {
        case 'warning': return 'bi bi-exclamation-triangle text-warning';
        case 'error': return 'bi bi-x-circle text-danger';
        case 'info': return 'bi bi-info-circle text-info';
        default: return 'bi bi-bell text-primary';
      }
    },
    
    getStockClass(current, min) {
      if (current <= 0) return 'text-danger';
      if (current <= min) return 'text-warning';
      return 'text-success';
    },
    
    getStatusClass(status) {
      switch (status.toLowerCase()) {
        case 'low': return 'status-warning';
        case 'out': return 'status-danger';
        case 'healthy': return 'status-success';
        default: return 'status-neutral';
      }
    },
    
    showNotification(message, type = 'info') {
      const notification = document.createElement('div');
      notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
      notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
      notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;
      
      document.body.appendChild(notification);
      
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 5000);
    }
  };
}

// Initialize Alpine.js when DOM is ready
document.addEventListener('alpine:init', () => {
  Alpine.data('inventoryAnalyticsDashboard', inventoryAnalyticsDashboard);
});