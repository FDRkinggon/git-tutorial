from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user, login_user
from app import db
from app.models import Client, Product, Invoice, InvoiceItem, User
from app.pdf_generator import generate_invoice_pdf
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import os

main_bp = Blueprint('main', __name__)

# ============= DASHBOARD =============
@main_bp.route('/')
@login_required
def dashboard():
    # Statistiques
    total_clients = Client.query.filter_by(user_id=current_user.id).count()
    total_invoices = Invoice.query.filter_by(
        user_id=current_user.id,
        document_type='invoice'
    ).count()
    total_quotes = Invoice.query.filter_by(
        user_id=current_user.id,
        document_type='quote'
    ).count()
    
    # Chiffre d'affaires (factures payées)
    revenue = db.session.query(func.sum(Invoice.total)).filter_by(
        user_id=current_user.id,
        document_type='invoice',
        status='paid'
    ).scalar() or 0
    
    # Factures en attente
    pending_amount = db.session.query(func.sum(Invoice.total)).filter_by(
        user_id=current_user.id,
        document_type='invoice',
        status='sent'
    ).scalar() or 0
    
    # Dernières factures
    recent_invoices = Invoice.query.filter_by(
        user_id=current_user.id
    ).order_by(Invoice.created_at.desc()).limit(10).all()
    
    # Revenus mensuels (12 derniers mois)
    monthly_revenue = []
    for i in range(11, -1, -1):
        target_date = datetime.now() - timedelta(days=30*i)
        month_revenue = db.session.query(func.sum(Invoice.total)).filter(
            Invoice.user_id == current_user.id,
            Invoice.document_type == 'invoice',
            Invoice.status == 'paid',
            extract('year', Invoice.date) == target_date.year,
            extract('month', Invoice.date) == target_date.month
        ).scalar() or 0
        monthly_revenue.append({
            'month': target_date.strftime('%b %Y'),
            'revenue': float(month_revenue)
        })
    
    # Top 5 clients
    top_clients = db.session.query(
        Client.name,
        func.sum(Invoice.total).label('total')
    ).join(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'paid'
    ).group_by(Client.id).order_by(func.sum(Invoice.total).desc()).limit(5).all()
    
    return render_template('dashboard.html',
        total_clients=total_clients,
        total_invoices=total_invoices,
        total_quotes=total_quotes,
        revenue=revenue,
        pending_amount=pending_amount,
        recent_invoices=recent_invoices,
        monthly_revenue=monthly_revenue,
        top_clients=top_clients
    )

# ============= CLIENTS =============
@main_bp.route('/clients')
@login_required
def clients():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Client.query.filter_by(user_id=current_user.id)
    
    if search:
        query = query.filter(
            db.or_(
                Client.name.ilike(f'%{search}%'),
                Client.email.ilike(f'%{search}%'),
                Client.city.ilike(f'%{search}%')
            )
        )
    
    clients = query.order_by(Client.name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('clients/list.html', clients=clients, search=search)

@main_bp.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Le nom du client est obligatoire.', 'danger')
            return render_template('clients/add.html')
        
        client = Client(
            user_id=current_user.id,
            name=name,
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            postal_code=request.form.get('postal_code'),
            country=request.form.get('country'),
            siret=request.form.get('siret'),
            tva_number=request.form.get('tva_number'),
            notes=request.form.get('notes')
        )
        db.session.add(client)
        db.session.commit()
        flash(f'Client "{name}" ajouté avec succès.', 'success')
        return redirect(url_for('main.clients'))
    
    return render_template('clients/add.html')

@main_bp.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.email = request.form.get('email')
        client.phone = request.form.get('phone')
        client.address = request.form.get('address')
        client.city = request.form.get('city')
        client.postal_code = request.form.get('postal_code')
        client.country = request.form.get('country')
        client.siret = request.form.get('siret')
        client.tva_number = request.form.get('tva_number')
        client.notes = request.form.get('notes')
        db.session.commit()
        flash(f'Client "{client.name}" modifié avec succès.', 'success')
        return redirect(url_for('main.clients'))
    
    return render_template('clients/edit.html', client=client)

@main_bp.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    # Vérifier s'il y a des factures
    if client.invoices:
        flash(f'Impossible de supprimer "{client.name}" : des factures existent pour ce client.', 'danger')
        return redirect(url_for('main.clients'))
    
    name = client.name
    db.session.delete(client)
    db.session.commit()
    flash(f'Client "{name}" supprimé avec succès.', 'success')
    return redirect(url_for('main.clients'))

# ============= PRODUITS =============
@main_bp.route('/products')
@login_required
def products():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Product.query.filter_by(user_id=current_user.id)
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%')
            )
        )
    
    products = query.order_by(Product.name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('products/list.html', products=products, search=search)

@main_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        
        if not name or not price:
            flash('Le nom et le prix sont obligatoires.', 'danger')
            return render_template('products/add.html')
        
        try:
            price = float(price)
        except ValueError:
            flash('Le prix doit être un nombre valide.', 'danger')
            return render_template('products/add.html')
        
        product = Product(
            user_id=current_user.id,
            name=name,
            description=request.form.get('description'),
            price=price,
            tva_rate=float(request.form.get('tva_rate', 20.0)),
            unit=request.form.get('unit', 'unité')
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Produit "{name}" ajouté avec succès.', 'success')
        return redirect(url_for('main.products'))
    
    return render_template('products/add.html')

@main_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.tva_rate = float(request.form.get('tva_rate', 20.0))
        product.unit = request.form.get('unit', 'unité')
        db.session.commit()
        flash(f'Produit "{product.name}" modifié avec succès.', 'success')
        return redirect(url_for('main.products'))
    
    return render_template('products/edit.html', product=product)

@main_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Produit "{name}" supprimé avec succès.', 'success')
    return redirect(url_for('main.products'))

# ============= FACTURES/DEVIS =============
@main_bp.route('/invoices')
@login_required
def invoices():
    doc_type = request.args.get('type', 'invoice')
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    query = Invoice.query.filter_by(user_id=current_user.id, document_type=doc_type)
    
    if status:
        query = query.filter_by(status=status)
    
    if search:
        query = query.join(Client).filter(
            db.or_(
                Invoice.number.ilike(f'%{search}%'),
                Client.name.ilike(f'%{search}%')
            )
        )
    
    invoices = query.order_by(Invoice.date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('invoices/list.html', 
        invoices=invoices, 
        doc_type=doc_type, 
        status=status,
        search=search
    )

@main_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create_invoice():
    doc_type = request.args.get('type', 'invoice')
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        if not client_id:
            flash('Veuillez sélectionner un client.', 'danger')
            return redirect(url_for('main.create_invoice', type=doc_type))
        
        # Génération du numéro
        if doc_type == 'invoice':
            number = current_user.get_next_invoice_number()
        else:
            number = current_user.get_next_quote_number()
        
        # Calcul de la date d'échéance
        invoice_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        due_date = invoice_date + timedelta(days=current_user.default_payment_terms)
        
        invoice = Invoice(
            user_id=current_user.id,
            client_id=client_id,
            number=number,
            document_type=doc_type,
            date=invoice_date,
            due_date=due_date,
            currency=request.form.get('currency', current_user.default_currency),
            notes=request.form.get('notes'),
            payment_terms=request.form.get('payment_terms')
        )
        db.session.add(invoice)
        db.session.flush()
        
        # Ajout des lignes
        items_count = int(request.form.get('items_count', 0))
        for i in range(items_count):
            description = request.form.get(f'item_description_{i}')
            if description:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=float(request.form.get(f'item_quantity_{i}', 1)),
                    unit=request.form.get(f'item_unit_{i}', 'unité'),
                    price=float(request.form.get(f'item_price_{i}', 0)),
                    tva_rate=float(request.form.get(f'item_tva_{i}', 20))
                )
                item.calculate_total()
                db.session.add(item)
        
        # Remise
        invoice.discount_type = request.form.get('discount_type', 'none')
        if invoice.discount_type != 'none':
            invoice.discount_value = float(request.form.get('discount_value', 0))
        
        invoice.calculate_totals()
        db.session.commit()
        
        doc_name = 'Facture' if doc_type == 'invoice' else 'Devis'
        flash(f'{doc_name} "{number}" créé avec succès.', 'success')
        return redirect(url_for('main.view_invoice', invoice_id=invoice.id))
    
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()
    
    return render_template('invoices/create.html', 
        doc_type=doc_type,
        clients=clients,
        products=products,
        today=datetime.now().strftime('%Y-%m-%d')
    )

@main_bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    return render_template('invoices/view.html', invoice=invoice)

@main_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        invoice.client_id = request.form.get('client_id')
        invoice.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        invoice.currency = request.form.get('currency')
        invoice.notes = request.form.get('notes')
        invoice.payment_terms = request.form.get('payment_terms')
        invoice.status = request.form.get('status')
        
        # Supprimer les anciennes lignes
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        
        # Ajouter les nouvelles lignes
        items_count = int(request.form.get('items_count', 0))
        for i in range(items_count):
            description = request.form.get(f'item_description_{i}')
            if description:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=float(request.form.get(f'item_quantity_{i}', 1)),
                    unit=request.form.get(f'item_unit_{i}', 'unité'),
                    price=float(request.form.get(f'item_price_{i}', 0)),
                    tva_rate=float(request.form.get(f'item_tva_{i}', 20))
                )
                item.calculate_total()
                db.session.add(item)
        
        # Remise
        invoice.discount_type = request.form.get('discount_type', 'none')
        if invoice.discount_type != 'none':
            invoice.discount_value = float(request.form.get('discount_value', 0))
        else:
            invoice.discount_value = 0
        
        invoice.calculate_totals()
        db.session.commit()
        flash(f'Document "{invoice.number}" modifié avec succès.', 'success')
        return redirect(url_for('main.view_invoice', invoice_id=invoice.id))
    
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()
    
    return render_template('invoices/edit.html', 
        invoice=invoice,
        clients=clients,
        products=products
    )

@main_bp.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    number = invoice.number
    doc_type = invoice.document_type
    
    # Supprimer le PDF si existe
    if invoice.pdf_path and os.path.exists(invoice.pdf_path):
        os.remove(invoice.pdf_path)
    
    db.session.delete(invoice)
    db.session.commit()
    
    doc_name = 'Facture' if doc_type == 'invoice' else 'Devis'
    flash(f'{doc_name} "{number}" supprimé avec succès.', 'success')
    return redirect(url_for('main.invoices', type=doc_type))

@main_bp.route('/invoices/<int:invoice_id>/generate-pdf')
@login_required
def generate_pdf(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    try:
        pdf_path = generate_invoice_pdf(invoice, current_user)
        invoice.pdf_path = pdf_path
        db.session.commit()
        return send_file(pdf_path, as_attachment=True, download_name=f'{invoice.number}.pdf')
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {str(e)}', 'danger')
        return redirect(url_for('main.view_invoice', invoice_id=invoice.id))

@main_bp.route('/invoices/<int:invoice_id>/change-status', methods=['POST'])
@login_required
def change_invoice_status(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    new_status = request.form.get('status')
    
    if new_status in ['draft', 'sent', 'paid', 'cancelled']:
        invoice.status = new_status
        db.session.commit()
        flash('Statut mis à jour avec succès.', 'success')
    else:
        flash('Statut invalide.', 'danger')
    
    return redirect(url_for('main.view_invoice', invoice_id=invoice.id))

# ============= PARAMÈTRES =============
@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.company_name = request.form.get('company_name')
        current_user.company_address = request.form.get('company_address')
        current_user.company_phone = request.form.get('company_phone')
        current_user.company_email = request.form.get('company_email')
        current_user.company_siret = request.form.get('company_siret')
        current_user.company_tva = request.form.get('company_tva')
        current_user.default_currency = request.form.get('default_currency')
        current_user.invoice_prefix = request.form.get('invoice_prefix')
        current_user.quote_prefix = request.form.get('quote_prefix')
        current_user.default_payment_terms = int(request.form.get('default_payment_terms'))
        current_user.default_template = request.form.get('default_template')
        current_user.template_color = request.form.get('template_color')
        current_user.legal_mentions = request.form.get('legal_mentions')
        
        # Gestion du logo
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"logo_{current_user.id}_{file.filename}")
                filepath = os.path.join('static/uploads', filename)
                file.save(filepath)
                current_user.logo_path = filepath
        
        db.session.commit()
        flash('Paramètres enregistrés avec succès.', 'success')
        return redirect(url_for('main.settings'))
    
    return render_template('settings.html')

# ============= API ENDPOINTS =============
@main_bp.route('/api/products')
@login_required
def api_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'tva_rate': p.tva_rate,
        'unit': p.unit
    } for p in products])

@main_bp.route('/api/clients')
@login_required
def api_clients():
    clients = Client.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'address': c.address,
        'city': c.city
    } for c in clients])

'''
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Add your authentication logic here
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):  # Assuming you have this method
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid email or password')
    
    return render_template('auth/login.html')

'''
'''
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Client, Product, Invoice, InvoiceItem
from app.pdf_generator import generate_invoice_pdf
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import os
main_bp = Blueprint('main', __name__)
# ============= DASHBOARD =============
@main_bp.route('/')
@login_required
def dashboard():
    # Statistiques
    total_clients = Client.query.filter_by(user_id=current_user.id).count()
    total_invoices = Invoice.query.filter_by(
        user_id=current_user.id,
        document_type='invoice'
    ).count()
    total_quotes = Invoice.query.filter_by(
        user_id=current_user.id,
        document_type='quote'
    ).count()
    # Chiffre d'affaires (factures payées)
    revenue = db.session.query(func.sum(Invoice.total)).filter_by(
        user_id=current_user.id,
        document_type='invoice',
        status='paid'
    ).scalar() or 0
    # Factures en attente
    pending_amount = db.session.query(func.sum(Invoice.total)).filter_by(
        user_id=current_user.id,
        document_type='invoice',
        status='sent'
    ).scalar() or 0
    # Dernières factures
    recent_invoices = Invoice.query.filter_by(
        user_id=current_user.id
    ).order_by(Invoice.created_at.desc()).limit(10).all()
    # Revenus mensuels (12 derniers mois)
    monthly_revenue = []
    for i in range(11, -1, -1):
        target_date = datetime.now() - timedelta(days=30*i)
        month_revenue = db.session.query(func.sum(Invoice.total)).filter(
            Invoice.user_id == current_user.id,
            Invoice.document_type == 'invoice',
            Invoice.status == 'paid',
            extract('year', Invoice.date) == target_date.year,
            extract('month', Invoice.date) == target_date.month
        ).scalar() or 0
        monthly_revenue.append({
            'month': target_date.strftime('%b %Y'),
            'revenue': float(month_revenue)
        })
    # Top 5 clients
    top_clients = db.session.query(
        Client.name,
        func.sum(Invoice.total).label('total')
    ).join(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'paid'
    ).group_by(Client.id).order_by(func.sum(Invoice.total).desc()).limit(5).all()
    return render_template('dashboard.html',
        total_clients=total_clients,
        total_invoices=total_invoices,
        total_quotes=total_quotes,
        revenue=revenue,
        pending_amount=pending_amount,
        recent_invoices=recent_invoices,
        monthly_revenue=monthly_revenue,
        top_clients=top_clients
    )
 # ============= CLIENTS =============
@main_bp.route('/clients')
@login_required
def clients():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Client.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(
            db.or_(
                Client.name.ilike(f'%{search}%'),
                Client.email.ilike(f'%{search}%'),
                Client.city.ilike(f'%{search}%')
            )
        )
    clients = query.order_by(Client.name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('clients/list.html', clients=clients, search=search)
@main_bp.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Le nom du client est obligatoire.', 'danger')
            return render_template('clients/add.html')
        client = Client(
            user_id=current_user.id,
            name=name,
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            postal_code=request.form.get('postal_code'),
            country=request.form.get('country'),
            siret=request.form.get('siret'),
            tva_number=request.form.get('tva_number'),
            notes=request.form.get('notes')
        )
        db.session.add(client)
        db.session.commit()
        flash(f'Client "{name}" ajouté avec succès.', 'success')
        return redirect(url_for('main.clients'))
    return render_template('clients/add.html')
@main_bp.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.email = request.form.get('email')
        client.phone = request.form.get('phone')
        client.address = request.form.get('address')
        client.city = request.form.get('city')
        client.postal_code = request.form.get('postal_code')
        client.country = request.form.get('country')
        client.siret = request.form.get('siret')
        client.tva_number = request.form.get('tva_number')
        client.notes = request.form.get('notes')
        db.session.commit()
        flash(f'Client "{client.name}" modifié avec succès.', 'success')
        return redirect(url_for('main.clients'))
    return render_template('clients/edit.html', client=client)
@main_bp.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    # Vérifier s'il y a des factures
    if client.invoices:
        flash(f'Impossible de supprimer "{client.name}" : des factures existent pour ce client.', 'danger')
        return redirect(url_for('main.clients'))
    name = client.name
    db.session.delete(client)
    db.session.commit()
    flash(f'Client "{name}" supprimé avec succès.', 'success')
    return redirect(url_for('main.clients'))
 # ============= PRODUITS =============
@main_bp.route('/products')
@login_required
def products():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Product.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(
        )
        db.or_(
            Product.name.ilike(f'%{search}%'),
            Product.description.ilike(f'%{search}%')
        )
    products = query.order_by(Product.name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('products/list.html', products=products, search=search)
@main_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        if not name or not price:
            flash('Le nom et le prix sont obligatoires.', 'danger')
            return render_template('products/add.html')
        try:
            price = float(price)
        except ValueError:
            flash('Le prix doit être un nombre valide.', 'danger')
            return render_template('products/add.html')
        product = Product(
            user_id=current_user.id,
            name=name,
            description=request.form.get('description'),
            price=price,
            tva_rate=float(request.form.get('tva_rate', 20.0)),
            unit=request.form.get('unit', 'unité')
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Produit "{name}" ajouté avec succès.', 'success')
        return redirect(url_for('main.products'))
    return render_template('products/add.html')
@main_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.tva_rate = float(request.form.get('tva_rate', 20.0))
        product.unit = request.form.get('unit', 'unité')
        db.session.commit()
        flash(f'Produit "{product.name}" modifié avec succès.', 'success')
        return redirect(url_for('main.products'))
    return render_template('products/edit.html', product=product)
@main_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Produit "{name}" supprimé avec succès.', 'success')
    return redirect(url_for('main.products'))
 # ============= FACTURES/DEVIS =============
@main_bp.route('/invoices')
@login_required
def invoices():
    doc_type = request.args.get('type', 'invoice')
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Invoice.query.filter_by(user_id=current_user.id, document_type=doc_type)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.join(Client).filter(
            db.or_(
                Invoice.number.ilike(f'%{search}%'),
                Client.name.ilike(f'%{search}%')
            )
        )
    invoices = query.order_by(Invoice.date.desc()).paginate(
    )
    paginated_invoices = invoices_query.paginate(
    page=page, per_page=20, error_out=False
)
    return render_template('invoices/list.html', 
        invoices=invoices, 
        doc_type=doc_type, 
        status=status,
        search=search
    )
@main_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create_invoice():
    doc_type = request.args.get('type', 'invoice')
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        if not client_id:
            flash('Veuillez sélectionner un client.', 'danger')
            return redirect(url_for('main.create_invoice', type=doc_type))
        # Génération du numéro
        if doc_type == 'invoice':
            number = current_user.get_next_invoice_number()
        else:
            number = current_user.get_next_quote_number()
        # Calcul de la date d'échéance
        invoice_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        due_date = invoice_date + timedelta(days=current_user.default_payment_terms)
        invoice = Invoice(
            user_id=current_user.id,
            client_id=client_id,
            number=number,
            document_type=doc_type,
            date=invoice_date,
            due_date=due_date,
            currency=request.form.get('currency', current_user.default_currency),
            notes=request.form.get('notes'),
            payment_terms=request.form.get('payment_terms')
        )
        db.session.add(invoice)
        db.session.flush()
        # Ajout des lignes
        items_count = int(request.form.get('items_count', 0))
        for i in range(items_count):
            description = request.form.get(f'item_description_{i}')
            if description:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=float(request.form.get(f'item_quantity_{i}', 1)),
                    unit=request.form.get(f'item_unit_{i}', 'unité'),
                    price=float(request.form.get(f'item_price_{i}', 0)),
                    tva_rate=float(request.form.get(f'item_tva_{i}', 20))
                )
                item.calculate_total()
                db.session.add(item)
        # Remise
        invoice.discount_type = request.form.get('discount_type', 'none')
        if invoice.discount_type != 'none':
            invoice.discount_value = float(request.form.get('discount_value', 0))
        invoice.calculate_totals()
        db.session.commit()
        doc_name = 'Facture' if doc_type == 'invoice' else 'Devis'
        flash(f'{doc_name} "{number}" créé avec succès.', 'success')
        return redirect(url_for('main.view_invoice', invoice_id=invoice.id))
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()
    return render_template('invoices/create.html', 
        doc_type=doc_type,
        clients=clients,
        products=products,
        today=datetime.now().strftime('%Y-%m-%d')
    )
@main_bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    return render_template('invoices/view.html', invoice=invoice)
@main_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        invoice.client_id = request.form.get('client_id')
        invoice.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        invoice.currency = request.form.get('currency')
        invoice.notes = request.form.get('notes')
        invoice.payment_terms = request.form.get('payment_terms')
        invoice.status = request.form.get('status')
        # Supprimer les anciennes lignes
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        # Ajouter les nouvelles lignes
        items_count = int(request.form.get('items_count', 0))
        for i in range(items_count):
            description = request.form.get(f'item_description_{i}')
            if description:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=float(request.form.get(f'item_quantity_{i}', 1)),
                    unit=request.form.get(f'item_unit_{i}', 'unité'),
                    price=float(request.form.get(f'item_price_{i}', 0)),
                    tva_rate=float(request.form.get(f'item_tva_{i}', 20))
                )
                item.calculate_total()
                db.session.add(item)
        # Remise
        invoice.discount_type = request.form.get('discount_type', 'none')
        if invoice.discount_type != 'none':
            invoice.discount_value = float(request.form.get('discount_value', 0))
        else:
            invoice.discount_value = 0
        invoice.calculate_totals()
        db.session.commit()
        flash(f'Document "{invoice.number}" modifié avec succès.', 'success')
        return redirect(url_for('main.view_invoice', invoice_id=invoice.id))
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.name).all()
    return render_template('invoices/edit.html', 
        invoice=invoice,
        clients=clients,
        products=products
    )
@main_bp.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    number = invoice.number
    doc_type = invoice.document_type
    # Supprimer le PDF si existe
    if invoice.pdf_path and os.path.exists(invoice.pdf_path):
        os.remove(invoice.pdf_path)
    db.session.delete(invoice)
    db.session.commit()
    doc_name = 'Facture' if doc_type == 'invoice' else 'Devis'
    flash(f'{doc_name} "{number}" supprimé avec succès.', 'success')
    return redirect(url_for('main.invoices', type=doc_type))
@main_bp.route('/invoices/<int:invoice_id>/generate-pdf')
@login_required
def generate_pdf(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    try:
        pdf_path = generate_invoice_pdf(invoice, current_user)
        invoice.pdf_path = pdf_path
        db.session.commit()
        return send_file(pdf_path, as_attachment=True, download_name=f'{invoice.number}.pdf')
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {str(e)}', 'danger')
        return redirect(url_for('main.view_invoice', invoice_id=invoice.id))
@main_bp.route('/invoices/<int:invoice_id>/change-status', methods=['POST'])
@login_required
def change_invoice_status(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    new_status = request.form.get('status')
    if new_status in ['draft', 'sent', 'paid', 'cancelled']:
        invoice.status = new_status
        db.session.commit()
        flash('Statut mis à jour avec succès.', 'success')
    else:
        flash('Statut invalide.', 'danger')
    return redirect(url_for('main.view_invoice', invoice_id=invoice.id))
 # ============= PARAMÈTRES =============
@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.company_name = request.form.get('company_name')
        current_user.company_address = request.form.get('company_address')
        current_user.company_phone = request.form.get('company_phone')
        current_user.company_email = request.form.get('company_email')
        current_user.company_siret = request.form.get('company_siret')
        current_user.company_tva = request.form.get('company_tva')
        current_user.default_currency = request.form.get('default_currency')
        current_user.invoice_prefix = request.form.get('invoice_prefix')
        current_user.quote_prefix = request.form.get('quote_prefix')
        current_user.default_payment_terms = int(request.form.get('default_payment_terms'))
        current_user.default_template = request.form.get('default_template')
        current_user.template_color = request.form.get('template_color')
        current_user.legal_mentions = request.form.get('legal_mentions')
        # Gestion du logo
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"logo_{current_user.id}_{file.filename}")
                filepath = os.path.join('static/uploads', filename)
                file.save(filepath)
                current_user.logo_path = filepath
        db.session.commit()
        flash('Paramètres enregistrés avec succès.', 'success')
        return redirect(url_for('main.settings'))
    return render_template('settings.html')
 # ============= API ENDPOINTS =============
@main_bp.route('/api/products')
@login_required
def api_products():
    products = Product.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'tva_rate': p.tva_rate,
        'unit': p.unit
    } for p in products])
@main_bp.route('/api/clients')
@login_required
def api_clients():
    clients = Client.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'address': c.address,
        'city': c.city
    } for c in clients])
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Add your authentication logic here
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):  # Assuming you have this method
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid email or password')
    
    return render_template('auth/login.html')
'''