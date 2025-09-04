import pyodbc
import pandas as pd
from typing import Optional
import subprocess
import socket

class SQLServerExtractor:
    def __init__(self, server_name: str, database_name: str):
        """
        Initialize SQL Server connection parameters
        
        Args:
            server_name: SQL Server instance name (e.g., 'LAPTOP-FO95TRO')
            database_name: Database name (e.g., 'Books')
        """
        self.server_name = server_name
        self.database_name = database_name
        self.connection = None
        
    def check_sql_server_services(self):
        """Check if SQL Server services are running"""
        print("Checking SQL Server services...")
        try:
            result = subprocess.run(['sc', 'query', 'MSSQLSERVER'], 
                                  capture_output=True, text=True)
            if 'RUNNING' in result.stdout:
                print("  - SQL Server (MSSQLSERVER): RUNNING")
            else:
                print("  - SQL Server (MSSQLSERVER): NOT RUNNING")
                print("    To start: sc start MSSQLSERVER")
        except Exception as e:
            print(f"  - Could not check MSSQLSERVER service: {e}")
        
        # Check SQL Server Browser
        try:
            result = subprocess.run(['sc', 'query', 'SQLBrowser'], 
                                  capture_output=True, text=True)
            if 'RUNNING' in result.stdout:
                print("  - SQL Server Browser: RUNNING")
            else:
                print("  - SQL Server Browser: NOT RUNNING")
        except Exception as e:
            print(f"  - Could not check SQLBrowser service: {e}")
    
    def test_port_connectivity(self, host='localhost', port=1433):
        """Test if SQL Server port is accessible"""
        print(f"Testing connectivity to {host}:{port}...")
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            print(f"  - Port {port} is accessible")
            return True
        except Exception as e:
            print(f"  - Port {port} is NOT accessible: {e}")
            return False

    def connect(self) -> bool:
        """
        Establish connection to SQL Server using Windows Authentication
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        # Run diagnostics first
        self.check_sql_server_services()
        print()
        self.test_port_connectivity()
        print()
        
        # List available drivers for diagnostics
        print("Available ODBC drivers:")
        drivers = pyodbc.drivers()
        for driver in drivers:
            print(f"  - {driver}")
        
        if not drivers:
            print("No ODBC drivers found!")
            return False
            
        # Try different connection approaches
        connection_strings = [
            # ODBC Driver 17 for SQL Server
            f"Driver={{ODBC Driver 17 for SQL Server}};Server={self.server_name};Database={self.database_name};Trusted_Connection=yes;",
            # ODBC Driver 13 for SQL Server  
            f"Driver={{ODBC Driver 13 for SQL Server}};Server={self.server_name};Database={self.database_name};Trusted_Connection=yes;",
            # SQL Server Native Client 11.0
            f"Driver={{SQL Server Native Client 11.0}};Server={self.server_name};Database={self.database_name};Trusted_Connection=yes;",
            # SQL Server
            f"Driver={{SQL Server}};Server={self.server_name};Database={self.database_name};Trusted_Connection=yes;",
            # Try with localhost
            f"Driver={{ODBC Driver 17 for SQL Server}};Server=localhost;Database={self.database_name};Trusted_Connection=yes;",
            # Try with (local)
            f"Driver={{ODBC Driver 17 for SQL Server}};Server=(local);Database={self.database_name};Trusted_Connection=yes;",
        ]
        
        for i, connection_string in enumerate(connection_strings):
            try:
                print(f"\nAttempt {i+1}: Trying connection string:")
                print(f"  {connection_string}")
                
                self.connection = pyodbc.connect(connection_string, timeout=10)
                print(f"SUCCESS: Connected to {self.server_name}/{self.database_name}")
                return True
                
            except pyodbc.Error as e:
                print(f"FAILED: {e}")
                continue
        
        print("\nAll connection attempts failed!")
        print("\nTroubleshooting steps:")
        print("1. Check if SQL Server is running:")
        print("   - Open Services (services.msc)")
        print("   - Look for 'SQL Server (MSSQLSERVER)' or similar")
        print("   - Ensure it's running")
        print("\n2. Check SQL Server Configuration:")
        print("   - Open SQL Server Configuration Manager")
        print("   - Enable TCP/IP and Named Pipes protocols")
        print("   - Restart SQL Server service")
        print("\n3. Verify server name:")
        print(f"   - Current: {self.server_name}")
        print("   - Try: localhost, (local), or your computer name")
        print("\n4. Check Windows Authentication:")
        print("   - Ensure your Windows user has access to SQL Server")
        
        return False
    
    def extract_book_names(self) -> Optional[pd.DataFrame]:
        """
        Extract all data from the book_names table
        
        Returns:
            pd.DataFrame: DataFrame containing book_names data, or None if error
        """
        if not self.connection:
            print("No active connection. Please connect first.")
            return None
            
        try:
            query = "SELECT * FROM book_names"
            df = pd.read_sql(query, self.connection)
            print(f"Successfully extracted {len(df)} rows from book_names table")
            return df
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            return None
    
    def extract_custom_query(self, query: str) -> Optional[pd.DataFrame]:
        """
        Execute custom SQL query
        
        Args:
            query: SQL query string
            
        Returns:
            pd.DataFrame: Query results, or None if error
        """
        if not self.connection:
            print("No active connection. Please connect first.")
            return None
            
        try:
            df = pd.read_sql(query, self.connection)
            print(f"Query executed successfully, returned {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    def close_connection(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            print("Connection closed")

def main():
    # Configuration - update these values for your setup
    SERVER_NAME = "localhost"       # Use localhost since TCP/IP is working
    DATABASE_NAME = "Books"         # Your database name
    
    # Initialize extractor
    extractor = SQLServerExtractor(SERVER_NAME, DATABASE_NAME)
    
    # Connect to database
    if not extractor.connect():
        return
    
    try:
        # Extract data from book_names table
        book_data = extractor.extract_book_names()
        
        if book_data is not None:
            # Display basic information about the data
            print(f"\nDataFrame shape: {book_data.shape}")
            print(f"Columns: {list(book_data.columns)}")
            print("\nFirst 5 rows:")
            print(book_data.head())
            
            # Save to CSV (optional)
            output_file = "book_names_export.csv"
            book_data.to_csv(output_file, index=False)
            print(f"\nData exported to {output_file}")
            
            # Example of custom query
            print("\n" + "="*50)
            print("Example: Custom query for specific books")
            
            custom_query = """
            SELECT TOP 10 * 
            FROM book_names 
            ORDER BY title DESC
            """
            
            recent_books = extractor.extract_custom_query(custom_query)
            if recent_books is not None:
                print(recent_books)
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Always close the connection
        extractor.close_connection()

if __name__ == "__main__":
    main()