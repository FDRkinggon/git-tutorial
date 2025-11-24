from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from datetime import datetime
import os
def generate_invoice_pdf(invoice, user):
    """Génère un PDF pour une facture ou un devis"""
    # Chemin du fichier PDF
    filename = f"{invoice.number.replace('/', '-')}.pdf"
    filepath = os.path.join('generated_pdfs', filename)
    # Créer le document
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor(user.template_color),
        spaceAfter=30
    )
    # Template sélectionné
    if user.default_template == 'modern':
        elements = generate_modern_template(invoice, user, styles, title_style)
    elif user.default_template == 'classic':
        elements = generate_classic_template(invoice, user, styles, title_style)
    else:
        elements = generate_minimal_template(invoice, user, styles, title_style)
    # Construction du PDF
    doc.build(elements)
    return filepath
def generate_modern_template(invoice, user, styles, title_style):
    """Template moderne avec design épuré"""
    elements = []
    # En-tête avec logo
    data = []
    if user.logo_path and os.path.exists(user.logo_path):
        try:
            logo = Image(user.logo_path, width=50*mm, height=50*mm, kind='proportional')
            company_info = Paragraph(f"""
                <b>{user.company_name}</b><br/>
                {user.company_address or ''}<br/>
                {user.company_phone or ''}<br/>
                {user.company_email or ''}<br/>
                SIRET: {user.company_siret or 'N/A'}<br/>
                TVA: {user.company_tva or 'N/A'}
            """, styles['Normal'])
            data.append([logo, company_info])
        except:
            data.append(['', get_company_info(user, styles)])
    else:
        data.append(['', get_company_info(user, styles)])
    header_table = Table(data, colWidths=[60*mm, 130*mm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20*mm))
    # Titre
    doc_title = "FACTURE" if invoice.document_type == 'invoice' else "DEVIS"
    elements.append(Paragraph(doc_title, title_style))
    # Informations document
    info_data = [
        ['Numéro:', invoice.number],
        ['Date:', invoice.date.strftime('%d/%m/%Y')],
    ]
    if invoice.document_type == 'invoice' and invoice.due_date:
        info_data.append(['Date d\'échéance:', invoice.due_date.strftime('%d/%m/%Y')])
    info_table = Table(info_data, colWidths=[40*mm, 60*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    # Informations client
    elements.append(Paragraph('<b>Client:</b>', styles['Heading3']))
    client_text = f"""
        <b>{invoice.client.name}</b><br/>
        {invoice.client.address or ''}<br/>
        {invoice.client.postal_code or ''} {invoice.client.city or ''}<br/>
        {invoice.client.country or ''}<br/>
    """
    if invoice.client.email:
        client_text += f"Email: {invoice.client.email}<br/>"
    if invoice.client.siret:
        client_text += f"SIRET: {invoice.client.siret}<br/>"
    if invoice.client.tva_number:
        client_text += f"TVA: {invoice.client.tva_number}"
    elements.append(Paragraph(client_text, styles['Normal']))
    elements.append(Spacer(1, 10*mm))
    # Tableau des articles
    items_data = [['Description', 'Qté', 'Unité', 'Prix U.', 'TVA', 'Total HT']]
    for item in invoice.items:
        items_data.append([
            item.description,
            str(item.quantity),
            item.unit,
            f"{item.price:.2f} {get_currency_symbol(invoice.currency)}",
            f"{item.tva_rate}%",
            f"{item.total:.2f} {get_currency_symbol(invoice.currency)}"
        ])
    items_table = Table(items_data, colWidths=[70*mm, 15*mm, 20*mm, 25*mm, 15*mm, 30*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(user.template_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10*mm))
    # Totaux
    totals_data = []
    # Sous-total
    totals_data.append(['Sous-total HT:', f"{invoice.subtotal:.2f} {get_currency_symbol(invoice.currency)}"])
    # Remise
    if invoice.discount_type != 'none' and invoice.discount_value > 0:
        if invoice.discount_type == 'percent':
            discount_label = f"Remise ({invoice.discount_value}%):"
            discount_amount = invoice.subtotal * (invoice.discount_value / 100)
        else:
            discount_label = "Remise:"
            discount_amount = invoice.discount_value
        totals_data.append([discount_label, f"-{discount_amount:.2f} {get_currency_symbol(invoice.currency)}"])
    # TVA
    totals_data.append(['TVA:', f"{invoice.tax_amount:.2f} {get_currency_symbol(invoice.currency)}"])
    # Total TTC
    totals_data.append(['<b>Total TTC:</b>', f"<b>{invoice.total:.2f} {get_currency_symbol(invoice.currency)}</b>"])
    totals_table = Table(totals_data, colWidths=[140*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor(user.template_color)),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 15*mm))
    # Notes
    if invoice.notes:
        elements.append(Paragraph('<b>Notes:</b>', styles['Heading4']))
        elements.append(Paragraph(invoice.notes, styles['Normal']))
        elements.append(Spacer(1, 5*mm))
    # Conditions de paiement
    if invoice.payment_terms:
        elements.append(Paragraph('<b>Conditions de paiement:</b>', styles['Heading4']))
        elements.append(Paragraph(invoice.payment_terms, styles['Normal']))
        elements.append(Spacer(1, 5*mm))
    # Mentions légales
    if user.legal_mentions:
        elements.append(Spacer(1, 10*mm))
        legal_style = ParagraphStyle(
            'Legal',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        )
        elements.append(Paragraph(user.legal_mentions, legal_style))
    return elements
def generate_classic_template(invoice, user, styles, title_style):
    """Template classique avec bordures"""
    # Implémentation simplifiée - réutilise le template moderne
    return generate_modern_template(invoice, user, styles, title_style)
def generate_minimal_template(invoice, user, styles, title_style):
    """Template minimaliste épuré"""
    # Implémentation simplifiée - réutilise le template moderne
    return generate_modern_template(invoice, user, styles, title_style)
def get_company_info(user, styles):
    """Retourne les informations de l'entreprise formatées"""
    return Paragraph(f"""
        <b>{user.company_name}</b><br/>
        {user.company_address or ''}<br/>
        {user.company_phone or ''}<br/>
        {user.company_email or ''}<br/>
        SIRET: {user.company_siret or 'N/A'}<br/>
        TVA: {user.company_tva or 'N/A'}
    """, styles['Normal'])
def get_currency_symbol(currency_code):
    """Retourne le symbole de la devise"""
    symbols = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
        'CHF': 'CHF',
        'CAD': 'C$'
    }
    return symbols.get(currency_code, currency_code)