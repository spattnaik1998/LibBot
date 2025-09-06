"""Database tools for chatbot agents to interact with SQL Server"""
import pyodbc
from typing import List, Dict, Optional, Any
from config import settings

class ChatbotDatabase:
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
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
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
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_book_by_title(self, title: str) -> Optional[Dict]:
        """Get book details by title"""
        query = "SELECT * FROM book_names WHERE title LIKE ?"
        results = self.execute_query(query, (f"%{title}%",))
        return results[0] if results else None
    
    def get_books_by_partial_title(self, search_term: str) -> List[Dict]:
        """Get books matching partial title or author"""
        query = """
        SELECT * FROM book_names 
        WHERE title LIKE ? OR author LIKE ? 
        ORDER BY title
        """
        search_pattern = f"%{search_term}%"
        return self.execute_query(query, (search_pattern, search_pattern)) or []
    
    def get_books_by_author(self, author_name: str) -> List[Dict]:
        """Get books by specific author"""
        query = "SELECT * FROM book_names WHERE author LIKE ? ORDER BY title"
        return self.execute_query(query, (f"%{author_name}%",)) or []
    
    def update_book_quantity(self, title: str, new_qty: int) -> bool:
        """Update book quantity"""
        query = "UPDATE book_names SET Qty = ? WHERE title = ?"
        return self.execute_non_query(query, (new_qty, title))
    
    def get_user_credits(self, user_id: int) -> Optional[int]:
        """Get user's available credits"""
        query = "SELECT available_credits FROM users WHERE user_id = ?"
        results = self.execute_query(query, (user_id,))
        return results[0]["available_credits"] if results else None
    
    def update_user_credits(self, user_id: int, new_credits: int) -> bool:
        """Update user's credits"""
        query = "UPDATE users SET available_credits = ? WHERE user_id = ?"
        return self.execute_non_query(query, (new_credits, user_id))
    
    def buy_book_transaction(self, user_id: int, book_title: str, quantity: int) -> Dict[str, Any]:
        """Execute buy book transaction (deduct quantity and credits)"""
        try:
            # Get book details
            book = self.get_book_by_title(book_title)
            if not book:
                return {"success": False, "error": "Book not found"}
            
            if book["Qty"] < quantity:
                return {"success": False, "error": f"Not enough books in stock. Available: {book['Qty']}"}
            
            # Get user credits
            current_credits = self.get_user_credits(user_id)
            if current_credits is None:
                return {"success": False, "error": "User not found"}
            
            total_cost = quantity * 20  # 20 credits per book
            if current_credits < total_cost:
                return {"success": False, "error": f"Not enough credits. Required: {total_cost}, Available: {current_credits}"}
            
            # Update book quantity - use the exact title from the database record
            new_book_qty = book["Qty"] - quantity
            actual_book_title = book["title"]  # Use exact title from database
            if not self.update_book_quantity(actual_book_title, new_book_qty):
                return {"success": False, "error": "Failed to update book quantity"}
            
            # Update user credits
            new_credits = current_credits - total_cost
            if not self.update_user_credits(user_id, new_credits):
                # Rollback book quantity change - use exact title for rollback too
                self.update_book_quantity(actual_book_title, book["Qty"])
                return {"success": False, "error": "Failed to update user credits"}
            
            return {
                "success": True,
                "book_title": book["title"],
                "quantity_purchased": quantity,
                "credits_spent": total_cost,
                "remaining_credits": new_credits,
                "remaining_book_qty": new_book_qty
            }
            
        except Exception as e:
            return {"success": False, "error": f"Transaction failed: {str(e)}"}
    
    def return_book_transaction(self, user_id: int, book_title: str, quantity: int) -> Dict[str, Any]:
        """Execute return book transaction (add quantity and credits)"""
        try:
            # Get book details
            book = self.get_book_by_title(book_title)
            if not book:
                return {"success": False, "error": "Book not found"}
            
            # Get user credits
            current_credits = self.get_user_credits(user_id)
            if current_credits is None:
                return {"success": False, "error": "User not found"}
            
            # Update book quantity - use the exact title from the database record
            new_book_qty = book["Qty"] + quantity
            actual_book_title = book["title"]  # Use exact title from database
            if not self.update_book_quantity(actual_book_title, new_book_qty):
                return {"success": False, "error": "Failed to update book quantity"}
            
            # Update user credits
            credits_refunded = quantity * 20  # 20 credits per book
            new_credits = current_credits + credits_refunded
            if not self.update_user_credits(user_id, new_credits):
                # Rollback book quantity change - use exact title for rollback too
                self.update_book_quantity(actual_book_title, book["Qty"])
                return {"success": False, "error": "Failed to update user credits"}
            
            return {
                "success": True,
                "book_title": book["title"],
                "quantity_returned": quantity,
                "credits_refunded": credits_refunded,
                "new_credits_total": new_credits,
                "new_book_qty": new_book_qty
            }
            
        except Exception as e:
            return {"success": False, "error": f"Transaction failed: {str(e)}"}
    
    def add_credits_transaction(self, user_id: int, credits_to_add: int) -> Dict[str, Any]:
        """Add credits to user account"""
        try:
            current_credits = self.get_user_credits(user_id)
            if current_credits is None:
                return {"success": False, "error": "User not found"}
            
            new_credits = current_credits + credits_to_add
            if not self.update_user_credits(user_id, new_credits):
                return {"success": False, "error": "Failed to add credits"}
            
            return {
                "success": True,
                "credits_added": credits_to_add,
                "new_credits_total": new_credits
            }
            
        except Exception as e:
            return {"success": False, "error": f"Transaction failed: {str(e)}"}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

# Global database instance for chatbot
chatbot_db = ChatbotDatabase()