// Enhanced Reports Dashboard JavaScript
// Chart.js integration with modern interactive features and bug fixes

function reportsDashboard() {
  return {
    // Data
    isLoading: false,
    hasData: true,
    charts: {},
    isUpdating: false, // Prevent recursive updates
    updateQueue: [], // Queue for debounced updates
    updateTimeout: null, // Timeout for debouncing
    
    // Stats
    stats: {
      totalSales: 0,
      totalOrders: 0,
      cancelledOrders: 0,
      averageOrderValue: 0,
      salesGrowth: 12,
      ordersGrowth: 8,
      cancelledGrowth: -3,
      aovGrowth: 5
    },
    
    // Filters
    filters: {
      reportType: 'dashboard',
      fromDate: '',
      toDate: '',
      comparison: 'none'
    },
    
    // Table Data
    tableData: [],
    
    // Chart configurations
    chartConfigs: {
      dailyOrdersChart: null,
      categoriesChart: null,
      paymentMethodsChart: null,
      monthlySalesChart: null,
      cgstChart: null,
      sgstChart: null
    },

    // Initialize
    init() {
      try {
        this.setDefaultDates();
        this.loadReportData();
        this.initCharts();
        
        // Auto-refresh every 5 minutes
        setInterval(() => {
          this.refreshAllData();
        }, 300000);
      } catch (error) {
        console.error('Error in init:', error);
        this.showNotification('Error initializing dashboard', 'error');
      }
    },

    // Set default date range (last 30 days)
    setDefaultDates() {
      try {
        const today = new Date();
        const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));
        
        this.filters.toDate = today.toISOString().split('T')[0];
        this.filters.fromDate = thirtyDaysAgo.toISOString().split('T')[0];
      } catch (error) {
        console.error('Error setting default dates:', error);
      }
    },

    // Load report data from API
    async loadReportData() {
      try {
        this.isLoading = true;
        
        // Simulate API call with mock data
        await this.fetchReportData();
        this.updateStats();
        this.updateCharts();
        this.updateTable();
        this.hasData = true;
        
        this.showNotification('Report data loaded successfully', 'success');
      } catch (error) {
        console.error('Error loading report data:', error);
        this.hasData = false;
        this.showNotification('Failed to load report data', 'error');
      } finally {
        this.isLoading = false;
        this.isUpdating = false;
      }
    },

    // Fetch report data (mock implementation)
    async fetchReportData() {
      try {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock data based on report type
        const mockData = this.generateMockData();
        
        // Update stats
        this.stats = {
          totalSales: mockData.totalSales,
          totalOrders: mockData.totalOrders,
          cancelledOrders: mockData.cancelledOrders,
          averageOrderValue: mockData.averageOrderValue,
          salesGrowth: mockData.salesGrowth,
          ordersGrowth: mockData.ordersGrowth,
          cancelledGrowth: mockData.cancelledGrowth,
          aovGrowth: mockData.aovGrowth
        };
        
        // Update table data
        this.tableData = mockData.tableData;
        
        return mockData;
      } catch (error) {
        console.error('Error fetching report data:', error);
        throw error;
      }
    },

    // Generate mock data for demonstration
    generateMockData() {
      try {
        const reportType = this.filters.reportType;
        
        // Base mock data
        const baseData = {
          totalSales: 125000 + Math.random() * 50000,
          totalOrders: 450 + Math.floor(Math.random() * 200),
          cancelledOrders: 15 + Math.floor(Math.random() * 10),
          averageOrderValue: 278 + Math.random() * 100,
          salesGrowth: 8 + Math.random() * 10,
          ordersGrowth: 5 + Math.random() * 8,
          cancelledGrowth: -5 + Math.random() * 5,
          aovGrowth: 3 + Math.random() * 7,
          tableData: []
        };
        
        // Generate table data
        const days = 30;
        for (let i = 0; i < days; i++) {
          const date = new Date();
          date.setDate(date.getDate() - (days - i));
          
          const orders = 10 + Math.floor(Math.random() * 30);
          const avgOrderValue = baseData.averageOrderValue + (Math.random() - 0.5) * 100;
          const grossSales = orders * avgOrderValue;
          const discount = grossSales * 0.02;
          const netSales = grossSales - discount;
          const cgst = netSales * 0.025;
          const sgst = netSales * 0.025;
          const total = netSales + cgst + sgst;
          
          baseData.tableData.push({
            date: date.toISOString().split('T')[0],
            orders: orders,
            grossSales: grossSales,
            discount: discount,
            netSales: netSales,
            cgst: cgst,
            sgst: sgst,
            total: total
          });
        }
        
        return baseData;
      } catch (error) {
        console.error('Error generating mock data:', error);
        throw error;
      }
    },

    // Initialize all charts with proper cleanup
    initCharts() {
      try {
        // Destroy existing charts first
        this.destroyAllCharts();
        
        this.$nextTick(() => {
          try {
            this.initDailyOrdersChart();
            this.initCategoriesChart();
            this.initPaymentMethodsChart();
            this.initMonthlySalesChart();
            this.initGSTCharts();
          } catch (error) {
            console.error('Error initializing individual charts:', error);
          }
        });
      } catch (error) {
        console.error('Error in initCharts:', error);
      }
    },

    // Destroy all existing charts to prevent memory leaks
    destroyAllCharts() {
      try {
        Object.keys(this.chartConfigs).forEach(chartKey => {
          const chart = this.chartConfigs[chartKey];
          if (chart && chart.destroy) {
            chart.destroy();
            this.chartConfigs[chartKey] = null;
          }
        });
      } catch (error) {
        console.error('Error destroying charts:', error);
      }
    },

    // Initialize Daily Orders Chart with error handling
    initDailyOrdersChart() {
      try {
        const ctx = document.getElementById('dailyOrdersChart');
        if (!ctx) return;
        
        // Destroy existing chart
        if (this.chartConfigs.dailyOrdersChart && this.chartConfigs.dailyOrdersChart.destroy) {
          this.chartConfigs.dailyOrdersChart.destroy();
        }
        
        const last7Days = this.getLast7Days();
        const ordersData = last7Days.map(() => 10 + Math.floor(Math.random() * 30));
        
        this.chartConfigs.dailyOrdersChart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: last7Days,
            datasets: [{
              label: 'Orders',
              data: ordersData,
              backgroundColor: 'rgba(102, 126, 234, 0.8)',
              borderColor: 'rgba(102, 126, 234, 1)',
              borderWidth: 1,
              borderRadius: 8,
              hoverBackgroundColor: 'rgba(102, 126, 234, 1)'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
              duration: 1000,
              easing: 'easeInOutQuart',
              onComplete: function() {
                // Ensure animation completes properly
              }
            },
            plugins: {
              legend: {
                display: false,
                position: 'top',
                labels: {
                  display: false,
                  color: '#666',
                  font: { size: 12 }
                }
              },
              tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                titleColor: '#fff',
                bodyColor: '#fff',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1,
                displayColors: false,
                enabled: true,
                mode: 'index',
                intersect: false,
                callbacks: {
                  label: function(context) {
                    // Add null checks for context and parsed values
                    if (!context || !context.parsed || context.parsed.y === undefined) {
                      return 'Orders: 0';
                    }
                    return `Orders: ${context.parsed.y}`;
                  }
                }
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                ticks: {
                  precision: 0,
                  callback: function(value) {
                    return value !== null && value !== undefined ? value.toString() : '0';
                  }
                }
              },
              x: {
                grid: { display: false },
                ticks: {
                  callback: function(value) {
                    return value !== null && value !== undefined ? value.toString() : '';
                  }
                }
              }
            }
          }
        });
      } catch (error) {
        console.error('Error initializing daily orders chart:', error);
      }
    },

    // Initialize Categories Chart with error handling
    initCategoriesChart() {
      try {
        const ctx = document.getElementById('categoriesChart');
        if (!ctx) return;
        
        // Destroy existing chart
        if (this.chartConfigs.categoriesChart && this.chartConfigs.categoriesChart.destroy) {
          this.chartConfigs.categoriesChart.destroy();
        }
        
        const categories = ['Beverages', 'Food', 'Desserts', 'Snacks', 'Others'];
        const data = [35, 30, 15, 12, 8];
        
        this.chartConfigs.categoriesChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: categories,
            datasets: [{
              data: data,
              backgroundColor: [
                'rgba(102, 126, 234, 0.8)',
                'rgba(72, 187, 120, 0.8)',
                'rgba(237, 137, 54, 0.8)',
                'rgba(159, 122, 234, 0.8)',
                'rgba(56, 178, 172, 0.8)'
              ],
              borderColor: [
                'rgba(102, 126, 234, 1)',
                'rgba(72, 187, 120, 1)',
                'rgba(237, 137, 54, 1)',
                'rgba(159, 122, 234, 1)',
                'rgba(56, 178, 172, 1)'
              ],
              borderWidth: 2
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
              animateRotate: true,
              animateScale: true,
              duration: 1000,
              easing: 'easeInOutQuart'
            },
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  padding: 15,
                  usePointStyle: true,
                  font: { size: 12 },
                  color: '#666'
                }
              },
              tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                enabled: true,
                mode: 'index',
                intersect: false,
                callbacks: {
                  label: function(context) {
                    // Add comprehensive null checks
                    if (!context || !context.dataset || !context.dataset.data) {
                      return '0%';
                    }
                    
                    const total = Array.isArray(context.dataset.data)
                      ? context.dataset.data.reduce((a, b) => a + (b || 0), 0)
                      : 0;
                    
                    if (total === 0) return '0%';
                    
                    const parsed = context.parsed !== undefined ? context.parsed : 0;
                    const percentage = ((parsed / total) * 100).toFixed(1);
                    const label = context.label || 'Unknown';
                    return `${label}: ${percentage}%`;
                  }
                }
              }
            }
          }
        });
      } catch (error) {
        console.error('Error initializing categories chart:', error);
      }
    },

    // Initialize Payment Methods Chart with error handling
    initPaymentMethodsChart() {
      try {
        const ctx = document.getElementById('paymentMethodsChart');
        if (!ctx) return;
        
        // Destroy existing chart
        if (this.chartConfigs.paymentMethodsChart && this.chartConfigs.paymentMethodsChart.destroy) {
          this.chartConfigs.paymentMethodsChart.destroy();
        }
        
        const methods = ['Cash', 'Card', 'UPI', 'Wallet'];
        const data = [40, 35, 20, 5];
        
        this.chartConfigs.paymentMethodsChart = new Chart(ctx, {
          type: 'pie',
          data: {
            labels: methods,
            datasets: [{
              data: data,
              backgroundColor: [
                'rgba(102, 126, 234, 0.8)',
                'rgba(72, 187, 120, 0.8)',
                'rgba(237, 137, 54, 0.8)',
                'rgba(245, 101, 101, 0.8)'
              ],
              borderColor: [
                'rgba(102, 126, 234, 1)',
                'rgba(72, 187, 120, 1)',
                'rgba(237, 137, 54, 1)',
                'rgba(245, 101, 101, 1)'
              ],
              borderWidth: 2
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
              animateRotate: true,
              animateScale: true,
              duration: 1000,
              easing: 'easeInOutQuart'
            },
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  padding: 15,
                  usePointStyle: true,
                  font: { size: 12 },
                  color: '#666'
                }
              },
              tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                enabled: true,
                callbacks: {
                  label: function(context) {
                    // Add comprehensive null checks
                    if (!context || !context.dataset || !context.dataset.data) {
                      return '0%';
                    }
                    
                    const total = Array.isArray(context.dataset.data)
                      ? context.dataset.data.reduce((a, b) => a + (b || 0), 0)
                      : 0;
                    
                    if (total === 0) return '0%';
                    
                    const parsed = context.parsed !== undefined ? context.parsed : 0;
                    const percentage = ((parsed / total) * 100).toFixed(1);
                    const label = context.label || 'Unknown';
                    return `${label}: ${percentage}%`;
                  }
                }
              }
            }
          }
        });
      } catch (error) {
        console.error('Error initializing payment methods chart:', error);
      }
    },

    // Initialize Monthly Sales Chart with error handling
    initMonthlySalesChart() {
      try {
        const ctx = document.getElementById('monthlySalesChart');
        if (!ctx) return;
        
        // Destroy existing chart
        if (this.chartConfigs.monthlySalesChart && this.chartConfigs.monthlySalesChart.destroy) {
          this.chartConfigs.monthlySalesChart.destroy();
        }
        
        const months = this.getLast12Months();
        const salesData = months.map(() => 80000 + Math.random() * 40000);
        const ordersData = months.map(() => 200 + Math.random() * 100);
        
        this.chartConfigs.monthlySalesChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: months,
            datasets: [{
              label: 'Sales (₹)',
              data: salesData,
              borderColor: 'rgba(102, 126, 234, 1)',
              backgroundColor: 'rgba(102, 126, 234, 0.1)',
              borderWidth: 3,
              fill: true,
              tension: 0.4,
              pointBackgroundColor: 'rgba(102, 126, 234, 1)',
              pointBorderColor: '#fff',
              pointBorderWidth: 2,
              pointRadius: 6,
              pointHoverRadius: 8
            }, {
              label: 'Orders',
              data: ordersData,
              borderColor: 'rgba(72, 187, 120, 1)',
              backgroundColor: 'rgba(72, 187, 120, 0.1)',
              borderWidth: 3,
              fill: true,
              tension: 0.4,
              pointBackgroundColor: 'rgba(72, 187, 120, 1)',
              pointBorderColor: '#fff',
              pointBorderWidth: 2,
              pointRadius: 6,
              pointHoverRadius: 8,
              yAxisID: 'y1'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
              mode: 'index',
              intersect: false
            },
            animation: {
              duration: 1500,
              easing: 'easeInOutQuart'
            },
            plugins: {
              legend: {
                position: 'top',
                labels: {
                  usePointStyle: true,
                  padding: 20
                }
              },
              tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                enabled: true,
                callbacks: {
                  label: function(context) {
                    // Add null checks for context and parsed values
                    if (!context || !context.dataset) {
                      return '0';
                    }
                    
                    let label = context.dataset.label || '';
                    if (label) {
                      label += ': ';
                    }
                    
                    if (context.parsed && context.parsed.y !== null && context.parsed.y !== undefined) {
                      if (context.datasetIndex === 0) {
                        label += '₹' + context.parsed.y.toFixed(0);
                      } else {
                        label += context.parsed.y.toFixed(0);
                      }
                    } else {
                      label += '0';
                    }
                    return label;
                  }
                }
              }
            },
            scales: {
              y: {
                type: 'linear',
                display: true,
                position: 'left',
                grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                ticks: {
                  callback: function(value) {
                    return '₹' + value.toLocaleString();
                  }
                }
              },
              y1: {
                type: 'linear',
                display: true,
                position: 'right',
                grid: { drawOnChartArea: false }
              },
              x: {
                grid: { display: false }
              }
            }
          }
        });
      } catch (error) {
        console.error('Error initializing monthly sales chart:', error);
      }
    },

    // Initialize GST Charts with error handling
    initGSTCharts() {
      try {
        // CGST Chart
        const cgstCtx = document.getElementById('cgstChart');
        if (cgstCtx) {
          // Destroy existing chart
          if (this.chartConfigs.cgstChart && this.chartConfigs.cgstChart.destroy) {
            this.chartConfigs.cgstChart.destroy();
          }
          
          const months = this.getLast6Months();
          const cgstData = months.map(() => 2000 + Math.random() * 1000);
          
          this.chartConfigs.cgstChart = new Chart(cgstCtx, {
            type: 'bar',
            data: {
              labels: months,
              datasets: [{
                label: 'CGST (₹)',
                data: cgstData,
                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1,
                borderRadius: 8
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              animation: { duration: 0 }, // Disable animation to prevent recursion
              plugins: {
                legend: {
                  display: false,
                  position: 'top',
                  labels: {
                    display: false,
                    color: '#666',
                    font: { size: 12 }
                  }
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                  ticks: {
                    callback: function(value) {
                      return '₹' + value.toLocaleString();
                    }
                  }
                },
                x: {
                  grid: { display: false }
                }
              }
            }
          });
        }
        
        // SGST Chart
        const sgstCtx = document.getElementById('sgstChart');
        if (sgstCtx) {
          // Destroy existing chart
          if (this.chartConfigs.sgstChart && this.chartConfigs.sgstChart.destroy) {
            this.chartConfigs.sgstChart.destroy();
          }
          
          const months = this.getLast6Months();
          const sgstData = months.map(() => 2000 + Math.random() * 1000);
          
          this.chartConfigs.sgstChart = new Chart(sgstCtx, {
            type: 'bar',
            data: {
              labels: months,
              datasets: [{
                label: 'SGST (₹)',
                data: sgstData,
                backgroundColor: 'rgba(72, 187, 120, 0.8)',
                borderColor: 'rgba(72, 187, 120, 1)',
                borderWidth: 1,
                borderRadius: 8
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              animation: { duration: 0 }, // Disable animation to prevent recursion
              plugins: {
                legend: {
                  display: false,
                  position: 'top',
                  labels: {
                    display: false,
                    color: '#666',
                    font: { size: 12 }
                  }
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                  ticks: {
                    callback: function(value) {
                      return '₹' + value.toLocaleString();
                    }
                  }
                },
                x: {
                  grid: { display: false }
                }
              }
            }
          });
        }
      } catch (error) {
        console.error('Error initializing GST charts:', error);
      }
    },

    // Update all charts with new data (with improved recursion protection and debouncing)
    updateCharts() {
      try {
        // Prevent recursive updates
        if (this.isUpdating) return;
        this.isUpdating = true;
        
        // Clear any existing timeout
        if (this.updateTimeout) {
          clearTimeout(this.updateTimeout);
        }
        
        // Debounce chart updates
        this.updateTimeout = setTimeout(() => {
          try {
            // Update chart data based on current filters
            Object.keys(this.chartConfigs).forEach(chartKey => {
              const chart = this.chartConfigs[chartKey];
              if (chart && this.shouldUpdateChart(chartKey)) {
                this.updateChartData(chartKey);
              }
            });
          } catch (error) {
            console.error('Error in debounced chart update:', error);
          } finally {
            // Reset update flag after all charts are updated
            this.isUpdating = false;
          }
        }, 50); // 50ms debounce delay
      } catch (error) {
        console.error('Error updating charts:', error);
        this.isUpdating = false;
      }
    },

    // Update specific chart data with improved error handling and validation
    updateChartData(chartKey) {
      try {
        const chart = this.chartConfigs[chartKey];
        if (!chart || !chart.data || !chart.config) {
          console.warn(`Chart ${chartKey} is not properly initialized`);
          return;
        }
        
        // Check if chart is in a valid state for updating
        if (chart.destroyed || chart.destroy) {
          console.warn(`Chart ${chartKey} is destroyed, skipping update`);
          return;
        }
        
        // Generate new data based on filters
        const newData = this.generateChartData(chartKey);
        
        // Validate new data structure
        if (!newData || !newData.labels || !Array.isArray(newData.datasets)) {
          console.error(`Invalid data structure for ${chartKey}:`, newData);
          return;
        }
        
        // Update chart with comprehensive error handling
        try {
          // Deep copy the data to prevent circular references
          const safeData = JSON.parse(JSON.stringify(newData));
          
          // Validate chart options before updating
          if (!chart.options) {
            chart.options = {};
          }
          
          // Ensure plugins object exists
          if (!chart.options.plugins) {
            chart.options.plugins = {};
          }
          
          // Ensure plugins.legend exists with proper structure
          if (!chart.options.plugins.legend) {
            chart.options.plugins.legend = { display: false };
          }
          
          // Ensure plugins.tooltip exists with proper structure
          if (!chart.options.plugins.tooltip) {
            chart.options.plugins.tooltip = { enabled: false };
          }
          
          // Update chart data safely
          chart.data = safeData;
          
          // Use 'none' animation to prevent recursion and add error handling
          if (typeof chart.update === 'function') {
            chart.update('none');
          }
        } catch (updateError) {
          console.error(`Error updating ${chartKey}:`, updateError);
          // Fallback to minimal data structure
          try {
            chart.data = { labels: [], datasets: [] };
            if (typeof chart.update === 'function') {
              chart.update('none');
            }
          } catch (fallbackError) {
            console.error(`Fallback update failed for ${chartKey}:`, fallbackError);
          }
        }
      } catch (error) {
        console.error(`Error in updateChartData for ${chartKey}:`, error);
      }
    },

    // Generate chart data based on filters with error handling
    generateChartData(chartKey) {
      try {
        const reportType = this.filters.reportType;
        
        switch (chartKey) {
          case 'dailyOrdersChart':
            return this.generateDailyOrdersData();
          case 'categoriesChart':
            return this.generateCategoriesData();
          case 'paymentMethodsChart':
            return this.generatePaymentMethodsData();
          case 'monthlySalesChart':
            return this.generateMonthlySalesData();
          default:
            return this.chartConfigs[chartKey].data;
        }
      } catch (error) {
        console.error(`Error generating chart data for ${chartKey}:`, error);
        return { labels: [], datasets: [] };
      }
    },

    // Generate daily orders data with error handling
    generateDailyOrdersData() {
      try {
        const days = this.filters.reportType === 'daily' ? 30 : 7;
        const labels = this.getLastNDays(days);
        const data = labels.map(() => 10 + Math.floor(Math.random() * 30));
        
        return {
          labels: labels,
          datasets: [{
            label: 'Orders',
            data: data,
            backgroundColor: 'rgba(102, 126, 234, 0.8)',
            borderColor: 'rgba(102, 126, 234, 1)',
            borderWidth: 1,
            borderRadius: 8
          }]
        };
      } catch (error) {
        console.error('Error generating daily orders data:', error);
        return { labels: [], datasets: [] };
      }
    },

    // Generate categories data with error handling
    generateCategoriesData() {
      try {
        const categories = ['Beverages', 'Food', 'Desserts', 'Snacks', 'Others'];
        const data = [
          30 + Math.random() * 10,
          25 + Math.random() * 10,
          15 + Math.random() * 5,
          15 + Math.random() * 5,
          5 + Math.random() * 5
        ];
        
        return {
          labels: categories,
          datasets: [{
            data: data,
            backgroundColor: [
              'rgba(102, 126, 234, 0.8)',
              'rgba(72, 187, 120, 0.8)',
              'rgba(237, 137, 54, 0.8)',
              'rgba(159, 122, 234, 0.8)',
              'rgba(56, 178, 172, 0.8)'
            ],
            borderColor: [
              'rgba(102, 126, 234, 1)',
              'rgba(72, 187, 120, 1)',
              'rgba(237, 137, 54, 1)',
              'rgba(159, 122, 234, 1)',
              'rgba(56, 178, 172, 1)'
            ],
            borderWidth: 2
          }]
        };
      } catch (error) {
        console.error('Error generating categories data:', error);
        return { labels: [], datasets: [] };
      }
    },

    // Generate payment methods data with error handling
    generatePaymentMethodsData() {
      try {
        const methods = ['Cash', 'Card', 'UPI', 'Wallet'];
        const data = [
          35 + Math.random() * 10,
          30 + Math.random() * 10,
          20 + Math.random() * 10,
          5 + Math.random() * 5
        ];
        
        return {
          labels: methods,
          datasets: [{
            data: data,
            backgroundColor: [
              'rgba(102, 126, 234, 0.8)',
              'rgba(72, 187, 120, 0.8)',
              'rgba(237, 137, 54, 0.8)',
              'rgba(245, 101, 101, 0.8)'
            ],
            borderColor: [
              'rgba(102, 126, 234, 1)',
              'rgba(72, 187, 120, 1)',
              'rgba(237, 137, 54, 1)',
              'rgba(245, 101, 101, 1)'
            ],
            borderWidth: 2
          }]
        };
      } catch (error) {
        console.error('Error generating payment methods data:', error);
        return { labels: [], datasets: [] };
      }
    },

    // Generate monthly sales data with error handling
    generateMonthlySalesData() {
      try {
        const months = this.filters.reportType === 'monthly' ? this.getLast12Months() : this.getLast6Months();
        const salesData = months.map(() => 80000 + Math.random() * 40000);
        const ordersData = months.map(() => 200 + Math.random() * 100);
        
        return {
          labels: months,
          datasets: [{
            label: 'Sales (₹)',
            data: salesData,
            borderColor: 'rgba(102, 126, 234, 1)',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4
          }, {
            label: 'Orders',
            data: ordersData,
            borderColor: 'rgba(72, 187, 120, 1)',
            backgroundColor: 'rgba(72, 187, 120, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            yAxisID: 'y1'
          }]
        };
      } catch (error) {
        console.error('Error generating monthly sales data:', error);
        return { labels: [], datasets: [] };
      }
    },

    // Check if chart should be updated
    shouldUpdateChart(chartKey) {
      try {
        const reportType = this.filters.reportType;
        
        if (reportType === 'dashboard') {
          return true;
        }
        
        if (reportType === 'gstr1' || reportType === 'gstr3b') {
          return chartKey === 'cgstChart' || chartKey === 'sgstChart';
        }
        
        return true;
      } catch (error) {
        console.error('Error checking if chart should update:', error);
        return false;
      }
    },

    // Update stats display
    updateStats() {
      try {
        // Stats are already updated in fetchReportData
        // This method can be used for additional formatting or calculations
      } catch (error) {
        console.error('Error updating stats:', error);
      }
    },

    // Update table display
    updateTable() {
      try {
        // Table data is already updated in fetchReportData
        // This method can be used for additional formatting or calculations
      } catch (error) {
        console.error('Error updating table:', error);
      }
    },

    // Update report type with error handling
    updateReportType() {
      try {
        this.loadReportData();
        
        // Re-initialize charts if needed
        this.$nextTick(() => {
          try {
            if (this.filters.reportType === 'gstr1' || this.filters.reportType === 'gstr3b') {
              this.initGSTCharts();
            }
          } catch (error) {
            console.error('Error updating report type:', error);
          }
        });
      } catch (error) {
        console.error('Error in updateReportType:', error);
      }
    },

    // Refresh all data with error handling
    async refreshAllData() {
      try {
        await this.loadReportData();
      } catch (error) {
        console.error('Error refreshing data:', error);
      }
    },

    // Reset filters with error handling
    resetFilters() {
      try {
        this.filters = {
          reportType: 'dashboard',
          fromDate: '',
          toDate: '',
          comparison: 'none'
        };
        
        this.setDefaultDates();
        this.loadReportData();
      } catch (error) {
        console.error('Error resetting filters:', error);
      }
    },

    // Export chart as image with error handling
    exportChart(chartId) {
      try {
        const chart = this.chartConfigs[chartId];
        if (!chart) return;
        
        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = `${chartId}_${new Date().toISOString().split('T')[0]}.png`;
        link.href = url;
        link.click();
        
        this.showNotification('Chart exported successfully', 'success');
      } catch (error) {
        console.error('Error exporting chart:', error);
        this.showNotification('Failed to export chart', 'error');
      }
    },

    // Toggle chart type with improved error handling
    toggleChartType(chartId) {
      try {
        const chart = this.chartConfigs[chartId];
        if (!chart || !chart.config) {
          console.warn(`Chart ${chartId} is not properly initialized for type toggle`);
          return;
        }
        
        // Prevent toggling during updates
        if (this.isUpdating) {
          console.warn('Cannot toggle chart type during update');
          return;
        }
        
        const currentType = chart.config.type;
        const newType = currentType === 'bar' ? 'line' : 'bar';
        
        // Safely update chart type
        chart.config.type = newType;
        
        // Use 'none' animation to prevent recursion
        if (typeof chart.update === 'function') {
          chart.update('none');
        }
      } catch (error) {
        console.error('Error toggling chart type:', error);
        this.showNotification('Failed to toggle chart type', 'error');
      }
    },

    // Export report with error handling
    exportReport(format) {
      try {
        switch (format) {
          case 'pdf':
            this.exportToPDF();
            break;
          case 'csv':
            this.exportToCSV();
            break;
          case 'excel':
            this.exportToExcel();
            break;
          default:
            this.showNotification('Invalid export format', 'error');
        }
      } catch (error) {
        console.error('Error exporting report:', error);
        this.showNotification('Failed to export report', 'error');
      }
    },

    // Export to PDF with error handling
    exportToPDF() {
      try {
        window.print();
        this.showNotification('PDF export initiated', 'success');
      } catch (error) {
        console.error('Error exporting to PDF:', error);
        this.showNotification('Failed to export to PDF', 'error');
      }
    },

    // Export to CSV with error handling
    exportToCSV() {
      try {
        const csvContent = this.generateCSVContent();
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `report_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        window.URL.revokeObjectURL(url);
        
        this.showNotification('CSV exported successfully', 'success');
      } catch (error) {
        console.error('Error exporting to CSV:', error);
        this.showNotification('Failed to export to CSV', 'error');
      }
    },

    // Export to Excel with error handling
    exportToExcel() {
      try {
        // For Excel export, we would typically use a library like xlsx
        // For now, we'll export as CSV and suggest the user can open it in Excel
        this.exportToCSV();
        this.showNotification('Excel export initiated (CSV format)', 'success');
      } catch (error) {
        console.error('Error exporting to Excel:', error);
        this.showNotification('Failed to export to Excel', 'error');
      }
    },

    // Generate CSV content with error handling
    generateCSVContent() {
      try {
        let csv = 'Date,Orders,Gross Sales,Discount,Net Sales,CGST,SGST,Total\n';
        
        this.tableData.forEach(row => {
          csv += `${row.date},${row.orders},${row.grossSales.toFixed(2)},${row.discount.toFixed(2)},${row.netSales.toFixed(2)},${row.cgst.toFixed(2)},${row.sgst.toFixed(2)},${row.total.toFixed(2)}\n`;
        });
        
        return csv;
      } catch (error) {
        console.error('Error generating CSV content:', error);
        return 'Error generating CSV';
      }
    },

    // Email report with error handling
    emailReport() {
      try {
        // This would typically open a modal or navigate to an email composition page
        this.showNotification('Email functionality coming soon', 'info');
      } catch (error) {
        console.error('Error in email report:', error);
      }
    },

    // Print report with error handling
    printReport() {
      try {
        window.print();
      } catch (error) {
        console.error('Error printing report:', error);
      }
    },

    // Utility functions with error handling
    formatCurrency(amount) {
      try {
        return new Intl.NumberFormat('en-IN', {
          style: 'currency',
          currency: 'INR',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0
        }).format(amount);
      } catch (error) {
        console.error('Error formatting currency:', error);
        return '₹0';
      }
    },

    // Get last N days with error handling
    getLastNDays(days) {
      try {
        const result = [];
        for (let i = days - 1; i >= 0; i--) {
          const date = new Date();
          date.setDate(date.getDate() - i);
          result.push(date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }));
        }
        return result;
      } catch (error) {
        console.error('Error getting last N days:', error);
        return [];
      }
    },

    // Get last 7 days with error handling
    getLast7Days() {
      try {
        return this.getLastNDays(7);
      } catch (error) {
        console.error('Error getting last 7 days:', error);
        return [];
      }
    },

    // Get last 6 months with error handling
    getLast6Months() {
      try {
        const result = [];
        for (let i = 5; i >= 0; i--) {
          const date = new Date();
          date.setMonth(date.getMonth() - i);
          result.push(date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }));
        }
        return result;
      } catch (error) {
        console.error('Error getting last 6 months:', error);
        return [];
      }
    },

    // Get last 12 months with error handling
    getLast12Months() {
      try {
        const result = [];
        for (let i = 11; i >= 0; i--) {
          const date = new Date();
          date.setMonth(date.getMonth() - i);
          result.push(date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }));
        }
        return result;
      } catch (error) {
        console.error('Error getting last 12 months:', error);
        return [];
      }
    },

    // Show notification with error handling
    showNotification(message, type = 'info') {
      try {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `reports-notification reports-notification-${type}`;
        notification.textContent = message;
        
        // Add styles
        Object.assign(notification.style, {
          position: 'fixed',
          top: '20px',
          right: '20px',
          padding: '12px 20px',
          borderRadius: '8px',
          color: '#fff',
          fontWeight: '500',
          zIndex: '9999',
          opacity: '0',
          transform: 'translateY(-20px)',
          transition: 'all 0.3s ease'
        });
        
        // Set background color based on type
        const colors = {
          success: '#48BB78',
          error: '#F56565',
          warning: '#ED8936',
          info: '#4299E1'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        // Add to DOM
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
          notification.style.opacity = '1';
          notification.style.transform = 'translateY(0)';
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
          notification.style.opacity = '0';
          notification.style.transform = 'translateY(-20px)';
          setTimeout(() => {
            if (document.body.contains(notification)) {
              document.body.removeChild(notification);
            }
          }, 300);
        }, 3000);
      } catch (error) {
        console.error('Error showing notification:', error);
      }
    }
  };
}

// Initialize when DOM is ready with error handling
document.addEventListener('alpine:init', () => {
  try {
    Alpine.data('reportsDashboard', reportsDashboard);
  } catch (error) {
    console.error('Error initializing Alpine:', error);
  }
});
