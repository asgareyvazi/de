"""
Main Window - با managerها
"""

import logging
from datetime import datetime, date, timedelta 

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from core.database import DatabaseManager, Well, Company, Project, DailyReport, Section
from core.managers import StatusBarManager, AutoSaveManager, ShortcutManager

from tabs.home_tab import HomeTab
from tabs.w1_well_info import WellInfoTab
from tabs.w2_Daily_Report import DailyReportWidget
from tabs.w3_drilling_report import DrillingReportWidget
from tabs.w4_Downhole_Widget import DownholeWidget
from tabs.w5_Equipment_Widget import EquipmentWidget
from tabs.w6_Trajectory_Widget import TrajectoryWidget
from tabs.w7_logistics_Widget import LogisticsWidget
from tabs.w8_Safety_Widget import SafetyWidget
from tabs.w9_Services_Widget import ServicesWidget
from tabs.w10_Planning_Widget import PlanningWidget
from tabs.w11_Export import ExportWidget
from tabs.w12_Analysis import AnalysisWidget

from dialogs.hierarchy_dialogs import NewCompanyDialog, NewProjectDialog, NewWellDialog,NewSectionDialog, NewDailyReportDialog
from dialogs.startup_dialog import StartupDialog

from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from pathlib import Path
import subprocess
from sqlalchemy import func

import json  
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window of the application"""

    def __init__(self, db_manager, user, startup_result=None):  # <-- startup_result اضافه شد
        super().__init__()
        self.db_manager = db_manager
        self.user = user
        self.startup_result = startup_result 

        # مدیرها
        self.status_manager = StatusBarManager()
        self.status_manager.register_main_window(self)

        self.auto_save_manager = AutoSaveManager()
        self.shortcut_manager = ShortcutManager(self)

        # متغیرهای حالت
        self.current_well = None
        self.current_report = None

        # تنظیمات
        self.settings = QSettings("Nikan", "DrillMaster")

        # راه‌اندازی
        self.init_ui()
        self.setup_connections()
        self.setup_managers()
        
        # اعمال startup result اگر وجود دارد
        if startup_result:
            QTimer.singleShot(500, lambda: self.apply_startup_result(startup_result))

        logger.info(f"Main window initialized for user: {user['username']}")
        QTimer.singleShot(1000, self.update_recent_menu)
        
    def init_ui(self):
        """Initialize user interface"""
        # Window properties
        self.setWindowTitle(f"DrillMaster - {self.user['username']}")
        
        # ابتدا تم پیش‌فرض را تنظیم کنید
        self.setStyleSheet("")  # Reset to default
        
        # 1. ابتدا منوی اصلی را ایجاد کنید (بسیار مهم!)
        self.create_menubar()
        
        # 2. یک اندازه ثابت خوب تنظیم کنید
        self.resize(1400, 800)
        
        # 3. مرکز کردن پنجره (بعد از resize)
        self.center_window()
        
        # 4. تنظیم حداقل اندازه
        self.setMinimumSize(1000, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create toolbar
        self.create_toolbar()

        # Create splitter
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # Create hierarchy tree
        self.create_hierarchy_tree()

        # Create tab widget
        self.create_tab_widget()

        # Create status bar
        self.create_status_bar()

        # Set splitter sizes
        self.splitter.setSizes([250, 750])
        
        # 5. اطمینان از نمایش منوی اصلی
        QTimer.singleShot(100, self.ensure_menubar_visible)

    def center_window(self):
        """مرکزیت دادن به پنجره"""
        # ابتدا هندسه فعلی را دریافت کنید
        frame_geometry = self.frameGeometry()
        
        # مرکز صفحه را پیدا کنید
        try:
            screen = QApplication.primaryScreen()
            if screen:
                screen_center = screen.availableGeometry().center()
            else:
                # Fallback
                screen_center = QPoint(960, 540)  # مرکز صفحه 1920x1080
        except:
            screen_center = QPoint(960, 540)
        
        # مرکز پنجره را تنظیم کنید
        frame_geometry.moveCenter(screen_center)
        
        # پنجره را حرکت دهید
        self.move(frame_geometry.topLeft())
        
        # لاگ برای دیباگ
        logger.info(f"Window centered at {frame_geometry.topLeft()}")
    
    def ensure_menubar_visible(self):
        """اطمینان از نمایش منوی اصلی"""
        try:
            # بررسی وجود منوی اصلی
            menubar = self.menuBar()
            if not menubar:
                logger.warning("Menubar does not exist, creating...")
                self.create_menubar()
                menubar = self.menuBar()
            
            # نمایش منوی اصلی
            menubar.setVisible(True)
            menubar.show()
            
            # به‌روزرسانی UI
            menubar.update()
            menubar.repaint()
            
            logger.info(f"Menubar ensured visible: {menubar.isVisible()}")
            
            # همچنین تولبار را بررسی کنید
            toolbar = self.findChild(QToolBar, "MainToolbar")
            if toolbar:
                toolbar.setVisible(True)
                logger.info(f"Toolbar ensured visible: {toolbar.isVisible()}")
                
        except Exception as e:
            logger.error(f"Error ensuring menubar visibility: {e}")
            
    def setup_managers(self):
        """تنظیم Managerها"""
        # تنظیم کلیدهای میانبر
        self.shortcut_manager.setup_default_shortcuts()

        # اضافه کردن میانبرهای سفارشی
        self.setup_custom_shortcuts()

        # فعال کردن auto-save برای تب‌ها
        self.setup_auto_save_for_tabs()

        logger.info("All managers setup complete")

    def setup_custom_shortcuts(self):
        """تنظیم کلیدهای میانبر سفارشی"""
        
        # میانبر برای ایجاد شرکت جدید
        self.shortcut_manager.add_shortcut_with_feedback(
            "Ctrl+Shift+C", self.new_company_dialog, "New Company"
        )
        
        # میانبر برای ایجاد پروژه جدید
        self.shortcut_manager.add_shortcut_with_feedback(
            "Ctrl+Shift+P", self.new_project_dialog, "New Project"
        )
        
        # میانبر برای ایجاد چاه جدید
        self.shortcut_manager.add_shortcut_with_feedback(
            "Ctrl+Shift+W", self.new_well_dialog, "New Well"
        )
    
        # میانبر برای باز کردن چاه
        self.shortcut_manager.add_shortcut_with_feedback(
            "Ctrl+O", self.open_well_dialog, "Open Well"
        )
        
        # میانبر برای خروج
        self.shortcut_manager.add_shortcut_with_feedback("Ctrl+Q", self.close, "Exit")

    def setup_auto_save_for_tabs(self):
        """فعال کردن Auto-save برای تب‌ها"""
        # برای تب Well Info
        if hasattr(self, "well_info_tab"):
            self.auto_save_manager.enable_for_widget(
                "WellInfoTab", self.well_info_tab, interval_minutes=5
            )

    def create_toolbar(self):
        """Create main toolbar - نسخه حرفه‌ای"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Home/Startup Button
        home_action = QAction("🏠 Home", self)
        home_action.setToolTip("Return to startup screen")
        home_action.triggered.connect(self.return_to_startup)
        toolbar.addAction(home_action)
        
        toolbar.addSeparator()
    
        # New Company
        new_company_action = QAction("🏢 New Company", self)
        new_company_action.setToolTip("Create a new company (Ctrl+Shift+C)")
        new_company_action.triggered.connect(self.new_company_dialog)
        toolbar.addAction(new_company_action)
        
        # New Project
        new_project_action = QAction("📁 New Project", self)
        new_project_action.setToolTip("Create a new project (Ctrl+Shift+P)")
        new_project_action.triggered.connect(self.new_project_dialog)
        toolbar.addAction(new_project_action)
        
        # New Well
        new_well_action = QAction("🛢️ New Well", self)
        new_well_action.setToolTip("Create a new well (Ctrl+Shift+W)")
        new_well_action.triggered.connect(self.new_well_dialog)
        toolbar.addAction(new_well_action)
        
        toolbar.addSeparator()

        # Open Well
        open_well_action = QAction("📂 Open Well", self)
        open_well_action.setShortcut("Ctrl+O")
        open_well_action.setToolTip("Open an existing well (Ctrl+O)")
        open_well_action.triggered.connect(self.open_well_dialog)
        toolbar.addAction(open_well_action)

        toolbar.addSeparator()

        # Save
        save_action = QAction("💾 Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setToolTip("Save current data (Ctrl+S)")
        save_action.triggered.connect(self.save_current_tab)
        toolbar.addAction(save_action)

        # Save All
        save_all_action = QAction("💾 Save All", self)
        save_all_action.setShortcut("Ctrl+Shift+S")
        save_all_action.setToolTip("Save all tabs (Ctrl+Shift+S)")
        save_all_action.triggered.connect(self.save_all_tabs)
        toolbar.addAction(save_all_action)

        refresh_tabs_action = QAction("🔄 Refresh Tabs", self)
        refresh_tabs_action.setToolTip("Refresh report tabs structure")
        refresh_tabs_action.triggered.connect(self.refresh_report_tabs)
        toolbar.addAction(refresh_tabs_action)

        toolbar.addSeparator()

        # New Report
        new_report_action = QAction("📅 New Daily Report", self)
        new_report_action.setShortcut("Ctrl+R")
        new_report_action.setToolTip("Create new daily report (Ctrl+R)")
        # new_report_action.triggered.connect(self.new_daily_report)
        toolbar.addAction(new_report_action)

        # Copy Previous Report
        copy_report_action = QAction("📋 Copy Previous", self)
        copy_report_action.setShortcut("Ctrl+Shift+R")
        copy_report_action.setToolTip("Copy from previous day's report (Ctrl+Shift+R)")
        copy_report_action.triggered.connect(self.copy_previous_report)
        toolbar.addAction(copy_report_action)

        toolbar.addSeparator()

        # Export
        export_action = QAction("📤 Export", self)
        export_action.setShortcut("Ctrl+E")
        export_action.setToolTip("Export data (Ctrl+E)")
        export_action.triggered.connect(self.export_current_tab)
        toolbar.addAction(export_action)

        # Print
        print_action = QAction("🖨️ Print", self)
        print_action.setShortcut("Ctrl+P")
        print_action.setToolTip("Print report (Ctrl+P)")
        print_action.triggered.connect(self.print_report)
        toolbar.addAction(print_action)

        toolbar.addSeparator()

        # Refresh
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.setToolTip("Refresh data (F5)")
        refresh_action.triggered.connect(self.refresh_all_tabs)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # Settings
        settings_action = QAction("⚙️ Settings", self)
        settings_action.setShortcut("Ctrl+Shift+P")
        settings_action.setToolTip("Settings (Ctrl+Shift+P)")
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)

        # Help
        help_action = QAction("❓ Help", self)
        help_action.setShortcut("F1")
        help_action.setToolTip("Help (F1)")
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)

        toolbar.addSeparator()

        # Auto-save toggle
        self.auto_save_action = QAction("💾 Auto-save: ON", self)
        self.auto_save_action.setCheckable(True)
        self.auto_save_action.setChecked(True)
        self.auto_save_action.toggled.connect(self.toggle_auto_save)
        toolbar.addAction(self.auto_save_action)

        toolbar.addSeparator()

        # User info با استایل بهتر
        user_widget = QWidget()
        user_layout = QHBoxLayout(user_widget)
        user_layout.setContentsMargins(5, 0, 5, 0)

        user_icon = QLabel("👤")
        user_label = QLabel(f"{self.user['username']} ({self.user['role']})")
        user_label.setStyleSheet("font-weight: bold; color: #2c3e50;")

        user_layout.addWidget(user_icon)
        user_layout.addWidget(user_label)
        user_layout.addStretch()

        toolbar.addWidget(user_widget)

    def refresh_report_tabs(self):
        """رفرش ساختار تب‌های گزارش"""
        if self.current_report:
            report_id = self.current_report.get("id")
            if report_id:
                self.db_manager.initialize_report_tabs(report_id)
                self.populate_hierarchy()
                self.status_manager.show_success("MainWindow", "Report tabs refreshed")
                
    def create_menubar(self):
        """Create menu bar - کامل و حرفه‌ای"""
        menubar = self.menuBar()

        # ========== File Menu ==========
        file_menu = menubar.addMenu("&File")

        # New Company
        new_company_action = QAction("New &Company...", self)
        new_company_action.setShortcut("Ctrl+Shift+C")
        new_company_action.setStatusTip("Create a new company")
        new_company_action.triggered.connect(self.new_company_dialog)
        file_menu.addAction(new_company_action)
        
        # New Project
        new_project_action = QAction("New &Project...", self)
        new_project_action.setShortcut("Ctrl+Shift+P")
        new_project_action.setStatusTip("Create a new project")
        new_project_action.triggered.connect(self.new_project_dialog)
        file_menu.addAction(new_project_action)
        
        # New Well
        new_well_action = QAction("New &Well...", self)
        new_well_action.setShortcut("Ctrl+Shift+W")
        new_well_action.setStatusTip("Create a new well")
        new_well_action.triggered.connect(self.new_well_dialog)
        file_menu.addAction(new_well_action)
        
        file_menu.addSeparator()

        # Open Well
        open_well_action = QAction("&Open Well...", self)
        open_well_action.setShortcut("Ctrl+O")
        open_well_action.setStatusTip("Open an existing well")
        open_well_action.triggered.connect(self.open_well_dialog)
        file_menu.addAction(open_well_action)

        file_menu.addSeparator()

        # Recent Wells submenu
        recent_menu = file_menu.addMenu("&Recent Wells")
        # این بعداً پر می‌شود
        self.recent_menu = recent_menu

        file_menu.addSeparator()

        # New Report
        new_report_action = QAction("New &Daily Report", self)
        new_report_action.setShortcut("Ctrl+R")
        new_report_action.setStatusTip("Create new daily report")
        new_report_action.triggered.connect(self.new_daily_report)
        file_menu.addAction(new_report_action)

        # Copy Previous Report
        copy_report_action = QAction("&Copy from Previous Day", self)
        copy_report_action.setShortcut("Ctrl+Shift+R")
        copy_report_action.setStatusTip("Copy data from previous day's report")
        copy_report_action.triggered.connect(self.copy_previous_report)
        file_menu.addAction(copy_report_action)

        file_menu.addSeparator()

        # Save
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip("Save current data")
        save_action.triggered.connect(self.save_current_tab)
        file_menu.addAction(save_action)

        # Save All
        save_all_action = QAction("Save &All", self)
        save_all_action.setShortcut("Ctrl+Shift+S")
        save_all_action.setStatusTip("Save all tabs")
        save_all_action.triggered.connect(self.save_all_tabs)
        file_menu.addAction(save_all_action)

        file_menu.addSeparator()

        # Export submenu
        export_menu = file_menu.addMenu("&Export")

        export_pdf_action = QAction("Export to &PDF...", self)
        export_pdf_action.setStatusTip("Export data to PDF format")
        export_pdf_action.triggered.connect(lambda: self.export_data("PDF"))
        export_menu.addAction(export_pdf_action)

        export_excel_action = QAction("Export to &Excel...", self)
        export_excel_action.setStatusTip("Export data to Excel format")
        export_excel_action.triggered.connect(lambda: self.export_data("Excel"))
        export_menu.addAction(export_excel_action)

        export_csv_action = QAction("Export to &CSV...", self)
        export_csv_action.setStatusTip("Export data to CSV format")
        export_csv_action.triggered.connect(lambda: self.export_data("CSV"))
        export_menu.addAction(export_csv_action)

        file_menu.addSeparator()

        # Print
        print_action = QAction("&Print...", self)
        print_action.setShortcut("Ctrl+P")
        print_action.setStatusTip("Print current report")
        print_action.triggered.connect(self.print_report)
        file_menu.addAction(print_action)

        # Print Preview
        print_preview_action = QAction("Print Pre&view", self)
        print_preview_action.setStatusTip("Preview before printing")
        print_preview_action.triggered.connect(self.print_preview)
        file_menu.addAction(print_preview_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ========== Edit Menu ==========
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setStatusTip("Undo last action")
        undo_action.triggered.connect(self.undo_action)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.setStatusTip("Redo last action")
        redo_action.triggered.connect(self.redo_action)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.setStatusTip("Cut selected text")
        cut_action.triggered.connect(self.cut_action)
        edit_menu.addAction(cut_action)

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.setStatusTip("Copy selected text")
        copy_action.triggered.connect(self.copy_action)
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.setStatusTip("Paste from clipboard")
        paste_action.triggered.connect(self.paste_action)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.setStatusTip("Select all text")
        select_all_action.triggered.connect(self.select_all_action)
        edit_menu.addAction(select_all_action)

        # ========== View Menu ==========
        view_menu = menubar.addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("Refresh view")
        refresh_action.triggered.connect(self.refresh_all_tabs)
        view_menu.addAction(refresh_action)

        view_menu.addSeparator()

        # Toolbars submenu
        toolbars_menu = view_menu.addMenu("&Toolbars")

        main_toolbar_action = QAction("&Main Toolbar", self)
        main_toolbar_action.setCheckable(True)
        main_toolbar_action.setChecked(True)
        main_toolbar_action.triggered.connect(self.toggle_main_toolbar)
        toolbars_menu.addAction(main_toolbar_action)

        view_menu.addSeparator()

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")

        light_theme_action = QAction("&Light", self)
        light_theme_action.setCheckable(True)
        light_theme_action.setChecked(True)
        light_theme_action.triggered.connect(lambda: self.set_theme("Light"))
        theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.triggered.connect(lambda: self.set_theme("Dark"))
        theme_menu.addAction(dark_theme_action)

        theme_menu.addSeparator()

        system_theme_action = QAction("&System", self)
        system_theme_action.triggered.connect(lambda: self.set_theme("System"))
        theme_menu.addAction(system_theme_action)

        # ========== Tools Menu ==========
        tools_menu = menubar.addMenu("&Tools")

        calculator_action = QAction("&Calculator", self)
        calculator_action.setStatusTip("Open calculator")
        calculator_action.triggered.connect(self.open_calculator)
        tools_menu.addAction(calculator_action)

        converter_action = QAction("Unit &Converter", self)
        converter_action.setStatusTip("Open unit converter")
        converter_action.triggered.connect(self.open_converter)
        tools_menu.addAction(converter_action)

        tools_menu.addSeparator()

        backup_action = QAction("&Backup Database", self)
        backup_action.setStatusTip("Create database backup")
        backup_action.triggered.connect(self.backup_database)
        tools_menu.addAction(backup_action)

        restore_action = QAction("&Restore Database", self)
        restore_action.setStatusTip("Restore database from backup")
        restore_action.triggered.connect(self.restore_database)
        tools_menu.addAction(restore_action)

        tools_menu.addSeparator()

        options_action = QAction("&Options...", self)
        options_action.setStatusTip("Application options")
        options_action.triggered.connect(self.show_settings)
        tools_menu.addAction(options_action)

        # ========== Window Menu ==========
        window_menu = menubar.addMenu("&Window")

        cascade_action = QAction("&Cascade", self)
        cascade_action.setStatusTip("Cascade windows")
        cascade_action.triggered.connect(self.cascade_windows)
        window_menu.addAction(cascade_action)

        tile_action = QAction("&Tile", self)
        tile_action.setStatusTip("Tile windows")
        tile_action.triggered.connect(self.tile_windows)
        window_menu.addAction(tile_action)

        window_menu.addSeparator()

        close_all_action = QAction("Close &All", self)
        close_all_action.setStatusTip("Close all windows")
        close_all_action.triggered.connect(self.close_all_windows)
        window_menu.addAction(close_all_action)

        # ========== Help Menu ==========
        help_menu = menubar.addMenu("&Help")

        help_action = QAction("&User Manual", self)
        help_action.setShortcut("F1")
        help_action.setStatusTip("Open user manual")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setStatusTip("Show keyboard shortcuts")
        shortcuts_action.triggered.connect(self.show_shortcuts_help)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        check_updates_action = QAction("Check for &Updates", self)
        check_updates_action.setStatusTip("Check for application updates")
        check_updates_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_updates_action)

        help_menu.addSeparator()

        about_action = QAction("&About DrillMaster", self)
        about_action.setStatusTip("About DrillMaster")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def return_to_startup(self):
        """بازگشت به صفحه Startup"""
        reply = QMessageBox.question(
            self,
            "Return to Startup",
            "Do you want to return to startup screen?\n\n"
            "Current work will be saved automatically.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # ذخیره داده‌های جاری
            self.save_current_tab()
            
            # پنهان کردن پنجره اصلی
            self.hide()
            
            # نمایش Startup Dialog
            try:
                from dialogs.startup_dialog import StartupDialog
                dialog = StartupDialog(self.db_manager, self)
                
                if dialog.exec():
                    result = dialog.get_result()
                    self.apply_startup_result(result)
                    
                    # نمایش مجدد پنجره اصلی
                    self.show()
                    self.raise_()
                    self.activateWindow()
                    
            except Exception as e:
                logger.error(f"Error returning to startup: {e}")
                self.show()  # در صورت خطا، پنجره را نشان بده
   
    def new_daily_report(self):
        """Create new daily report"""
        self.status_manager.show_message("MainWindow", "Daily Report feature coming soon", 2000)

    def copy_previous_report(self):
        """Copy from previous day's report"""
        self.status_manager.show_message("MainWindow", "Copy Previous Report feature coming soon", 2000)

    def export_data(self, format):
        """Export data"""
        self.status_manager.show_message("MainWindow", f"Export to {format} feature coming soon", 2000)

    def print_report(self):
        """Print current report"""
        self.status_manager.show_message("MainWindow", "Print Report feature coming soon", 2000)

    def print_preview(self):
        """Print preview"""
        self.status_manager.show_message("MainWindow", "Print Preview feature coming soon", 2000)

    def backup_database(self):
        """Backup database"""
        self.status_manager.show_message("MainWindow", "Backup Database feature coming soon", 2000)

    def restore_database(self):
        """Restore database"""
        self.status_manager.show_message("MainWindow", "Restore Database feature coming soon", 2000)

    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>DrillMaster</h2>
        <p>Version 1.0.0</p>
        <p>Drilling Operations Management System</p>
        <p>© 2024 DrillMaster Inc.</p>
        """
        QMessageBox.about(self, "About DrillMaster", about_text)
    
    def create_hierarchy_tree(self):
        """Create hierarchy tree widget"""
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("🏢 Project Hierarchy")
        self.tree_widget.setColumnCount(2)
        self.tree_widget.setHeaderLabels(["Name", "Type"])
        self.tree_widget.setMinimumWidth(250)
        
        # فعال کردن کلیک راست
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        self.splitter.addWidget(self.tree_widget)
        
        # Populate tree
        self.populate_hierarchy()
        
        # Connect signals
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)

    def show_tree_context_menu(self, position):
        """نمایش منوی راست‌کلیک برای tree hierarchy"""
        item = self.tree_widget.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        
        data = item.data(0, Qt.UserRole)
        if data:
            item_type = data.get("type")
            item_id = data.get("id")
            
            if item_type == "company":
                # برای شرکت: امکان اضافه کردن پروژه
                add_project_action = QAction("📁 Add Project", self)
                add_project_action.triggered.connect(
                    lambda: self.new_project_dialog_for_company(item_id)
                )
                menu.addAction(add_project_action)
                
            elif item_type == "project":
                # برای پروژه: امکان اضافه کردن چاه
                add_well_action = QAction("🛢️ Add Well", self)
                add_well_action.triggered.connect(
                    lambda: self.new_well_dialog_for_project(item_id)
                )
                menu.addAction(add_well_action)
                
            elif item_type == "well":
                # برای چاه: امکان اضافه کردن سکشن
                add_section_action = QAction("📊 Add Section", self)
                add_section_action.triggered.connect(
                    lambda: self.new_section_dialog_for_well(item_id)
                )
                menu.addAction(add_section_action)
            
            elif item_type == "section":
                # برای سکشن: امکان اضافه کردن گزارش روزانه
                add_daily_report_action = QAction("📅 Add Daily Report", self)
                add_daily_report_action.triggered.connect(
                    lambda: self.new_daily_report_dialog_for_section(item_id)
                )
                menu.addAction(add_daily_report_action)
                
            elif item_type == "daily_report":
                # برای گزارش: امکان حذف یا ویرایش
                delete_report_action = QAction("🗑️ Delete Report", self)
                delete_report_action.triggered.connect(
                    lambda: self.delete_daily_report(item_id)
                )
                menu.addAction(delete_report_action)
        
        # گزینه‌های عمومی
        menu.addSeparator()
        refresh_action = QAction("🔄 Refresh Hierarchy", self)
        refresh_action.triggered.connect(self.populate_hierarchy)
        menu.addAction(refresh_action)
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def new_daily_report_dialog_for_section(self, section_id):
        """باز کردن دیالوگ ایجاد گزارش روزانه برای سکشن مشخص"""
        try:
            session = self.db_manager.create_session()
            section = session.query(Section).filter(Section.id == section_id).first()
            session.close()
            
            if section:
                dialog = NewDailyReportDialog(self.db_manager, self, section_id)
                if dialog.exec():
                    self.status_manager.show_success(
                        "MainWindow", 
                        f"Daily report created successfully for section {section.name}!"
                    )
                    self.populate_hierarchy()
        except Exception as e:
            logger.error(f"Error creating daily report for section: {e}")
    def new_project_dialog_for_company(self, company_id):
        """باز کردن دیالوگ ایجاد پروژه برای شرکت مشخص"""
        try:
            session = self.db_manager.create_session()
            company = session.query(Company).filter(Company.id == company_id).first()
            session.close()
            
            if company:
                dialog = NewProjectDialog(self.db_manager, self)
                # تنظیم شرکت انتخاب شده
                for i in range(dialog.company_combo.count()):
                    if dialog.company_combo.itemData(i) == company_id:
                        dialog.company_combo.setCurrentIndex(i)
                        break
                        
                if dialog.exec():
                    self.status_manager.show_success(
                        "MainWindow", 
                        f"Project created successfully under {company.name}!"
                    )
                    self.populate_hierarchy()
        except Exception as e:
            logger.error(f"Error creating project for company: {e}")
    def new_section_dialog_for_well(self, well_id):
        """Open dialog to create new section for a well"""
        from dialogs.hierarchy_dialogs import NewSectionDialog
        dialog = NewSectionDialog(self.db_manager, self, well_id)
        if dialog.exec():
            # Refresh section lists if needed
            if hasattr(self, 'current_daily_report_widget'):
                self.current_daily_report_widget.load_sections(well_id)
    def new_well_dialog_for_project(self, project_id):
        """باز کردن دیالوگ ایجاد چاه برای پروژه مشخص"""
        try:
            session = self.db_manager.create_session()
            project = session.query(Project).filter(Project.id == project_id).first()
            session.close()
            
            if project:
                dialog = NewWellDialog(self.db_manager, self, project_id)
                
                if dialog.exec():
                    self.status_manager.show_success(
                        "MainWindow", 
                        f"Well created successfully under {project.name}!"
                    )
                    self.populate_hierarchy()
        except Exception as e:
            logger.error(f"Error creating well for project: {e}")
      
    def apply_startup_result(self, result):
        """اعمال نتیجه Startup"""
        if not result:
            return
            
        try:
            action = result.get("action")
            logger.info(f"Applying startup action: {action}")
            
            if action == "load_well":
                well_id = result.get("well_id")
                if well_id:
                    QTimer.singleShot(300, lambda: self.load_and_select_well(well_id))
                    
            elif action == "load_project":
                project_id = result.get("project_id")
                if project_id:
                    QTimer.singleShot(300, lambda: self.load_and_select_project(project_id))
                    
            elif action == "create_well":
                # ایجاد چاه جدید
                QTimer.singleShot(500, self.new_well_dialog)
                
            elif action == "create_project":
                # ایجاد پروژه جدید
                QTimer.singleShot(500, self.new_project_dialog)
                
        except Exception as e:
            logger.error(f"Error applying startup result: {e}")
            self.status_manager.show_error(
                "MainWindow",
                f"Failed to load startup data: {str(e)}"
            )

    def load_and_select_project(self, project_id):
        """بارگذاری و انتخاب پروژه"""
        try:
            session = self.db_manager.create_session()
            from core.database import Project, Well
            
            # یافتن پروژه
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                # یافتن اولین چاه
                well = session.query(Well).filter(Well.project_id == project_id).first()
                if well:
                    self.load_and_select_well(well.id)
                else:
                    # اگر چاهی نداشت، پیام بده
                    self.status_manager.show_message(
                        "MainWindow",
                        f"Project '{project.name}' has no wells. Please create a well."
                    )
                    # رفتن به تب Well Info برای ایجاد چاه
                    self.tab_widget.setCurrentIndex(1)
                    if hasattr(self, "well_info_tab"):
                        self.well_info_tab.clear_form_fields()
                        self.well_info_tab.project_id = project_id
        except Exception as e:
            logger.error(f"Error loading project {project_id}: {e}")
        finally:
            try:
                session.close()
            except:
                pass

    def highlight_well_in_tree(self, well_id):
        """هایلایت کردن چاه در tree"""
        try:
            # تازه‌سازی tree
            self.populate_hierarchy()
            
            # جستجوی چاه در tree
            def find_well_item(item, target_id):
                if item is None:
                    return None
                
                data = item.data(0, Qt.UserRole)
                if data and data.get("type") == "well" and data.get("id") == target_id:
                    return item
                
                for i in range(item.childCount()):
                    found = find_well_item(item.child(i), target_id)
                    if found:
                        return found
                
                return None
            
            # جستجو در tree
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                found = find_well_item(item, well_id)
                if found:
                    self.tree_widget.setCurrentItem(found)
                    self.tree_widget.scrollToItem(found)
                    found.setExpanded(True)
                    break
                    
        except Exception as e:
            logger.error(f"Error highlighting well in tree: {e}")
        
    def create_tab_widget(self):
        """Create main tab widget"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(True)

        # Create tabs
        self.create_tabs()

        # Add to splitter
        self.splitter.addWidget(self.tab_widget)

    def create_tabs(self):
        """Create all application tabs"""

        # Tab 0: Home
        self.home_tab = HomeTab(self.db_manager, self)
        self.tab_widget.addTab(self.home_tab, "🏠 Home")

        # Tab 1: Well Info
        self.well_info_tab = WellInfoTab(self.db_manager, self)
        self.tab_widget.addTab(self.well_info_tab, "🛢️ Well Info")

        # Tab 2: Daily Report
        self.Daily_Report_tab = DailyReportWidget(self.db_manager, self)
        self.tab_widget.addTab(self.Daily_Report_tab, "📅 Daily Report")


        # Tab 3: Drilling Report
        self.drilling_report_tab = DrillingReportWidget(self.db_manager, self)
        self.tab_widget.addTab(self.drilling_report_tab, "🧭 Drilling Report")

        # Tab 4: Downhole
        self.downhole_tab = DownholeWidget(self.db_manager)
        self.tab_widget.addTab(self.downhole_tab, "📡 Downhole")
        
        # Tab 5: Equipment
        self.equipment_widget = EquipmentWidget(self.db_manager)
        self.tab_widget.addTab(self.equipment_widget, "🏗️ Equipment")
        
        # Tab 6: Trajectory
        self.trajectory_widget = TrajectoryWidget(self.db_manager)
        self.tab_widget.addTab(self.trajectory_widget, "📈Trajectory")
        
        # Tab 7: Trajectory
        self.logistics_widget = LogisticsWidget(self.db_manager)
        self.tab_widget.addTab(self.logistics_widget, "📦 Logistics")

        # Tab 8: Safety
        self.safety_widget = SafetyWidget(self.db_manager)
        self.tab_widget.addTab(self.safety_widget, "🛡️ Safety")
        
        # Tab 9: Services
        self.services_widget = ServicesWidget(self.db_manager)
        self.tab_widget.addTab(self.services_widget, "🔌 Services")

        # Tab 10: Planning
        self.planning_widget = PlanningWidget(self.db_manager)
        self.tab_widget.addTab(self.planning_widget, "📋 Planning")
        
        # Tab 11: Export
        self.export_widget =ExportWidget(self.db_manager)
        self.tab_widget.addTab(self.export_widget, "📤 Export")
        
        # Tab 12: Analysis
        self.analysis_widget =AnalysisWidget(self.db_manager)
        self.tab_widget.addTab(self.analysis_widget, "📊 Analysis")

    def create_status_bar(self):
        """Create status bar"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Left section - Status messages
        self.status_label = QLabel("✅ Ready")
        self.status_label.setMinimumWidth(200)
        self.status_label.setAlignment(Qt.AlignLeft)
        status_bar.addWidget(self.status_label, 1)  
        
        # Middle section - Fixed info
        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(10, 0, 10, 0)
        middle_layout.setSpacing(15)

        # Auto-save
        self.auto_save_label = QLabel("💾 Auto-save: ON")
        middle_layout.addWidget(self.auto_save_label)

        # Separator
        separator1 = QLabel("│")
        separator1.setStyleSheet("color: #ccc;")
        middle_layout.addWidget(separator1)

        # User info
        self.user_label = QLabel(f"👤 {self.user['username']}")
        middle_layout.addWidget(self.user_label)

        separator2 = QLabel("│")
        separator2.setStyleSheet("color: #ccc;")
        middle_layout.addWidget(separator2)

        # Current time
        self.time_label = QLabel()
        self.update_time()
        middle_layout.addWidget(self.time_label)

        middle_layout.addStretch()
        status_bar.addPermanentWidget(middle_widget)

        # Right section - Well info
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.current_well_label = QLabel("🛢️ No well selected")
        self.current_well_label.setMinimumWidth(200)
        self.current_well_label.setAlignment(Qt.AlignRight)
        self.current_well_label.setStyleSheet(
            """
            QLabel {
                padding: 0 10px;
                background-color: #f0f0f0;
                border-radius: 3px;
                border: 1px solid #ddd;
            }
        """
        )
        right_layout.addWidget(self.current_well_label)

        status_bar.addPermanentWidget(right_widget)

        # تایمر برای به‌روزرسانی زمان
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(60000)  # هر دقیقه

    def new_company_dialog(self):
        """باز کردن دیالوگ ایجاد شرکت جدید"""
        try:
            dialog = NewCompanyDialog(self.db_manager, self)
            if dialog.exec():
                self.status_manager.show_success(
                    "MainWindow", 
                    "Company created successfully!"
                )
                # تازه‌سازی tree hierarchy
                self.populate_hierarchy()
                # تازه‌سازی تب Home
                if hasattr(self, 'home_tab') and hasattr(self.home_tab, 'refresh'):
                    self.home_tab.refresh()
        except Exception as e:
            logger.error(f"Error showing new company dialog: {e}")
            self.status_manager.show_error(
                "MainWindow",
                f"Failed to create company: {str(e)}"
            )

    def new_project_dialog(self):
        """باز کردن دیالوگ ایجاد پروژه جدید"""
        try:
            dialog = NewProjectDialog(self.db_manager, self)
            if dialog.exec():
                self.status_manager.show_success(
                    "MainWindow", 
                    "Project created successfully!"
                )
                # تازه‌سازی tree hierarchy
                self.populate_hierarchy()
                # تازه‌سازی تب Home
                if hasattr(self, 'home_tab') and hasattr(self.home_tab, 'refresh'):
                    self.home_tab.refresh()
        except Exception as e:
            logger.error(f"Error showing new project dialog: {e}")
            self.status_manager.show_error(
                "MainWindow",
                f"Failed to create project: {str(e)}"
            )

    def new_well_dialog(self, project_id=None):
        """باز کردن دیالوگ ایجاد چاه جدید"""
        try:
            dialog = NewWellDialog(self.db_manager, self, project_id)
            if dialog.exec():
                self.status_manager.show_success(
                    "MainWindow", 
                    "Well created successfully!"
                )
                # تازه‌سازی tree hierarchy
                self.populate_hierarchy()
                # تازه‌سازی تب Home
                if hasattr(self, 'home_tab') and hasattr(self.home_tab, 'refresh'):
                    self.home_tab.refresh()
                # تازه‌سازی تب Well Info
                if hasattr(self, 'well_info_tab') and hasattr(self.well_info_tab, 'refresh'):
                    self.well_info_tab.refresh()
        except Exception as e:
            logger.error(f"Error showing new well dialog: {e}")
            self.status_manager.show_error(
                "MainWindow",
                f"Failed to create well: {str(e)}"
            )
    
    def update_time(self):
        """به‌روزرسانی زمان"""
        current_time = QDateTime.currentDateTime().toString("hh:mm AP")
        self.time_label.setText(f"🕒 {current_time}")

    def setup_connections(self):
        """Setup signal connections"""
        # Tab changes
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Auto-save timer
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.auto_save)

    def on_tab_changed(self, index):
        """Handle tab change"""
        tab_name = self.tab_widget.tabText(index)
        self.status_label.setText(f"📑 Active tab: {tab_name}")
        self.status_manager.show_message("MainWindow", f"Switched to {tab_name}", 1000)

    def populate_hierarchy(self):
        """Populate hierarchy tree با ساختار پویا از دیتابیس"""
        self.tree_widget.clear()

        hierarchy = self.db_manager.get_hierarchy()

        for company_data in hierarchy:
            company_item = QTreeWidgetItem(self.tree_widget)
            company_item.setText(0, f"🏢 {company_data['name']}")
            company_item.setText(1, "Company")
            company_item.setData(
                0, Qt.UserRole, {"type": "company", "id": company_data["id"]}
            )

            for project_data in company_data.get("projects", []):
                project_item = QTreeWidgetItem(company_item)
                project_item.setText(0, f"📁 {project_data['name']}")
                project_item.setText(1, "Project")
                project_item.setData(
                    0, Qt.UserRole, {"type": "project", "id": project_data["id"]}
                )

                for well_data in project_data.get("wells", []):
                    well_item = QTreeWidgetItem(project_item)
                    well_item.setText(0, f"🛢️ {well_data['name']}")
                    well_item.setText(1, "Well")
                    well_item.setData(
                        0, Qt.UserRole, {"type": "well", "id": well_data["id"]}
                    )
                    
                    # اضافه کردن سکشن‌های هر چاه
                    sections = self.db_manager.get_sections_by_well(well_data["id"])
                    for section in sections:
                        section_item = QTreeWidgetItem(well_item)
                        section_item.setText(0, f"📊 {section['name']}")
                        section_item.setText(1, "Section")
                        section_item.setData(
                            0, Qt.UserRole, {"type": "section", "id": section["id"]}
                        )
                        
                        # اضافه کردن گزارش‌های روزانه هر سکشن
                        daily_reports = self.db_manager.get_daily_reports_by_section(section["id"])
                        for report in daily_reports:
                            report_item = QTreeWidgetItem(section_item)
                            # ساخت عنوان درست برای نمایش در tree
                            report_date = report['report_date'].strftime('%Y-%m-%d') if isinstance(report['report_date'], date) else report['report_date']
                            display_text = f"📅 {report['report_number']:02d} Daily Report, {project_data['name']}, {report_date}"
                            report_item.setText(0, display_text)
                            report_item.setText(1, "Daily Report")
                            report_item.setData(
                                0, Qt.UserRole, {
                                    "type": "daily_report", 
                                    "id": report["id"],
                                    "section_id": section["id"],
                                    "report_number": report["report_number"],
                                    "project_name": project_data['name'],
                                    "report_date": report_date
                                }
                            )
                            
                            # اضافه کردن تب‌های زیرمجموعه گزارش با ساختار پویا
                            self.add_report_tabs_dynamic(report_item, report["id"])

        self.tree_widget.expandAll()

    def add_report_tabs_dynamic(self, parent_item, report_id):
        """اضافه کردن تب‌های گزارش با ساختار پویا از دیتابیس"""
        try:
            # دریافت ساختار تب‌ها از دیتابیس
            tab_structure = self.db_manager.get_report_tab_structure(report_id)
            
            if not tab_structure:
                logger.warning(f"No tab structure found for report {report_id}")
                return
                
            # اضافه کردن تب‌ها به صورت بازگشتی
            self._add_tabs_recursive(parent_item, report_id, tab_structure, level=0)
            
        except Exception as e:
            logger.error(f"Error adding report tabs for report {report_id}: {e}")
            # Fallback: استفاده از ساختار قدیمی
            self.add_report_tabs_fallback(parent_item, report_id)

    def _add_tabs_recursive(self, parent_item, report_id, tabs, level=0):
        """افزودن تب‌ها به صورت بازگشتی"""
        for tab in tabs:
            # تعیین پیشوند بر اساس سطح
            if level == 0:
                prefix = "  ├─ "
            elif level == 1:
                prefix = "    ├─ "
            else:
                prefix = "      " + "  " * (level - 2) + "└─ "
            
            # ایجاد آیتم درخت
            tab_item = QTreeWidgetItem(parent_item)
            tab_item.setText(0, f"{prefix}{tab.get('icon', '📄')} {tab['tab_name']}")
            tab_item.setText(1, "Main Tab" if level == 0 else "Sub Tab")
            
            # ذخیره داده‌های تب
            tab_item.setData(
                0, Qt.UserRole, {
                    "type": "report_tab",
                    "report_id": report_id,
                    "tab_id": tab['id'],
                    "tab_type": tab['tab_type'],
                    "tab_name": tab['tab_name'],
                    "widget_class": tab.get('widget_class'),
                    "tab_level": level,
                    "parent_tab_type": tab.get('parent_tab_type'),
                    "tab_data": tab  # ذخیره کل داده‌های تب
                }
            )
            
            # اضافه کردن زیرتب‌ها به صورت بازگشتی
            children = tab.get('children', [])
            if children:
                self._add_tabs_recursive(tab_item, report_id, children, level + 1)

    def add_report_tabs_fallback(self, parent_item, report_id):
        """Fallback: اضافه کردن تب‌ها با ساختار ثابت قدیمی"""
        try:
            # دریافت ساختار پیش‌فرض از دیتابیس منیجر
            default_structure = self.db_manager._get_default_tab_structure()
            self._add_tabs_recursive(parent_item, report_id, default_structure, level=0)
        except Exception as e:
            logger.error(f"Error in fallback tab structure: {e}")
            
    def on_tree_item_clicked(self, item, column):
        """Handle tree item click با ساختار پویا"""
        data = item.data(0, Qt.UserRole)
        if data:
            item_type = data.get("type")
            
            if item_type == "daily_report":
                self._handle_daily_report_click(data)
                
            elif item_type == "report_tab":
                self._handle_report_tab_click(data)

    def _handle_daily_report_click(self, data):
        """هندل کلیک روی گزارش روزانه"""
        report_id = data.get("report_id") or data.get("id")
        self.db_manager.initialize_report_tabs(report_id)
        report_number = data.get("report_number", 1)
        
        # ست کردن گزارش جاری
        self.current_report = {
            "id": report_id,
            "number": report_number,
            "section_id": data.get("section_id"),
            "date": data.get("report_date")
        }
        
        # بارگذاری در تب Daily Report
        self.tab_widget.setCurrentIndex(2)  # تب Daily Report
        
        # اگر تب Daily Report تابع load_report دارد، فراخوانی کن
        if hasattr(self.Daily_Report_tab, "load_report"):
            self.Daily_Report_tab.load_report(report_id)
        
        # آپدیت label
        self.current_well_label.setText(
            f"📅 Report #{report_number} - {data.get('project_name', '')}"
        )
        
        logger.info(f"Loaded daily report #{report_number} (ID: {report_id})")

    def _handle_report_tab_click(self, data):
        """هندل کلیک روی تب گزارش"""
        report_id = data.get("report_id")
        tab_type = data.get("tab_type")
        tab_name = data.get("tab_name")
        widget_class = data.get("widget_class")
        tab_level = data.get("tab_level", 0)
        
        logger.info(f"Clicked on tab: {tab_name} (type: {tab_type}, level: {tab_level}, widget: {widget_class})")
        
        # اول برو به تب Daily Report
        self.tab_widget.setCurrentIndex(2)
        
        try:
            # اگر تابع load_dynamic_tab وجود دارد، از آن استفاده کن
            if hasattr(self.Daily_Report_tab, "load_dynamic_tab"):
                result = self.Daily_Report_tab.load_dynamic_tab(
                    report_id=report_id,
                    tab_type=tab_type,
                    tab_name=tab_name,
                    widget_class=widget_class,
                    tab_level=tab_level
                )
                
                if result:
                    self.status_manager.show_success(
                        "MainWindow", 
                        f"Loaded {tab_name}"
                    )
                else:
                    self.status_manager.show_message(
                        "MainWindow", 
                        f"Tab {tab_name} could not be loaded", 
                        3000
                    )
                    
            elif hasattr(self.Daily_Report_tab, "load_tab"):
                # Fallback: استفاده از تابع قدیمی
                self.Daily_Report_tab.load_tab(report_id, tab_type)
                self.status_manager.show_message(
                    "MainWindow", 
                    f"Loaded {tab_name} (legacy method)", 
                    2000
                )
            else:
                logger.warning(f"DailyReportTab has no load method for tabs")
                self.status_manager.show_error(
                    "MainWindow", 
                    f"Cannot load tab {tab_name}: No load method found"
                )
                
        except Exception as e:
            logger.error(f"Error loading tab {tab_type}: {e}")
            self.status_manager.show_error(
                "MainWindow", 
                f"Failed to load tab: {str(e)[:50]}"
            )
    
    def get_tab_structure_for_report(self, report_id):
        """دریافت ساختار تب‌ها برای یک گزارش"""
        try:
            # اول از دیتابیس دریافت کن
            structure = self.db_manager.get_report_tab_structure(report_id)
            if structure:
                return structure
                
            # اگر وجود نداشت، از ساختار پیش‌فرض استفاده کن
            logger.info(f"No custom tab structure for report {report_id}, using default")
            return self.db_manager._get_default_tab_structure()
            
        except Exception as e:
            logger.error(f"Error getting tab structure: {e}")
            return []

    def refresh_report_tabs(self, report_id):
        """رفرش تب‌های یک گزارش"""
        try:
            # پیدا کردن آیتم گزارش در درخت
            report_item = self._find_report_item(report_id)
            if report_item:
                # حذف تب‌های قدیمی
                child_count = report_item.childCount()
                for i in range(child_count - 1, -1, -1):
                    report_item.removeChild(report_item.child(i))
                
                # اضافه کردن تب‌های جدید
                self.add_report_tabs_dynamic(report_item, report_id)
                
                self.status_manager.show_success(
                    "MainWindow", 
                    f"Report tabs refreshed"
                )
                return True
                
        except Exception as e:
            logger.error(f"Error refreshing report tabs: {e}")
            
        return False

    def _find_report_item(self, report_id):
        """پیدا کردن آیتم گزارش در درخت"""
        def search_items(item):
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "daily_report" and data.get("id") == report_id:
                return item
                
            for i in range(item.childCount()):
                found = search_items(item.child(i))
                if found:
                    return found
                    
            return None
        
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            found = search_items(item)
            if found:
                return found
                
        return None
    
    def save_current_tab(self):
        """ذخیره تب جاری"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "save_data"):
            try:
                if current_tab.save_data():
                    self.status_manager.show_success(
                        "MainWindow",
                        f"Saved {self.tab_widget.tabText(self.tab_widget.currentIndex())}",
                    )
                else:
                    self.status_manager.show_error(
                        "MainWindow",
                        f"Failed to save {self.tab_widget.tabText(self.tab_widget.currentIndex())}",
                    )
            except Exception as e:
                self.status_manager.show_error(
                    "MainWindow", f"Save error: {str(e)[:50]}"
                )
        else:
            self.status_manager.show_message(
                "MainWindow", "Current tab cannot be saved", 2000
            )

    def auto_save(self):
        """Auto-save data"""
        # این تابع توسط auto_save_manager مدیریت می‌شود
        pass

    def export_current_tab(self):
        """اکسپورت تب جاری"""
        self.status_manager.show_message(
            "MainWindow", "Export feature coming soon...", 2000
        )

    def refresh_all_tabs(self):
        """رفرش همه تب‌ها"""
        self.status_manager.show_progress("MainWindow", "Refreshing data...")

        try:
            # رفرش سلسله مراتب
            self.populate_hierarchy()

            # رفرش هر تب
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if hasattr(tab, "refresh"):
                    tab.refresh()

            self.status_manager.show_success("MainWindow", "Data refreshed")
        except Exception as e:
            self.status_manager.show_error(
                "MainWindow", f"Refresh failed: {str(e)[:50]}"
            )

    def toggle_auto_save(self, enabled):
        """تغییر وضعیت Auto-save"""
        self.auto_save_manager.set_enabled(enabled)
        status = "ON" if enabled else "OFF"

        self.auto_save_action.setText(f"💾 Auto-save: {status}")
        self.auto_save_label.setText(f"💾 Auto-save: {status}")

        self.status_manager.show_message("MainWindow", f"Auto-save {status}", 2000)

    def show_shortcuts_help(self):
        """نمایش help میانبرها"""
        help_text = """
        <h3>🎮 Keyboard Shortcuts</h3>
        <table>
        <tr><td><b>Ctrl+S</b></td><td>Save current tab</td></tr>
        <tr><td><b>Ctrl+Shift+S</b></td><td>Save all tabs</td></tr>
        <tr><td><b>Ctrl+O</b></td><td>Open well</td></tr>
        <tr><td><b>Ctrl+N</b></td><td>New well</td></tr>
        <tr><td><b>Ctrl+E</b></td><td>Export</td></tr>
        <tr><td><b>F5</b></td><td>Refresh</td></tr>
        <tr><td><b>F1</b></td><td>Help</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Exit</td></tr>
        <tr><td><b>Ctrl+Shift+C</b></td><td>New Company</td></tr>
        <tr><td><b>Ctrl+Shift+P</b></td><td>New Project</td></tr>
        <tr><td><b>Ctrl+Shift+W</b></td><td>New Well</td></tr>
        <tr><td><b>Ctrl+R</b></td><td>New Daily Report</td></tr>
        <tr><td><b>Ctrl+P</b></td><td>Print</td></tr>
        </table>
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Keyboard Shortcuts")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(help_text)
        msg_box.exec()

    def open_well_dialog(self):
        """باز کردن دیالوگ انتخاب چاه"""
        if hasattr(self, "well_info_tab"):
            self.well_info_tab.load_well_dialog()

    def show_settings(self):
        """Show settings dialog"""
        from dialogs.settings_dialog import SettingsDialog

        try:
            dialog = SettingsDialog(self)
            if dialog.exec():
                self.status_manager.show_success(
                    "MainWindow", "Settings saved successfully!"
                )
                # اعمال مجدد تم
                self.apply_theme()
        except ImportError:
            QMessageBox.information(
                self,
                "Settings",
                "Settings dialog will be implemented soon.\n\n"
                "Current settings:\n"
                f"- User: {self.user['username']}\n"
                f"- Auto-save: {'Enabled' if self.auto_save_action.isChecked() else 'Disabled'}\n"
                f"- Theme: {self.settings.value('ui/theme', 'Light')}",
            )

    def closeEvent(self, event):
        """رویداد بستن پنجره"""
        # ذخیره همه تب‌ها
        if self.auto_save_action.isChecked():
            self.status_manager.show_message(
                "MainWindow", "Auto-saving before exit...", 1000
            )
            # اینجا می‌توانید save_all_tabs را فراخوانی کنید

        # تایید خروج
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    # ==================== توابع منو ====================

    def toggle_main_toolbar(self, checked):
        """نمایش/مخفی کردن تولبار اصلی"""
        toolbar = self.findChild(QToolBar, "MainToolbar")
        if toolbar:
            toolbar.setVisible(checked)
            status = "shown" if checked else "hidden"
            self.status_manager.show_message(
                "MainWindow", f"Main toolbar {status}", 2000
            )

    def undo_action(self):
        """انجام Undo"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "undo"):
            current_tab.undo()
        else:
            self.status_manager.show_message(
                "MainWindow", "Undo not available in current tab", 2000
            )

    def redo_action(self):
        """انجام Redo"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "redo"):
            current_tab.redo()
        else:
            self.status_manager.show_message(
                "MainWindow", "Redo not available in current tab", 2000
            )

    def cut_action(self):
        """Cut"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "cut"):
            current_tab.cut()
        else:
            # Try to find focused widget
            focused = self.focusWidget()
            if hasattr(focused, "cut"):
                focused.cut()

    def copy_action(self):
        """Copy"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "copy"):
            current_tab.copy()
        else:
            # Try to find focused widget
            focused = self.focusWidget()
            if hasattr(focused, "copy"):
                focused.copy()

    def paste_action(self):
        """Paste"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "paste"):
            current_tab.paste()
        else:
            # Try to find focused widget
            focused = self.focusWidget()
            if hasattr(focused, "paste"):
                focused.paste()

    def select_all_action(self):
        """Select All"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, "select_all"):
            current_tab.select_all()
        else:
            # Try to find focused widget
            focused = self.focusWidget()
            if hasattr(focused, "selectAll"):
                focused.selectAll()

    def open_calculator(self):
        """Open calculator"""
        QMessageBox.information(
            self, "Calculator", "Calculator feature will be implemented soon."
        )

    def open_converter(self):
        """Open unit converter"""
        QMessageBox.information(
            self, "Unit Converter", "Unit converter feature will be implemented soon."
        )

    def print_preview(self):
        """Print preview"""
        QMessageBox.information(
            self, "Print Preview", "Print preview feature will be implemented soon."
        )

    def cascade_windows(self):
        """Cascade windows"""
        # برای برنامه‌های چند پنجره‌ای
        self.status_manager.show_message("MainWindow", "Cascade windows", 2000)

    def tile_windows(self):
        """Tile windows"""
        # برای برنامه‌های چند پنجره‌ای
        self.status_manager.show_message("MainWindow", "Tile windows", 2000)

    def close_all_windows(self):
        """Close all windows"""
        # برای برنامه‌های چند پنجره‌ای
        self.status_manager.show_message("MainWindow", "Close all windows", 2000)

    def check_for_updates(self):
        """Check for updates"""
        QMessageBox.information(
            self, "Check for Updates", "Update check feature will be implemented soon."
        )

    def update_recent_menu(self):
        """Update recent wells menu"""
        if not hasattr(self, "recent_menu"):
            return

        # پاک کردن منوی قبلی
        self.recent_menu.clear()

        # TODO: اضافه کردن چاه‌های اخیر از دیتابیس
        # برای حالا چند نمونه اضافه می‌کنیم
        sample_wells = [
            ("Well #1 - XYZ Field", 1),
            ("Well #2 - ABC Field", 2),
            ("Well #3 - Test Well", 3),
        ]

        for name, well_id in sample_wells:
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked, wid=well_id: self.open_well_by_id(wid)
            )
            self.recent_menu.addAction(action)

        if not sample_wells:
            no_wells_action = QAction("No recent wells", self)
            no_wells_action.setEnabled(False)
            self.recent_menu.addAction(no_wells_action)

        self.recent_menu.addSeparator()

        clear_action = QAction("Clear List", self)
        clear_action.triggered.connect(self.clear_recent_list)
        self.recent_menu.addAction(clear_action)

    def clear_recent_list(self):
        """Clear recent wells list"""
        reply = QMessageBox.question(
            self,
            "Clear Recent List",
            "Are you sure you want to clear the recent wells list?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.status_manager.show_success("MainWindow", "Recent wells list cleared")

    def show_help(self):
        """Show help dialog"""
        help_text = """
        <h2>DrillMaster - User Guide</h2>
        
        <h3>Getting Started</h3>
        <ol>
        <li><b>Create a new well:</b> File → New Well or click 📋 button</li>
        <li><b>Open an existing well:</b> File → Open Well or click 📂 button</li>
        <li><b>Save data:</b> File → Save or Ctrl+S</li>
        <li><b>Create daily report:</b> File → New Daily Report or click 📅 button</li>
        </ol>
        
        <h3>Navigation</h3>
        <ul>
        <li>Use the tree view on the left to navigate between companies, projects, and wells</li>
        <li>Switch between tabs to access different features</li>
        <li>Use the toolbar for quick access to common functions</li>
        </ul>
        
        <h3>Keyboard Shortcuts</h3>
        <table border="1" cellpadding="5">
        <tr><th>Shortcut</th><th>Action</th></tr>
        <tr><td>Ctrl+N</td><td>New Well</td></tr>
        <tr><td>Ctrl+O</td><td>Open Well</td></tr>
        <tr><td>Ctrl+S</td><td>Save</td></tr>
        <tr><td>Ctrl+Shift+S</td><td>Save All</td></tr>
        <tr><td>Ctrl+R</td><td>New Daily Report</td></tr>
        <tr><td>Ctrl+E</td><td>Export</td></tr>
        <tr><td>Ctrl+P</td><td>Print</td></tr>
        <tr><td>F5</td><td>Refresh</td></tr>
        <tr><td>F1</td><td>Help</td></tr>
        <tr><td>Ctrl+Q</td><td>Exit</td></tr>
        </table>
        
        <h3>Need More Help?</h3>
        <p>Contact support: support@drillmaster.com</p>
        """

        dialog = QDialog(self)
        dialog.setWindowTitle("DrillMaster Help")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout()

        # Text browser برای نمایش help
        text_browser = QTextBrowser()
        text_browser.setHtml(help_text)
        text_browser.setOpenExternalLinks(True)

        layout.addWidget(text_browser)

        # دکمه بستن
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        dialog.exec()

    def cleanup(self):
        """Cleanup resources"""
        # Cleanup tabs
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, "cleanup"):
                tab.cleanup()

        logger.info("Main window cleanup completed")

    def save_all_tabs(self):
        """ذخیره همه تب‌ها"""
        saved_count = 0
        total_tabs = self.tab_widget.count()

        self.status_manager.show_progress("MainWindow", "Saving all tabs...")

        for i in range(total_tabs):
            tab = self.tab_widget.widget(i)
            tab_name = self.tab_widget.tabText(i)

            if hasattr(tab, "save_data"):
                try:
                    if tab.save_data():
                        saved_count += 1
                        logger.info(f"✅ Saved tab: {tab_name}")
                    else:
                        logger.warning(f"❌ Failed to save tab: {tab_name}")
                except Exception as e:
                    logger.error(f"Error saving tab {tab_name}: {e}")

        if saved_count > 0:
            self.status_manager.show_success(
                "MainWindow", f"Saved {saved_count}/{total_tabs} tabs successfully!"
            )
        else:
            self.status_manager.show_message(
                "MainWindow", "No tabs could be saved", 3000
            )

        return saved_count

    def new_well_dialog(self):
        """باز کردن دیالوگ چاه جدید"""
        # رفتن به تب Well Info و clear کردن فرم
        self.tab_widget.setCurrentIndex(1)  # تب Well Info
        if hasattr(self, "well_info_tab"):
            self.well_info_tab.clear_form_fields()

        self.status_manager.show_message("MainWindow", "Ready to create new well", 2000)

    def open_well_dialog(self):
        """باز کردن دیالوگ انتخاب چاه"""
        if hasattr(self, "well_info_tab"):
            self.well_info_tab.load_well_dialog()
        else:
            QMessageBox.information(
                self, "Open Well", "Please use the Well Info tab to open wells"
            )

    def export_current_tab(self):
        """اکسپورت تب جاری"""
        current_tab = self.tab_widget.currentWidget()
        tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())

        self.status_manager.show_message("MainWindow", f"Exporting {tab_name}...", 2000)

        # اگر تب export_manager دارد
        if hasattr(current_tab, "export_manager"):
            current_tab.export_manager.export_table_with_dialog(
                getattr(current_tab, "table_widget", None),
                default_name=tab_name.lower().replace(" ", "_"),
            )
        else:
            QMessageBox.information(
                self,
                "Export",
                f"Export feature for '{tab_name}' will be implemented soon.",
            )

    def apply_theme(self):
        """اعمال تم تنظیم شده"""
        theme = self.settings.value("ui/theme", "Light")
        if theme == "Dark":
            self.setStyleSheet(
                """
                QMainWindow { background-color: #2b2b2b; color: #ffffff; }
                QWidget { background-color: #2b2b2b; color: #ffffff; }
            """
            )
        else:
            self.setStyleSheet("")  # بازگشت به حالت پیش‌فرض

    def set_theme(self, theme):
        """تنظیم تم"""
        self.settings.setValue("ui/theme", theme)
        self.apply_theme()

    def open_well_by_id(self, well_id):
        """باز کردن چاه با ID"""
        try:
            if self.tab_widget.currentIndex() != 1:  # اگر در تب Well Info نیستیم
                self.tab_widget.setCurrentIndex(1)

            if hasattr(self, "well_info_tab"):
                # بارگذاری چاه در تب Well Info
                self.well_info_tab.load_well_by_id(well_id)
                self.status_manager.show_success("MainWindow", f"Well {well_id} loaded")
        except Exception as e:
            logger.error(f"Error opening well {well_id}: {e}")
    def load_and_select_well(self, well_id):
        """بارگذاری و انتخاب چاه"""
        try:
            well_data = self.db_manager.get_well_by_id(well_id)
            if well_data:
                # انتخاب در tree
                self.select_item_in_tree("well", well_id)
                
                # بارگذاری در تب Well Info
                self.tab_widget.setCurrentIndex(1)  # برو به تب Well Info
                if hasattr(self, "well_info_tab"):
                    self.well_info_tab.load_well_by_id(well_id)
                
                # آپدیت status bar
                self.current_well = well_data
                self.current_well_label.setText(f"🛢️ Well: {well_data['name']}")
                
                self.status_manager.show_success(
                    "MainWindow",
                    f"Well '{well_data['name']}' loaded successfully"
                )
        except Exception as e:
            logger.error(f"Error loading well {well_id}: {e}")

    def load_and_select_project(self, project_id):
        """بارگذاری و انتخاب پروژه"""
        try:
            session = self.db_manager.create_session()
            from core.database import Project, Well
            
            # یافتن پروژه
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                # یافتن اولین چاه
                well = session.query(Well).filter(Well.project_id == project_id).first()
                if well:
                    self.load_and_select_well(well.id)
                else:
                    # اگر چاهی نداشت، پیام بده
                    self.status_manager.show_message(
                        "MainWindow",
                        f"Project '{project.name}' has no wells. Please create a well."
                    )
                    self.tab_widget.setCurrentIndex(1)  # برو به تب Well Info
        except Exception as e:
            logger.error(f"Error loading project {project_id}: {e}")
        finally:
            try:
                session.close()
            except:
                pass

    def select_item_in_tree(self, item_type, item_id):
        """انتخاب آیتم در tree hierarchy"""
        def find_item(item):
            if item is None:
                return None
                
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == item_type and data.get("id") == item_id:
                return item
                
            for i in range(item.childCount()):
                found = find_item(item.child(i))
                if found:
                    return found
                    
            return None
        
        # جستجو در tree
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            found = find_item(item)
            if found:
                self.tree_widget.setCurrentItem(found)  # این خط درست است
                self.tree_widget.scrollToItem(found)
                
                # باز کردن parent ها
                parent = found.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                    
                break
                
    def showEvent(self, event):
        """رویداد نمایش پنجره"""
        super().showEvent(event)
        
        # وقتی پنجره نمایش داده می‌شود، منوی اصلی را بررسی کنید
        QTimer.singleShot(50, self.ensure_menubar_visible)
        
        # همچنین لاگ هندسه پنجره
        logger.info(f"Window shown - Geometry: {self.geometry()}, Frame: {self.frameGeometry()}")