import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
    
    _database_url = os.getenv("DATABASE_URL")
    if _database_url:
        # Check if sslmode is already in the URL
        if "sslmode" not in _database_url:
            if "?" in _database_url:
                SQLALCHEMY_DATABASE_URI = _database_url + "&sslmode=require"
            else:
                SQLALCHEMY_DATABASE_URI = _database_url + "?sslmode=require"
        else:
            SQLALCHEMY_DATABASE_URI = _database_url
    else:
        raise ValueError("DATABASE_URL environment variable is not set!")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'}
