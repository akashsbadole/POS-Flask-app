# Web Cloud POS - Advanced Features & Updates

## 🚀 Overview

This document provides comprehensive information about the advanced features, enhancements, and capabilities that have been added to the Web Cloud Restaurant POS system beyond the basic functionality described in the main README.md.

## 📋 Table of Contents

1. [Advanced Thermal Printer System](#advanced-thermal-printer-system)
2. [Performance Monitoring & Optimization](#performance-monitoring--optimization)
3. [Security Enhancement Suite](#security-enhancement-suite)
4. [Print Management & Analytics](#print-management--analytics)
5. [Advanced Order Management](#advanced-order-management)
6. [Email Notification System](#email-notification-system)
7. [Footer Customization System](#footer-customization-system)
8. [Data Export & Reporting](#data-export--reporting)
9. [Multi-Level Caching System](#multi-level-caching-system)
10. [Key Management & Encryption](#key-management--encryption)
11. [Enhanced API Endpoints](#enhanced-api-endpoints)
12. [Configuration Guides](#configuration-guides)
13. [Usage Guides](#usage-guides)
14. [Troubleshooting](#troubleshooting)

---

## 🖨️ Advanced Thermal Printer System

### Features Overview

The POS system includes a comprehensive thermal printer optimization system designed specifically for restaurant environments:

#### **Thermal Printer Specifications**
- **Supported Paper Widths**: 58mm and 80mm (80mm default)
- **Color Scheme**: Black text only (monochrome optimized)
- **Font Family**: 'Courier New', monospace for thermal printers
- **Character Encoding**: UTF-8 support for international characters
- **Print Quality**: High contrast, optimized for thermal printing

#### **Print Templates**
- **Bill Printing**: Optimized 80mm thermal bill format
- **KOT Printing**: Kitchen Order Ticket with urgency indicators
- **PDF Invoice**: Standard PDF format for digital invoices
- **Print Preview**: Real-time preview before printing

#### **Key Files**
```
web_cloud/
├── routes/print_management.py      # Print management routes
├── utils/print_manager.py          # Print manager utility
├── models/print_history.py         # Print history tracking
├── templates/orders/print.html     # Thermal bill template
├── templates/kot/print.html        # KOT thermal template
└── static/css/thermal-print.css    # Thermal printer styles
```

### Print Management Interface

Access the print management dashboard at `/orders/print-management`

#### **Features**
- Real-time printer status monitoring
- Print history with detailed analytics
- Printer configuration interface
- Print testing functionality
- Export capabilities for print history

#### **Printer Configuration Options**
```json
{
  "thermal_printer_name": "Default",
  "paper_width": "80mm",
  "font_size": "Medium",
  "auto_print_enabled": true
}
```

### Print History Tracking

Every print operation is automatically tracked with:
- Order ID and user attribution
- Print type (bill, KOT, invoice)
- Print method (thermal, PDF, preview)
- Number of copies
- Success/failure status with error messages
- Timestamp and printer information

#### **Print Statistics**
- Total prints by type and period
- Success rate analysis
- Top users by print volume
- Error rate monitoring
- Paper usage estimation

---

## 📊 Performance Monitoring & Optimization

### Performance Monitor System

The system includes a comprehensive performance monitoring suite that tracks and optimizes application performance in real-time.

#### **Key Features**
- **Response Time Tracking**: Monitors API response times
- **Memory Usage Monitoring**: Tracks memory consumption with alerts
- **Cache Performance**: Monitors cache hit/miss rates
- **Error Rate Tracking**: Tracks application errors by endpoint
- **Slow Query Detection**: Identifies and reports slow operations
- **Active Connection Monitoring**: Tracks concurrent user connections

#### **Background Monitoring**
The system runs background monitoring every 30 seconds:
- Memory usage tracking with cleanup suggestions
- Performance optimization recommendations
- Garbage collection optimization
- Alert system for performance issues

#### **Performance Metrics Dashboard**
Access performance metrics through the performance dashboard:
```python
# Get current performance metrics
metrics = performance_monitor.get_metrics()

# Returns:
{
    'uptime': 3600.5,
    'avg_response_time': 0.245,
    'total_requests': 1250,
    'cache_hit_rate': 85.2,
    'memory_usage': [...],
    'slow_queries_count': 3,
    'error_rate': 0.8,
    'active_connections': 12
}
```

### Cache Management System

#### **Features**
- **TTL-based Caching**: Configurable time-to-live for cached items
- **LRU Eviction**: Least Recently Used cache cleanup
- **Memory Optimization**: Automatic memory usage monitoring
- **Cache Statistics**: Hit/miss rate tracking and optimization

#### **Cache Usage**
```python
# Cache decorator for functions
@cache_result(ttl=300, key_prefix='menu')
def get_menu_items():
    # Function results cached for 5 minutes
    pass

# Manual cache operations
cache_manager.set('key', data, ttl=300)
cached_data = cache_manager.get('key')
```

---

## 🔒 Security Enhancement Suite

### Comprehensive Security Features

The POS system includes enterprise-grade security features to protect sensitive data and prevent unauthorized access.

#### **Security Manager Features**
- **CSRF Protection**: Cryptographically secure CSRF tokens
- **Rate Limiting**: IP-based rate limiting with automatic blocking
- **Suspicious Activity Detection**: AI-powered threat detection
- **Input Sanitization**: XSS and injection prevention
- **Password Security**: HMAC-SHA256 password hashing
- **IP Blocking**: Automatic blocking of malicious IPs

#### **Security Headers**
All responses include comprehensive security headers:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

#### **Rate Limiting Configuration**
```python
# Custom rate limits per endpoint
@rate_limit(limit=100, window=60)  # 100 requests per minute
def api_endpoint():
    pass

# Automatic IP blocking on violations
- Temporary IP blocks: 2x window duration
- Repeated violations: Permanent blocking consideration
- Admin notification of security events
```

#### **Security Event Logging**
All security events are logged with:
- IP address and user agent
- Event type and details
- Timestamp and context
- Automatic threat level assessment

### Authentication & Authorization

#### **Enhanced Login Security**
- Failed attempt tracking with IP monitoring
- Account lockout after multiple failed attempts
- Secure session management with timeout
- Password strength requirements

#### **CSRF Protection**
```python
# Generate CSRF token
csrf_token = generate_csrf_token()

# Validate CSRF token in forms
@validate_csrf
def protected_route():
    pass
```

---

## 📈 Print Management & Analytics

### Print Management System

Comprehensive print management with detailed tracking and analytics.

#### **Print Operations**
- **Bill Printing**: Thermal optimized bills with GST breakdown
- **KOT Printing**: Kitchen order tickets with status tracking
- **PDF Generation**: Professional PDF invoices
- **Print Preview**: Real-time preview before printing
- **Batch Printing**: Multiple copies with queue management

#### **Print History API**
```python
# Get print history with filters
GET /api/printer/history
{
    "order_id": 123,
    "user_id": 5,
    "print_type": "bill",
    "limit": 50
}

# Response:
{
    "success": true,
    "history": [
        {
            "id": 456,
            "order_id": 123,
            "order_number": "ORD-00123",
            "user_id": 5,
            "username": "admin",
            "print_type": "bill",
            "print_method": "thermal",
            "copies": 2,
            "printer_name": "Default",
            "success": true,
            "created_at": "2024-12-13T14:30:00Z"
        }
    ]
}
```

#### **Print Statistics**
```python
# Get print statistics
GET /api/printer/statistics?days=30

# Response:
{
    "success": true,
    "statistics": {
        "prints_by_type": [
            {"type": "bill", "count": 150, "total_copies": 180},
            {"type": "kot", "count": 200, "total_copies": 200},
            {"type": "invoice", "count": 50, "total_copies": 55}
        ],
        "total_prints": 400,
        "successful_prints": 395,
        "success_rate": 98.75,
        "top_users": [
            {"user_id": 5, "print_count": 120},
            {"user_id": 3, "print_count": 85}
        ]
    }
}
```

### Print Configuration

#### **Thermal Printer Settings**
```json
{
    "thermal_printer_name": "EPSON_TM-T88V",
    "paper_width": "80mm",
    "font_size": "Medium",
    "auto_print_enabled": true,
    "print_density": "Normal",
    "paper_cut": true
}
```

#### **Print Testing**
```python
# Test print bill
POST /api/printer/test/bill
{
    "order_id": 123,
    "copies": 1
}

# Test print KOT
POST /api/printer/test/kot
{
    "order_id": 123,
    "copies": 1
}

# Test PDF generation
POST /api/printer/test/pdf
{
    "order_id": 123,
    "copies": 1
}
```


## 🔄 Advanced Order Management

### Order Operations Manager

The POS system includes advanced order management capabilities that go beyond basic order creation and processing.

#### **Key Features**
- **Order Merging**: Combine multiple orders into a single order
- **Order Splitting**: Split orders into multiple separate orders
- **Order Transferring**: Move orders between tables
- **Payment Splitting**: Split payments across multiple methods
- **Order History**: Complete audit trail of order modifications

#### **Order Merging**
```python
# Merge multiple orders
POST /api/orders/merge
{
    "source_order_ids": [123, 124, 125],
    "target_order_id": 126
}

Response:
{
    "success": true,
    "message": "Successfully merged 3 orders",
    "merged_order_id": 126,
    "merged_amount": 450.75,
    "target_order_number": "ORD-00126"
}
```

#### **Order Splitting**
```python
# Split order into multiple orders
POST /api/orders/split
{
    "order_id": 126,
    "split_items": [
        {
            "items": [
                {"item_id": 1, "quantity": 2},
                {"item_id": 3, "quantity": 1}
            ]
        },
        {
            "items": [
                {"item_id": 2, "quantity": 1}
            ]
        }
    ]
}
```

#### **Order Transferring**
```python
# Transfer order between tables
POST /api/orders/transfer
{
    "order_id": 126,
    "from_table_id": 5,
    "to_table_id": 8
}
```

#### **Payment Splitting**
```python
# Split payment across methods
POST /api/orders/split-payment
{
    "order_id": 126,
    "payment_splits": [
        {"method": "Cash", "amount": 200.00},
        {"method": "Card", "amount": 150.00},
        {"method": "UPI", "amount": 100.75}
    ]
}
```

#### **Order History Tracking**
Complete audit trail for all order modifications:
- Original creation timestamp
- Transfer records with source/destination tables
- Split operations with new order references
- Merge operations with source order details
- Cancellation records with reasons
- Payment processing with method details

#### **Key Files**
```
web_cloud/
├── utils/order_manager.py         # Order operations manager
├── routes/orders.py              # Order management routes
└── models/order.py               # Order data models
```

---

## 📧 Email Notification System

### Advanced Email Management

The POS system includes a comprehensive email notification system for automated communications and backup notifications.

#### **Key Features**
- **SMTP Configuration**: Support for multiple email providers
- **Email Queue**: Asynchronous email processing
- **Email Templates**: Customizable email templates
- **Backup Notifications**: Automated backup completion emails
- **Low Stock Alerts**: Inventory threshold notifications
- **Daily Reports**: Automated sales report emails
- **Email History**: Complete email delivery tracking

#### **Supported Email Providers**
- Gmail
- Outlook/Hotmail
- Yahoo Mail
- Office 365
- Custom SMTP servers

#### **Email Configuration**
```json
{
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "use_tls": true,
    "use_ssl": false,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "from_email": "pos@restaurant.com",
    "from_name": "Restaurant POS",
    "recipients": ["manager@restaurant.com"],
    "backup_notifications": true,
    "test_emails": true,
    "max_attachment_size_mb": 25,
    "retry_attempts": 3,
    "retry_delay_seconds": 5
}
```

#### **Email Types**
1. **Order Notifications**: New order confirmations
2. **Low Stock Alerts**: Automatic inventory alerts
3. **Backup Notifications**: Backup completion reports
4. **Daily Sales Reports**: Automated daily summaries
5. **Test Emails**: Configuration verification

#### **Email Queue System**
- Asynchronous processing for better performance
- Retry mechanism for failed emails
- Attachment support for large files
- Email priority and scheduling
- Delivery status tracking

#### **Key Files**
```
web_cloud/
├── routes/email.py              # Email configuration routes
├── utils/email_service.py         # Advanced email service
├── utils/email_notifier.py       # Email notification manager
└── templates/email/              # Email templates
```

#### **Email API Endpoints**
```http
# Email configuration
GET /email/config
POST /email/config

# Email operations
POST /email/test
GET /email/history
POST /email/history/clear
GET /email/queue/status

# Provider presets
GET /email/providers
GET /email/providers/preset/{provider}
```

---

## 🎨 Footer Customization System

### Dynamic Footer Management

The POS system includes a comprehensive footer customization system that allows restaurant-specific branding and information display on all printed documents.

#### **Key Features**
- **Business Information**: Restaurant details and contact info
- **Receipt Information**: Order-specific receipt details
- **User Information**: Staff details and identification
- **Custom Text**: Customizable messages and branding
- **Styling Options**: Complete CSS customization
- **Dynamic Content**: Real-time data integration
- **Multiple Document Types**: Different footers for bills, KOTs, reports

#### **Footer Components**
1. **Business Information Section**
   - Restaurant name and logo
   - Address and contact details
   - Social media links
   - Business hours

2. **Receipt Information Section**
   - Order number and date
   - Table number and time
   - Order type (dine-in/takeaway)

3. **User Information Section**
   - Staff name and ID
   - Role and permissions
   - Timestamp of service

4. **Custom Message Section**
   - Thank you messages
   - Promotional text
   - Legal disclaimers
   - Special offers

#### **Footer Configuration**
```json
{
    "footer_enabled": true,
    "footer_fixed_position": false,
    "footer_business_name": "Restaurant Name",
    "footer_address": "123 Main St, City, State 12345",
    "footer_phone": "+1 (555) 123-4567",
    "footer_email": "contact@restaurant.com",
    "footer_company_logo": "/static/images/logo.png",
    "footer_logo_height": "30px",
    "footer_show_business_info": true,
    "footer_show_receipt_info": true,
    "footer_show_user_name": true,
    "footer_show_user_id": false,
    "footer_show_timestamp": true,
    "footer_show_page_info": true,
    "footer_show_version": false,
    "footer_custom_text": "Thank you for your business!",
    "footer_background_color": "#2c3e50",
    "footer_text_color": "#ecf0f1",
    "footer_border_color": "#34495e",
    "footer_border_width": "2px",
    "footer_font_family": "Arial, sans-serif",
    "footer_font_size": "12px",
    "footer_header_font_size": "14px",
    "footer_header_color": "#3498db",
    "footer_header_font_weight": "bold",
    "footer_small_font_size": "10px",
    "footer_padding": "15px 20px",
    "footer_version": "1.0.0",
    "footer_default_user": "Staff"
}
```

#### **Styling Customization**
- Background and text colors
- Border styles and widths
- Font families and sizes
- Padding and margins
- Responsive design support
- Print-specific styling

#### **Footer Preview**
Real-time preview functionality:
- Live preview while configuring
- Multiple document type previews
- Print optimization preview
- Mobile compatibility testing

#### **Key Files**
```
web_cloud/
├── routes/footer_settings.py      # Footer configuration routes
├── utils/footer_generator.py      # Footer generation utility
├── templates/footer/              # Footer templates
└── static/css/footer.css          # Footer styling
```

---

## 📊 Data Export & Reporting

### Advanced Export Capabilities

The POS system includes comprehensive data export and reporting capabilities for business intelligence and compliance.

#### **Export Formats**
- **CSV**: Excel-compatible data export
- **PDF**: Professional reports and invoices
- **Excel**: Native Excel format with formatting
- **JSON**: Structured data for API integration

#### **Export Categories**
1. **Order Data**
   - Complete order history
   - Order items and modifications
   - Payment processing records
   - Customer information

2. **Inventory Data**
   - Stock levels and movements
   - Low stock alerts
   - Supplier information
   - Cost analysis

3. **Sales Reports**
   - Daily/monthly summaries
   - Product performance
   - Category-wise analysis
   - GST compliance reports

4. **Employee Data**
   - Staff performance metrics
   - Working hours and schedules
   - Order processing statistics
   - Commission calculations

#### **GST Export Features**
- **GSTR-1 Reports**: Outward supplies
- **GSTR-3B Reports**: Tax summary
- **HSN Summary**: HSN code analysis
- **B2B vs B2C**: Customer type breakdown

#### **Export API**
```python
# Export orders to CSV
POST /api/export/orders
{
    "date_from": "2024-12-01",
    "date_to": "2024-12-31",
    "format": "csv",
    "include_items": true,
    "include_payments": true
}

# Export GST reports
POST /api/export/gst
{
    "report_type": "gstr1",
    "month": "12",
    "year": "2024",
    "format": "excel"
}

# Export inventory
POST /api/export/inventory
{
    "include_low_stock": true,
    "include_movements": true,
    "format": "csv"
}
```

#### **Key Files**
```
web_cloud/
├── utils/data_exporter.py         # Data export utility
├── routes/reports.py             # Report generation routes
└── exports/                     # Export file storage
    ├── orders/
    ├── pdf/
    └── text/
```

---

## 🗄️ Multi-Level Caching System

### Advanced Caching Architecture

The POS system implements a sophisticated multi-level caching system for optimal performance.

#### **Cache Levels**
1. **Memory Cache (L1)**
   - Fastest access for frequently used data
   - LRU eviction policy
   - Configurable size limits
   - TTL-based expiration

2. **Disk Cache (L2)**
   - Persistent cache for larger datasets
   - Automatic cleanup and compression
   - Size-based management
   - Backup and restore capabilities

#### **Cache Features**
- **TTL Management**: Configurable time-to-live per cache level
- **Cache Warming**: Preloading frequently accessed data
- **Cache Statistics**: Hit/miss rate monitoring
- **Cache Invalidation**: Smart invalidation strategies
- **Cache Backup**: Persistent cache across restarts

#### **Cache Configuration**
```python
# Cache levels configuration
cache_config = {
    'memory': {
        'max_size': 1000,
        'ttl': 300,  # 5 minutes
        'enabled': True
    },
    'disk': {
        'cache_dir': 'cache',
        'max_size_mb': 100,
        'ttl': 3600,  # 1 hour
        'enabled': True
    }
}

# Cache usage
@cache_result(ttl=300, key_prefix='menu')
def get_menu_items():
    # Results cached in memory first, then disk
    pass
```

#### **Cache Statistics**
```python
# Get cache performance
cache_stats = cache_manager.get_stats()

{
    'memory_cache': {
        'total_items': 245,
        'hit_rate': 85.2,
        'memory_usage': '12.5MB'
    },
    'disk_cache': {
        'total_items': 1250,
        'hit_rate': 92.1,
        'disk_usage': '45.2MB'
    },
    'overall_hit_rate': 89.7
}
```

#### **Key Files**
```
web_cloud/
├── utils/cache_manager.py         # Multi-level cache system
└── cache/                       # Cache storage directory
```

---

## 🔐 Key Management & Encryption

### Advanced Security Infrastructure

The POS system includes enterprise-grade key management and encryption for data protection.

#### **Key Management Features**
- **Encryption Keys**: AES-256 encryption for sensitive data
- **Key Rotation**: Automated key rotation schedules
- **Key Backup**: Secure backup and recovery
- **Key Integrity**: Verification and validation
- **Hardware Binding**: License hardware binding
- **Audit Trail**: Complete key usage logging

#### **Encryption Capabilities**
- **Data Encryption**: Sensitive customer and payment data
- **Field-Level Encryption**: Individual field protection
- **Database Encryption**: Full database encryption support
- **Transmission Encryption**: Secure data transmission
- **Key Escrow**: Recovery mechanisms

#### **Key Management API**
```python
# Generate new encryption key
POST /api/keys/generate
{
    "key_type": "encryption",
    "key_size": 256,
    "description": "Monthly key rotation"
}

# Rotate encryption key
POST /api/keys/rotate
{
    "key_id": "current_key_id",
    "new_master_key": "optional_new_key"
}

# Key backup operations
GET /api/keys/backup
POST /api/keys/restore
DELETE /api/keys/cleanup

# Key status and integrity
GET /api/keys/status
POST /api/keys/verify
```

#### **Encryption Utilities**
```python
# Field-level encryption
from utils.encryption import encrypt_data, decrypt_data

# Encrypt sensitive fields
encrypted_email = encrypt_data(customer_email)
encrypted_phone = encrypt_data(customer_phone)

# Database encryption
class Customer(db.Model):
    name = db.Column(db.String(100))
    email_encrypted = db.Column(db.Text)  # Encrypted field
    phone_encrypted = db.Column(db.Text)  # Encrypted field
```

#### **Key Files**
```
web_cloud/
├── utils/key_manager.py          # Key management utility
├── utils/encryption.py           # Encryption utilities
├── config/encryption.key         # Current encryption key
└── config/encryption.key.backup   # Key backups
```

---

## 🔌 Enhanced API Endpoints

### Print Management APIs

#### **Printer Status**
```http
GET /printer/status
Authorization: Bearer <token>

Response:
{
    "online": true,
    "paper_width": "80mm",
    "printer_name": "Default",
    "status": "Ready",
    "last_check": "2024-12-13T14:30:00Z"
}
```

#### **Configure Printer**
```http
POST /printer/configure
Content-Type: application/json

{
    "thermal_printer_name": "EPSON_TM-T88V",
    "paper_width": "80mm",
    "auto_print_enabled": true
}
```

#### **Export Print History**
```http
POST /printer/export
Content-Type: application/json

{
    "order_id": 123,
    "user_id": 5,
    "print_type": "bill",
    "date_from": "2024-12-01",
    "date_to": "2024-12-13"
}

Response: CSV file download
```

### Performance Monitoring APIs

#### **Get Performance Metrics**
```http
GET /api/performance/metrics
Authorization: Bearer <token>

Response:
{
    "uptime": 3600.5,
    "avg_response_time": 0.245,
    "total_requests": 1250,
    "cache_hit_rate": 85.2,
    "memory_usage": [
        {"timestamp": "2024-12-13T14:30:00Z", "percent": 45.2}
    ],
    "error_rate": 0.8
}
```

#### **Get Slow Queries**
```http
GET /api/performance/slow-queries?limit=10

Response:
{
    "slow_queries": [
        {
            "endpoint": "/api/orders",
            "response_time": 3.2,
            "timestamp": "2024-12-13T14:30:00Z",
            "status_code": 200
        }
    ]
}
```

### Security APIs

#### **Check IP Status**
```http
GET /api/security/ip-status/{ip_address}

Response:
{
    "is_blocked": false,
    "blocked_until": null,
    "block_count": 0,
    "failed_attempts": 0
}
```

#### **Security Events**
```http
GET /api/security/events?limit=50

Response:
{
    "events": [
        {
            "event_type": "RATE_LIMIT_VIOLATION",
            "ip": "192.168.1.100",
            "timestamp": "2024-12-13T14:30:00Z",
            "details": "Rate limit exceeded for /api/orders"
        }
    ]
}
```

---

## ⚙️ Configuration Guides

### Thermal Printer Configuration

#### **Step 1: Install Printer Drivers**
1. Install manufacturer-provided drivers for your thermal printer
2. Test printer with Windows test page
3. Ensure printer is set as default

#### **Step 2: Configure in POS**
1. Navigate to `/orders/print-management`
2. Click "Configure Printer"
3. Set printer name and specifications:
   ```
   Printer Name: EPSON_TM-T88V (or your model)
   Paper Width: 80mm (or 58mm for compact printers)
   Font Size: Medium (recommended)
   Auto Print: Enabled
   ```

#### **Step 3: Test Printing**
1. Use "Test Print" functionality
2. Verify bill and KOT print quality
3. Check paper alignment and text clarity
4. Adjust settings if needed

### Performance Monitoring Setup

#### **Enable Performance Monitoring**
Performance monitoring is enabled by default. To configure:

```python
# In app.py, ensure these imports
from utils.performance_monitor import performance_monitor, performance_track

# Monitoring is automatically started when app initializes
```

#### **Configure Alert Thresholds**
```python
# Custom alert thresholds (optional)
performance_monitor.slow_query_threshold = 2.0  # seconds
performance_monitor.memory_warning_threshold = 80  # percent
performance_monitor.error_rate_threshold = 5.0  # percent
```

#### **View Performance Dashboard**
Access performance metrics through:
- Admin dashboard → Performance tab
- Direct API: `/api/performance/metrics`
- Logs: Check `logs/performance.log`

### Security Configuration

#### **Rate Limiting Configuration**
```python
# Global rate limits
RATE_LIMIT_DEFAULT = 100  # requests per minute
RATE_LIMIT_API = 200     # requests per minute for API endpoints
RATE_LIMIT_AUTH = 5      # login attempts per minute

# IP blocking configuration
IP_BLOCK_DURATION = 300  # seconds (5 minutes)
MAX_FAILED_ATTEMPTS = 5   # before blocking
```

#### **CSRF Protection**
```python
# CSRF token is automatically generated
# Ensure all forms include:
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

# For AJAX requests, include header:
headers: {
    'X-CSRF-Token': csrf_token
}
```

#### **Security Headers**
Security headers are automatically added to all responses. Custom headers can be configured in `app.py`:

```python
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    # Additional headers as needed
    return response
```

---

## 📖 Usage Guides

### Thermal Printer Usage

#### **Printing Bills**
1. Navigate to order view: `/orders/view/{order_id}`
2. Click "Print" dropdown button
3. Select "Thermal Bill" for optimized thermal printing
4. Print dialog opens automatically
5. Select printer and adjust copies if needed

#### **Printing KOTs**
1. From order view, click "Print" dropdown
2. Select "KOT" for kitchen order ticket
3. KOT automatically formatted for thermal printer
4. Multiple copies can be printed for different kitchen stations

#### **PDF Invoice Generation**
1. From order view, select "PDF Invoice"
2. Professional PDF invoice generated
3. Can be printed on standard printer
4. Suitable for email attachments and digital records

### Performance Monitoring Usage

#### **Monitoring Dashboard**
1. Access performance metrics at `/dashboard/performance`
2. View real-time metrics:
   - Response times
   - Memory usage
   - Cache performance
   - Error rates
   - Active connections

#### **Performance Alerts**
- Automatic alerts for:
  - Memory usage > 80%
  - Response time > 2 seconds
  - Error rate > 5%
  - High number of slow queries

#### **Optimization Recommendations**
The system provides automatic recommendations:
- Query optimization suggestions
- Cache configuration improvements
- Memory cleanup recommendations
- Database indexing suggestions

### Print History Management

#### **Viewing Print History**
1. Navigate to `/orders/print-management`
2. Click "Print History" tab
3. Filter by:
   - Date range
   - Print type (bill, KOT, invoice)
   - User
   - Success/failure status
4. Export data to CSV for analysis

#### **Print Analytics**
- Track print volumes by period
- Analyze success rates
- Monitor printer performance
- Identify frequently printed orders
- Calculate paper usage

### Security Best Practices

#### **User Security**
- Use strong passwords (minimum 8 characters)
- Enable account lockout after failed attempts
- Regular password updates
- Limited admin access

#### **Network Security**
- Use HTTPS in production
- Configure firewall rules
- Regular security updates
- Monitor access logs

#### **Data Protection**
- Regular database backups
- Encrypted sensitive data
- Access control by role
- Audit trail for all operations

---

## 🔧 Troubleshooting

### Printer Issues

#### **Problem: Print is too wide/small**
**Solution:**
1. Check printer configuration: `/orders/print-management`
2. Verify paper width setting (58mm vs 80mm)
3. Check printer driver settings
4. Test with different font sizes

#### **Problem: Text is not clear**
**Solution:**
1. Check printer head cleaning
2. Verify font size settings
3. Test different print density settings
4. Ensure thermal paper quality

#### **Problem: Colors are printing**
**Solution:**
1. Ensure thermal printer is in monochrome mode
2. Check printer driver settings
3. Verify CSS uses black text only
4. Test with different printer settings

#### **Problem: Print job fails**
**Solution:**
1. Check printer status: `/printer/status`
2. Verify printer connection
3. Check print history for error messages
4. Restart print spooler service

### Performance Issues

#### **Problem: Slow response times**
**Solution:**
1. Check performance metrics: `/api/performance/metrics`
2. Identify slow queries in logs
3. Optimize database queries
4. Increase cache TTL for frequently accessed data

#### **Problem: High memory usage**
**Solution:**
1. Monitor memory usage in dashboard
2. Check for memory leaks in application logs
3. Restart application if needed
4. Optimize data processing

#### **Problem: High error rates**
**Solution:**
1. Check error logs in `logs/performance.log`
2. Identify problematic endpoints
3. Review recent code changes
4. Implement proper error handling

### Security Issues

#### **Problem: Rate limit blocks legitimate users**
**Solution:**
1. Check IP status: `/api/security/ip-status/{ip}`
2. Review rate limit configuration
3. Adjust limits if too restrictive
4. Whitelist trusted IPs if needed

#### **Problem: CSRF token errors**
**Solution:**
1. Ensure CSRF token is included in forms
2. Check token expiration
3. Verify session configuration
4. Clear browser cache and cookies

#### **Problem: Suspicious activity alerts**
**Solution:**
1. Review security event logs
2. Identify source of suspicious activity
3. Block malicious IPs permanently
4. Strengthen authentication requirements

### Common Issues and Solutions

#### **Database Connection Issues**
**Symptoms:** Orders not saving, data not loading
**Solutions:**
1. Check database file permissions
2. Verify database path in config
3. Restart application
4. Check disk space

#### **Cache Issues**
**Symptoms:** Stale data, performance degradation
**Solutions:**
1. Clear cache: `cache_manager.clear()`
2. Verify cache configuration
3. Check memory availability
4. Restart cache service

#### **Session Issues**
**Symptoms:** Users logged out unexpectedly
**Solutions:**
1. Check session configuration
2. Verify secret key
3. Clear session data
4. Check browser cookie settings

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks

#### **Daily**
- Check error logs
- Monitor performance metrics
- Review security events
- Verify printer status

#### **Weekly**
- Database backup
- Performance review
- Security audit
- Print history cleanup

#### **Monthly**
- System updates
- Security patches
- Performance optimization
- Hardware maintenance

### Backup Procedures

#### **Database Backup**
```bash
# Backup SQLite database
cp instance/restaurant_pos.db backups/restaurant_pos_$(date +%Y%m%d).db

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp instance/restaurant_pos.db backups/restaurant_pos_$DATE.db
find backups/ -name "*.db" -mtime +30 -delete
```

#### **Configuration Backup**
```bash
# Backup configuration files
tar -czf backups/config_$(date +%Y%m%d).tar.gz config/ email_config.json
```

### Log Management

#### **Log Files**
- `logs/pos_app.log` - Application logs
- `logs/performance.log` - Performance metrics
- `logs/security.log` - Security events
- `logs/encryption.log` - Encryption operations

#### **Log Rotation**
Logs are automatically rotated when they reach 10MB with 10 backup copies.

### Contact Support

For technical support:
1. Check this documentation first
2. Review application logs
3. Run diagnostic tests
4. Contact support with detailed information

---

## 📋 Feature Checklist

### ✅ Implemented Features

- [x] **Thermal Printer System**
  - [x] 80mm/58mm paper support
  - [x] Print history tracking
  - [x] Print management interface
  - [x] Print analytics
  - [x] Printer configuration

- [x] **Performance Monitoring**
  - [x] Real-time metrics
  - [x] Memory monitoring
  - [x] Cache management
  - [x] Error tracking
  - [x] Performance optimization

- [x] **Security Enhancements**
  - [x] CSRF protection
  - [x] Rate limiting
  - [x] Input sanitization
  - [x] Security event logging
  - [x] IP blocking

- [x] **Print Management**
  - [x] Print job tracking
  - [x] Print statistics
  - [x] Export functionality
  - [x] Print testing
  - [x] Multiple printer support

- [x] **Advanced Order Management**
  - [x] Order merging functionality
  - [x] Order splitting capabilities
  - [x] Order transferring between tables
  - [x] Payment splitting across methods
  - [x] Complete order history tracking
  - [x] Order cancellation with reasons

- [x] **Email Notification System**
  - [x] Multi-provider SMTP support
  - [x] Email queue processing
  - [x] Automated backup notifications
  - [x] Low stock email alerts
  - [x] Daily sales report emails
  - [x] Email history tracking
  - [x] Email template customization

- [x] **Footer Customization System**
  - [x] Dynamic footer generation
  - [x] Business information display
  - [x] Receipt details integration
  - [x] User information display
  - [x] Custom text and messages
  - [x] Complete CSS styling options
  - [x] Real-time preview functionality

- [x] **Data Export & Reporting**
  - [x] Multiple format exports (CSV, PDF, Excel, JSON)
  - [x] Order data exports
  - [x] Inventory data exports
  - [x] GST compliance reports (GSTR-1, GSTR-3B)
  - [x] Employee performance reports
  - [x] Automated export scheduling

- [x] **Multi-Level Caching System**
  - [x] Memory cache (L1) with LRU eviction
  - [x] Disk cache (L2) with persistence
  - [x] TTL-based cache management
  - [x] Cache statistics and monitoring
  - [x] Smart cache invalidation
  - [x] Cache backup and restore

- [x] **Key Management & Encryption**
  - [x] AES-256 encryption for sensitive data
  - [x] Automated key rotation
  - [x] Key backup and recovery
  - [x] Field-level encryption
  - [x] Database encryption support
  - [x] Hardware binding support
  - [x] Complete audit trail

### 🔄 Planned Enhancements

- [ ] **Advanced Analytics**
  - [ ] Sales trend analysis
  - [ ] Customer behavior tracking
  - [ ] Inventory optimization
  - [ ] Staff performance metrics

- [ ] **Mobile App Integration**
  - [ ] Native mobile app
  - [ ] Push notifications
  - [ ] Offline mode
  - [ ] Real-time sync

- [ ] **Cloud Features**
  - [ ] Cloud backup
  - [ ] Multi-location support
  - [ ] Cloud printing
  - [ ] Remote management

---

## 📈 Performance Benchmarks

### System Requirements

#### **Minimum Requirements**
- **CPU**: 2.0 GHz dual-core processor
- **RAM**: 4GB RAM
- **Storage**: 10GB available space
- **Network**: 100 Mbps connection
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+

#### **Recommended Requirements**
- **CPU**: 2.5 GHz quad-core processor
- **RAM**: 8GB RAM
- **Storage**: 20GB available space
- **Network**: 1 Gbps connection
- **Browser**: Latest Chrome/Firefox

### Performance Metrics

#### **Expected Performance**
- **Page Load Time**: < 2 seconds
- **API Response Time**: < 500ms
- **Print Job Time**: < 10 seconds
- **Database Query**: < 100ms (optimized queries)
- **Memory Usage**: < 500MB (typical load)

#### **Scalability**
- **Concurrent Users**: 50+ active users
- **Orders per Hour**: 500+ orders
- **Print Jobs**: 1000+ per day
- **Database Size**: Supports 1M+ orders

---

## 🎯 Conclusion

The Web Cloud POS system has evolved into a comprehensive, enterprise-ready restaurant management solution with advanced features for:

- **Thermal Printer Integration**: Professional printing with detailed tracking
- **Performance Monitoring**: Real-time optimization and alerting
- **Security Enhancement**: Enterprise-grade security features
- **Print Management**: Comprehensive print analytics and management
- **API Integration**: Rich API ecosystem for extensibility

The system is designed for scalability, reliability, and ease of use, making it suitable for restaurants of all sizes from small cafes to large restaurant chains.

### Next Steps

1. **Deploy to Production**: Follow the installation guide for production deployment
2. **Configure Features**: Set up printers, security, and monitoring
3. **Train Staff**: Provide comprehensive training on all features
4. **Monitor Performance**: Use the built-in monitoring tools
5. **Regular Updates**: Keep the system updated with latest features and security patches

For any questions or issues, refer to the troubleshooting section or contact technical support.

---

**Version**: 2.0.0 Advanced Features  
**Last Updated**: December 2024  
**Documentation**: Web Cloud POS Team
