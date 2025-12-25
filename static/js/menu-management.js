/**
 * Menu Management JavaScript
 * Handles image uploads, form submissions, and UI interactions for menu management
 */

function menuManagement() {
    return {
        searchQuery: "",
        selectedCategory: "",
        stockFilter: "all",
        editingItem: false,
        imagePreview: null,
        uploading: false,
        formData: {
            id: null,
            name: "",
            description: "",
            category_id: "",
            price: "",
            stock_quantity: "",
            unit: "",
            image_path: "",
        },

        init() {
            // Initialize Alpine.js data
            console.log('Menu management initialized');
        },

        filterItems() {
            const items = document.querySelectorAll(".menu-item");
            const query = this.searchQuery.toLowerCase();
            const category = this.selectedCategory;
            const stock = this.stockFilter;

            items.forEach((item) => {
                const itemCategory = item.dataset.category;
                const itemName = item.dataset.name;
                const itemStock = item.dataset.stock;

                const categoryMatch = !category || itemCategory === category;
                const nameMatch = !query || itemName.includes(query);
                let stockMatch = stock === "all";

                if (stock === "in_stock") stockMatch = itemStock === "in_stock";
                else if (stock === "low_stock")
                    stockMatch = itemStock === "low_stock";
                else if (stock === "out_of_stock")
                    stockMatch = itemStock === "out_of_stock";

                item.style.display =
                    categoryMatch && nameMatch && stockMatch ? "" : "none";
            });
        },

        showAddModal() {
            this.editingItem = false;
            this.resetForm();
            const modal = new bootstrap.Modal(document.getElementById("itemModal"));
            modal.show();
        },

        async editItem(itemId) {
            try {
                // Fetch item data from API
                const response = await fetch(`/menu/api_items/${itemId}`);
                const result = await response.json();
                
                if (result.success) {
                    this.editingItem = true;
                    this.formData = {
                        id: result.item.id,
                        name: result.item.name,
                        description: result.item.description || "",
                        category_id: result.item.category_id,
                        price: result.item.price,
                        stock_quantity: result.item.stock_quantity,
                        unit: result.item.unit || "",
                        image_path: result.item.image_path || "",
                    };
                    
                    // Set image preview if image exists
                    if (result.item.image_path) {
                        this.imagePreview = `/static/uploads/${result.item.image_path}`;
                    }
                    
                    const modal = new bootstrap.Modal(document.getElementById("itemModal"));
                    modal.show();
                } else {
                    this.showNotification("Error loading item data", "error");
                }
            } catch (error) {
                console.error('Error fetching item:', error);
                this.showNotification("Error loading item data", "error");
            }
        },

        resetForm() {
            this.formData = {
                id: null,
                name: "",
                description: "",
                category_id: "",
                price: "",
                stock_quantity: "",
                unit: "",
                image_path: "",
            };
            this.imagePreview = null;
            this.uploading = false;
            
            // Reset file input
            const imageInput = document.getElementById('imageInput');
            if (imageInput) {
                imageInput.value = '';
            }
        },

        async saveItem() {
            try {
                const url = this.editingItem ? `/menu/update_item/${this.formData.id}` : '/menu/add_item';
                const method = 'POST';
                
                // Create form data
                const formData = new FormData();
                formData.append('name', this.formData.name);
                formData.append('description', this.formData.description);
                formData.append('category_id', this.formData.category_id);
                formData.append('price', this.formData.price);
                formData.append('stock_quantity', this.formData.stock_quantity);
                formData.append('unit', this.formData.unit);
                formData.append('image_path', this.formData.image_path);
                
                // Add image file if uploading
                const imageInput = document.getElementById('imageInput');
                if (imageInput && imageInput.files[0]) {
                    formData.append('image', imageInput.files[0]);
                }
                
                const response = await fetch(url, {
                    method: method,
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (response.ok) {
                    this.showNotification(
                        this.editingItem ? "Item updated successfully" : "Item added successfully", 
                        "success"
                    );
                    
                    // Close modal and refresh page
                    const modal = bootstrap.Modal.getInstance(
                        document.getElementById("itemModal")
                    );
                    modal.hide();
                    
                    // Reload page to show updated data
                    window.location.reload();
                } else {
                    this.showNotification("Error saving item", "error");
                }
            } catch (error) {
                console.error('Save error:', error);
                this.showNotification("Error saving item", "error");
            }
        },

        async toggleStatus(itemId) {
            try {
                const response = await fetch(`/menu/toggle_status/${itemId}`, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (response.ok) {
                    this.showNotification("Item status updated", "success");
                    window.location.reload();
                } else {
                    this.showNotification("Error updating item status", "error");
                }
            } catch (error) {
                console.error('Status toggle error:', error);
                this.showNotification("Error updating item status", "error");
            }
        },

        async handleImageUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            // Validate file type
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
            if (!allowedTypes.includes(file.type)) {
                this.showNotification("Invalid file type. Please upload JPG, PNG, GIF, or WebP images.", "error");
                event.target.value = '';
                return;
            }
            
            // Validate file size (5MB max)
            if (file.size > 5 * 1024 * 1024) {
                this.showNotification("File too large. Please upload images smaller than 5MB.", "error");
                event.target.value = '';
                return;
            }
            
            // Show preview
            this.imagePreview = URL.createObjectURL(file);
            this.uploading = true;
            
            // Upload image
            const formData = new FormData();
            formData.append('image', file);
            
            try {
                const response = await fetch('/menu/upload_image', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.formData.image_path = result.image_path;
                    this.showNotification("Image uploaded successfully", "success");
                } else {
                    this.showNotification(result.message || "Error uploading image", "error");
                    this.removeImage();
                }
            } catch (error) {
                console.error('Upload error:', error);
                this.showNotification("Error uploading image", "error");
                this.removeImage();
            } finally {
                this.uploading = false;
            }
        },
        
        removeImage() {
            this.imagePreview = null;
            this.formData.image_path = "";
            const imageInput = document.getElementById('imageInput');
            if (imageInput) {
                imageInput.value = '';
            }
        },

        exportData() {
            // Export functionality
            this.showNotification("Export feature coming soon", "info");
        },

        showNotification(message, type = "info") {
            const toast = document.createElement("div");
            toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
            toast.style.zIndex = "9999";
            toast.textContent = message;

            document.body.appendChild(toast);

            setTimeout(() => {
                toast.remove();
            }, 3000);
        },
    };
}

// Initialize Alpine.js when DOM is ready
document.addEventListener('alpine:init', () => {
    Alpine.data('menuManagement', menuManagement);
});

// Also initialize manually for non-Alpine pages
document.addEventListener('DOMContentLoaded', () => {
    if (typeof Alpine === 'undefined') {
        console.warn('Alpine.js not loaded, menu management features may not work properly');
    }
});