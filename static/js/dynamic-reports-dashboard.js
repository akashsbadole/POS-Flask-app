/**
 * Dynamic Reports Dashboard JavaScript
 * Handles real-time dashboard functionality with Chart.js integration
 */

function dynamicReportsDashboard() {
  return {
    // Data properties
    dashboardData: {},
    realtimeData: {
      connected: false,
      lastUpdated: null,
      todaySales: 0,
      activeOrders: 0,
      lowStockItems: 0
    },
    topSellingItems: [],
    recentOrders: [],
    alerts: [],
    
    // UI state
    isLoading: false,
    isFullscreen: false,
    
    // Configuration
    dateRange: {
      quickSelect: 'last30days',
      fromDate: '',
      toDate: '',
      comparison: 'none'
    },
    
    charts: {
      salesChart: null,
      categoryChart: null,
      paymentChart: null,
      hourlyChart: null,
      salesTrendType: 'daily'
    },
    
    // Chart instances
    chartInstances: {},
    
    // WebSocket connection
    wsConnection: null,
    
    init() {
      this.initializeDateRange();
      this.loadDashboardData();
      this.initializeWebSocket();
      this.initializeCharts();
      this.initializeTables();
      this.setupEventListeners();
      
      // Auto-refresh every 30 seconds
      setInterval(() => {
        this.refreshDashboard();
      }, 30000);
    },
    
    initializeDateRange() {
      const today = new Date();
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(today.getDate() - 30);
      
      this.dateRange.toDate = today.toISOString().split('T')[0];
      this.dateRange.fromDate = thirtyDaysAgo.toISOString().split('T')[0];
    },
    
    async loadDashboardData() {
      this.isLoading = true;
      
      try {
        const params = new URLSearchParams({
          from_date: this.dateRange.fromDate,
          to_date: this.dateRange.toDate,
          realtime: 'true'
        });
        
        const response = await fetch(`/dynamic-reports/api/dashboard/data?${params}`);
        const result = await response.json();
        
        if (result.success) {
          this.dashboardData = result.data;
          this.updateRealtimeData();
          this.updateCharts();
          this.updateTables();
          this.loadAlerts();
        } else {
          this.showNotification('Failed to load dashboard data', 'error');
        }
      } catch (error) {
        console.error('Error loading dashboard data:', error);
        this.showNotification('Error loading dashboard data', 'error');
      } finally {
        this.isLoading = false;
      }
    },
    
    updateRealtimeData() {
      if (this.dashboardData.real_time) {
        this.realtimeData = {
          connected: true,
          lastUpdated: this.dashboardData.real_time.last_updated,
          todaySales: this.dashboardData.real_time.today_sales || 0,
          activeOrders: this.dashboardData.real_time.active_orders || 0,
          lowStockItems: this.dashboardData.real_time.low_stock_items || 0
        };
      }
    },
    
    initializeCharts() {
      // Sales Trend Chart
      this.initializeSalesChart();
      
      // Category Distribution Chart
      this.initializeCategoryChart();
      
      // Payment Methods Chart
      this.initializePaymentChart();
      
      // Hourly Pattern Chart
      this.initializeHourlyChart();
    },
    
    initializeSalesChart() {
      const ctx = document.getElementById('salesChart').getContext('2d');
      
      this.chartInstances.sales = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: 'Sales',
            data: [],
            borderColor: '#667EEA',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
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
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
                label: (context) => `₹${context.parsed.y.toLocaleString()}`
              }
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
                text: 'Sales (₹)'
              },
              beginAtZero: true,
              ticks: {
                callback: (value) => `₹${value.toLocaleString()}`
              }
            }
          },
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
          }
        }
      });
    },
    
    initializeCategoryChart() {
      const ctx = document.getElementById('categoryChart').getContext('2d');
      
      this.chartInstances.category = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: [],
          datasets: [{
            data: [],
            backgroundColor: [
              '#667EEA',
              '#48BB78',
              '#ED8936',
              '#9F7AEA',
              '#38B2AC',
              '#F56565',
              '#4299E1',
              '#ECC94B'
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
                  return `${label}: ₹${value.toLocaleString()} (${percentage}%)`;
                }
              }
            }
          }
        }
      });
    },
    
    initializePaymentChart() {
      const ctx = document.getElementById('paymentChart').getContext('2d');
      
      this.chartInstances.payment = new Chart(ctx, {
        type: 'pie',
        data: {
          labels: [],
          datasets: [{
            data: [],
            backgroundColor: [
              '#48BB78',
              '#4299E1',
              '#ED8936',
              '#9F7AEA',
              '#38B2AC'
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
                  return `${label}: ₹${value.toLocaleString()} (${percentage}%)`;
                }
              }
            }
          }
        }
      });
    },
    
    initializeHourlyChart() {
      const ctx = document.getElementById('hourlyChart').getContext('2d');
      
      this.chartInstances.hourly = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: [],
          datasets: [{
            label: 'Sales',
            data: [],
            backgroundColor: 'rgba(102, 126, 234, 0.6)',
            borderColor: '#667EEA',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              callbacks: {
                label: (context) => `₹${context.parsed.y.toLocaleString()}`
              }
            }
          },
          scales: {
            x: {
              display: true,
              title: {
                display: true,
                text: 'Hour of Day'
              }
            },
            y: {
              display: true,
              title: {
                display: true,
                text: 'Sales (₹)'
              },
              beginAtZero: true,
              ticks: {
                callback: (value) => `₹${value.toLocaleString()}`
              }
            }
          }
        }
      });
    },
    
    updateCharts() {
      this.updateSalesChart();
      this.updateCategoryChart();
      this.updatePaymentChart();
      this.updateHourlyChart();
    },
    
    updateSalesChart() {
      if (!this.chartInstances.sales || !this.dashboardData.trends) return;
      
      const trendData = this.dashboardData.trends.daily_trend || [];
      
      this.chartInstances.sales.data.labels = trendData.map(item => {
        return new Date(item.date).toLocaleDateString();
      });
      
      this.chartInstances.sales.data.datasets[0].data = trendData.map(item => item.sales);
      this.chartInstances.sales.update('active');
    },
    
    updateCategoryChart() {
      if (!this.chartInstances.category || !this.dashboardData.categories) return;
      
      const categories = this.dashboardData.categories.categories || [];
      
      this.chartInstances.category.data.labels = categories.map(cat => cat.name);
      this.chartInstances.category.data.datasets[0].data = categories.map(cat => cat.sales);
      this.chartInstances.category.update('active');
    },
    
    updatePaymentChart() {
      if (!this.chartInstances.payment || !this.dashboardData.payment_methods) return;
      
      const paymentData = this.dashboardData.payment_methods.methods || [];
      
      this.chartInstances.payment.data.labels = paymentData.map(pm => pm.method);
      this.chartInstances.payment.data.datasets[0].data = paymentData.map(pm => pm.amount);
      this.chartInstances.payment.update('active');
    },
    
    updateHourlyChart() {
      if (!this.chartInstances.hourly || !this.dashboardData.trends) return;
      
      const hourlyData = this.dashboardData.trends.hourly_pattern || [];
      
      this.chartInstances.hourly.data.labels = hourlyData.map(item => `${item.hour}:00`);
      this.chartInstances.hourly.data.datasets[0].data = hourlyData.map(item => item.sales);
      this.chartInstances.hourly.update('active');
    },
    
    initializeTables() {
      // Initialize DataTables
      if ($.fn.DataTable.isDataTable('#topItemsTable')) {
        $('#topItemsTable').DataTable().destroy();
      }
      
      if ($.fn.DataTable.isDataTable('#recentOrdersTable')) {
        $('#recentOrdersTable').DataTable().destroy();
      }
      
      // Initialize with empty data
      this.updateTables();
    },
    
    updateTables() {
      // Update top selling items table
      this.updateTopItemsTable();
      
      // Update recent orders table
      this.updateRecentOrdersTable();
    },
    
    updateTopItemsTable() {
      // Simulate top selling items data
      this.topSellingItems = [
        {
          id: 1,
          name: 'Butter Chicken',
          description: 'Creamy tomato-based curry',
          category: 'Indian Curries',
          quantitySold: 145,
          revenue: 7250,
          trend: 'up',
          trendPercentage: 12
        },
        {
          id: 2,
          name: 'Biryani',
          description: 'Fragrant rice with spices',
          category: 'Rice Dishes',
          quantitySold: 132,
          revenue: 6600,
          trend: 'up',
          trendPercentage: 8
        },
        {
          id: 3,
          name: 'Naan Bread',
          description: 'Traditional Indian bread',
          category: 'Bread',
          quantitySold: 298,
          revenue: 4470,
          trend: 'down',
          trendPercentage: -3
        },
        {
          id: 4,
          name: 'Dal Makhani',
          description: 'Rich black lentil curry',
          category: 'Indian Curries',
          quantitySold: 89,
          revenue: 3560,
          trend: 'stable',
          trendPercentage: 0
        },
        {
          id: 5,
          name: 'Chicken Tikka',
          description: 'Grilled chicken pieces',
          category: 'Tandoor',
          quantitySold: 76,
          revenue: 3800,
          trend: 'up',
          trendPercentage: 15
        }
      ];
      
      // Reinitialize DataTable
      setTimeout(() => {
        if ($.fn.DataTable.isDataTable('#topItemsTable')) {
          $('#topItemsTable').DataTable().destroy();
        }
        
        $('#topItemsTable').DataTable({
          paging: false,
          searching: false,
          info: false,
          order: [[3, 'desc']],
          columnDefs: [
            { orderable: false, targets: [0, 5] }
          ]
        });
      }, 100);
    },
    
    updateRecentOrdersTable() {
      // Simulate recent orders data
      this.recentOrders = [
        {
          id: 1,
          orderNumber: 'ORD-2025-001',
          customerName: 'John Doe',
          tableNumber: 5,
          itemsCount: 3,
          total: 450,
          status: 'Completed',
          createdAt: new Date(Date.now() - 15 * 60000).toISOString()
        },
        {
          id: 2,
          orderNumber: 'ORD-2025-002',
          customerName: 'Jane Smith',
          tableNumber: 12,
          itemsCount: 2,
          total: 320,
          status: 'In Progress',
          createdAt: new Date(Date.now() - 25 * 60000).toISOString()
        },
        {
          id: 3,
          orderNumber: 'ORD-2025-003',
          customerName: 'Walk-in',
          tableNumber: null,
          itemsCount: 1,
          total: 180,
          status: 'Ready',
          createdAt: new Date(Date.now() - 35 * 60000).toISOString()
        },
        {
          id: 4,
          orderNumber: 'ORD-2025-004',
          customerName: 'Mike Johnson',
          tableNumber: 8,
          itemsCount: 4,
          total: 680,
          status: 'Completed',
          createdAt: new Date(Date.now() - 45 * 60000).toISOString()
        },
        {
          id: 5,
          orderNumber: 'ORD-2025-005',
          customerName: 'Sarah Wilson',
          tableNumber: 3,
          itemsCount: 2,
          total: 290,
          status: 'New',
          createdAt: new Date(Date.now() - 55 * 60000).toISOString()
        }
      ];
      
      // Reinitialize DataTable
      setTimeout(() => {
        if ($.fn.DataTable.isDataTable('#recentOrdersTable')) {
          $('#recentOrdersTable').DataTable().destroy();
        }
        
        $('#recentOrdersTable').DataTable({
          paging: false,
          searching: false,
          info: false,
          order: [[5, 'desc']],
          columnDefs: [
            { orderable: false, targets: [2, 4] }
          ]
        });
      }, 100);
    },
    
    loadAlerts() {
      if (this.dashboardData.alerts) {
        this.alerts = this.dashboardData.alerts.map((alert, index) => ({
          id: index,
          ...alert,
          timestamp: new Date().toLocaleString()
        }));
      }
    },
    
    initializeWebSocket() {
      // WebSocket implementation would go here
      // For now, simulate connection
      setTimeout(() => {
        this.realtimeData.connected = true;
        this.realtimeData.lastUpdated = new Date().toISOString();
      }, 1000);
    },
    
    setupEventListeners() {
      // Listen for window resize to handle chart responsiveness
      window.addEventListener('resize', () => {
        Object.values(this.chartInstances).forEach(chart => {
          if (chart) chart.resize();
        });
      });
      
      // Keyboard shortcuts
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
          switch(e.key) {
            case 'r':
              e.preventDefault();
              this.refreshDashboard();
              break;
            case 'f':
              e.preventDefault();
              this.toggleFullscreen();
              break;
          }
        }
      });
    },
    
    // UI Actions
    async refreshDashboard() {
      await this.loadDashboardData();
      this.showNotification('Dashboard refreshed', 'success');
    },
    
    toggleFullscreen() {
      this.isFullscreen = !this.isFullscreen;
      
      if (this.isFullscreen) {
        document.documentElement.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    },
    
    updateDateRange() {
      const today = new Date();
      
      switch (this.dateRange.quickSelect) {
        case 'today':
          this.dateRange.fromDate = today.toISOString().split('T')[0];
          this.dateRange.toDate = today.toISOString().split('T')[0];
          break;
        case 'yesterday':
          const yesterday = new Date(today);
          yesterday.setDate(yesterday.getDate() - 1);
          this.dateRange.fromDate = yesterday.toISOString().split('T')[0];
          this.dateRange.toDate = yesterday.toISOString().split('T')[0];
          break;
        case 'last7days':
          const weekAgo = new Date(today);
          weekAgo.setDate(weekAgo.getDate() - 7);
          this.dateRange.fromDate = weekAgo.toISOString().split('T')[0];
          this.dateRange.toDate = today.toISOString().split('T')[0];
          break;
        case 'last30days':
          const monthAgo = new Date(today);
          monthAgo.setDate(monthAgo.getDate() - 30);
          this.dateRange.fromDate = monthAgo.toISOString().split('T')[0];
          this.dateRange.toDate = today.toISOString().split('T')[0];
          break;
        case 'thisMonth':
          this.dateRange.fromDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
          this.dateRange.toDate = today.toISOString().split('T')[0];
          break;
        case 'lastMonth':
          const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
          const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
          this.dateRange.fromDate = lastMonth.toISOString().split('T')[0];
          this.dateRange.toDate = lastMonthEnd.toISOString().split('T')[0];
          break;
      }
      
      this.loadDashboardData();
    },
    
    updateSalesChart() {
      if (this.charts.salesTrendType === 'daily') {
        this.updateDailySalesChart();
      }
      // Add weekly and monthly implementations
    },
    
    updateDailySalesChart() {
      if (!this.chartInstances.sales || !this.dashboardData.trends) return;
      
      const trendData = this.dashboardData.trends.daily_trend || [];
      
      this.chartInstances.sales.data.labels = trendData.map(item => {
        return new Date(item.date).toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric' 
        });
      });
      
      this.chartInstances.sales.data.datasets[0].data = trendData.map(item => item.sales);
      this.chartInstances.sales.update('active');
    },
    
    refreshTopItems() {
      this.updateTopItemsTable();
      this.showNotification('Top items refreshed', 'success');
    },
    
    refreshRecentOrders() {
      this.updateRecentOrdersTable();
      this.showNotification('Recent orders refreshed', 'success');
    },
    
    dismissAlert(alertId) {
      this.alerts = this.alerts.filter(alert => alert.id !== alertId);
    },
    
    // Export functions
    async exportReport(format) {
      try {
        const params = new URLSearchParams({
          type: 'dashboard',
          format: format,
          from_date: this.dateRange.fromDate,
          to_date: this.dateRange.toDate
        });
        
        const response = await fetch(`/dynamic-reports/api/export?${params}`);
        
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `dashboard_report_${new Date().toISOString().split('T')[0]}.${format}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          
          this.showNotification(`Report exported as ${format.toUpperCase()}`, 'success');
        } else {
          throw new Error('Export failed');
        }
      } catch (error) {
        console.error('Export error:', error);
        this.showNotification('Failed to export report', 'error');
      }
    },
    
    exportChart(chartId) {
      if (this.chartInstances[chartId.replace('Chart', '')]) {
        const chart = this.chartInstances[chartId.replace('Chart', '')];
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
    
    formatTime(timestamp) {
      if (!timestamp) return '';
      
      const date = new Date(timestamp);
      const now = new Date();
      const diff = now - date;
      const minutes = Math.floor(diff / 60000);
      
      if (minutes < 1) return 'Just now';
      if (minutes < 60) return `${minutes}m ago`;
      
      const hours = Math.floor(minutes / 60);
      if (hours < 24) return `${hours}h ago`;
      
      return date.toLocaleDateString();
    },
    
    getChangeClass(value) {
      if (value > 0) return 'positive';
      if (value < 0) return 'negative';
      return 'neutral';
    },
    
    getChangeIcon(value) {
      if (value > 0) return 'bi bi-arrow-up';
      if (value < 0) return 'bi bi-arrow-down';
      return 'bi bi-dash';
    },
    
    getTrendIcon(trend) {
      switch (trend) {
        case 'up': return 'bi bi-arrow-up text-success';
        case 'down': return 'bi bi-arrow-down text-danger';
        default: return 'bi bi-dash text-muted';
      }
    },
    
    getAlertIcon(type) {
      switch (type) {
        case 'warning': return 'bi bi-exclamation-triangle text-warning';
        case 'error': return 'bi bi-x-circle text-danger';
        case 'info': return 'bi bi-info-circle text-info';
        default: return 'bi bi-bell text-primary';
      }
    },
    
    animateValue(element, start, end, duration) {
      const range = end - start;
      const increment = end > start ? 1 : -1;
      const stepTime = Math.abs(Math.floor(duration / range));
      
      let current = start;
      const timer = setInterval(() => {
        current += increment;
        this.animatedValue = current;
        
        if (current === end) {
          clearInterval(timer);
        }
      }, stepTime);
    },
    
    showNotification(message, type = 'info') {
      // Simple notification system
      const notification = document.createElement('div');
      notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
      notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
      notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;
      
      document.body.appendChild(notification);
      
      // Auto remove after 5 seconds
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
  Alpine.data('dynamicReportsDashboard', dynamicReportsDashboard);
});

// CSS animations for spinning icon
const style = document.createElement('style');
style.textContent = `
  .spinning {
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  
  .pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #28a745;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }
  
  @keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); }
  }
`;
document.head.appendChild(style);