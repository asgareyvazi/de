"""
w8_Safety_Widget.py
Comprehensive Safety Management Module with Database Integration
"""

import logging
import csv
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

from core.managers import (
    TableManager, TableButtonManager, ExportManager, 
    setup_widget_with_managers, StatusBarManager
)
from core.database import DatabaseManager, WasteRecord, BOPComponent, SafetyIncident, SafetyReport
logger = logging.getLogger(__name__)


# ==================== Base Widget Class ====================

class DrillWidgetBase(QWidget):
    """Base class for drill widgets with common functionality"""
    
    def __init__(self, widget_name, db_manager=None):
        super().__init__()
        self.widget_name = widget_name
        self.db = db_manager
        self.status_manager = StatusBarManager()
        self.status_manager.register_widget(widget_name, self)
        
        # Initialize managers
        self.table_managers = {}
        self.export_manager = ExportManager(self)
        
    def show_message(self, message, timeout=3000):
        """Show status message"""
        self.status_manager.show_message(self.widget_name, message, timeout)
    
    def show_success(self, message):
        """Show success message"""
        self.status_manager.show_success(self.widget_name, message)
    
    def show_error(self, message):
        """Show error message"""
        self.status_manager.show_error(self.widget_name, message)
    
    def show_progress(self, message):
        """Show progress message"""
        self.status_manager.show_progress(self.widget_name, message)


# ==================== Safety & BOP Tab ====================

class SafetyBOPTab(QWidget):
    """Safety and BOP Management Tab"""
    
    def __init__(self, parent_widget):
        super().__init__()
        self.parent = parent_widget
        self.db = parent_widget.db
        self.table_managers = {}  # <-- اضافه کردن این خط
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Safety Drills Section
        drills_group = QGroupBox("Safety Drills")
        drills_layout = QGridLayout()
        
        drills_layout.addWidget(QLabel("Last Fire Drill:"), 0, 0)
        self.last_fire_drill = QDateEdit()
        self.last_fire_drill.setDate(QDate.currentDate().addDays(-7))
        self.last_fire_drill.setCalendarPopup(True)
        drills_layout.addWidget(self.last_fire_drill, 0, 1)
        
        drills_layout.addWidget(QLabel("Last BOP Drill:"), 0, 2)
        self.last_bop_drill = QDateEdit()
        self.last_bop_drill.setDate(QDate.currentDate().addDays(-14))
        self.last_bop_drill.setCalendarPopup(True)
        drills_layout.addWidget(self.last_bop_drill, 0, 3)
        
        drills_layout.addWidget(QLabel("Last H2S Drill:"), 1, 0)
        self.last_h2s_drill = QDateEdit()
        self.last_h2s_drill.setDate(QDate.currentDate().addDays(-21))
        self.last_h2s_drill.setCalendarPopup(True)
        drills_layout.addWidget(self.last_h2s_drill, 1, 1)
        
        drills_layout.addWidget(QLabel("Days without LTI:"), 1, 2)
        self.days_no_lti = QSpinBox()
        self.days_no_lti.setRange(0, 10000)
        self.days_no_lti.setValue(120)
        drills_layout.addWidget(self.days_no_lti, 1, 3)
        
        update_lti_btn = QPushButton("🔄 Update LTI Days")
        update_lti_btn.clicked.connect(self.update_lti_days)
        drills_layout.addWidget(update_lti_btn, 2, 0, 1, 4)
        
        drills_group.setLayout(drills_layout)
        layout.addWidget(drills_group)
        
        # BOP Tests Section
        bop_group = QGroupBox("BOP Tests")
        bop_layout = QGridLayout()
        
        bop_layout.addWidget(QLabel("Last Rams Test:"), 0, 0)
        self.last_rams_test = QDateEdit()
        self.last_rams_test.setDate(QDate.currentDate().addDays(-10))
        self.last_rams_test.setCalendarPopup(True)
        bop_layout.addWidget(self.last_rams_test, 0, 1)
        
        bop_layout.addWidget(QLabel("Test Pressure (psi):"), 0, 2)
        self.test_pressure = QDoubleSpinBox()
        self.test_pressure.setRange(0, 20000)
        self.test_pressure.setValue(5000)
        self.test_pressure.setSuffix(" psi")
        bop_layout.addWidget(self.test_pressure, 0, 3)
        
        bop_layout.addWidget(QLabel("Last Koomey Test:"), 1, 0)
        self.last_koomey_test = QDateEdit()
        self.last_koomey_test.setDate(QDate.currentDate().addDays(-5))
        self.last_koomey_test.setCalendarPopup(True)
        bop_layout.addWidget(self.last_koomey_test, 1, 1)
        
        bop_layout.addWidget(QLabel("Days Since Last Test:"), 1, 2)
        self.days_since_last_test = QSpinBox()
        self.days_since_last_test.setRange(0, 365)
        self.days_since_last_test.setValue(5)
        bop_layout.addWidget(self.days_since_last_test, 1, 3)
        
        calculate_days_btn = QPushButton("🔄 Calculate Days Since Test")
        calculate_days_btn.clicked.connect(self.calculate_days_since_test)
        bop_layout.addWidget(calculate_days_btn, 2, 0, 1, 4)
        
        bop_group.setLayout(bop_layout)
        layout.addWidget(bop_group)
        
        # BOP Test Report ComboBox
        bop_layout.addWidget(QLabel("BOP Test Report:"), 3, 0)
        self.bop_test_report = QComboBox()
        self.bop_test_report.addItems([
            "Weekly Routine Test",
            "Monthly Full Test", 
            "Post-Maintenance Test",
            "Pre-Spud Test",
            "Annular Function Test",
            "Pipe Rams Function Test",
            "Shear Rams Function Test",
            "Choke & Kill Line Test",
            "Accumulator (Koomey) Test",
            "Emergency Disconnect Test",
            "Shallow Water Test",
            "Deepwater Test",
            "Other - Custom"
        ])
        self.bop_test_report.setEditable(True)  # قابلیت اضافه کردن تست جدید
        self.bop_test_report.setCurrentText("Weekly Routine Test")
        bop_layout.addWidget(self.bop_test_report, 3, 1)

        # Test Status ComboBox
        bop_layout.addWidget(QLabel("Test Status:"), 3, 2)
        self.test_status = QComboBox()
        self.test_status.addItems([
            "Scheduled",
            "In Progress",
            "Completed - Pass",
            "Completed - Fail",
            "Cancelled",
            "Postponed"
        ])
        self.test_status.setCurrentText("Scheduled")
        bop_layout.addWidget(self.test_status, 3, 3)

        add_test_btn = QPushButton("➕ Add New Test Type")
        add_test_btn.clicked.connect(self.add_new_test_type)
        bop_layout.addWidget(add_test_btn, 4, 0, 1, 4)


        # BOP Stack Table
        bop_stack_group = QGroupBox("BOP Stack & Wellhead")
        bop_stack_layout = QVBoxLayout()
        
        self.bop_stack_table = QTableWidget(0, 8)
        self.bop_stack_table.setHorizontalHeaderLabels([
            "Name", "Type", "WP (psi)", "Size (in)", "RAMs", 
            "Last Test", "Next Due", "Remarks"
        ])
        self.bop_stack_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bop_stack_table.setEditTriggers(QTableWidget.AllEditTriggers)
        
        # Setup Table Manager
        self.bop_table_manager = TableManager(self.bop_stack_table, self)
        self.table_managers['bop'] = self.bop_table_manager
        
        bop_stack_layout.addWidget(self.bop_stack_table)
        
        # BOP Table Buttons
        bop_button_layout = QHBoxLayout()
        self.add_bop_btn = QPushButton("➕ Add BOP Component")
        self.remove_bop_btn = QPushButton("➖ Remove BOP Component")
        self.calculate_bop_btn = QPushButton("🔄 Calculate Test Schedule")
        self.export_bop_btn = QPushButton("📤 Export BOP Data")
        
        bop_button_layout.addWidget(self.add_bop_btn)
        bop_button_layout.addWidget(self.remove_bop_btn)
        bop_button_layout.addWidget(self.calculate_bop_btn)
        bop_button_layout.addWidget(self.export_bop_btn)
        bop_button_layout.addStretch()
        
        bop_stack_layout.addLayout(bop_button_layout)
        bop_stack_group.setLayout(bop_stack_layout)
        layout.addWidget(bop_stack_group)
        
        self.setLayout(layout)
    def add_new_test_type(self):
        """Add new BOP test type to combobox"""
        text, ok = QInputDialog.getText(
            self, "Add New BOP Test Type",
            "Enter new BOP test type:",
            text="Custom Test - "
        )
        
        if ok and text:
            # بررسی وجود در لیست
            if self.bop_test_report.findText(text) == -1:
                self.bop_test_report.addItem(text)
                self.bop_test_report.setCurrentText(text)
                self.parent.show_success(f"New test type added: {text}")
            else:
                self.parent.show_message(f"Test type '{text}' already exists")
                
    def setup_connections(self):
        """Setup signal connections"""
        self.add_bop_btn.clicked.connect(self.add_bop_row)
        self.remove_bop_btn.clicked.connect(self.remove_bop_row)
        self.calculate_bop_btn.clicked.connect(self.calculate_bop_schedule)
        self.export_bop_btn.clicked.connect(self.export_bop_data)
    
    def add_bop_row(self):
        """Add row to BOP table"""
        if 'bop' in self.table_managers:  # <-- اصلاح شده
            self.table_managers['bop'].add_row()
        else:
            row = self.bop_stack_table.rowCount()
            self.bop_stack_table.insertRow(row)
            self.setup_bop_row_with_defaults(row)
    
    def setup_bop_row_with_defaults(self, row):
        """Setup BOP row with default values"""
        today = QDate.currentDate()
        
        # Default values
        defaults = [
            "New Component",
            "Type",
            "5000",
            "13-5/8",
            "N/A",
            today.toString("yyyy-MM-dd"),
            today.addDays(30).toString("yyyy-MM-dd"),
            "In Service"
        ]
        
        for col, value in enumerate(defaults):
            item = QTableWidgetItem(value)
            if col in [2]:  # Numeric columns
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.bop_stack_table.setItem(row, col, item)
    
    def remove_bop_row(self):
        """Remove selected row from BOP table"""
        if 'bop' in self.table_managers:  # <-- اصلاح شده
            self.table_managers['bop'].delete_row()
        else:
            current_row = self.bop_stack_table.currentRow()
            if current_row >= 0:
                self.bop_stack_table.removeRow(current_row)
    
    def calculate_bop_schedule(self):
        """Calculate next test due dates for BOP components"""
        self.parent.show_progress("Calculating BOP test schedule...")
        
        try:
            today = QDate.currentDate()
            overdue_count = 0
            warning_count = 0
            
            for row in range(self.bop_stack_table.rowCount()):
                last_test_item = self.bop_stack_table.item(row, 5)
                if last_test_item and last_test_item.text():
                    try:
                        last_test_date = QDate.fromString(last_test_item.text(), "yyyy-MM-dd")
                        if last_test_date.isValid():
                            # Calculate next due date (30 days after last test)
                            next_due = last_test_date.addDays(30)
                            
                            # Check if overdue
                            if next_due < today:
                                next_due = today.addDays(7)
                                overdue_count += 1
                                # Highlight row in red
                                self.highlight_bop_row(row, QColor(255, 220, 220))
                            elif next_due <= today.addDays(7):
                                warning_count += 1
                                # Highlight row in yellow
                                self.highlight_bop_row(row, QColor(255, 255, 200))
                            else:
                                # Clear highlights
                                self.clear_bop_row_highlight(row)
                            
                            # Update next due date
                            next_due_item = QTableWidgetItem(next_due.toString("yyyy-MM-dd"))
                            self.bop_stack_table.setItem(row, 6, next_due_item)
                    except Exception as e:
                        logger.error(f"Error calculating BOP schedule for row {row}: {e}")
            
            # Show results
            message = "✅ BOP Test Schedule Updated\n\n"
            if overdue_count > 0:
                message += f"⚠️ {overdue_count} components are OVERDUE for testing\n"
            if warning_count > 0:
                message += f"⚠️ {warning_count} components need testing within 7 days\n"
            if overdue_count == 0 and warning_count == 0:
                message += "✅ All BOP components are up to date"
            
            QMessageBox.information(self, "BOP Schedule Update", message)
            self.parent.show_success("BOP schedule calculated successfully")
            
        except Exception as e:
            self.parent.show_error(f"Error calculating BOP schedule: {str(e)}")
    
    def highlight_bop_row(self, row, color):
        """Highlight BOP table row with specified color"""
        for col in range(self.bop_stack_table.columnCount()):
            item = self.bop_stack_table.item(row, col)
            if item:
                item.setBackground(color)
    
    def clear_bop_row_highlight(self, row):
        """Clear highlight from BOP table row"""
        for col in range(self.bop_stack_table.columnCount()):
            item = self.bop_stack_table.item(row, col)
            if item:
                item.setBackground(QColor(255, 255, 255))
    
    def export_bop_data(self):
        """Export BOP data to file"""
        result = self.parent.export_manager.export_table_with_dialog(
            self.bop_stack_table, "bop_data"
        )
        if result:
            self.parent.show_success(f"BOP data exported to {result}")
    
    def calculate_days_since_test(self):
        """Calculate days since last BOP test"""
        today = QDate.currentDate()
        days_since_rams = self.last_rams_test.date().daysTo(today)
        days_since_koomey = self.last_koomey_test.date().daysTo(today)
        
        self.days_since_last_test.setValue(max(days_since_rams, days_since_koomey))
        
        # نشان دادن اطلاعات تست فعلی
        test_report = self.bop_test_report.currentText()
        test_status = self.test_status.currentText()
        
        QMessageBox.information(
            self,
            "BOP Test Information",
            f"📋 Test Report: {test_report}\n"
            f"📊 Status: {test_status}\n"
            f"⏰ Days since last Rams test: {days_since_rams}\n"
            f"⏰ Days since last Koomey test: {days_since_koomey}\n"
            f"📈 Maximum days: {max(days_since_rams, days_since_koomey)}\n\n"
            f"⚠️ {'TEST OVERDUE!' if max(days_since_rams, days_since_koomey) > 30 else 'Test within schedule'}"
        )

    def update_lti_days(self):
        """Update LTI days based on last incident date"""
        current_days = self.days_no_lti.value()
        self.days_no_lti.setValue(current_days + 1)
        
        QMessageBox.information(
            self,
            "LTI Days Updated",
            f"Days without LTI: {current_days + 1}\n"
            "Note: This is a manual update."
        )
    
    def save_to_database(self, well_id, report_date):
        """Save BOP data to database"""
        if not self.db:
            return False
        
        try:
            # Collect BOP stack data
            bop_stack_data = []
            for row in range(self.bop_stack_table.rowCount()):
                row_data = {}
                for col in range(self.bop_stack_table.columnCount()):
                    header = self.bop_stack_table.horizontalHeaderItem(col).text()
                    item = self.bop_stack_table.item(row, col)
                    row_data[header] = item.text() if item else ""
                bop_stack_data.append(row_data)
            
            # Prepare safety report data
            report_data = {
                'well_id': well_id,
                'report_date': report_date,
                'report_type': 'Daily',
                'last_fire_drill': self.last_fire_drill.date().toPython(),
                'last_bop_drill': self.last_bop_drill.date().toPython(),
                'last_h2s_drill': self.last_h2s_drill.date().toPython(),
                'days_without_lti': self.days_no_lti.value(),
                'last_rams_test': self.last_rams_test.date().toPython(),
                'test_pressure': self.test_pressure.value(),
                'last_koomey_test': self.last_koomey_test.date().toPython(),
                'days_since_last_test': self.days_since_last_test.value(),
                'bop_test_report': self.bop_test_report.currentText(),  # <-- جدید
                'test_status': self.test_status.currentText(),          # <-- جدید
                'bop_stack_json': bop_stack_data
            }
            
            # Save to database
            if hasattr(self.db, 'save_safety_report'):
                record_id = self.db.save_safety_report(report_data)
                if record_id:
                    # Save individual BOP components
                    for component_data in bop_stack_data:
                        component_data['well_id'] = well_id
                        component_data['safety_report_id'] = record_id
                        if 'Last Test' in component_data:
                            component_data['last_test_date'] = QDate.fromString(
                                component_data['Last Test'], "yyyy-MM-dd"
                            ).toPython()
                        if 'Next Due' in component_data:
                            component_data['next_test_due'] = QDate.fromString(
                                component_data['Next Due'], "yyyy-MM-dd"
                            ).toPython()
                        
                        self.db.save_bop_component({
                            'well_id': well_id,
                            'safety_report_id': record_id,
                            'component_name': component_data.get('Name', ''),
                            'component_type': component_data.get('Type', ''),
                            'working_pressure': float(component_data.get('WP (psi)', 0)),
                            'size': component_data.get('Size (in)', ''),
                            'ram_type': component_data.get('RAMs', ''),
                            'last_test_date': QDate.fromString(
                                component_data.get('Last Test', ''), "yyyy-MM-dd"
                            ).toPython() if component_data.get('Last Test') else None,
                            'next_test_due': QDate.fromString(
                                component_data.get('Next Due', ''), "yyyy-MM-dd"
                            ).toPython() if component_data.get('Next Due') else None,
                            'remarks': component_data.get('Remarks', '')
                        })
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving BOP data to database: {e}")
            return False
    
    def load_from_database(self, well_id, report_date):
        """Load BOP data from database"""
        if not self.db:
            return False
        
        try:
            # Load safety report
            if hasattr(self.db, 'get_safety_report'):
                report_data = self.db.get_safety_report(well_id, report_date)
                if report_data:
                    # Load form fields
                    if report_data.get('last_fire_drill'):
                        self.last_fire_drill.setDate(QDate.fromString(
                            str(report_data['last_fire_drill']), "yyyy-MM-dd"
                        ))
                    if report_data.get('last_bop_drill'):
                        self.last_bop_drill.setDate(QDate.fromString(
                            str(report_data['last_bop_drill']), "yyyy-MM-dd"
                        ))
                    if report_data.get('last_h2s_drill'):
                        self.last_h2s_drill.setDate(QDate.fromString(
                            str(report_data['last_h2s_drill']), "yyyy-MM-dd"
                        ))
                    
                    self.days_no_lti.setValue(report_data.get('days_without_lti', 0))
                    
                    if report_data.get('last_rams_test'):
                        self.last_rams_test.setDate(QDate.fromString(
                            str(report_data['last_rams_test']), "yyyy-MM-dd"
                        ))
                    
                    self.test_pressure.setValue(report_data.get('test_pressure', 0))
                    
                    if report_data.get('last_koomey_test'):
                        self.last_koomey_test.setDate(QDate.fromString(
                            str(report_data['last_koomey_test']), "yyyy-MM-dd"
                        ))
                    # Load test report info
                    if report_data.get('bop_test_report'):
                        index = self.bop_test_report.findText(report_data['bop_test_report'])
                        if index >= 0:
                            self.bop_test_report.setCurrentIndex(index)
                        else:
                            self.bop_test_report.setCurrentText(report_data['bop_test_report'])
                    
                    if report_data.get('test_status'):
                        index = self.test_status.findText(report_data['test_status'])
                        if index >= 0:
                            self.test_status.setCurrentIndex(index)
                    self.days_since_last_test.setValue(report_data.get('days_since_last_test', 0))
                    
                    # Load BOP stack data
                    bop_stack_data = report_data.get('bop_stack_json', [])
                    self.bop_stack_table.setRowCount(0)
                    for component in bop_stack_data:
                        row = self.bop_stack_table.rowCount()
                        self.bop_stack_table.insertRow(row)
                        for col, (key, value) in enumerate(component.items()):
                            item = QTableWidgetItem(str(value))
                            self.bop_stack_table.setItem(row, col, item)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading BOP data from database: {e}")
            return False


# ==================== Waste Management Tab ====================

class WasteManagementTab(QWidget):
    """Waste Management Tab"""
    
    def __init__(self, parent_widget):
        super().__init__()
        self.parent = parent_widget
        self.db = parent_widget.db
        self.table_managers = {}  # <-- اضافه کردن این خط
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Current Waste Status
        waste_group = QGroupBox("Waste Management - Current Status")
        waste_form = QGridLayout()
        
        waste_form.addWidget(QLabel("Recycled (BBL):"), 0, 0)
        self.recycled_volume = QDoubleSpinBox()
        self.recycled_volume.setRange(0, 10000)
        self.recycled_volume.setValue(150.5)
        self.recycled_volume.setSuffix(" BBL")
        waste_form.addWidget(self.recycled_volume, 0, 1)
        
        waste_form.addWidget(QLabel("pH:"), 0, 2)
        self.waste_ph = QDoubleSpinBox()
        self.waste_ph.setRange(0, 14)
        self.waste_ph.setValue(7.2)
        waste_form.addWidget(self.waste_ph, 0, 3)
        
        waste_form.addWidget(QLabel("Turbidity/TSS:"), 1, 0)
        self.turbidity = QLineEdit()
        self.turbidity.setText("15 NTU")
        waste_form.addWidget(self.turbidity, 1, 1)
        
        waste_form.addWidget(QLabel("Hardness/Ca++:"), 1, 2)
        self.hardness = QLineEdit()
        self.hardness.setText("250 mg/L")
        waste_form.addWidget(self.hardness, 1, 3)
        
        waste_form.addWidget(QLabel("Cutting Trans. (m³):"), 2, 0)
        self.cutting_volume = QDoubleSpinBox()
        self.cutting_volume.setRange(0, 1000)
        self.cutting_volume.setValue(25.3)
        self.cutting_volume.setSuffix(" m³")
        waste_form.addWidget(self.cutting_volume, 2, 1)
        
        waste_form.addWidget(QLabel("Oil Content (ppm):"), 2, 2)
        self.oil_content = QDoubleSpinBox()
        self.oil_content.setRange(0, 10000)
        self.oil_content.setValue(45.2)
        self.oil_content.setSuffix(" ppm")
        waste_form.addWidget(self.oil_content, 2, 3)
        
        waste_form.addWidget(QLabel("Waste Type:"), 3, 0)
        self.waste_type = QComboBox()
        self.waste_type.addItems([
            "Drilling Waste", "Cuttings", "Mud", "Chemicals", 
            "Packaging", "Other"
        ])
        waste_form.addWidget(self.waste_type, 3, 1)
        
        waste_form.addWidget(QLabel("Waste Disposal Method:"), 3, 2)
        self.disposal_method = QComboBox()
        self.disposal_method.addItems([
            "Landfill", "Recycle", "Incineration", "Treatment", "Other"
        ])
        waste_form.addWidget(self.disposal_method, 3, 3)
        
        waste_form.addWidget(QLabel("Remarks:"), 4, 0)
        self.waste_remarks = QTextEdit()
        self.waste_remarks.setMaximumHeight(80)
        self.waste_remarks.setPlaceholderText("Enter waste management remarks...")
        waste_form.addWidget(self.waste_remarks, 4, 1, 1, 3)
        
        current_buttons = QHBoxLayout()
        save_current_btn = QPushButton("💾 Save Current Data")
        clear_current_btn = QPushButton("🗑️ Clear Form")
        
        save_current_btn.clicked.connect(self.save_current_waste_data)
        clear_current_btn.clicked.connect(self.clear_waste_form)
        
        current_buttons.addWidget(save_current_btn)
        current_buttons.addWidget(clear_current_btn)
        current_buttons.addStretch()
        
        waste_form.addLayout(current_buttons, 5, 0, 1, 4)
        waste_group.setLayout(waste_form)
        layout.addWidget(waste_group)
        
        # Waste Management History Table
        waste_table_group = QGroupBox("Waste Management History")
        waste_table_layout = QVBoxLayout()
        
        self.waste_table = QTableWidget(0, 6)
        self.waste_table.setHorizontalHeaderLabels([
            "Date", "Type", "Volume (BBL)", "pH", "Disposal Method", "Remarks"
        ])
        self.waste_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.waste_table.setEditTriggers(QTableWidget.AllEditTriggers)
        
        # Setup Table Manager
        self.waste_table_manager = TableManager(self.waste_table, self)
        self.table_managers['waste'] = self.waste_table_manager  # <-- اضافه کردن این خط
        
        waste_table_layout.addWidget(self.waste_table)
        
        waste_btn_layout = QHBoxLayout()
        self.add_waste_btn = QPushButton("➕ Add Waste Record")
        self.remove_waste_btn = QPushButton("➖ Remove Row")
        self.calculate_waste_btn = QPushButton("🔄 Calculate Totals")
        self.export_waste_btn = QPushButton("📤 Export Waste Data")
        
        waste_btn_layout.addWidget(self.add_waste_btn)
        waste_btn_layout.addWidget(self.remove_waste_btn)
        waste_btn_layout.addWidget(self.calculate_waste_btn)
        waste_btn_layout.addWidget(self.export_waste_btn)
        waste_btn_layout.addStretch()
        
        waste_table_layout.addLayout(waste_btn_layout)
        waste_table_group.setLayout(waste_table_layout)
        layout.addWidget(waste_table_group)
        
        self.setLayout(layout)
    
    def setup_connections(self):
        """Setup signal connections"""
        self.add_waste_btn.clicked.connect(self.add_waste_row)
        self.remove_waste_btn.clicked.connect(self.remove_waste_row)
        self.calculate_waste_btn.clicked.connect(self.calculate_waste_totals)
        self.export_waste_btn.clicked.connect(self.export_waste_data)
    
    def add_waste_row(self):
        """Add row to waste table"""
        if 'waste' in self.table_managers:  # <-- اصلاح شده
            self.table_managers['waste'].add_row()
            row = self.waste_table.rowCount() - 1
            self.setup_waste_row_with_defaults(row)
        else:
            row = self.waste_table.rowCount()
            self.waste_table.insertRow(row)
            self.setup_waste_row_with_defaults(row)
    
    def setup_waste_row_with_defaults(self, row):
        """Setup waste row with default values"""
        today = QDate.currentDate()
        
        # Get values from form
        waste_type = self.waste_type.currentText()
        volume = self.cutting_volume.value()
        ph = self.waste_ph.value()
        disposal_method = self.disposal_method.currentText()
        remarks = self.waste_remarks.toPlainText() or "Daily record"
        
        # Add additional info to remarks
        full_remarks = f"{remarks} | TSS: {self.turbidity.text()} | Hardness: {self.hardness.text()} | Oil: {self.oil_content.value()}ppm"
        
        values = [
            today.toString("yyyy-MM-dd"),
            waste_type,
            f"{volume:.1f}",
            f"{ph:.1f}",
            disposal_method,
            full_remarks
        ]
        
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col in [2, 3]:  # Numeric columns
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.waste_table.setItem(row, col, item)
    
    def remove_waste_row(self):
        """Remove selected row from waste table"""
        if 'waste' in self.table_managers:  # <-- اصلاح شده
            self.table_managers['waste'].delete_row()
        else:
            current_row = self.waste_table.currentRow()
            if current_row >= 0:
                self.waste_table.removeRow(current_row)
    
    def calculate_waste_totals(self):
        """Calculate total waste volumes and statistics"""
        self.parent.show_progress("Calculating waste totals...")
        
        try:
            total_volume = 0
            volume_by_type = {}
            volume_by_method = {}
            ph_values = []
            
            for row in range(self.waste_table.rowCount()):
                type_item = self.waste_table.item(row, 1)
                volume_item = self.waste_table.item(row, 2)
                ph_item = self.waste_table.item(row, 3)
                method_item = self.waste_table.item(row, 4)
                
                if volume_item:
                    try:
                        # Extract numeric value from string
                        vol_text = volume_item.text()
                        vol_value = float(''.join(filter(str.isdigit, vol_text)) or 0)
                        total_volume += vol_value
                        
                        # By waste type
                        if type_item:
                            waste_type = type_item.text()
                            volume_by_type[waste_type] = volume_by_type.get(waste_type, 0) + vol_value
                        
                        # By disposal method
                        if method_item:
                            method = method_item.text()
                            volume_by_method[method] = volume_by_method.get(method, 0) + vol_value
                        
                        # Collect pH values
                        if ph_item:
                            try:
                                ph_text = ph_item.text()
                                ph = float(''.join(filter(lambda x: x.isdigit() or x == '.', ph_text)) or 7.0)
                                ph_values.append(ph)
                            except:
                                pass
                                
                    except ValueError:
                        continue
            
            # Calculate average pH
            avg_ph = sum(ph_values) / len(ph_values) if ph_values else 7.0
            
            # Generate report
            report = f"📊 **Waste Management Report**\n\n"
            report += f"📦 **Total Volume:** {total_volume:,.1f} BBL\n"
            report += f"📈 **Average pH:** {avg_ph:.1f}\n"
            report += f"📋 **Records:** {self.waste_table.rowCount()}\n\n"
            
            if volume_by_type:
                report += "**📋 By Waste Type:**\n"
                for waste_type, vol in volume_by_type.items():
                    percentage = (vol / total_volume * 100) if total_volume > 0 else 0
                    report += f"  • {waste_type}: {vol:,.1f} BBL ({percentage:.1f}%)\n"
            
            if volume_by_method:
                report += "\n**🗑️ By Disposal Method:**\n"
                for method, vol in volume_by_method.items():
                    percentage = (vol / total_volume * 100) if total_volume > 0 else 0
                    report += f"  • {method}: {vol:,.1f} BBL ({percentage:.1f}%)\n"
            
            # Show report
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Waste Management Report")
            msg_box.setText(report)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            
            self.parent.show_success("Waste totals calculated successfully")
            
        except Exception as e:
            self.parent.show_error(f"Error calculating waste totals: {str(e)}")
    
    def save_current_waste_data(self):
        """Save current waste data to history table"""
        try:
            # Add to table
            self.add_waste_row()
            
            # Clear form after saving
            self.clear_waste_form()
            
            self.parent.show_success("Current waste data saved to history")
            
        except Exception as e:
            self.parent.show_error(f"Failed to save data: {str(e)}")
    
    def clear_waste_form(self):
        """Clear waste management form"""
        self.recycled_volume.setValue(0)
        self.waste_ph.setValue(7.0)
        self.turbidity.clear()
        self.hardness.clear()
        self.cutting_volume.setValue(0)
        self.oil_content.setValue(0)
        self.waste_type.setCurrentIndex(0)
        self.disposal_method.setCurrentIndex(0)
        self.waste_remarks.clear()
    
    def export_waste_data(self):
        """Export waste data to file"""
        result = self.parent.export_manager.export_table_with_dialog(
            self.waste_table, "waste_data"
        )
        if result:
            self.parent.show_success(f"Waste data exported to {result}")
    
    def save_to_database(self, well_id, report_date):
        """Save waste data to database"""
        if not self.db:
            return False
        
        try:
            # Collect waste history data
            waste_history = []
            for row in range(self.waste_table.rowCount()):
                row_data = {}
                for col in range(self.waste_table.columnCount()):
                    header = self.waste_table.horizontalHeaderItem(col).text()
                    item = self.waste_table.item(row, col)
                    row_data[header] = item.text() if item else ""
                waste_history.append(row_data)
            
            # Prepare safety report data with waste info
            report_data = {
                'well_id': well_id,
                'report_date': report_date,
                'report_type': 'Daily',
                'recycled_volume': self.recycled_volume.value(),
                'waste_ph': self.waste_ph.value(),
                'turbidity': self.turbidity.text(),
                'hardness': self.hardness.text(),
                'cutting_volume': self.cutting_volume.value(),
                'oil_content': self.oil_content.value(),
                'waste_type': self.waste_type.currentText(),
                'disposal_method': self.disposal_method.currentText(),
                'waste_history_json': waste_history
            }
            
            # Save to database
            if hasattr(self.db, 'save_safety_report'):
                record_id = self.db.save_safety_report(report_data)
                if record_id:
                    # Save individual waste records
                    for waste_data in waste_history:
                        try:
                            # Parse volume
                            vol_text = waste_data.get('Volume (BBL)', '0')
                            volume = float(''.join(filter(str.isdigit, vol_text)) or 0)
                            
                            # Parse pH
                            ph_text = waste_data.get('pH', '7.0')
                            ph = float(''.join(filter(lambda x: x.isdigit() or x == '.', ph_text)) or 7.0)
                            
                            self.db.save_waste_record({
                                'well_id': well_id,
                                'safety_report_id': record_id,
                                'record_date': report_date,
                                'waste_type': waste_data.get('Type', ''),
                                'volume': volume,
                                'ph': ph,
                                'disposal_method': waste_data.get('Disposal Method', ''),
                                'remarks': waste_data.get('Remarks', '')
                            })
                        except Exception as e:
                            logger.error(f"Error saving waste record: {e}")
                            continue
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving waste data to database: {e}")
            return False
    
    def load_from_database(self, well_id, report_date):
        """Load waste data from database"""
        if not self.db:
            return False
        
        try:
            # Load safety report
            if hasattr(self.db, 'get_safety_report'):
                report_data = self.db.get_safety_report(well_id, report_date)
                if report_data:
                    # Load form fields
                    self.recycled_volume.setValue(report_data.get('recycled_volume', 0))
                    self.waste_ph.setValue(report_data.get('waste_ph', 7.0))
                    self.turbidity.setText(report_data.get('turbidity', ''))
                    self.hardness.setText(report_data.get('hardness', ''))
                    self.cutting_volume.setValue(report_data.get('cutting_volume', 0))
                    self.oil_content.setValue(report_data.get('oil_content', 0))
                    
                    waste_type = report_data.get('waste_type', 'Drilling Waste')
                    index = self.waste_type.findText(waste_type)
                    if index >= 0:
                        self.waste_type.setCurrentIndex(index)
                    
                    disposal_method = report_data.get('disposal_method', 'Landfill')
                    index = self.disposal_method.findText(disposal_method)
                    if index >= 0:
                        self.disposal_method.setCurrentIndex(index)
                    
                    # Load waste history
                    waste_history = report_data.get('waste_history_json', [])
                    self.waste_table.setRowCount(0)
                    for waste in waste_history:
                        row = self.waste_table.rowCount()
                        self.waste_table.insertRow(row)
                        for col, (key, value) in enumerate(waste.items()):
                            item = QTableWidgetItem(str(value))
                            self.waste_table.setItem(row, col, item)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading waste data from database: {e}")
            return False


# ==================== Safety Widget Main Class ====================

class SafetyWidget(DrillWidgetBase):
    """Main Safety Widget with Tabs"""
    
    def __init__(self, db_manager=None):
        super().__init__("SafetyWidget", db_manager)
        self.current_well = None
        self.current_report = None
        self.tabs = {}
        self.init_ui()
        
        # Setup with managers
        setup_widget_with_managers(
            self, "SafetyWidget", 
            enable_autosave=True, 
            autosave_interval=5, 
            setup_shortcuts=True
        )
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.safety_bop_tab = SafetyBOPTab(self)
        self.waste_tab = WasteManagementTab(self)
        
        # Add tabs to widget
        self.tab_widget.addTab(self.safety_bop_tab, "🛡️ Safety & BOP")
        self.tab_widget.addTab(self.waste_tab, "🗑️ Waste Management")
        
        # Store tab references
        self.tabs['safety_bop'] = self.safety_bop_tab
        self.tabs['waste'] = self.waste_tab
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        
        # Load sample data
        QTimer.singleShot(100, self.load_sample_data)
    
    def load_sample_data(self):
        """Load sample data into tables"""
        # تنظیم مقادیر ComboBox‌های BOP Test
        self.safety_bop_tab.bop_test_report.setCurrentText("Monthly Full Test")
        self.safety_bop_tab.test_status.setCurrentText("Completed - Pass")

        # BOP Table sample data
        bop_samples = [
            ("Upper Annular Preventer", "Annular", "10000", "13-5/8", "N/A", 
             QDate.currentDate().addDays(-15).toString("yyyy-MM-dd"),
             QDate.currentDate().addDays(15).toString("yyyy-MM-dd"),
             "Hydril Type, Good condition"),
            ("Lower Annular Preventer", "Annular", "10000", "13-5/8", "N/A",
             QDate.currentDate().addDays(-20).toString("yyyy-MM-dd"),
             QDate.currentDate().addDays(10).toString("yyyy-MM-dd"),
             "Shaffer Type, Minor wear"),
            ("Upper Pipe Rams", "Pipe Rams", "15000", "5", "5\" Variable",
             QDate.currentDate().addDays(-10).toString("yyyy-MM-dd"),
             QDate.currentDate().addDays(20).toString("yyyy-MM-dd"),
             "Variable Bore, Excellent"),
            ("Shear Rams", "Shear Rams", "15000", "All", "Shear",
             QDate.currentDate().addDays(-5).toString("yyyy-MM-dd"),
             QDate.currentDate().addDays(25).toString("yyyy-MM-dd"),
             "Emergency, Never used")
        ]
        
        for sample in bop_samples:
            self.safety_bop_tab.add_bop_row()
            row = self.safety_bop_tab.bop_stack_table.rowCount() - 1
            for col, value in enumerate(sample):
                item = QTableWidgetItem(value)
                self.safety_bop_tab.bop_stack_table.setItem(row, col, item)
        
        # Waste Table sample data
        waste_samples = [
            (QDate.currentDate().addDays(-5).toString("yyyy-MM-dd"), 
             "Drilling Waste", "120.5", "7.0", "Treatment",
             "Normal operations, shale formation"),
            (QDate.currentDate().addDays(-3).toString("yyyy-MM-dd"),
             "Cuttings", "45.2", "6.8", "Recycle",
             "Shale cuttings, good for cement"),
            (QDate.currentDate().addDays(-1).toString("yyyy-MM-dd"),
             "Mud", "75.8", "8.2", "Treatment",
             "Oil-based mud, requires special handling")
        ]
        
        for sample in waste_samples:
            self.waste_tab.add_waste_row()
            row = self.waste_tab.waste_table.rowCount() - 1
            for col, value in enumerate(sample):
                item = QTableWidgetItem(value)
                self.waste_tab.waste_table.setItem(row, col, item)
    
    def set_current_well(self, well_id):
        """Set current well for data operations"""
        self.current_well = well_id
        self.show_message(f"Current well set to ID: {well_id}")
    
    def set_current_report(self, report_id):
        """Set current report for data operations"""
        self.current_report = report_id
        self.show_message(f"Current report set to ID: {report_id}")
    
    def save_data(self):
        """Save all safety data to database"""
        if not self.current_well:
            self.show_error("No well selected. Please select a well first.")
            return False
        
        try:
            self.show_progress("Saving safety data...")
            
            # Get current date for report
            report_date = date.today()
            
            # Save Safety & BOP data
            safety_bop_saved = self.safety_bop_tab.save_to_database(
                self.current_well, report_date
            )
            
            # Save Waste Management data
            waste_saved = self.waste_tab.save_to_database(
                self.current_well, report_date
            )
            
            if safety_bop_saved or waste_saved:
                self.show_success("Safety data saved successfully")
                return True
            else:
                self.show_warning("No data to save or database error")
                return False
                
        except Exception as e:
            self.show_error(f"Save failed: {str(e)}")
            logger.error(f"Error saving safety data: {e}")
            return False
    
    def load_data(self):
        """Load safety data from database"""
        if not self.current_well:
            self.show_error("No well selected. Please select a well first.")
            return False
        
        try:
            self.show_progress("Loading safety data...")
            
            # Get today's date for report
            report_date = date.today()
            
            # Load Safety & BOP data
            safety_bop_loaded = self.safety_bop_tab.load_from_database(
                self.current_well, report_date
            )
            
            # Load Waste Management data
            waste_loaded = self.waste_tab.load_from_database(
                self.current_well, report_date
            )
            
            if safety_bop_loaded or waste_loaded:
                self.show_success("Safety data loaded successfully")
                return True
            else:
                self.show_message("No saved data found for today")
                return False
                
        except Exception as e:
            self.show_error(f"Load failed: {str(e)}")
            logger.error(f"Error loading safety data: {e}")
            return False
    
    def export_all_data(self):
        """Export all safety data"""
        try:
            # Determine which tab is active
            current_tab_index = self.tab_widget.currentIndex()
            
            if current_tab_index == 0:  # Safety & BOP tab
                self.safety_bop_tab.export_bop_data()
            elif current_tab_index == 1:  # Waste Management tab
                self.waste_tab.export_waste_data()
                
        except Exception as e:
            self.show_error(f"Export failed: {str(e)}")
    
    def clear_all_data(self):
        """Clear all safety data"""
        reply = QMessageBox.question(
            self, "Clear All Data",
            "Are you sure you want to clear all safety data? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Clear Safety & BOP tab
            self.safety_bop_tab.bop_stack_table.setRowCount(0)
            self.safety_bop_tab.last_fire_drill.setDate(QDate.currentDate().addDays(-7))
            self.safety_bop_tab.last_bop_drill.setDate(QDate.currentDate().addDays(-14))
            self.safety_bop_tab.last_h2s_drill.setDate(QDate.currentDate().addDays(-21))
            self.safety_bop_tab.days_no_lti.setValue(0)
            self.safety_bop_tab.last_rams_test.setDate(QDate.currentDate().addDays(-10))
            self.safety_bop_tab.test_pressure.setValue(0)
            self.safety_bop_tab.last_koomey_test.setDate(QDate.currentDate().addDays(-5))
            self.safety_bop_tab.days_since_last_test.setValue(0)
            
            # Clear Waste Management tab
            self.waste_tab.clear_waste_form()
            self.waste_tab.waste_table.setRowCount(0)
            
            self.show_success("All safety data cleared")
    
    def show_warning(self, message):
        """Show warning message"""
        self.status_manager.show_warning(self.widget_name, message)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for the widget"""
        from PySide6.QtGui import QShortcut, QKeySequence
        
        shortcuts = {
            "Ctrl+S": self.save_data,
            "Ctrl+L": self.load_data,
            "Ctrl+E": self.export_all_data,
            "Ctrl+Shift+C": self.clear_all_data,
            "Ctrl+A": self.add_current_row,
            "Ctrl+D": self.remove_current_row,
            "F5": self.refresh_data
        }
        
        for key_seq, slot in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key_seq), self)
            shortcut.activated.connect(slot)
    
    def add_current_row(self):
        """Add row to current table"""
        current_tab_index = self.tab_widget.currentIndex()
        
        if current_tab_index == 0:  # Safety & BOP tab
            self.safety_bop_tab.add_bop_row()
        elif current_tab_index == 1:  # Waste Management tab
            self.waste_tab.add_waste_row()
    
    def remove_current_row(self):
        """Remove row from current table"""
        current_tab_index = self.tab_widget.currentIndex()
        
        if current_tab_index == 0:  # Safety & BOP tab
            self.safety_bop_tab.remove_bop_row()
        elif current_tab_index == 1:  # Waste Management tab
            self.waste_tab.remove_waste_row()
    
    def refresh_data(self):
        """Refresh data from database"""
        self.load_data()
    
    def get_widget_data(self):
        """Get all widget data as dictionary for serialization"""
        data = {
            'widget_name': self.widget_name,
            'current_well': self.current_well,
            'current_report': self.current_report,
            'safety_bop_data': self.get_safety_bop_data(),
            'waste_data': self.get_waste_data()
        }
        return data
    
    def get_safety_bop_data(self):
        """Get Safety & BOP tab data"""
        return {
            'last_fire_drill': self.safety_bop_tab.last_fire_drill.date().toString("yyyy-MM-dd"),
            'last_bop_drill': self.safety_bop_tab.last_bop_drill.date().toString("yyyy-MM-dd"),
            'last_h2s_drill': self.safety_bop_tab.last_h2s_drill.date().toString("yyyy-MM-dd"),
            'days_no_lti': self.safety_bop_tab.days_no_lti.value(),
            'last_rams_test': self.safety_bop_tab.last_rams_test.date().toString("yyyy-MM-dd"),
            'test_pressure': self.safety_bop_tab.test_pressure.value(),
            'last_koomey_test': self.safety_bop_tab.last_koomey_test.date().toString("yyyy-MM-dd"),
            'days_since_last_test': self.safety_bop_tab.days_since_last_test.value(),
            'bop_test_report': self.safety_bop_tab.bop_test_report.currentText(),  # <-- اضافه شده
            'test_status': self.safety_bop_tab.test_status.currentText(),          # <-- اضافه شده
            'bop_components': self.get_table_data(self.safety_bop_tab.bop_stack_table)
        }
    
    def get_waste_data(self):
        """Get Waste Management tab data"""
        return {
            'recycled_volume': self.waste_tab.recycled_volume.value(),
            'waste_ph': self.waste_tab.waste_ph.value(),
            'turbidity': self.waste_tab.turbidity.text(),
            'hardness': self.waste_tab.hardness.text(),
            'cutting_volume': self.waste_tab.cutting_volume.value(),
            'oil_content': self.waste_tab.oil_content.value(),
            'waste_type': self.waste_tab.waste_type.currentText(),
            'disposal_method': self.waste_tab.disposal_method.currentText(),
            'waste_remarks': self.waste_tab.waste_remarks.toPlainText(),
            'waste_history': self.get_table_data(self.waste_tab.waste_table)
        }
    
    def get_table_data(self, table):
        """Get table data as list of dictionaries"""
        data = []
        for row in range(table.rowCount()):
            row_data = {}
            for col in range(table.columnCount()):
                header = table.horizontalHeaderItem(col).text()
                item = table.item(row, col)
                row_data[header] = item.text() if item else ""
            data.append(row_data)
        return data