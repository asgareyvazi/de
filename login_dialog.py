"""
Login Dialog - Dialog for user authentication
"""

import logging
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.user = None
        
        self.setWindowTitle("DrillMaster - Login")
        self.setFixedSize(400, 250)
        self.setModal(True)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("🔐 DrillMaster Login")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        layout.addWidget(header_label)
        
        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("👤 Username:"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter username")
        self.username_edit.setText("admin")  # Default username
        username_layout.addWidget(self.username_edit)
        layout.addLayout(username_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("🔑 Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setText("admin123")  # Default password
        password_layout.addWidget(self.password_edit)
        layout.addLayout(password_layout)
        
        # Remember me
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setChecked(True)
        layout.addWidget(self.remember_checkbox)
        
        # Error label (initially hidden)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                background-color: #fadbd8;
                padding: 5px;
                border-radius: 3px;
                border: 1px solid #f5b7b1;
            }
        """)
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("🚀 Login")
        self.login_btn.setDefault(True)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.login_btn.clicked.connect(self.authenticate)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect return pressed to login
        self.username_edit.returnPressed.connect(self.authenticate)
        self.password_edit.returnPressed.connect(self.authenticate)
        
    def authenticate(self):
        """Authenticate user"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            self.show_error("Please enter both username and password")
            return
            
        try:
            # Show loading
            self.login_btn.setText("🔐 Authenticating...")
            self.login_btn.setEnabled(False)
            QApplication.processEvents()
            
            # Authenticate using database manager
            user = self.db.authenticate_user(username, password)
            
            if user:
                self.user = {
                    'id': user.id,
                    'username': user.username,
                    'full_name': getattr(user, 'full_name', user.username),
                    'role': getattr(user, 'role', 'user'),
                    'email': getattr(user, 'email', f'{user.username}@drillmaster.com')
                }
                logger.info(f"User authenticated: {username}")
                self.accept()
            else:
                self.show_error("Invalid username or password")
                self.password_edit.clear()
                self.password_edit.setFocus()
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.show_error(f"Authentication error: {str(e)}")
        finally:
            self.login_btn.setText("🚀 Login")
            self.login_btn.setEnabled(True)
            
    def show_error(self, message):
        """Show error message"""
        self.error_label.setText(f"❌ {message}")
        self.error_label.setVisible(True)
        
    def get_user(self):
        """Get authenticated user data"""
        return self.user
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)