from app import db
from flask_login import UserMixin
from datetime import datetime
import bcrypt

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Informations entreprise
    company_name = db.Column(db.String(200), nullable=False)
    company_address = db.Column(db.Text)
    company_phone = db.Column(db.String(20))
    company_email = db.Column(db.String(120))
    company_siret = db.Column(db.String(50))
    company_tva = db.Column(db.String(50))
    logo_path = db.Column(db.String(255))
    
    # Paramètres
    default_currency = db.Column(db.String(3), default='EUR')
    invoice_prefix = db.Column(db.String(10), default='INV')
    quote_prefix = db.Column(db.String(10), default='DEV')
    default_payment_terms = db.Column(db.Integer, default=30)  # jours
    default_template = db.Column(db.String(20), default='modern')
    template_color = db.Column(db.String(7), default='#2563eb')  # bleu
    
    # Mentions légales
    legal_mentions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    clients = db.relationship('Client', backref='user', lazy=True, cascade='all, delete-orphan')
    products = db.relationship('Product', backref='user', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def get_next_invoice_number(self):
        from sqlalchemy import desc
        last_invoice = Invoice.query.filter_by(
            user_id=self.id,
            document_type='invoice'
        ).order_by(desc(Invoice.id)).first()
        
        if last_invoice and last_invoice.number:
            try:
                # Extract number from format like "INV-0001"
                prefix = self.invoice_prefix + "-"
                if last_invoice.number.startswith(prefix):
                    last_num = int(last_invoice.number[len(prefix):])
                    return f"{prefix}{last_num + 1:04d}"
            except (ValueError, IndexError):
                pass
        return f"{self.invoice_prefix}-0001"

    def get_next_quote_number(self):
        from sqlalchemy import desc
        last_quote = Invoice.query.filter_by(
            user_id=self.id,
            document_type='quote'
        ).order_by(desc(Invoice.id)).first()
        
        if last_quote and last_quote.number:
            try:
                # Extract number from format like "DEV-0001"
                prefix = self.quote_prefix + "-"
                if last_quote.number.startswith(prefix):
                    last_num = int(last_quote.number[len(prefix):])
                    return f"{prefix}{last_num + 1:04d}"
            except (ValueError, IndexError):
                pass
        return f"{self.quote_prefix}-0001"

    def __repr__(self):
        return f'<User {self.email}>'


class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    siret = db.Column(db.String(50))
    tva_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    invoices = db.relationship('Invoice', backref='client', lazy=True)

    def __repr__(self):
        return f'<Client {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    tva_rate = db.Column(db.Float, default=20.0)  # TVA en %
    unit = db.Column(db.String(20), default='unité')  # unité, heure, jour, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Product {self.name}>'


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    number = db.Column(db.String(50), nullable=False, unique=True)
    document_type = db.Column(db.String(20), nullable=False)  # 'invoice' ou 'quote'
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    
    # Calculs
    subtotal = db.Column(db.Float, default=0.0)
    discount_type = db.Column(db.String(10), default='none')  # 'none', 'percent', 'amount'
    discount_value = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='EUR')
    
    # Statut
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, cancelled
    
    # Notes
    notes = db.Column(db.Text)
    payment_terms = db.Column(db.Text)
    
    # PDF
    pdf_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')

    def calculate_totals(self):
        """Calcule les totaux de la facture"""
        self.subtotal = sum(item.total for item in self.items)
        
        # Application de la remise
        discount_amount = 0
        if self.discount_type == 'percent':
            discount_amount = self.subtotal * (self.discount_value / 100)
        elif self.discount_type == 'amount':
            discount_amount = self.discount_value
        
        subtotal_after_discount = self.subtotal - discount_amount
        
        # Calcul de la TVA
        self.tax_amount = sum(
            (item.quantity * item.price * item.tva_rate / 100)
            for item in self.items
        )
        
        # Si remise, on l'applique aussi sur la TVA
        if discount_amount > 0 and self.subtotal > 0:
            self.tax_amount = self.tax_amount * (subtotal_after_discount / self.subtotal)
        
        self.total = subtotal_after_discount + self.tax_amount

    def __repr__(self):
        return f'<Invoice {self.number}>'


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit = db.Column(db.String(20), default='unité')
    price = db.Column(db.Float, nullable=False)
    tva_rate = db.Column(db.Float, default=20.0)
    total = db.Column(db.Float, nullable=False)

    def calculate_total(self):
        self.total = self.quantity * self.price

    def __repr__(self):
        return f'<InvoiceItem {self.description}>'


'''from app import db
from flask_login import UserMixin
from datetime import datetime
import bcrypt
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # Informations entreprise
    company_name = db.Column(db.String(200), nullable=False)
    company_address = db.Column(db.Text)
    company_phone = db.Column(db.String(20))
    company_email = db.Column(db.String(120))
    company_siret = db.Column(db.String(50))
    company_tva = db.Column(db.String(50))
    logo_path = db.Column(db.String(255))
    # Paramètres
    default_currency = db.Column(db.String(3), default='EUR')
    invoice_prefix = db.Column(db.String(10), default='INV')
    quote_prefix = db.Column(db.String(10), default='DEV')
    default_payment_terms = db.Column(db.Integer, default=30)  # jours
    default_template = db.Column(db.String(20), default='modern')
    template_color = db.Column(db.String(7), default='#2563eb')  # bleu
    # Mentions légales
    legal_mentions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relations
    clients = db.relationship('Client', backref='user', lazy=True, cascade='all, delete-orphan')
    products = db.relationship('Product', backref='user', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='user', lazy=True, cascade='all, delete-orphan')
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    def get_next_invoice_number(self):
        last_invoice = Invoice.query.filter_by(
            user_id=self.id,
            document_type='invoice'
        ).order_by(Invoice.number.desc()).first()
        if last_invoice and last_invoice.number:
            try:
                last_num = int(last_invoice.number.split('-')[-1])
                return f"{self.invoice_prefix}-{last_num + 1:04d}"
            except:
                pass
        return f"{self.invoice_prefix}-0001"
    def get_next_quote_number(self):
        last_quote = Invoice.query.filter_by(
            user_id=self.id,
            document_type='quote'
        ).order_by(Invoice.number.desc()).first()
        if last_quote and last_quote.number:
            try:
                last_num = int(last_quote.number.split('-')[-1])
                return f"{self.quote_prefix}-{last_num + 1:04d}"
            except:
                pass
        return f"{self.quote_prefix}-0001"
class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    siret = db.Column(db.String(50))
    tva_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relations
    invoices = db.relationship('Invoice', backref='client', lazy=True)
    def __repr__(self):
        return f'<Client {self.name}>'
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    tva_rate = db.Column(db.Float, default=20.0)  # TVA en %
    unit = db.Column(db.String(20), default='unité')  # unité, heure, jour, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self):
        return f'<Product {self.name}>'
class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    number = db.Column(db.String(50), nullable=False, unique=True)
    document_type = db.Column(db.String(20), nullable=False)  # 'invoice' ou 'quote'
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    # Calculs
    subtotal = db.Column(db.Float, default=0.0)
    discount_type = db.Column(db.String(10), default='none')  # 'none', 'percent', 'amount'
    discount_value = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='EUR')
    # Statut
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, cancelled
    # Notes
    notes = db.Column(db.Text)
    payment_terms = db.Column(db.Text)
    # PDF
    pdf_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relations
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    def calculate_totals(self):
        """Calcule les totaux de la facture"""
        self.subtotal = sum(item.total for item in self.items)
        # Application de la remise
        discount_amount = 0
        if self.discount_type == 'percent':
            discount_amount = self.subtotal * (self.discount_value / 100)
        elif self.discount_type == 'amount':
            discount_amount = self.discount_value
        subtotal_after_discount = self.subtotal - discount_amount
        # Calcul de la TVA
        self.tax_amount = sum(
            (item.quantity * item.price * item.tva_rate / 100)
            for item in self.items
        )
        # Si remise, on l'applique aussi sur la TVA
        if discount_amount > 0 and self.subtotal > 0:
            self.tax_amount = self.tax_amount * (subtotal_after_discount / self.subtotal)
        self.total = subtotal_after_discount + self.tax_amount
    def __repr__(self):
        return f'<Invoice {self.number}>'
class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit = db.Column(db.String(20), default='unité')
    price = db.Column(db.Float, nullable=False)
    tva_rate = db.Column(db.Float, default=20.0)
    total = db.Column(db.Float, nullable=False)
    def calculate_total(self):
        self.total = self.quantity * self.price
    def __repr__(self):
        return f'<InvoiceItem {self.description}>'
        '''