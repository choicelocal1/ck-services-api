import os
import logging
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

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
    password_hash = db.Column(db.String(256), nullable=False)

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

# Global error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad Request',
        'message': 'The request was malformed or missing required parameters',
        'status_code': 400
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Authentication is required to access this resource',
        'status_code': 401
    }), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        'error': 'Forbidden',
        'message': 'You do not have permission to access this resource',
        'status_code': 403
    }), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'status_code': 404
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method Not Allowed',
        'message': 'The HTTP method is not allowed for this endpoint',
        'status_code': 405
    }), 405

@app.errorhandler(409)
def conflict(error):
    return jsonify({
        'error': 'Conflict',
        'message': 'The request conflicts with the current state of the resource',
        'status_code': 409
    }), 409

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred on the server',
        'status_code': 500
    }), 500

# Custom error handler for database errors
@app.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    db.session.rollback()  # Roll back the session in case of error
    return jsonify({
        'error': 'Database Error',
        'message': 'A database error occurred while processing your request',
        'status_code': 500
    }), 500

# Authentication handler
@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.verify_password(password):
        return user
    return None

# Updated error handler for unauthorized access
@auth.error_handler
def auth_error():
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Invalid credentials or authentication token',
        'status_code': 401
    }), 401

# GET route for office page - requires authentication and handles / correctly
@app.route('/offices/<state_token>/<office_token>/areas/<area_served_token>/services/<service_token>/page', methods=['GET'])
@auth.login_required
def get_office_page(state_token, office_token, area_served_token, service_token):
    try:
        # Validate input parameters
        if not state_token or not office_token or not area_served_token or not service_token:
            return jsonify({
                'error': 'Bad Request',
                'message': 'All parameters (state_token, office_token, area_served_token, service_token) are required',
                'status_code': 400
            }), 400
            
        # Using slash format to match your data
        state_office_token = f"{state_token}/{office_token}"
        
        page = OfficePage.query.filter_by(
            state_office_token=state_office_token,
            area_served_token=area_served_token,
            service_token=service_token
        ).first()
        
        if not page:
            return jsonify({
                'error': 'Not Found',
                'message': f'No page found for office: {state_office_token}, area: {area_served_token}, service: {service_token}',
                'status_code': 404
            }), 404
        
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
        
    except Exception as e:
        app.logger.error(f"Error in get_office_page: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred while processing your request',
            'status_code': 500
        }), 500

# Service lookup endpoint without office token
@app.route('/services/<state_token>/<area_served_token>/<service_token>', methods=['GET'])
@auth.login_required
def get_service_info(state_token, area_served_token, service_token):
    try:
        # Validate input parameters
        if not state_token or not area_served_token or not service_token:
            return jsonify({
                'error': 'Bad Request',
                'message': 'All parameters (state_token, area_served_token, service_token) are required',
                'status_code': 400
            }), 400
            
        # Find all matching pages by partial matching on state_office_token
        pages = OfficePage.query.filter(
            OfficePage.state_office_token.like(f"{state_token}/%"),
            OfficePage.area_served_token == area_served_token,
            OfficePage.service_token == service_token
        ).all()
        
        if not pages:
            return jsonify({
                'error': 'Not Found',
                'message': f'No service found matching state: {state_token}, area: {area_served_token}, service: {service_token}',
                'status_code': 404
            }), 404
        
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
        
    except Exception as e:
        app.logger.error(f"Error in get_service_info: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred while processing your request',
            'status_code': 500
        }), 500

# GET route to list services for an area
@app.route('/offices/<state_token>/<office_token>/areas/<area_served_token>/services', methods=['GET'])
@auth.login_required
def get_area_services(state_token, office_token, area_served_token):
    try:
        # Validate input parameters
        if not state_token or not office_token or not area_served_token:
            return jsonify({
                'error': 'Bad Request',
                'message': 'All parameters (state_token, office_token, area_served_token) are required',
                'status_code': 400
            }), 400
            
        # Using slash format to match your data
        state_office_token = f"{state_token}/{office_token}"
        
        # Query for all pages matching the state_office_token and area_served_token
        pages = OfficePage.query.filter_by(
            state_office_token=state_office_token,
            area_served_token=area_served_token
        ).all()
        
        if not pages:
            return jsonify({
                'error': 'Not Found',
                'message': f'No services found for office: {state_office_token}, area: {area_served_token}',
                'status_code': 404
            }), 404
        
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
        
    except Exception as e:
        app.logger.error(f"Error in get_area_services: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred while processing your request',
            'status_code': 500
        }), 500

# POST route to create a new office page
@app.route('/offices', methods=['POST'])
@auth.login_required
def create_office_page():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'No JSON data provided in request body',
                'status_code': 400
            }), 400
        
        # Validate required fields
        required_fields = ['state_office_token', 'area_served_token', 'service_token', 
                        'meta_title', 'meta_description', 'page_title', 'page_content']
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'status_code': 400
            }), 400
        
        # Check if page already exists
        existing_page = OfficePage.query.filter_by(
            state_office_token=data['state_office_token'],
            area_served_token=data['area_served_token'],
            service_token=data['service_token']
        ).first()
        
        if existing_page:
            return jsonify({
                'error': 'Conflict',
                'message': f'Page already exists for state_office_token: {data["state_office_token"]}, area_served_token: {data["area_served_token"]}, service_token: {data["service_token"]}',
                'status_code': 409
            }), 409
        
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
            'message': 'Page created successfully',
            'status_code': 201
        }), 201
        
    except ValueError as e:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid JSON format in request body',
            'status_code': 400
        }), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Database error in create_office_page: {str(e)}")
        return jsonify({
            'error': 'Database Error',
            'message': 'A database error occurred while creating the page',
            'status_code': 500
        }), 500
    except Exception as e:
        app.logger.error(f"Error in create_office_page: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred while processing your request',
            'status_code': 500
        }), 500

# GET endpoint for office sitemap in JSON format
@app.route('/offices/<state_token>/<office_token>/areas/services/sitemap.xml', methods=['GET'])
@auth.login_required
def get_office_sitemap(state_token, office_token):
    try:
        # Validate input parameters
        if not state_token or not office_token:
            return jsonify({
                'error': 'Bad Request',
                'message': 'All parameters (state_token, office_token) are required',
                'status_code': 400
            }), 400
            
        # Using slash format to match your data
        state_office_token = f"{state_token}/{office_token}"
        
        # Query for all pages matching the state_office_token
        pages = OfficePage.query.filter_by(
            state_office_token=state_office_token
        ).all()
        
        if not pages:
            return jsonify({
                'error': 'Not Found',
                'message': f'No services found for office: {state_office_token}',
                'status_code': 404
            }), 404
        
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
        
    except Exception as e:
        app.logger.error(f"Error in get_office_sitemap: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred while processing your request',
            'status_code': 500
        }), 500

# GET endpoint for sitemap index with all distinct state_office_tokens
@app.route('/sitemap-index.json', methods=['GET'])
@auth.login_required
def get_sitemap_index():
    try:
        # Query for all distinct state_office_tokens
        distinct_tokens = db.session.query(OfficePage.state_office_token).distinct().all()
        
        if not distinct_tokens:
            return jsonify({
                'error': 'Not Found',
                'message': 'No office pages found in the database',
                'status_code': 404
            }), 404
        
        # Format the response
        tokens = [token[0] for token in distinct_tokens]
        
        return jsonify(tokens)
        
    except SQLAlchemyError as e:
        app.logger.error(f"Database error in get_sitemap_index: {str(e)}")
        return jsonify({
            'error': 'Database Error',
            'message': 'A database error occurred while retrieving the sitemap index',
            'status_code': 500
        }), 500
    except Exception as e:
        app.logger.error(f"Error in get_sitemap_index: {str(e)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred while processing your request',
            'status_code': 500
        }), 500

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
