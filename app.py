"""
DrillMaster - Main Application with Startup System
"""
import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

# Import from our modules
from core.database import DatabaseManager
from dialogs.login_dialog import LoginDialog
from dialogs.startup_dialog import StartupDialog
from main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('drillmaster.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DrillMasterApp(QApplication):
    """Main application class with startup management"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # Set application metadata
        self.setApplicationName("DrillMaster")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("DrillMaster Inc.")
        
        # Set font and style
        self.setFont(QFont("Segoe UI", 10))
        self.setStyle("Fusion")
        
        # High DPI support
        self.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # Initialize
        self.db_manager = None
        self.user = None
        self.main_window = None
        self.startup_result = None
        
        self.initialize()
    
    def initialize(self):
        """Initialize application"""
        try:
            logger.info("Starting DrillMaster application...")
            
            # Initialize database
            self.db_manager = DatabaseManager()
            if not self.db_manager.initialize():
                QMessageBox.critical(
                    None,
                    "Database Error",
                    "Failed to initialize database. Application will exit."
                )
                sys.exit(1)
            
            # Check if database is empty
            if self.is_database_empty():
                self.show_welcome_message()
            
            # Show login dialog
            if not self.show_login():
                logger.info("Login cancelled by user")
                sys.exit(0)
            
            # Show startup dialog
            if not self.show_startup():
                logger.info("Startup cancelled by user")
                sys.exit(0)
            
            # Create and show main window
            self.create_main_window()
            
            # Connect cleanup
            self.aboutToQuit.connect(self.cleanup)
            
            logger.info("Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            QMessageBox.critical(
                None,
                "Initialization Error",
                f"Failed to initialize application:\n\n{str(e)}"
            )
            sys.exit(1)
    
    def is_database_empty(self):
        """Check if database has any data"""
        try:
            session = self.db_manager.create_session()
            from core.database import Company, Project, Well, User
            
            # Check for any data
            company_count = session.query(Company).count()
            project_count = session.query(Project).count()
            well_count = session.query(Well).count()
            user_count = session.query(User).count()
            
            session.close()
            
            # If only default user exists and no other data
            return company_count == 0 and project_count == 0 and well_count == 0
            
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            return False
    
    def show_welcome_message(self):
        """Show welcome message for first-time users"""
        reply = QMessageBox.question(
            None,
            "Welcome to DrillMaster!",
            "👋 Welcome to DrillMaster!\n\n"
            "It looks like this is your first time using the application.\n"
            "Would you like to create a sample project to get started?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.create_sample_data()
    
    def create_sample_data(self):
        """Create sample data for first-time users"""
        try:
            from datetime import date
            session = self.db_manager.create_session()
            from core.database import Company, Project, Well
            
            # Create sample company
            company = Company(
                name="Demo Drilling Company",
                code="DDC001",
                address="123 Oilfield Ave, Houston, TX",
                contact_person="Demo Manager",
                contact_email="demo@drillmaster.com",
                contact_phone="+1-713-555-0123"
            )
            session.add(company)
            session.commit()
            
            # Create sample project
            project = Project(
                company_id=company.id,
                name="Demo Exploration Project",
                code="DEMO_001",
                location="Demo Field, Texas",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                status="Active",
                manager="Project Manager",
                budget=1000000.00,
                currency="USD"
            )
            session.add(project)
            session.commit()
            
            # Create sample well
            well = Well(
                project_id=project.id,
                name="Demo Well #1",
                code="DEMO_WELL_001",
                well_type="Exploration",
                purpose="Oil Production",
                status="Planning",
                field_name="Demo Field",
                location="Texas, USA",
                target_depth=3000.0,
                water_depth=0.0,
                elevation=100.0
            )
            session.add(well)
            session.commit()
            
            logger.info("Sample data created successfully")
            
            QMessageBox.information(
                None,
                "Sample Data Created",
                "✅ Sample data has been created successfully!\n\n"
                "You can now explore the application with this demo project."
            )
            
        except Exception as e:
            logger.error(f"Error creating sample data: {e}")
            QMessageBox.warning(
                None,
                "Sample Data Error",
                f"Could not create sample data:\n\n{str(e)}"
            )
        finally:
            try:
                session.close()
            except:
                pass
    
    def show_login(self):
        """Show login dialog"""
        try:
            login_dialog = LoginDialog(self.db_manager)
            
            if login_dialog.exec() == QDialog.Accepted:
                self.user = login_dialog.get_user()
                if self.user:
                    logger.info(f"User authenticated: {self.user['username']}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            QMessageBox.critical(
                None,
                "Login Error",
                f"Failed to authenticate:\n\n{str(e)}"
            )
            return False
    
    def show_startup(self):
        """Show startup dialog to select/create project/well"""
        try:
            startup_dialog = StartupDialog(self.db_manager)
            
            if startup_dialog.exec() == QDialog.Accepted:
                self.startup_result = startup_dialog.get_result()
                
                if not self.startup_result:
                    logger.warning("Startup dialog returned no result")
                    return False
                
                logger.info(f"Startup result: {self.startup_result}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Startup dialog error: {e}")
            # Fallback: create main window without startup result
            self.startup_result = None
            return True  # Continue anyway
    
    def create_main_window(self):
        """Create and show main window"""
        try:
            self.main_window = MainWindow(
                db_manager=self.db_manager,
                user=self.user,
                startup_result=self.startup_result
            )
            
            self.main_window.show()
            
            # Center the window
            screen = self.primaryScreen()
            screen_geometry = screen.availableGeometry()
            window_geometry = self.main_window.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.main_window.move(window_geometry.topLeft())
            
            # Bring window to front
            self.main_window.raise_()
            self.main_window.activateWindow()
            
            logger.info("Main window created and shown")
            
        except Exception as e:
            logger.error(f"Error creating main window: {e}")
            QMessageBox.critical(
                None,
                "Window Error",
                f"Failed to create main window:\n\n{str(e)}"
            )
            sys.exit(1)
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Application cleanup started")
        
        try:
            if self.main_window:
                if hasattr(self.main_window, 'cleanup'):
                    self.main_window.cleanup()
                self.main_window = None
            
            if self.db_manager:
                self.db_manager.close()
                self.db_manager = None
            
            logger.info("Application cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


def main():
    """Main entry point"""
    try:
        app = DrillMasterApp(sys.argv)
        return app.exec()
        
    except Exception as e:
        logger.error(f"Fatal application error: {e}")
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"A fatal error occurred:\n\n{str(e)}\n\n"
            "The application will now exit."
        )
        return 1

