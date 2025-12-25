"""
Data Export Utility for Flask POS Application
Handles exporting data to various formats including PDF, CSV, and Excel
"""

import os
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import current_app
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

class DataExporter:
    """Data export manager"""
    
    def __init__(self, export_folder: str = 'exports'):
        self.export_folder = export_folder
        self.ensure_export_folder()
    
    def ensure_export_folder(self):
        """Ensure export folder exists"""
        if not os.path.exists(self.export_folder):
            os.makedirs(self.export_folder)
        
        # Create subfolders
        subfolders = ['orders', 'reports', 'inventory', 'menu']
        for subfolder in subfolders:
            path = os.path.join(self.export_folder, subfolder)
            if not os.path.exists(path):
                os.makedirs(path)
    
    def export_orders_to_csv(self, orders: List[Dict[str, Any]], 
                           filename: str = None) -> str:
        """Export orders to CSV format"""
        if not filename:
            filename = f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.export_folder, 'orders', filename)
        
        # Define CSV headers
        headers = [
            'Order Number', 'Order Type', 'Customer Name', 'Customer Mobile',
            'Table', 'Subtotal', 'CGST', 'SGST', 'Discount', 'Grand Total',
            'Payment Status', 'Created At', 'Items Count'
        ]
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                
                for order in orders:
                    row = [
                        order.get('order_number', ''),
                        order.get('order_type', ''),
                        order.get('customer_name', 'Walk-in'),
                        order.get('customer_mobile', ''),
                        order.get('table_name', ''),
                        order.get('subtotal', 0),
                        order.get('cgst', 0),
                        order.get('sgst', 0),
                        order.get('discount_amount', 0),
                        order.get('grand_total', 0),
                        order.get('payment_status', 'Pending'),
                        order.get('created_at', ''),
                        len(order.get('items', []))
                    ]
                    writer.writerow(row)
            
            return filepath
            
        except Exception as e:
            print(f"Error exporting orders to CSV: {e}")
            return None
    
    def export_orders_to_pdf(self, orders: List[Dict[str, Any]], 
                           filename: str = None) -> str:
        """Export orders to PDF format"""
        if not filename:
            filename = f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        filepath = os.path.join(self.export_folder, 'orders', filename)
        
        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center
            )
            
            story.append(Paragraph("Orders Report", title_style))
            story.append(Spacer(1, 12))
            
            # Summary
            total_orders = len(orders)
            total_revenue = sum(order.get('grand_total', 0) for order in orders)
            
            summary_data = [
                ['Total Orders', str(total_orders)],
                ['Total Revenue', f"₹{total_revenue:.2f}"],
                ['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Orders Table
            headers = [
                'Order #', 'Type', 'Customer', 'Table', 'Subtotal', 
                'GST', 'Total', 'Status'
            ]
            
            data = [headers]
            for order in orders[:50]:  # Limit to 50 orders per PDF
                data.append([
                    order.get('order_number', ''),
                    order.get('order_type', ''),
                    order.get('customer_name', 'Walk-in'),
                    order.get('table_name', ''),
                    f"₹{order.get('subtotal', 0):.2f}",
                    f"₹{(order.get('cgst', 0) + order.get('sgst', 0)):.2f}",
                    f"₹{order.get('grand_total', 0):.2f}",
                    order.get('payment_status', 'Pending')
                ])
            
            table = Table(data, colWidths=[0.8*inch]*8)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8)
            ]))
            
            story.append(table)
            
            if len(orders) > 50:
                story.append(Spacer(1, 12))
                note = Paragraph(f"Note: Showing first 50 orders out of {len(orders)} total orders", 
                              styles['Normal'])
                story.append(note)
            
            doc.build(story)
            return filepath
            
        except Exception as e:
            print(f"Error exporting orders to PDF: {e}")
            return None
    
    def export_inventory_to_csv(self, items: List[Dict[str, Any]], 
                              filename: str = None) -> str:
        """Export inventory to CSV format"""
        if not filename:
            filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.export_folder, 'inventory', filename)
        
        headers = [
            'Item Name', 'Category', 'Current Stock', 'Min Stock Level', 'Unit',
            'Price', 'Cost Price', 'Status', 'Last Updated'
        ]
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                
                for item in items:
                    row = [
                        item.get('name', ''),
                        item.get('category_name', ''),
                        item.get('stock_quantity', 0),
                        item.get('min_stock_level', 0),
                        item.get('unit', ''),
                        item.get('price', 0),
                        item.get('cost_price', 0),
                        'Low Stock' if item.get('is_low_stock') else 'In Stock',
                        item.get('updated_at', '')
                    ]
                    writer.writerow(row)
            
            return filepath
            
        except Exception as e:
            print(f"Error exporting inventory to CSV: {e}")
            return None
    
    def export_menu_to_csv(self, menu_items: List[Dict[str, Any]], 
                         filename: str = None) -> str:
        """Export menu items to CSV format"""
        if not filename:
            filename = f"menu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.export_folder, 'menu', filename)
        
        headers = [
            'Item Name', 'Category', 'Description', 'Price', 'Cost Price',
            'Stock Quantity', 'Unit', 'Min Stock Level', 'Status', 'Image Path'
        ]
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                
                for item in menu_items:
                    row = [
                        item.get('name', ''),
                        item.get('category_name', ''),
                        item.get('description', ''),
                        item.get('price', 0),
                        item.get('cost_price', 0),
                        item.get('stock_quantity', 0),
                        item.get('unit', ''),
                        item.get('min_stock_level', 0),
                        'Active' if item.get('is_active') else 'Inactive',
                        item.get('image_path', '')
                    ]
                    writer.writerow(row)
            
            return filepath
            
        except Exception as e:
            print(f"Error exporting menu to CSV: {e}")
            return None
    
    def export_sales_report_to_csv(self, report_data: Dict[str, Any], 
                                filename: str = None) -> str:
        """Export sales report to CSV format"""
        if not filename:
            filename = f"sales_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.export_folder, 'reports', filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write summary
                writer.writerow(['Sales Report Summary'])
                writer.writerow(['Date', report_data.get('date', '')])
                writer.writerow(['Total Orders', report_data.get('total_orders', 0)])
                writer.writerow(['Total Revenue', f"₹{report_data.get('total_revenue', 0):.2f}"])
                writer.writerow(['CGST', f"₹{report_data.get('cgst_total', 0):.2f}"])
                writer.writerow(['SGST', f"₹{report_data.get('sgst_total', 0):.2f}"])
                writer.writerow(['Total GST', f"₹{report_data.get('total_gst', 0):.2f}"])
                writer.writerow([])
                
                # Write item details if available
                if report_data.get('items'):
                    writer.writerow(['Item Sales Details'])
                    item_headers = ['Item Name', 'Category', 'Quantity Sold', 'Revenue']
                    writer.writerow(item_headers)
                    
                    for item in report_data['items']:
                        writer.writerow([
                            item.get('name', ''),
                            item.get('category_name', ''),
                            item.get('quantity_sold', 0),
                            f"₹{item.get('revenue', 0):.2f}"
                        ])
            
            return filepath
            
        except Exception as e:
            print(f"Error exporting sales report to CSV: {e}")
            return None
    
    def export_gstr1_to_csv(self, gstr1_data: Dict[str, Any], 
                           filename: str = None) -> str:
        """Export GSTR-1 report to CSV format"""
        if not filename:
            filename = f"gstr1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.export_folder, 'reports', filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # GSTR-1 Format
                headers = [
                    'Invoice Number', 'Invoice Date', 'Customer Name', 'Customer GSTIN',
                    'Taxable Value', 'CGST Rate', 'CGST Amount', 'SGST Rate', 
                    'SGST Amount', 'Total Tax', 'Total Amount', 'Place of Supply'
                ]
                
                writer.writerow(headers)
                
                for invoice in gstr1_data.get('invoices', []):
                    writer.writerow([
                        invoice.get('invoice_number', ''),
                        invoice.get('invoice_date', ''),
                        invoice.get('customer_name', ''),
                        invoice.get('customer_gstin', ''),
                        invoice.get('taxable_value', 0),
                        invoice.get('cgst_rate', 2.5),
                        invoice.get('cgst_amount', 0),
                        invoice.get('sgst_rate', 2.5),
                        invoice.get('sgst_amount', 0),
                        invoice.get('total_tax', 0),
                        invoice.get('total_amount', 0),
                        invoice.get('place_of_supply', '')
                    ])
            
            return filepath
            
        except Exception as e:
            print(f"Error exporting GSTR-1 to CSV: {e}")
            return None
    
    def export_to_excel(self, data: List[Dict[str, Any]], 
                      sheet_name: str = 'Data', 
                      filename: str = None) -> str:
        """Export data to Excel format"""
        if not filename:
            filename = f"{sheet_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        filepath = os.path.join(self.export_folder, filename)
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Create Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return filepath
            
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return None
    
    def create_custom_report(self, data: Dict[str, Any], 
                          report_type: str = 'custom') -> str:
        """Create custom report with mixed data"""
        filename = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.export_folder, 'reports', filename)
        
        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=20,
                alignment=1
            )
            
            title = data.get('title', f'{report_type.title()} Report')
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 12))
            
            # Report Period
            if data.get('period'):
                period_style = ParagraphStyle(
                    'Period',
                    parent=styles['Normal'],
                    fontSize=12,
                    alignment=1,
                    spaceAfter=20
                )
                story.append(Paragraph(f"Period: {data['period']}", period_style))
            
            # Summary Section
            if data.get('summary'):
                summary_title = Paragraph("Summary", styles['Heading2'])
                story.append(summary_title)
                story.append(Spacer(1, 12))
                
                summary_data = []
                for key, value in data['summary'].items():
                    summary_data.append([key.title(), str(value)])
                
                summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(summary_table)
                story.append(Spacer(1, 20))
            
            # Charts Section (placeholder for future implementation)
            if data.get('charts'):
                charts_title = Paragraph("Charts & Graphs", styles['Heading2'])
                story.append(charts_title)
                story.append(Spacer(1, 12))
                
                charts_note = Paragraph("Charts will be displayed here in future versions", 
                                   styles['Normal'])
                story.append(charts_note)
                story.append(Spacer(1, 20))
            
            # Detailed Data Section
            if data.get('details'):
                details_title = Paragraph("Detailed Data", styles['Heading2'])
                story.append(details_title)
                story.append(Spacer(1, 12))
                
                # Create table from details data
                if data['details']:
                    headers = list(data['details'][0].keys()) if data['details'] else []
                    table_data = [headers]
                    
                    for item in data['details'][:100]:  # Limit to 100 items
                        row = [str(item.get(header, '')) for header in headers]
                        table_data.append(row)
                    
                    # Calculate column widths
                    num_cols = len(headers)
                    col_width = (6.5 * inch) / num_cols if num_cols > 0 else inch
                    
                    detail_table = Table(table_data, colWidths=[col_width]*num_cols)
                    detail_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 1), (-1, -1), 7)
                    ]))
                    
                    story.append(detail_table)
            
            # Footer
            if len(data.get('details', [])) > 100:
                story.append(Spacer(1, 12))
                footer_note = Paragraph(f"Note: Showing first 100 records out of {len(data['details'])} total records", 
                                    styles['Normal'])
                story.append(footer_note)
            
            # Generated timestamp
            story.append(Spacer(1, 20))
            timestamp = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                               styles['Normal'])
            story.append(timestamp)
            
            doc.build(story)
            return filepath
            
        except Exception as e:
            print(f"Error creating custom report: {e}")
            return None
    
    def cleanup_old_exports(self, days: int = 7):
        """Clean up export files older than specified days"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            for root, dirs, files in os.walk(self.export_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        print(f"Removed old export file: {file_path}")
                        
        except Exception as e:
            print(f"Error cleaning up old exports: {e}")
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """Get list of exported files with metadata"""
        exports = []
        
        try:
            for root, dirs, files in os.walk(self.export_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    stat = os.stat(file_path)
                    
                    exports.append({
                        'filename': file,
                        'path': file_path,
                        'size': self._format_file_size(stat.st_size),
                        'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        'type': self._get_file_type(file)
                    })
            
            # Sort by creation date (newest first)
            exports.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            print(f"Error getting export history: {e}")
        
        return exports
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def _get_file_type(self, filename: str) -> str:
        """Get file type from filename"""
        if filename.endswith('.pdf'):
            return 'PDF'
        elif filename.endswith('.csv'):
            return 'CSV'
        elif filename.endswith('.xlsx'):
            return 'Excel'
        else:
            return 'Unknown'

# Global data exporter instance
data_exporter = DataExporter()
