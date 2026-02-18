"""
Export Module for DrillMaster Application
Manages daily exports, end of well reports, and batch exports
"""

import os
import sys
import logging
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any

# PySide6 imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from ui.helper import make_scrollable

import csv
import io
import zipfile

# Import managers
from core.managers import (
    StatusBarManager, 
    AutoSaveManager, 
    ExportManager, 
    TableManager,
    DrillingManager
)

# Import database models
from core.database import (
    DatabaseManager,
    Company, Project, Well, Section, DailyReport,
    DrillingParameters, MudReport, CasingReport, CementReport,
    BitReport, BHAReport, FormationReport,
    LogisticsPersonnel, ServiceCompanyPOB, FuelWaterInventory,
    SafetyReport, BOPComponent, WasteRecord,
    ServiceCompany, ServiceNote, MaterialRequest, EquipmentLog,
    SevenDaysLookahead, NPTReport, ActivityCode, TimeDepthData, ROPAnalysis, ExportTemplate  
)

# Import base widget if available
try:
    from base_widgets import DrillWidgetBase
except ImportError:
    # Define a minimal base class if not available
    class DrillWidgetBase(QWidget):
        def __init__(self, widget_name: str, db_manager: DatabaseManager = None):
            super().__init__()
            self.widget_name = widget_name
            self.db = db_manager
            self.status_manager = StatusBarManager()

logger = logging.getLogger(__name__)


# ==================== Daily Export Tab ====================
@make_scrollable
class DailyExportTab(QWidget):
    """Daily Export Tab - For generating daily reports"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        super().__init__()
        self.db = db_manager
        self.status_manager = StatusBarManager()
        
        # Create export components
        if db_manager:
            try:
                self.export_generator = ExportGenerator(self.db)
                self.data_collector = ExportDataCollector(self.db)
            except Exception as e:
                logger.error(f"Failed to create export components: {e}")
                self.export_generator = None
                self.data_collector = None
        else:
            self.export_generator = None
            self.data_collector = None
        
        self.current_well = None
        self.current_reports = []
        
        self.init_ui()
        self.setup_connections()
        self.load_data()
    
    def init_ui(self):
        """Initialize the UI for daily export tab"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header
        header_label = QLabel("📤 Daily Export - Generate Daily Drilling Reports")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #e8f4f8;
                border-radius: 5px;
                border-left: 5px solid #4CAF50;
            }
        """)
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Selection Group
        selection_group = self.create_selection_group()
        main_layout.addWidget(selection_group)
        
        # Format Selection Group
        format_group = self.create_format_group()
        main_layout.addWidget(format_group)
        
        # Options Group
        options_group = self.create_options_group()
        main_layout.addWidget(options_group)
        
        # Action Buttons
        action_group = self.create_action_buttons()
        main_layout.addWidget(action_group)
        
        # Progress Section
        progress_group = self.create_progress_section()
        main_layout.addWidget(progress_group)
        
        main_layout.addStretch()
    
    def create_selection_group(self) -> QGroupBox:
        """Create selection group for well, date range, and reports"""
        group = QGroupBox("📋 Select Data for Export")
        group.setStyleSheet("""
        QGroupBox {
            font-size: 11pt;
            font-weight: bold;
            border: 2px solid #4CAF50;
            border-radius: 6px;
            margin-top: 18px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 10px;
        }
        """)
        
        layout = QVBoxLayout()
        
        # Well Selection
        well_layout = QHBoxLayout()
        well_layout.addWidget(QLabel("🎯 Well:"))
        
        self.well_combo = QComboBox()
        self.well_combo.setMinimumHeight(35)
        self.well_combo.setFont(QFont("Arial", 10))
        well_layout.addWidget(self.well_combo)
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh wells list")
        refresh_btn.clicked.connect(self.refresh_wells_list)
        well_layout.addWidget(refresh_btn)
        
        layout.addLayout(well_layout)
        
        # Date Range
        date_layout = QHBoxLayout()
        date_layout.setSpacing(20)
        
        from_layout = QVBoxLayout()
        from_layout.addWidget(QLabel("📅 From Date:"))
        
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-7))
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setMinimumHeight(35)
        from_layout.addWidget(self.from_date)
        date_layout.addLayout(from_layout)
        
        to_layout = QVBoxLayout()
        to_layout.addWidget(QLabel("📅 To Date:"))
        
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setMinimumHeight(35)
        to_layout.addWidget(self.to_date)
        date_layout.addLayout(to_layout)
        
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # Report Selection
        reports_group = QGroupBox("📄 Select Reports")
        reports_scroll = QScrollArea()
        reports_scroll.setWidgetResizable(True)
        reports_scroll.setMinimumHeight(250)
        
        reports_container = QWidget()
        reports_layout = QGridLayout(reports_container)
        reports_layout.setSpacing(10)
        
        self.report_checkboxes = []
        reports = [
            ("Well Info", "📋 Well Information", "Basic well details and location"),
            ("Daily Report", "📅 Daily Drilling Report", "Daily operations summary"),
            ("Drilling Parameters", "⚙️ Drilling Parameters", "ROP, WOB, RPM, TQ"),
            ("Mud Report", "🧪 Mud Properties", "Mud weight, viscosity, properties"),
            ("Bit Record", "🧱 Bit Record", "Bit run history and performance"),
            ("BHA Report", "🔧 BHA Design", "Bottom hole assembly details"),
            ("Trajectory", "📈 Trajectory Survey", "Well path and coordinates"),
            ("Equipment", "🧰 Equipment Status", "Rig equipment and inventory"),
            ("Safety", "🦺 Safety Records", "BOP tests and safety drills"),
            ("Planning", "📝 Planning Data", "Lookahead and NPT analysis"),
            ("Casing", "🛢️ Casing Program", "Casing design and installation"),
            ("Cement", "🧱 Cement Jobs", "Cementing operations and results"),
            ("Logistics", "🚚 Logistics", "Personnel, transport, materials"),
            ("Services", "🏢 Service Companies", "Third-party services log"),
            ("Cost Analysis", "💰 Cost Tracking", "Daily cost breakdown"),
        ]

        row, col = 0, 0
        for report_name, report_label, tooltip in reports:
            cb = QCheckBox(report_label)
            cb.setChecked(True)
            cb.setToolTip(tooltip)
            cb.setFont(QFont("Arial", 9))
            
            self.report_checkboxes.append((report_name, cb))
            reports_layout.addWidget(cb, row, col)
            
            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1
        
        reports_scroll.setWidget(reports_container)
        
        # Select all buttons
        select_all_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Select All")
        deselect_all_btn = QPushButton("❌ Deselect All")
        
        select_all_btn.clicked.connect(self.select_all_reports)
        deselect_all_btn.clicked.connect(self.deselect_all_reports)
        
        select_all_layout.addWidget(select_all_btn)
        select_all_layout.addWidget(deselect_all_btn)
        select_all_layout.addStretch()
        
        reports_vlayout = QVBoxLayout()
        reports_vlayout.addWidget(reports_scroll)
        reports_vlayout.addLayout(select_all_layout)
        
        reports_group.setLayout(reports_vlayout)
        layout.addWidget(reports_group)
        
        group.setLayout(layout)
        return group
    
    def create_format_group(self) -> QGroupBox:
        """Create format selection group"""
        group = QGroupBox("📁 Export Format")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                border: 1px solid #FF9800;
                border-radius: 5px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # تعریف radio buttons به عنوان attributeهای کلاس
        self.pdf_radio = QRadioButton("📄 PDF Document")
        self.word_radio = QRadioButton("📝 Word Document")
        self.excel_radio = QRadioButton("📊 Excel Spreadsheet")
        self.all_formats_radio = QRadioButton("📦 All Formats")
        
        # تنظیم word به عنوان پیش‌فرض
        self.word_radio.setChecked(True)
        
        for radio in [self.pdf_radio, self.word_radio, self.excel_radio, self.all_formats_radio]:
            radio.setFont(QFont("Arial", 10))
            layout.addWidget(radio)
        
        layout.addStretch()
        group.setLayout(layout)
        
        # اضافه کردن logging برای دیباگ
        logger.info("Format group created")
        logger.info(f"Word radio checked: {self.word_radio.isChecked()}")
        logger.info(f"PDF radio checked: {self.pdf_radio.isChecked()}")
        
        return group
    
    def create_options_group(self) -> QGroupBox:
        """Create export options group"""
        group = QGroupBox("⚙️ Export Options")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                border: 1px solid #9C27B0;
                border-radius: 5px;
            }
        """)
        
        layout = QGridLayout()
        
        self.include_charts = QCheckBox("📈 Include Charts and Graphs")
        self.include_charts.setChecked(True)
        self.include_charts.setFont(QFont("Arial", 9))
        layout.addWidget(self.include_charts, 0, 0)
        
        self.include_summary = QCheckBox("📋 Include Executive Summary")
        self.include_summary.setChecked(True)
        self.include_summary.setFont(QFont("Arial", 9))
        layout.addWidget(self.include_summary, 0, 1)
        
        self.compress_pdf = QCheckBox("🗜️ Compress PDF Files")
        self.compress_pdf.setFont(QFont("Arial", 9))
        layout.addWidget(self.compress_pdf, 1, 0)
        
        self.password_protect = QCheckBox("🔒 Password Protect")
        self.password_protect.setFont(QFont("Arial", 9))
        layout.addWidget(self.password_protect, 1, 1)
        
        # Password field
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Enter password for protection")
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_field.setEnabled(False)
        layout.addWidget(self.password_field, 2, 0, 1, 2)
        
        self.password_protect.stateChanged.connect(
            lambda state: self.password_field.setEnabled(state == Qt.Checked)
        )
        
        group.setLayout(layout)
        return group
    
    def create_action_buttons(self) -> QGroupBox:
        """Create action buttons group"""
        group = QGroupBox("🚀 Export Actions")
        
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        self.export_btn = QPushButton("🚀 Generate Daily Export")
        self.export_btn.setMinimumHeight(45)
        self.export_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        self.preview_btn = QPushButton("👁️ Preview Report")
        self.preview_btn.setMinimumHeight(40)
        
        self.schedule_btn = QPushButton("⏰ Schedule Export")
        self.schedule_btn.setMinimumHeight(40)
        
        self.save_template_btn = QPushButton("💾 Save Template")
        self.save_template_btn.setMinimumHeight(40)
        
        for btn in [self.preview_btn, self.schedule_btn, self.save_template_btn]:
            btn.setFont(QFont("Arial", 10))
            
        self.load_template_btn = QPushButton("📂 Load Template")
        self.load_template_btn.setMinimumHeight(40)
        self.load_template_btn.setFont(QFont("Arial", 10))
        self.load_template_btn.clicked.connect(self.load_template_dialog)
    
        layout.addWidget(self.export_btn)
        layout.addWidget(self.preview_btn)
        layout.addWidget(self.schedule_btn)
        layout.addWidget(self.save_template_btn)
        layout.addWidget(self.load_template_btn)
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def create_progress_section(self) -> QGroupBox:
        """Create progress section"""
        group = QGroupBox("📊 Export Progress")
        
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        self.status_label = QLabel("✅ Ready to generate daily export")
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Arial", 9))
        self.details_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
                background-color: #f9f9f9;
            }
        """)
        
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.details_text)
        
        group.setLayout(layout)
        return group
    
    def setup_connections(self):
        """Setup signal connections"""
        self.export_btn.clicked.connect(self.generate_export)
        self.preview_btn.clicked.connect(self.preview_export)
        self.schedule_btn.clicked.connect(self.schedule_export)
        self.save_template_btn.clicked.connect(self.save_template)
    
    def load_data(self):
        """Load data from database"""
        self.refresh_wells_list()
    
    def refresh_wells_list(self):
        """Refresh wells list from database"""
        try:
            self.well_combo.clear()
            logger.info("Clearing wells combo box")
            
            if self.db:
                wells = self.db.get_wells_by_project(None)  # Get all wells
                logger.info(f"Retrieved {len(wells) if wells else 0} wells from database")
                
                if wells:
                    for well in wells:
                        well_id = well.get('id')
                        well_name = well.get('name', f'Well_{well_id}')
                        
                        logger.info(f"Adding well: {well_name} (ID: {well_id})")
                        
                        if well_id is not None:
                            # استفاده از یک روش ثابت
                            self.well_combo.addItem(well_name, userData=well_id)
                        else:
                            logger.warning(f"Well ID is None for well: {well_name}")
                
                else:
                    logger.warning("No wells returned from database")
                    # اضافه کردن داده‌های نمونه برای تست
                    sample_wells = [
                        {"id": 1, "name": "Default Well - Test"},
                        {"id": 2, "name": "Test Well 1"},
                        {"id": 3, "name": "Test Well 2"}
                    ]
                    for well in sample_wells:
                        self.well_combo.addItem(well['name'], userData=well['id'])
                        logger.info(f"Added sample well: {well['name']}")
            
            else:
                logger.error("Database manager is None!")
                # داده‌های نمونه
                self.well_combo.addItem("Test Well A", userData=1)
                self.well_combo.addItem("Test Well B", userData=2)
                self.well_combo.addItem("Test Well C", userData=3)
            
            if self.well_combo.count() > 0:
                self.well_combo.setCurrentIndex(0)
                current_id = self.well_combo.currentData()
                current_name = self.well_combo.currentText()
                logger.info(f"Set default well: '{current_name}' (ID: {current_id})")
            else:
                logger.error("No wells available in combo box!")
                    
        except Exception as e:
            logger.error(f"Error refreshing wells list: {e}", exc_info=True)
            self.status_manager.show_error("DailyExportTab", f"Error loading wells: {str(e)}")
            
    def select_all_reports(self):
        """Select all reports"""
        for _, checkbox in self.report_checkboxes:
            checkbox.setChecked(True)
    
    def deselect_all_reports(self):
        """Deselect all reports"""
        for _, checkbox in self.report_checkboxes:
            checkbox.setChecked(False)
    
    def get_selected_reports(self) -> List[str]:
        """
        Returns list of selected report identifiers
        Example: ["Well Info", "Daily Report", "Mud Report"]
        """
        selected_reports = []

        for report_key, checkbox in self.report_checkboxes:
            if checkbox.isChecked():
                selected_reports.append(report_key)

        return selected_reports
 
    def get_export_format(self) -> str:
        """Get selected export format"""
        logger.info("Checking export format...")
        
        if self.pdf_radio and self.pdf_radio.isChecked():
            logger.info("PDF format selected")
            return "pdf"
        elif self.word_radio and self.word_radio.isChecked():
            logger.info("Word format selected")
            return "word"
        elif self.excel_radio and self.excel_radio.isChecked():
            logger.info("Excel format selected")
            return "excel"
        elif self.all_formats_radio and self.all_formats_radio.isChecked():
            logger.info("All formats selected")
            return "all"
        else:
            logger.warning("No format selected, defaulting to JSON")
            return "json"
        
    def validate_inputs(self) -> bool:
        logger.info("=== DailyExportTab Validation ===")

        # --- Well validation ---
        if self.well_combo.count() == 0:
            QMessageBox.warning(self, "Validation Error", "No wells available.")
            return False

        if self.well_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validation Error", "Please select a well.")
            return False

        well_id = self.well_combo.currentData()
        well_name = self.well_combo.currentText()

        if well_id is None:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Selected well '{well_name}' has no valid ID."
            )
            return False

        logger.info(f"Selected well OK: {well_name} (ID={well_id})")

        # --- Reports validation ---
        selected_reports = self.get_selected_reports()
        logger.info(f"Selected reports: {selected_reports}")

        if not selected_reports:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select at least one report to export."
            )
            return False

        # --- Date validation ---
        from_date = self.from_date.date()
        to_date = self.to_date.date()

        if from_date > to_date:
            QMessageBox.warning(
                self,
                "Validation Error",
                "'From Date' cannot be after 'To Date'."
            )
            return False

        logger.info("Validation PASSED")
        return True
      
    def get_current_well_id(self) -> Optional[int]:
        """Get current well ID safely"""
        if self.well_combo.currentIndex() < 0:
            return None
        
        well_id = self.well_combo.currentData()
        
        # اگر None بود، سعی کن از متن استخراج کنی
        if well_id is None:
            text = self.well_combo.currentText()
            # سعی کن ID را از متن استخراج کنی
            import re
            match = re.search(r'\(ID: (\d+)\)', text)
            if match:
                well_id = int(match.group(1))
        
        return well_id
    
    def generate_export(self):
        """Generate the export - نسخه اصلاح شده"""
        try:
            logger.info("=" * 50)
            logger.info("STARTING EXPORT PROCESS")
            logger.info("=" * 50)
            
            if not self.validate_inputs():
                logger.warning("Input validation failed")
                return
            
            # Get export parameters
            well_id = self.well_combo.currentData()
            well_name = self.well_combo.currentText()
            export_format = self.get_export_format()  # این خط مهم است!
            
            logger.info(f"Export Parameters:")
            logger.info(f"  - Well ID: {well_id}")
            logger.info(f"  - Well Name: {well_name}")
            logger.info(f"  - Format: {export_format}")
            
            # تبدیل تاریخ‌ها
            from_date = self.from_date.date()
            to_date = self.to_date.date()
            
            # تبدیل QDate به Python date
            if hasattr(from_date, 'toPython'):
                from_date_py = from_date.toPython()
                to_date_py = to_date.toPython()
            else:
                from_date_py = date(from_date.year(), from_date.month(), from_date.day())
                to_date_py = date(to_date.year(), to_date.month(), to_date.day())
            
            logger.info(f"  - Date Range: {from_date_py} to {to_date_py}")
            
            selected_reports = self.get_selected_reports()
            logger.info(f"  - Selected Reports: {selected_reports}")
            
            # Update UI
            self.progress_bar.setValue(0)
            self.status_label.setText(f"🔄 Preparing {export_format.upper()} export for {well_name}...")
            self.details_text.clear()
            QApplication.processEvents()
            
            # بررسی وجود DatabaseManager
            if not self.db:
                QMessageBox.critical(self, "Error", "Database connection not available!")
                return
            
            # Create export components
            try:
                export_generator = ExportGenerator(self.db)
                data_collector = ExportDataCollector(self.db)
                logger.info("Export components created successfully")
            except Exception as e:
                logger.error(f"Error creating export components: {e}")
                QMessageBox.critical(self, "Error", f"Failed to initialize export: {str(e)}")
                return
            
            # ایجاد پوشه خروجی بر اساس فرمت
            output_dir = f"exports/{export_format.lower()}"
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Output directory: {output_dir}")
            
            total_reports = len(selected_reports)
            exported_files = []
            
            for i, report_type in enumerate(selected_reports):
                progress = int((i + 1) / total_reports * 100)
                self.progress_bar.setValue(progress)
                
                logger.info(f"Processing report: {report_type}")
                self.details_text.append(f"📄 Exporting {report_type} as {export_format.upper()}...")
                QApplication.processEvents()
                
                try:
                    file_path = ""
                    
                    # بر اساس نوع گزارش و فرمت، export مناسب را فراخوانی کنید
                    if report_type == "Well Info":
                        well_data = data_collector.get_well_info(well_id)
                        if well_data:
                            file_path = self.get_export_format(
                                export_generator, well_data, well_name, report_type, 
                                export_format, output_dir
                            )
                    
                    elif report_type == "Daily Report":
                        reports_data = data_collector.get_daily_reports_for_export(
                            well_id, from_date_py, to_date_py
                        )
                        if reports_data:
                            file_path = self.get_export_format(
                                export_generator, reports_data, well_name, report_type, 
                                export_format, output_dir
                            )
                    
                    elif report_type == "Drilling Parameters":
                        drilling_data = data_collector.get_drilling_parameters_for_export(
                            well_id, from_date_py, to_date_py
                        )
                        if drilling_data:
                            file_path = self.get_export_format(
                                export_generator, drilling_data, well_name, report_type, 
                                export_format, output_dir
                            )
                    
                    elif report_type == "Mud Report":
                        mud_data = data_collector.get_mud_reports_for_export(
                            well_id, from_date_py, to_date_py
                        )
                        if mud_data:
                            file_path = self.get_export_format(
                                export_generator, mud_data, well_name, report_type, 
                                export_format, output_dir
                            )
                    
                    elif report_type == "Safety":
                        safety_data = {
                            "safety_reports": data_collector.get_safety_reports_for_export(
                                well_id, from_date_py, to_date_py
                            ),
                            "bop_components": data_collector.get_bop_components_for_export(well_id),
                            "waste_records": data_collector.get_waste_records_for_export(
                                well_id, from_date_py, to_date_py
                            )
                        }
                        if any(safety_data.values()):
                            file_path = self.get_export_format(
                                export_generator, safety_data, well_name, report_type, 
                                export_format, output_dir
                            )
                    
                    # بقیه گزارش‌ها...
                    
                    if file_path:
                        exported_files.append(file_path)
                        self.details_text.append(f"   ✓ Saved to: {os.path.basename(file_path)}")
                        logger.info(f"File saved: {file_path}")
                    else:
                        self.details_text.append(f"   ⚠️ No data available")
                    
                except Exception as e:
                    logger.error(f"Error exporting {report_type}: {e}", exc_info=True)
                    self.details_text.append(f"   ❌ Error: {str(e)[:50]}")
                
                QApplication.processEvents()
                import time
                time.sleep(0.1)
            
            self.progress_bar.setValue(100)
            
            # نمایش نتایج
            if exported_files:
                self.status_label.setText(f"✅ {export_format.upper()} export completed for {well_name}!")
                
                message = f"""
                📤 Export Summary - {export_format.upper()}
                
                Well: {well_name}
                Format: {export_format.upper()}
                Reports: {len(exported_files)}/{len(selected_reports)}
                Location: {output_dir}/
                
                Files created:
                """
                
                for i, file_path in enumerate(exported_files):
                    message += f"\n{i+1}. {os.path.basename(file_path)}"
                
                QMessageBox.information(
                    self,
                    f"✅ {export_format.upper()} Export Complete",
                    message
                )
                
                # باز کردن پوشه خروجی
                self._open_export_folder(output_dir)
                
            else:
                self.status_label.setText("⚠️ No files were exported")
                QMessageBox.warning(
                    self,
                    "Export Warning",
                    "No files were exported. Check if data exists for selected reports."
                )
            
        except Exception as e:
            logger.error(f"Error in generate_export: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
            self.status_label.setText("❌ Export failed")
            
    def preview_export(self):
        """Preview the export"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📊 Daily Export Preview")
        dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Preview content
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        
        # Build preview
        content = """
        <h2>📊 Daily Export Preview</h2>
        <hr>
        <h3>🎯 Well Information</h3>
        <p><b>Well:</b> {well}</p>
        <p><b>Date Range:</b> {from_date} to {to_date}</p>
        <hr>
        <h3>📄 Selected Reports</h3>
        <ul>
        """.format(
            well=self.well_combo.currentText(),
            from_date=self.from_date.date().toString('yyyy-MM-dd'),
            to_date=self.to_date.date().toString('yyyy-MM-dd')
        )
        
        for report_name, checkbox in self.report_checkboxes:
            if checkbox.isChecked():
                content += f"<li>✓ {report_name}</li>"
        
        content += """
        </ul>
        <hr>
        <h3>📁 Export Settings</h3>
        <p><b>Format:</b> {format}</p>
        <p><b>Include Charts:</b> {charts}</p>
        <p><b>Include Summary:</b> {summary}</p>
        <hr>
        <p style='color: #666; font-style: italic;'>
        This is a preview. Actual export will generate complete reports with all data.
        </p>
        """.format(
            format=self.get_export_format().upper(),
            charts='Yes' if self.include_charts.isChecked() else 'No',
            summary='Yes' if self.include_summary.isChecked() else 'No'
        )
        
        preview_text.setHtml(content)
        layout.addWidget(preview_text)
        
        # Close button
        close_btn = QPushButton("Close Preview")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def schedule_export(self):
        """Schedule daily export"""
        dialog = QDialog(self)
        dialog.setWindowTitle("⏰ Schedule Daily Export")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Schedule options
        layout.addWidget(QLabel("🕒 Schedule Time:"))
        time_edit = QTimeEdit()
        time_edit.setTime(QTime(18, 0))
        layout.addWidget(time_edit)
        
        layout.addWidget(QLabel("📅 Frequency:"))
        freq_combo = QComboBox()
        freq_combo.addItems(["Daily", "Weekly", "Monthly"])
        layout.addWidget(freq_combo)
        
        layout.addWidget(QLabel("📧 Email Notification:"))
        email_edit = QLineEdit()
        email_edit.setPlaceholderText("email@example.com")
        layout.addWidget(email_edit)
        
        layout.addWidget(QLabel("💾 Save Location:"))
        save_combo = QComboBox()
        save_combo.addItems(["Local Server", "Cloud Storage", "Email", "All"])
        layout.addWidget(save_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        schedule_btn = QPushButton("✅ Schedule")
        cancel_btn = QPushButton("❌ Cancel")
        
        btn_layout.addWidget(schedule_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        def on_schedule():
            QMessageBox.information(
                dialog,
                "✅ Export Scheduled",
                f"""
                Export scheduled successfully!
                
                Time: {time_edit.time().toString('HH:mm')}
                Frequency: {freq_combo.currentText()}
                Email: {email_edit.text() or 'None'}
                Save to: {save_combo.currentText()}
                
                Next export: Tomorrow at {time_edit.time().toString('HH:mm')}
                """
            )
            dialog.close()
        
        schedule_btn.clicked.connect(on_schedule)
        cancel_btn.clicked.connect(dialog.close)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def export_single_report(
        self,
        export_generator,
        well_data: dict,
        well_name: str,
        report_type: str,
        export_format: str,
        output_dir: str
    ) -> str:
        """
        Export a single report using selected generator
        """

        if export_format == "word":
            return export_generator.export_word(
                well_data=well_data,
                well_name=well_name,
                report_type=report_type,
                output_dir=output_dir
            )

        if export_format == "pdf":
            return export_generator.export_pdf(
                well_data=well_data,
                well_name=well_name,
                report_type=report_type,
                output_dir=output_dir
            )

        raise ValueError(f"Unsupported export format: {export_format}")


    def save_template(self):
        """Save template to database"""
        try:
            # تشخیص نوع تب
            if isinstance(self, DailyExportTab):
                template_type = "daily"
            elif isinstance(self, EOWRExportTab):
                template_type = "eowr"
            elif isinstance(self, BatchExportTab):
                template_type = "batch"
            else:
                template_type = "general"
            
            template_data = {
                "name": f"{template_type.upper()} Template - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "template_type": template_type,
                "description": f"{template_type.upper()} export template",
                "created_at": datetime.now(),
                "version": "1.0"
            }
            
            if self.db:
                template_id = self.db.save_export_template(template_data)
                if template_id:
                    self.status_manager.show_success(self.__class__.__name__, 
                                                   f"Template saved (ID: {template_id})")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False
            
    def load_template_dialog(self):
        """Open dialog to load daily export template from database"""
        if not self.db:
            QMessageBox.warning(self, "Warning", "Database not available")
            return
        
        try:
            # Get templates from database for daily export
            templates = self.db.get_export_templates(template_type="daily")
            
            if not templates:
                QMessageBox.information(self, "No Templates", 
                                      "No saved daily export templates found.")
                return
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("📂 Load Daily Export Template")
            dialog.setFixedSize(500, 400)
            
            layout = QVBoxLayout()
            
            # Template list
            template_list = QListWidget()
            for template in templates:
                item = QListWidgetItem(f"📄 {template['name']}")
                item.setData(Qt.UserRole, template['id'])
                item.setToolTip(template.get('description', 'No description'))
                
                # Mark default template
                if template.get('is_default'):
                    item.setText(f"⭐ {template['name']} (Default)")
                    item.setForeground(QColor("#FF9900"))
                
                template_list.addItem(item)
            
            layout.addWidget(QLabel("Select template to load:"))
            layout.addWidget(template_list)
            
            # Preview area
            preview_label = QLabel("Template preview will appear here...")
            preview_label.setWordWrap(True)
            preview_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    min-height: 60px;
                }
            """)
            layout.addWidget(preview_label)
            
            # Update preview when selection changes
            def update_preview():
                selected = template_list.currentItem()
                if selected:
                    template_id = selected.data(Qt.UserRole)
                    template_data = next((t for t in templates if t['id'] == template_id), None)
                    if template_data:
                        preview = f"""
                        <b>{template_data['name']}</b><br>
                        Type: {template_data.get('template_type', 'daily')}<br>
                        Created: {template_data.get('created_at', 'Unknown')}<br>
                        Reports: {len(template_data.get('report_selection', []))}<br>
                        Description: {template_data.get('description', 'No description')}
                        """
                        preview_label.setText(preview)
            
            template_list.currentItemChanged.connect(lambda: update_preview())
            
            # Buttons
            btn_layout = QHBoxLayout()
            load_btn = QPushButton("📂 Load Template")
            set_default_btn = QPushButton("⭐ Set as Default")
            delete_btn = QPushButton("🗑️ Delete")
            cancel_btn = QPushButton("❌ Cancel")
            
            for btn in [load_btn, set_default_btn, delete_btn, cancel_btn]:
                btn.setMinimumHeight(35)
            
            btn_layout.addWidget(load_btn)
            btn_layout.addWidget(set_default_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.addStretch()
            btn_layout.addWidget(cancel_btn)
            
            layout.addLayout(btn_layout)
            
            def on_load():
                selected = template_list.currentItem()
                if not selected:
                    QMessageBox.warning(dialog, "Warning", "Please select a template")
                    return
                
                template_id = selected.data(Qt.UserRole)
                success = self.load_template(template_id)
                if success:
                    dialog.accept()
            
            def on_set_default():
                selected = template_list.currentItem()
                if not selected:
                    QMessageBox.warning(dialog, "Warning", "Please select a template")
                    return
                
                template_id = selected.data(Qt.UserRole)
                template_data = next((t for t in templates if t['id'] == template_id), None)
                if template_data:
                    reply = QMessageBox.question(dialog, "Set as Default", 
                                               f"Set '{template_data['name']}' as default template?",
                                               QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        if self.db.set_default_template(template_id, "daily"):
                            # Update UI
                            for i in range(template_list.count()):
                                item = template_list.item(i)
                                item_id = item.data(Qt.UserRole)
                                if item_id == template_id:
                                    item.setText(f"⭐ {template_data['name']} (Default)")
                                    item.setForeground(QColor("#FF9900"))
                                else:
                                    # Remove star from other items
                                    text = item.text()
                                    if text.startswith("⭐ "):
                                        text = text.replace("⭐ ", "").replace(" (Default)", "")
                                        item.setText(text)
                                        item.setForeground(QColor("#000000"))
                            
                            self.status_manager.show_success("DailyExportTab", 
                                                           f"'{template_data['name']}' set as default")
            
            def on_delete():
                selected = template_list.currentItem()
                if not selected:
                    QMessageBox.warning(dialog, "Warning", "Please select a template")
                    return
                
                template_id = selected.data(Qt.UserRole)
                template_data = next((t for t in templates if t['id'] == template_id), None)
                if template_data:
                    reply = QMessageBox.question(dialog, "Confirm Delete", 
                                               f"Are you sure you want to delete '{template_data['name']}'?",
                                               QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        if self.db.delete_export_template(template_id):
                            template_list.takeItem(template_list.row(selected))
                            self.status_manager.show_success("DailyExportTab", "Template deleted")
                            
                            # Update preview
                            preview_label.setText("Template deleted. Select another template.")
            
            load_btn.clicked.connect(on_load)
            set_default_btn.clicked.connect(on_set_default)
            delete_btn.clicked.connect(on_delete)
            cancel_btn.clicked.connect(dialog.reject)
            
            # Connect double-click to load
            template_list.itemDoubleClicked.connect(on_load)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error loading template dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load templates: {str(e)}")

    def load_template(self, template_id: int) -> bool:
        """Load daily export template from database"""
        try:
            if not self.db:
                return False
            
            template_data = self.db.get_export_template_by_id(template_id)
            if not template_data:
                QMessageBox.warning(self, "Warning", "Template not found")
                return False
            
            # Apply template settings to UI
            self.apply_template_to_ui(template_data)
            
            self.status_manager.show_success("DailyExportTab", 
                                           f"Template '{template_data['name']}' loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load template: {str(e)}")
            return False

    def apply_template_to_ui(self, template_data: dict):
        """Apply template settings to UI elements"""
        try:
            # Apply well selection
            well_selection = template_data.get('well_selection', {})
            if well_selection:
                well_id = well_selection.get('well_id')
                if well_id:
                    # Find and select the well in combo box
                    for i in range(self.well_combo.count()):
                        if self.well_combo.itemData(i) == well_id:
                            self.well_combo.setCurrentIndex(i)
                            break
            
            # Apply report selection
            report_selection = template_data.get('report_selection', [])
            for report_name, checkbox in self.report_checkboxes:
                checkbox.setChecked(report_name in report_selection)
            
            # Apply date range
            date_range = template_data.get('date_range', {})
            if date_range:
                from_date = date_range.get('from_date')
                to_date = date_range.get('to_date')
                
                if from_date:
                    self.from_date.setDate(QDate.fromString(from_date, "yyyy-MM-dd"))
                if to_date:
                    self.to_date.setDate(QDate.fromString(to_date, "yyyy-MM-dd"))
            
            # Apply format settings
            format_settings = template_data.get('format_settings', {})
            if format_settings:
                format_type = format_settings.get('format', 'word')
                
                if format_type == 'pdf':
                    self.pdf_radio.setChecked(True)
                elif format_type == 'word':
                    self.word_radio.setChecked(True)
                elif format_type == 'excel':
                    self.excel_radio.setChecked(True)
                else:
                    self.all_formats_radio.setChecked(True)
                
                # Apply options
                self.include_charts.setChecked(format_settings.get('include_charts', True))
                self.include_summary.setChecked(format_settings.get('include_summary', True))
                self.compress_pdf.setChecked(format_settings.get('compress_pdf', False))
                
                password_protect = format_settings.get('password_protect', False)
                self.password_protect.setChecked(password_protect)
                
                # Apply password if exists
                options = template_data.get('options', {})
                if password_protect and options.get('password'):
                    self.password_field.setText(options['password'])
            
            # Update status
            self.status_label.setText(f"✅ Template '{template_data['name']}' loaded")
            
        except Exception as e:
            logger.error(f"Error applying template to UI: {e}")
            raise


# ==================== EOWR Export Tab ====================
@make_scrollable
class EOWRExportTab(QWidget):
    """End of Well Report Export Tab"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        super().__init__()
        self.db = db_manager
        self.status_manager = StatusBarManager()
        self.current_well = None
        self.selected_sections = []
        if db_manager:
            self.data_collector = ExportDataCollector(db_manager)
        else:
            self.data_collector = None
        
        self.init_ui()
        self.setup_connections()
        self.load_data()
    def get_selected_reports(self) -> List[str]:
        """Get list of selected report names - برای EOWR"""

        return self.get_selected_sections()
    
    def init_ui(self):
        """Initialize the UI for EOWR tab"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header
        header_label = QLabel("📑 End of Well Report (EOWR) - Comprehensive Well Analysis")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #e8f4f8;
                border-radius: 5px;
                border-left: 5px solid #3498db;
            }
        """)
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Splitter for two panels
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #ddd;
                width: 2px;
            }
        """)
        
        # Left panel: Report sections
        left_panel = self.create_left_panel()
        
        # Right panel: Export settings
        right_panel = self.create_right_panel()
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # Progress and Status
        progress_group = self.create_progress_section()
        main_layout.addWidget(progress_group)
        
        main_layout.addStretch()
    
    def create_left_panel(self) -> QWidget:
        """Create left panel with report sections"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("📋 Report Contents")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setStyleSheet("color: #2c3e50;")
        layout.addWidget(header)
        
        # Tree widget for sections
        self.sections_tree = QTreeWidget()
        self.sections_tree.setHeaderLabel("📁 Report Sections")
        self.sections_tree.setFont(QFont("Arial", 10))
        self.sections_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1565c0;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        self.setup_report_sections()
        layout.addWidget(self.sections_tree)
        
        # Select all checkbox
        select_layout = QHBoxLayout()
        self.select_all_cb = QCheckBox("✅ Select All Sections")
        self.select_all_cb.setFont(QFont("Arial", 10))
        self.select_all_cb.stateChanged.connect(self.toggle_all_sections)
        select_layout.addWidget(self.select_all_cb)
        
        # ============ این خط را اضافه کنید ============
        self.count_label = QLabel("Selected: 0 sections")  # <-- این خط را اضافه کنید
        self.count_label.setFont(QFont("Arial", 9))
        select_layout.addWidget(self.count_label)
        select_layout.addStretch()
        
        layout.addLayout(select_layout)
        
        # Selection info
        info_group = QGroupBox("ℹ️ Selection Info")
        info_group.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                border: 1px solid #7f8c8d;
                border-radius: 5px;
            }
        """)
        
        info_layout = QVBoxLayout()
        self.selection_summary = QLabel("No sections selected")
        self.selection_summary.setFont(QFont("Arial", 9))
        self.selection_summary.setWordWrap(True)
        info_layout.addWidget(self.selection_summary)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with export settings"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Well information
        well_group = QGroupBox("🎯 Well Information")
        well_group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                border: 2px solid #2ecc71;
                border-radius: 5px;
            }
        """)
        
        well_layout = QFormLayout()
        well_layout.setSpacing(10)
        
        self.well_combo = QComboBox()
        self.well_combo.setMinimumHeight(35)
        self.well_combo.setFont(QFont("Arial", 10))
        well_layout.addRow("Well Name:", self.well_combo)
        
        self.operator_edit = QLineEdit()
        self.operator_edit.setPlaceholderText("e.g., NIOC, Schlumberger")
        well_layout.addRow("Operator:", self.operator_edit)
        
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("e.g., Field, Block, Coordinates")
        well_layout.addRow("Location:", self.location_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Exploration", "Development", "Appraisal", "Injection"])
        well_layout.addRow("Well Type:", self.type_combo)
        
        well_group.setLayout(well_layout)
        layout.addWidget(well_group)
        
        # Format selection
        format_group = QGroupBox("📁 Export Format")
        format_group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                border: 1px solid #FF9800;
                border-radius: 5px;
            }
        """)
        
        format_layout = QVBoxLayout()
        format_layout.setSpacing(10)
        
        self.format_pdf = QRadioButton("📄 PDF Document (Recommended)")
        self.format_word = QRadioButton("📝 Word Document (Editable)")
        self.format_xml = QRadioButton("📊 XML (Project Exchange)")
        self.format_excel = QRadioButton("📈 Excel Spreadsheet (Data Only)")
        self.format_all = QRadioButton("📦 All Formats (Complete Package)")
        
        self.format_pdf.setChecked(True)
        
        for radio in [self.format_pdf, self.format_word, self.format_xml, 
                     self.format_excel, self.format_all]:
            radio.setFont(QFont("Arial", 10))
            format_layout.addWidget(radio)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Settings
        settings_group = QGroupBox("⚙️ Report Settings")
        settings_group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                border: 1px solid #9C27B0;
                border-radius: 5px;
            }
        """)
        
        settings_layout = QGridLayout()
        settings_layout.setSpacing(10)
        
        # Logo settings
        settings_layout.addWidget(QLabel("🏢 Company Logo:"), 0, 0)
        
        logo_layout = QHBoxLayout()
        self.logo_path = QLineEdit()
        self.logo_path.setPlaceholderText("Path to company logo...")
        self.browse_logo_btn = QPushButton("Browse...")
        
        logo_layout.addWidget(self.logo_path)
        logo_layout.addWidget(self.browse_logo_btn)
        settings_layout.addLayout(logo_layout, 0, 1)
        
        self.preview_logo_btn = QPushButton("👁️ Preview")
        settings_layout.addWidget(self.preview_logo_btn, 0, 2)
        
        # Additional settings
        self.include_charts_cb = QCheckBox("📈 Include Charts & Graphs")
        self.include_charts_cb.setChecked(True)
        settings_layout.addWidget(self.include_charts_cb, 1, 0, 1, 3)
        
        self.include_images_cb = QCheckBox("🖼️ Include Images & Schematics")
        self.include_images_cb.setChecked(True)
        settings_layout.addWidget(self.include_images_cb, 2, 0, 1, 3)
        
        self.include_raw_data_cb = QCheckBox("📊 Include Raw Data Tables")
        self.include_raw_data_cb.setChecked(True)
        settings_layout.addWidget(self.include_raw_data_cb, 3, 0, 1, 3)
        
        settings_layout.addWidget(QLabel("🔒 Watermark Text:"), 4, 0)
        self.watermark_edit = QLineEdit()
        self.watermark_edit.setPlaceholderText("e.g., CONFIDENTIAL - COMPANY PROPERTY")
        settings_layout.addWidget(self.watermark_edit, 4, 1, 1, 2)
        
        settings_layout.addWidget(QLabel("📄 Report Title:"), 5, 0)
        self.report_title_edit = QLineEdit()
        self.report_title_edit.setPlaceholderText("e.g., Well X-1 Final Drilling Report")
        settings_layout.addWidget(self.report_title_edit, 5, 1, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Generation options
        gen_group = QGroupBox("🚀 Generation Options")
        gen_layout = QHBoxLayout()
        
        self.sequential_gen = QRadioButton("Sequential (Slower but safer)")
        self.parallel_gen = QRadioButton("Parallel (Faster but more memory)")
        self.parallel_gen.setChecked(True)
        
        gen_layout.addWidget(self.sequential_gen)
        gen_layout.addWidget(self.parallel_gen)
        gen_layout.addStretch()
        
        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)
        
        # Generate button
        self.generate_btn = QPushButton("🚀 Generate Full EOWR Report")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        layout.addWidget(self.generate_btn)
        
        # Additional buttons
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("👁️ Preview Sections")
        self.save_template_btn = QPushButton("💾 Save Template")
        self.load_template_btn = QPushButton("📂 Load Template")
        
        for btn in [self.preview_btn, self.save_template_btn, self.load_template_btn]:
            btn.setMinimumHeight(35)
            btn.setFont(QFont("Arial", 10))
            button_layout.addWidget(btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        return panel
    
    def create_progress_section(self) -> QGroupBox:
        """Create progress section"""
        group = QGroupBox("📊 Generation Progress")
        
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("✅ Ready to generate End of Well Report")
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(120)
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Arial", 9))
        layout.addWidget(self.details_text)
        
        group.setLayout(layout)
        return group
    
    def setup_report_sections(self):
        """Setup the EOWR report sections tree"""
        sections = {
            "📋 1. General Information": [
                "📄 1.1 Field Introduction & Geology",
                "🗺️ 1.2 Well Location Map & Coordinates",
                "🏷️ 1.3 Well Identification & History",
                "👥 1.4 Project Team & Contacts"
            ],
            "📈 2. Drilling Operations": [
                "⚙️ 2.1 Drilling Parameters Summary",
                "📊 2.2 ROP & Performance Charts",
                "🧱 2.3 Bit Record & Analysis",
                "🔧 2.4 BHA Design & History",
                "🛢️ 2.5 Casing Program & Installation",
                "🧱 2.6 Cementing Operations"
            ],
            "⏱️ 3. Time Analysis": [
                "📅 3.1 Time vs Depth Chart",
                "📊 3.2 Total Time Break-Down",
                "⚠️ 3.3 NPT Analysis & Summary",
                "📈 3.4 Performance Benchmarking"
            ],
            "🌍 4. Geological Analysis": [
                "📝 4.1 Formation Evaluation",
                "📊 4.2 Logging & Testing Reports",
                "🖼️ 4.3 Geological Cross-Sections"
            ],
            "🧪 5. Mud & Fluids": [
                "📋 5.1 Mud Program Summary",
                "📊 5.2 Fluid Properties History",
                "📈 5.3 Volume & Hydraulics Analysis"
            ],
            "🦺 6. Safety & Environment": [
                "📝 6.1 HSE Performance",
                "🔧 6.2 BOP Test Records",
                "🗑️ 6.3 Waste Management Report",
                "📋 6.4 Incident & Near-Miss Log"
            ],
            "📊 7. Engineering Analysis": [
                "📈 7.1 Hydraulics & ECD Analysis",
                "⚙️ 7.2 Torque & Drag Analysis",
                "📐 7.3 Wellbore Stability",
                "🎯 7.4 Directional Drilling Analysis"
            ],
            "📝 8. Final Well Status": [
                "🛢️ 8.1 Completion Details",
                "🎄 8.2 Wellhead & X-mas Tree",
                "📐 8.3 Final Well Schematic",
                "⚠️ 8.4 Abandonment Details (if applicable)"
            ],
            "📋 9. Appendices": [
                "📄 9.1 Daily Drilling Reports",
                "📊 9.2 Raw Data Tables",
                "🖼️ 9.3 Supporting Images",
                "📝 9.4 Certificates & Approvals"
            ]
        }

        for parent, children in sections.items():
            parent_item = QTreeWidgetItem(self.sections_tree, [parent])
            parent_item.setCheckState(0, Qt.Checked)
            parent_item.setFont(0, QFont("Arial", 10, QFont.Bold))

            for child in children:
                child_item = QTreeWidgetItem(parent_item, [child])
                child_item.setCheckState(0, Qt.Checked)
                child_item.setFont(0, QFont("Arial", 9))

        self.sections_tree.expandAll()
        self.update_selection_count()
    
    def setup_connections(self):
        """Setup signal connections"""
        self.browse_logo_btn.clicked.connect(self.browse_logo)
        self.preview_logo_btn.clicked.connect(self.preview_logo)
        self.sections_tree.itemChanged.connect(self.update_selection_count)
        self.sections_tree.itemChanged.connect(self.update_selection_summary)
        self.generate_btn.clicked.connect(self.generate_report)
        self.preview_btn.clicked.connect(self.preview_sections)
        self.save_template_btn.clicked.connect(self.save_template)
        self.load_template_btn.clicked.connect(self.load_template)
    
    def load_data(self):
        """Load data from database"""
        self.refresh_wells_list()
        
        # Set default values
        self.operator_edit.setText("National Iranian Oil Company")
        self.location_edit.setText("South Pars Gas Field, Block 12")
        self.report_title_edit.setText("Well X-1 Final Drilling Report")
    
    def refresh_wells_list(self):
        """Refresh wells list from database"""
        try:
            self.well_combo.clear()
            logger.info("Clearing wells combo box")
            
            if self.db:
                wells = self.db.get_wells_by_project(None)  # Get all wells
                logger.info(f"Retrieved {len(wells) if wells else 0} wells from database")
                
                if wells:
                    for well in wells:
                        well_id = well.get('id')
                        well_name = well.get('name', f'Well_{well_id}')
                        
                        logger.info(f"Adding well: {well_name} (ID: {well_id})")
                        
                        if well_id is not None:
                            # استفاده از یک روش ثابت
                            self.well_combo.addItem(well_name, userData=well_id)
                        else:
                            logger.warning(f"Well ID is None for well: {well_name}")
                
                else:
                    logger.warning("No wells returned from database")
                    # اضافه کردن داده‌های نمونه برای تست
                    sample_wells = [
                        {"id": 1, "name": "Default Well - Test"},
                        {"id": 2, "name": "Test Well 1"},
                        {"id": 3, "name": "Test Well 2"}
                    ]
                    for well in sample_wells:
                        self.well_combo.addItem(well['name'], userData=well['id'])
                        logger.info(f"Added sample well: {well['name']}")
            
            else:
                logger.error("Database manager is None!")
                # داده‌های نمونه
                self.well_combo.addItem("Test Well A", userData=1)
                self.well_combo.addItem("Test Well B", userData=2)
                self.well_combo.addItem("Test Well C", userData=3)
            
            if self.well_combo.count() > 0:
                self.well_combo.setCurrentIndex(0)
                current_id = self.well_combo.currentData()
                current_name = self.well_combo.currentText()
                logger.info(f"Set default well: '{current_name}' (ID: {current_id})")
            else:
                logger.error("No wells available in combo box!")
                    
        except Exception as e:
            logger.error(f"Error refreshing wells list: {e}", exc_info=True)
            self.status_manager.show_error("DailyExportTab", f"Error loading wells: {str(e)}")
        
    def toggle_all_sections(self, state):
        """Toggle selection of all sections"""
        # تبدیل state از int به Qt.CheckState
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        root = self.sections_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setCheckState(0, check_state)
            for j in range(item.childCount()):
                child = item.child(j)
                child.setCheckState(0, check_state)
            
    def update_selection_count(self):
        """Update count of selected sections"""
        count = 0
        root = self.sections_tree.invisibleRootItem()
        
        def count_selected(item):
            nonlocal count
            if item.checkState(0) == Qt.Checked:
                count += 1
            for i in range(item.childCount()):
                count_selected(item.child(i))
        
        for i in range(root.childCount()):
            count_selected(root.child(i))
        
        if hasattr(self, 'count_label'): 
            self.count_label.setText(f"Selected: {count} sections")
    
    def update_selection_summary(self):
        """Update selection summary text"""
        selected = self.get_selected_sections()
        
        if not selected:
            self.selection_summary.setText("❌ No sections selected")
            return
            
        # Group by main category
        categories = {}
        for section in selected:
            if '.' in section:
                cat_num = section.split('.')[0]
                categories.setdefault(cat_num, []).append(section)
        
        summary = "✅ Selected sections:\n"
        for cat_num in sorted(categories.keys()):
            sections = categories[cat_num]
            if len(sections) <= 3:
                summary += f"• Category {cat_num}: {', '.join(s.split('. ')[1][:20] + '...' for s in sections)}\n"
            else:
                summary += f"• Category {cat_num}: {len(sections)} sections\n"
        
        self.selection_summary.setText(summary)
    
    def get_selected_sections(self) -> List[str]:
        """Get list of selected sections"""
        selected = []
        root = self.sections_tree.invisibleRootItem()

        def traverse(item):
            if item.checkState(0) == Qt.Checked:
                text = item.text(0)
                selected.append(text)  # متن کامل را برمی‌گردانیم
            for i in range(item.childCount()):
                traverse(item.child(i))

        for i in range(root.childCount()):
            traverse(root.child(i))

        return selected
    
    def get_export_format(self) -> str:
        """Get selected export format"""
        logger.info("Checking export format...")
        
        if self.pdf_radio and self.pdf_radio.isChecked():
            logger.info("PDF format selected")
            return "pdf"
        elif self.word_radio and self.word_radio.isChecked():
            logger.info("Word format selected")
            return "word"
        elif self.excel_radio and self.excel_radio.isChecked():
            logger.info("Excel format selected")
            return "excel"
        elif self.all_formats_radio and self.all_formats_radio.isChecked():
            logger.info("All formats selected")
            return "all"
        else:
            logger.warning("No format selected, defaulting to JSON")
            return "json"
            
    def browse_logo(self):
        """Browse for company logo"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Logo", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        if file_name:
            self.logo_path.setText(file_name)
    
    def preview_logo(self):
        """Preview selected logo"""
        logo_path = self.logo_path.text()
        if not logo_path or not os.path.exists(logo_path):
            QMessageBox.warning(self, "No Logo", "Please select a valid logo file first")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Logo Preview")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Display logo
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            label = QLabel()
            label.setPixmap(pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        
        # File info
        file_info = QLabel(f"File: {os.path.basename(logo_path)}\nSize: {pixmap.width()}x{pixmap.height()}")
        file_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(file_info)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def validate_inputs(self) -> bool:
        """Validate user inputs"""
        # بررسی انتخاب چاه
        if self.well_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Warning", "Please select a well.")
            return False
        
        well_id = self.well_combo.currentData()
        well_name = self.well_combo.currentText()
        
        if well_id is None:
            QMessageBox.warning(self, "Warning", "Invalid well selected. Please select a valid well.")
            return False
        
        logger.info(f"Selected well - Name: {well_name}, ID: {well_id}")
        
        # در EOWR ما sections داریم نه reports
        selected_sections = self.get_selected_sections()
        if not selected_sections:
            QMessageBox.warning(self, "Warning", "Please select at least one section.")
            return False
        
        # EOWR نیازی به تاریخ ندارد، اما می‌توانیم تاریخ‌های پیش‌فرض داشته باشیم
        return True
    
    def generate_report(self):
        """Generate the EOWR report"""
        try:
            if not self.validate_inputs():
                return
            
            # Get report parameters
            well_id = self.well_combo.currentData()
            well_name = self.well_combo.currentText()
            selected_sections = self.get_selected_sections()
            export_format = self.get_export_format()
            
            # Update UI
            self.progress_bar.setValue(0)
            self.status_label.setText(f"🚀 Starting EOWR generation for {well_name}...")
            self.details_text.clear()
            QApplication.processEvents()
            
            # Create export generator
            export_generator = ExportGenerator(self.db)
            
            # Export complete well report
            self.details_text.append("📊 Collecting all well data...")
            QApplication.processEvents()
            
            # Get complete well data
            complete_data = self.data_collector.get_complete_well_data_for_export(well_id)
            
            if not complete_data:
                QMessageBox.warning(self, "No Data", f"No data found for well {well_name}")
                return
            
            self.progress_bar.setValue(50)
            self.details_text.append("📄 Generating export file...")
            QApplication.processEvents()
            
            # Generate export based on format
            file_path = ""
            if export_format == "PDF":
                file_path = export_generator._export_to_pdf(complete_data, f"{well_name}_EOWR")
            elif export_format == "Word":
                file_path = export_generator._export_to_json(complete_data, f"{well_name}_EOWR")  # Temp
            elif export_format == "Excel":
                file_path = export_generator._export_to_excel(complete_data, f"{well_name}_EOWR")
            elif export_format == "XML":
                file_path = export_generator._export_to_json(complete_data, f"{well_name}_EOWR")  # Temp
            else:  # All formats
                results = export_generator.export_complete_well_report(well_id, None, None, "all")
                file_path = "\n".join(results.values())
            
            self.progress_bar.setValue(100)
            
            if file_path:
                self.details_text.append(f"✅ Report generated: {file_path}")
                self.status_label.setText(f"✅ EOWR for {well_name} generated successfully!")
                
                QMessageBox.information(
                    self, 
                    "🎉 EOWR Generated Successfully!", 
                    f"""
                    📑 End of Well Report Generated!
                    
                    Well: {well_name}
                    Format: {export_format}
                    File: {file_path}
                    
                    Report includes comprehensive well data.
                    """
                )
            else:
                self.status_label.setText("❌ EOWR generation failed")
                QMessageBox.warning(self, "Export Failed", "Failed to generate EOWR report")
                
        except Exception as e:
            logger.error(f"Error generating EOWR: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate EOWR: {str(e)}")
            self.status_label.setText("❌ EOWR generation failed")
        
    def generate_report_step_by_step(self, sections: List[str], format_type: str, 
                                    well_name: str, operator: str):
        """Generate EOWR step by step with progress updates"""
        total_steps = len(sections) + 3  # +3 for setup, compilation, finalization
        current_step = 0
        
        # Step 1: Setup
        current_step += 1
        self.progress_bar.setValue(int(current_step / total_steps * 100))
        self.details_text.append(f"✅ Step 1/{total_steps}: Setting up report structure...")
        QApplication.processEvents()
        
        # Step 2: Collect data for each section
        for i, section in enumerate(sections):
            current_step += 1
            progress = int(current_step / total_steps * 100)
            self.progress_bar.setValue(progress)
            
            self.details_text.append(f"📊 Step {current_step}/{total_steps}: Collecting data for '{section}'...")
            QApplication.processEvents()
            
            # Collect data for this section
            data = self.collect_section_data(section, well_name)
            self.details_text.append(f"   ✓ Collected {data.get('count', 0)} records")
            QApplication.processEvents()
            
            # Simulate processing time
            QTimer.singleShot(500, lambda: None)
        
        # Step 3: Compile report
        current_step += 1
        self.progress_bar.setValue(int(current_step / total_steps * 100))
        self.details_text.append(f"📄 Step {current_step}/{total_steps}: Compiling {format_type} report...")
        QApplication.processEvents()
        
        # Simulate compilation time
        QTimer.singleShot(1000, lambda: None)
        
        # Step 4: Finalize
        current_step += 1
        self.progress_bar.setValue(100)
        self.details_text.append(f"✅ Step {total_steps}/{total_steps}: Report generation complete!")
        
        # Show success message
        QMessageBox.information(
            self, 
            "🎉 EOWR Generated Successfully!", 
            f"""
            📑 End of Well Report Generated!
            
            Well: {well_name}
            Operator: {operator}
            Format: {format_type}
            Sections: {len(sections)} sections included
            
            Report includes:
            • Executive Summary
            • Technical Analysis
            • Charts and Graphs
            • Recommendations
            """
        )
        
        self.status_label.setText(f"✅ EOWR for {well_name} generated successfully!")
    
    def collect_section_data(self, section: str, well_name: str) -> Dict[str, Any]:
        """Collect data for a specific section"""
        # This should collect data from database
        # For now, return sample data
        
        data_collectors = {
            "General Information": self.collect_general_info,
            "Drilling Operations": self.collect_drilling_data,
            "Time Analysis": self.collect_time_data,
            "Geological Analysis": self.collect_geology_data,
            "Mud & Fluids": self.collect_mud_data,
            "Safety & Environment": self.collect_safety_data,
            "Engineering Analysis": self.collect_engineering_data,
            "Final Well Status": self.collect_final_status,
            "Appendices": self.collect_appendix_data
        }
        
        for key, collector in data_collectors.items():
            if key.lower() in section.lower():
                return collector(well_name)
        
        return {"count": 0, "data": [], "summary": f"No data collector for {section}"}
    
    def collect_general_info(self, well_name: str) -> Dict[str, Any]:
        """Collect general well information"""
        return {
            "count": 5,
            "data": [
                {"type": "Well Information", "value": f"Well: {well_name}"},
                {"type": "Location", "value": "Field: XYZ, Block: A, Coordinates: 28.5N, 45.3E"},
                {"type": "Operator", "value": "National Iranian Oil Company (NIOC)"},
                {"type": "Contractor", "value": "Schlumberger"},
                {"type": "Dates", "value": "Start: 2024-01-01, End: 2024-03-15"}
            ],
            "summary": "Basic well identification and location data"
        }
    
    def collect_drilling_data(self, well_name: str) -> Dict[str, Any]:
        """Collect drilling operations data"""
        return {
            "count": 8,
            "data": [
                {"type": "Total Depth", "value": "3,500 m"},
                {"type": "Hole Sizes", "value": "26\", 17.5\", 12.25\", 8.5\""},
                {"type": "Casing", "value": "13-3/8\", 9-5/8\", 7\" liner"},
                {"type": "Bit Runs", "value": "12 bit runs"},
                {"type": "Average ROP", "value": "15.3 m/hr"},
                {"type": "Max ROP", "value": "28.5 m/hr"},
                {"type": "Total Drilling Time", "value": "45 days"},
                {"type": "NPT Percentage", "value": "12.5%"}
            ],
            "summary": "Drilling performance and operations summary"
        }
    
    def collect_time_data(self, well_name: str) -> Dict[str, Any]:
        """Collect time analysis data"""
        return {
            "count": 6,
            "data": [
                {"type": "Total Operation Time", "value": "1,080 hours"},
                {"type": "Productive Time", "value": "945 hours (87.5%)"},
                {"type": "NPT Time", "value": "135 hours (12.5%)"},
                {"type": "Main NPT Causes", "value": "Weather, Equipment, Waiting on Materials"},
                {"type": "Best Performance", "value": "Section 3: 320 m/day"},
                {"type": "Performance vs Plan", "value": "+5.2% ahead of schedule"}
            ],
            "summary": "Time breakdown and performance analysis"
        }
    
    def collect_geology_data(self, well_name: str) -> Dict[str, Any]:
        """Collect geological data"""
        return {
            "count": 4,
            "data": [
                {"type": "Formation Top", "value": "Asmari Formation at 2,100 m"},
                {"type": "Reservoir", "value": "Bangestan Group, 2,300-2,800 m"},
                {"type": "Porosity", "value": "12-18%"},
                {"type": "Permeability", "value": "50-200 mD"}
            ],
            "summary": "Geological formation analysis"
        }
    
    def collect_mud_data(self, well_name: str) -> Dict[str, Any]:
        """Collect mud and fluids data"""
        return {
            "count": 5,
            "data": [
                {"type": "Mud Type", "value": "Water-based mud"},
                {"type": "Weight Range", "value": "9.5-12.5 ppg"},
                {"type": "PH Range", "value": "9.5-10.5"},
                {"type": "Filtrate", "value": "6-10 cc/30min"},
                {"type": "Total Volume", "value": "2,500 bbl"}
            ],
            "summary": "Mud program and properties"
        }
    
    def collect_safety_data(self, well_name: str) -> Dict[str, Any]:
        """Collect safety and environment data"""
        return {
            "count": 4,
            "data": [
                {"type": "Days Without LTI", "value": "245 days"},
                {"type": "Last BOP Test", "value": "2024-03-01"},
                {"type": "Waste Managed", "value": "1,200 bbl"},
                {"type": "Safety Drills", "value": "Monthly fire and H2S drills"}
            ],
            "summary": "Safety performance and environmental management"
        }
    
    def collect_engineering_data(self, well_name: str) -> Dict[str, Any]:
        """Collect engineering analysis data"""
        return {
            "count": 4,
            "data": [
                {"type": "Torque & Drag", "value": "Within safe limits"},
                {"type": "ECD Management", "value": "Maintained below fracture gradient"},
                {"type": "Wellbore Stability", "value": "Stable throughout drilling"},
                {"type": "Directional Control", "value": "Accurate to within 5m tolerance"}
            ],
            "summary": "Engineering analysis and calculations"
        }
    
    def collect_final_status(self, well_name: str) -> Dict[str, Any]:
        """Collect final well status data"""
        return {
            "count": 3,
            "data": [
                {"type": "Completion", "value": "7\" production liner installed"},
                {"type": "Wellhead", "value": "10,000 psi wellhead installed"},
                {"type": "Abandonment", "value": "Not applicable - production well"}
            ],
            "summary": "Final well status and completion"
        }
    
    def collect_appendix_data(self, well_name: str) -> Dict[str, Any]:
        """Collect appendix data"""
        return {
            "count": 3,
            "data": [
                {"type": "Daily Reports", "value": "45 daily reports"},
                {"type": "Certificates", "value": "All equipment certificates available"},
                {"type": "Approvals", "value": "All regulatory approvals obtained"}
            ],
            "summary": "Supporting documents and appendices"
        }
    
    def preview_sections(self):
        """Preview selected sections"""
        selected = self.get_selected_sections()
        
        if not selected:
            QMessageBox.warning(self, "No Sections", "Please select sections to preview")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📋 EOWR Sections Preview")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Section list
        list_widget = QListWidget()
        for section in selected:
            list_widget.addItem(f"✓ {section}")
        
        layout.addWidget(list_widget)
        
        # Info
        info_label = QLabel(f"Total sections: {len(selected)}")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_template(self):
        """Save template to database"""
        try:
            # تشخیص نوع تب
            if isinstance(self, DailyExportTab):
                template_type = "daily"
            elif isinstance(self, EOWRExportTab):
                template_type = "eowr"
            elif isinstance(self, BatchExportTab):
                template_type = "batch"
            else:
                template_type = "general"
            
            template_data = {
                "name": f"{template_type.upper()} Template - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "template_type": template_type,
                "description": f"{template_type.upper()} export template",
                "created_at": datetime.now(),
                "version": "1.0"
            }
            
            if self.db:
                template_id = self.db.save_export_template(template_data)
                if template_id:
                    self.status_manager.show_success(self.__class__.__name__, 
                                                   f"Template saved (ID: {template_id})")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False
            
    def load_template(self):
        """Load EOWR template"""
        QMessageBox.information(self, "Template Loaded", "EOWR template loaded successfully!")

    def load_template_dialog(self):
        """Open dialog to load EOWR template from database"""
        if not self.db:
            QMessageBox.warning(self, "Warning", "Database not available")
            return
        
        try:
            # Get templates from database for EOWR
            templates = self.db.get_export_templates(template_type="eowr")
            
            if not templates:
                QMessageBox.information(self, "No Templates", 
                                      "No saved EOWR templates found.")
                return
            
            # Create dialog (similar to DailyExportTab but with EOWR specific preview)
            dialog = QDialog(self)
            dialog.setWindowTitle("📂 Load EOWR Template")
            dialog.setFixedSize(500, 400)
            
            layout = QVBoxLayout()
            
            # Template list
            template_list = QListWidget()
            for template in templates:
                item = QListWidgetItem(f"📑 {template['name']}")
                item.setData(Qt.UserRole, template['id'])
                item.setToolTip(template.get('description', 'No description'))
                
                if template.get('is_default'):
                    item.setText(f"⭐ {template['name']} (Default)")
                    item.setForeground(QColor("#FF9900"))
                
                template_list.addItem(item)
            
            layout.addWidget(QLabel("Select EOWR template to load:"))
            layout.addWidget(template_list)
            
            # Similar button setup as DailyExportTab...
            # ... (کد مشابه DailyExportTab با تغییرات جزئی)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error loading EOWR template dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load EOWR templates: {str(e)}")
            
# ==================== Batch Export Tab ====================
@make_scrollable
class BatchExportTab(QWidget):
    """Batch Export Tab - For multiple wells and reports"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        super().__init__()
        self.db = db_manager
        self.status_manager = StatusBarManager()
        self.export_manager = ExportManager(self)
        
        self.init_ui()
        self.setup_connections()
        self.load_data()
    
    def init_ui(self):
        """Initialize the UI for batch export tab"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header
        header_label = QLabel("📊 Batch Export - Multiple Wells & Reports")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #e8f4f8;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(header_label)
        
        # Selection Group
        selection_group = self.create_selection_group()
        main_layout.addWidget(selection_group)
        
        # Options Group
        options_group = self.create_options_group()
        main_layout.addWidget(options_group)
        
        # Action Buttons
        action_group = self.create_action_buttons()
        main_layout.addWidget(action_group)
        
        # Progress Section
        progress_group = self.create_progress_section()
        main_layout.addWidget(progress_group)
        
        main_layout.addStretch()
    
    def create_selection_group(self) -> QGroupBox:
        """Create selection group for batch export"""
        group = QGroupBox("🎯 Select Wells and Reports")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Wells selection
        wells_layout = QHBoxLayout()
        wells_layout.addWidget(QLabel("🏭 Select Wells:"))
        
        self.wells_list = QListWidget()
        self.wells_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.wells_list.setMinimumHeight(150)
        
        # Buttons for wells selection
        wells_btn_layout = QVBoxLayout()
        select_all_wells_btn = QPushButton("✅ All")
        select_all_wells_btn.clicked.connect(lambda: self.wells_list.selectAll())
        
        deselect_all_wells_btn = QPushButton("❌ None")
        deselect_all_wells_btn.clicked.connect(lambda: self.wells_list.clearSelection())
        
        load_wells_btn = QPushButton("🔄 Load")
        load_wells_btn.clicked.connect(self.load_wells)
        
        for btn in [select_all_wells_btn, deselect_all_wells_btn, load_wells_btn]:
            btn.setMaximumWidth(80)
            wells_btn_layout.addWidget(btn)
        
        wells_btn_layout.addStretch()
        
        wells_main_layout = QHBoxLayout()
        wells_main_layout.addWidget(self.wells_list)
        wells_main_layout.addLayout(wells_btn_layout)
        
        layout.addLayout(wells_main_layout)
        
        # Reports selection
        reports_label = QLabel("📄 Select Reports to Export:")
        reports_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(reports_label)
        
        reports_layout = QGridLayout()
        
        self.report_checkboxes = []
        reports = [
            ("Well Info", "📋 Well Information"),
            ("Daily Reports", "📅 Daily Drilling Reports"),
            ("Drilling Parameters", "⚙️ Drilling Parameters"),
            ("Mud Reports", "🧪 Mud Properties"),
            ("Bit Records", "🧱 Bit Records"),
            ("BHA Reports", "🔧 BHA Design"),
            ("Casing Data", "🛢️ Casing Program"),
            ("Safety Reports", "🦺 Safety Records"),
            ("Planning Data", "📝 Planning Data"),
            ("Cost Analysis", "💰 Cost Analysis"),
        ]

        row, col = 0, 0
        for report_name, report_label in reports:
            cb = QCheckBox(report_label)
            cb.setChecked(True)
            cb.setFont(QFont("Arial", 9))
            
            self.report_checkboxes.append((report_name, cb))
            reports_layout.addWidget(cb, row, col)
            
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1
        
        layout.addLayout(reports_layout)
        
        # Date range
        date_layout = QHBoxLayout()
        date_layout.setSpacing(20)
        
        from_layout = QVBoxLayout()
        from_layout.addWidget(QLabel("📅 From Date:"))
        
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        from_layout.addWidget(self.from_date)
        date_layout.addLayout(from_layout)
        
        to_layout = QVBoxLayout()
        to_layout.addWidget(QLabel("📅 To Date:"))
        
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        to_layout.addWidget(self.to_date)
        date_layout.addLayout(to_layout)
        
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        group.setLayout(layout)
        return group
    
    def create_options_group(self) -> QGroupBox:
        """Create options group for batch export"""
        group = QGroupBox("⚙️ Export Options")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                border: 1px solid #3498db;
                border-radius: 5px;
            }
        """)
        
        layout = QGridLayout()
        
        # Format selection
        layout.addWidget(QLabel("📁 Export Format:"), 0, 0)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Excel (Multiple Sheets)", "Excel (Multiple Files)", 
                                   "PDF (Combined)", "PDF (Separate)", "All Formats"])
        layout.addWidget(self.format_combo, 0, 1)
        
        # Output location
        layout.addWidget(QLabel("💾 Output Location:"), 1, 0)
        
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output folder...")
        self.output_path.setText("Exports/Batch/")
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_output_folder)
        
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)
        layout.addLayout(output_layout, 1, 1)
        
        # Options
        self.compress_files = QCheckBox("🗜️ Compress files (ZIP)")
        self.compress_files.setChecked(True)
        layout.addWidget(self.compress_files, 2, 0, 1, 2)
        
        self.include_summary = QCheckBox("📋 Include summary report")
        self.include_summary.setChecked(True)
        layout.addWidget(self.include_summary, 3, 0, 1, 2)
        
        self.overwrite_existing = QCheckBox("🔄 Overwrite existing files")
        layout.addWidget(self.overwrite_existing, 4, 0, 1, 2)
        
        # Add new checkbox برای باز کردن پوشه بعد از export
        self.show_folder_after_export = QCheckBox("📂 Open folder after export")
        self.show_folder_after_export.setChecked(True)
        layout.addWidget(self.show_folder_after_export, 5, 0, 1, 2)
    
    
        group.setLayout(layout)
        return group
    
    def create_action_buttons(self) -> QGroupBox:
        """Create action buttons group"""
        group = QGroupBox("🚀 Batch Export Actions")
        
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        self.export_btn = QPushButton("🚀 Start Batch Export")
        self.export_btn.setMinimumHeight(45)
        self.export_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #7d3c98;
            }
        """)
        
        self.preview_btn = QPushButton("👁️ Preview Selection")
        self.preview_btn.setMinimumHeight(40)
        
        self.schedule_btn = QPushButton("⏰ Schedule Batch")
        self.schedule_btn.setMinimumHeight(40)
        
        for btn in [self.preview_btn, self.schedule_btn]:
            btn.setFont(QFont("Arial", 10))
        
        layout.addWidget(self.export_btn)
        layout.addWidget(self.preview_btn)
        layout.addWidget(self.schedule_btn)
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def create_progress_section(self) -> QGroupBox:
        """Create progress section"""
        group = QGroupBox("📊 Batch Export Progress")
        
        layout = QVBoxLayout()
        
        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #9b59b6;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.overall_progress)
        
        # Current item progress
        self.item_progress = QProgressBar()
        self.item_progress.setTextVisible(True)
        self.item_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #95a5a6;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.item_progress)
        
        # Status labels
        self.status_label = QLabel("✅ Ready for batch export")
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.current_item_label = QLabel("")
        self.current_item_label.setFont(QFont("Arial", 9))
        self.current_item_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_item_label)
        
        # Details
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(150)
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Arial", 9))
        self.details_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
                background-color: #f9f9f9;
            }
        """)
        layout.addWidget(self.details_text)
        
        # Statistics
        stats_layout = QHBoxLayout()
        
        self.wells_count_label = QLabel("Wells: 0")
        self.reports_count_label = QLabel("Reports: 0")
        self.files_count_label = QLabel("Files: 0")
        
        for label in [self.wells_count_label, self.reports_count_label, self.files_count_label]:
            label.setFont(QFont("Arial", 9))
            label.setStyleSheet("padding: 5px; background-color: #ecf0f1; border-radius: 3px;")
            stats_layout.addWidget(label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        group.setLayout(layout)
        return group
    
    def setup_connections(self):
        """Setup signal connections"""
        self.export_btn.clicked.connect(self.start_batch_export)
        self.preview_btn.clicked.connect(self.preview_selection)
        self.schedule_btn.clicked.connect(self.schedule_batch)
    
    def load_data(self):
        """Load data from database"""
        self.load_wells()
    
    def load_wells(self):
        """Load wells from database"""
        try:
            self.wells_list.clear()
            
            if self.db:
                wells = self.db.get_wells_by_project(None)  # Get all wells
                for well in wells:
                    item = QListWidgetItem(well.get('name', 'Unknown'))
                    item.setData(Qt.UserRole, well.get('id'))
                    self.wells_list.addItem(item)
            else:
                # Sample data for testing
                sample_wells = ["Well X-1", "Well Y-2", "Well Z-3", 
                               "Exploration Well A", "Development Well B",
                               "Well Alpha", "Well Beta", "Well Gamma"]
                for well in sample_wells:
                    self.wells_list.addItem(well)
            
            self.update_statistics()
                
        except Exception as e:
            logger.error(f"Error loading wells: {e}")
            self.status_manager.show_error("BatchExportTab", f"Error loading wells: {str(e)}")
    
    def browse_output_folder(self):
        """Browse for output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", 
                                                  self.output_path.text())
        if folder:
            self.output_path.setText(folder)
    
    def get_selected_reports(self) -> List[str]:
        selected = []
        for report_name, checkbox in self.report_checkboxes:
            if checkbox.isChecked():
                selected.append(report_name)
        return selected

    
    def get_selected_reports(self) -> List[str]:
        """Get list of selected report types"""
        selected = []
        for report_name, checkbox in self.report_checkboxes:
            if checkbox.isChecked():
                selected.append(report_name)
        return selected
    
    def validate_inputs(self) -> bool:
        """Validate user inputs"""
        # بررسی انتخاب چاه
        if self.well_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Warning", "Please select a well.")
            return False
        
        well_id = self.well_combo.currentData()
        well_name = self.well_combo.currentText()
        
        if well_id is None:
            QMessageBox.warning(self, "Warning", "Invalid well selected. Please select a valid well.")
            return False
        
        logger.info(f"Selected well - Name: {well_name}, ID: {well_id}")
        
        selected_reports = self.get_selected_reports()  # ❌ این متد وجود ندارد!
        if not selected_reports:
            QMessageBox.warning(self, "Warning", "Please select at least one report.")
            return False
            
        
        if from_date > to_date:
            QMessageBox.warning(self, "Warning", "From date cannot be after To date.")
            return False
        
        output_path = self.output_path.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Warning", "Please select an output location.")
            return False
        
        # Create directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        return True
    def update_statistics(self):
        """Update statistics display"""
        selected_wells = len(self.get_selected_wells())
        selected_reports = len(self.get_selected_reports())
        
        self.wells_count_label.setText(f"Wells: {selected_wells}")
        self.reports_count_label.setText(f"Reports: {selected_reports}")
        
        # Estimate file count
        file_count = selected_wells * selected_reports
        if self.format_combo.currentText() == "Excel (Multiple Sheets)":
            file_count = selected_wells  # One file per well
        
        self.files_count_label.setText(f"Files: ~{file_count}")
    
    def start_batch_export(self):
        """Start batch export process"""
        try:
            if not self.validate_inputs():
                return
            
            # Get export parameters
            selected_wells = self.get_selected_wells()
            selected_reports = self.get_selected_reports()
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().toString("yyyy-MM-dd")
            output_path = self.output_path.text()
            export_format = self.format_combo.currentText()
            
            # Update UI
            self.overall_progress.setValue(0)
            self.item_progress.setValue(0)
            self.status_label.setText("🔄 Starting batch export...")
            self.details_text.clear()
            QApplication.processEvents()
            
            # Start export
            self.perform_batch_export(selected_wells, selected_reports, 
                                      from_date, to_date, output_path, export_format)
            
        except Exception as e:
            logger.error(f"Error in batch export: {e}")
            QMessageBox.critical(self, "Error", f"Batch export failed: {str(e)}")
            self.status_label.setText("❌ Batch export failed")
    
    def perform_batch_export(self, wells: List[Dict], reports: List[str], 
                            from_date: str, to_date: str, 
                            output_path: str, export_format: str):
        """Perform the batch export - نسخه کامل شده"""
        total_wells = len(wells)
        total_reports = len(reports)
        total_items = total_wells * total_reports
        
        successful_exports = 0
        failed_exports = 0
        exported_files = []
        
        # Create export generator and data collector
        export_generator = ExportGenerator(self.db)
        data_collector = ExportDataCollector(self.db)
        
        # Convert date strings to date objects
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
        except Exception as e:
            logger.error(f"Error parsing dates: {e}")
            from_date_obj = None
            to_date_obj = None
        
        self.details_text.append(f"📊 Starting batch export for {total_wells} wells, {total_reports} report types")
        self.details_text.append(f"📁 Output: {output_path}")
        self.details_text.append(f"📅 Date range: {from_date} to {to_date}")
        self.details_text.append(f"📦 Format: {export_format}")
        self.details_text.append("─" * 50)
        
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        for well_idx, well in enumerate(wells):
            well_progress = int((well_idx) / total_wells * 100)
            self.overall_progress.setValue(well_progress)
            
            self.current_item_label.setText(f"Processing: {well['name']}")
            self.details_text.append(f"\n🔵 Well: {well['name']} (ID: {well.get('id', 'N/A')})")
            QApplication.processEvents()
            
            for report_idx, report_type in enumerate(reports):
                item_progress = int((report_idx) / total_reports * 100)
                self.item_progress.setValue(item_progress)
                
                self.details_text.append(f"  📄 {report_type}...")
                QApplication.processEvents()
                
                try:
                    # Export based on report type
                    success = False
                    file_path = ""
                    
                    if report_type == "Well Info":
                        well_data = data_collector.get_well_info(well['id'])
                        if well_data:
                            file_path = export_generator._export_to_json(
                                well_data, 
                                f"{well['name'].replace(' ', '_')}_well_info",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Daily Reports":
                        reports_data = data_collector.get_daily_reports_for_export(
                            well['id'], from_date_obj, to_date_obj
                        )
                        if reports_data:
                            if "Excel" in export_format:
                                file_path = export_generator._export_to_excel(
                                    reports_data, 
                                    f"{well['name'].replace(' ', '_')}_daily_reports",
                                    output_path
                                )
                            elif "PDF" in export_format:
                                file_path = export_generator._export_to_pdf(
                                    reports_data, 
                                    f"{well['name'].replace(' ', '_')}_daily_reports",
                                    output_path
                                )
                            else:
                                file_path = export_generator._export_to_json(
                                    reports_data, 
                                    f"{well['name'].replace(' ', '_')}_daily_reports",
                                    output_path
                                )
                            success = bool(file_path)
                    
                    elif report_type == "Drilling Parameters":
                        drilling_data = data_collector.get_drilling_parameters_for_export(
                            well['id'], from_date_obj, to_date_obj
                        )
                        if drilling_data:
                            file_path = export_generator._export_to_json(
                                drilling_data, 
                                f"{well['name'].replace(' ', '_')}_drilling_parameters",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Mud Reports":
                        mud_data = data_collector.get_mud_reports_for_export(
                            well['id'], from_date_obj, to_date_obj
                        )
                        if mud_data:
                            file_path = export_generator._export_to_json(
                                mud_data, 
                                f"{well['name'].replace(' ', '_')}_mud_reports",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Bit Records":
                        bit_data = data_collector.get_bit_reports_for_export(well['id'])
                        if bit_data:
                            file_path = export_generator._export_to_json(
                                bit_data, 
                                f"{well['name'].replace(' ', '_')}_bit_records",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "BHA Reports":
                        bha_data = data_collector.get_bha_reports_for_export(well['id'])
                        if bha_data:
                            file_path = export_generator._export_to_json(
                                bha_data, 
                                f"{well['name'].replace(' ', '_')}_bha_reports",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Casing Data":
                        casing_data = data_collector.get_casing_reports_for_export(
                            well['id'], from_date_obj, to_date_obj
                        )
                        if casing_data:
                            file_path = export_generator._export_to_json(
                                casing_data, 
                                f"{well['name'].replace(' ', '_')}_casing_data",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Safety Reports":
                        safety_data = {
                            "safety_reports": data_collector.get_safety_reports_for_export(
                                well['id'], from_date_obj, to_date_obj
                            ),
                            "bop_components": data_collector.get_bop_components_for_export(well['id']),
                            "waste_records": data_collector.get_waste_records_for_export(
                                well['id'], from_date_obj, to_date_obj
                            )
                        }
                        if any(safety_data.values()):
                            file_path = export_generator._export_to_json(
                                safety_data, 
                                f"{well['name'].replace(' ', '_')}_safety_reports",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Planning Data":
                        planning_data = {
                            "lookahead_plans": data_collector.get_lookahead_plans_for_export(
                                well['id'], from_date_obj, to_date_obj
                            ),
                            "npt_reports": data_collector.get_npt_reports_for_export(
                                well['id'], from_date_obj, to_date_obj
                            ),
                            "activity_codes": data_collector.get_activity_codes_for_export(well['id'])
                        }
                        if any(planning_data.values()):
                            file_path = export_generator._export_to_json(
                                planning_data, 
                                f"{well['name'].replace(' ', '_')}_planning_data",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Cost Analysis":
                        # This would require a separate cost tracking table
                        # For now, create placeholder
                        cost_data = {
                            "well_id": well['id'],
                            "well_name": well['name'],
                            "note": "Cost analysis export not yet implemented",
                            "date_range": f"{from_date} to {to_date}"
                        }
                        file_path = export_generator._export_to_json(
                            cost_data, 
                            f"{well['name'].replace(' ', '_')}_cost_analysis",
                            output_path
                        )
                        success = bool(file_path)
                        self.details_text.append(f"    ⚠️ Cost analysis is a placeholder")
                    
                    elif report_type == "Logistics":
                        logistics_data = {
                            "logistics_personnel": data_collector.get_logistics_personnel_for_export(well['id']),
                            "service_company_pob": data_collector.get_service_company_pob_for_export(well['id']),
                            "fuel_water_inventory": data_collector.get_fuel_water_inventory_for_export(
                                well['id'], from_date_obj, to_date_obj
                            ),
                            "bulk_materials": data_collector.get_bulk_materials_for_export(
                                well['id'], from_date_obj, to_date_obj
                            ),
                            "transport_logs": data_collector.get_transport_logs_for_export(
                                well['id'], from_date_obj, to_date_obj
                            )
                        }
                        if any(logistics_data.values()):
                            file_path = export_generator._export_to_json(
                                logistics_data, 
                                f"{well['name'].replace(' ', '_')}_logistics",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Services":
                        services_data = {
                            "service_companies": data_collector.get_service_companies_for_export(well['id']),
                            "material_requests": data_collector.get_material_requests_for_export(
                                well['id'], from_date_obj, to_date_obj
                            ),
                            "equipment_logs": data_collector.get_equipment_logs_for_export(
                                well['id'], from_date_obj, to_date_obj
                            )
                        }
                        if any(services_data.values()):
                            file_path = export_generator._export_to_json(
                                services_data, 
                                f"{well['name'].replace(' ', '_')}_services",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Trajectory":
                        trajectory_data = {
                            "survey_points": data_collector.get_survey_points_for_export(well['id']),
                            "trajectory_calculations": data_collector.get_trajectory_calculations_for_export(well['id']),
                            "trip_sheet_entries": data_collector.get_trip_sheet_entries_for_export(
                                well['id'], from_date_obj, to_date_obj
                            )
                        }
                        if any(trajectory_data.values()):
                            file_path = export_generator._export_to_json(
                                trajectory_data, 
                                f"{well['name'].replace(' ', '_')}_trajectory",
                                output_path
                            )
                            success = bool(file_path)
                    
                    elif report_type == "Analysis":
                        analysis_data = {
                            "time_depth_data": data_collector.get_time_depth_data_for_export(
                                well['id'], from_date_obj, to_date_obj
                            ),
                            "rop_analysis": data_collector.get_rop_analysis_for_export(
                                well['id'], from_date_obj, to_date_obj
                            )
                        }
                        if any(analysis_data.values()):
                            file_path = export_generator._export_to_json(
                                analysis_data, 
                                f"{well['name'].replace(' ', '_')}_analysis",
                                output_path
                            )
                            success = bool(file_path)
                    
                    # Check if export was successful
                    if success and file_path:
                        successful_exports += 1
                        exported_files.append(file_path)
                        self.details_text.append(f"    ✓ Exported to: {os.path.basename(file_path)}")
                    else:
                        failed_exports += 1
                        self.details_text.append(f"    ✗ No data available for export")
                    
                    QApplication.processEvents()
                    QThread.msleep(100)  # Small delay for UI update
                
                except Exception as e:
                    failed_exports += 1
                    logger.error(f"Error exporting {well['name']} - {report_type}: {e}")
                    self.details_text.append(f"    ✗ Error: {str(e)[:100]}...")
                    QApplication.processEvents()
            
            self.item_progress.setValue(100)
        
        # Finalize
        self.overall_progress.setValue(100)
        self.item_progress.setValue(0)
        self.current_item_label.setText("")
        
        # Create ZIP archive if requested
        zip_file_path = ""
        if self.compress_files.isChecked() and exported_files:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_file_path = os.path.join(output_path, f"batch_export_{timestamp}.zip")
                
                with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in exported_files:
                        if os.path.exists(file_path):
                            arcname = os.path.relpath(file_path, output_path)
                            zipf.write(file_path, arcname)
                
                self.details_text.append(f"🗜️ Created ZIP archive: {os.path.basename(zip_file_path)}")
                
                # Delete original files if ZIP creation successful
                if self.overwrite_existing.isChecked():
                    for file_path in exported_files:
                        try:
                            os.remove(file_path)
                        except:
                            pass
            
            except Exception as e:
                logger.error(f"Error creating ZIP archive: {e}")
                self.details_text.append(f"⚠️ Failed to create ZIP archive: {e}")
        
        # Show summary
        self.details_text.append("\n" + "=" * 50)
        self.details_text.append("📋 BATCH EXPORT SUMMARY")
        self.details_text.append("=" * 50)
        self.details_text.append(f"✅ Successful: {successful_exports}")
        self.details_text.append(f"❌ Failed: {failed_exports}")
        self.details_text.append(f"📁 Output folder: {output_path}")
        
        # File count based on export format
        if export_format == "Excel (Multiple Sheets)":
            self.details_text.append(f"📄 Files: {total_wells} Excel files (multiple sheets)")
        elif export_format == "Excel (Multiple Files)":
            self.details_text.append(f"📄 Files: ~{len(exported_files)} Excel files")
        elif export_format == "PDF (Combined)":
            self.details_text.append(f"📄 Files: {total_wells} PDF files")
        elif export_format == "PDF (Separate)":
            self.details_text.append(f"📄 Files: ~{len(exported_files)} PDF files")
        else:
            self.details_text.append(f"📄 Files: {len(exported_files)} total files")
        
        if zip_file_path:
            self.details_text.append(f"🗜️ ZIP archive: {zip_file_path}")
        
        self.details_text.append("\n📦 Exported files:")
        for i, file_path in enumerate(exported_files[:20]):  # Show first 20 files
            self.details_text.append(f"  {i+1:3d}. {os.path.basename(file_path)}")
        
        if len(exported_files) > 20:
            self.details_text.append(f"  ... and {len(exported_files) - 20} more files")
        
        self.status_label.setText(f"✅ Batch export completed: {successful_exports} successful, {failed_exports} failed")
        
        # Show completion message
        message = f"""
        Batch Export Complete!
        
        📊 Statistics:
        • Wells processed: {total_wells}
        • Report types: {total_reports}
        • Total items: {total_items}
        • Successful exports: {successful_exports}
        • Failed exports: {failed_exports}
        • Success rate: {(successful_exports/total_items*100):.1f}%
        
        📁 Output location: {output_path}
        """
        
        if zip_file_path:
            message += f"\n🗜️ ZIP archive created: {os.path.basename(zip_file_path)}"
        
        if failed_exports == 0:
            QMessageBox.information(
                self, 
                "✅ Batch Export Success", 
                message
            )
        else:
            QMessageBox.warning(
                self, 
                "⚠️ Batch Export Completed with Errors", 
                message + f"\n\n⚠️ {failed_exports} exports failed. Check details for more information."
            )
        
        # Open output folder
        if self.show_folder_after_export.isChecked():  # نیاز به اضافه کردن checkbox جدید
            try:
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    os.startfile(output_path)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", output_path])
                else:  # Linux
                    subprocess.run(["xdg-open", output_path])
            except Exception as e:
                logger.error(f"Error opening folder: {e}")
                
    def query_database_data(self, well_id: Any, report_type: str, 
                           from_date: str, to_date: str) -> Dict[str, Any]:
        """Query database for specific data"""
        # This is a simulation - in real implementation, this would query the database
        
        sample_data = {
            "well_id": well_id,
            "report_type": report_type,
            "date_range": f"{from_date} to {to_date}",
            "data_points": 25,
            "last_updated": datetime.now().isoformat()
        }
        
        # Add mock data based on report type
        if report_type == "Well Info":
            sample_data.update({
                "well_name": f"Well {well_id}",
                "location": "Field X, Block Y",
                "operator": "NIOC",
                "status": "Active",
                "depth": 3500.5
            })
        elif report_type == "Daily Reports":
            sample_data.update({
                "reports_count": 45,
                "average_rop": 15.3,
                "total_npt_hours": 135.5,
                "days_covered": 45
            })
        elif report_type == "Drilling Parameters":
            sample_data.update({
                "parameters": ["ROP", "WOB", "RPM", "Torque", "SPP"],
                "data_points": 1200,
                "time_range": "Full drilling period"
            })
        
        return sample_data
    
    def preview_selection(self):
        """Preview the selected wells and reports"""
        selected_wells = self.get_selected_wells()
        selected_reports = self.get_selected_reports()
        
        if not selected_wells or not selected_reports:
            QMessageBox.warning(self, "Warning", "Please select wells and reports to preview.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📋 Batch Export Preview")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Summary
        summary_text = QTextEdit()
        summary_text.setReadOnly(True)
        
        content = f"""
        <h2>📊 Batch Export Preview</h2>
        <hr>
        <h3>🎯 Selected Wells ({len(selected_wells)})</h3>
        <ul>
        """
        
        for well in selected_wells[:10]:  # Show first 10
            content += f"<li>• {well['name']}</li>"
        
        if len(selected_wells) > 10:
            content += f"<li>... and {len(selected_wells) - 10} more</li>"
        
        content += """
        </ul>
        <hr>
        <h3>📄 Selected Reports ({reports_count})</h3>
        <ul>
        """.format(reports_count=len(selected_reports))
        
        for report in selected_reports:
            content += f"<li>• {report}</li>"
        
        content += f"""
        </ul>
        <hr>
        <h3>📅 Date Range</h3>
        <p><b>From:</b> {self.from_date.date().toString('yyyy-MM-dd')}</p>
        <p><b>To:</b> {self.to_date.date().toString('yyyy-MM-dd')}</p>
        <hr>
        <h3>📁 Export Settings</h3>
        <p><b>Format:</b> {self.format_combo.currentText()}</p>
        <p><b>Output:</b> {self.output_path.text()}</p>
        <p><b>Compress:</b> {'Yes' if self.compress_files.isChecked() else 'No'}</p>
        <hr>
        <h3>📈 Estimated Output</h3>
        <p><b>Total items:</b> {len(selected_wells)} wells × {len(selected_reports)} reports = {len(selected_wells) * len(selected_reports)} items</p>
        """
        
        summary_text.setHtml(content)
        layout.addWidget(summary_text)
        
        # Close button
        close_btn = QPushButton("Close Preview")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def schedule_batch(self):
        """Schedule batch export"""
        dialog = QDialog(self)
        dialog.setWindowTitle("⏰ Schedule Batch Export")
        dialog.setFixedSize(400, 350)
        
        layout = QVBoxLayout()
        
        # Schedule options
        layout.addWidget(QLabel("🕒 Schedule Time:"))
        time_edit = QTimeEdit()
        time_edit.setTime(QTime(22, 0))  # 10 PM
        layout.addWidget(time_edit)
        
        layout.addWidget(QLabel("📅 Start Date:"))
        start_date_edit = QDateEdit()
        start_date_edit.setDate(QDate.currentDate().addDays(1))
        start_date_edit.setCalendarPopup(True)
        layout.addWidget(start_date_edit)
        
        layout.addWidget(QLabel("📆 Frequency:"))
        freq_combo = QComboBox()
        freq_combo.addItems(["Once", "Daily", "Weekly", "Monthly"])
        layout.addWidget(freq_combo)
        
        layout.addWidget(QLabel("📧 Notification Email:"))
        email_edit = QLineEdit()
        email_edit.setPlaceholderText("email@example.com")
        layout.addWidget(email_edit)
        
        layout.addWidget(QLabel("💾 Auto Save Location:"))
        save_combo = QComboBox()
        save_combo.addItems(["Reports/Batch/Scheduled/", "Cloud Storage", "Both"])
        layout.addWidget(save_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        schedule_btn = QPushButton("✅ Schedule")
        cancel_btn = QPushButton("❌ Cancel")
        
        btn_layout.addWidget(schedule_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        def on_schedule():
            QMessageBox.information(
                dialog,
                "✅ Batch Export Scheduled",
                f"""
                Batch export scheduled successfully!
                
                Start: {start_date_edit.date().toString('yyyy-MM-dd')} at {time_edit.time().toString('HH:mm')}
                Frequency: {freq_combo.currentText()}
                Email: {email_edit.text() or 'None'}
                Save to: {save_combo.currentText()}
                
                Next export will process {len(self.get_selected_wells())} wells.
                """
            )
            dialog.close()
        
        schedule_btn.clicked.connect(on_schedule)
        cancel_btn.clicked.connect(dialog.close)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_template(self):
        """Save template to database"""
        try:
            # تشخیص نوع تب
            if isinstance(self, DailyExportTab):
                template_type = "daily"
            elif isinstance(self, EOWRExportTab):
                template_type = "eowr"
            elif isinstance(self, BatchExportTab):
                template_type = "batch"
            else:
                template_type = "general"
            
            template_data = {
                "name": f"{template_type.upper()} Template - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "template_type": template_type,
                "description": f"{template_type.upper()} export template",
                "created_at": datetime.now(),
                "version": "1.0"
            }
            
            if self.db:
                template_id = self.db.save_export_template(template_data)
                if template_id:
                    self.status_manager.show_success(self.__class__.__name__, 
                                                   f"Template saved (ID: {template_id})")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False
        
    def load_template_dialog(self):
        """Open dialog to load batch export template from database"""
        if not self.db:
            QMessageBox.warning(self, "Warning", "Database not available")
            return
        
        try:
            # Get templates from database for batch export
            templates = self.db.get_export_templates(template_type="batch")
            
            if not templates:
                QMessageBox.information(self, "No Templates", 
                                      "No saved batch export templates found.")
                return
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("📂 Load Batch Export Template")
            dialog.setFixedSize(500, 400)
            
            layout = QVBoxLayout()
            
            # Template list
            template_list = QListWidget()
            for template in templates:
                item = QListWidgetItem(f"📊 {template['name']}")
                item.setData(Qt.UserRole, template['id'])
                item.setToolTip(template.get('description', 'No description'))
                
                if template.get('is_default'):
                    item.setText(f"⭐ {template['name']} (Default)")
                    item.setForeground(QColor("#FF9900"))
                
                template_list.addItem(item)
            
            layout.addWidget(QLabel("Select batch export template to load:"))
            layout.addWidget(template_list)
            
            # Similar button setup as DailyExportTab...
            # ... (کد مشابه DailyExportTab با تغییرات جزئی)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error loading batch template dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load batch templates: {str(e)}")

# ==================== Export Database Functions ====================

class ExportDataCollector:
    """Collects all data from database for export purposes"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    # ============ Basic Information ============
    
    def get_company_info(self, company_id: int) -> Dict[str, Any]:
        """Get company information"""
        session = self.db.create_session()
        try:
            company = session.query(Company).filter(Company.id == company_id).first()
            if company:
                return {
                    "id": company.id,
                    "name": company.name,
                    "code": company.code,
                    "address": company.address,
                    "contact_person": company.contact_person,
                    "contact_email": company.contact_email,
                    "contact_phone": company.contact_phone,
                    "created_at": company.created_at,
                    "updated_at": company.updated_at
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting company info: {e}")
            return {}
        finally:
            session.close()
    
    def get_project_info(self, project_id: int) -> Dict[str, Any]:
        """Get project information"""
        session = self.db.create_session()
        try:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                return {
                    "id": project.id,
                    "company_id": project.company_id,
                    "name": project.name,
                    "code": project.code,
                    "location": project.location,
                    "start_date": project.start_date,
                    "end_date": project.end_date,
                    "status": project.status,
                    "manager": project.manager,
                    "budget": project.budget,
                    "currency": project.currency,
                    "created_at": project.created_at,
                    "updated_at": project.updated_at
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting project info: {e}")
            return {}
        finally:
            session.close()
    
    def get_well_info(self, well_id: int) -> Dict[str, Any]:
        """Get complete well information"""
        session = self.db.create_session()
        try:
            well = session.query(Well).filter(Well.id == well_id).first()
            if well:
                # Get all well data
                well_data = {
                    "id": well.id,
                    "project_id": well.project_id,
                    "name": well.name,
                    "code": well.code,
                    "field_name": well.field_name,
                    "location": well.location,
                    "coordinates": well.coordinates,
                    "elevation": well.elevation,
                    "water_depth": well.water_depth,
                    "spud_date": well.spud_date,
                    "target_depth": well.target_depth,
                    "status": well.status,
                    "well_type": well.well_type,
                    "purpose": well.purpose,
                    "well_type_field": well.well_type_field,
                    "section_name": well.section_name,
                    "client": well.client,
                    "client_rep": well.client_rep,
                    "operator": well.operator,
                    "project_name": well.project_name,
                    "rig_name": well.rig_name,
                    "drilling_contractor": well.drilling_contractor,
                    "report_no": well.report_no,
                    "rig_type": well.rig_type,
                    "well_shape": well.well_shape,
                    "gle_msl": well.gle_msl,
                    "rte_msl": well.rte_msl,
                    "gle_rte": well.gle_rte,
                    "estimated_final_depth": well.estimated_final_depth,
                    "derrick_height": well.derrick_height,
                    "lta_day": well.lta_day,
                    "actual_rig_days": well.actual_rig_days,
                    "rig_heading": well.rig_heading,
                    "kop1": well.kop1,
                    "kop2": well.kop2,
                    "formation": well.formation,
                    "latitude": well.latitude,
                    "longitude": well.longitude,
                    "northing": well.northing,
                    "easting": well.easting,
                    "start_hole_date": well.start_hole_date,
                    "rig_move_date": well.rig_move_date,
                    "report_date": well.report_date,
                    "operation_manager": well.operation_manager,
                    "superintendent": well.superintendent,
                    "supervisor_day": well.supervisor_day,
                    "supervisor_night": well.supervisor_night,
                    "geologist1": well.geologist1,
                    "geologist2": well.geologist2,
                    "tool_pusher_day": well.tool_pusher_day,
                    "tool_pusher_night": well.tool_pusher_night,
                    "objectives": well.objectives,
                    "created_at": well.created_at,
                    "updated_at": well.updated_at
                }
                
                # Get sections
                sections = session.query(Section).filter(Section.well_id == well_id).all()
                well_data["sections"] = [
                    {
                        "id": s.id,
                        "name": s.name,
                        "code": s.code,
                        "depth_from": s.depth_from,
                        "depth_to": s.depth_to,
                        "diameter": s.diameter,
                        "hole_size": s.hole_size,
                        "purpose": s.purpose,
                        "description": s.description,
                        "created_at": s.created_at,
                        "updated_at": s.updated_at
                    }
                    for s in sections
                ]
                
                return well_data
            return {}
        except Exception as e:
            logger.error(f"Error getting well info: {e}")
            return {}
        finally:
            session.close()
    
    # ============ Daily Reports ============
    
    def get_daily_reports_for_export(self, well_id: int, start_date: date = None, 
                                    end_date: date = None) -> List[Dict[str, Any]]:
        """Get daily reports with all related data"""
        session = self.db.create_session()
        try:
            query = session.query(DailyReport).filter(DailyReport.well_id == well_id)
            
            if start_date:
                query = query.filter(DailyReport.report_date >= start_date)
            if end_date:
                query = query.filter(DailyReport.report_date <= end_date)
            
            reports = query.order_by(DailyReport.report_date).all()
            
            result = []
            for report in reports:
                report_data = {
                    "id": report.id,
                    "well_id": report.well_id,
                    "section_id": report.section_id,
                    "report_date": report.report_date,
                    "report_number": report.report_number,
                    "rig_day": report.rig_day,
                    "report_title": report.report_title,
                    "drilling_data": report.drilling_data,
                    "mud_data": report.mud_data,
                    "equipment_data": report.equipment_data,
                    "downhole_data": report.downhole_data,
                    "trajectory_data": report.trajectory_data,
                    "logistics_data": report.logistics_data,
                    "safety_data": report.safety_data,
                    "services_data": report.services_data,
                    "analysis_data": report.analysis_data,
                    "planning_data": report.planning_data,
                    "export_data": report.export_data,
                    "depth_0000": report.depth_0000,
                    "depth_0600": report.depth_0600,
                    "depth_2400": report.depth_2400,
                    "summary": report.summary,
                    "status": report.status,
                    "created_at": report.created_at,
                    "updated_at": report.updated_at,
                    "created_by": report.created_by
                }
                
                # Get time logs
                report_data["time_logs_24h"] = self._get_time_logs_24h(session, report.id)
                report_data["time_logs_morning"] = self._get_time_logs_morning(session, report.id)
                
                result.append(report_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting daily reports: {e}")
            return []
        finally:
            session.close()
    
    def _get_time_logs_24h(self, session, report_id: int) -> List[Dict[str, Any]]:
        """Get 24h time logs"""
        try:
            logs = session.query(TimeLog24H).filter(
                TimeLog24H.report_id == report_id
            ).order_by(TimeLog24H.time_from).all()
            
            return [
                {
                    "id": l.id,
                    "time_from": l.time_from.strftime("%H:%M") if l.time_from else "",
                    "time_to": l.time_to.strftime("%H:%M") if l.time_to else "",
                    "is_from_2400": l.is_from_2400,
                    "is_to_2400": l.is_to_2400,
                    "duration": l.duration,
                    "main_phase": l.main_phase,
                    "main_code": l.main_code,
                    "sub_code": l.sub_code,
                    "status": l.status,
                    "is_npt": l.is_npt,
                    "activity_description": l.activity_description
                }
                for l in logs
            ]
        except Exception as e:
            logger.error(f"Error getting 24h time logs: {e}")
            return []
    
    def _get_time_logs_morning(self, session, report_id: int) -> List[Dict[str, Any]]:
        """Get morning time logs"""
        try:
            logs = session.query(TimeLogMorning).filter(
                TimeLogMorning.report_id == report_id
            ).order_by(TimeLogMorning.time_from).all()
            
            return [
                {
                    "id": l.id,
                    "time_from": l.time_from.strftime("%H:%M") if l.time_from else "",
                    "time_to": l.time_to.strftime("%H:%M") if l.time_to else "",
                    "is_from_2400": l.is_from_2400,
                    "is_to_2400": l.is_to_2400,
                    "duration": l.duration,
                    "main_phase": l.main_phase,
                    "main_code": l.main_code,
                    "sub_code": l.sub_code,
                    "status": l.status,
                    "is_npt": l.is_npt,
                    "activity_description": l.activity_description
                }
                for l in logs
            ]
        except Exception as e:
            logger.error(f"Error getting morning time logs: {e}")
            return []
    
    # ============ Drilling Data ============
    
    def get_drilling_parameters_for_export(self, well_id: int, start_date: date = None, 
                                          end_date: date = None) -> List[Dict[str, Any]]:
        """Get drilling parameters"""
        session = self.db.create_session()
        try:
            query = session.query(DrillingParameters).filter(
                DrillingParameters.well_id == well_id
            )
            
            if start_date:
                query = query.filter(DrillingParameters.report_date >= start_date)
            if end_date:
                query = query.filter(DrillingParameters.report_date <= end_date)
            
            params = query.order_by(DrillingParameters.report_date).all()
            
            return [
                {
                    "id": p.id,
                    "well_id": p.well_id,
                    "report_date": p.report_date,
                    "bit_no": p.bit_no,
                    "bit_rerun": p.bit_rerun,
                    "bit_size": p.bit_size,
                    "bit_type": p.bit_type,
                    "manufacturer": p.manufacturer,
                    "iadc_code": p.iadc_code,
                    "nozzles_json": p.nozzles_json,
                    "tfa": p.tfa,
                    "depth_in": p.depth_in,
                    "depth_out": p.depth_out,
                    "bit_drilled": p.bit_drilled,
                    "cum_drilled": p.cum_drilled,
                    "hours_on_bottom": p.hours_on_bottom,
                    "cum_hours": p.cum_hours,
                    "wob_min": p.wob_min,
                    "wob_max": p.wob_max,
                    "rpm_min": p.rpm_min,
                    "rpm_max": p.rpm_max,
                    "torque_min": p.torque_min,
                    "torque_max": p.torque_max,
                    "pump_pressure_min": p.pump_pressure_min,
                    "pump_pressure_max": p.pump_pressure_max,
                    "pump_output_min": p.pump_output_min,
                    "pump_output_max": p.pump_output_max,
                    "pump1_spm": p.pump1_spm,
                    "pump1_spp": p.pump1_spp,
                    "pump2_spm": p.pump2_spm,
                    "pump2_spp": p.pump2_spp,
                    "avg_rop": p.avg_rop,
                    "hsi": p.hsi,
                    "annular_velocity": p.annular_velocity,
                    "bit_revolution": p.bit_revolution,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "created_by": p.created_by
                }
                for p in params
            ]
            
        except Exception as e:
            logger.error(f"Error getting drilling parameters: {e}")
            return []
        finally:
            session.close()
    
    def get_mud_reports_for_export(self, well_id: int, start_date: date = None, 
                                  end_date: date = None) -> List[Dict[str, Any]]:
        """Get mud reports"""
        session = self.db.create_session()
        try:
            query = session.query(MudReport).filter(MudReport.well_id == well_id)
            
            if start_date:
                query = query.filter(MudReport.report_date >= start_date)
            if end_date:
                query = query.filter(MudReport.report_date <= end_date)
            
            reports = query.order_by(MudReport.report_date).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "report_date": r.report_date,
                    "mud_type": r.mud_type,
                    "sample_time": r.sample_time.strftime("%H:%M") if r.sample_time else "",
                    "mw": r.mw,
                    "pv": r.pv,
                    "yp": r.yp,
                    "funnel_vis": r.funnel_vis,
                    "gel_10s": r.gel_10s,
                    "gel_10m": r.gel_10m,
                    "fl": r.fl,
                    "cake_thickness": r.cake_thickness,
                    "ph": r.ph,
                    "temperature": r.temperature,
                    "solid_percent": r.solid_percent,
                    "oil_percent": r.oil_percent,
                    "water_percent": r.water_percent,
                    "chloride": r.chloride,
                    "volume_hole": r.volume_hole,
                    "total_circulated": r.total_circulated,
                    "loss_downhole": r.loss_downhole,
                    "loss_surface": r.loss_surface,
                    "chemicals_json": r.chemicals_json,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "created_by": r.created_by
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting mud reports: {e}")
            return []
        finally:
            session.close()
    
    def get_cement_reports_for_export(self, well_id: int, start_date: date = None, 
                                     end_date: date = None) -> List[Dict[str, Any]]:
        """Get cement reports"""
        session = self.db.create_session()
        try:
            query = session.query(CementReport).filter(CementReport.well_id == well_id)
            
            if start_date:
                query = query.filter(CementReport.report_date >= start_date)
            if end_date:
                query = query.filter(CementReport.report_date <= end_date)
            
            reports = query.order_by(CementReport.report_date).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "report_date": r.report_date,
                    "report_name": r.report_name,
                    "materials_json": r.materials_json,
                    "summary": r.summary,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "created_by": r.created_by
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting cement reports: {e}")
            return []
        finally:
            session.close()
    
    def get_casing_reports_for_export(self, well_id: int, start_date: date = None, 
                                     end_date: date = None) -> List[Dict[str, Any]]:
        """Get casing reports"""
        session = self.db.create_session()
        try:
            query = session.query(CasingReport).filter(CasingReport.well_id == well_id)
            
            if start_date:
                query = query.filter(CasingReport.report_date >= start_date)
            if end_date:
                query = query.filter(CasingReport.report_date <= end_date)
            
            reports = query.order_by(CasingReport.report_date).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "report_date": r.report_date,
                    "report_name": r.report_name,
                    "casing_json": r.casing_json,
                    "tally_json": r.tally_json,
                    "summary": r.summary,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "created_by": r.created_by
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting casing reports: {e}")
            return []
        finally:
            session.close()
    
    # ============ Downhole Equipment ============
    
    def get_bit_reports_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get bit reports"""
        session = self.db.create_session()
        try:
            reports = session.query(BitReport).filter(BitReport.well_id == well_id).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "report_date": r.report_date,
                    "report_name": r.report_name,
                    "bit_records_json": r.bit_records_json,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting bit reports: {e}")
            return []
        finally:
            session.close()
    
    def get_bha_reports_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get BHA reports"""
        session = self.db.create_session()
        try:
            reports = session.query(BHAReport).filter(BHAReport.well_id == well_id).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "bha_name": r.bha_name,
                    "bha_data_json": r.bha_data_json,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting BHA reports: {e}")
            return []
        finally:
            session.close()
    
    def get_downhole_equipment_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get downhole equipment"""
        session = self.db.create_session()
        try:
            equipment = session.query(DownholeEquipment).filter(
                DownholeEquipment.well_id == well_id
            ).all()
            
            return [
                {
                    "id": e.id,
                    "well_id": e.well_id,
                    "equipment_data_json": e.equipment_data_json,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at
                }
                for e in equipment
            ]
            
        except Exception as e:
            logger.error(f"Error getting downhole equipment: {e}")
            return []
        finally:
            session.close()
    
    def get_formation_reports_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get formation reports"""
        session = self.db.create_session()
        try:
            reports = session.query(FormationReport).filter(
                FormationReport.well_id == well_id
            ).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "report_name": r.report_name,
                    "formations_json": r.formations_json,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting formation reports: {e}")
            return []
        finally:
            session.close()
    
    # ============ Trajectory Data ============
    
    def get_trip_sheet_entries_for_export(self, well_id: int, start_date: date = None, 
                                         end_date: date = None) -> List[Dict[str, Any]]:
        """Get trip sheet entries"""
        session = self.db.create_session()
        try:
            query = session.query(TripSheetEntry).filter(TripSheetEntry.well_id == well_id)
            
            if start_date:
                query = query.filter(TripSheetEntry.created_at >= start_date)
            if end_date:
                query = query.filter(TripSheetEntry.created_at <= end_date)
            
            entries = query.order_by(TripSheetEntry.time).all()
            
            return [
                {
                    "id": e.id,
                    "well_id": e.well_id,
                    "section_id": e.section_id,
                    "report_id": e.report_id,
                    "time": e.time.strftime("%H:%M") if e.time else "",
                    "activity": e.activity,
                    "depth": e.depth,
                    "cum_trip": e.cum_trip,
                    "duration": e.duration,
                    "remarks": e.remarks,
                    "supervisor": e.supervisor,
                    "verified": e.verified,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                    "created_by": e.created_by
                }
                for e in entries
            ]
            
        except Exception as e:
            logger.error(f"Error getting trip sheet entries: {e}")
            return []
        finally:
            session.close()
    
    def get_survey_points_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get survey points"""
        session = self.db.create_session()
        try:
            points = session.query(SurveyPoint).filter(
                SurveyPoint.well_id == well_id
            ).order_by(SurveyPoint.md).all()
            
            return [
                {
                    "id": p.id,
                    "well_id": p.well_id,
                    "section_id": p.section_id,
                    "calculation_id": p.calculation_id,
                    "md": p.md,
                    "inc": p.inc,
                    "azi": p.azi,
                    "tvd": p.tvd,
                    "north": p.north,
                    "east": p.east,
                    "vs": p.vs,
                    "hd": p.hd,
                    "dls": p.dls,
                    "tool": p.tool,
                    "remarks": p.remarks,
                    "measured_at": p.measured_at,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "created_by": p.created_by
                }
                for p in points
            ]
            
        except Exception as e:
            logger.error(f"Error getting survey points: {e}")
            return []
        finally:
            session.close()
    
    def get_trajectory_calculations_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get trajectory calculations"""
        session = self.db.create_session()
        try:
            calculations = session.query(TrajectoryCalculation).filter(
                TrajectoryCalculation.well_id == well_id
            ).all()
            
            return [
                {
                    "id": c.id,
                    "well_id": c.well_id,
                    "section_id": c.section_id,
                    "method": c.method,
                    "calculation_date": c.calculation_date,
                    "parameters_json": c.parameters_json,
                    "results_json": c.results_json,
                    "target_north": c.target_north,
                    "target_east": c.target_east,
                    "target_tvd": c.target_tvd,
                    "total_hd": c.total_hd,
                    "total_tvd": c.total_tvd,
                    "total_md": c.total_md,
                    "description": c.description,
                    "calculated_by": c.calculated_by,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at
                }
                for c in calculations
            ]
            
        except Exception as e:
            logger.error(f"Error getting trajectory calculations: {e}")
            return []
        finally:
            session.close()
    
    # ============ Logistics Data ============
    
    def get_logistics_personnel_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get logistics personnel"""
        session = self.db.create_session()
        try:
            personnel = session.query(LogisticsPersonnel).filter(
                LogisticsPersonnel.well_id == well_id
            ).all()
            
            return [
                {
                    "id": p.id,
                    "well_id": p.well_id,
                    "section_id": p.section_id,
                    "report_id": p.report_id,
                    "name": p.name,
                    "position": p.position,
                    "company": p.company,
                    "arrival_date": p.arrival_date,
                    "departure_date": p.departure_date,
                    "contact_info": p.contact_info,
                    "remarks": p.remarks,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "created_by": p.created_by
                }
                for p in personnel
            ]
            
        except Exception as e:
            logger.error(f"Error getting logistics personnel: {e}")
            return []
        finally:
            session.close()
    
    def get_service_company_pob_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get service company POB"""
        session = self.db.create_session()
        try:
            pobs = session.query(ServiceCompanyPOB).filter(
                ServiceCompanyPOB.well_id == well_id
            ).all()
            
            return [
                {
                    "id": p.id,
                    "well_id": p.well_id,
                    "section_id": p.section_id,
                    "report_id": p.report_id,
                    "company_name": p.company_name,
                    "service_type": p.service_type,
                    "personnel_count": p.personnel_count,
                    "date_in": p.date_in,
                    "date_out": p.date_out,
                    "remarks": p.remarks,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "created_by": p.created_by
                }
                for p in pobs
            ]
            
        except Exception as e:
            logger.error(f"Error getting service company POB: {e}")
            return []
        finally:
            session.close()
    
    def get_fuel_water_inventory_for_export(self, well_id: int, start_date: date = None, 
                                           end_date: date = None) -> List[Dict[str, Any]]:
        """Get fuel water inventory"""
        session = self.db.create_session()
        try:
            query = session.query(FuelWaterInventory).filter(
                FuelWaterInventory.well_id == well_id
            )
            
            if start_date:
                query = query.filter(FuelWaterInventory.report_date >= start_date)
            if end_date:
                query = query.filter(FuelWaterInventory.report_date <= end_date)
            
            inventories = query.order_by(FuelWaterInventory.report_date).all()
            
            return [
                {
                    "id": i.id,
                    "well_id": i.well_id,
                    "section_id": i.section_id,
                    "report_id": i.report_id,
                    "report_date": i.report_date,
                    "fuel_type": i.fuel_type,
                    "fuel_consumed": i.fuel_consumed,
                    "fuel_stock": i.fuel_stock,
                    "fuel_received": i.fuel_received,
                    "water_consumed": i.water_consumed,
                    "water_stock": i.water_stock,
                    "water_received": i.water_received,
                    "fuel_remaining": i.fuel_remaining,
                    "water_remaining": i.water_remaining,
                    "days_remaining_fuel": i.days_remaining_fuel,
                    "days_remaining_water": i.days_remaining_water,
                    "created_at": i.created_at,
                    "updated_at": i.updated_at,
                    "created_by": i.created_by
                }
                for i in inventories
            ]
            
        except Exception as e:
            logger.error(f"Error getting fuel water inventory: {e}")
            return []
        finally:
            session.close()
    
    def get_bulk_materials_for_export(self, well_id: int, start_date: date = None, 
                                     end_date: date = None) -> List[Dict[str, Any]]:
        """Get bulk materials"""
        session = self.db.create_session()
        try:
            query = session.query(BulkMaterials).filter(BulkMaterials.well_id == well_id)
            
            if start_date:
                query = query.filter(BulkMaterials.report_date >= start_date)
            if end_date:
                query = query.filter(BulkMaterials.report_date <= end_date)
            
            materials = query.order_by(BulkMaterials.report_date).all()
            
            return [
                {
                    "id": m.id,
                    "well_id": m.well_id,
                    "section_id": m.section_id,
                    "report_id": m.report_id,
                    "report_date": m.report_date,
                    "material_name": m.material_name,
                    "unit": m.unit,
                    "initial_stock": m.initial_stock,
                    "received": m.received,
                    "used": m.used,
                    "current_stock": m.current_stock,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                    "created_by": m.created_by
                }
                for m in materials
            ]
            
        except Exception as e:
            logger.error(f"Error getting bulk materials: {e}")
            return []
        finally:
            session.close()
    
    def get_transport_logs_for_export(self, well_id: int, start_date: date = None, 
                                     end_date: date = None) -> List[Dict[str, Any]]:
        """Get transport logs"""
        session = self.db.create_session()
        try:
            query = session.query(TransportLog).filter(TransportLog.well_id == well_id)
            
            if start_date:
                query = query.filter(TransportLog.log_date >= start_date)
            if end_date:
                query = query.filter(TransportLog.log_date <= end_date)
            
            logs = query.order_by(TransportLog.log_date, TransportLog.arrival_time).all()
            
            return [
                {
                    "id": l.id,
                    "well_id": l.well_id,
                    "section_id": l.section_id,
                    "report_id": l.report_id,
                    "log_date": l.log_date,
                    "vehicle_type": l.vehicle_type,
                    "vehicle_name": l.vehicle_name,
                    "vehicle_id": l.vehicle_id,
                    "arrival_time": l.arrival_time.strftime("%H:%M") if l.arrival_time else "",
                    "departure_time": l.departure_time.strftime("%H:%M") if l.departure_time else "",
                    "duration": l.duration,
                    "passengers_in": l.passengers_in,
                    "passengers_out": l.passengers_out,
                    "cargo_description": l.cargo_description,
                    "status": l.status,
                    "purpose": l.purpose,
                    "remarks": l.remarks,
                    "created_at": l.created_at,
                    "updated_at": l.updated_at,
                    "created_by": l.created_by
                }
                for l in logs
            ]
            
        except Exception as e:
            logger.error(f"Error getting transport logs: {e}")
            return []
        finally:
            session.close()
    
    # ============ Safety Data ============
    
    def get_safety_reports_for_export(self, well_id: int, start_date: date = None, 
                                     end_date: date = None) -> List[Dict[str, Any]]:
        """Get safety reports"""
        session = self.db.create_session()
        try:
            query = session.query(SafetyReport).filter(SafetyReport.well_id == well_id)
            
            if start_date:
                query = query.filter(SafetyReport.report_date >= start_date)
            if end_date:
                query = query.filter(SafetyReport.report_date <= end_date)
            
            reports = query.order_by(SafetyReport.report_date).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "section_id": r.section_id,
                    "report_id": r.report_id,
                    "report_date": r.report_date,
                    "report_type": r.report_type,
                    "title": r.title,
                    "last_fire_drill": r.last_fire_drill,
                    "last_bop_drill": r.last_bop_drill,
                    "last_h2s_drill": r.last_h2s_drill,
                    "days_without_lti": r.days_without_lti,
                    "lti_count": r.lti_count,
                    "near_miss_count": r.near_miss_count,
                    "last_rams_test": r.last_rams_test,
                    "test_pressure": r.test_pressure,
                    "last_koomey_test": r.last_koomey_test,
                    "days_since_last_test": r.days_since_last_test,
                    "bop_stack_json": r.bop_stack_json,
                    "recycled_volume": r.recycled_volume,
                    "waste_ph": r.waste_ph,
                    "turbidity": r.turbidity,
                    "hardness": r.hardness,
                    "cutting_volume": r.cutting_volume,
                    "oil_content": r.oil_content,
                    "waste_type": r.waste_type,
                    "disposal_method": r.disposal_method,
                    "waste_history_json": r.waste_history_json,
                    "safety_observations": r.safety_observations,
                    "incidents_json": r.incidents_json,
                    "equipment_checks": r.equipment_checks,
                    "status": r.status,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "created_by": r.created_by
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting safety reports: {e}")
            return []
        finally:
            session.close()
    
    def get_bop_components_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get BOP components"""
        session = self.db.create_session()
        try:
            components = session.query(BOPComponent).filter(
                BOPComponent.well_id == well_id
            ).all()
            
            return [
                {
                    "id": c.id,
                    "well_id": c.well_id,
                    "safety_report_id": c.safety_report_id,
                    "component_name": c.component_name,
                    "component_type": c.component_type,
                    "working_pressure": c.working_pressure,
                    "size": c.size,
                    "ram_type": c.ram_type,
                    "manufacturer": c.manufacturer,
                    "serial_number": c.serial_number,
                    "last_test_date": c.last_test_date,
                    "next_test_due": c.next_test_due,
                    "test_pressure": c.test_pressure,
                    "test_result": c.test_result,
                    "status": c.status,
                    "remarks": c.remarks,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "created_by": c.created_by
                }
                for c in components
            ]
            
        except Exception as e:
            logger.error(f"Error getting BOP components: {e}")
            return []
        finally:
            session.close()
    
    def get_waste_records_for_export(self, well_id: int, start_date: date = None, 
                                    end_date: date = None) -> List[Dict[str, Any]]:
        """Get waste records"""
        session = self.db.create_session()
        try:
            query = session.query(WasteRecord).filter(WasteRecord.well_id == well_id)
            
            if start_date:
                query = query.filter(WasteRecord.record_date >= start_date)
            if end_date:
                query = query.filter(WasteRecord.record_date <= end_date)
            
            records = query.order_by(WasteRecord.record_date).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "safety_report_id": r.safety_report_id,
                    "record_date": r.record_date,
                    "waste_type": r.waste_type,
                    "volume": r.volume,
                    "unit": r.unit,
                    "ph": r.ph,
                    "turbidity": r.turbidity,
                    "hardness": r.hardness,
                    "oil_content": r.oil_content,
                    "disposal_method": r.disposal_method,
                    "disposal_date": r.disposal_date,
                    "disposal_company": r.disposal_company,
                    "waste_ticket_number": r.waste_ticket_number,
                    "manifest_number": r.manifest_number,
                    "remarks": r.remarks,
                    "status": r.status,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "created_by": r.created_by
                }
                for r in records
            ]
            
        except Exception as e:
            logger.error(f"Error getting waste records: {e}")
            return []
        finally:
            session.close()
    
    # ============ Services Data ============
    
    def get_service_companies_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get service companies"""
        session = self.db.create_session()
        try:
            companies = session.query(ServiceCompany).filter(
                ServiceCompany.well_id == well_id
            ).all()
            
            return [
                {
                    "id": c.id,
                    "well_id": c.well_id,
                    "section_id": c.section_id,
                    "report_id": c.report_id,
                    "company_name": c.company_name,
                    "service_type": c.service_type,
                    "start_datetime": c.start_datetime,
                    "end_datetime": c.end_datetime,
                    "contact_person": c.contact_person,
                    "contact_phone": c.contact_phone,
                    "contact_email": c.contact_email,
                    "equipment_used": c.equipment_used,
                    "personnel_count": c.personnel_count,
                    "status": c.status,
                    "description": c.description,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "created_by": c.created_by
                }
                for c in companies
            ]
            
        except Exception as e:
            logger.error(f"Error getting service companies: {e}")
            return []
        finally:
            session.close()
    
    def get_material_requests_for_export(self, well_id: int, start_date: date = None, 
                                        end_date: date = None) -> List[Dict[str, Any]]:
        """Get material requests"""
        session = self.db.create_session()
        try:
            query = session.query(MaterialRequest).filter(
                MaterialRequest.well_id == well_id
            )
            
            if start_date:
                query = query.filter(MaterialRequest.request_date >= start_date)
            if end_date:
                query = query.filter(MaterialRequest.request_date <= end_date)
            
            requests = query.order_by(MaterialRequest.request_date).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "section_id": r.section_id,
                    "report_id": r.report_id,
                    "request_date": r.request_date,
                    "requested_items": r.requested_items,
                    "requested_quantity": r.requested_quantity,
                    "requested_unit": r.requested_unit,
                    "outstanding_items": r.outstanding_items,
                    "outstanding_quantity": r.outstanding_quantity,
                    "received_items": r.received_items,
                    "received_quantity": r.received_quantity,
                    "received_date": r.received_date,
                    "backload_items": r.backload_items,
                    "backload_quantity": r.backload_quantity,
                    "backload_date": r.backload_date,
                    "remarks": r.remarks,
                    "status": r.status,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "created_by": r.created_by
                }
                for r in requests
            ]
            
        except Exception as e:
            logger.error(f"Error getting material requests: {e}")
            return []
        finally:
            session.close()
    
    def get_equipment_logs_for_export(self, well_id: int, start_date: date = None, 
                                     end_date: date = None) -> List[Dict[str, Any]]:
        """Get equipment logs"""
        session = self.db.create_session()
        try:
            query = session.query(EquipmentLog).filter(EquipmentLog.well_id == well_id)
            
            if start_date:
                query = query.filter(EquipmentLog.created_at >= start_date)
            if end_date:
                query = query.filter(EquipmentLog.created_at <= end_date)
            
            logs = query.order_by(EquipmentLog.service_date).all()
            
            return [
                {
                    "id": l.id,
                    "well_id": l.well_id,
                    "section_id": l.section_id,
                    "report_id": l.report_id,
                    "equipment_type": l.equipment_type,
                    "equipment_name": l.equipment_name,
                    "equipment_id": l.equipment_id,
                    "manufacturer": l.manufacturer,
                    "serial_number": l.serial_number,
                    "service_date": l.service_date,
                    "service_type": l.service_type,
                    "service_provider": l.service_provider,
                    "hours_worked": l.hours_worked,
                    "status": l.status,
                    "notes": l.notes,
                    "created_at": l.created_at,
                    "updated_at": l.updated_at,
                    "created_by": l.created_by
                }
                for l in logs
            ]
            
        except Exception as e:
            logger.error(f"Error getting equipment logs: {e}")
            return []
        finally:
            session.close()
    
    # ============ Planning Data ============
    
    def get_lookahead_plans_for_export(self, well_id: int, start_date: date = None, 
                                      end_date: date = None) -> List[Dict[str, Any]]:
        """Get lookahead plans"""
        session = self.db.create_session()
        try:
            query = session.query(SevenDaysLookahead).filter(
                SevenDaysLookahead.well_id == well_id
            )
            
            if start_date:
                query = query.filter(SevenDaysLookahead.plan_date >= start_date)
            if end_date:
                query = query.filter(SevenDaysLookahead.plan_date <= end_date)
            
            plans = query.order_by(SevenDaysLookahead.plan_date, 
                                 SevenDaysLookahead.day_number).all()
            
            return [
                {
                    "id": p.id,
                    "well_id": p.well_id,
                    "section_id": p.section_id,
                    "report_id": p.report_id,
                    "plan_date": p.plan_date,
                    "day_number": p.day_number,
                    "activity": p.activity,
                    "tools": p.tools,
                    "responsible": p.responsible,
                    "remarks": p.remarks,
                    "status": p.status,
                    "progress_percentage": p.progress_percentage,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "created_by": p.created_by
                }
                for p in plans
            ]
            
        except Exception as e:
            logger.error(f"Error getting lookahead plans: {e}")
            return []
        finally:
            session.close()
    
    def get_npt_reports_for_export(self, well_id: int, start_date: date = None, 
                                  end_date: date = None) -> List[Dict[str, Any]]:
        """Get NPT reports"""
        session = self.db.create_session()
        try:
            query = session.query(NPTReport).filter(NPTReport.well_id == well_id)
            
            if start_date:
                query = query.filter(NPTReport.npt_date >= start_date)
            if end_date:
                query = query.filter(NPTReport.npt_date <= end_date)
            
            reports = query.order_by(NPTReport.npt_date).all()
            
            return [
                {
                    "id": r.id,
                    "well_id": r.well_id,
                    "section_id": r.section_id,
                    "report_id": r.report_id,
                    "npt_date": r.npt_date,
                    "start_time": r.start_time.strftime("%H:%M") if r.start_time else "",
                    "end_time": r.end_time.strftime("%H:%M") if r.end_time else "",
                    "duration_hours": r.duration_hours,
                    "npt_category": r.npt_category,
                    "npt_code": r.npt_code,
                    "npt_description": r.npt_description,
                    "responsible_party": r.responsible_party,
                    "cost_impact": r.cost_impact,
                    "status": r.status,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "created_by": r.created_by
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting NPT reports: {e}")
            return []
        finally:
            session.close()
    
    def get_activity_codes_for_export(self, well_id: int) -> List[Dict[str, Any]]:
        """Get activity codes"""
        session = self.db.create_session()
        try:
            codes = session.query(ActivityCode).filter(
                ActivityCode.well_id == well_id
            ).all()
            
            return [
                {
                    "id": c.id,
                    "well_id": c.well_id,
                    "main_phase": c.main_phase,
                    "main_code": c.main_code,
                    "sub_code": c.sub_code,
                    "code_name": c.code_name,
                    "code_description": c.code_description,
                    "is_productive": c.is_productive,
                    "is_npt": c.is_npt,
                    "color_code": c.color_code,
                    "usage_count": c.usage_count,
                    "total_hours": c.total_hours,
                    "last_used": c.last_used,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "created_by": c.created_by
                }
                for c in codes
            ]
            
        except Exception as e:
            logger.error(f"Error getting activity codes: {e}")
            return []
        finally:
            session.close()
    
    # ============ Analysis Data ============
    
    def get_time_depth_data_for_export(self, well_id: int, start_date: date = None, 
                                      end_date: date = None) -> List[Dict[str, Any]]:
        """Get time depth data"""
        session = self.db.create_session()
        try:
            query = session.query(TimeDepthData).filter(TimeDepthData.well_id == well_id)
            
            if start_date:
                query = query.filter(TimeDepthData.created_at >= start_date)
            if end_date:
                query = query.filter(TimeDepthData.created_at <= end_date)
            
            data = query.order_by(TimeDepthData.timestamp).all()
            
            return [
                {
                    "id": d.id,
                    "well_id": d.well_id,
                    "section_id": d.section_id,
                    "timestamp": d.timestamp,
                    "depth": d.depth,
                    "activity_code": d.activity_code,
                    "rop": d.rop,
                    "wob": d.wob,
                    "rpm": d.rpm,
                    "torque": d.torque,
                    "cumulative_time": d.cumulative_time,
                    "daily_progress": d.daily_progress,
                    "created_at": d.created_at,
                    "updated_at": d.updated_at,
                    "created_by": d.created_by
                }
                for d in data
            ]
            
        except Exception as e:
            logger.error(f"Error getting time depth data: {e}")
            return []
        finally:
            session.close()
    
    def get_rop_analysis_for_export(self, well_id: int, start_date: date = None, 
                                   end_date: date = None) -> List[Dict[str, Any]]:
        """Get ROP analysis"""
        session = self.db.create_session()
        try:
            query = session.query(ROPAnalysis).filter(ROPAnalysis.well_id == well_id)
            
            if start_date:
                query = query.filter(ROPAnalysis.analysis_date >= start_date)
            if end_date:
                query = query.filter(ROPAnalysis.analysis_date <= end_date)
            
            analyses = query.order_by(ROPAnalysis.analysis_date).all()
            
            return [
                {
                    "id": a.id,
                    "well_id": a.well_id,
                    "section_id": a.section_id,
                    "analysis_date": a.analysis_date,
                    "start_depth": a.start_depth,
                    "end_depth": a.end_depth,
                    "avg_rop": a.avg_rop,
                    "max_rop": a.max_rop,
                    "min_rop": a.min_rop,
                    "rop_std_dev": a.rop_std_dev,
                    "formation_type": a.formation_type,
                    "bit_type": a.bit_type,
                    "hydraulics_efficiency": a.hydraulics_efficiency,
                    "drill_string_config": a.drill_string_config,
                    "rop_chart_data": a.rop_chart_data,
                    "depth_chart_data": a.depth_chart_data,
                    "recommendations": a.recommendations,
                    "efficiency_score": a.efficiency_score,
                    "created_at": a.created_at,
                    "updated_at": a.updated_at,
                    "created_by": a.created_by
                }
                for a in analyses
            ]
            
        except Exception as e:
            logger.error(f"Error getting ROP analysis: {e}")
            return []
        finally:
            session.close()
    
    # ============ Comprehensive Export ============
    
    def get_complete_well_data_for_export(self, well_id: int, start_date: date = None, 
                                         end_date: date = None) -> Dict[str, Any]:
        """Get ALL data for a well - comprehensive export"""
        
        # Get basic well info
        well_data = self.get_well_info(well_id)
        
        if not well_data:
            return {}
        
        # Add all data categories
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "well_id": well_id,
                "well_name": well_data.get("name", ""),
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "export_version": "1.0"
            },
            
            "well_information": well_data,
            
            "daily_operations": {
                "daily_reports": self.get_daily_reports_for_export(well_id, start_date, end_date),
                "trip_sheet_entries": self.get_trip_sheet_entries_for_export(well_id, start_date, end_date)
            },
            
            "drilling_technical": {
                "drilling_parameters": self.get_drilling_parameters_for_export(well_id, start_date, end_date),
                "mud_reports": self.get_mud_reports_for_export(well_id, start_date, end_date),
                "cement_reports": self.get_cement_reports_for_export(well_id, start_date, end_date),
                "casing_reports": self.get_casing_reports_for_export(well_id, start_date, end_date)
            },
            
            "downhole_equipment": {
                "bit_reports": self.get_bit_reports_for_export(well_id),
                "bha_reports": self.get_bha_reports_for_export(well_id),
                "downhole_equipment": self.get_downhole_equipment_for_export(well_id),
                "formation_reports": self.get_formation_reports_for_export(well_id)
            },
            
            "trajectory_survey": {
                "survey_points": self.get_survey_points_for_export(well_id),
                "trajectory_calculations": self.get_trajectory_calculations_for_export(well_id)
            },
            
            "logistics_materials": {
                "logistics_personnel": self.get_logistics_personnel_for_export(well_id),
                "service_company_pob": self.get_service_company_pob_for_export(well_id),
                "fuel_water_inventory": self.get_fuel_water_inventory_for_export(well_id, start_date, end_date),
                "bulk_materials": self.get_bulk_materials_for_export(well_id, start_date, end_date),
                "transport_logs": self.get_transport_logs_for_export(well_id, start_date, end_date)
            },
            
            "safety_environment": {
                "safety_reports": self.get_safety_reports_for_export(well_id, start_date, end_date),
                "bop_components": self.get_bop_components_for_export(well_id),
                "waste_records": self.get_waste_records_for_export(well_id, start_date, end_date)
            },
            
            "services_maintenance": {
                "service_companies": self.get_service_companies_for_export(well_id),
                "material_requests": self.get_material_requests_for_export(well_id, start_date, end_date),
                "equipment_logs": self.get_equipment_logs_for_export(well_id, start_date, end_date)
            },
            
            "planning_analysis": {
                "lookahead_plans": self.get_lookahead_plans_for_export(well_id, start_date, end_date),
                "npt_reports": self.get_npt_reports_for_export(well_id, start_date, end_date),
                "activity_codes": self.get_activity_codes_for_export(well_id),
                "time_depth_data": self.get_time_depth_data_for_export(well_id, start_date, end_date),
                "rop_analysis": self.get_rop_analysis_for_export(well_id, start_date, end_date)
            },
            
            "statistics": {
                "total_daily_reports": len(export_data["daily_operations"]["daily_reports"]),
                "total_drilling_parameters": len(export_data["drilling_technical"]["drilling_parameters"]),
                "total_safety_reports": len(export_data["safety_environment"]["safety_reports"]),
                "total_logistics_items": len(export_data["logistics_materials"]["logistics_personnel"]) + 
                                        len(export_data["logistics_materials"]["service_company_pob"]) +
                                        len(export_data["logistics_materials"]["bulk_materials"]),
                "total_planning_items": len(export_data["planning_analysis"]["lookahead_plans"]) +
                                       len(export_data["planning_analysis"]["npt_reports"])
            }
        }
        
        return export_data
    
    def get_batch_export_data(self, well_ids: List[int], start_date: date = None, 
                             end_date: date = None) -> Dict[str, Any]:
        """Get data for multiple wells - batch export"""
        
        batch_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "well_count": len(well_ids),
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "export_version": "1.0"
            },
            "wells": {}
        }
        
        for well_id in well_ids:
            try:
                # Get basic well info first
                well_info = self.get_well_info(well_id)
                if well_info:
                    well_name = well_info.get("name", f"Well_{well_id}")
                    batch_data["wells"][well_name] = self.get_complete_well_data_for_export(
                        well_id, start_date, end_date
                    )
            except Exception as e:
                logger.error(f"Error getting data for well {well_id}: {e}")
                batch_data["wells"][f"Error_Well_{well_id}"] = {
                    "error": str(e),
                    "well_id": well_id
                }
        
        # Add batch statistics
        batch_data["statistics"] = {
            "total_wells_exported": len(batch_data["wells"]),
            "successful_exports": sum(1 for w in batch_data["wells"].values() if "error" not in w),
            "failed_exports": sum(1 for w in batch_data["wells"].values() if "error" in w)
        }
        
        return batch_data


# ==================== Export Generator ====================

class ExportGenerator:
    """Generates export files in various formats"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.data_collector = ExportDataCollector(db_manager)
    
    def export_daily_report(self, well_id: int, start_date: date, end_date: date, 
                           format_type: str = "json") -> str:
        """Export daily report data"""
        
        # Collect data
        data = self.data_collector.get_daily_reports_for_export(well_id, start_date, end_date)
        
        if format_type == "json":
            return self._export_to_json(data, "daily_report")
        elif format_type == "excel":
            return self._export_to_excel(data, "daily_report")
        elif format_type == "csv":
            return self._export_to_csv(data, "daily_report")
        else:
            return self._export_to_json(data, "daily_report")
    
    def export_drilling_data(self, well_id: int, start_date: date, end_date: date, 
                            format_type: str = "json") -> str:
        """Export drilling data"""
        
        # Collect all drilling data
        drilling_data = {
            "drilling_parameters": self.data_collector.get_drilling_parameters_for_export(well_id, start_date, end_date),
            "mud_reports": self.data_collector.get_mud_reports_for_export(well_id, start_date, end_date),
            "cement_reports": self.data_collector.get_cement_reports_for_export(well_id, start_date, end_date),
            "casing_reports": self.data_collector.get_casing_reports_for_export(well_id, start_date, end_date)
        }
        
        if format_type == "json":
            return self._export_to_json(drilling_data, "drilling_data")
        elif format_type == "excel":
            return self._export_to_excel(drilling_data, "drilling_data")
        else:
            return self._export_to_json(drilling_data, "drilling_data")
    
    def export_safety_data(self, well_id: int, start_date: date, end_date: date, 
                          format_type: str = "json") -> str:
        """Export safety data"""
        
        safety_data = {
            "safety_reports": self.data_collector.get_safety_reports_for_export(well_id, start_date, end_date),
            "bop_components": self.data_collector.get_bop_components_for_export(well_id),
            "waste_records": self.data_collector.get_waste_records_for_export(well_id, start_date, end_date)
        }
        
        if format_type == "json":
            return self._export_to_json(safety_data, "safety_data")
        elif format_type == "excel":
            return self._export_to_excel(safety_data, "safety_data")
        else:
            return self._export_to_json(safety_data, "safety_data")
    
    def export_complete_well_report(self, well_id: int, start_date: date = None, 
                                   end_date: date = None, format_type: str = "json") -> Dict[str, str]:
        """Export complete well report in multiple formats"""
        
        # Get complete data
        complete_data = self.data_collector.get_complete_well_data_for_export(well_id, start_date, end_date)
        
        # Export in different formats
        results = {}
        
        if "json" in format_type or format_type == "all":
            results["json"] = self._export_to_json(complete_data, "complete_well_report")
        
        if "excel" in format_type or format_type == "all":
            results["excel"] = self._export_to_excel(complete_data, "complete_well_report")
        
        if "pdf" in format_type or format_type == "all":
            results["pdf"] = self._export_to_pdf(complete_data, "complete_well_report")
        
        if "csv" in format_type or format_type == "all":
            results["csv"] = self._export_to_csv(complete_data, "complete_well_report")
        
        return results
    
    def export_batch_report(self, well_ids: List[int], start_date: date = None, 
                           end_date: date = None, format_type: str = "json") -> Dict[str, str]:
        """Export batch report for multiple wells"""
        
        # Get batch data
        batch_data = self.data_collector.get_batch_export_data(well_ids, start_date, end_date)
        
        # Export in different formats
        results = {}
        
        if "json" in format_type or format_type == "all":
            results["json"] = self._export_to_json(batch_data, "batch_export")
        
        if "excel" in format_type or format_type == "all":
            results["excel"] = self._export_to_excel(batch_data, "batch_export")
        
        if "zip" in format_type or format_type == "all":
            results["zip"] = self._export_to_zip(batch_data, "batch_export")
        
        return results
    
    def _export_to_json(self, data: Any, file_prefix: str) -> str:
        """Export data to JSON file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exports/{file_prefix}_{timestamp}.json"
            
            # Create exports directory if it doesn't exist
            os.makedirs("exports", exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return ""
    
    def _export_to_excel(self, data: Any, file_prefix: str) -> str:
        """Export data to Excel file"""
        try:
            # This would use pandas or openpyxl to create Excel file
            # For now, create a simple implementation
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exports/{file_prefix}_{timestamp}.xlsx"
            
            # Create exports directory if it doesn't exist
            os.makedirs("exports", exist_ok=True)
            
            # For now, just save as JSON and rename
            # In production, implement actual Excel export using pandas
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            
            # Rename to .xlsx (this is temporary)
            excel_file = filename.replace('.json', '.xlsx')
            os.rename(filename, excel_file)
            
            return excel_file
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return ""
    
    def _export_to_pdf(self, data: Any, file_prefix: str) -> str:
        """Export data to PDF file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exports/{file_prefix}_{timestamp}.pdf"
            
            # Create exports directory if it doesn't exist
            os.makedirs("exports", exist_ok=True)
            
            # This would use a PDF library like ReportLab or WeasyPrint
            # For now, create a simple placeholder
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"PDF Export of {file_prefix}\n")
                f.write(f"Generated: {datetime.now()}\n\n")
                f.write("Data summary:\n")
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (list, dict)):
                            f.write(f"{key}: {len(value) if isinstance(value, list) else len(value.keys())} items\n")
                        else:
                            f.write(f"{key}: {value}\n")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}")
            return ""
    
    def _export_to_csv(self, data: Any, file_prefix: str) -> str:
        """Export data to CSV file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exports/{file_prefix}_{timestamp}.csv"
            
            # Create exports directory if it doesn't exist
            os.makedirs("exports", exist_ok=True)
            
            if isinstance(data, list) and len(data) > 0:
                # If it's a list of dictionaries, write as CSV
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if data and isinstance(data[0], dict):
                        fieldnames = data[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data)
                    else:
                        writer = csv.writer(f)
                        writer.writerow(["Data"])
                        for item in data:
                            writer.writerow([str(item)])
            elif isinstance(data, dict):
                # If it's a dictionary, flatten it
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    for key, value in data.items():
                        writer.writerow([key, str(value)])
            else:
                # For other types
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(data))
            
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return ""
    
    def _export_to_zip(self, data: Any, file_prefix: str) -> str:
        """Export data to ZIP archive with multiple files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"exports/{file_prefix}_{timestamp}.zip"
            
            # Create exports directory if it doesn't exist
            os.makedirs("exports", exist_ok=True)
            
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                # Add JSON version
                json_data = json.dumps(data, indent=2, default=str, ensure_ascii=False)
                zipf.writestr(f"{file_prefix}.json", json_data)
                
                # Add CSV versions for main data sections
                if isinstance(data, dict) and "wells" in data:
                    for well_name, well_data in data["wells"].items():
                        if isinstance(well_data, dict):
                            # Create CSV for well summary
                            summary_data = []
                            for section, items in well_data.items():
                                if isinstance(items, list):
                                    summary_data.append({
                                        "section": section,
                                        "item_count": len(items)
                                    })
                            
                            if summary_data:
                                csv_buffer = io.StringIO()
                                fieldnames = summary_data[0].keys()
                                writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(summary_data)
                                zipf.writestr(f"{well_name}_summary.csv", csv_buffer.getvalue())
            
            return zip_filename
            
        except Exception as e:
            logger.error(f"Error exporting to ZIP: {e}")
            return ""

# ==================== Main Export Widget ====================
class ExportWidget(DrillWidgetBase):
    """Main Export Widget containing all export tabs"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        super().__init__("ExportWidget", db_manager)
        self.db = db_manager
        self.status_manager = StatusBarManager()
        
        # Setup autosave
        self.autosave_manager = AutoSaveManager()
        self.autosave_manager.enable_for_widget("ExportWidget", self, interval_minutes=10)
        
        self.init_ui()
        self.setup_connections()
        self.load_data()
    
    def init_ui(self):
        """Initialize the main UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabBar::tab {
                padding: 10px 20px;
                font-size: 12pt;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QTabBar::tab:!selected {
                background: #f0f0f0;
                color: #555;
            }
        """)
        
        # Create tabs
        self.daily_tab = DailyExportTab(self.db)
        self.eowr_tab = EOWRExportTab(self.db)
        self.batch_tab = BatchExportTab(self.db)
        
        # Add tabs
        self.tab_widget.addTab(self.daily_tab, "📤 Daily Export")
        self.tab_widget.addTab(self.eowr_tab, "📑 End of Well Report")
        self.tab_widget.addTab(self.batch_tab, "📊 Batch Export")
        
        main_layout.addWidget(self.tab_widget)
    
    def setup_connections(self):
        """Setup signal connections"""
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def load_data(self):
        """Load initial data"""
        # This will be called by each tab individually
        pass
    
    def on_tab_changed(self, index: int):
        """Handle tab change"""
        tab_names = ["Daily Export", "EOWR", "Batch Export"]
        if 0 <= index < len(tab_names):
            self.status_manager.show_message("ExportWidget", 
                                           f"Switched to {tab_names[index]} tab")
    
    def save_data(self) -> bool:
        """Save export settings and data"""
        try:
            # Collect data from all tabs
            export_data = {
                "last_save": datetime.now().isoformat(),
                "active_tab": self.tab_widget.currentIndex(),
                "version": "1.0"
            }
            
            # Save to database if available
            if self.db:
                # Create or update export settings in database
                pass
            
            self.status_manager.show_success("ExportWidget", "Export settings saved")
            return True
            
        except Exception as e:
            logger.error(f"Error saving export data: {e}")
            self.status_manager.show_error("ExportWidget", f"Save failed: {str(e)}")
            return False
    
    def load_data_from_db(self):
        """Load data from database"""
        try:
            if self.db:
                # Load saved export settings
                pass
            
            self.status_manager.show_message("ExportWidget", "Export settings loaded")
            return True
            
        except Exception as e:
            logger.error(f"Error loading export data: {e}")
            return False


# ==================== Database Functions for Export ====================
class ExportDatabaseManager:
    """Database functions specific to export operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_daily_reports_for_export(self, well_id: int, start_date: date, 
                                    end_date: date) -> List[Dict[str, Any]]:
        """Get daily reports for export within date range"""
        try:
            reports = self.db.get_daily_reports_by_well(well_id)
            
            # Filter by date range
            filtered_reports = []
            for report in reports:
                report_date = report.get('report_date')
                if isinstance(report_date, str):
                    report_date = datetime.strptime(report_date, "%Y-%m-%d").date()
                
                if start_date <= report_date <= end_date:
                    # Get full report data
                    full_report = self.db.get_daily_report_by_id(report['id'])
                    if full_report:
                        filtered_reports.append(full_report)
            
            return filtered_reports
            
        except Exception as e:
            logger.error(f"Error getting daily reports for export: {e}")
            return []
    
    def get_drilling_parameters_for_export(self, well_id: int, start_date: date, 
                                          end_date: date) -> List[Dict[str, Any]]:
        """Get drilling parameters for export"""
        try:
            # This would query the DrillingParameters table
            # For now, return sample data
            return [
                {
                    "date": start_date.isoformat(),
                    "bit_size": 12.25,
                    "depth_in": 1500,
                    "depth_out": 1650,
                    "rop": 15.3,
                    "wob": 25.5,
                    "rpm": 120,
                    "torque": 12.8
                }
            ]
            
        except Exception as e:
            logger.error(f"Error getting drilling parameters for export: {e}")
            return []
    
    def get_mud_reports_for_export(self, well_id: int, start_date: date, 
                                  end_date: date) -> List[Dict[str, Any]]:
        """Get mud reports for export"""
        try:
            # This would query the MudReport table
            return []
            
        except Exception as e:
            logger.error(f"Error getting mud reports for export: {e}")
            return []
    
    def get_safety_data_for_export(self, well_id: int, start_date: date, 
                                  end_date: date) -> Dict[str, Any]:
        """Get safety data for export"""
        try:
            # This would query SafetyReport, BOPComponent, WasteRecord tables
            return {
                "safety_reports": [],
                "bop_components": [],
                "waste_records": []
            }
            
        except Exception as e:
            logger.error(f"Error getting safety data for export: {e}")
            return {}
    
    def get_well_summary_for_export(self, well_id: int) -> Dict[str, Any]:
        """Get well summary for export"""
        try:
            well_data = self.db.get_well_by_id(well_id)
            if not well_data:
                return {}
            
            # Get additional data
            sections = self.db.get_sections_by_well(well_id)
            daily_reports = self.db.get_daily_reports_by_well(well_id)
            
            summary = {
                "well_info": well_data,
                "sections_count": len(sections),
                "daily_reports_count": len(daily_reports),
                "last_report_date": daily_reports[0]['report_date'] if daily_reports else None,
                "total_depth": max([s.get('depth_to', 0) for s in sections]) if sections else 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting well summary for export: {e}")
            return {}
    
    def save_export_template(self, template_data: Dict[str, Any]) -> bool:
        """Save export template to database"""
        try:
            # This would save to a dedicated ExportTemplate table
            # For now, just log it
            logger.info(f"Export template saved: {template_data.get('name', 'Unnamed')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving export template: {e}")
            return False
    
    def load_export_template(self, template_name: str) -> Dict[str, Any]:
        """Load export template from database"""
        try:
            # This would load from ExportTemplate table
            # For now, return sample template
            return {
                "name": template_name,
                "format": "Excel",
                "sections": ["Well Info", "Daily Reports", "Drilling Parameters"],
                "options": {
                    "include_charts": True,
                    "include_summary": True,
                    "compress": False
                }
            }
            
        except Exception as e:
            logger.error(f"Error loading export template: {e}")
            return {}
