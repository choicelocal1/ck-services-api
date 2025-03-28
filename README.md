# Office Services API

A Flask REST API for managing office service pages with authentication. This API allows you to create and retrieve office service information through secure endpoints.

## Features

- Secure authentication using HTTP Basic Auth
- Create new office service pages
- Retrieve office service information
- Multiple endpoints for flexible data retrieval
- SQLite database for development, PostgreSQL for production
- Automated daily import from Google Sheets
- Comprehensive error handling
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
   GOOGLE_API_KEY=your_google_api_key
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

### Health Check

```
GET /
```

Returns the health status of the API.

### GET Office Page

```
GET /offices/:state_token/:office_token/areas/:area_served_token/services/:service_token/page
```

Example:
```bash
curl -u username:password "http://localhost:5000/offices/tennessee/chattanooga/areas/lookout-mountain/services/care-services/page"
```

### Get Services by Area

```
GET /offices/:state_token/:office_token/areas/:area_served_token/services
```

Returns all services available for a specific office location and area.

### Get Services by State, Area, and Service (without specifying office)

```
GET /services/:state_token/:area_served_token/:service_token
```

Returns service information based on state, area, and service tokens without requiring an office token.

### Get Office Sitemap

```
GET /offices/:state_token/:office_token/areas/services/sitemap.xml
```

Returns a JSON list of all areas and services for a specific office location.

### Get All Office Locations

```
GET /sitemap-index.json
```

Returns a list of all unique state_office_tokens in the database.

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

## Error Handling

The API provides comprehensive error handling with consistent JSON responses:

```json
{
  "error": "Error Type",
  "message": "Detailed description of the error",
  "status_code": 400
}
```

Common error codes:
- 400: Bad Request - Missing or invalid parameters
- 401: Unauthorized - Authentication required
- 404: Not Found - Resource not found
- 409: Conflict - Resource already exists
- 500: Internal Server Error - Server-side error

## Database Management

- List users: `python list_users.py`
- List pages: `python list_pages.py`

## Google Sheets Integration

The API includes functionality to automatically import data from a Google Sheet and refresh the database daily.

### Google Sheet Format

The Google Sheet should contain the following columns:
- `state_office_token`
- `area_served_token`
- `service_token`
- `meta_title`
- `meta_description`
- `page_title`
- `page_content`

### Manual Import

To manually trigger a data import from Google Sheets:

```bash
python import_sheet.py
```

### Scheduled Import Setup

For Heroku deployment, follow these steps to set up automatic daily imports:

1. Add the Heroku Scheduler add-on:
   ```bash
   heroku addons:create scheduler:standard
   ```

2. Configure the Google API Key:
   ```bash
   heroku config:set GOOGLE_API_KEY=your_google_api_key
   ```

3. Open the Scheduler dashboard:
   ```bash
   heroku addons:open scheduler
   ```

4. Create a new scheduled task:
   - Command: `python import_sheet.py`
   - Frequency: "Every day at..."
   - Time: Select 5:00 AM in your local time zone (Eastern Time)
     - 5:00 AM EST = 10:00 AM UTC (during standard time)
     - 5:00 AM EDT = 9:00 AM UTC (during daylight saving time)
   - Click "Save Job"

5. Verify scheduled imports by checking logs:
   ```bash
   heroku logs --tail --ps scheduler
   ```

## Deployment

### Heroku Deployment

1. Create a Heroku account and install the Heroku CLI
2. Login to Heroku:
   ```bash
   heroku login
   ```

3. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```

4. Add PostgreSQL database:
   ```bash
   heroku addons:create heroku-postgresql:essential-0
   ```

5. Configure environment variables:
   ```bash
   heroku config:set GOOGLE_API_KEY=your_google_api_key
   ```

6. Deploy to Heroku:
   ```bash
   git push heroku main
   ```

7. Initialize the database:
   ```bash
   heroku run python init_db.py
   ```

8. Create a user for API authentication:
   ```bash
   heroku run python create_user.py <username> <password>
   ```

## Security Notes

- Always use strong passwords for API users
- The .env file contains sensitive information and should not be committed to version control
- Store API keys and credentials as environment variables, never in code
- In production, use HTTPS to secure API communications

## License

[MIT License](LICENSE)
