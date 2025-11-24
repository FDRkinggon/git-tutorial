from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
from urllib.parse import urlparse  # ← CORRECTION ICI

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        company_name = request.form.get('company_name')
        
        # Validation
        if not all([email, password, password_confirm, company_name]):
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('auth/register.html')
        
        # Création utilisateur
        user = User(
            email=email,
            company_name=company_name,
            company_email=email  # ← ADD THIS LINE
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

'''
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Email et mot de passe requis.', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':  # ← CORRECTION ICI
            next_page = url_for('main.dashboard')
        
        flash(f'Bienvenue {user.company_name} !', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))

'''


'''
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
from urllib.parse import urlparse  # ← CORRECTION ICI

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        company_name = request.form.get('company_name')
        
        # Validation
        if not all([email, password, password_confirm, company_name]):
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('auth/register.html')
        
        # Création utilisateur
        user = User(
            email=email,
            company_name=company_name
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Email et mot de passe requis.', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':  # ← CORRECTION ICI
            next_page = url_for('main.dashboard')
        
        flash(f'Bienvenue {user.company_name} !', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))

'''