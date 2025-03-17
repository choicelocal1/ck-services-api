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

# New service lookup endpoint without office token
@app.route('/services/<state_token>/<area_served_token>/<service_token>', methods=['GET'])
@auth.login_required
def get_service_info(state_token, area_served_token, service_token):
    # Find all matching pages by partial matching on state_office_token
    pages = OfficePage.query.filter(
        OfficePage.state_office_token.like(f"{state_token}/%"),
        OfficePage.area_served_token == area_served_token,
        OfficePage.service_token == service_token
    ).all()
    
    if not pages:
        return jsonify({'error': 'No matching service found'}), 404
    
    # Format the response
    results = []
    for page in pages:
        results.append({
            'id': page.id,
            'state_office_token': page.state_office_token,
            'area_served_token': page.area_served_token,
            'service_token': page.service_token,
            'meta_title': page.meta_title,
            'meta_description': page.meta_description,
            'page_title': page.page_title,
            'page_content': page.page_content
        })
    
    # If only one result is found, return it directly as a single object
    if len(results) == 1:
        return jsonify(results[0])
    
    # Otherwise return all matching results
    return jsonify(results)

# New GET route to list services for an area - requires authentication
@app.route('/offices/<state_token>/<office_token>/areas/<area_served_token>/services', methods=['GET'])
@auth.login_required
def get_area_services(state_token, office_token, area_served_token):
    # Using slash format to match your data
    state_office_token = f"{state_token}/{office_token}"
    
    # Query for all pages matching the state_office_token and area_served_token
    pages = OfficePage.query.filter_by(
        state_office_token=state_office_token,
        area_served_token=area_served_token
    ).all()
    
    if not pages:
        return jsonify({'error': 'No services found for this area'}), 404
    
    # Format the response to include only the required fields
    services = []
    for page in pages:
        services.append({
            'id': page.id,
            'state_office_token': page.state_office_token,
            'area_served_token': page.area_served_token,
            'service_token': page.service_token,
            'service_page': page.page_title
        })
    
    return jsonify(services)

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

# GET endpoint for office sitemap in JSON format
@app.route('/offices/<state_token>/<office_token>/areas/services/sitemap.xml', methods=['GET'])
@auth.login_required
def get_office_sitemap(state_token, office_token):
    # Using slash format to match your data
    state_office_token = f"{state_token}/{office_token}"
    
    # Query for all pages matching the state_office_token
    pages = OfficePage.query.filter_by(
        state_office_token=state_office_token
    ).all()
    
    if not pages:
        return jsonify({'error': 'No services found for this office'}), 404
    
    # Format the response to include only the required fields
    services = []
    for page in pages:
        services.append({
            'state_office_token': page.state_office_token,
            'area_served_token': page.area_served_token,
            'service_token': page.service_token
        })
    
    # The route has .xml extension but we're returning JSON as requested
    return jsonify(services)

# GET endpoint for sitemap index with all distinct state_office_tokens
@app.route('/sitemap-index.json', methods=['GET'])
@auth.login_required
def get_sitemap_index():
    # Query for all distinct state_office_tokens
    # We need to use db.session.query instead of OfficePage.query
    # to get distinct values easily
    distinct_tokens = db.session.query(OfficePage.state_office_token).distinct().all()
    
    # Format the response
    # Extract the first item from each tuple returned by the query
    tokens = [token[0] for token in distinct_tokens]
    
    return jsonify(tokens)

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
