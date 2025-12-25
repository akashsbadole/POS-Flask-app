"""
PDF Invoice Generator for Restaurant POS System
Generates GST-compliant invoices with proper formatting
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

class PDFInvoiceGenerator:
    """Generate professional GST-compliant invoices"""
    
    def __init__(self, output_path: str = 'exports/invoices/'):
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
    def _setup_custom_styles(self):
        """Setup custom styles for invoice"""
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='RightAlign',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT
        ))
        
        self.styles.add(ParagraphStyle(
            name='CenterAlign',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='BoldText',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8
        ))

    def generate_invoice(self, order_data: Dict, settings: Dict = None) -> str:
        """Generate PDF invoice and return file path"""
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"invoice_{order_data['order_number']}_{timestamp}.pdf"
        filepath = os.path.join(self.output_path, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Build story (content)
        story = []
        
        # Add invoice content
        story.extend(self._build_invoice_header(order_data, settings))
        story.extend(self._build_billing_info(order_data))
        story.extend(self._build_order_items_table(order_data))
        story.extend(self._build_tax_breakdown(order_data))
        story.extend(self._build_payment_info(order_data))
        story.extend(self._build_footer(order_data, settings))
        
        # Build PDF
        doc.build(story)
        
        return filepath

    def _build_invoice_header(self, order_data: Dict, settings: Dict) -> List:
        """Build invoice header section"""
        elements = []
        
        # Restaurant Info
        restaurant_name = settings.get('restaurant_name', 'Restaurant POS') if settings else 'Restaurant POS'
        restaurant_address = settings.get('restaurant_address', '') if settings else ''
        restaurant_phone = settings.get('restaurant_phone', '') if settings else ''
        gstin = settings.get('gst_number', '') if settings else ''
        
        elements.append(Paragraph(restaurant_name, self.styles['InvoiceTitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Restaurant details
        if restaurant_address:
            elements.append(Paragraph(restaurant_address, self.styles['CenterAlign']))
        if restaurant_phone:
            elements.append(Paragraph(f"Phone: {restaurant_phone}", self.styles['CenterAlign']))
        if gstin:
            elements.append(Paragraph(f"GSTIN: {gstin}", self.styles['CenterAlign']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Invoice details table
        invoice_data = [
            ['Invoice Number:', order_data['order_number']],
            ['Invoice Date:', self._format_date(order_data['created_at'])],
            ['Order Type:', order_data['order_type']],
            ['Table:', order_data.get('table_number', 'N/A')]
        ]
        
        invoice_table = Table(invoice_data, colWidths=[2*inch, 4*inch])
        invoice_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(invoice_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _build_billing_info(self, order_data: Dict) -> List:
        """Build billing information section"""
        elements = []
        
        # Customer information
        customer_name = order_data.get('customer_name', 'Walk-in Customer')
        customer_mobile = order_data.get('customer_mobile', 'N/A')
        
        billing_info = [
            ['Bill To:', ''],
            ['Name:', customer_name],
            ['Mobile:', customer_mobile],
            ['Order Type:', order_data['order_type']],
            ['Table:', order_data.get('table_number', 'N/A')]
        ]
        
        billing_table = Table(billing_info, colWidths=[1.5*inch, 4.5*inch])
        billing_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(billing_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Special instructions
        special_instructions = order_data.get('special_instructions')
        if special_instructions:
            elements.append(Paragraph("Special Instructions:", self.styles['BoldText']))
            elements.append(Paragraph(special_instructions, self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        return elements

    def _build_order_items_table(self, order_data: Dict) -> List:
        """Build order items table"""
        elements = []
        
        elements.append(Paragraph("Order Items", self.styles['BoldText']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Table headers
        headers = ['#', 'Item Name', 'Qty', 'Price', 'Total']
        data = [headers]
        
        # Add items
        for i, item in enumerate(order_data['items'], 1):
            row_data = [
                str(i),
                item['item_name'],
                str(item['quantity']),
                f"₹{item['price']:.2f}",
                f"₹{item['total']:.2f}"
            ]
            data.append(row_data)
            
            # Add special instructions if any
            if item.get('special_instructions'):
                instruction_row = ['', f"Note: {item['special_instructions']}", '', '', '']
                data.append(instruction_row)
        
        # Create table
        col_widths = [0.5*inch, 3.5*inch, 0.8*inch, 1.2*inch, 1.2*inch]
        items_table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Style the table
        items_table.setStyle(TableStyle([
            # Header styling
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
            
            # Data styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Sr. No.
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),   # Item Name
            ('ALIGN', (2, 1), (4, -1), 'RIGHT'),  # Qty, Price, Total
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            
            # Grid lines
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _build_tax_breakdown(self, order_data: Dict) -> List:
        """Build tax breakdown section"""
        elements = []
        
        # Tax calculation table
        tax_data = [
            ['Subtotal:', f"₹{order_data['subtotal']:.2f}"],
            ['CGST (2.5%):', f"₹{order_data['cgst_amount']:.2f}"],
            ['SGST (2.5%):', f"₹{order_data['sgst_amount']:.2f}"],
        ]
        
        # Add discount if applicable
        if order_data.get('discount_amount', 0) > 0:
            tax_data.append(['Discount:', f"-₹{order_data['discount_amount']:.2f}"])
        
        # Add service charge if applicable
        if order_data.get('service_charge', 0) > 0:
            tax_data.append(['Service Charge:', f"₹{order_data['service_charge']:.2f}"])
        
        # Add delivery charges if applicable
        if order_data.get('delivery_charges', 0) > 0:
            tax_data.append(['Delivery Charges:', f"₹{order_data['delivery_charges']:.2f}"])
        
        # Add separator
        tax_data.append(['=' * 30, '=' * 20])
        
        # Grand total
        tax_data.append(['Grand Total:', f"₹{order_data['grand_total']:.2f}"])
        
        tax_table = Table(tax_data, colWidths=[3*inch, 2*inch])
        tax_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -2), (-1, -1), 12),
            ('TEXTCOLOR', (0, -2), (-1, -1), colors.darkblue),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.grey),
        ]))
        
        elements.append(tax_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _build_payment_info(self, order_data: Dict) -> List:
        """Build payment information section"""
        elements = []
        
        payments = order_data.get('payments', [])
        if payments:
            elements.append(Paragraph("Payment Details", self.styles['BoldText']))
            elements.append(Spacer(1, 0.1*inch))
            
            payment_data = [['Mode', 'Amount', 'Date', 'Reference']]
            for payment in payments:
                payment_data.append([
                    payment['payment_mode'],
                    f"₹{payment['amount']:.2f}",
                    self._format_date(payment['created_at']),
                    payment.get('reference_number', 'N/A')
                ])
            
            payment_table = Table(payment_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 2*inch])
            payment_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (0, 1), (2, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'LEFT'),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(payment_table)
            elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _build_footer(self, order_data: Dict, settings: Dict) -> List:
        """Build invoice footer"""
        elements = []
        
        # Add separator
        elements.append(Spacer(1, 0.5*inch))
        
        # Footer text
        if settings:
            footer_text = settings.get('receipt_footer', 'Thank you for visiting!')
            if footer_text:
                elements.append(Paragraph(footer_text, self.styles['CenterAlign']))
                elements.append(Spacer(1, 0.1*inch))
        
        # GST information
        elements.append(Paragraph("Tax Summary", self.styles['BoldText']))
        tax_summary = [
            f"Taxable Amount: ₹{order_data['subtotal']:.2f}",
            f"CGST (2.5%): ₹{order_data['cgst_amount']:.2f}",
            f"SGST (2.5%): ₹{order_data['sgst_amount']:.2f}",
            f"Total GST: ₹{order_data['cgst_amount'] + order_data['sgst_amount']:.2f}"
        ]
        
        for tax_line in tax_summary:
            elements.append(Paragraph(tax_line, self.styles['SmallText']))
        
        elements.append(Spacer(1, 0.1*inch))
        
        # Terms and conditions
        terms = [
            "1. This is a computer-generated invoice.",
            "2. GST is calculated as per applicable rates.",
            "3. Please check the order details before payment.",
            "4. For any queries, contact restaurant management."
        ]
        
        elements.append(Paragraph("Terms & Conditions", self.styles['BoldText']))
        for term in terms:
            elements.append(Paragraph(term, self.styles['SmallText']))
        
        return elements

    def _format_date(self, date_str: str) -> str:
        """Format date string"""
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_obj.strftime('%d/%m/%Y %I:%M %p')
        except:
            return date_str

    def generate_kot_pdf(self, order_data: Dict, settings: Dict = None) -> str:
        """Generate KOT PDF and return file path"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"kot_{order_data['order_number']}_{timestamp}.pdf"
        filepath = os.path.join(self.output_path, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        story = []
        
        # KOT Header
        restaurant_name = settings.get('restaurant_name', 'Restaurant POS') if settings else 'Restaurant POS'
        story.append(Paragraph("KITCHEN ORDER TICKET", self.styles['InvoiceTitle']))
        story.append(Paragraph(restaurant_name, self.styles['CenterAlign']))
        story.append(Spacer(1, 0.2*inch))
        
        # Order info
        kot_info = [
            ['Order #:', order_data['order_number']],
            ['Date:', self._format_date(order_data['created_at'])],
            ['Table:', order_data.get('table_number', 'N/A')],
            ['Type:', order_data['order_type']]
        ]
        
        kot_table = Table(kot_info, colWidths=[1.5*inch, 4.5*inch])
        kot_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(kot_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Items
        kot_items = [['Qty', 'Item']]
        for item in order_data['items']:
            kot_items.append([str(item['quantity']), item['item_name']])
            if item.get('special_instructions'):
                kot_items.append(['', f"Note: {item['special_instructions']}"])
        
        kot_items_table = Table(kot_items, colWidths=[1*inch, 5*inch])
        kot_items_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.grey),
        ]))
        
        story.append(kot_items_table)
        
        # Special instructions
        if order_data.get('special_instructions'):
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("Special Instructions:", self.styles['BoldText']))
            story.append(Paragraph(order_data['special_instructions'], self.styles['Normal']))
        
        doc.build(story)
        return filepath

def generate_invoice_pdf(order_data: Dict, settings: Dict = None) -> str:
    """Convenience function to generate invoice PDF"""
    generator = PDFInvoiceGenerator()
    return generator.generate_invoice(order_data, settings)

def generate_kot_pdf(order_data: Dict, settings: Dict = None) -> str:
    """Convenience function to generate KOT PDF"""
    generator = PDFInvoiceGenerator()
    return generator.generate_kot_pdf(order_data, settings)
