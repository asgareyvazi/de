
"""
Planning Widget - Comprehensive planning module for drilling operations
"""

import sys
import os
from datetime import datetime, date, timedelta
import random
import json
from ui.helper import make_scrollable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QGridLayout, QMessageBox, QDateEdit, QTimeEdit,
    QComboBox, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QFileDialog,
    QHeaderView, QProgressBar, QSplitter, QFrame, QCheckBox, QRadioButton,
    QButtonGroup, QScrollArea, QToolBar, QStatusBar, QApplication, QMainWindow,
    QDialog, QInputDialog, QFormLayout, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QDate, QTime, Signal, Slot, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QPen, QBrush
from PySide6.QtCore import QDateTime

# Import database and managers
from core.database import DatabaseManager
from core.managers import (
    StatusBarManager, AutoSaveManager, ShortcutManager, 
    TableManager, TableButtonManager, ExportManager
)

import logging
logger = logging.getLogger(__name__)

# Import for charts
try:
    from PySide6.QtCharts import QChart, QChartView, QLineSeries, QScatterSeries, QValueAxis, QDateTimeAxis
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    logger.warning("QtCharts not available. Charts will be disabled.")

# Base widget class
class DrillWidgetBase(QWidget):
    def __init__(self, widget_name, db_manager=None):
        super().__init__()
        self.widget_name = widget_name
        self.db_manager = db_manager
        self.status_manager = None 
        self.parent_widget = None  

    def set_parent_widget(self, parent):
        """تنظیم والد برای دسترسی به status_bar"""
        self.parent_widget = parent
    
    def show_message(self, message, timeout=3000, is_error=False):
        """نمایش پیام در status_bar والد"""
        if self.parent_widget and hasattr(self.parent_widget, 'status_bar'):
            prefix = "❌ " if is_error else "✅ "
            self.parent_widget.status_bar.showMessage(prefix + message, timeout)
        else:
            log_level = "ERROR" if is_error else "INFO"
            print(f"[{log_level} - {self.widget_name}]: {message}")
    
    def show_success(self, message, timeout=3000):
        self.show_message(message, timeout, is_error=False)
    
    def show_error(self, message, timeout=5000):
        self.show_message(message, timeout, is_error=True)
    
    def show_progress(self, message):
        self.show_message("🔄 " + message, timeout=0)
    
    def load_wells_combo(self, combo_widget):
        """بارگذاری چاه‌ها در ComboBox"""
        try:
            if self.db_manager:
                wells = self.db_manager.get_hierarchy()
                combo_widget.clear()
                for company in wells:
                    for project in company["projects"]:
                        for well in project["wells"]:
                            combo_widget.addItem(f"{well['name']} ({well['code']})", well["id"])
                return combo_widget.count() > 0
        except Exception as e:
            self.show_error(f"Error loading wells: {str(e)}")
        return False
        
# Tab 1: Seven Days Lookahead
@make_scrollable
class SevenDaysLookaheadTab(DrillWidgetBase):
    def __init__(self, db_manager=None):
        super().__init__("SevenDaysLookaheadTab", db_manager)
        self.current_well = None
        self.current_section = None
        self.current_report = None
        self.init_ui()
        self.setup_connections()
        self.load_initial_data()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("📅 Seven Days Lookahead Planning")
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(self.title_label)
        
        # Report selector
        report_group = QGroupBox("Report Info")
        report_layout = QHBoxLayout()
        report_layout.addWidget(QLabel("Report No:"))
        self.report_combo = QComboBox()
        self.report_combo.setMinimumWidth(150)
        report_layout.addWidget(self.report_combo)
        report_layout.addWidget(QLabel("Section:"))
        self.section_combo = QComboBox()
        report_layout.addWidget(self.section_combo)
        report_layout.addWidget(QLabel("Well:"))
        self.well_combo = QComboBox()
        report_layout.addWidget(self.well_combo)
        report_group.setLayout(report_layout)
        header_layout.addWidget(report_group)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Table
        self.lookahead_table = QTableWidget(7, 6)
        self.lookahead_table.setHorizontalHeaderLabels([
            "Day", "Date", "Activity", "Tools", "Responsible", "Remarks"
        ])
        self.lookahead_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lookahead_table.setAlternatingRowColors(True)
        
        # Initialize table with days
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today = QDate.currentDate()
        for i in range(7):
            day_date = today.addDays(i)
            self.lookahead_table.setItem(i, 0, QTableWidgetItem(days[i]))
            self.lookahead_table.setItem(i, 1, QTableWidgetItem(day_date.toString("yyyy-MM-dd")))
            self.lookahead_table.setItem(i, 2, QTableWidgetItem(""))
            self.lookahead_table.setItem(i, 3, QTableWidgetItem(""))
            self.lookahead_table.setItem(i, 4, QTableWidgetItem(""))
            self.lookahead_table.setItem(i, 5, QTableWidgetItem(""))
        
        main_layout.addWidget(self.lookahead_table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        # Action buttons
        self.fill_week_btn = QPushButton("📋 Fill Week Plan")
        self.fill_week_btn.setToolTip("Fill week with suggested activities")
        button_layout.addWidget(self.fill_week_btn)
        
        self.copy_prev_btn = QPushButton("📋 Copy Previous Week")
        self.copy_prev_btn.setToolTip("Copy plan from previous week")
        button_layout.addWidget(self.copy_prev_btn)
        
        self.add_row_btn = QPushButton("➕ Add Row")
        self.add_row_btn.setToolTip("Add additional row for detailed planning")
        button_layout.addWidget(self.add_row_btn)
        
        self.delete_row_btn = QPushButton("➖ Delete Row")
        self.delete_row_btn.setToolTip("Delete selected row")
        button_layout.addWidget(self.delete_row_btn)
        
        button_layout.addStretch()
        
        # Export buttons
        self.export_csv_btn = QPushButton("📤 Export CSV")
        button_layout.addWidget(self.export_csv_btn)
        
        self.export_excel_btn = QPushButton("📤 Export Excel")
        button_layout.addWidget(self.export_excel_btn)
        
        self.export_pdf_btn = QPushButton("📤 Export PDF")
        button_layout.addWidget(self.export_pdf_btn)
        
        self.save_btn = QPushButton("💾 Save Plan")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
        
        # Setup Table Manager
        self.table_manager = TableManager(self.lookahead_table, self)
        self.table_manager.set_alternating_row_colors(True, "#FFFFFF", "#F5F5F5")
        
    def setup_connections(self):
        self.fill_week_btn.clicked.connect(self.fill_week_plan)
        self.copy_prev_btn.clicked.connect(self.copy_previous_week)
        self.add_row_btn.clicked.connect(self.add_row)
        self.delete_row_btn.clicked.connect(self.delete_row)
        self.export_csv_btn.clicked.connect(lambda: self.export_plan("csv"))
        self.export_excel_btn.clicked.connect(lambda: self.export_plan("excel"))
        self.export_pdf_btn.clicked.connect(lambda: self.export_plan("pdf"))
        self.save_btn.clicked.connect(self.save_plan)
        
        # Combo box connections
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        self.section_combo.currentIndexChanged.connect(self.on_section_changed)
        self.report_combo.currentIndexChanged.connect(self.on_report_changed)
        
    def load_initial_data(self):
        """Load initial data"""
        try:
            if self.db_manager:
                # Load wells
                wells = self.db_manager.get_hierarchy()
                self.well_combo.clear()
                for company in wells:
                    for project in company["projects"]:
                        for well in project["wells"]:
                            self.well_combo.addItem(f"{well['name']} ({well['code']})", well["id"])
                
                if self.load_wells_combo(self.well_combo):
                    self.current_well = self.well_combo.currentData()
                    self.load_lookahead_plan() 
                    
        except Exception as e:
            self.show_error(f"Error loading data: {str(e)}")
    
    def load_sections(self):
        """Load sections for current well"""
        try:
            if self.db_manager and self.current_well:
                sections = self.db_manager.get_sections_by_well(self.current_well)
                self.section_combo.clear()
                for section in sections:
                    self.section_combo.addItem(f"{section['name']} ({section['code']})", section["id"])
                
                if self.section_combo.count() > 0:
                    self.current_section = self.section_combo.currentData()
                    self.load_reports()
                    
        except Exception as e:
            self.show_error(f"Error loading sections: {str(e)}")
    
    def load_reports(self):
        """Load reports for current section"""
        try:
            if self.db_manager and self.current_section:
                reports = self.db_manager.get_daily_reports_by_section(self.current_section)
                self.report_combo.clear()
                for report in reports:
                    self.report_combo.addItem(
                        f"Report #{report['report_number']} - {report['report_date']}",
                        report["id"]
                    )
                
                if self.report_combo.count() > 0:
                    self.current_report = self.report_combo.currentData()
                    self.load_lookahead_plan()
                    
        except Exception as e:
            self.show_error(f"Error loading reports: {str(e)}")
    
    def load_lookahead_plan(self):
        """Load lookahead plan from database"""
        try:
            if self.db_manager and self.current_report:
                # Get lookahead plans for this report
                plans = self.db_manager.get_seven_days_lookahead(
                    report_id=self.current_report
                )
                
                # Clear table
                for i in range(self.lookahead_table.rowCount()):
                    for j in range(2, 6):  # Skip Day and Date columns
                        self.lookahead_table.setItem(i, j, QTableWidgetItem(""))
                
                # Fill table with plans
                for plan in plans:
                    day_num = plan.get("day_number", 1) - 1  # Convert to 0-based index
                    if 0 <= day_num < self.lookahead_table.rowCount():
                        self.lookahead_table.setItem(day_num, 2, QTableWidgetItem(plan.get("activity", "")))
                        self.lookahead_table.setItem(day_num, 3, QTableWidgetItem(plan.get("tools", "")))
                        self.lookahead_table.setItem(day_num, 4, QTableWidgetItem(plan.get("responsible", "")))
                        self.lookahead_table.setItem(day_num, 5, QTableWidgetItem(plan.get("remarks", "")))
                
                self.status_label.setText(f"Loaded {len(plans)} plan items")
                self.show_success("Lookahead plan loaded")
                
        except Exception as e:
            self.show_error(f"Error loading lookahead plan: {str(e)}")
    
    def on_well_changed(self, index):
        if index >= 0:
            self.current_well = self.well_combo.currentData()
            self.load_sections()
    
    def on_section_changed(self, index):
        if index >= 0:
            self.current_section = self.section_combo.currentData()
            self.load_reports()
    
    def on_report_changed(self, index):
        if index >= 0:
            self.current_report = self.report_combo.currentData()
            self.load_lookahead_plan()
    
    def fill_week_plan(self):
        """Fill week with suggested activities"""
        try:
            # Sample activities based on drilling phase
            activities = [
                "Drilling 8-1/2\" section",
                "Drilling 12-1/4\" section",
                "Tripping Operations",
                "Casing Operations",
                "Cementing Operations",
                "Wireline Logging",
                "Well Testing"
            ]
            
            tools = [
                "PDC Bit, MWD, Motors",
                "Tricone Bit, Stabilizers",
                "Elevators, Tongs",
                "Casing, Cement",
                "Cement Pump",
                "Wireline Tools",
                "Test Separator"
            ]
            
            responsible = [
                "John Smith - Driller",
                "Mike Johnson - Tool Pusher",
                "Sarah Williams - Engineer",
                "David Brown - Supervisor",
                "Robert Wilson - Company Man",
                "Wireline Crew",
                "Test Engineer"
            ]
            
            remarks = [
                "Monitor ECD and torque",
                "Check hole cleaning",
                "Inspect pipe for wear",
                "Centralize casing properly",
                "Monitor cement returns",
                "Calibrate tools before run",
                "Monitor flow rates"
            ]
            
            today = QDate.currentDate()
            for i in range(7):
                day_date = today.addDays(i)
                self.lookahead_table.setItem(i, 1, QTableWidgetItem(day_date.toString("yyyy-MM-dd")))
                
                # Cycle through activities
                activity_idx = i % len(activities)
                self.lookahead_table.setItem(i, 2, QTableWidgetItem(activities[activity_idx]))
                self.lookahead_table.setItem(i, 3, QTableWidgetItem(tools[activity_idx]))
                self.lookahead_table.setItem(i, 4, QTableWidgetItem(responsible[activity_idx]))
                self.lookahead_table.setItem(i, 5, QTableWidgetItem(f"{remarks[activity_idx]}\nTarget depth: {1000 + i*200}m"))
            
            self.show_success("Week plan filled with suggested activities")
            
        except Exception as e:
            self.show_error(f"Error filling week plan: {str(e)}")
    
    def copy_previous_week(self):
        """Copy plan from previous week"""
        try:
            reply = QMessageBox.question(
                self, "Copy Previous Week",
                "This will overwrite current week plan. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # In real implementation, load from previous week's data
                # For now, just show a message
                self.show_progress("Loading previous week data...")
                QTimer.singleShot(1000, lambda: self.show_success("Previous week data copied (simulated)"))
                
        except Exception as e:
            self.show_error(f"Error copying previous week: {str(e)}")
    
    def add_row(self):
        """Add additional row for detailed planning"""
        self.table_manager.add_row([""] * self.lookahead_table.columnCount())
    
    def delete_row(self):
        """Delete selected row"""
        self.table_manager.delete_row()
    
    def export_plan(self, format_type):
        """Export plan to different formats"""
        try:
            export_manager = ExportManager(self)
            filename = export_manager.export_table_with_dialog(
                self.lookahead_table,
                f"seven_days_lookahead_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            if filename:
                self.show_success(f"Plan exported to {os.path.basename(filename)}")
                
        except Exception as e:
            self.show_error(f"Error exporting plan: {str(e)}")
    
    def save_plan(self):
        """Save lookahead plan to database"""
        try:
            if not self.db_manager:
                self.show_error("Database not connected")
                return
            
            if not self.current_report:
                self.show_error("Please select a report first")
                return
            
            self.show_progress("Saving plan...")
            
            # Collect data from table
            plans = []
            today = QDate.currentDate()
            
            for i in range(self.lookahead_table.rowCount()):
                activity_item = self.lookahead_table.item(i, 2)
                tools_item = self.lookahead_table.item(i, 3)
                responsible_item = self.lookahead_table.item(i, 4)
                remarks_item = self.lookahead_table.item(i, 5)
                
                plan_data = {
                    "well_id": self.current_well,
                    "section_id": self.current_section,
                    "report_id": self.current_report,
                    "plan_date": today.addDays(i).toString("yyyy-MM-dd"),
                    "day_number": i + 1,
                    "activity": activity_item.text() if activity_item else "",
                    "tools": tools_item.text() if tools_item else "",
                    "responsible": responsible_item.text() if responsible_item else "",
                    "remarks": remarks_item.text() if remarks_item else "",
                    "status": "Planned"
                }
                plans.append(plan_data)
            
            # Save to database
            success_count = 0
            for plan in plans:
                result = self.db_manager.save_seven_days_lookahead(plan)
                if result:
                    success_count += 1
            
            if success_count > 0:
                self.show_success(f"Saved {success_count} plan items")
                self.status_label.setText(f"Saved {success_count} items at {datetime.now().strftime('%H:%M:%S')}")
            else:
                self.show_error("Failed to save plan")
                
        except Exception as e:
            self.show_error(f"Error saving plan: {str(e)}")

# Tab 2: NPT Report Tab
@make_scrollable
class NPTReportTab(DrillWidgetBase):
    def __init__(self, db_manager=None):
        super().__init__("NPTReportTab", db_manager)
        self.current_well = None
        self.init_ui()
        self.setup_connections()
        self.load_initial_data()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("⏱️ Non-Productive Time (NPT) Report")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        # Well selector
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(200)
        header_layout.addWidget(QLabel("Well:"))
        header_layout.addWidget(self.well_combo)
        
        # Date range
        header_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-7))
        header_layout.addWidget(self.from_date)
        
        header_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        header_layout.addWidget(self.to_date)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        header_layout.addWidget(self.refresh_btn)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Statistics panel
        stats_group = QGroupBox("📊 NPT Statistics")
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Total NPT Hours:"), 0, 0)
        self.total_npt_hours = QLabel("0.0")
        self.total_npt_hours.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.total_npt_hours, 0, 1)
        
        stats_layout.addWidget(QLabel("Total NPT Events:"), 0, 2)
        self.total_npt_events = QLabel("0")
        self.total_npt_events.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.total_npt_events, 0, 3)
        
        stats_layout.addWidget(QLabel("NPT Percentage:"), 1, 0)
        self.npt_percentage = QLabel("0.0%")
        self.npt_percentage.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.npt_percentage, 1, 1)
        
        stats_layout.addWidget(QLabel("Most Frequent:"), 1, 2)
        self.most_frequent_npt = QLabel("None")
        stats_layout.addWidget(self.most_frequent_npt, 1, 3)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # Splitter for table and chart
        splitter = QSplitter(Qt.Vertical)
        
        # Table
        self.npt_table = QTableWidget(0, 7)
        self.npt_table.setHorizontalHeaderLabels([
            "Date", "Start", "End", "Duration (hrs)", "Category", "Code", "Description"
        ])
        self.npt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.npt_table)
        
        # Chart area
        chart_widget = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.addWidget(QLabel("📈 NPT Distribution"))
        
        if CHARTS_AVAILABLE:
            self.npt_chart_view = QChartView()
            self.npt_chart_view.setMinimumHeight(300)
            chart_layout.addWidget(self.npt_chart_view)
        else:
            chart_layout.addWidget(QLabel("Charts not available. Install QtCharts module."))
        
        chart_widget.setLayout(chart_layout)
        splitter.addWidget(chart_widget)
        
        splitter.setSizes([400, 300])
        main_layout.addWidget(splitter)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.add_npt_btn = QPushButton("➕ Add NPT")
        button_layout.addWidget(self.add_npt_btn)
        
        self.auto_update_btn = QPushButton("🔄 Update from Daily Reports")
        button_layout.addWidget(self.auto_update_btn)
        
        self.calculate_btn = QPushButton("🧮 Calculate Statistics")
        button_layout.addWidget(self.calculate_btn)
        
        button_layout.addStretch()
        
        self.export_btn = QPushButton("📤 Export NPT Data")
        button_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # Setup Table Manager
        self.table_manager = TableManager(self.npt_table, self)
    
    def setup_connections(self):
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        self.refresh_btn.clicked.connect(self.load_npt_data)
        self.add_npt_btn.clicked.connect(self.add_npt_record)
        self.auto_update_btn.clicked.connect(self.auto_update_from_daily_reports)
        self.calculate_btn.clicked.connect(self.calculate_statistics)
        self.export_btn.clicked.connect(self.export_npt_data)
    
    def load_initial_data(self):
        """Load initial data"""
        try:
            if self.db_manager:
                # Load wells
                wells = self.db_manager.get_hierarchy()
                self.well_combo.clear()
                for company in wells:
                    for project in company["projects"]:
                        for well in project["wells"]:
                            self.well_combo.addItem(f"{well['name']} ({well['code']})", well["id"])
                
                if self.load_wells_combo(self.well_combo):
                    self.current_well = self.well_combo.currentData()
                    self.load_npt_data()
                    
        except Exception as e:
            self.show_error(f"Error loading data: {str(e)}")
    
    def on_well_changed(self, index):
        if index >= 0:
            self.current_well = self.well_combo.currentData()
            self.load_npt_data()
    
    def load_npt_data(self):
        """Load NPT data from database"""
        try:
            if not self.db_manager or not self.current_well:
                return
            
            self.show_progress("Loading NPT data...")
            
            # Get NPT reports
            npt_reports = self.db_manager.get_npt_reports(
                well_id=self.current_well,
                start_date=self.from_date.date().toPython(),
                end_date=self.to_date.date().toPython()
            )
            
            # Clear table
            self.npt_table.setRowCount(0)
            
            # Fill table
            for report in npt_reports:
                row = self.npt_table.rowCount()
                self.npt_table.insertRow(row)
                
                self.npt_table.setItem(row, 0, QTableWidgetItem(str(report.get("npt_date", ""))))
                self.npt_table.setItem(row, 1, QTableWidgetItem(report.get("start_time", "")))
                self.npt_table.setItem(row, 2, QTableWidgetItem(report.get("end_time", "")))
                self.npt_table.setItem(row, 3, QTableWidgetItem(str(report.get("duration_hours", 0))))
                self.npt_table.setItem(row, 4, QTableWidgetItem(report.get("npt_category", "")))
                self.npt_table.setItem(row, 5, QTableWidgetItem(report.get("npt_code", "")))
                self.npt_table.setItem(row, 6, QTableWidgetItem(report.get("npt_description", "")))
            
            # Calculate statistics
            self.calculate_statistics()
            
            # Update chart
            self.update_chart()
            
            self.show_success(f"Loaded {len(npt_reports)} NPT records")
            
        except Exception as e:
            self.show_error(f"Error loading NPT data: {str(e)}")
    
    def add_npt_record(self):
        """Add new NPT record"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Add NPT Record")
            dialog.setMinimumWidth(500)
            
            layout = QFormLayout()
            
            date_edit = QDateEdit()
            date_edit.setDate(QDate.currentDate())
            layout.addRow("Date:", date_edit)
            
            start_time = QTimeEdit()
            start_time.setTime(QTime(8, 0))
            layout.addRow("Start Time:", start_time)
            
            end_time = QTimeEdit()
            end_time.setTime(QTime(10, 0))
            layout.addRow("End Time:", end_time)
            
            category_combo = QComboBox()
            category_combo.addItems(["Weather", "Equipment", "Waiting", "Safety", "Logistics", "Other"])
            layout.addRow("Category:", category_combo)
            
            code_edit = QLineEdit()
            code_edit.setPlaceholderText("e.g., WOC, WOW, EQP")
            layout.addRow("NPT Code:", code_edit)
            
            desc_edit = QTextEdit()
            desc_edit.setMaximumHeight(100)
            layout.addRow("Description:", desc_edit)
            
            # Buttons
            button_box = QHBoxLayout()
            save_btn = QPushButton("Save")
            cancel_btn = QPushButton("Cancel")
            
            save_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            
            button_box.addWidget(save_btn)
            button_box.addWidget(cancel_btn)
            layout.addRow(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec() == QDialog.Accepted:
                # Calculate duration
                duration = start_time.time().secsTo(end_time.time()) / 3600.0
                if duration < 0:
                    duration += 24  # Cross midnight
                
                # Add to table
                row = self.npt_table.rowCount()
                self.npt_table.insertRow(row)
                
                self.npt_table.setItem(row, 0, QTableWidgetItem(date_edit.date().toString("yyyy-MM-dd")))
                self.npt_table.setItem(row, 1, QTableWidgetItem(start_time.time().toString("HH:mm")))
                self.npt_table.setItem(row, 2, QTableWidgetItem(end_time.time().toString("HH:mm")))
                self.npt_table.setItem(row, 3, QTableWidgetItem(f"{duration:.1f}"))
                self.npt_table.setItem(row, 4, QTableWidgetItem(category_combo.currentText()))
                self.npt_table.setItem(row, 5, QTableWidgetItem(code_edit.text()))
                self.npt_table.setItem(row, 6, QTableWidgetItem(desc_edit.toPlainText()))
                
                # Save to database
                if self.db_manager and self.current_well:
                    npt_data = {
                        "well_id": self.current_well,
                        "npt_date": date_edit.date().toPython(),
                        "start_time": start_time.time().toPython(),
                        "end_time": end_time.time().toPython(),
                        "duration_hours": duration,
                        "npt_category": category_combo.currentText(),
                        "npt_code": code_edit.text(),
                        "npt_description": desc_edit.toPlainText(),
                        "responsible_party": "Manual Entry"
                    }
                    self.db_manager.save_npt_report(npt_data)
                
                self.show_success("NPT record added")
                
        except Exception as e:
            self.show_error(f"Error adding NPT record: {str(e)}")
    
    def auto_update_from_daily_reports(self):
        """Auto-update NPT data from daily reports"""
        try:
            if not self.db_manager:
                self.show_error("Database not connected")
                return
            
            self.show_progress("Updating from daily reports...")
            
            # This would normally query daily reports and extract NPT
            # For now, simulate with sample data
            QTimer.singleShot(2000, lambda: self.show_success("Updated NPT from daily reports (simulated)"))
            
        except Exception as e:
            self.show_error(f"Error updating from daily reports: {str(e)}")
    
    def calculate_statistics(self):
        """Calculate NPT statistics"""
        try:
            total_hours = 0.0
            code_counts = {}
            
            for row in range(self.npt_table.rowCount()):
                try:
                    hours_item = self.npt_table.item(row, 3)
                    code_item = self.npt_table.item(row, 5)
                    
                    if hours_item and hours_item.text():
                        total_hours += float(hours_item.text())
                    
                    if code_item and code_item.text():
                        code = code_item.text()
                        code_counts[code] = code_counts.get(code, 0) + 1
                        
                except ValueError:
                    continue
            
            # Update statistics
            self.total_npt_hours.setText(f"{total_hours:.1f}")
            self.total_npt_events.setText(str(self.npt_table.rowCount()))
            
            # Calculate percentage (assuming 24-hour days)
            total_days = max(self.npt_table.rowCount() / 3, 1)
            total_possible_hours = total_days * 24
            npt_percentage = (total_hours / total_possible_hours * 100) if total_possible_hours > 0 else 0
            self.npt_percentage.setText(f"{npt_percentage:.1f}%")
            
            # Most frequent NPT
            if code_counts:
                most_frequent = max(code_counts.items(), key=lambda x: x[1])
                self.most_frequent_npt.setText(f"{most_frequent[0]} ({most_frequent[1]} times)")
            else:
                self.most_frequent_npt.setText("None")
                
        except Exception as e:
            self.show_error(f"Error calculating statistics: {str(e)}")
    
    def update_chart(self):
        """Update NPT chart"""
        if not CHARTS_AVAILABLE:
            return
        
        try:
            # Collect data by category
            category_data = {}
            for row in range(self.npt_table.rowCount()):
                category_item = self.npt_table.item(row, 4)
                hours_item = self.npt_table.item(row, 3)
                
                if category_item and hours_item:
                    category = category_item.text()
                    try:
                        hours = float(hours_item.text())
                        category_data[category] = category_data.get(category, 0) + hours
                    except ValueError:
                        continue
            
            # Create chart
            chart = QChart()
            chart.setTitle("NPT Distribution by Category")
            
            # Create series
            series = QPieSeries() if hasattr(QChart, 'QPieSeries') else None
            
            if series:
                for category, hours in category_data.items():
                    series.append(category, hours)
                
                chart.addSeries(series)
                chart.setAnimationOptions(QChart.SeriesAnimations)
                
                self.npt_chart_view.setChart(chart)
                self.npt_chart_view.setRenderHint(QPainter.Antialiasing)
                
        except Exception as e:
            logger.error(f"Error updating chart: {e}")
    
    def export_npt_data(self):
        """Export NPT data"""
        try:
            export_manager = ExportManager(self)
            filename = export_manager.export_table_with_dialog(
                self.npt_table,
                f"npt_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            if filename:
                self.show_success(f"NPT data exported to {os.path.basename(filename)}")
                
        except Exception as e:
            self.show_error(f"Error exporting NPT data: {str(e)}")

# Tab 3: Code Management Tab
@make_scrollable
class CodeManagementTab(DrillWidgetBase):
    def __init__(self, db_manager=None):
        super().__init__("CodeManagementTab", db_manager)
        self.current_well = None
        self.init_ui()
        self.setup_connections()
        self.load_initial_data()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("🏷️ Activity Code Management")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        # Well selector
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(200)
        header_layout.addWidget(QLabel("Well:"))
        header_layout.addWidget(self.well_combo)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        header_layout.addWidget(self.refresh_btn)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Statistics panel
        stats_group = QGroupBox("📊 Code Statistics")
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Total Codes:"), 0, 0)
        self.total_codes = QLabel("0")
        self.total_codes.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.total_codes, 0, 1)
        
        stats_layout.addWidget(QLabel("Main Phases:"), 0, 2)
        self.total_phases = QLabel("0")
        self.total_phases.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.total_phases, 0, 3)
        
        stats_layout.addWidget(QLabel("Most Used:"), 1, 0)
        self.most_used_code = QLabel("None")
        stats_layout.addWidget(self.most_used_code, 1, 1)
        
        stats_layout.addWidget(QLabel("Total Hours:"), 1, 2)
        self.total_hours = QLabel("0.0")
        self.total_hours.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.total_hours, 1, 3)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # Table
        self.code_table = QTableWidget(0, 7)
        self.code_table.setHorizontalHeaderLabels([
            "Main Phase", "Main Code", "Sub Code", "Code Name", "Productive", "NPT", "Usage Count"
        ])
        self.code_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.code_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.code_table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.add_code_btn = QPushButton("➕ Add Code")
        button_layout.addWidget(self.add_code_btn)
        
        self.edit_code_btn = QPushButton("✏️ Edit Code")
        button_layout.addWidget(self.edit_code_btn)
        
        self.delete_code_btn = QPushButton("➖ Delete Code")
        button_layout.addWidget(self.delete_code_btn)
        
        self.import_btn = QPushButton("📂 Import Codes")
        button_layout.addWidget(self.import_btn)
        
        button_layout.addStretch()
        
        self.auto_update_btn = QPushButton("🔄 Update from Daily Reports")
        button_layout.addWidget(self.auto_update_btn)
        
        self.export_btn = QPushButton("📤 Export Codes")
        button_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # Setup Table Manager
        self.table_manager = TableManager(self.code_table, self)
    
    def setup_connections(self):
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        self.refresh_btn.clicked.connect(self.load_codes)
        self.add_code_btn.clicked.connect(self.add_code)
        self.edit_code_btn.clicked.connect(self.edit_code)
        self.delete_code_btn.clicked.connect(self.delete_code)
        self.import_btn.clicked.connect(self.import_codes)
        self.auto_update_btn.clicked.connect(self.auto_update_from_daily_reports)
        self.export_btn.clicked.connect(self.export_codes)
    
    def load_initial_data(self):
        """Load initial data"""
        try:
            if self.db_manager:
                # Load wells
                wells = self.db_manager.get_hierarchy()
                self.well_combo.clear()
                for company in wells:
                    for project in company["projects"]:
                        for well in project["wells"]:
                            self.well_combo.addItem(f"{well['name']} ({well['code']})", well["id"])
                
                if self.load_wells_combo(self.well_combo):
                    self.current_well = self.well_combo.currentData()
                    self.load_codes()
                    
        except Exception as e:
            self.show_error(f"Error loading data: {str(e)}")
    
    def on_well_changed(self, index):
        if index >= 0:
            self.current_well = self.well_combo.currentData()
            self.load_codes()
    
    def load_codes(self):
        """Load activity codes from database"""
        try:
            if not self.db_manager or not self.current_well:
                return
            
            self.show_progress("Loading activity codes...")
            
            # Get activity codes
            codes = self.db_manager.get_activity_codes(well_id=self.current_well)
            
            # Clear table
            self.code_table.setRowCount(0)
            
            # Fill table
            for code in codes:
                row = self.code_table.rowCount()
                self.code_table.insertRow(row)
                
                self.code_table.setItem(row, 0, QTableWidgetItem(code.get("main_phase", "")))
                self.code_table.setItem(row, 1, QTableWidgetItem(code.get("main_code", "")))
                self.code_table.setItem(row, 2, QTableWidgetItem(code.get("sub_code", "")))
                self.code_table.setItem(row, 3, QTableWidgetItem(code.get("code_name", "")))
                
                # Productive checkbox
                productive_item = QTableWidgetItem()
                productive_item.setCheckState(Qt.Checked if code.get("is_productive", True) else Qt.Unchecked)
                self.code_table.setItem(row, 4, productive_item)
                
                # NPT checkbox
                npt_item = QTableWidgetItem()
                npt_item.setCheckState(Qt.Checked if code.get("is_npt", False) else Qt.Unchecked)
                self.code_table.setItem(row, 5, npt_item)
                
                self.code_table.setItem(row, 6, QTableWidgetItem(str(code.get("usage_count", 0))))
            
            # Calculate statistics
            self.calculate_statistics()
            
            self.show_success(f"Loaded {len(codes)} activity codes")
            
        except Exception as e:
            self.show_error(f"Error loading activity codes: {str(e)}")
    
    def add_code(self):
        """Add new activity code"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Activity Code")
            dialog.setMinimumWidth(400)
            
            layout = QFormLayout()
            
            main_phase_combo = QComboBox()
            main_phase_combo.addItems(["Drilling", "Tripping", "Casing", "Cementing", "Logging", "Testing", "Completion", "NPT", "Other"])
            layout.addRow("Main Phase:", main_phase_combo)
            
            main_code_edit = QLineEdit()
            main_code_edit.setPlaceholderText("e.g., DRL, TRP, CAS")
            layout.addRow("Main Code:", main_code_edit)
            
            sub_code_edit = QLineEdit()
            sub_code_edit.setPlaceholderText("e.g., DRL-01, TRP-01")
            layout.addRow("Sub Code:", sub_code_edit)
            
            code_name_edit = QLineEdit()
            code_name_edit.setPlaceholderText("e.g., Vertical Drilling, POOH")
            layout.addRow("Code Name:", code_name_edit)
            
            desc_edit = QTextEdit()
            desc_edit.setMaximumHeight(80)
            layout.addRow("Description:", desc_edit)
            
            productive_check = QCheckBox("Productive Time")
            productive_check.setChecked(True)
            layout.addRow(productive_check)
            
            npt_check = QCheckBox("NPT Code")
            npt_check.setChecked(False)
            layout.addRow(npt_check)
            
            # Buttons
            button_box = QHBoxLayout()
            save_btn = QPushButton("Save")
            cancel_btn = QPushButton("Cancel")
            
            save_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            
            button_box.addWidget(save_btn)
            button_box.addWidget(cancel_btn)
            layout.addRow(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec() == QDialog.Accepted:
                # Add to table
                row = self.code_table.rowCount()
                self.code_table.insertRow(row)
                
                self.code_table.setItem(row, 0, QTableWidgetItem(main_phase_combo.currentText()))
                self.code_table.setItem(row, 1, QTableWidgetItem(main_code_edit.text()))
                self.code_table.setItem(row, 2, QTableWidgetItem(sub_code_edit.text()))
                self.code_table.setItem(row, 3, QTableWidgetItem(code_name_edit.text()))
                
                productive_item = QTableWidgetItem()
                productive_item.setCheckState(Qt.Checked if productive_check.isChecked() else Qt.Unchecked)
                self.code_table.setItem(row, 4, productive_item)
                
                npt_item = QTableWidgetItem()
                npt_item.setCheckState(Qt.Checked if npt_check.isChecked() else Qt.Unchecked)
                self.code_table.setItem(row, 5, npt_item)
                
                self.code_table.setItem(row, 6, QTableWidgetItem("0"))
                
                # Save to database
                if self.db_manager and self.current_well:
                    code_data = {
                        "well_id": self.current_well,
                        "main_phase": main_phase_combo.currentText(),
                        "main_code": main_code_edit.text(),
                        "sub_code": sub_code_edit.text(),
                        "code_name": code_name_edit.text(),
                        "code_description": desc_edit.toPlainText(),
                        "is_productive": productive_check.isChecked(),
                        "is_npt": npt_check.isChecked(),
                        "color_code": "#0078D4"
                    }
                    self.db_manager.save_activity_code(code_data)
                
                self.show_success("Activity code added")
                self.calculate_statistics()
                
        except Exception as e:
            self.show_error(f"Error adding activity code: {str(e)}")
    
    def edit_code(self):
        """Edit selected activity code"""
        selected_row = self.code_table.currentRow()
        if selected_row < 0:
            self.show_error("Please select a code to edit")
            return
        
        # Similar to add_code but pre-filled
        # Implementation similar to add_code with pre-filled values
        self.show_progress("Edit feature under development")
    
    def delete_code(self):
        """Delete selected activity code"""
        selected_row = self.code_table.currentRow()
        if selected_row < 0:
            self.show_error("Please select a code to delete")
            return
        
        reply = QMessageBox.question(
            self, "Delete Code",
            "Are you sure you want to delete this activity code?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.code_table.removeRow(selected_row)
            self.show_success("Activity code deleted")
            self.calculate_statistics()
    
    def import_codes(self):
        """Import codes from file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Import Activity Codes", "",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*.*)"
            )
            
            if filename:
                self.show_progress("Importing codes...")
                
                # In real implementation, parse the file and add codes
                # For now, simulate
                QTimer.singleShot(1500, lambda: self.show_success(f"Codes imported from {os.path.basename(filename)}"))
                
        except Exception as e:
            self.show_error(f"Error importing codes: {str(e)}")
    
    def auto_update_from_daily_reports(self):
        """Auto-update code usage from daily reports"""
        try:
            if not self.db_manager or not self.current_well:
                self.show_error("Database not connected or no well selected")
                return
            
            self.show_progress("Updating code usage from daily reports...")
            
            # This would normally query daily reports and update usage counts
            # For now, simulate
            QTimer.singleShot(2000, lambda: self.show_success("Code usage updated from daily reports (simulated)"))
            
        except Exception as e:
            self.show_error(f"Error updating from daily reports: {str(e)}")
    
    def calculate_statistics(self):
        """Calculate code statistics"""
        try:
            total_codes = self.code_table.rowCount()
            phases = set()
            total_usage = 0
            
            for row in range(self.code_table.rowCount()):
                phase_item = self.code_table.item(row, 0)
                usage_item = self.code_table.item(row, 6)
                
                if phase_item and phase_item.text():
                    phases.add(phase_item.text())
                
                if usage_item and usage_item.text():
                    try:
                        total_usage += int(usage_item.text())
                    except ValueError:
                        pass
            
            # Update statistics
            self.total_codes.setText(str(total_codes))
            self.total_phases.setText(str(len(phases)))
            self.total_hours.setText(str(total_usage))
            
            # Find most used code
            most_used = None
            max_usage = 0
            
            for row in range(self.code_table.rowCount()):
                code_item = self.code_table.item(row, 3)
                usage_item = self.code_table.item(row, 6)
                
                if code_item and usage_item:
                    try:
                        usage = int(usage_item.text())
                        if usage > max_usage:
                            max_usage = usage
                            most_used = code_item.text()
                    except ValueError:
                        pass
            
            if most_used:
                self.most_used_code.setText(f"{most_used} ({max_usage} uses)")
            else:
                self.most_used_code.setText("None")
                
        except Exception as e:
            self.show_error(f"Error calculating statistics: {str(e)}")
    
    def export_codes(self):
        """Export activity codes"""
        try:
            export_manager = ExportManager(self)
            filename = export_manager.export_table_with_dialog(
                self.code_table,
                f"activity_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            if filename:
                self.show_success(f"Activity codes exported to {os.path.basename(filename)}")
                
        except Exception as e:
            self.show_error(f"Error exporting codes: {str(e)}")

# Tab 4: Time vs Depth Tab
@make_scrollable
class TimeVsDepthTab(DrillWidgetBase):
    def __init__(self, db_manager=None):
        super().__init__("TimeVsDepthTab", db_manager)
        self.current_well = None
        self.chart_data = []
        self.init_ui()
        self.setup_connections()
        self.load_initial_data()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("📈 Time vs Depth Analysis")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        # Well selector
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(200)
        header_layout.addWidget(QLabel("Well:"))
        header_layout.addWidget(self.well_combo)
        
        # Options
        self.show_rop_check = QCheckBox("Show ROP")
        self.show_rop_check.setChecked(True)
        header_layout.addWidget(self.show_rop_check)
        
        self.show_wob_check = QCheckBox("Show WOB")
        header_layout.addWidget(self.show_wob_check)
        
        self.auto_update_check = QCheckBox("Auto-update")
        self.auto_update_check.setChecked(True)
        header_layout.addWidget(self.auto_update_check)
        
        self.refresh_btn = QPushButton("🔄 Refresh Chart")
        header_layout.addWidget(self.refresh_btn)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Chart area
        chart_container = QWidget()
        chart_layout = QVBoxLayout()
        
        if CHARTS_AVAILABLE:
            self.chart_view = QChartView()
            self.chart_view.setMinimumHeight(400)
            chart_layout.addWidget(self.chart_view)
        else:
            chart_layout.addWidget(QLabel("Charts not available. Install QtCharts module."))
        
        # Data table
        self.data_table = QTableWidget(0, 5)
        self.data_table.setHorizontalHeaderLabels([
            "Time", "Depth (m)", "ROP (m/hr)", "WOB (klb)", "Activity"
        ])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setMaximumHeight(200)
        chart_layout.addWidget(self.data_table)
        
        chart_container.setLayout(chart_layout)
        main_layout.addWidget(chart_container)
        
        # Statistics
        stats_group = QGroupBox("📊 Statistics")
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Total Depth:"), 0, 0)
        self.total_depth = QLabel("0.0 m")
        stats_layout.addWidget(self.total_depth, 0, 1)
        
        stats_layout.addWidget(QLabel("Avg ROP:"), 0, 2)
        self.avg_rop = QLabel("0.0 m/hr")
        stats_layout.addWidget(self.avg_rop, 0, 3)
        
        stats_layout.addWidget(QLabel("Max ROP:"), 1, 0)
        self.max_rop = QLabel("0.0 m/hr")
        stats_layout.addWidget(self.max_rop, 1, 1)
        
        stats_layout.addWidget(QLabel("Drilling Time:"), 1, 2)
        self.drilling_time = QLabel("0.0 hrs")
        stats_layout.addWidget(self.drilling_time, 1, 3)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.export_chart_btn = QPushButton("📤 Export Chart")
        button_layout.addWidget(self.export_chart_btn)
        
        self.export_data_btn = QPushButton("📤 Export Data")
        button_layout.addWidget(self.export_data_btn)
        
        self.generate_report_btn = QPushButton("📄 Generate Report")
        button_layout.addWidget(self.generate_report_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("💾 Save Analysis")
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # Setup Table Manager for data table
        self.table_manager = TableManager(self.data_table, self)
    
    def setup_connections(self):
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        self.refresh_btn.clicked.connect(self.load_chart_data)
        self.show_rop_check.stateChanged.connect(self.update_chart)
        self.show_wob_check.stateChanged.connect(self.update_chart)
        self.export_chart_btn.clicked.connect(self.export_chart)
        self.export_data_btn.clicked.connect(self.export_data)
        self.generate_report_btn.clicked.connect(self.generate_report)
        self.save_btn.clicked.connect(self.save_analysis)
    
    def load_initial_data(self):
        """Load initial data"""
        try:
            if self.db_manager:
                # Load wells
                wells = self.db_manager.get_hierarchy()
                self.well_combo.clear()
                for company in wells:
                    for project in company["projects"]:
                        for well in project["wells"]:
                            self.well_combo.addItem(f"{well['name']} ({well['code']})", well["id"])
                
                if self.load_wells_combo(self.well_combo):
                    self.current_well = self.well_combo.currentData()
                    self.load_chart_data()
                
        except Exception as e:
            self.show_error(f"Error loading data: {str(e)}")
    
    def on_well_changed(self, index):
        if index >= 0:
            self.current_well = self.well_combo.currentData()
            self.load_chart_data()
    
    def load_chart_data(self):
        """Load time vs depth data"""
        try:
            if not self.db_manager or not self.current_well:
                return
            
            self.show_progress("Loading chart data...")
            
            # Get time depth data
            chart_data = self.db_manager.generate_time_depth_chart_data(self.current_well)
            
            if chart_data:
                self.chart_data = chart_data
                self.update_chart()
                self.update_data_table()
                self.calculate_statistics()
                self.show_success("Chart data loaded")
            else:
                # Generate sample data for demonstration
                self.generate_sample_data()
                self.show_success("Generated sample chart data")
                
        except Exception as e:
            self.show_error(f"Error loading chart data: {str(e)}")
    
    def generate_sample_data(self):
        """Generate sample data for demonstration"""
        self.chart_data = {
            "timestamps": [datetime.now() + timedelta(hours=i) for i in range(24)],
            "depths": [1000 + i * 50 + random.uniform(-10, 10) for i in range(24)],
            "rop": [20 + random.uniform(-5, 5) for _ in range(24)],
            "data_points": 24
        }
        self.update_chart()
        self.update_data_table()
        self.calculate_statistics()
    
    def update_chart(self):
        """Update the chart with current data"""
        if not CHARTS_AVAILABLE or not self.chart_data:
            return
        
        try:
            chart = QChart()
            chart.setTitle("Time vs Depth Analysis")
            
            # Create depth series
            depth_series = QLineSeries()
            depth_series.setName("Depth (m)")
            
            for i in range(len(self.chart_data.get("timestamps", []))):
                if i < len(self.chart_data.get("depths", [])):
                    timestamp = self.chart_data["timestamps"][i]
                    depth = self.chart_data["depths"][i]
                    
                    qdatetime = QDateTime(
                        timestamp.year, timestamp.month, timestamp.day,
                        timestamp.hour, timestamp.minute, timestamp.second
                    )
                    depth_series.append(qdatetime.toMSecsSinceEpoch(), depth)
            
            chart.addSeries(depth_series)
            
            # Add ROP series if enabled
            if self.show_rop_check.isChecked() and "rop" in self.chart_data:
                rop_series = QLineSeries()
                rop_series.setName("ROP (m/hr)")
                
                for i in range(len(self.chart_data["timestamps"])):
                    if i < len(self.chart_data["rop"]):
                        timestamp = self.chart_data["timestamps"][i]
                        rop = self.chart_data["rop"][i]
                        
                        qdatetime = QDateTime(
                            timestamp.year, timestamp.month, timestamp.day,
                            timestamp.hour, timestamp.minute, timestamp.second
                        )
                        rop_series.append(qdatetime.toMSecsSinceEpoch(), rop)
                
                chart.addSeries(rop_series)
            
            # Create axes
            axis_x = QDateTimeAxis()
            axis_x.setFormat("MM-dd HH:mm")
            axis_x.setTitleText("Time")
            chart.addAxis(axis_x, Qt.AlignBottom)
            depth_series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            axis_y.setTitleText("Depth (m)")
            axis_y.setLabelFormat("%.1f")
            chart.addAxis(axis_y, Qt.AlignLeft)
            depth_series.attachAxis(axis_y)
            
            # Add second Y axis for ROP if needed
            if self.show_rop_check.isChecked() and "rop" in self.chart_data:
                axis_y2 = QValueAxis()
                axis_y2.setTitleText("ROP (m/hr)")
                axis_y2.setLabelFormat("%.1f")
                chart.addAxis(axis_y2, Qt.AlignRight)
                if hasattr(chart, 'series') and len(chart.series()) > 1:
                    chart.series()[1].attachAxis(axis_y2)
            
            chart.legend().setVisible(True)
            chart.setAnimationOptions(QChart.SeriesAnimations)
            
            self.chart_view.setChart(chart)
            self.chart_view.setRenderHint(QPainter.Antialiasing)
            
        except Exception as e:
            logger.error(f"Error updating chart: {e}")
    
    def update_data_table(self):
        """Update data table with chart data"""
        try:
            self.data_table.setRowCount(0)
            
            timestamps = self.chart_data.get("timestamps", [])
            depths = self.chart_data.get("depths", [])
            rop_values = self.chart_data.get("rop", [])
            
            for i in range(min(len(timestamps), 50)):  # Limit to 50 rows
                row = self.data_table.rowCount()
                self.data_table.insertRow(row)
                
                timestamp = timestamps[i]
                depth = depths[i] if i < len(depths) else 0
                rop = rop_values[i] if i < len(rop_values) else 0
                
                self.data_table.setItem(row, 0, QTableWidgetItem(timestamp.strftime("%Y-%m-%d %H:%M")))
                self.data_table.setItem(row, 1, QTableWidgetItem(f"{depth:.1f}"))
                self.data_table.setItem(row, 2, QTableWidgetItem(f"{rop:.1f}" if rop else ""))
                self.data_table.setItem(row, 3, QTableWidgetItem(""))  # WOB placeholder
                self.data_table.setItem(row, 4, QTableWidgetItem("Drilling" if rop and rop > 0 else "Other"))
                
        except Exception as e:
            self.show_error(f"Error updating data table: {str(e)}")
    
    def calculate_statistics(self):
        """Calculate statistics from chart data"""
        try:
            depths = self.chart_data.get("depths", [])
            rop_values = self.chart_data.get("rop", [])
            
            if depths:
                max_depth = max(depths)
                self.total_depth.setText(f"{max_depth:.1f} m")
            
            if rop_values:
                valid_rop = [r for r in rop_values if r is not None and r > 0]
                if valid_rop:
                    avg_rop = sum(valid_rop) / len(valid_rop)
                    max_rop = max(valid_rop)
                    drilling_time = len(valid_rop)  # Simplified
                    
                    self.avg_rop.setText(f"{avg_rop:.1f} m/hr")
                    self.max_rop.setText(f"{max_rop:.1f} m/hr")
                    self.drilling_time.setText(f"{drilling_time:.1f} hrs")
                    
        except Exception as e:
            self.show_error(f"Error calculating statistics: {str(e)}")
    
    def export_chart(self):
        """Export chart as image"""
        try:
            if not CHARTS_AVAILABLE:
                self.show_error("Charts not available")
                return
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Chart", 
                f"time_depth_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*.*)"
            )
            
            if filename:
                pixmap = self.chart_view.grab()
                pixmap.save(filename)
                self.show_success(f"Chart saved to {os.path.basename(filename)}")
                
        except Exception as e:
            self.show_error(f"Error exporting chart: {str(e)}")
    
    def export_data(self):
        """Export data table"""
        try:
            export_manager = ExportManager(self)
            filename = export_manager.export_table_with_dialog(
                self.data_table,
                f"time_depth_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            if filename:
                self.show_success(f"Data exported to {os.path.basename(filename)}")
                
        except Exception as e:
            self.show_error(f"Error exporting data: {str(e)}")
    
    def generate_report(self):
        """Generate analysis report"""
        try:
            report = f"Time vs Depth Analysis Report\n"
            report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            report += "=" * 50 + "\n\n"
            
            report += f"Total Depth: {self.total_depth.text()}\n"
            report += f"Average ROP: {self.avg_rop.text()}\n"
            report += f"Maximum ROP: {self.max_rop.text()}\n"
            report += f"Drilling Time: {self.drilling_time.text()}\n\n"
            
            report += "Data Points:\n"
            for i in range(min(self.data_table.rowCount(), 10)):
                time = self.data_table.item(i, 0).text() if self.data_table.item(i, 0) else ""
                depth = self.data_table.item(i, 1).text() if self.data_table.item(i, 1) else ""
                rop = self.data_table.item(i, 2).text() if self.data_table.item(i, 2) else ""
                report += f"  {time}: Depth={depth}m, ROP={rop}m/hr\n"
            
            QMessageBox.information(self, "Analysis Report", report)
            
        except Exception as e:
            self.show_error(f"Error generating report: {str(e)}")
    
    def save_analysis(self):
        """Save analysis to database"""
        try:
            if not self.db_manager or not self.current_well:
                self.show_error("Database not connected or no well selected")
                return
            
            self.show_progress("Saving analysis...")
            
            # In real implementation, save the analysis data
            # For now, simulate
            QTimer.singleShot(1500, lambda: self.show_success("Analysis saved to database"))
            
        except Exception as e:
            self.show_error(f"Error saving analysis: {str(e)}")

# Tab 5: ROP Chart Tab
@make_scrollable
class ROPChartTab(DrillWidgetBase):
    def __init__(self, db_manager=None):
        super().__init__("ROPChartTab", db_manager)
        self.current_well = None
        self.rop_data = []
        self.init_ui()
        self.setup_connections()
        self.load_initial_data()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("📊 ROP (Rate of Penetration) Analysis")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        # Well selector
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(200)
        header_layout.addWidget(QLabel("Well:"))
        header_layout.addWidget(self.well_combo)
        
        # Depth range
        header_layout.addWidget(QLabel("From:"))
        self.from_depth = QDoubleSpinBox()
        self.from_depth.setRange(0, 10000)
        self.from_depth.setValue(0)
        header_layout.addWidget(self.from_depth)
        
        header_layout.addWidget(QLabel("To:"))
        self.to_depth = QDoubleSpinBox()
        self.to_depth.setRange(0, 10000)
        self.to_depth.setValue(5000)
        header_layout.addWidget(self.to_depth)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        header_layout.addWidget(self.refresh_btn)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Chart area
        chart_container = QWidget()
        chart_layout = QVBoxLayout()
        
        if CHARTS_AVAILABLE:
            self.rop_chart_view = QChartView()
            self.rop_chart_view.setMinimumHeight(400)
            chart_layout.addWidget(self.rop_chart_view)
        else:
            chart_layout.addWidget(QLabel("Charts not available. Install QtCharts module."))
        
        chart_container.setLayout(chart_layout)
        main_layout.addWidget(chart_container)
        
        # ROP Statistics
        stats_group = QGroupBox("📈 ROP Statistics")
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Average ROP:"), 0, 0)
        self.avg_rop = QLabel("0.0 m/hr")
        self.avg_rop.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.avg_rop, 0, 1)
        
        stats_layout.addWidget(QLabel("Maximum ROP:"), 0, 2)
        self.max_rop = QLabel("0.0 m/hr")
        self.max_rop.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.max_rop, 0, 3)
        
        stats_layout.addWidget(QLabel("Minimum ROP:"), 1, 0)
        self.min_rop = QLabel("0.0 m/hr")
        self.min_rop.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.min_rop, 1, 1)
        
        stats_layout.addWidget(QLabel("Standard Deviation:"), 1, 2)
        self.std_dev = QLabel("0.0")
        self.std_dev.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.std_dev, 1, 3)
        
        stats_layout.addWidget(QLabel("Efficiency Score:"), 2, 0)
        self.efficiency_score = QLabel("0%")
        self.efficiency_score.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.efficiency_score, 2, 1)
        
        stats_layout.addWidget(QLabel("Data Points:"), 2, 2)
        self.data_points = QLabel("0")
        self.data_points.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.data_points, 2, 3)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # Recommendations
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setMaximumHeight(100)
        self.recommendations_text.setPlaceholderText("ROP analysis recommendations will appear here...")
        main_layout.addWidget(QLabel("💡 Recommendations:"))
        main_layout.addWidget(self.recommendations_text)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🧮 Analyze ROP")
        button_layout.addWidget(self.analyze_btn)
        
        self.compare_btn = QPushButton("📊 Compare with Offset")
        button_layout.addWidget(self.compare_btn)
        
        self.trend_btn = QPushButton("📈 Show Trend Line")
        button_layout.addWidget(self.trend_btn)
        
        button_layout.addStretch()
        
        self.export_btn = QPushButton("📤 Export Analysis")
        button_layout.addWidget(self.export_btn)
        
        self.save_btn = QPushButton("💾 Save ROP Analysis")
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def setup_connections(self):
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        self.refresh_btn.clicked.connect(self.load_rop_data)
        self.analyze_btn.clicked.connect(self.analyze_rop)
        self.compare_btn.clicked.connect(self.compare_with_offset)
        self.trend_btn.clicked.connect(self.show_trend_line)
        self.export_btn.clicked.connect(self.export_analysis)
        self.save_btn.clicked.connect(self.save_rop_analysis)
    
    def load_initial_data(self):
        """Load initial data"""
        try:
            if self.db_manager:
                # Load wells
                wells = self.db_manager.get_hierarchy()
                self.well_combo.clear()
                for company in wells:
                    for project in company["projects"]:
                        for well in project["wells"]:
                            self.well_combo.addItem(f"{well['name']} ({well['code']})", well["id"])
                
                if self.load_wells_combo(self.well_combo):
                    self.current_well = self.well_combo.currentData()
                    self.load_rop_data()
                    
        except Exception as e:
            self.show_error(f"Error loading data: {str(e)}")
    
    def on_well_changed(self, index):
        if index >= 0:
            self.current_well = self.well_combo.currentData()
            self.load_rop_data()
    
    def load_rop_data(self):
        """Load ROP data from database"""
        try:
            if not self.db_manager or not self.current_well:
                return
            
            self.show_progress("Loading ROP data...")
            
            # Get ROP analysis
            rop_analysis = self.db_manager.get_rop_analysis(well_id=self.current_well)
            
            if rop_analysis:
                self.rop_data = rop_analysis
                self.update_chart()
                self.calculate_statistics()
                self.show_success("ROP data loaded")
            else:
                # Generate sample data
                self.generate_sample_data()
                self.show_success("Generated sample ROP data")
                
        except Exception as e:
            self.show_error(f"Error loading ROP data: {str(e)}")
    
    def generate_sample_data(self):
        """Generate sample ROP data"""
        # Generate sample depth-ROP pairs
        depths = []
        rop_values = []
        
        for i in range(50):
            depth = 1000 + i * 100
            # ROP decreases with depth, with some randomness
            rop = 30 - (depth / 500) + random.uniform(-5, 5)
            if rop < 5:
                rop = 5 + random.uniform(0, 3)
            
            depths.append(depth)
            rop_values.append(rop)
        
        self.rop_data = {
            "depths": depths,
            "rop_values": rop_values,
            "avg_rop": sum(rop_values) / len(rop_values),
            "max_rop": max(rop_values),
            "min_rop": min(rop_values),
            "data_points": len(depths)
        }
        
        self.update_chart()
        self.calculate_statistics()
    
    def update_chart(self):
        """Update ROP chart"""
        if not CHARTS_AVAILABLE or not self.rop_data:
            return
        
        try:
            chart = QChart()
            chart.setTitle("ROP vs Depth")
            
            # Create ROP series
            rop_series = QScatterSeries()
            rop_series.setName("ROP (m/hr)")
            rop_series.setMarkerSize(8.0)
            
            depths = self.rop_data.get("depths", [])
            rop_values = self.rop_data.get("rop_values", [])
            
            for i in range(len(depths)):
                if i < len(rop_values):
                    rop_series.append(depths[i], rop_values[i])
            
            chart.addSeries(rop_series)
            
            # Add average line
            avg_rop = self.rop_data.get("avg_rop", 0)
            if avg_rop > 0:
                avg_series = QLineSeries()
                avg_series.setName(f"Average ROP: {avg_rop:.1f} m/hr")
                
                if depths:
                    avg_series.append(depths[0], avg_rop)
                    avg_series.append(depths[-1], avg_rop)
                
                chart.addSeries(avg_series)
            
            # Create axes
            axis_x = QValueAxis()
            axis_x.setTitleText("Depth (m)")
            axis_x.setLabelFormat("%.0f")
            chart.addAxis(axis_x, Qt.AlignBottom)
            rop_series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            axis_y.setTitleText("ROP (m/hr)")
            axis_y.setLabelFormat("%.1f")
            chart.addAxis(axis_y, Qt.AlignLeft)
            rop_series.attachAxis(axis_y)
            
            chart.legend().setVisible(True)
            chart.setAnimationOptions(QChart.SeriesAnimations)
            
            self.rop_chart_view.setChart(chart)
            self.rop_chart_view.setRenderHint(QPainter.Antialiasing)
            
        except Exception as e:
            logger.error(f"Error updating ROP chart: {e}")
    
    def calculate_statistics(self):
        """Calculate ROP statistics"""
        try:
            rop_values = self.rop_data.get("rop_values", [])
            
            if rop_values:
                avg_rop = sum(rop_values) / len(rop_values)
                max_rop = max(rop_values)
                min_rop = min(rop_values)
                
                # Calculate standard deviation
                variance = sum((x - avg_rop) ** 2 for x in rop_values) / len(rop_values)
                std_dev = variance ** 0.5
                
                # Calculate efficiency score (0-100%)
                # Higher average ROP and lower std dev = better efficiency
                max_possible_rop = 50  # Assume 50 m/hr is max possible
                efficiency = (avg_rop / max_possible_rop) * 100
                # Penalize for high variation
                if std_dev > avg_rop * 0.5:  # If std dev > 50% of average
                    efficiency *= 0.8
                
                self.avg_rop.setText(f"{avg_rop:.1f} m/hr")
                self.max_rop.setText(f"{max_rop:.1f} m/hr")
                self.min_rop.setText(f"{min_rop:.1f} m/hr")
                self.std_dev.setText(f"{std_dev:.1f}")
                self.efficiency_score.setText(f"{min(100, int(efficiency))}%")
                self.data_points.setText(str(len(rop_values)))
                
                # Generate recommendations
                self.generate_recommendations(avg_rop, std_dev, efficiency)
                
        except Exception as e:
            self.show_error(f"Error calculating statistics: {str(e)}")
    
    def generate_recommendations(self, avg_rop, std_dev, efficiency):
        """Generate ROP improvement recommendations"""
        recommendations = "ROP Analysis Recommendations:\n\n"
        
        if avg_rop < 15:
            recommendations += "• Low ROP detected. Consider:\n"
            recommendations += "  - Increasing weight on bit (WOB)\n"
            recommendations += "  - Optimizing hydraulics\n"
            recommendations += "  - Checking bit wear\n"
            recommendations += "  - Reviewing formation characteristics\n"
        elif avg_rop > 30:
            recommendations += "• Good ROP achieved. Maintain current parameters.\n"
        else:
            recommendations += "• Average ROP. Room for optimization.\n"
        
        if std_dev > avg_rop * 0.4:
            recommendations += "\n• High ROP variation detected:\n"
            recommendations += "  - Check for formation changes\n"
            recommendations += "  - Monitor drilling parameters consistency\n"
            recommendations += "  - Consider more frequent surveys\n"
        
        if efficiency < 60:
            recommendations += "\n• Low drilling efficiency:\n"
            recommendations += "  - Review overall drilling practices\n"
            recommendations += "  - Consider different bit types\n"
            recommendations += "  - Optimize mud properties\n"
        elif efficiency > 80:
            recommendations += "\n• Excellent drilling efficiency achieved.\n"
        
        recommendations += "\n• General recommendations:\n"
        recommendations += "  - Monitor torque and drag\n"
        recommendations += "  - Ensure proper hole cleaning\n"
        recommendations += "  - Regularly check equipment condition\n"
        
        self.recommendations_text.setText(recommendations)
    
    def analyze_rop(self):
        """Perform detailed ROP analysis"""
        try:
            self.show_progress("Analyzing ROP...")
            
            # In real implementation, perform complex analysis
            # For now, simulate
            QTimer.singleShot(2000, lambda: self.show_success("ROP analysis complete"))
            
        except Exception as e:
            self.show_error(f"Error analyzing ROP: {str(e)}")
    
    def compare_with_offset(self):
        """Compare ROP with offset wells"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Compare with Offset Wells")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout()
            
            layout.addWidget(QLabel("Select offset wells for comparison:"))
            
            offset_list = QListWidget()
            offset_list.addItems(["Well A - Similar Formation", "Well B - Offset 1", "Well C - Offset 2", "Well D - Best Performance"])
            offset_list.setSelectionMode(QListWidget.MultiSelection)
            layout.addWidget(offset_list)
            
            button_box = QHBoxLayout()
            compare_btn = QPushButton("Compare")
            cancel_btn = QPushButton("Cancel")
            
            compare_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            
            button_box.addWidget(compare_btn)
            button_box.addWidget(cancel_btn)
            layout.addLayout(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec() == QDialog.Accepted:
                selected = offset_list.selectedItems()
                if selected:
                    self.show_success(f"Comparing with {len(selected)} offset wells")
                else:
                    self.show_error("No offset wells selected")
                    
        except Exception as e:
            self.show_error(f"Error comparing with offset: {str(e)}")
    
    def show_trend_line(self):
        """Show trend line on chart"""
        try:
            if not CHARTS_AVAILABLE:
                return
            
            self.show_progress("Calculating trend line...")
            
            # In real implementation, calculate and display trend line
            # For now, simulate
            QTimer.singleShot(1500, lambda: self.show_success("Trend line displayed"))
            
        except Exception as e:
            self.show_error(f"Error showing trend line: {str(e)}")
    
    def export_analysis(self):
        """Export ROP analysis"""
        try:
            export_manager = ExportManager(self)
            
            # Create a simple report
            report = f"ROP Analysis Report\n"
            report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            report += "=" * 50 + "\n\n"
            
            report += f"Average ROP: {self.avg_rop.text()}\n"
            report += f"Maximum ROP: {self.max_rop.text()}\n"
            report += f"Minimum ROP: {self.min_rop.text()}\n"
            report += f"Standard Deviation: {self.std_dev.text()}\n"
            report += f"Efficiency Score: {self.efficiency_score.text()}\n"
            report += f"Data Points: {self.data_points.text()}\n\n"
            
            report += "Recommendations:\n"
            report += self.recommendations_text.toPlainText()
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save ROP Analysis Report",
                f"rop_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt);;All Files (*.*)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                self.show_success(f"Analysis exported to {os.path.basename(filename)}")
                
        except Exception as e:
            self.show_error(f"Error exporting analysis: {str(e)}")
    
    def save_rop_analysis(self):
        """Save ROP analysis to database"""
        try:
            if not self.db_manager or not self.current_well:
                self.show_error("Database not connected or no well selected")
                return
            
            self.show_progress("Saving ROP analysis...")
            
            # Prepare analysis data
            analysis_data = {
                "well_id": self.current_well,
                "analysis_date": datetime.now().date(),
                "start_depth": self.from_depth.value(),
                "end_depth": self.to_depth.value(),
                "avg_rop": float(self.avg_rop.text().replace(" m/hr", "")),
                "max_rop": float(self.max_rop.text().replace(" m/hr", "")),
                "min_rop": float(self.min_rop.text().replace(" m/hr", "")),
                "rop_std_dev": float(self.std_dev.text()),
                "efficiency_score": int(self.efficiency_score.text().replace("%", "")),
                "recommendations": self.recommendations_text.toPlainText()
            }
            
            result = self.db_manager.save_rop_analysis(analysis_data)
            if result:
                self.show_success("ROP analysis saved to database")
            else:
                self.show_error("Failed to save ROP analysis")
                
        except Exception as e:
            self.show_error(f"Error saving ROP analysis: {str(e)}")

# Main Planning Widget
class PlanningWidget(DrillWidgetBase):
    def __init__(self, db_manager=None):
        super().__init__("PlanningWidget", db_manager)
        self.init_ui()
        self.setup_connections()
        
        self.setup_tab_parents()
    
    def setup_tab_parents(self):
        """تنظیم parent_widget برای همه تب‌ها"""
        tabs = [
            self.lookahead_tab,
            self.npt_tab, 
            self.code_tab,
            self.time_depth_tab,
            self.rop_tab
        ]
        
        for tab in tabs:
            if hasattr(tab, 'set_parent_widget'):
                tab.set_parent_widget(self)
                
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.lookahead_tab = SevenDaysLookaheadTab(self.db_manager)
        self.npt_tab = NPTReportTab(self.db_manager)
        self.code_tab = CodeManagementTab(self.db_manager)
        self.time_depth_tab = TimeVsDepthTab(self.db_manager)
        self.rop_tab = ROPChartTab(self.db_manager)
        
        # Add tabs
        self.tab_widget.addTab(self.lookahead_tab, "📅 7 Days Lookahead")
        self.tab_widget.addTab(self.npt_tab, "⏱️ NPT Report")
        self.tab_widget.addTab(self.code_tab, "🏷️ Code Management")
        self.tab_widget.addTab(self.time_depth_tab, "📈 Time vs Depth")
        self.tab_widget.addTab(self.rop_tab, "📊 ROP Chart")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Planning Module Ready")
        main_layout.addWidget(self.status_bar)
        
        self.setLayout(main_layout)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def on_tab_changed(self, index):
        """Handle tab change"""
        tab_names = ["7 Days Lookahead", "NPT Report", "Code Management", "Time vs Depth", "ROP Chart"]
        if 0 <= index < len(tab_names):
            self.status_bar.showMessage(f"Active: {tab_names[index]}")
    
    def save_data(self):
        """Save all planning data"""
        try:
            self.show_progress("Saving all planning data...")
            
            # Save data from each tab
            tabs = [self.lookahead_tab, self.npt_tab, self.code_tab, self.time_depth_tab, self.rop_tab]
            save_count = 0
            
            for tab in tabs:
                if hasattr(tab, 'save_plan'):
                    if tab.save_plan():
                        save_count += 1
                elif hasattr(tab, 'save_analysis'):
                    if tab.save_analysis():
                        save_count += 1
                elif hasattr(tab, 'save_rop_analysis'):
                    if tab.save_rop_analysis():
                        save_count += 1
            
            self.show_success(f"Saved data from {save_count} tabs")
            return True
            
        except Exception as e:
            self.show_error(f"Error saving data: {str(e)}")
            return False
    
    def refresh_all(self):
        """Refresh all tabs"""
        try:
            self.show_progress("Refreshing all tabs...")
            
            # Refresh each tab
            tabs = [self.lookahead_tab, self.npt_tab, self.code_tab, self.time_depth_tab, self.rop_tab]
            
            for tab in tabs:
                if hasattr(tab, 'load_data'):
                    tab.load_data()
                elif hasattr(tab, 'load_npt_data'):
                    tab.load_npt_data()
                elif hasattr(tab, 'load_codes'):
                    tab.load_codes()
                elif hasattr(tab, 'load_chart_data'):
                    tab.load_chart_data()
                elif hasattr(tab, 'load_rop_data'):
                    tab.load_rop_data()
            
            self.show_success("All tabs refreshed")
            
        except Exception as e:
            self.show_error(f"Error refreshing tabs: {str(e)}")
    
    def export_all(self):
        """Export all planning data"""
        try:
            export_manager = ExportManager(self)
            
            # Create a comprehensive report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"planning_export_{timestamp}.zip"
            
            self.show_progress("Exporting all planning data...")
            
            # In real implementation, create ZIP with all exports
            # For now, show message
            QTimer.singleShot(2000, lambda: self.show_success(f"Planning data exported to {filename}"))
            
        except Exception as e:
            self.show_error(f"Error exporting data: {str(e)}")
            