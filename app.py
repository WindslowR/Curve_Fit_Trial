from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from scipy.optimize import curve_fit
import numpy as np
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///curve_fit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class CurveFit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dataset_name = db.Column(db.String(150), nullable=False)
    fit_params = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='sha256')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid email or password!')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_fits = CurveFit.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', user_fits=user_fits)

@app.route('/curve_fit', methods=['GET', 'POST'])
@login_required
def curve_fit_page():
    if request.method == 'POST':
        dataset_name = request.form['dataset_name']
        x_data = list(map(float, request.form.getlist('x_data')))
        y_data = list(map(float, request.form.getlist('y_data')))

        # Curve fitting
        def fit_function(x, a, b, c):
            return a * x**2 + b * x + c

        try:
            popt, _ = curve_fit(fit_function, np.array(x_data), np.array(y_data))
            fit_params = ', '.join(map(str, popt))

            # Save to database
            new_fit = CurveFit(user_id=current_user.id, dataset_name=dataset_name, fit_params=fit_params)
            db.session.add(new_fit)
            db.session.commit()

            flash(f'Curve fitting successful! Parameters: {fit_params}')
            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f'Error during curve fitting: {str(e)}')

    return render_template('curve_fit.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Initialize Database
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
