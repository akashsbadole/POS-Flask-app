# Flask POS - Restaurant Management System

A modern, web-based Point of Sale (POS) system for restaurants with GST compliance, built using Flask, Alpine.js, and Bootstrap.

## 🚀 Features

### Core Features

- **Multi-Order Management**: Handle multiple orders simultaneously with tabbed interface
- **GST-Compliant Billing**: Automatic tax calculations (2.5% CGST + 2.5% SGST)
- **Menu Management**: Full CRUD operations with categories and stock tracking
- **Table Management**: Visual table layout and status tracking
- **Inventory Management**: Stock tracking with low-stock alerts
- **KOT System**: Real-time Kitchen Order Ticket management
- **GST Reports**: GSTR-1 and GSTR-3B compliance reports
- **Export Functionality**: CSV and PDF export capabilities
- **Mobile Responsive**: Works seamlessly on all devices

### Technical Features

- **Modern Stack**: Flask 2.3.3 + Alpine.js + Bootstrap 5
- **Database**: SQLAlchemy with SQLite/PostgreSQL support
- **Real-time Updates**: Auto-refresh KOT system
- **Security**: CSRF protection, session management
- **ES5 Compatible**: JavaScript works on all browsers

## 📋 Requirements

### System Requirements

- Python 3.8+
- Modern web browser (Chrome, Firefox, Safari, Edge)
- 2GB RAM minimum
- 100MB disk space

### Python Dependencies

```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-WTF==1.1.1
WTForms==3.0.1
Werkzeug==2.3.7
ReportLab==4.0.4
Pillow==10.0.1
python-dotenv==1.0.0
```

## 🛠️ Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd posmvp/web_cloud
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python init_db.py
```

### 5. Run Application

```bash
python app.py
```

### 6. Access Application

Open browser and navigate to: `http://localhost:5000`

## 🔑 Default Login

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Important**: Change the default password after first login!

## 📱 Usage

### Getting Started

1. **Login**: Use default credentials to access the system
2. **Dashboard**: View overview of orders, sales, and inventory
3. **Orders**: Create and manage customer orders
4. **Menu**: Add/edit menu items and categories
5. **Tables**: Manage restaurant tables and seating
6. **KOT**: Monitor kitchen orders in real-time
7. **Inventory**: Track stock levels and manage supplies
8. **Reports**: Generate GST-compliant reports

### Order Management

1. Select order type (Dine-in/Takeaway/Delivery)
2. Choose table (for dine-in orders)
3. Add items from menu categories
4. Apply discounts if needed
5. Save order and proceed to payment
6. Print KOT automatically sent to kitchen

### GST Compliance

- Automatic tax calculation at 5% (2.5% CGST + 2.5% SGST)
- GST reports for filing (GSTR-1, GSTR-3B)
- Tax breakdown on receipts
- Export data in GST-compliant format

## 🧪 Testing

Run the test suite to verify installation:

```bash
python test_app.py
```

This will run:

- Database connection tests
- Model validation tests
- Route functionality tests
- Template and static file checks
- GST calculation verification

## 📊 Reports

### Available Reports

- **Daily Sales**: Day-wise sales summary with GST
- **Monthly Sales**: Monthly sales analysis
- **GSTR-1**: Outward supplies report
- **GSTR-3B**: Tax summary and ITC details
- **Item-wise**: Sales by menu items
- **Category-wise**: Sales by categories

### Export Options

- **CSV**: For Excel/Google Sheets
- **PDF**: Print-ready reports
- **Print**: Direct printer output

## 🔧 Configuration

### Database Settings

Edit `config.py` to change database:

```python
# SQLite (default)
SQLALCHEMY_DATABASE_URI = 'sqlite:///restaurant_pos.db'

# PostgreSQL
SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/pos_db'

# MySQL
SQLALCHEMY_DATABASE_URI = 'mysql://user:password@localhost/pos_db'
```

### Restaurant Settings

Update restaurant information in Settings menu:

- Restaurant name and address
- GST number
- Contact details
- Receipt footer
- Tax rates

## 📱 Mobile Usage

The application is fully mobile-responsive:

### Phone/Tablet Features

- Touch-friendly interface
- Swipe gestures for order tabs
- Optimized layouts
- Mobile KOT view

### Recommended Devices

- **Counter**: Desktop/Laptop
- **Floor Staff**: Tablets/iPads
- **Kitchen**: Large monitor/tablet
- **Mobile**: Managers on the go

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Error

```bash
# Check database file exists
ls -la restaurant_pos.db

# Reinitialize database
python init_db.py
```

#### Missing Dependencies

```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

#### JavaScript Errors

- Check browser console (F12)
- Ensure all static files are loading
- Clear browser cache

#### Permission Issues

```bash
# Linux/Mac - Fix permissions
chmod +x init_db.py
chmod +x app.py

# Windows - Run as administrator
```

### Log Files

Check application logs in:

- Console output (when running `python app.py`)
- Browser developer tools
- Web server logs (if using production server)

## 🔄 Updates

### Updating the Application

1. **Backup Database**: Copy `restaurant_pos.db`
2. **Update Code**: Pull latest changes
3. **Install Dependencies**: `pip install -r requirements.txt`
4. **Run Migrations**: If database schema changed
5. **Test**: Run `python test_app.py`

### Data Backup

Regular backups are recommended:

```bash
# Backup database
cp restaurant_pos.db backup/restaurant_pos_$(date +%Y%m%d).db

# Backup settings
cp config.py backup/config_$(date +%Y%m%d).py
```

## 🛡️ Security

### Production Deployment

1. **Change Default Password**: Immediately update admin password
2. **Use HTTPS**: Configure SSL certificate
3. **Environment Variables**: Use .env file for secrets
4. **Regular Updates**: Keep dependencies updated
5. **Firewall**: Restrict access to production server

### Security Features

- CSRF protection enabled
- Session management
- Password hashing
- SQL injection protection
- XSS prevention
- Input validation

## 📞 Support

### Getting Help

1. **Documentation**: Check this README first
2. **Logs**: Review application logs
3. **Test Suite**: Run `python test_app.py`
4. **GitHub Issues**: Report bugs and feature requests

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Flask**: Web framework
- **Alpine.js**: Reactive JavaScript framework
- **Bootstrap**: UI framework
- **Font Awesome**: Icons
- **ReportLab**: PDF generation
- **SQLAlchemy**: Database ORM

---

**Version**: 1.0.0  
**Last Updated**: December 2024  
**Developer**: Restaurant POS Team
