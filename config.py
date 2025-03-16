import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
    
    # Ensure DATABASE_URL is set in Render's Environment Variables.
    # Append "?sslmode=require" to enforce SSL for remote PostgreSQL.
    _database_url = os.getenv("DATABASE_URL")
    if _database_url:
        SQLALCHEMY_DATABASE_URI = _database_url + "?sslmode=require"
    else:
        raise ValueError("DATABASE_URL environment variable is not set!")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'}
