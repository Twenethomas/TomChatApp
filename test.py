import pyodbc

# Replace with your connection details
server = 'localhost'
database = 'TomChat'
driver = 'ODBC Driver 17 for SQL Server'

# For Windows Authentication
connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;'

# For SQL Server Authentication
# connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID=username;PWD=password;TrustServerCertificate=yes;'

try:
    conn = pyodbc.connect(connection_string)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")