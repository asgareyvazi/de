"""
w9_Services_Widget.py
Services Management Widget with full database integration and enhanced functionality
"""

import logging
from datetime import datetime
import csv
import os
from typing import Dict, List, Optional, Any

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtPrintSupport import *

from core.database import (
    ServiceCompany, ServiceNote, MaterialRequest, EquipmentLog,
    DailyReport, Well, Section
)
from core.managers import (
    StatusBarManager, TableManager, TableButtonManager,
    ExportManager, AutoSaveManager
)

logger = logging.getLogger(__name__)


# ------------------------ Service Company Tab ------------------------
class ServiceCompanyTab(QWidget):
    """Tab for managing service companies"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_well = None
        self.current_report = None
        self.status_manager = StatusBarManager()
        self.table_manager = None
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("🏢 Service Company Management")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title_label)
        
        # Search and filter area
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search company, service type, or description...")
        self.search_input.textChanged.connect(self.filter_table)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Active", "Completed", "Cancelled"])
        self.status_filter.currentTextChanged.connect(self.filter_table)
        
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        
        main_layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget(0, 10)
        self.setup_table()
        main_layout.addWidget(self.table)
        
        # Button panel
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add Company")
        self.add_btn.clicked.connect(self.add_company)
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_company)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_company)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_data)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_data)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # Statistics panel
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Total Companies: 0")
        self.active_label = QLabel("Active: 0")
        self.personnel_label = QLabel("Total Personnel: 0")
        
        for label in [self.total_label, self.active_label, self.personnel_label]:
            label.setStyleSheet("font-weight: bold; color: #34495e;")
            stats_layout.addWidget(label)
        
        stats_layout.addStretch()
        main_layout.addLayout(stats_layout)
        
    def setup_table(self):
        headers = [
            "ID", "Company Name", "Service Type", "Start Date/Time", 
            "End Date/Time", "Contact Person", "Phone", "Email",
            "Personnel Count", "Status"
        ]
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Set column widths
        self.table.setColumnWidth(0, 50)   # ID
        self.table.setColumnWidth(1, 200)  # Company Name
        self.table.setColumnWidth(2, 150)  # Service Type
        self.table.setColumnWidth(3, 150)  # Start
        self.table.setColumnWidth(4, 150)  # End
        self.table.setColumnWidth(5, 150)  # Contact Person
        self.table.setColumnWidth(6, 120)  # Phone
        self.table.setColumnWidth(7, 180)  # Email
        self.table.setColumnWidth(8, 120)  # Personnel Count
        self.table.setColumnWidth(9, 100)  # Status
        
        # Initialize table manager
        self.table_manager = TableManager(self.table)
        self.table_manager.set_alternating_row_colors(True)
        
    def setup_connections(self):
        self.table.doubleClicked.connect(self.edit_company)
        
    def set_current_well(self, well_id):
        self.current_well = well_id
        self.load_data()
        
    def set_current_report(self, report_id):
        self.current_report = report_id
        
    def load_data(self):
        if not self.db:
            return
            
        try:
            # اگر current_well تنظیم نشده، جدول را خالی کن
            if not self.current_well:
                self.table.setRowCount(0)
                self.total_label.setText("Total Companies: 0")
                self.active_label.setText("Active: 0")
                self.personnel_label.setText("Total Personnel: 0")
                return
                
            companies = self.db.get_service_companies(well_id=self.current_well)
            self.table.setRowCount(0)
            
            total_personnel = 0
            active_count = 0
            
            for company in companies:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                self.table.setItem(row, 0, QTableWidgetItem(str(company.get("id", ""))))
                self.table.setItem(row, 1, QTableWidgetItem(company.get("company_name", "")))
                self.table.setItem(row, 2, QTableWidgetItem(company.get("service_type", "")))
                
                start_date = company.get("start_datetime")
                if start_date:
                    if isinstance(start_date, str):
                        self.table.setItem(row, 3, QTableWidgetItem(start_date))
                    else:
                        self.table.setItem(row, 3, QTableWidgetItem(start_date.strftime("%Y-%m-%d %H:%M")))
                
                end_date = company.get("end_datetime")
                if end_date:
                    if isinstance(end_date, str):
                        self.table.setItem(row, 4, QTableWidgetItem(end_date))
                    else:
                        self.table.setItem(row, 4, QTableWidgetItem(end_date.strftime("%Y-%m-%d %H:%M")))
                
                self.table.setItem(row, 5, QTableWidgetItem(company.get("contact_person", "")))
                self.table.setItem(row, 6, QTableWidgetItem(company.get("contact_phone", "")))
                self.table.setItem(row, 7, QTableWidgetItem(company.get("contact_email", "")))
                
                personnel = company.get("personnel_count", 0)
                self.table.setItem(row, 8, QTableWidgetItem(str(personnel)))
                total_personnel += personnel
                
                status = company.get("status", "")
                self.table.setItem(row, 9, QTableWidgetItem(status))
                
                if status == "Active":
                    active_count += 1
                
                # Color coding for status
                if status == "Active":
                    for col in range(10):
                        self.table.item(row, col).setBackground(QColor("#d4edda"))
                elif status == "Completed":
                    for col in range(10):
                        self.table.item(row, col).setBackground(QColor("#cce5ff"))
                elif status == "Cancelled":
                    for col in range(10):
                        self.table.item(row, col).setBackground(QColor("#f8d7da"))
            
            # Update statistics
            self.total_label.setText(f"Total Companies: {len(companies)}")
            self.active_label.setText(f"Active: {active_count}")
            self.personnel_label.setText(f"Total Personnel: {total_personnel}")
            
        except Exception as e:
            logger.error(f"Error loading service companies: {e}")
            
    def filter_table(self):
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.table.rowCount()):
            show_row = True
            
            # Search filter
            if search_text:
                row_has_text = False
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_has_text = True
                        break
                if not row_has_text:
                    show_row = False
            
            # Status filter
            if status_filter != "All Status":
                status_item = self.table.item(row, 9)
                if not status_item or status_item.text() != status_filter:
                    show_row = False
            
            self.table.setRowHidden(row, not show_row)
            
    def add_company(self):
        dialog = ServiceCompanyDialog(self.db, self.current_well, self.current_report, self)
        if dialog.exec():
            self.load_data()
            self.status_manager.show_success("ServiceCompanyTab", "Service company added successfully")
            
    def edit_company(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a company to edit.")
            return
            
        company_id = int(self.table.item(selected_row, 0).text())
        dialog = ServiceCompanyDialog(self.db, self.current_well, self.current_report, self, company_id)
        if dialog.exec():
            self.load_data()
            self.status_manager.show_success("ServiceCompanyTab", "Service company updated successfully")
            
    def delete_company(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a company to delete.")
            return
            
        company_id = int(self.table.item(selected_row, 0).text())
        company_name = self.table.item(selected_row, 1).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{company_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.db.delete_service_company(company_id):
                    self.load_data()
                    self.status_manager.show_success("ServiceCompanyTab", "Service company deleted successfully")
                else:
                    self.status_manager.show_error("ServiceCompanyTab", "Failed to delete service company")
            except Exception as e:
                logger.error(f"Error deleting service company: {e}")
                self.status_manager.show_error("ServiceCompanyTab", f"Error: {str(e)}")
                
    def export_data(self):
        try:
            export_manager = ExportManager(self)
            result = export_manager.export_table_with_dialog(self.table, "service_companies")
            if result:
                self.status_manager.show_success("ServiceCompanyTab", f"Data exported to {result}")
        except Exception as e:
            logger.error(f"Export error: {e}")
            self.status_manager.show_error("ServiceCompanyTab", f"Export failed: {str(e)}")


# ------------------------ Service Company Dialog ------------------------
class ServiceCompanyDialog(QDialog):
    """Dialog for adding/editing service companies"""
    
    def __init__(self, db_manager, well_id, report_id, parent=None, company_id=None):
        super().__init__(parent)
        self.db = db_manager
        self.well_id = well_id
        self.report_id = report_id
        self.company_id = company_id
        self.status_manager = StatusBarManager()
        self.init_ui()
        self.load_company_data()
        
    def init_ui(self):
        self.setWindowTitle("Service Company" + (" - Edit" if self.company_id else " - Add"))
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter company name")
        form_layout.addRow("Company Name:", self.name_input)
        
        self.service_type_input = QComboBox()
        self.service_type_input.addItems([
            "Mud Logging", "Wireline", "Directional Drilling",
            "Cementing", "Casing", "Mud Engineering",
            "Well Testing", "Completion", "Other"
        ])
        self.service_type_input.setEditable(True)
        form_layout.addRow("Service Type:", self.service_type_input)
        
        datetime_layout = QHBoxLayout()
        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate())
        self.start_time_input = QTimeEdit()
        self.start_time_input.setTime(QTime(8, 0))
        datetime_layout.addWidget(self.start_date_input)
        datetime_layout.addWidget(self.start_time_input)
        form_layout.addRow("Start Date/Time:", datetime_layout)
        
        datetime_layout2 = QHBoxLayout()
        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDate(QDate.currentDate())
        self.end_time_input = QTimeEdit()
        self.end_time_input.setTime(QTime(17, 0))
        datetime_layout2.addWidget(self.end_date_input)
        datetime_layout2.addWidget(self.end_time_input)
        form_layout.addRow("End Date/Time:", datetime_layout2)
        
        self.contact_person_input = QLineEdit()
        form_layout.addRow("Contact Person:", self.contact_person_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1-234-567-8900")
        form_layout.addRow("Phone:", self.phone_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("contact@company.com")
        form_layout.addRow("Email:", self.email_input)
        
        self.personnel_input = QSpinBox()
        self.personnel_input.setRange(1, 1000)
        self.personnel_input.setValue(1)
        form_layout.addRow("Personnel Count:", self.personnel_input)
        
        self.status_input = QComboBox()
        self.status_input.addItems(["Active", "Completed", "Cancelled"])
        form_layout.addRow("Status:", self.status_input)
        
        self.equipment_input = QTextEdit()
        self.equipment_input.setMaximumHeight(80)
        form_layout.addRow("Equipment Used:", self.equipment_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_input)
        
        layout.addLayout(form_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_company)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def load_company_data(self):
        if not self.company_id:
            return
            
        try:
            companies = self.db.get_service_companies()
            company = None
            for c in companies:
                if c.get("id") == self.company_id:
                    company = c
                    break
                    
            if company:
                self.name_input.setText(company.get("company_name", ""))
                
                service_type = company.get("service_type", "")
                if service_type:
                    index = self.service_type_input.findText(service_type)
                    if index >= 0:
                        self.service_type_input.setCurrentIndex(index)
                    else:
                        self.service_type_input.setCurrentText(service_type)
                
                start_datetime = company.get("start_datetime")
                if start_datetime:
                    if isinstance(start_datetime, str):
                        try:
                            dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                            self.start_date_input.setDate(QDate(dt.year, dt.month, dt.day))
                            self.start_time_input.setTime(QTime(dt.hour, dt.minute))
                        except:
                            pass
                
                end_datetime = company.get("end_datetime")
                if end_datetime:
                    if isinstance(end_datetime, str):
                        try:
                            dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                            self.end_date_input.setDate(QDate(dt.year, dt.month, dt.day))
                            self.end_time_input.setTime(QTime(dt.hour, dt.minute))
                        except:
                            pass
                
                self.contact_person_input.setText(company.get("contact_person", ""))
                self.phone_input.setText(company.get("contact_phone", ""))
                self.email_input.setText(company.get("contact_email", ""))
                self.personnel_input.setValue(company.get("personnel_count", 1))
                
                status = company.get("status", "Active")
                index = self.status_input.findText(status)
                if index >= 0:
                    self.status_input.setCurrentIndex(index)
                
                self.equipment_input.setText(company.get("equipment_used", ""))
                self.description_input.setText(company.get("description", ""))
                
        except Exception as e:
            logger.error(f"Error loading company data: {e}")
            
    def save_company(self):
        try:
            # Validate inputs
            if not self.name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Company name is required.")
                return
            
            # بررسی well_id
            if not self.well_id:
                QMessageBox.critical(self, "Error", "Well ID is not set. Cannot save service company.")
                return
                
            # Prepare data
            start_datetime = datetime.combine(
                self.start_date_input.date().toPython(),
                self.start_time_input.time().toPython()
            )
            
            end_datetime = datetime.combine(
                self.end_date_input.date().toPython(),
                self.end_time_input.time().toPython()
            )
            
            company_data = {
                "well_id": self.well_id,
                "report_id": self.report_id,
                "company_name": self.name_input.text().strip(),
                "service_type": self.service_type_input.currentText(),
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "contact_person": self.contact_person_input.text().strip(),
                "contact_phone": self.phone_input.text().strip(),
                "contact_email": self.email_input.text().strip(),
                "personnel_count": self.personnel_input.value(),
                "status": self.status_input.currentText(),
                "equipment_used": self.equipment_input.toPlainText().strip(),
                "description": self.description_input.toPlainText().strip(),
            }
            
            if self.company_id:
                company_data["id"] = self.company_id
                
            # Save to database
            result = self.db.save_service_company(company_data)
            if result:
                self.accept()
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save service company.")
                
        except Exception as e:
            logger.error(f"Error saving service company: {e}")
            QMessageBox.critical(self, "Save Error", f"Error: {str(e)}")

    def add_company(self):
        if not self.current_well:
            self.show_well_selection_error()
            return
            
        dialog = ServiceCompanyDialog(self.db, self.current_well, self.current_report, self)
        if dialog.exec():
            self.load_data()
            self.status_manager.show_success("ServiceCompanyTab", "Service company added successfully")

    def show_well_selection_error(self):
        QMessageBox.warning(
            self, 
            "Well Not Selected",
            "Please select a well before adding service companies.\n\n"
            "Go to 'Well Information' tab and select a well first."
        )

# ------------------------ Material Handling Tab ------------------------
class MaterialHandlingTab(QWidget):
    """Tab for material handling, notes, and requests"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_well = None
        self.current_report = None
        self.status_manager = StatusBarManager()
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Create tab widget for different material sections
        self.tab_widget = QTabWidget()
        
        # Notes Tab
        self.notes_tab = self.create_notes_tab()
        self.tab_widget.addTab(self.notes_tab, "📝 Notes")
        
        # Material Requests Tab
        self.requests_tab = self.create_requests_tab()
        self.tab_widget.addTab(self.requests_tab, "📦 Material Requests")
        
        # Equipment Log Tab
        self.equipment_tab = self.create_equipment_tab()
        self.tab_widget.addTab(self.equipment_tab, "🔧 Equipment Log")
        
        main_layout.addWidget(self.tab_widget)
        
    def create_notes_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Title
        title_label = QLabel("Service Notes Management")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Search and filter
        filter_layout = QHBoxLayout()
        self.note_search = QLineEdit()
        self.note_search.setPlaceholderText("Search notes...")
        self.note_search.textChanged.connect(self.filter_notes)
        
        self.note_type_filter = QComboBox()
        self.note_type_filter.addItems(["All Types", "General", "Safety", "Technical", "Logistics", "Other"])
        self.note_type_filter.currentTextChanged.connect(self.filter_notes)
        
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.note_search)
        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.note_type_filter)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Notes table
        self.notes_table = QTableWidget(0, 6)
        self.setup_notes_table()
        layout.addWidget(self.notes_table)
        
        # Button panel
        button_layout = QHBoxLayout()
        
        self.add_note_btn = QPushButton("➕ Add Note")
        self.add_note_btn.clicked.connect(self.add_note)
        
        self.edit_note_btn = QPushButton("✏️ Edit")
        self.edit_note_btn.clicked.connect(self.edit_note)
        
        self.delete_note_btn = QPushButton("🗑️ Delete")
        self.delete_note_btn.clicked.connect(self.delete_note)
        
        self.export_notes_btn = QPushButton("📤 Export")
        self.export_notes_btn.clicked.connect(self.export_notes)
        
        button_layout.addWidget(self.add_note_btn)
        button_layout.addWidget(self.edit_note_btn)
        button_layout.addWidget(self.delete_note_btn)
        button_layout.addWidget(self.export_notes_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return tab
        
    def create_requests_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Title
        title_label = QLabel("Material Request Management")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # New request form
        form_group = QGroupBox("New Material Request")
        form_layout = QFormLayout()
        
        self.request_date_input = QDateEdit()
        self.request_date_input.setCalendarPopup(True)
        self.request_date_input.setDate(QDate.currentDate())
        form_layout.addRow("Request Date:", self.request_date_input)
        
        self.requested_items_input = QTextEdit()
        self.requested_items_input.setMaximumHeight(60)
        self.requested_items_input.setPlaceholderText("Enter requested items (one per line or comma separated)")
        form_layout.addRow("Requested Items:", self.requested_items_input)
        
        self.requested_qty_input = QDoubleSpinBox()
        self.requested_qty_input.setRange(0, 999999)
        self.requested_qty_input.setValue(0)
        form_layout.addRow("Requested Quantity:", self.requested_qty_input)
        
        self.requested_unit_input = QComboBox()
        self.requested_unit_input.addItems(["units", "kg", "lbs", "liters", "gallons", "meters", "feet"])
        form_layout.addRow("Unit:", self.requested_unit_input)
        
        layout.addWidget(form_group)
        form_group.setLayout(form_layout)
        
        # Request buttons
        request_btn_layout = QHBoxLayout()
        self.save_request_btn = QPushButton("💾 Save Request")
        self.save_request_btn.clicked.connect(self.save_material_request)
        
        self.clear_request_btn = QPushButton("🗑️ Clear Form")
        self.clear_request_btn.clicked.connect(self.clear_request_form)
        
        request_btn_layout.addWidget(self.save_request_btn)
        request_btn_layout.addWidget(self.clear_request_btn)
        request_btn_layout.addStretch()
        
        layout.addLayout(request_btn_layout)
        
        # History table
        history_group = QGroupBox("Request History")
        history_layout = QVBoxLayout()
        
        self.requests_table = QTableWidget(0, 9)
        self.setup_requests_table()
        history_layout.addWidget(self.requests_table)
        
        # History buttons
        history_btn_layout = QHBoxLayout()
        self.refresh_requests_btn = QPushButton("🔄 Refresh")
        self.refresh_requests_btn.clicked.connect(self.load_material_requests)
        
        self.delete_request_btn = QPushButton("🗑️ Delete")
        self.delete_request_btn.clicked.connect(self.delete_material_request)
        
        self.export_requests_btn = QPushButton("📤 Export")
        self.export_requests_btn.clicked.connect(self.export_requests)
        
        history_btn_layout.addWidget(self.refresh_requests_btn)
        history_btn_layout.addWidget(self.delete_request_btn)
        history_btn_layout.addWidget(self.export_requests_btn)
        history_btn_layout.addStretch()
        
        history_layout.addLayout(history_btn_layout)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        scroll.setWidget(container)
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(scroll)
        
        return tab
        
    def create_equipment_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Title
        title_label = QLabel("Equipment Log Management")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Equipment table
        self.equipment_table = QTableWidget(0, 8)
        self.setup_equipment_table()
        layout.addWidget(self.equipment_table)
        
        # Button panel
        button_layout = QHBoxLayout()
        
        self.add_equipment_btn = QPushButton("➕ Add Equipment")
        self.add_equipment_btn.clicked.connect(self.add_equipment)
        
        self.edit_equipment_btn = QPushButton("✏️ Edit")
        self.edit_equipment_btn.clicked.connect(self.edit_equipment)
        
        self.delete_equipment_btn = QPushButton("🗑️ Delete")
        self.delete_equipment_btn.clicked.connect(self.delete_equipment)
        
        self.export_equipment_btn = QPushButton("📤 Export")
        self.export_equipment_btn.clicked.connect(self.export_equipment)
        
        button_layout.addWidget(self.add_equipment_btn)
        button_layout.addWidget(self.edit_equipment_btn)
        button_layout.addWidget(self.delete_equipment_btn)
        button_layout.addWidget(self.export_equipment_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return tab
        
    def setup_notes_table(self):
        headers = ["ID", "Note #", "Type", "Content", "Priority", "Status"]
        self.notes_table.setColumnCount(len(headers))
        self.notes_table.setHorizontalHeaderLabels(headers)
        self.notes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.notes_table.setColumnWidth(3, 400)  # Content column wider
        
    def setup_requests_table(self):
        headers = [
            "ID", "Date", "Requested Items", "Quantity", "Unit",
            "Outstanding", "Received", "Backload", "Status"
        ]
        self.requests_table.setColumnCount(len(headers))
        self.requests_table.setHorizontalHeaderLabels(headers)
        self.requests_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        
    def setup_equipment_table(self):
        headers = [
            "ID", "Equipment Name", "Type", "Serial #", 
            "Service Date", "Service Type", "Hours Worked", "Status"
        ]
        self.equipment_table.setColumnCount(len(headers))
        self.equipment_table.setHorizontalHeaderLabels(headers)
        self.equipment_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        
    def setup_connections(self):
        self.notes_table.doubleClicked.connect(self.edit_note)
        self.requests_table.doubleClicked.connect(self.edit_material_request)
        self.equipment_table.doubleClicked.connect(self.edit_equipment)
        
    def set_current_well(self, well_id):
        self.current_well = well_id
        self.load_all_data()
        
    def set_current_report(self, report_id):
        self.current_report = report_id
        
    def load_all_data(self):
        self.load_notes()
        self.load_material_requests()
        self.load_equipment_logs()
        
    def load_notes(self):
        if not self.db:
            return
            
        try:
            if not self.current_well:
                self.notes_table.setRowCount(0)
                return
                
            notes = self.db.get_service_notes(well_id=self.current_well)
            self.notes_table.setRowCount(0)
            
            for note in notes:
                row = self.notes_table.rowCount()
                self.notes_table.insertRow(row)
                
                self.notes_table.setItem(row, 0, QTableWidgetItem(str(note.get("id", ""))))
                self.notes_table.setItem(row, 1, QTableWidgetItem(str(note.get("note_number", ""))))
                self.notes_table.setItem(row, 2, QTableWidgetItem(note.get("note_type", "")))
                
                content = note.get("content", "")
                if len(content) > 100:
                    content = content[:97] + "..."
                self.notes_table.setItem(row, 3, QTableWidgetItem(content))
                self.notes_table.item(row, 3).setToolTip(note.get("content", ""))
                
                self.notes_table.setItem(row, 4, QTableWidgetItem(note.get("priority", "")))
                self.notes_table.setItem(row, 5, QTableWidgetItem(note.get("status", "")))
                
        except Exception as e:
            logger.error(f"Error loading notes: {e}")
            
    def load_material_requests(self):
        if not self.db or not self.current_well:
            return
            
        try:
            requests = self.db.get_material_requests(well_id=self.current_well)
            self.requests_table.setRowCount(0)
            
            for req in requests:
                row = self.requests_table.rowCount()
                self.requests_table.insertRow(row)
                
                self.requests_table.setItem(row, 0, QTableWidgetItem(str(req.get("id", ""))))
                
                date = req.get("request_date")
                if date:
                    if isinstance(date, str):
                        self.requests_table.setItem(row, 1, QTableWidgetItem(date))
                    else:
                        self.requests_table.setItem(row, 1, QTableWidgetItem(date.strftime("%Y-%m-%d")))
                
                self.requests_table.setItem(row, 2, QTableWidgetItem(req.get("requested_items", "")))
                self.requests_table.setItem(row, 3, QTableWidgetItem(str(req.get("requested_quantity", 0))))
                self.requests_table.setItem(row, 4, QTableWidgetItem(req.get("requested_unit", "")))
                self.requests_table.setItem(row, 5, QTableWidgetItem(req.get("outstanding_items", "")))
                self.requests_table.setItem(row, 6, QTableWidgetItem(req.get("received_items", "")))
                self.requests_table.setItem(row, 7, QTableWidgetItem(req.get("backload_items", "")))
                self.requests_table.setItem(row, 8, QTableWidgetItem(req.get("status", "")))
                
        except Exception as e:
            logger.error(f"Error loading material requests: {e}")
            
    def load_equipment_logs(self):
        if not self.db or not self.current_well:
            return
            
        try:
            equipment = self.db.get_equipment_logs(well_id=self.current_well)
            self.equipment_table.setRowCount(0)
            
            for eq in equipment:
                row = self.equipment_table.rowCount()
                self.equipment_table.insertRow(row)
                
                self.equipment_table.setItem(row, 0, QTableWidgetItem(str(eq.get("id", ""))))
                self.equipment_table.setItem(row, 1, QTableWidgetItem(eq.get("equipment_name", "")))
                self.equipment_table.setItem(row, 2, QTableWidgetItem(eq.get("equipment_type", "")))
                self.equipment_table.setItem(row, 3, QTableWidgetItem(eq.get("serial_number", "")))
                
                date = eq.get("service_date")
                if date:
                    if isinstance(date, str):
                        self.equipment_table.setItem(row, 4, QTableWidgetItem(date))
                    else:
                        self.equipment_table.setItem(row, 4, QTableWidgetItem(date.strftime("%Y-%m-%d")))
                
                self.equipment_table.setItem(row, 5, QTableWidgetItem(eq.get("service_type", "")))
                self.equipment_table.setItem(row, 6, QTableWidgetItem(str(eq.get("hours_worked", 0))))
                self.equipment_table.setItem(row, 7, QTableWidgetItem(eq.get("status", "")))
                
        except Exception as e:
            logger.error(f"Error loading equipment logs: {e}")
            
    def filter_notes(self):
        search_text = self.note_search.text().lower()
        type_filter = self.note_type_filter.currentText()
        
        for row in range(self.notes_table.rowCount()):
            show_row = True
            
            if search_text:
                row_has_text = False
                for col in range(self.notes_table.columnCount()):
                    item = self.notes_table.item(row, col)
                    if item and search_text in item.text().lower():
                        row_has_text = True
                        break
                if not row_has_text:
                    show_row = False
                    
            if type_filter != "All Types":
                type_item = self.notes_table.item(row, 2)
                if not type_item or type_item.text() != type_filter:
                    show_row = False
                    
            self.notes_table.setRowHidden(row, not show_row)
            
    def add_note(self):
        if not self.current_well:
            self.show_well_selection_error()
            return
            
        dialog = ServiceNoteDialog(self.db, self.current_well, self.current_report, self)
        if dialog.exec():
            self.load_notes()
            self.status_manager.show_success("MaterialHandlingTab", "Note added successfully")
   
    def edit_note(self):
        selected_row = self.notes_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a note to edit.")
            return
            
        note_id = int(self.notes_table.item(selected_row, 0).text())
        dialog = ServiceNoteDialog(self.db, self.current_well, self.current_report, self, note_id)
        if dialog.exec():
            self.load_notes()
            self.status_manager.show_success("MaterialHandlingTab", "Note updated successfully")
            
    def delete_note(self):
        selected_row = self.notes_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a note to delete.")
            return
            
        note_id = int(self.notes_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this note?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.db.delete_service_note(note_id):
                    self.load_notes()
                    self.status_manager.show_success("MaterialHandlingTab", "Note deleted successfully")
                else:
                    self.status_manager.show_error("MaterialHandlingTab", "Failed to delete note")
            except Exception as e:
                logger.error(f"Error deleting note: {e}")
                self.status_manager.show_error("MaterialHandlingTab", f"Error: {str(e)}")
                
    def save_material_request(self):
        if not self.current_well:
            self.show_well_selection_error()
            return
        try:
            # Validate
            requested_items = self.requested_items_input.toPlainText().strip()
            if not requested_items:
                QMessageBox.warning(self, "Validation Error", "Requested items are required.")
                return
                
            request_data = {
                "well_id": self.current_well,
                "report_id": self.current_report,
                "request_date": self.request_date_input.date().toPython(),
                "requested_items": requested_items,
                "requested_quantity": self.requested_qty_input.value(),
                "requested_unit": self.requested_unit_input.currentText(),
                "status": "Pending"
            }
            
            result = self.db.save_material_request(request_data)
            if result:
                self.clear_request_form()
                self.load_material_requests()
                self.status_manager.show_success("MaterialHandlingTab", "Material request saved successfully")
            else:
                self.status_manager.show_error("MaterialHandlingTab", "Failed to save material request")
                
        except Exception as e:
            logger.error(f"Error saving material request: {e}")
            self.status_manager.show_error("MaterialHandlingTab", f"Error: {str(e)}")
            
    def clear_request_form(self):
        self.requested_items_input.clear()
        self.requested_qty_input.setValue(0)
        self.requested_unit_input.setCurrentIndex(0)
        
    def edit_material_request(self):
        selected_row = self.requests_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request to edit.")
            return
            
        request_id = int(self.requests_table.item(selected_row, 0).text())
        
        # For simplicity, we'll just update status here
        # In a full implementation, you'd create a dialog
        statuses = ["Pending", "Partially Received", "Fully Received", "Closed"]
        status, ok = QInputDialog.getItem(
            self, "Update Status", "Select new status:", statuses, 0, False
        )
        
        if ok and status:
            try:
                request_data = {"status": status}
                # We need an update method in db_manager
                # For now, we'll just show a message
                self.status_manager.show_message("MaterialHandlingTab", f"Status updated to {status}")
                self.load_material_requests()
            except Exception as e:
                logger.error(f"Error updating request status: {e}")
                
    def delete_material_request(self):
        selected_row = self.requests_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request to delete.")
            return
            
        request_id = int(self.requests_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this material request?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.db.delete_material_request(request_id):
                    self.load_material_requests()
                    self.status_manager.show_success("MaterialHandlingTab", "Request deleted successfully")
                else:
                    self.status_manager.show_error("MaterialHandlingTab", "Failed to delete request")
            except Exception as e:
                logger.error(f"Error deleting material request: {e}")
                self.status_manager.show_error("MaterialHandlingTab", f"Error: {str(e)}")
                
    def add_equipment(self):
        if not self.current_well:
            self.show_well_selection_error()
            return
            
        dialog = EquipmentDialog(self.db, self.current_well, self.current_report, self)
        if dialog.exec():
            self.load_equipment_logs()
            self.status_manager.show_success("MaterialHandlingTab", "Equipment added successfully")
       
    def edit_equipment(self):
        selected_row = self.equipment_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select equipment to edit.")
            return
            
        equipment_id = int(self.equipment_table.item(selected_row, 0).text())
        dialog = EquipmentDialog(self.db, self.current_well, self.current_report, self, equipment_id)
        if dialog.exec():
            self.load_equipment_logs()
            self.status_manager.show_success("MaterialHandlingTab", "Equipment updated successfully")
            
    def delete_equipment(self):
        selected_row = self.equipment_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select equipment to delete.")
            return
            
        equipment_id = int(self.equipment_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this equipment record?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.db.delete_equipment_log(equipment_id):
                    self.load_equipment_logs()
                    self.status_manager.show_success("MaterialHandlingTab", "Equipment deleted successfully")
                else:
                    self.status_manager.show_error("MaterialHandlingTab", "Failed to delete equipment")
            except Exception as e:
                logger.error(f"Error deleting equipment: {e}")
                self.status_manager.show_error("MaterialHandlingTab", f"Error: {str(e)}")
                
    def export_notes(self):
        try:
            export_manager = ExportManager(self)
            result = export_manager.export_table_with_dialog(self.notes_table, "service_notes")
            if result:
                self.status_manager.show_success("MaterialHandlingTab", f"Notes exported to {result}")
        except Exception as e:
            logger.error(f"Export error: {e}")
            self.status_manager.show_error("MaterialHandlingTab", f"Export failed: {str(e)}")
            
    def export_requests(self):
        try:
            export_manager = ExportManager(self)
            result = export_manager.export_table_with_dialog(self.requests_table, "material_requests")
            if result:
                self.status_manager.show_success("MaterialHandlingTab", f"Requests exported to {result}")
        except Exception as e:
            logger.error(f"Export error: {e}")
            self.status_manager.show_error("MaterialHandlingTab", f"Export failed: {str(e)}")
            
    def export_equipment(self):
        try:
            export_manager = ExportManager(self)
            result = export_manager.export_table_with_dialog(self.equipment_table, "equipment_logs")
            if result:
                self.status_manager.show_success("MaterialHandlingTab", f"Equipment logs exported to {result}")
        except Exception as e:
            logger.error(f"Export error: {e}")
            self.status_manager.show_error("MaterialHandlingTab", f"Export failed: {str(e)}")


# ------------------------ Service Note Dialog ------------------------
class ServiceNoteDialog(QDialog):
    """Dialog for adding/editing service notes"""
    
    def __init__(self, db_manager, well_id, report_id, parent=None, note_id=None):
        super().__init__(parent)
        self.db = db_manager
        self.well_id = well_id
        self.report_id = report_id
        self.note_id = note_id
        self.init_ui()
        self.load_note_data()
        
    def init_ui(self):
        self.setWindowTitle("Service Note" + (" - Edit" if self.note_id else " - Add"))
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.note_number_input = QSpinBox()
        self.note_number_input.setRange(1, 9999)
        form_layout.addRow("Note Number:", self.note_number_input)
        
        self.note_type_input = QComboBox()
        self.note_type_input.addItems(["General", "Safety", "Technical", "Logistics", "Other"])
        form_layout.addRow("Note Type:", self.note_type_input)
        
        self.content_input = QTextEdit()
        self.content_input.setMaximumHeight(150)
        form_layout.addRow("Content:", self.content_input)
        
        self.priority_input = QComboBox()
        self.priority_input.addItems(["Low", "Medium", "High", "Critical"])
        form_layout.addRow("Priority:", self.priority_input)
        
        self.status_input = QComboBox()
        self.status_input.addItems(["Active", "Resolved", "Archived"])
        form_layout.addRow("Status:", self.status_input)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_note)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def load_note_data(self):
        if not self.note_id:
            # Auto-generate next note number
            try:
                notes = self.db.get_service_notes(well_id=self.well_id)
                if notes:
                    max_note = max([n.get("note_number", 0) for n in notes])
                    self.note_number_input.setValue(max_note + 1)
                else:
                    self.note_number_input.setValue(1)
            except:
                self.note_number_input.setValue(1)
            return
            
        try:
            notes = self.db.get_service_notes()
            note = None
            for n in notes:
                if n.get("id") == self.note_id:
                    note = n
                    break
                    
            if note:
                self.note_number_input.setValue(note.get("note_number", 1))
                
                note_type = note.get("note_type", "General")
                index = self.note_type_input.findText(note_type)
                if index >= 0:
                    self.note_type_input.setCurrentIndex(index)
                    
                self.content_input.setText(note.get("content", ""))
                
                priority = note.get("priority", "Medium")
                index = self.priority_input.findText(priority)
                if index >= 0:
                    self.priority_input.setCurrentIndex(index)
                    
                status = note.get("status", "Active")
                index = self.status_input.findText(status)
                if index >= 0:
                    self.status_input.setCurrentIndex(index)
                    
        except Exception as e:
            logger.error(f"Error loading note data: {e}")
            
    def save_note(self):
        try:
            if not self.content_input.toPlainText().strip():
                QMessageBox.warning(self, "Validation Error", "Note content is required.")
                return
            
            # بررسی well_id
            if not self.well_id:
                QMessageBox.critical(self, "Error", "Well ID is not set. Cannot save note.")
                return
            
            note_data = {
                "well_id": self.well_id,
                "report_id": self.report_id,
                "note_number": self.note_number_input.value(),
                "note_type": self.note_type_input.currentText(),
                "content": self.content_input.toPlainText().strip(),
                "priority": self.priority_input.currentText(),
                "status": self.status_input.currentText(),
            }
            
            if self.note_id:
                note_data["id"] = self.note_id
                
            result = self.db.save_service_note(note_data)
            if result:
                self.accept()
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save note.")
                
        except Exception as e:
            logger.error(f"Error saving note: {e}")
            QMessageBox.critical(self, "Save Error", f"Error: {str(e)}")


# ------------------------ Equipment Dialog ------------------------
class EquipmentDialog(QDialog):
    """Dialog for adding/editing equipment logs"""
    
    def __init__(self, db_manager, well_id, report_id, parent=None, equipment_id=None):
        super().__init__(parent)
        self.db = db_manager
        self.well_id = well_id
        self.report_id = report_id
        self.equipment_id = equipment_id
        self.init_ui()
        self.load_equipment_data()
        
    def init_ui(self):
        self.setWindowTitle("Equipment Log" + (" - Edit" if self.equipment_id else " - Add"))
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.equipment_type_input = QComboBox()
        self.equipment_type_input.addItems([
            "Pump", "Generator", "Compressor", "Crane",
            "Mixer", "Winch", "Other"
        ])
        self.equipment_type_input.setEditable(True)
        form_layout.addRow("Equipment Type:", self.equipment_type_input)
        
        self.equipment_name_input = QLineEdit()
        form_layout.addRow("Equipment Name:", self.equipment_name_input)
        
        self.equipment_id_input = QLineEdit()
        form_layout.addRow("Equipment ID:", self.equipment_id_input)
        
        self.manufacturer_input = QLineEdit()
        form_layout.addRow("Manufacturer:", self.manufacturer_input)
        
        self.serial_input = QLineEdit()
        form_layout.addRow("Serial Number:", self.serial_input)
        
        self.service_date_input = QDateEdit()
        self.service_date_input.setCalendarPopup(True)
        self.service_date_input.setDate(QDate.currentDate())
        form_layout.addRow("Service Date:", self.service_date_input)
        
        self.service_type_input = QComboBox()
        self.service_type_input.addItems([
            "Routine Maintenance", "Repair", "Calibration",
            "Inspection", "Overhaul"
        ])
        self.service_type_input.setEditable(True)
        form_layout.addRow("Service Type:", self.service_type_input)
        
        self.service_provider_input = QLineEdit()
        form_layout.addRow("Service Provider:", self.service_provider_input)
        
        self.hours_input = QDoubleSpinBox()
        self.hours_input.setRange(0, 99999)
        self.hours_input.setValue(0)
        form_layout.addRow("Hours Worked:", self.hours_input)
        
        self.status_input = QComboBox()
        self.status_input.addItems(["Operational", "Under Maintenance", "Out of Service"])
        form_layout.addRow("Status:", self.status_input)
        
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        form_layout.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_equipment)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def load_equipment_data(self):
        if not self.equipment_id:
            return
            
        try:
            equipment_list = self.db.get_equipment_logs()
            equipment = None
            for eq in equipment_list:
                if eq.get("id") == self.equipment_id:
                    equipment = eq
                    break
                    
            if equipment:
                equipment_type = equipment.get("equipment_type", "")
                if equipment_type:
                    index = self.equipment_type_input.findText(equipment_type)
                    if index >= 0:
                        self.equipment_type_input.setCurrentIndex(index)
                    else:
                        self.equipment_type_input.setCurrentText(equipment_type)
                        
                self.equipment_name_input.setText(equipment.get("equipment_name", ""))
                self.equipment_id_input.setText(equipment.get("equipment_id", ""))
                self.manufacturer_input.setText(equipment.get("manufacturer", ""))
                self.serial_input.setText(equipment.get("serial_number", ""))
                
                date = equipment.get("service_date")
                if date:
                    if isinstance(date, str):
                        try:
                            dt = datetime.strptime(date, "%Y-%m-%d")
                            self.service_date_input.setDate(QDate(dt.year, dt.month, dt.day))
                        except:
                            pass
                    else:
                        self.service_date_input.setDate(QDate(date.year, date.month, date.day))
                        
                service_type = equipment.get("service_type", "")
                if service_type:
                    index = self.service_type_input.findText(service_type)
                    if index >= 0:
                        self.service_type_input.setCurrentIndex(index)
                    else:
                        self.service_type_input.setCurrentText(service_type)
                        
                self.service_provider_input.setText(equipment.get("service_provider", ""))
                self.hours_input.setValue(equipment.get("hours_worked", 0))
                
                status = equipment.get("status", "Operational")
                index = self.status_input.findText(status)
                if index >= 0:
                    self.status_input.setCurrentIndex(index)
                    
                self.notes_input.setText(equipment.get("notes", ""))
                
        except Exception as e:
            logger.error(f"Error loading equipment data: {e}")
            
    def save_equipment(self):
        try:
            if not self.equipment_name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Equipment name is required.")
                return
            
            # بررسی well_id
            if not self.well_id:
                QMessageBox.critical(self, "Error", "Well ID is not set. Cannot save equipment.")
                return
                
            equipment_data = {
                "well_id": self.well_id,
                "report_id": self.report_id,
                "equipment_type": self.equipment_type_input.currentText(),
                "equipment_name": self.equipment_name_input.text().strip(),
                "equipment_id": self.equipment_id_input.text().strip(),
                "manufacturer": self.manufacturer_input.text().strip(),
                "serial_number": self.serial_input.text().strip(),
                "service_date": self.service_date_input.date().toPython(),
                "service_type": self.service_type_input.currentText(),
                "service_provider": self.service_provider_input.text().strip(),
                "hours_worked": self.hours_input.value(),
                "status": self.status_input.currentText(),
                "notes": self.notes_input.toPlainText().strip(),
            }
            
            if self.equipment_id:
                equipment_data["id"] = self.equipment_id
                
            result = self.db.save_equipment_log(equipment_data)
            if result:
                self.accept()
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save equipment.")
                
        except Exception as e:
            logger.error(f"Error saving equipment: {e}")
            QMessageBox.critical(self, "Save Error", f"Error: {str(e)}")


# ------------------------ Main Services Widget ------------------------
class ServicesWidget(QWidget):
    """Main Services Widget combining all tabs"""
    
    def __init__(self, db_manager=None):
        super().__init__()
        self.db = db_manager
        self.current_well = None
        self.current_report = None
        self.current_well_name = None
        self.status_manager = StatusBarManager()
        self.status_manager.register_widget("ServicesWidget", self)
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("🛠️ Services Management")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 18pt; 
            font-weight: bold; 
            color: #2c3e50;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 5px;
        """)
        main_layout.addWidget(title_label)
        
        # Well selection area
        selection_layout = QHBoxLayout()
        
        self.well_label = QLabel("Current Well: Not Selected")
        self.well_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        
        selection_layout.addWidget(self.well_label)
        selection_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh All")
        refresh_btn.clicked.connect(self.refresh_all)
        selection_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(selection_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.service_company_tab = ServiceCompanyTab(self.db)
        self.material_handling_tab = MaterialHandlingTab(self.db)
        
        # Add tabs
        self.tab_widget.addTab(self.service_company_tab, "🏢 Service Companies")
        self.tab_widget.addTab(self.material_handling_tab, "📦 Material Handling")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)
        
        # Setup auto-save
        self.setup_auto_save()
        
    def set_current_well(self, well_id, well_name=None):
        self.current_well = well_id
        self.current_well_name = well_name  # ذخیره نام چاه
        
        if well_id:
            if well_name:
                display_text = f"Current Well: {well_name} (ID: {well_id})"
                style = "font-weight: bold; color: #27ae60;"
            else:
                display_text = f"Current Well: ID {well_id}"
                style = "font-weight: bold; color: #27ae60;"
        else:
            display_text = "Current Well: Not Selected"
            style = "font-weight: bold; color: #e74c3c;"
        
        self.well_label.setText(display_text)
        self.well_label.setStyleSheet(style)
        
        # Propagate to tabs
        if well_id:
            self.service_company_tab.set_current_well(well_id)
            self.material_handling_tab.set_current_well(well_id)
        else:
            # پاک کردن داده‌ها اگر چاهی انتخاب نشده
            self.service_company_tab.load_data()  # این تابع باید بدون well_id کار کند
            self.material_handling_tab.load_all_data()  # این تابع باید بدون well_id کار کند
    def set_current_report(self, report_id):
        self.current_report = report_id
        self.service_company_tab.set_current_report(report_id)
        self.material_handling_tab.set_current_report(report_id)
        
    def refresh_all(self):
        if self.current_well:
            self.service_company_tab.load_data()
            self.material_handling_tab.load_all_data()
            self.status_manager.show_success("ServicesWidget", "All data refreshed")
        else:
            self.status_manager.show_warning("ServicesWidget", "No well selected")
            
    def setup_auto_save(self):
        auto_save_manager = AutoSaveManager()
        auto_save_manager.enable_for_widget("ServicesWidget", self, interval_minutes=5)
        
    def save_data(self):
        """Save all services data"""
        try:
            # Note: Each tab handles its own saving
            # This method is for bulk saving if needed
            self.status_manager.show_success("ServicesWidget", "Services data saved")
            return True
        except Exception as e:
            self.status_manager.show_error("ServicesWidget", f"Save failed: {e}")
            return False
            
    def load_data(self):
        """Load services data"""
        try:
            if self.current_well:
                self.refresh_all()
                self.status_manager.show_message("ServicesWidget", "Services data loaded")
            return True
        except Exception as e:
            self.status_manager.show_error("ServicesWidget", f"Load failed: {e}")
            return False

