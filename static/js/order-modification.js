/**
 * Order Modification Frontend JavaScript
 * Handles all client-side interactions for order modifications
 */

class OrderModification {
    constructor() {
        this.currentModification = null;
        this.selectedItems = [];
        this.priceImpact = 0;
        this.ws = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeWebSocket();
        this.loadPendingModifications();
        this.setupFormValidation();
    }

    bindEvents() {
        // Form submission
        document.getElementById('modification-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitModification();
        });

        // Clear form
        document.getElementById('clear-form').addEventListener('click', () => {
            this.clearForm();
        });

        // Modification type change
        document.getElementById('modification-type').addEventListener('change', (e) => {
            this.handleModificationTypeChange(e.target.value);
        });

        // Quick action buttons
        document.getElementById('add-item-btn').addEventListener('click', () => {
            this.openAddItemModal();
        });

        document.getElementById('change-quantity-btn').addEventListener('click', () => {
            this.openChangeQuantityModal();
        });

        document.getElementById('change-item-btn').addEventListener('click', () => {
            this.openChangeItemModal();
        });

        document.getElementById('cancel-order-btn').addEventListener('click', () => {
            this.openCancelOrderModal();
        });

        // Quick modify buttons on order items
        document.querySelectorAll('.quick-modify-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const orderItemId = e.target.closest('button').dataset.orderItemId;
                const itemName = e.target.closest('button').dataset.itemName;
                this.openQuickModifyModal(orderItemId, itemName);
            });
        });

        document.querySelectorAll('.remove-item-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const orderItemId = e.target.closest('button').dataset.orderItemId;
                const itemName = e.target.closest('button').dataset.itemName;
                this.confirmRemoveItem(orderItemId, itemName);
            });
        });

        // Approval/Rejection buttons
        document.querySelectorAll('.approve-modification-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modificationId = e.target.closest('button').dataset.modificationId;
                this.openApprovalModal(modificationId, 'approve');
            });
        });

        document.querySelectorAll('.reject-modification-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modificationId = e.target.closest('button').dataset.modificationId;
                this.openApprovalModal(modificationId, 'reject');
            });
        });

        document.querySelectorAll('.cancel-modification-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modificationId = e.target.closest('button').dataset.modificationId;
                this.cancelModification(modificationId);
            });
        });

        document.querySelectorAll('.implement-modification-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modificationId = e.target.closest('button').dataset.modificationId;
                this.implementModification(modificationId);
            });
        });

        // Modal confirmations
        document.getElementById('confirm-add-item').addEventListener('click', () => {
            this.confirmAddItem();
        });

        document.getElementById('confirm-approval').addEventListener('click', () => {
            this.confirmApproval();
        });

        document.getElementById('confirm-cancel-order').addEventListener('click', () => {
            this.confirmCancelOrder();
        });

        // Item search functionality
        document.getElementById('item-search').addEventListener('input', (e) => {
            this.searchItems(e.target.value);
        });

        document.getElementById('item-category').addEventListener('change', (e) => {
            this.searchItems(document.getElementById('item-search').value);
        });

        // Confirmation checkbox for cancellation
        document.getElementById('confirm-cancellation').addEventListener('change', (e) => {
            document.getElementById('confirm-cancel-order').disabled = !e.target.checked;
        });
    }

    initializeWebSocket() {
        // Initialize WebSocket connection for real-time updates
        if (typeof socketio !== 'undefined') {
            socketio.on('modification_created', (data) => {
                this.handleModificationUpdate(data);
            });

            socketio.on('modification_approved', (data) => {
                this.handleModificationUpdate(data);
            });

            socketio.on('modification_rejected', (data) => {
                this.handleModificationUpdate(data);
            });

            socketio.on('modification_implemented', (data) => {
                this.handleModificationUpdate(data);
            });

            socketio.on('kitchen_modification_update', (data) => {
                this.handleKitchenUpdate(data);
            });
        }
    }

    loadPendingModifications() {
        // Load pending modifications for approval dashboard
        fetch('/api/modifications/pending')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.updateApprovalDashboard(data.pending_modifications);
                }
            })
            .catch(error => {
                console.error('Error loading pending modifications:', error);
            });
    }

    setupFormValidation() {
        // Set up form validation rules
        const form = document.getElementById('modification-form');
        const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
        });
    }

    handleModificationTypeChange(type) {
        const container = document.getElementById('item-modifications-container');
        const priceImpactDisplay = document.getElementById('price-impact-display');
        
        if (type && type !== 'cancel_order' && type !== 'partial_cancel' && type !== 'kitchen_hold') {
            container.style.display = 'block';
            this.addItemModificationSection();
        } else {
            container.style.display = 'none';
            document.getElementById('item-modifications-list').innerHTML = '';
        }
        
        priceImpactDisplay.style.display = 'none';
    }

    addItemModificationSection() {
        const container = document.getElementById('item-modifications-list');
        const modificationType = document.getElementById('modification-type').value;
        
        const sectionHtml = `
            <div class="item-modification-section mb-3">
                <div class="card">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <label class="form-label">Action Type</label>
                                <select class="form-select item-action-type" onchange="OrderModification.handleItemActionChange(this)">
                                    <option value="">Select action...</option>
                                    <option value="add_item">Add Item</option>
                                    <option value="remove_item">Remove Item</option>
                                    <option value="change_quantity">Change Quantity</option>
                                    <option value="change_item">Substitute Item</option>
                                    <option value="update_instructions">Update Instructions</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Order Item (if applicable)</label>
                                <select class="form-select order-item-select">
                                    <option value="">Select order item...</option>
                                    ${this.getOrderItemsOptions()}
                                </select>
                            </div>
                        </div>
                        <div class="item-details mt-2" style="display: none;">
                            <!-- Item details will be populated here -->
                        </div>
                        <button type="button" class="btn btn-outline-danger btn-sm mt-2 remove-item-modification" 
                                onclick="OrderModification.removeItemModification(this)">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', sectionHtml);
    }

    getOrderItemsOptions() {
        // Get current order items for dropdown
        const orderItems = [];
        document.querySelectorAll('tbody tr').forEach(row => {
            const itemName = row.querySelector('td:first-child strong').textContent;
            const itemId = row.querySelector('button[data-order-item-id]').dataset.orderItemId;
            orderItems.push({ id: itemId, name: itemName });
        });
        
        return orderItems.map(item => `<option value="${item.id}">${item.name}</option>`).join('');
    }

    handleItemActionChange(select) {
        const section = select.closest('.item-modification-section');
        const detailsContainer = section.querySelector('.item-details');
        
        // Clear previous content
        detailsContainer.innerHTML = '';
        
        const actionType = select.value;
        if (!actionType) {
            detailsContainer.style.display = 'none';
            return;
        }
        
        detailsContainer.style.display = 'block';
        
        // Populate appropriate form based on action type
        switch (actionType) {
            case 'add_item':
                this.populateAddItemForm(detailsContainer);
                break;
            case 'remove_item':
                this.populateRemoveItemForm(detailsContainer, section);
                break;
            case 'change_quantity':
                this.populateQuantityChangeForm(detailsContainer, section);
                break;
            case 'change_item':
                this.populateItemSubstitutionForm(detailsContainer, section);
                break;
            case 'update_instructions':
                this.populateInstructionsForm(detailsContainer, section);
                break;
        }
        
        this.calculatePriceImpact();
    }

    populateAddItemForm(container) {
        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">Menu Item</label>
                    <input type="text" class="form-control menu-item-search" placeholder="Search menu items..." 
                           oninput="OrderModification.searchMenuItems(this)">
                    <div class="menu-item-results" style="max-height: 200px; overflow-y: auto;"></div>
                </div>
                <div class="col-md-3">
                    <label class="form-label">Quantity</label>
                    <input type="number" class="form-control item-quantity" min="1" value="1" 
                           onchange="OrderModification.calculatePriceImpact()">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Price</label>
                    <input type="number" class="form-control item-price" step="0.01" min="0">
                </div>
            </div>
            <div class="mt-2">
                <label class="form-label">Special Instructions</label>
                <textarea class="form-control item-instructions" rows="2"></textarea>
            </div>
        `;
    }

    populateRemoveItemForm(container, section) {
        const orderItemSelect = section.querySelector('.order-item-select');
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                This will remove the selected item from the order and process a refund.
            </div>
        `;
    }

    populateQuantityChangeForm(container, section) {
        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">New Quantity</label>
                    <input type="number" class="form-control new-quantity" min="1" value="1" 
                           onchange="OrderModification.calculatePriceImpact()">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Price Impact</label>
                    <input type="text" class="form-control price-impact" readonly>
                </div>
            </div>
        `;
    }

    populateItemSubstitutionForm(container, section) {
        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">New Menu Item</label>
                    <input type="text" class="form-control new-menu-item-search" placeholder="Search menu items..." 
                           oninput="OrderModification.searchMenuItems(this)">
                    <div class="menu-item-results" style="max-height: 200px; overflow-y: auto;"></div>
                </div>
                <div class="col-md-3">
                    <label class="form-label">Quantity</label>
                    <input type="number" class="form-control item-quantity" min="1" value="1" 
                           onchange="OrderModification.calculatePriceImpact()">
                </div>
                <div class="col-md-3">
                    <label class="form-label">New Price</label>
                    <input type="number" class="form-control new-item-price" step="0.01" min="0">
                </div>
            </div>
        `;
    }

    populateInstructionsForm(container, section) {
        container.innerHTML = `
            <div class="row">
                <div class="col-md-12">
                    <label class="form-label">New Instructions</label>
                    <textarea class="form-control new-instructions" rows="3"></textarea>
                </div>
            </div>
        `;
    }

    searchMenuItems(input) {
        const query = input.value;
        if (query.length < 2) {
            input.nextElementSibling.innerHTML = '';
            return;
        }
        
        fetch(`/api/menu/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.displayMenuItemResults(input.nextElementSibling, data.items);
                }
            })
            .catch(error => {
                console.error('Error searching menu items:', error);
            });
    }

    displayMenuItemResults(container, items) {
        if (items.length === 0) {
            container.innerHTML = '<div class="p-2 text-muted">No items found</div>';
            return;
        }
        
        container.innerHTML = items.map(item => `
            <div class="search-result-item p-2 border-bottom" onclick="OrderModification.selectMenuItem('${item.id}', '${item.name}', '${item.price}')">
                <strong>${item.name}</strong><br>
                <small class="text-muted">${item.category || 'No category'} - ₹${item.price}</small>
            </div>
        `).join('');
    }

    selectMenuItem(itemId, itemName, itemPrice) {
        // Populate the form with selected item details
        const container = event.target.closest('.item-details');
        container.querySelector('.item-price').value = itemPrice;
        container.querySelector('.menu-item-search').value = itemName;
        container.querySelector('.menu-item-search').dataset.itemId = itemId;
        
        // Hide search results
        container.querySelector('.menu-item-results').innerHTML = '';
        
        this.calculatePriceImpact();
    }

    removeItemModification(button) {
        button.closest('.item-modification-section').remove();
        this.calculatePriceImpact();
    }

    calculatePriceImpact() {
        // Calculate total price impact of all modifications
        let totalImpact = 0;
        const modifications = document.querySelectorAll('.item-modification-section');
        
        modifications.forEach(section => {
            const actionType = section.querySelector('.item-action-type').value;
            if (!actionType) return;
            
            switch (actionType) {
                case 'add_item':
                    const addPrice = parseFloat(section.querySelector('.item-price').value) || 0;
                    const addQuantity = parseInt(section.querySelector('.item-quantity').value) || 0;
                    totalImpact += addPrice * addQuantity;
                    break;
                    
                case 'change_quantity':
                    const orderItemSelect = section.querySelector('.order-item-select');
                    if (orderItemSelect.value) {
                        const newQuantity = parseInt(section.querySelector('.new-quantity').value) || 0;
                        // This would need actual order item data to calculate properly
                        // For now, just show placeholder
                        section.querySelector('.price-impact').value = '₹0.00 (calculated server-side)';
                    }
                    break;
                    
                case 'change_item':
                    const newPrice = parseFloat(section.querySelector('.new-item-price').value) || 0;
                    const quantity = parseInt(section.querySelector('.item-quantity').value) || 0;
                    totalImpact += newPrice * quantity;
                    break;
            }
        });
        
        this.updatePriceImpactDisplay(totalImpact);
    }

    updatePriceImpactDisplay(impact) {
        const display = document.getElementById('price-impact-display');
        const amountSpan = document.getElementById('price-impact-amount');
        const detailsSpan = document.getElementById('price-impact-details');
        
        if (Math.abs(impact) > 0.01) {
            display.style.display = 'block';
            amountSpan.textContent = impact > 0 ? `+₹${impact.toFixed(2)} (Additional Charge)` : `₹${impact.toFixed(2)} (Refund)`;
            detailsSpan.textContent = impact > 0 ? 'Additional payment required' : 'Refund will be processed';
            display.className = 'alert ' + (impact > 0 ? 'alert-warning' : 'alert-success');
        } else {
            display.style.display = 'none';
        }
    }

    async submitModification() {
        const formData = this.getFormData();
        
        if (!this.validateForm(formData)) {
            return;
        }
        
        try {
            const response = await fetch('/api/modifications/order/' + formData.order_id + '/modify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Modification request submitted successfully');
                this.clearForm();
                this.loadPendingModifications();
                
                // Refresh the page to show the new modification
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                this.showErrorMessage(result.error || 'Failed to submit modification request');
            }
        } catch (error) {
            console.error('Error submitting modification:', error);
            this.showErrorMessage('An error occurred while submitting the modification request');
        }
    }

    getFormData() {
        const formData = {
            order_id: parseInt(document.getElementById('order-id').value),
            modification_type: document.getElementById('modification-type').value,
            reason: document.getElementById('modification-reason').value,
            customer_reason: document.getElementById('customer-reason').value,
            priority: document.getElementById('modification-priority').value,
            item_modifications: this.getItemModifications()
        };
        
        return formData;
    }

    getItemModifications() {
        const modifications = [];
        const sections = document.querySelectorAll('.item-modification-section');
        
        sections.forEach(section => {
            const actionType = section.querySelector('.item-action-type').value;
            const orderItemSelect = section.querySelector('.order-item-select');
            
            if (!actionType) return;
            
            const modification = {
                modification_type: actionType,
                order_item_id: orderItemSelect.value || null
            };
            
            switch (actionType) {
                case 'add_item':
                    modification.original_menu_item_id = section.querySelector('.menu-item-search').dataset.itemId;
                    modification.new_quantity = parseInt(section.querySelector('.item-quantity').value);
                    modification.new_price = parseFloat(section.querySelector('.item-price').value);
                    modification.new_instructions = section.querySelector('.item-instructions').value;
                    break;
                    
                case 'remove_item':
                    // Order item ID is already set
                    break;
                    
                case 'change_quantity':
                    modification.new_quantity = parseInt(section.querySelector('.new-quantity').value);
                    break;
                    
                case 'change_item':
                    modification.new_menu_item_id = section.querySelector('.new-menu-item-search').dataset.itemId;
                    modification.new_quantity = parseInt(section.querySelector('.item-quantity').value);
                    modification.new_price = parseFloat(section.querySelector('.new-item-price').value);
                    break;
                    
                case 'update_instructions':
                    modification.new_instructions = section.querySelector('.new-instructions').value;
                    break;
            }
            
            modifications.push(modification);
        });
        
        return modifications;
    }

    validateForm(formData) {
        if (!formData.modification_type) {
            this.showErrorMessage('Please select a modification type');
            return false;
        }
        
        if (!formData.reason.trim()) {
            this.showErrorMessage('Please provide a reason for the modification');
            return false;
        }
        
        // Validate item modifications
        if (formData.item_modifications.length === 0 && 
            !['cancel_order', 'partial_cancel', 'kitchen_hold'].includes(formData.modification_type)) {
            this.showErrorMessage('Please add at least one item modification');
            return false;
        }
        
        return true;
    }

    clearForm() {
        document.getElementById('modification-form').reset();
        document.getElementById('item-modifications-container').style.display = 'none';
        document.getElementById('item-modifications-list').innerHTML = '';
        document.getElementById('price-impact-display').style.display = 'none';
        this.priceImpact = 0;
    }

    // Modal handlers
    openAddItemModal() {
        new bootstrap.Modal(document.getElementById('addItemModal')).show();
    }

    openChangeQuantityModal() {
        // Implementation for change quantity modal
        this.openQuickActionModal('change_quantity');
    }

    openChangeItemModal() {
        // Implementation for change item modal
        this.openQuickActionModal('change_item');
    }

    openCancelOrderModal() {
        new bootstrap.Modal(document.getElementById('cancelOrderModal')).show();
    }

    openQuickModifyModal(orderItemId, itemName) {
        // Implementation for quick modify modal
        console.log('Quick modify:', orderItemId, itemName);
    }

    openApprovalModal(modificationId, action) {
        document.getElementById('approval-modification-id').value = modificationId;
        document.getElementById('approval-action').value = action;
        document.getElementById('approval-modal-title').textContent = 
            action === 'approve' ? 'Approve Modification' : 'Reject Modification';
        document.getElementById('rejection-reason-container').style.display = 
            action === 'reject' ? 'block' : 'none';
        
        new bootstrap.Modal(document.getElementById('approvalModal')).show();
    }

    async confirmApproval() {
        const modificationId = document.getElementById('approval-modification-id').value;
        const action = document.getElementById('approval-action').value;
        const notes = document.getElementById('approval-notes').value;
        const reason = document.getElementById('rejection-reason').value;
        
        const endpoint = action === 'approve' ? 'approve' : 'reject';
        const payload = action === 'approve' ? { notes } : { reason };
        
        try {
            const response = await fetch(`/api/modifications/${modificationId}/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage(`Modification ${action}d successfully`);
                bootstrap.Modal.getInstance(document.getElementById('approvalModal')).hide();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showErrorMessage(result.error || `Failed to ${action} modification`);
            }
        } catch (error) {
            console.error(`Error ${action}ing modification:`, error);
            this.showErrorMessage(`An error occurred while ${action}ing the modification`);
        }
    }

    async implementModification(modificationId) {
        try {
            const response = await fetch(`/api/modifications/${modificationId}/implement`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ notes: 'Implemented via kitchen display' })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Modification implemented successfully');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showErrorMessage(result.error || 'Failed to implement modification');
            }
        } catch (error) {
            console.error('Error implementing modification:', error);
            this.showErrorMessage('An error occurred while implementing the modification');
        }
    }

    async cancelModification(modificationId) {
        if (!confirm('Are you sure you want to cancel this modification request?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/modifications/${modificationId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ reason: 'Cancelled by user request' })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Modification request cancelled successfully');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showErrorMessage(result.error || 'Failed to cancel modification request');
            }
        } catch (error) {
            console.error('Error cancelling modification:', error);
            this.showErrorMessage('An error occurred while cancelling the modification request');
        }
    }

    async confirmCancelOrder() {
        const reason = document.getElementById('cancel-reason').value;
        
        if (!reason.trim()) {
            this.showErrorMessage('Please provide a reason for cancellation');
            return;
        }
        
        try {
            const orderId = document.getElementById('order-id').value;
            const response = await fetch('/api/modifications/quick/cancel-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    order_id: parseInt(orderId),
                    reason: reason,
                    partial: false
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Order cancellation request submitted successfully');
                bootstrap.Modal.getInstance(document.getElementById('cancelOrderModal')).hide();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showErrorMessage(result.error || 'Failed to submit cancellation request');
            }
        } catch (error) {
            console.error('Error cancelling order:', error);
            this.showErrorMessage('An error occurred while submitting the cancellation request');
        }
    }

    confirmRemoveItem(orderItemId, itemName) {
        if (!confirm(`Are you sure you want to remove "${itemName}" from this order?`)) {
            return;
        }
        
        this.submitQuickModification('remove_item', { order_item_id: orderItemId });
    }

    async submitQuickModification(type, data) {
        try {
            const orderId = document.getElementById('order-id').value;
            const endpoint = this.getQuickEndpoint(type);
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    order_id: parseInt(orderId),
                    ...data
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage(result.message);
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showErrorMessage(result.error || 'Failed to submit modification');
            }
        } catch (error) {
            console.error('Error submitting quick modification:', error);
            this.showErrorMessage('An error occurred while submitting the modification');
        }
    }

    getQuickEndpoint(type) {
        const endpoints = {
            'remove_item': '/api/modifications/quick/remove-item',
            'change_quantity': '/api/modifications/quick/change-quantity',
            'add_item': '/api/modifications/quick/add-item'
        };
        return endpoints[type] || '/api/modifications/order/unknown/modify';
    }

    // Real-time update handlers
    handleModificationUpdate(data) {
        console.log('Modification update received:', data);
        // Update UI with new modification data
        this.loadPendingModifications();
    }

    handleKitchenUpdate(data) {
        console.log('Kitchen update received:', data);
        // Update kitchen-specific UI elements
        this.updateKitchenDisplay(data);
    }

    updateKitchenDisplay(data) {
        // Update kitchen displays with modification information
        const kitchenUpdates = document.getElementById('kitchen-updates');
        if (kitchenUpdates) {
            const updateHtml = `
                <div class="alert alert-info">
                    <strong>Order ${data.order_number}:</strong> ${data.modification_type} - ${data.status}
                </div>
            `;
            kitchenUpdates.insertAdjacentHTML('afterbegin', updateHtml);
        }
    }

    updateApprovalDashboard(modifications) {
        const pendingCount = modifications.length;
        document.getElementById('pending-count').textContent = pendingCount;
        
        // Update other dashboard metrics
        // This would be enhanced based on actual data
    }

    // Utility methods
    validateField(field) {
        const isValid = field.checkValidity();
        field.classList.toggle('is-invalid', !isValid);
        field.classList.toggle('is-valid', isValid);
        return isValid;
    }

    showSuccessMessage(message) {
        this.showAlert(message, 'success');
    }

    showErrorMessage(message) {
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at the top of the main content
        const mainContent = document.querySelector('.container-fluid');
        mainContent.insertBefore(alertDiv, mainContent.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    // Search functionality
    searchItems(query) {
        if (query.length < 2) {
            document.getElementById('item-search-results').innerHTML = '';
            return;
        }
        
        fetch(`/api/menu/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.displaySearchResults(data.items);
                }
            })
            .catch(error => {
                console.error('Error searching items:', error);
            });
    }

    displaySearchResults(items) {
        const container = document.getElementById('item-search-results');
        
        if (items.length === 0) {
            container.innerHTML = '<div class="p-3 text-muted">No items found</div>';
            return;
        }
        
        container.innerHTML = items.map(item => `
            <div class="search-result-item" onclick="OrderModification.selectSearchItem('${item.id}', '${item.name}', '${item.price}')">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${item.name}</strong><br>
                        <small class="text-muted">${item.category || 'No category'}</small>
                    </div>
                    <div class="text-end">
                        <strong>₹${item.price}</strong><br>
                        <small class="text-muted">${item.is_available ? 'Available' : 'Out of stock'}</small>
                    </div>
                </div>
            </div>
        `).join('');
    }

    selectSearchItem(itemId, itemName, itemPrice) {
        // Populate selected item details
        document.getElementById('selected-item-name').textContent = itemName;
        document.getElementById('selected-item-price').value = itemPrice;
        document.getElementById('selected-item-details').style.display = 'block';
        
        // Hide search results
        document.getElementById('item-search-results').innerHTML = '';
    }

    async confirmAddItem() {
        const itemName = document.getElementById('selected-item-name').textContent;
        const quantity = parseInt(document.getElementById('selected-item-quantity').value);
        const price = parseFloat(document.getElementById('selected-item-price').value);
        const instructions = document.getElementById('selected-item-instructions').value;
        
        if (!itemName || !quantity || !price) {
            this.showErrorMessage('Please fill in all required fields');
            return;
        }
        
        // Get the menu item ID from the selected item (this would need to be stored)
        const menuItemId = this.getSelectedMenuItemId();
        
        if (!menuItemId) {
            this.showErrorMessage('Please select a valid menu item');
            return;
        }
        
        await this.submitQuickModification('add_item', {
            menu_item_id: menuItemId,
            quantity: quantity,
            special_instructions: instructions
        });
        
        bootstrap.Modal.getInstance(document.getElementById('addItemModal')).hide();
    }

    getSelectedMenuItemId() {
        // This would need to be implemented to store the selected item ID
        // For now, return null
        return null;
    }

    // Static method to initialize the class
    static init() {
        if (!window.orderModificationInstance) {
            window.orderModificationInstance = new OrderModification();
        }
        return window.orderModificationInstance;
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    OrderModification.init();
});