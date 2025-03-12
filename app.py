import os
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure database - handle Heroku PostgreSQL URL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///offices.db')
# Heroku Postgres uses postgres:// but SQLAlchemy needs postgresql://
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
auth = HTTPBasicAuth()

# Define User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

# Define the Office Page model
class OfficePage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state_office_token = db.Column(db.String(100), nullable=False)
    area_served_token = db.Column(db.String(100), nullable=False)
    service_token = db.Column(db.String(100), nullable=False)
    meta_title = db.Column(db.String(200), nullable=False)
    meta_description = db.Column(db.Text, nullable=False)
    page_title = db.Column(db.String(200), nullable=False)
    page_content = db.Column(db.Text, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('state_office_token', 'area_served_token', 'service_token'),
    )

# Authentication handler
@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.verify_password(password):
        return user
    return None

# Error handler for unauthorized access
@auth.error_handler
def unauthorized():
    return jsonify({'error': 'Unauthorized access'}), 401

# GET route for office page - requires authentication and handles / correctly
@app.route('/offices/<state_token>/<office_token>/areas/<area_served_token>/services/<service_token>/page', methods=['GET'])
@auth.login_required
def get_office_page(state_token, office_token, area_served_token, service_token):
    # Using slash format to match your data
    state_office_token = f"{state_token}/{office_token}"
    
    page = OfficePage.query.filter_by(
        state_office_token=state_office_token,
        area_served_token=area_served_token,
        service_token=service_token
    ).first()
    
    if not page:
        return jsonify({'error': 'Page not found'}), 404
    
    return jsonify({
        'id': page.id,
        'state_office_token': page.state_office_token,
        'area_served_token': page.area_served_token,
        'service_token': page.service_token,
        'meta_title': page.meta_title,
        'meta_description': page.meta_description,
        'page_title': page.page_title,
        'page_content': page.page_content
    })

# POST route to create a new office page - already requires authentication
@app.route('/offices', methods=['POST'])
@auth.login_required
def create_office_page():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['state_office_token', 'area_served_token', 'service_token', 
                       'meta_title', 'meta_description', 'page_title', 'page_content']
    
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Check if page already exists
    existing_page = OfficePage.query.filter_by(
        state_office_token=data['state_office_token'],
        area_served_token=data['area_served_token'],
        service_token=data['service_token']
    ).first()
    
    if existing_page:
        return jsonify({'error': 'Page already exists'}), 409
    
    # Create new page
    new_page = OfficePage(
        state_office_token=data['state_office_token'],
        area_served_token=data['area_served_token'],
        service_token=data['service_token'],
        meta_title=data['meta_title'],
        meta_description=data['meta_description'],
        page_title=data['page_title'],
        page_content=data['page_content']
    )
    
    db.session.add(new_page)
    db.session.commit()
    
    return jsonify({
        'id': new_page.id,
        'message': 'Page created successfully'
    }), 201

# Health check endpoint
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Office Services API is running'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', False))
