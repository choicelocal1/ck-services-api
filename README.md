# Office Services API

A Flask REST API for managing office service pages with authentication. This API allows you to create and retrieve office service information through secure endpoints.

## Features

- Secure authentication using HTTP Basic Auth
- Create new office service pages
- Retrieve office service information
- SQLite database for development, PostgreSQL for production
- Ready for Heroku deployment

## Installation

### Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)

### Setup Steps

1. Clone the repository
   ```bash
   git clone https://github.com/choicelocal1/ck-services-api.git
   cd ck-services-api
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables in `.env`
   ```
   FLASK_APP=app.py
   FLASK_DEBUG=True
   DATABASE_URL=sqlite:///offices.db
   ```

5. Initialize the database
   ```bash
   python init_db.py
   ```

6. Create a user for API authentication
   ```bash
   python create_user.py <username> <password>
   ```

7. Run the application
   ```bash
   flask run
   ```

## API Endpoints

All endpoints require HTTP Basic Authentication.

### GET Office Page

```
GET /offices/:state_token/:office_token/areas/:area_served_token/services/:service_token/page
```

Example:
```bash
curl -u username:password "http://localhost:5000/offices/tennessee/chattanooga/areas/lookout-mountain/services/care-services/page"
```

### Create Office Page

```
POST /offices
```

Example:
```bash
curl -X POST "http://localhost:5000/offices" \
  -u username:password \
  -H "Content-Type: application/json" \
  -d '{
    "state_office_token": "tennessee/chattanooga",
    "area_served_token": "lookout-mountain",
    "service_token": "care-services",
    "meta_title": "Office Services Title",
    "meta_description": "Office services description",
    "page_title": "Page Title",
    "page_content": "Page content goes here"
  }'
```

## Database Management

- List users: `python list_users.py`
- List pages: `python list_pages.py`

## Deployment

This application is ready for deployment to Heroku. See the deployment instructions in the documentation for more details.

## Security Notes

- Always use strong passwords for API users
- The .env file contains sensitive information and should not be committed to version control
- In production, use HTTPS to secure API communications

## License

[MIT License](LICENSE)
