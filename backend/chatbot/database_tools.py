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
    
    def buy_multiple_books_transaction(self, user_id: int, book_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute multiple book purchases in a single atomic transaction
        
        Args:
            user_id: The user making the purchase
            book_requests: List of dicts with keys: 'title', 'quantity'
                          Example: [{'title': 'Book 1', 'quantity': 2}, {'title': 'Book 2', 'quantity': 1}]
        
        Returns:
            Dict with success status and transaction details
        """
        try:
            # Validate all books exist and have sufficient quantity first
            validated_books = []
            total_cost = 0
            
            for request in book_requests:
                book_title = request['title']
                quantity = request['quantity']
                
                if quantity <= 0:
                    return {"success": False, "error": f"Invalid quantity for '{book_title}': {quantity}"}
                
                # Get book details
                book = self.get_book_by_title(book_title)
                if not book:
                    return {"success": False, "error": f"Book not found: '{book_title}'"}
                
                if book["Qty"] < quantity:
                    return {"success": False, "error": f"Not enough copies of '{book['title']}'. Available: {book['Qty']}, Requested: {quantity}"}
                
                cost = quantity * 20  # 20 credits per book
                total_cost += cost
                
                validated_books.append({
                    'book': book,
                    'requested_quantity': quantity,
                    'cost': cost,
                    'actual_title': book['title']  # Use exact title from database
                })
            
            # Check user has enough credits for total purchase
            current_credits = self.get_user_credits(user_id)
            if current_credits is None:
                return {"success": False, "error": "User not found"}
            
            if current_credits < total_cost:
                return {"success": False, "error": f"Not enough credits. Required: {total_cost}, Available: {current_credits}"}
            
            # Execute all transactions atomically
            purchased_books = []
            
            # Update book quantities
            for book_data in validated_books:
                book = book_data['book']
                quantity = book_data['requested_quantity']
                actual_title = book_data['actual_title']
                
                new_book_qty = book["Qty"] - quantity
                if not self.update_book_quantity(actual_title, new_book_qty):
                    # Rollback previous book quantity updates
                    for prev_book in purchased_books:
                        self.update_book_quantity(prev_book['actual_title'], prev_book['original_qty'])
                    return {"success": False, "error": f"Failed to update quantity for '{actual_title}'"}
                
                purchased_books.append({
                    'title': actual_title,
                    'quantity_purchased': quantity,
                    'cost': book_data['cost'],
                    'remaining_qty': new_book_qty,
                    'original_qty': book["Qty"]  # For rollback
                })
            
            # Update user credits
            new_credits = current_credits - total_cost
            if not self.update_user_credits(user_id, new_credits):
                # Rollback all book quantity changes
                for book_data in purchased_books:
                    self.update_book_quantity(book_data['title'], book_data['original_qty'])
                return {"success": False, "error": "Failed to update user credits"}
            
            return {
                "success": True,
                "purchased_books": purchased_books,
                "total_books_purchased": sum(book['quantity_purchased'] for book in purchased_books),
                "total_credits_spent": total_cost,
                "remaining_credits": new_credits,
                "transaction_summary": f"Successfully purchased {len(purchased_books)} different books"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Multiple book transaction failed: {str(e)}"}
    

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