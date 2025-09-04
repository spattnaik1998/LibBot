import pyodbc
import os

def setup_database():
    """Set up database tables for user authentication system"""
    
    # Database connection parameters
    SERVER_NAME = "localhost"
    DATABASE_NAME = "Books"
    
    try:
        # Connection string
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={SERVER_NAME};"
            f"Database={DATABASE_NAME};"
            f"Trusted_Connection=yes;"
        )
        
        # Connect to database
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        
        # Read SQL setup file
        sql_file_path = os.path.join(os.path.dirname(__file__), 'database_setup.sql')
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        # Split by GO statements and execute each batch
        sql_batches = sql_script.split('GO')
        
        for batch in sql_batches:
            batch = batch.strip()
            if batch:
                try:
                    cursor.execute(batch)
                    connection.commit()
                except Exception as e:
                    print(f"Error executing SQL batch: {e}")
                    print(f"Batch content: {batch[:100]}...")
        
        print("Database setup completed successfully!")
        
        # Close connections
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

if __name__ == "__main__":
    setup_database()