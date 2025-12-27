/**
 * Sales Analytics Dashboard JavaScript
 * Advanced sales analytics with Chart.js integration and filtering
 */

function salesAnalyticsDashboard() {
  return {
    // Data properties
    salesData: {
      totalRevenue: 0,
      totalOrders: 0,
      averageOrderValue: 0,
      revenueGrowth: 0,
      ordersGrowth: 0,
      aovGrowth: 0,
      conversionRate: 0,
      comparison: null
    },
    topItems: [],
    salesSummary: [],
    
    // UI state
    isLoading: false,
    
    // Configuration
    filters: {
      period: 'last30days',
      fromDate: '',
      toDate: '',
      groupBy: 'day',
      category: 'all',
      paymentMethod: 'all'
    },
    
    topItemsLimit: 10,
    
    charts: {
      revenueChart: null,
      categoryChart: null,
      paymentChart: null,
      hourlyChart: null,
      revenueType: 'line'
    },
    
    chartInstances: {},
    
    init() {
      this.initializeFilters();
      this.loadSalesData();
      this.initializeCharts();
      this.initializeTables();
      this.setupEventListeners();
      
      // Auto-refresh every 60 seconds
      setInterval(() => {
        this.refreshData();
      }, 60000);
    },
    
    initializeFilters() {
      const today = new Date();
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(today.getDate() - 30);
      
      this.filters.toDate = today.toISOString().split('T')[0];
      this.filters.fromDate = thirtyDaysAgo.toISOString().split('T')[0];
    },
    
    async loadSalesData() {
      this.isLoading = true;
      
      try {
        const params = new URLSearchParams({
          from_date: this.filters.fromDate,
          to_date: this.filters.toDate,
          group_by: this.filters.groupBy,
          chart_type: this.charts.revenueType
        });
        
        if (this.filters.category !== 'all') {
          params.append('category', this.filters.category);
        }
        
        if (this.filters.paymentMethod !== 'all') {
          params.append('payment_method', this.filters.paymentMethod);
        }
        
        const response = await fetch(`/dynamic-reports/api/sales/analytics?${params}`);
        const result = await response.json();
        
        if (result.success) {
          this.salesData = {
            ...result.data,
            ...result.summary
          };
          this.updateCharts();
          this.updateTables();
        } else {
          this.showNotification('Failed to load sales data', 'error');
        }
      } catch (error) {
        console.error('Error loading sales data:', error);
        this.showNotification('Error loading sales data', 'error');
      } finally {
        this.isLoading = false;
      }
    },
    
    initializeCharts() {
      this.initializeRevenueChart();
      this.initializeCategoryChart();
      this.initializePaymentChart();
      this.initializeHourlyChart();
    },
    
    initializeRevenueChart() {
      const ctx = document.getElementById('revenueChart').getContext('2d');
      
      this.chartInstances.revenue = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Revenue',
              data: [],
              borderColor: '#48BB78',
              backgroundColor: 'rgba(72, 187, 120, 0.1)',
              borderWidth: 3,
              fill: true,
              tension: 0.4
            },
            {
              label: 'Orders',
              data: [],
              borderColor: '#4299E1',
              backgroundColor: 'rgba(66, 153, 225, 0.1)',
              borderWidth: 2,
              fill: false,
              tension: 0.4,
              yAxisID: 'y1'
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
              intersect: false,
              callbacks: {
                label: (context) => {
                  const label = context.dataset.label || '';
                  const value = context.parsed.y;
                  if (label === 'Revenue') {
                    return `${label}: ₹${value.toLocaleString()}`;
                  } else {
                    return `${label}: ${value}`;
                  }
                }
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
              type: 'linear',
              display: true,
              position: 'left',
              title: {
                display: true,
                text: 'Revenue (₹)'
              },
              beginAtZero: true,
              ticks: {
                callback: (value) => `₹${value.toLocaleString()}`
              }
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              title: {
                display: true,
                text: 'Orders'
              },
              beginAtZero: true,
              grid: {
                drawOnChartArea: false,
              },
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
              '#48BB78',
              '#4299E1',
              '#ED8936',
              '#9F7AEA',
              '#38B2AC',
              '#F56565',
              '#ECC94B',
              '#ED64A6'
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
            backgroundColor: 'rgba(72, 187, 120, 0.6)',
            borderColor: '#48BB78',
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
      this.updateRevenueChart();
      this.updateCategoryChart();
      this.updatePaymentChart();
      this.updateHourlyChart();
    },
    
    updateRevenueChart() {
      if (!this.chartInstances.revenue) return;
      
      // Simulate revenue data
      const labels = this.generateDateLabels();
      const revenueData = this.generateRevenueData(labels.length);
      const ordersData = this.generateOrdersData(labels.length);
      
      this.chartInstances.revenue.data.labels = labels;
      this.chartInstances.revenue.data.datasets[0].data = revenueData;
      this.chartInstances.revenue.data.datasets[1].data = ordersData;
      this.chartInstances.revenue.update('active');
    },
    
    updateCategoryChart() {
      if (!this.chartInstances.category) return;
      
      // Simulate category data
      const categories = ['Appetizers', 'Main Courses', 'Desserts', 'Beverages', 'Indian Curries', 'Rice Dishes'];
      const data = [12500, 25800, 8200, 15600, 32100, 18900];
      
      this.chartInstances.category.data.labels = categories;
      this.chartInstances.category.data.datasets[0].data = data;
      this.chartInstances.category.update('active');
    },
    
    updatePaymentChart() {
      if (!this.chartInstances.payment) return;
      
      // Simulate payment method data
      const methods = ['Cash', 'Card', 'UPI', 'Digital Wallet'];
      const data = [28500, 35200, 19800, 12600];
      
      this.chartInstances.payment.data.labels = methods;
      this.chartInstances.payment.data.datasets[0].data = data;
      this.chartInstances.payment.update('active');
    },
    
    updateHourlyChart() {
      if (!this.chartInstances.hourly) return;
      
      // Simulate hourly pattern
      const hours = Array.from({length: 24}, (_, i) => i);
      const data = [0, 0, 0, 0, 0, 0, 500, 1200, 2100, 3400, 4800, 6200, 
                   5800, 4500, 3800, 4200, 6800, 9200, 11500, 9800, 7200, 4800, 2100, 800];
      
      this.chartInstances.hourly.data.labels = hours.map(h => `${h}:00`);
      this.chartInstances.hourly.data.datasets[0].data = data;
      this.chartInstances.hourly.update('active');
    },
    
    initializeTables() {
      this.updateTopItems();
      this.updateSalesSummary();
    },
    
    updateTopItems() {
      // Simulate top selling items data
      this.topItems = [
        {
          id: 1,
          name: 'Butter Chicken',
          description: 'Creamy tomato-based curry',
          category: 'Indian Curries',
          quantity: 145,
          revenue: 7250,
          growth: 12
        },
        {
          id: 2,
          name: 'Biryani',
          description: 'Fragrant rice with spices',
          category: 'Rice Dishes',
          quantity: 132,
          revenue: 6600,
          growth: 8
        },
        {
          id: 3,
          name: 'Naan Bread',
          description: 'Traditional Indian bread',
          category: 'Bread',
          quantity: 298,
          revenue: 4470,
          growth: -3
        },
        {
          id: 4,
          name: 'Dal Makhani',
          description: 'Rich black lentil curry',
          category: 'Indian Curries',
          quantity: 89,
          revenue: 3560,
          growth: 0
        },
        {
          id: 5,
          name: 'Chicken Tikka',
          description: 'Grilled chicken pieces',
          category: 'Tandoor',
          quantity: 76,
          revenue: 3800,
          growth: 15
        }
      ].slice(0, this.topItemsLimit);
      
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
    
    updateSalesSummary() {
      // Simulate sales summary data
      const today = new Date();
      this.salesSummary = [];
      
      for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        
        this.salesSummary.push({
          date: date.toISOString().split('T')[0],
          orders: Math.floor(Math.random() * 50) + 20,
          revenue: Math.floor(Math.random() * 8000) + 3000,
          aov: Math.floor(Math.random() * 200) + 150,
          tax: Math.floor(Math.random() * 800) + 300,
          discount: Math.floor(Math.random() * 400) + 100
        });
      }
      
      // Reinitialize DataTable
      setTimeout(() => {
        if ($.fn.DataTable.isDataTable('#salesSummaryTable')) {
          $('#salesSummaryTable').DataTable().destroy();
        }
        
        $('#salesSummaryTable').DataTable({
          paging: false,
          searching: false,
          info: false,
          order: [[0, 'desc']],
          columnDefs: [
            { orderable: false, targets: [1, 2, 3, 4, 5] }
          ]
        });
      }, 100);
    },
    
    setupEventListeners() {
      // Listen for window resize
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
              this.refreshData();
              break;
          }
        }
      });
    },
    
    // UI Actions
    async refreshData() {
      await this.loadSalesData();
      this.showNotification('Sales data refreshed', 'success');
    },
    
    updateDateRange() {
      const today = new Date();
      
      switch (this.filters.period) {
        case 'today':
          this.filters.fromDate = today.toISOString().split('T')[0];
          this.filters.toDate = today.toISOString().split('T')[0];
          break;
        case 'yesterday':
          const yesterday = new Date(today);
          yesterday.setDate(yesterday.getDate() - 1);
          this.filters.fromDate = yesterday.toISOString().split('T')[0];
          this.filters.toDate = yesterday.toISOString().split('T')[0];
          break;
        case 'last7days':
          const weekAgo = new Date(today);
          weekAgo.setDate(weekAgo.getDate() - 7);
          this.filters.fromDate = weekAgo.toISOString().split('T')[0];
          this.filters.toDate = today.toISOString().split('T')[0];
          break;
        case 'last30days':
          const monthAgo = new Date(today);
          monthAgo.setDate(monthAgo.getDate() - 30);
          this.filters.fromDate = monthAgo.toISOString().split('T')[0];
          this.filters.toDate = today.toISOString().split('T')[0];
          break;
        case 'thisMonth':
          this.filters.fromDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
          this.filters.toDate = today.toISOString().split('T')[0];
          break;
        case 'lastMonth':
          const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
          const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
          this.filters.fromDate = lastMonth.toISOString().split('T')[0];
          this.filters.toDate = lastMonthEnd.toISOString().split('T')[0];
          break;
      }
      
      this.loadSalesData();
    },
    
    updateRevenueChart() {
      if (this.charts.revenueType === 'line') {
        this.chartInstances.revenue.config.type = 'line';
      } else {
        this.chartInstances.revenue.config.type = 'bar';
      }
      
      this.chartInstances.revenue.update('active');
    },
    
    refreshSummary() {
      this.updateSalesSummary();
      this.showNotification('Sales summary refreshed', 'success');
    },
    
    // Export functions
    async exportData(format) {
      try {
        const params = new URLSearchParams({
          type: 'sales',
          format: format,
          from_date: this.filters.fromDate,
          to_date: this.filters.toDate,
          group_by: this.filters.groupBy
        });
        
        const response = await fetch(`/dynamic-reports/api/export?${params}`);
        
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `sales_report_${new Date().toISOString().split('T')[0]}.${format}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          
          this.showNotification(`Sales data exported as ${format.toUpperCase()}`, 'success');
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
        'revenueChart': 'revenue',
        'categoryChart': 'category',
        'paymentChart': 'payment',
        'hourlyChart': 'hourly'
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
    
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      });
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
    
    getGrowthClass(growth) {
      if (growth > 0) return 'positive';
      if (growth < 0) return 'negative';
      return 'neutral';
    },
    
    getGrowthIcon(growth) {
      if (growth > 0) return 'bi bi-arrow-up';
      if (growth < 0) return 'bi bi-arrow-down';
      return 'bi bi-dash';
    },
    
    generateDateLabels() {
      const labels = [];
      const today = new Date();
      const days = this.filters.groupBy === 'day' ? 30 : this.filters.groupBy === 'week' ? 12 : 6;
      
      for (let i = days - 1; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric' 
        }));
      }
      
      return labels;
    },
    
    generateRevenueData(count) {
      return Array.from({length: count}, () => Math.floor(Math.random() * 8000) + 2000);
    },
    
    generateOrdersData(count) {
      return Array.from({length: count}, () => Math.floor(Math.random() * 50) + 10);
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
  Alpine.data('salesAnalyticsDashboard', salesAnalyticsDashboard);
});