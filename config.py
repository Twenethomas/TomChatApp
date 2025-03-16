import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
    # ✅ Securely load database URL from environment variables
    SQLALCHEMY_DATABASE_URI = os.getenv("postgresql://thomas:nFYYwWVe5DAYmKWyhsb9fufxmHn9ryOc@dpg-cvb8lnqn91rc739e3q00-a.oregon-postgres.render.com/tomchat_db_brky") + "?sslmode=require"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'}
