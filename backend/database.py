import pyodbc
from config import settings
from typing import Optional

class DatabaseConnection:
    def __init__(self):
        self.connection = None
    
    def connect(self) -> bool:
        """Establish connection to SQL Server"""
        try:
            connection_string = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server={settings.SERVER_NAME};"
                f"Database={settings.DATABASE_NAME};"
                f"Trusted_Connection=yes;"
            )
            
            self.connection = pyodbc.connect(connection_string)
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[list]:
        """Execute a SELECT query and return results"""
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            print(f"Query execution error: {e}")
            return None
    
    def execute_non_query(self, query: str, params: tuple = None) -> bool:
        """Execute INSERT, UPDATE, DELETE queries"""
        if not self.connection:
            if not self.connect():
                return False
        
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Non-query execution error: {e}")
            self.connection.rollback()
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

# Global database instance
db = DatabaseConnection()