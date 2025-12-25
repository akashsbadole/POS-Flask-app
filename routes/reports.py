from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Order, Payment, MenuItem, Category, Settings
from datetime import datetime, timedelta
from decimal import Decimal
import io
import csv
import json

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    """Reports dashboard"""
    return render_template('reports/index.html')

@reports_bp.route('/daily')
@login_required
def daily_report():
    """Daily sales report"""
    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = datetime.utcnow().date()
    
    # Get orders for the day
    orders = Order.query.filter(
        db.func.date(Order.created_at) == report_date
    ).order_by(Order.created_at.desc()).all()
    
    # Calculate totals
    total_orders = len(orders)
    total_revenue = sum(order.grand_total or 0 for order in orders)
    total_cgst = sum(order.cgst_amount or 0 for order in orders)
    total_sgst = sum(order.sgst_amount or 0 for order in orders)
    
    # Payment breakdown
    payment_breakdown = {}
    for order in orders:
        payments = Payment.get_completed_payments_by_order(order.id)
        for payment in payments:
            mode = payment.payment_mode
            payment_breakdown[mode] = payment_breakdown.get(mode, Decimal('0')) + payment.amount
    
    # Order status breakdown
    status_breakdown = {}
    for order in orders:
        status = order.status
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
    
    return render_template('reports/daily.html',
                        report_date=report_date,
                        orders=orders,
                        total_orders=total_orders,
                        total_revenue=total_revenue,
                        total_cgst=total_cgst,
                        total_sgst=total_sgst,
                        payment_breakdown=payment_breakdown,
                        status_breakdown=status_breakdown)

@reports_bp.route('/monthly')
@login_required
def monthly_report():
    """Monthly sales report"""
    month_str = request.args.get('month', datetime.utcnow().strftime('%Y-%m'))
    
    try:
        year, month = map(int, month_str.split('-'))
    except ValueError:
        year = datetime.utcnow().year
        month = datetime.utcnow().month
    
    # Get orders for the month
    orders = Order.query.filter(
        db.func.extract('year', Order.created_at) == year,
        db.func.extract('month', Order.created_at) == month
    ).order_by(Order.created_at.desc()).all()
    
    # Calculate totals
    total_orders = len(orders)
    total_revenue = sum(order.grand_total or 0 for order in orders)
    total_cgst = sum(order.cgst_amount or 0 for order in orders)
    total_sgst = sum(order.sgst_amount or 0 for order in orders)
    
    # Daily breakdown
    daily_breakdown = {}
    for order in orders:
        day = order.created_at.day
        if day not in daily_breakdown:
            daily_breakdown[day] = {
                'orders': 0,
                'revenue': Decimal('0'),
                'cgst': Decimal('0'),
                'sgst': Decimal('0')
            }
        
        daily_breakdown[day]['orders'] += 1
        daily_breakdown[day]['revenue'] += order.grand_total or 0
        daily_breakdown[day]['cgst'] += order.cgst_amount or 0
        daily_breakdown[day]['sgst'] += order.sgst_amount or 0
    
    return render_template('reports/monthly.html',
                        year=year,
                        month=month,
                        orders=orders,
                        total_orders=total_orders,
                        total_revenue=total_revenue,
                        total_cgst=total_cgst,
                        total_sgst=total_sgst,
                        daily_breakdown=daily_breakdown)

@reports_bp.route('/gstr1')
@login_required
def gstr1_report():
    """GSTR-1 report generation"""
    month_str = request.args.get('month', datetime.utcnow().strftime('%Y-%m'))
    
    try:
        year, month = map(int, month_str.split('-'))
    except ValueError:
        year = datetime.utcnow().year
        month = datetime.utcnow().month
    
    # Get orders for the month (completed orders only)
    orders = Order.query.filter(
        db.func.extract('year', Order.created_at) == year,
        db.func.extract('month', Order.created_at) == month,
        Order.status == 'Completed'
    ).order_by(Order.created_at.desc()).all()
    
    # GSTR-1 calculations
    total_turnover = sum(order.grand_total or 0 for order in orders)
    total_cgst = sum(order.cgst_amount or 0 for order in orders)
    total_sgst = sum(order.sgst_amount or 0 for order in orders)
    total_igst = Decimal('0')  # Interstate sales (if applicable)
    
    # Taxable supplies (inter-state)
    taxable_supplies = total_turnover
    
    return render_template('reports/gstr1.html',
                        year=year,
                        month=month,
                        orders=orders,
                        total_turnover=total_turnover,
                        total_cgst=total_cgst,
                        total_sgst=total_sgst,
                        total_igst=total_igst,
                        taxable_supplies=taxable_supplies)

@reports_bp.route('/export/daily')
@login_required
def export_daily():
    """Export daily report as CSV"""
    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = datetime.utcnow().date()
    
    orders = Order.query.filter(
        db.func.date(Order.created_at) == report_date
    ).order_by(Order.created_at.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Order Number', 'Date', 'Customer', 'Subtotal', 'CGST', 'SGST', 
        'Total', 'Status', 'Payment Mode'
    ])
    
    # Write data
    for order in orders:
        payments = Payment.get_completed_payments_by_order(order.id)
        payment_mode = payments[0].payment_mode if payments else 'N/A'
        
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.customer_name or 'N/A',
            order.subtotal or 0,
            order.cgst_amount or 0,
            order.sgst_amount or 0,
            order.grand_total or 0,
            order.status,
            payment_mode
        ])
    
    # Create response
    output.seek(0)
    filename = f'daily_report_{report_date.strftime("%Y%m%d")}.csv'
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        filename=filename,
        as_attachment=True,
        mimetype='text/csv'
    )

@reports_bp.route('/export/monthly')
@login_required
def export_monthly():
    """Export monthly report as CSV"""
    month_str = request.args.get('month', datetime.utcnow().strftime('%Y-%m'))
    
    try:
        year, month = map(int, month_str.split('-'))
    except ValueError:
        year = datetime.utcnow().year
        month = datetime.utcnow().month
    
    orders = Order.query.filter(
        db.func.extract('year', Order.created_at) == year,
        db.func.extract('month', Order.created_at) == month
    ).order_by(Order.created_at.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Order Number', 'Date', 'Customer', 'Subtotal', 'CGST', 'SGST', 
        'Total', 'Status', 'Payment Mode'
    ])
    
    # Write data
    for order in orders:
        payments = Payment.get_completed_payments_by_order(order.id)
        payment_mode = payments[0].payment_mode if payments else 'N/A'
        
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.customer_name or 'N/A',
            order.subtotal or 0,
            order.cgst_amount or 0,
            order.sgst_amount or 0,
            order.grand_total or 0,
            order.status,
            payment_mode
        ])
    
    # Create response
    output.seek(0)
    filename = f'monthly_report_{year}{month:02d}.csv'
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        filename=filename,
        as_attachment=True,
        mimetype='text/csv'
    )

@reports_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """API endpoint for dashboard data"""
    try:
        # Get date range from query params
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        if not from_date:
            from_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Parse dates
        from_date = datetime.strptime(from_date, '%Y-%m-%d')
        to_date = datetime.strptime(to_date, '%Y-%m-%d')
        
        # Get orders for the period
        orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date
        ).all()
        
        # Calculate stats
        total_sales = sum(order.grand_total or 0 for order in orders)
        total_orders = len(orders)
        cancelled_orders = len([order for order in orders if order.status == 'Cancelled'])
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        # Calculate growth (compare with previous period)
        prev_from_date = from_date - timedelta(days=(to_date - from_date).days + 1)
        prev_to_date = from_date - timedelta(days=1)
        
        prev_orders = Order.query.filter(
            Order.created_at >= prev_from_date,
            Order.created_at <= prev_to_date
        ).all()
        
        prev_total_sales = sum(order.grand_total or 0 for order in prev_orders)
        prev_total_orders = len(prev_orders)
        prev_cancelled_orders = len([order for order in prev_orders if order.status == 'Cancelled'])
        prev_avg_order_value = prev_total_sales / prev_total_orders if prev_total_orders > 0 else 0
        
        # Calculate growth percentages
        sales_growth = ((total_sales - prev_total_sales) / prev_total_sales * 100) if prev_total_sales > 0 else 0
        orders_growth = ((total_orders - prev_total_orders) / prev_total_orders * 100) if prev_total_orders > 0 else 0
        cancelled_growth = ((cancelled_orders - prev_cancelled_orders) / prev_cancelled_orders * 100) if prev_cancelled_orders > 0 else 0
        aov_growth = ((avg_order_value - prev_avg_order_value) / prev_avg_order_value * 100) if prev_avg_order_value > 0 else 0
        
        # Generate daily data for charts
        daily_data = []
        current_date = from_date
        while current_date <= to_date:
            day_orders = [order for order in orders if order.created_at.date() == current_date.date()]
            day_sales = sum(order.grand_total or 0 for order in day_orders)
            day_orders_count = len(day_orders)
            
            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'orders': day_orders_count,
                'sales': float(day_sales),
                'revenue': float(day_sales)
            })
            
            current_date += timedelta(days=1)
        
        # Category-wise sales
        category_data = {}
        for order in orders:
            for order_item in order.order_items:
                category_name = order_item.menu_item.category.name if order_item.menu_item and order_item.menu_item.category else 'Others'
                if category_name not in category_data:
                    category_data[category_name] = 0
                category_data[category_name] += float(order_item.total or 0)
        
        # Payment methods breakdown
        payment_data = {}
        for order in orders:
            payments = Payment.get_completed_payments_by_order(order.id)
            for payment in payments:
                method = payment.payment_mode
                if method not in payment_data:
                    payment_data[method] = 0
                payment_data[method] += float(payment.amount)
        
        return jsonify({
            'stats': {
                'totalSales': float(total_sales),
                'totalOrders': total_orders,
                'cancelledOrders': cancelled_orders,
                'averageOrderValue': float(avg_order_value),
                'salesGrowth': round(sales_growth, 1),
                'ordersGrowth': round(orders_growth, 1),
                'cancelledGrowth': round(cancelled_growth, 1),
                'aovGrowth': round(aov_growth, 1)
            },
            'dailyData': daily_data,
            'categoryData': [{'name': k, 'value': float(v)} for k, v in category_data.items()],
            'paymentData': [{'name': k, 'value': float(v)} for k, v in payment_data.items()]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/monthly')
@login_required
def api_monthly():
    """API endpoint for monthly data"""
    try:
        months = int(request.args.get('months', 12))
        
        monthly_data = []
        for i in range(months):
            # Calculate month start and end
            current_date = datetime.utcnow()
            month_start = datetime(current_date.year, current_date.month, 1) - timedelta(days=30 * i)
            
            if month_start.month == 12:
                month_end = datetime(month_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = datetime(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
            
            # Get orders for the month
            month_orders = Order.query.filter(
                Order.created_at >= month_start,
                Order.created_at <= month_end
            ).all()
            
            total_sales = sum(order.grand_total or 0 for order in month_orders)
            total_orders = len(month_orders)
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'monthName': month_start.strftime('%b %Y'),
                'sales': float(total_sales),
                'orders': total_orders
            })
        
        return jsonify({'monthlyData': monthly_data[::-1]})  # Reverse to show oldest first
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/categories')
@login_required
def api_categories():
    """API endpoint for category-wise sales data"""
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        if not from_date:
            from_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        from_date = datetime.strptime(from_date, '%Y-%m-%d')
        to_date = datetime.strptime(to_date, '%Y-%m-%d')
        
        # Get orders for the period
        orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date
        ).all()
        
        # Aggregate sales by category
        category_sales = {}
        for order in orders:
            for order_item in order.order_items:
                category_name = order_item.menu_item.category.name if order_item.menu_item and order_item.menu_item.category else 'Others'
                if category_name not in category_sales:
                    category_sales[category_name] = {
                        'sales': 0,
                        'quantity': 0,
                        'orders': 0
                    }
                
                category_sales[category_name]['sales'] += float(order_item.total or 0)
                category_sales[category_name]['quantity'] += order_item.quantity or 0
                category_sales[category_name]['orders'] += 1
        
        return jsonify({
            'categories': [
                {
                    'name': name,
                    'sales': float(data['sales']),
                    'quantity': data['quantity'],
                    'orders': data['orders']
                }
                for name, data in category_sales.items()
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/gst')
@login_required
def api_gst():
    """API endpoint for GST data"""
    try:
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        if not from_date:
            from_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        from_date = datetime.strptime(from_date, '%Y-%m-%d')
        to_date = datetime.strptime(to_date, '%Y-%m-%d')
        
        # Get orders for the period
        orders = Order.query.filter(
            Order.created_at >= from_date,
            Order.created_at <= to_date,
            Order.status == 'Completed'
        ).all()
        
        # Calculate GST totals
        total_turnover = sum(order.grand_total or 0 for order in orders)
        total_cgst = sum(order.cgst_amount or 0 for order in orders)
        total_sgst = sum(order.sgst_amount or 0 for order in orders)
        total_igst = 0  # IGST not implemented in current Order model
        
        # Monthly GST breakdown
        monthly_gst = {}
        for order in orders:
            month_key = order.created_at.strftime('%Y-%m')
            if month_key not in monthly_gst:
                monthly_gst[month_key] = {
                    'cgst': 0,
                    'sgst': 0,
                    'igst': 0,
                    'total': 0
                }
            
            monthly_gst[month_key]['cgst'] += order.cgst_amount or 0
            monthly_gst[month_key]['sgst'] += order.sgst_amount or 0
            monthly_gst[month_key]['igst'] += 0  # IGST not implemented in current Order model
            monthly_gst[month_key]['total'] += order.grand_total or 0
        
        return jsonify({
            'gstSummary': {
                'totalTurnover': float(total_turnover),
                'totalCGST': float(total_cgst),
                'totalSGST': float(total_sgst),
                'totalIGST': float(total_igst),
                'totalTax': float(total_cgst + total_sgst + total_igst)
            },
            'monthlyGST': [
                {
                    'month': month,
                    'monthName': datetime.strptime(month, '%Y-%m').strftime('%b %Y'),
                    'cgst': float(data['cgst']),
                    'sgst': float(data['sgst']),
                    'igst': float(data['igst']),
                    'total': float(data['total'])
                }
                for month, data in sorted(monthly_gst.items())
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
