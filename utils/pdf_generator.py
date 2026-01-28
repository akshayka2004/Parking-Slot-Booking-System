"""
PDF Receipt Generator for Parking Slot Booking System
Generates professional booking receipts in PDF format
"""

from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime


def generate_booking_receipt(booking):
    """
    Generate a PDF receipt for a booking
    
    Args:
        booking: Booking object with all booking details
        
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=10,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=5
    )
    
    # Build content
    content = []
    
    # Header
    content.append(Paragraph("🅿️ ParkHub", title_style))
    content.append(Paragraph("AI-Powered Smart Parking System", subtitle_style))
    content.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563eb')))
    content.append(Spacer(1, 10))
    
    # Receipt Title
    content.append(Paragraph("BOOKING RECEIPT", ParagraphStyle(
        'ReceiptTitle',
        fontSize=18,
        textColor=colors.HexColor('#16a34a'),
        alignment=TA_CENTER,
        spaceAfter=20
    )))
    
    # Booking Details Table
    content.append(Paragraph("Booking Details", heading_style))
    
    slot_name = booking.slot.slot_number.replace('slot_', 'Slot ') if booking.slot else 'N/A'
    
    booking_data = [
        ['Booking ID:', f'#{booking.id}'],
        ['Status:', booking.status.upper()],
        ['Booking Date:', booking.created_at.strftime('%B %d, %Y at %I:%M %p')],
    ]
    
    booking_table = Table(booking_data, colWidths=[150, 300])
    booking_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
    ]))
    content.append(booking_table)
    content.append(Spacer(1, 15))
    
    # Parking Details
    content.append(Paragraph("Parking Details", heading_style))
    
    parking_data = [
        ['Slot Number:', slot_name],
        ['Vehicle Number:', booking.vehicle_number],
        ['Start Time:', booking.start_time.strftime('%B %d, %Y at %I:%M %p')],
        ['End Time:', booking.end_time.strftime('%B %d, %Y at %I:%M %p')],
        ['Duration:', f'{int(booking.duration_hours)} hour(s)'],
    ]
    
    parking_table = Table(parking_data, colWidths=[150, 300])
    parking_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#111827')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fdf4')),
    ]))
    content.append(parking_table)
    content.append(Spacer(1, 15))
    
    # Payment Details
    content.append(Paragraph("Payment Details", heading_style))
    
    payment_data = [
        ['Hourly Rate:', f'₹{booking.hourly_rate:.2f}'],
        ['Duration:', f'{int(booking.duration_hours)} hour(s)'],
        ['', ''],
        ['Total Amount:', f'₹{booking.total_price:.2f}'],
    ]
    
    payment_table = Table(payment_data, colWidths=[150, 300])
    payment_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 1), 'Helvetica'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 2), 11),
        ('FONTSIZE', (0, 3), (-1, 3), 14),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('TEXTCOLOR', (1, 3), (1, 3), colors.HexColor('#16a34a')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 3), (-1, 3), 1, colors.HexColor('#d1d5db')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef3c7')),
    ]))
    content.append(payment_table)
    content.append(Spacer(1, 30))
    
    # Footer
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#d1d5db')))
    content.append(Spacer(1, 10))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    content.append(Paragraph(
        f"Receipt generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        footer_style
    ))
    content.append(Paragraph(
        "Thank you for using ParkHub - AI-Powered Smart Parking System",
        footer_style
    ))
    content.append(Paragraph(
        "Please keep this receipt for your records.",
        footer_style
    ))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    
    return buffer
