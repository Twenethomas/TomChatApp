import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "1234")
    # ✅ Securely load database URL from environment variables
    SQLALCHEMY_DATABASE_URI = os.getenv("postgresql://thomas:nFYYwWVe5DAYmKWyhsb9fufxmHn9ryOc@dpg-cvb8lnqn91rc739e3q00-a.oregon-postgres.render.com/tomchat_db_brky") 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'}
