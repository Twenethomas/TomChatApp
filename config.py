class Config:
    SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://@localhost/TomChat?driver=ODBC+Driver+18+for+SQL+Server&Trusted_Connection=yes&TrustServerCertificate=yes'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '1234'  # Required for Flask sessions and flash messages
    