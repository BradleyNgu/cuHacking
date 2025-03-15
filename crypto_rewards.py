# crypto_rewards.py - Token rewards system for waste sorting
import json
import os
import time
import uuid
import hashlib
import qrcode
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import requests

# Import database module
from database import SortingDatabase

class RecycleToken:
    """Token reward system for recycling activities"""
    
    def __init__(self, database=None):
        """Initialize the token system"""
        # Initialize database
        self.db = database if database else SortingDatabase()
        
        # Token value in USD
        self.token_value = 0.05  # $0.05 per can recycled
        
        # Current user
        self.current_user = None
        self.user_data = None
        
        # QR code for login
        self.login_qr = None
        self.session_id = None
        
        # Observers for balance changes
        self.observers = []
    
    def create_user(self, username, email=None, settings=None):
        """Create a new user"""
        return self.db.add_user(username, email, settings)
    
    def login_user(self, username):
        """Log in a user"""
        # Get user data
        user_data = self.db.get_user(username=username)
        
        if not user_data:
            return False, "User not found"
        
        # Update user's last login time
        self.db.update_user_login(username)
        
        # Set current user
        self.current_user = username
        self.user_data = user_data
        
        return True, user_data
    
    def logout_user(self):
        """Log out the current user"""
        self.current_user = None
        self.user_data = None
    
    def get_current_user(self):
        """Get current logged in user data"""
        if self.current_user:
            # Refresh user data
            self.user_data = self.db.get_user(username=self.current_user)
            return self.user_data
        return None
    
    def award_tokens(self, can_count, metadata=None):
        """Award tokens to the current user based on can count"""
        if not self.current_user or not self.user_data:
            return False, "No user logged in"
        
        # Calculate token amount
        token_amount = can_count
        
        # Add transaction
        if metadata is None:
            metadata = {}
        
        metadata["source"] = "can_recycling"
        metadata["can_count"] = can_count
        
        transaction_id = self.db.add_token_transaction(
            self.user_data["id"],
            token_amount,
            "award",
            None,
            metadata
        )
        
        # Refresh user data
        self.user_data = self.db.get_user(username=self.current_user)
        
        # Notify observers
        self._notify_observers()
        
        return True, token_amount
    
    def get_user_balance(self):
        """Get current user's token balance"""
        if not self.current_user or not self.user_data:
            return 0.0
        
        return self.db.get_user_balance(self.user_data["id"])
    
    def get_balance_usd(self):
        """Get user balance in USD"""
        balance = self.get_user_balance()
        return balance * self.token_value
    
    def get_user_transactions(self, limit=50):
        """Get current user's transactions"""
        if not self.current_user or not self.user_data:
            return []
        
        return self.db.get_user_transactions(self.user_data["id"], limit)
    
    def generate_login_qr(self):
        """Generate a QR code for login"""
        # Create a unique session ID
        self.session_id = str(uuid.uuid4())
        
        # URL that would be scanned (in a real implementation this would point to your app)
        login_url = f"recycletoken://login?session={self.session_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(login_url)
        qr.make(fit=True)
        
        self.login_qr = qr.make_image(fill_color="black", back_color="white")
        return self.login_qr
    
    def simulate_qr_login(self, username):
        """Simulate a login via QR code (for demonstration)"""
        # In a real implementation, this would verify the session against a database
        if not self.session_id:
            return False, "No active session"
        
        # Login the user
        return self.login_user(username)
    
    def add_observer(self, callback):
        """Add an observer to be notified of balance changes"""
        if callback not in self.observers:
            self.observers.append(callback)
    
    def remove_observer(self, callback):
        """Remove an observer"""
        if callback in self.observers:
            self.observers.remove(callback)
    
    def _notify_observers(self):
        """Notify all observers of a balance change"""
        for callback in self.observers:
            try:
                callback()
            except Exception as e:
                print(f"Error notifying observer: {e}")


class RecycleTokenUI:
    """UI for the RecycleToken system"""
    
    def __init__(self, root, token_system, sorter_app=None):
        """Initialize the token UI"""
        self.root = root
        self.token_system = token_system
        self.sorter_app = sorter_app  # Reference to the main sorter app
        
        # Add observer to update UI when balance changes
        self.token_system.add_observer(self.update_user_info)
        
        # Create a new window
        self.window = tk.Toplevel(root)
        self.window.title("RecycleToken Rewards")
        self.window.geometry("500x700")
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)  # Hide instead of close
        
        # Create UI elements
        self.create_ui()
        
        # Initially hide the window
        self.window.withdraw()
    
    def create_ui(self):
        """Create the UI elements"""
        # Main frame with scrolling
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas with scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Title
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        title_label = ttk.Label(
            title_frame, 
            text="RecycleToken Rewards", 
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=10)
        
        description = ttk.Label(
            title_frame,
            text="Earn tokens worth $0.05 for each recycled can!",
            font=("Arial", 10),
            wraplength=450
        )
        description.pack(pady=5)
        
        # Separator
        ttk.Separator(scrollable_frame).pack(fill=tk.X, padx=20, pady=10)
        
        # Login frame
        self.login_frame = ttk.LabelFrame(scrollable_frame, text="User Login", padding=20)
        self.login_frame.pack(fill=tk.X, padx=20, pady=10)
        
        login_form = ttk.Frame(self.login_frame)
        login_form.pack(fill=tk.X, pady=10)
        
        # Username
        ttk.Label(login_form, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(login_form, textvariable=self.username_var, width=25)
        username_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Email (for new users)
        ttk.Label(login_form, text="Email:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(login_form, textvariable=self.email_var, width=25)
        email_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Login/Register buttons
        button_frame = ttk.Frame(login_form)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        login_btn = ttk.Button(button_frame, text="Login", command=self.login)
        login_btn.pack(side=tk.LEFT, padx=5)
        
        register_btn = ttk.Button(button_frame, text="Register", command=self.register)
        register_btn.pack(side=tk.LEFT, padx=5)
        
        # Alternatively, scan QR code
        qr_frame = ttk.Frame(self.login_frame)
        qr_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(qr_frame, text="Or scan QR code with mobile app:").pack(pady=5)
        
        # Generate QR code
        qr_img = self.token_system.generate_login_qr()
        qr_img = qr_img.resize((150, 150))
        self.qr_photo = ImageTk.PhotoImage(qr_img)
        
        qr_label = ttk.Label(qr_frame, image=self.qr_photo)
        qr_label.pack(pady=10)
        
        # Simulate QR login button (for demo purposes)
        simulate_frame = ttk.Frame(self.login_frame)
        simulate_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            simulate_frame, 
            text="Simulate QR Scan", 
            command=lambda: self.token_system.simulate_qr_login(self.username_var.get())
        ).pack()
        
        # User info frame (hidden by default)
        self.user_frame = ttk.LabelFrame(scrollable_frame, text="User Information", padding=20)
        
        user_content = ttk.Frame(self.user_frame)
        user_content.pack(fill=tk.X, pady=10)
        
        # Username display
        ttk.Label(user_content, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_label = ttk.Label(user_content, text="")
        self.username_label.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # User balance
        ttk.Label(user_content, text="Token Balance:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.balance_label = ttk.Label(user_content, text="0", font=("Arial", 12, "bold"))
        self.balance_label.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # USD Value
        ttk.Label(user_content, text="USD Value:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.usd_label = ttk.Label(user_content, text="$0.00", font=("Arial", 12, "bold"))
        self.usd_label.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Logout button
        logout_btn = ttk.Button(user_content, text="Logout", command=self.logout)
        logout_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Transaction history frame
        self.history_frame = ttk.LabelFrame(scrollable_frame, text="Transaction History", padding=20)
        
        # Treeview for transactions
        self.transaction_tree = ttk.Treeview(
            self.history_frame, 
            columns=("date", "type", "amount"), 
            show="headings", 
            height=10
        )
        self.transaction_tree.heading("date", text="Date")
        self.transaction_tree.heading("type", text="Type")
        self.transaction_tree.heading("amount", text="Amount")
        
        self.transaction_tree.column("date", width=150)
        self.transaction_tree.column("type", width=100)
        self.transaction_tree.column("amount", width=100)
        
        self.transaction_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Auto-reward toggle
        settings_frame = ttk.LabelFrame(scrollable_frame, text="Settings", padding=20)
        settings_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.auto_reward_var = tk.BooleanVar(value=False)
        auto_reward_chk = ttk.Checkbutton(
            settings_frame, 
            text="Automatically reward tokens for recycled cans", 
            variable=self.auto_reward_var
        )
        auto_reward_chk.pack(anchor=tk.W, pady=5)
        
        # Exchange rate info
        exchange_frame = ttk.Frame(settings_frame)
        exchange_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(exchange_frame, text="Token Value:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(
            exchange_frame, 
            text=f"${self.token_system.token_value:.2f} USD per token", 
            font=("Arial", 10, "bold")
        ).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Check if a user is already logged in
        current_user = self.token_system.get_current_user()
        if current_user:
            self.username_var.set(self.token_system.current_user)
            self.update_user_info()
    
    def show_window(self):
        """Show the token UI window"""
        self.window.deiconify()
        self.window.lift()
        
        # Refresh data if user is logged in
        if self.token_system.current_user:
            self.update_user_info()
    
    def hide_window(self):
        """Hide the token UI window"""
        self.window.withdraw()
    
    def login(self):
        """Login with the entered username"""
        username = self.username_var.get().strip()
        if not username:
            messagebox.showwarning("Login Error", "Please enter a username")
            return
        
        success, result = self.token_system.login_user(username)
        if success:
            self.update_user_info()
            messagebox.showinfo("Login Success", f"Welcome, {username}!")
        else:
            messagebox.showerror("Login Error", result)
    
    def register(self):
        """Register a new user"""
        username = self.username_var.get().strip()
        email = self.email_var.get().strip()
        
        if not username:
            messagebox.showwarning("Registration Error", "Please enter a username")
            return
        
        user_id, message = self.token_system.create_user(username, email)
        
        if user_id:
            messagebox.showinfo("Registration Success", f"User '{username}' created successfully!")
            # Login the new user
            self.login()
        else:
            messagebox.showerror("Registration Error", message)
    
    def logout(self):
        """Logout the current user"""
        self.token_system.logout_user()
        self.username_var.set("")
        self.email_var.set("")
        
        # Hide user frames
        self.user_frame.pack_forget()
        self.history_frame.pack_forget()
        
        # Show login frame
        self.login_frame.pack(fill=tk.X, padx=20, pady=10)
        
        messagebox.showinfo("Logout", "You have been logged out.")
    
    def update_user_info(self):
        """Update user information display"""
        user = self.token_system.get_current_user()
        if not user:
            return
        
        # Hide login frame
        self.login_frame.pack_forget()
        
        # Show user frame
        self.user_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Update user info
        self.username_label.config(text=user.get("username", ""))
        
        # Update balance
        balance = self.token_system.get_user_balance()
        self.balance_label.config(text=str(balance))
        
        # Update USD value
        usd_value = self.token_system.get_balance_usd()
        self.usd_label.config(text=f"${usd_value:.2f}")
        
        # Show transaction history
        self.history_frame.pack(fill=tk.X, padx=20, pady=10)
        self.update_transaction_history()
    
    def update_transaction_history(self):
        """Update transaction history display"""
        # Clear current items
        for item in self.transaction_tree.get_children():
            self.transaction_tree.delete(item)
        
        # Get transactions
        transactions = self.token_system.get_user_transactions()
        
        # Add to treeview
        for transaction in transactions:
            date = datetime.fromisoformat(transaction["timestamp"]).strftime("%Y-%m-%d %H:%M")
            
            # Format transaction type
            tx_type = transaction["transaction_type"].capitalize()
            
            # Add to treeview
            self.transaction_tree.insert(
                "", 
                "end", 
                values=(date, tx_type, f"{transaction['amount']:.2f}")
            )
    
    def award_tokens_for_cans(self, count):
        """Award tokens for recycled cans"""
        if not self.token_system.current_user or not self.auto_reward_var.get():
            return None
        
        # Generate metadata
        metadata = {
            "source": "waste_sorter",
            "automatic": True,
            "timestamp": datetime.now().isoformat()
        }
        
        success, amount = self.token_system.award_tokens(count, metadata)
        if success:
            self.update_user_info()
            return f"Awarded {amount} tokens for recycling {count} cans!"
        return None


# Example of how to use this in the main application
if __name__ == "__main__":
    # Create database
    db = SortingDatabase()
    
    # Create token system
    token_system = RecycleToken(db)
    
    # Create UI
    root = tk.Tk()
    root.title("Token System Test")
    
    token_ui = RecycleTokenUI(root, token_system)
    token_ui.show_window()
    
    # Create demo button
    ttk.Button(root, text="Show Token UI", command=token_ui.show_window).pack(pady=20)
    
    root.mainloop()