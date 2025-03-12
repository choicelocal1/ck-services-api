# Office Services API

A Flask REST API for managing office service pages.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env`
4. Initialize the database: `python init_db.py`
5. Run the application: `flask run`

## API Endpoints

- `GET /offices/:state_token/:office_token/areas/:area_served_token/services/:service_token/page`: Get office page
- `POST /offices`: Create a new office page (requires authentication)

## Authentication

This API uses HTTP Basic Authentication. Create users with:

