function paymentProcessor() {
  return {
    orderData: window.orderData || {},
    selectedMethod: null,
    processing: false,
    paymentData: {
      amount_paid: 0,
      cash_received: 0,
      change: 0,
      card_number: "",
      expiry: "",
      card_holder: "",
      transaction_id: "",
      upi_id: "",
      upi_transaction_id: "",
      wallet_number: "",
      wallet_transaction_id: "",
      credit_customer: "",
      credit_period: "",
    },

    init() {
      // Initialize amount with order total
      this.paymentData.amount_paid = this.orderData.grand_total || 0;

      // Auto-format card number
      this.$watch("paymentData.card_number", (value) => {
        if (value) {
          // Remove non-digit characters
          let cleaned = value.replace(/\D/g, "");
          // Format as groups of 4
          let formatted = cleaned.match(/.{1,4}/g)?.join(" ") || cleaned;
          if (formatted !== value) {
            this.paymentData.card_number = formatted.slice(0, 19); // Max 19 chars (16 digits + 3 spaces)
          }
        }
      });

      // Auto-format expiry date
      this.$watch("paymentData.expiry", (value) => {
        if (value) {
          // Remove non-digit characters
          let cleaned = value.replace(/\D/g, "");
          // Format as MM/YY
          if (cleaned.length >= 2) {
            formatted = cleaned.slice(0, 2) + "/" + cleaned.slice(2, 4);
          } else {
            formatted = cleaned;
          }
          if (formatted !== value) {
            this.paymentData.expiry = formatted.slice(0, 5); // Max 5 chars (MM/YY)
          }
        }
      });
    },

    get paymentBalance() {
      const total = this.orderData.grand_total || 0;
      const paid = parseFloat(this.paymentData.amount_paid) || 0;
      return (paid - total).toFixed(2);
    },

    get canProcessPayment() {
      if (!this.selectedMethod || this.processing) {
        return false;
      }

      const total = this.orderData.grand_total || 0;
      const paid = parseFloat(this.paymentData.amount_paid) || 0;

      if (paid < total) {
        return false;
      }

      // Validate method-specific requirements
      switch (this.selectedMethod) {
        case "Cash":
          return this.paymentData.cash_received >= total;
        case "Card":
          return (
            this.paymentData.card_number &&
            this.paymentData.expiry &&
            this.paymentData.card_holder
          );
        case "UPI":
          return this.paymentData.upi_id && this.paymentData.upi_transaction_id;
        case "Wallet":
          return (
            this.paymentData.wallet_number &&
            this.paymentData.wallet_transaction_id
          );
        case "Credit":
          return (
            this.paymentData.credit_customer && this.paymentData.credit_period
          );
        default:
          return false;
      }
    },

    selectPaymentMethod(method) {
      this.selectedMethod = method;
      this.resetPaymentFields();
      this.paymentData.amount_paid = this.orderData.grand_total || 0;

      // Auto-set amount for cash payments
      if (method === "Cash") {
        this.paymentData.cash_received = this.orderData.grand_total || 0;
        this.calculateChange();
      }
    },

    resetPaymentFields() {
      this.paymentData = {
        amount_paid: 0,
        cash_received: 0,
        change: 0,
        card_number: "",
        expiry: "",
        card_holder: "",
        transaction_id: "",
        upi_id: "",
        upi_transaction_id: "",
        wallet_number: "",
        wallet_transaction_id: "",
        credit_customer: "",
        credit_period: "",
      };
    },

    calculateChange() {
      const total = this.orderData.grand_total || 0;
      const cashReceived = parseFloat(this.paymentData.cash_received) || 0;
      this.paymentData.change = Math.max(0, cashReceived - total);
      this.paymentData.amount_paid = cashReceived;
    },

    validatePayment() {
      const total = this.orderData.grand_total || 0;
      const paid = parseFloat(this.paymentData.amount_paid) || 0;

      if (paid < total) {
        this.showNotification("Insufficient payment amount", "error");
        return false;
      }
      return true;
    },

    async processPayment() {
      if (!this.validatePayment()) {
        return;
      }

      this.processing = true;

      try {
        // Prepare payment details
        const paymentDetails = {};

        switch (this.selectedMethod) {
          case "Cash":
            paymentDetails.cash_received = this.paymentData.cash_received;
            paymentDetails.change = this.paymentData.change;
            break;
          case "Card":
            paymentDetails.card_number = this.paymentData.card_number;
            paymentDetails.expiry = this.paymentData.expiry;
            paymentDetails.card_holder = this.paymentData.card_holder;
            paymentDetails.transaction_id = this.paymentData.transaction_id;
            break;
          case "UPI":
            paymentDetails.upi_id = this.paymentData.upi_id;
            paymentDetails.upi_transaction_id =
              this.paymentData.upi_transaction_id;
            break;
          case "Wallet":
            paymentDetails.wallet_number = this.paymentData.wallet_number;
            paymentDetails.wallet_transaction_id =
              this.paymentData.wallet_transaction_id;
            break;
          case "Credit":
            paymentDetails.credit_customer = this.paymentData.credit_customer;
            paymentDetails.credit_period = this.paymentData.credit_period;
            break;
        }

        const response = await fetch("/orders/process_payment", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            order_id: this.orderData.id,
            payment_method: this.selectedMethod,
            amount_paid: this.paymentData.amount_paid,
            discount: this.orderData.discount_amount || 0,
            payment_details: paymentDetails,
          }),
        });

        const result = await response.json();

        if (result.success) {
          this.showNotification(
            `Payment processed successfully! Order: ${result.order_number}`,
            "success"
          );

          // Redirect to orders page after successful payment
          setTimeout(() => {
            window.location.href = "/orders/list";
          }, 2000);
        } else {
          this.showNotification(result.message || "Payment failed", "error");
        }
      } catch (error) {
        console.error("Payment processing error:", error);
        this.showNotification(
          "Payment processing failed. Please try again.",
          "error"
        );
      } finally {
        this.processing = false;
      }
    },

    showNotification(message, type = "info") {
      // Create toast notification
      const toast = document.createElement("div");
      toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
      toast.style.zIndex = "9999";
      toast.style.minWidth = "300px";
      toast.innerHTML = `
        <div class="d-flex align-items-center">
          <i class="fas fa-${
            type === "success"
              ? "check-circle"
              : type === "error"
              ? "exclamation-circle"
              : "info-circle"
          } me-2"></i>
          <span>${message}</span>
        </div>
      `;

      document.body.appendChild(toast);

      // Auto-remove after 3 seconds
      setTimeout(() => {
        toast.remove();
      }, 3000);
    },

    // Utility methods
    formatCurrency(amount) {
      // Use global formatCurrency function from utils.js
      return window.formatCurrency(amount);
    },

    validateCardNumber(number) {
      // Basic Luhn algorithm for card validation
      const cleaned = number.replace(/\D/g, "");
      if (cleaned.length < 13 || cleaned.length > 19) return false;

      let sum = 0;
      let isEven = false;

      for (let i = cleaned.length - 1; i >= 0; i--) {
        let digit = parseInt(cleaned.charAt(i), 10);

        if (isEven) {
          digit *= 2;
          if (digit > 9) {
            digit = (digit % 10) + 1;
          }
        }

        sum += digit;
        isEven = !isEven;
      }

      return sum % 10 === 0;
    },

    validateExpiry(expiry) {
      if (!expiry || !expiry.includes("/")) return false;

      const [month, year] = expiry.split("/");
      const currentDate = new Date();
      const currentYear = currentDate.getFullYear() % 100;
      const currentMonth = currentDate.getMonth() + 1;

      const expMonth = parseInt(month, 10);
      const expYear = parseInt(year, 10);

      if (expMonth < 1 || expMonth > 12) return false;

      if (
        expYear < currentYear ||
        (expYear === currentYear && expMonth < currentMonth)
      ) {
        return false;
      }

      return true;
    },
  };
}

// Initialize when DOM is ready
document.addEventListener("alpine:init", () => {
  Alpine.data("paymentProcessor", paymentProcessor);
});
