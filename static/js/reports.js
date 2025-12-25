function reportsManagement() {
  return {
    reportType: "daily",
    fromDate: "",
    toDate: "",
    dailyStats: {
      totalSales: 0,
      cgstAmount: 0,
      sgstAmount: 0,
      totalTax: 0,
    },
    monthlyStats: {
      totalSales: 0,
      cgstAmount: 0,
      sgstAmount: 0,
      totalTax: 0,
    },

    init: function () {
      // Set default dates
      var today = new Date();
      this.toDate = today.toISOString().split("T")[0];

      var firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      this.fromDate = firstDay.toISOString().split("T")[0];

      this.loadReportData();
    },

    updateReportView: function () {
      this.loadReportData();
    },

    loadReportData: function () {
      var self = this;

      // Show loading state
      this.showNotification("Loading report data...", "info");

      // In a real application, this would make an API call
      // For now, we'll simulate loading data

      setTimeout(function () {
        if (self.reportType === "daily") {
          self.dailyStats = {
            totalSales: 12250.0,
            cgstAmount: 306.25,
            sgstAmount: 306.25,
            totalTax: 612.5,
          };
        } else if (self.reportType === "monthly") {
          self.monthlyStats = {
            totalSales: 123450.0,
            cgstAmount: 3086.25,
            sgstAmount: 3086.25,
            totalTax: 6172.5,
          };
        }

        self.showNotification("Report loaded successfully", "success");
      }, 1000);
    },

    exportReport: function () {
      var self = this;

      // Determine file name based on report type
      var fileName = this.getReportFileName();

      // Create CSV content
      var csvContent = this.generateCSVContent();

      // Create download link
      var blob = new Blob([csvContent], { type: "text/csv" });
      var url = window.URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      this.showNotification("Report exported successfully", "success");
    },

    printReport: function () {
      window.print();
    },

    getReportFileName: function () {
      var date = new Date().toISOString().split("T")[0];
      var reportNames = {
        daily: "daily_sales_" + date + ".csv",
        monthly: "monthly_sales_" + date + ".csv",
        gstr1: "gstr1_" + date + ".csv",
        gstr3b: "gstr3b_" + date + ".csv",
        itemwise: "itemwise_sales_" + date + ".csv",
        categorywise: "categorywise_sales_" + date + ".csv",
      };

      return reportNames[this.reportType] || "report_" + date + ".csv";
    },

    generateCSVContent: function () {
      var csvContent = "";

      switch (this.reportType) {
        case "daily":
          csvContent = this.generateDailyCSV();
          break;
        case "monthly":
          csvContent = this.generateMonthlyCSV();
          break;
        case "gstr1":
          csvContent = this.generateGSTR1CSV();
          break;
        case "gstr3b":
          csvContent = this.generateGSTR3BCSV();
          break;
        default:
          csvContent = "No data available for this report type";
      }

      return csvContent;
    },

    generateDailyCSV: function () {
      var headers =
        "Date,Orders,Gross Sales,Discount,Net Sales,CGST,SGST,Total\n";
      var data =
        "2024-01-15,45,12500.00,250.00,12250.00,306.25,306.25,12862.50\n";
      return headers + data;
    },

    generateMonthlyCSV: function () {
      var headers = "Month,Orders,Gross Sales,Net Sales,CGST,SGST,Total\n";
      var data =
        "January 2024,1245,125600.00,123450.00,3086.25,3086.25,129622.50\n";
      return headers + data;
    },

    generateGSTR1CSV: function () {
      var headers =
        "Description,Total Taxable Value,Integrated Tax,Central Tax,State/UT Tax,Cess\n";
      var data =
        "Outward Taxable Supplies,123450.00,0.00,3086.25,3086.25,0.00\n";
      return headers + data;
    },

    generateGSTR3BCSV: function () {
      var headers =
        "Description,Integrated Tax,Central Tax,State/UT Tax,Cess\n";
      var data1 = "Taxable Outward Supplies,0.00,3086.25,3086.25,0.00\n";
      var data2 = "ITC Available,0.00,1250.00,1250.00,0.00\n";
      return headers + data1 + data2;
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
  Alpine.data("reportsManagement", reportsManagement);
});
