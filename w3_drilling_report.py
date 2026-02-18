"""
Drilling Report - کلاس اصلی یکپارچه برای تمام تب‌های گزارش حفاری
"""

import logging
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from core.database import DatabaseManager
from core.managers import (
    StatusBarManager, 
    AutoSaveManager, 
    ShortcutManager,
    TableButtonManager,
    ExportManager,
    DrillingManager
)

logger = logging.getLogger(__name__)

# ==================== DrillingReport (کلاس اصلی) ====================
class DrillingReportWidget(QWidget):
    """کلاس اصلی گزارش حفاری - شامل تمام تب‌ها"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        
        self.current_well = None
        self.current_data = {}
        
        # Managerها
        self.status_manager = StatusBarManager()
        self.drilling_manager = DrillingManager()
        
        # ایجاد تب‌ها
        self.drilling_tab = None
        self.mud_tab = None
        self.cement_tab = None
        self.casing_tab = None
        self.schematic_tab = None
        
        self.init_ui()
        self.setup_connections()
        
        logger.info("DrillingReport initialized")
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ============ نوار ابزار بالایی ============
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        
        # دکمه‌های نوار ابزار
        self.save_all_btn = QAction("💾 Save All Tabs", self)
        self.save_all_btn.triggered.connect(self.save_all_tabs)
        toolbar.addAction(self.save_all_btn)
        
        self.load_all_btn = QAction("📂 Load All Tabs", self)
        self.load_all_btn.triggered.connect(self.load_all_tabs)
        toolbar.addAction(self.load_all_btn)
        
        toolbar.addSeparator()
        
        self.export_btn = QAction("📤 Export Report", self)
        self.export_btn.triggered.connect(self.export_complete_report)
        toolbar.addAction(self.export_btn)
        
        toolbar.addSeparator()
        
        # نشانگر چاه جاری
        self.current_well_label = QLabel("No well selected")
        self.current_well_label.setStyleSheet("padding: 5px; font-weight: bold; color: #0078d4;")
        toolbar.addWidget(self.current_well_label)
             
        layout.addWidget(toolbar)
        
        # ============ تب‌های اصلی ============
        self.tab_widget = QTabWidget()
        
        # ایجاد تب‌ها
        self.drilling_tab = DrillingParametersTab(self.db_manager, self)
        self.mud_tab = MudReportTab(self.db_manager, self)
        self.cement_tab = CementReportTab(self.db_manager, self)
        self.casing_tab = CasingReportTab(self.db_manager, self)
        self.casing_tally_tab = CasingTallyWidget(self.db_manager, self)
        self.schematic_tab = WellboreSchematicTab(self.db_manager, self)
        
        # اضافه کردن تب‌ها
        self.tab_widget.addTab(self.drilling_tab, "⚙️ Drilling Parameters")
        self.tab_widget.addTab(self.mud_tab, "🧪 Mud Report")
        self.tab_widget.addTab(self.cement_tab, "🏗️ Cement Report")
        self.tab_widget.addTab(self.casing_tally_tab, "📏 Casing Tally")
        self.tab_widget.addTab(self.casing_tab, "🔩 Casing Report")
        self.tab_widget.addTab(self.schematic_tab, "📊 Wellbore Schematic")
        
        # تنظیم آیکن‌ها برای تب‌ها
        self.tab_widget.setTabIcon(0, QIcon("📊"))
        self.tab_widget.setTabIcon(1, QIcon("🧪"))
        self.tab_widget.setTabIcon(2, QIcon("🏗️"))
        self.tab_widget.setTabIcon(3, QIcon("🔩"))
        self.tab_widget.setTabIcon(4, QIcon("📏"))
        self.tab_widget.setTabIcon(5, QIcon("📐"))
        
        layout.addWidget(self.tab_widget)
        
        # ============ نوار وضعیت ============
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        layout.addWidget(self.status_bar)
        
        # تنظیم Managerها برای تب‌ها
        self.register_tabs_with_managers()
    
    def register_tabs_with_managers(self):
        """ثبت تب‌ها در Managerها"""
        try:
            # ثبت در StatusBar Manager
            self.status_manager.register_widget("DrillingReport_Main", self)
            self.status_manager.register_widget("DrillingParametersTab", self.drilling_tab)
            self.status_manager.register_widget("MudReportTab", self.mud_tab)
            self.status_manager.register_widget("CementReportTab", self.cement_tab)
            self.status_manager.register_widget("CasingReportTab", self.casing_tab)
            self.status_manager.register_widget("WellboreSchematicTab", self.schematic_tab)
            
            logger.info("✅ All tabs registered with managers")
            
        except Exception as e:
            logger.error(f"Error registering tabs: {e}")
    
    def setup_connections(self):
        """اتصال سیگنال‌های اصلی"""
        # اتصال تغییر تب
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # اتصال دکمه‌های نوار ابزار اصلی
        self.save_all_btn.triggered.connect(self.save_all_tabs)
        self.load_all_btn.triggered.connect(self.load_all_tabs)
        self.export_btn.triggered.connect(self.export_complete_report)
        
        # اتصال validation - فقط اگر دکمه وجود دارد
        if hasattr(self, 'validate_btn'):
            self.validate_btn.clicked.connect(self.validate_all_tabs)
        
        # اتصال clear all - فقط اگر دکمه وجود دارد
        if hasattr(self, 'clear_all_btn'):
            self.clear_all_btn.clicked.connect(self.clear_all_tabs)
        
        # اتصال refresh - فقط اگر دکمه وجود دارد
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.clicked.connect(self.refresh_all_tabs)
        
        # اتصال help - فقط اگر دکمه وجود دارد
        if hasattr(self, 'help_btn'):
            self.help_btn.clicked.connect(self.show_help)
        
        # اتصال تغییر چاه
        if hasattr(self, 'well_selection_combo'):
            self.well_selection_combo.currentIndexChanged.connect(
                self.on_well_selection_changed
            )
    def on_tab_changed(self, index):
        """هنگام تغییر تب"""
        tab_name = self.tab_widget.tabText(index)
        self.status_bar.showMessage(f"Active tab: {tab_name}")
        
        # به‌روزرسانی وضعیت بر اساس چاه جاری
        if self.current_well:
            self.status_manager.show_message(
                "DrillingReport_Main",
                f"Editing well {self.current_well} - {tab_name}",
                2000
            )
    
    # ============ متدهای اصلی ============
    def set_current_well(self, well_id, well_name=None):
        """تنظیم چاه جاری"""
        self.current_well = well_id
        
        # این خط مهم است - برچسب را به‌روزرسانی کنید
        if hasattr(self, 'current_well_label'):
            if well_name:
                self.current_well_label.setText(f"Current Well: {well_name} (ID: {well_id})")
            else:
                self.current_well_label.setText(f"Current Well ID: {well_id}")
        
        logger.info(f"CasingTallyWidget: Current well set to {well_id}")
    
    # def set_current_well(self, well_id, well_name=None):
        # """تنظیم چاه جاری برای تمام تب‌ها"""
        # self.current_well = well_id
        
        # # به‌روزرسانی label
        # if well_name:
            # self.current_well_label.setText(f"Current Well: {well_name} (ID: {well_id})")
        # else:
            # self.current_well_label.setText(f"Current Well ID: {well_id}")
        
        # # تنظیم چاه جاری در تمام تب‌ها
        # self.drilling_tab.set_current_well(well_id)
        # self.mud_tab.set_current_well(well_id)
        # self.cement_tab.set_current_well(well_id)
        # self.casing_tab.set_current_well(well_id)
        # self.casing_tally_tab.set_current_well(well_id)
        # self.schematic_tab.set_current_well(well_id)
        
        # # نمایش پیام
        # self.status_manager.show_success(
            # "DrillingReport_Main",
            # f"Well {well_id} selected for editing"
        # )
        
        # logger.info(f"Current well set to: {well_id}")
    
    def save_all_tabs(self):
        """ذخیره تمام تب‌ها"""
        if not self.current_well:
            self.status_manager.show_error(
                "DrillingReport_Main",
                "Please select a well first"
            )
            return False
        
        try:
            results = {
                "drilling": self.drilling_tab.save_data(),
                "mud": self.mud_tab.save_data(),
                "cement": self.cement_tab.save_data(),
                "casing": self.casing_tab.save_data(),
                "schematic": self.schematic_tab.save_schematic()
            }
            
            success_count = sum(1 for r in results.values() if r)
            
            if success_count > 0:
                self.status_manager.show_success(
                    "DrillingReport_Main",
                    f"Saved {success_count} out of 5 tabs successfully"
                )
                return True
            else:
                self.status_manager.show_error(
                    "DrillingReport_Main",
                    "Failed to save any tabs"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error saving all tabs: {e}")
            self.status_manager.show_error(
                "DrillingReport_Main",
                f"Save error: {str(e)}"
            )
            return False
    
    def load_all_tabs(self):
        """بارگذاری داده‌ها در تمام تب‌ها"""
        if not self.current_well:
            self.status_manager.show_error(
                "DrillingReport_Main",
                "Please select a well first"
            )
            return False
        
        try:
            results = {
                "drilling": self.drilling_tab.load_data(),
                "mud": self.mud_tab.load_data(),
                "cement": self.cement_tab.load_data(),
                "casing": self.casing_tab.load_data(),
                "schematic": self.schematic_tab.load_schematic()
            }
            
            success_count = sum(1 for r in results.values() if r)
            
            if success_count > 0:
                self.status_manager.show_success(
                    "DrillingReport_Main",
                    f"Loaded {success_count} out of 5 tabs successfully"
                )
                return True
            else:
                self.status_manager.show_warning(
                    "DrillingReport_Main",
                    "No data found to load"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error loading all tabs: {e}")
            self.status_manager.show_error(
                "DrillingReport_Main",
                f"Load error: {str(e)}"
            )
            return False
    
    def export_complete_report(self):
        """اکسپورت گزارش کامل"""
        try:
            # دیالوگ انتخاب فرمت
            formats = ["PDF", "Word", "Excel"]
            format_choice, ok = QInputDialog.getItem(
                self, "Export Format", "Select export format:", formats, 0, False
            )
            
            if not ok or not format_choice:
                return
            
            # دیالوگ انتخاب مسیر
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"drilling_report_{self.current_well}_{timestamp}"
            
            if format_choice == "PDF":
                filter_text = "PDF Files (*.pdf)"
                ext = ".pdf"
            elif format_choice == "Word":
                filter_text = "Word Documents (*.docx)"
                ext = ".docx"
            else:  # Excel
                filter_text = "Excel Files (*.xlsx)"
                ext = ".xlsx"
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Complete Report", default_filename + ext, filter_text
            )
            
            if not filename:
                return
            
            # نمایش progress
            self.status_manager.show_progress(
                "DrillingReport_Main",
                f"Exporting complete report to {format_choice}..."
            )
            
            # TODO: پیاده‌سازی export کامل
            # اینجا می‌توانید از ExportManager استفاده کنید
            
            QTimer.singleShot(1000, lambda: self._finish_export(filename, format_choice))
            
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            self.status_manager.show_error(
                "DrillingReport_Main",
                f"Export failed: {str(e)}"
            )
    
    def _finish_export(self, filename, format_choice):
        """پایان export (شبیه‌سازی)"""
        self.status_manager.show_success(
            "DrillingReport_Main",
            f"Report exported to: {filename}"
        )
    
    def clear_all_tabs(self):
        """پاک کردن تمام فرم‌ها"""
        reply = QMessageBox.question(
            self, "Clear All Tabs",
            "Are you sure you want to clear all tabs? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.drilling_tab.clear_form()
            self.mud_tab.clear_form()
            self.cement_tab.clear_form()
            self.casing_tab.clear_form()
            self.schematic_tab.clear_schematic()
            
            self.status_manager.show_success(
                "DrillingReport_Main",
                "All tabs cleared"
            )
    
    def get_report_summary(self):
        """دریافت خلاصه گزارش"""
        if not self.current_well:
            return "No well selected"
        
        summary = {
            "well_id": self.current_well,
            "timestamp": datetime.now().isoformat(),
            "tabs": {
                "drilling": self.drilling_tab.current_data if hasattr(self.drilling_tab, 'current_data') else {},
                "mud": self.mud_tab.current_data if hasattr(self.mud_tab, 'current_data') else {},
                "cement": self.cement_tab.current_data if hasattr(self.cement_tab, 'current_data') else {},
                "casing": self.casing_tab.current_data if hasattr(self.casing_tab, 'current_data') else {},
                "schematic": "Schematic data available" if hasattr(self.schematic_tab, 'graphics_scene') else "No schematic"
            }
        }
        
        return json.dumps(summary, indent=2, default=str)
    
    def validate_all_tabs(self):
        """اعتبارسنجی تمام تب‌ها"""
        errors = []
        
        # اعتبارسنجی drilling tab
        if hasattr(self.drilling_tab, 'validate_form'):
            drilling_errors = self.drilling_tab.validate_form()
            if drilling_errors:
                errors.append(f"Drilling Parameters: {drilling_errors}")
        
        # TODO: اعتبارسنجی سایر تب‌ها
        
        if errors:
            error_msg = "\n".join(errors)
            self.status_manager.show_error(
                "DrillingReport_Main",
                f"Validation errors:\n{error_msg}"
            )
            return False
        else:
            self.status_manager.show_success(
                "DrillingReport_Main",
                "All tabs validated successfully"
            )
            return True
    
    # ============ متدهای کمکی ============
    
    def show_help(self):
        """نمایش راهنما"""
        help_text = """
        Drilling Report Module
        
        This module contains 5 tabs:
        1. ⚙️ Drilling Parameters - Bit info, depth, drilling parameters
        2. 🧪 Mud Report - Mud properties and chemicals
        3. 🏗️ Cement Report - Cement job information
        4. 🔩 Casing Report - Casing design and running parameters
        5. 📊 Wellbore Schematic - Visual wellbore diagram
        
        Tips:
        - Select a well before editing
        - Use Save All to save all tabs at once
        - Use Export to generate complete reports
        """
        
        QMessageBox.information(self, "Help - Drilling Report", help_text)
    
    def get_active_tab(self):
        """دریافت تب فعال"""
        return self.tab_widget.currentWidget()
    
    def set_active_tab(self, tab_index):
        """تنظیم تب فعال"""
        if 0 <= tab_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(tab_index)
    
    def refresh_all_tabs(self):
        """رفرش تمام تب‌ها"""
        try:
            # رفرش هر تب
            if hasattr(self.drilling_tab, 'refresh'):
                self.drilling_tab.refresh()
            if hasattr(self.mud_tab, 'refresh'):
                self.mud_tab.refresh()
            if hasattr(self.cement_tab, 'refresh'):
                self.cement_tab.refresh()
            if hasattr(self.casing_tab, 'refresh'):
                self.casing_tab.refresh()
            if hasattr(self.schematic_tab, 'refresh'):
                self.schematic_tab.refresh()
            
            self.status_manager.show_success(
                "DrillingReport_Main",
                "All tabs refreshed"
            )
            
        except Exception as e:
            logger.error(f"Error refreshing tabs: {e}")

# ==================== CLASS 1: DrillingParametersTab ====================
class DrillingParametersTab(QWidget):
    """تب پارامترهای حفاری"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        
        self.current_well = None
        self.current_data = {}
        
        if parent and hasattr(parent, 'drilling_manager'):
            self.drilling_manager = parent.drilling_manager
        else:
            self.drilling_manager = DrillingManager()
        
        self.init_ui()
        self.setup_connections()
        
        logger.info("DrillingParametersTab initialized")
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ایجاد اسکرول‌ایریا
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        # ============ Bit Information ============
        bit_group = QGroupBox("📌 Bit Information")
        bit_layout = QGridLayout()
        
        # Bit No
        bit_layout.addWidget(QLabel("Bit No:"), 0, 0)
        self.bit_no = QLineEdit()
        self.bit_no.setPlaceholderText("Enter bit number")
        bit_layout.addWidget(self.bit_no, 0, 1)
        
        # Rerun No
        bit_layout.addWidget(QLabel("Rerun No:"), 0, 2)
        self.bit_rerun = QSpinBox()
        self.bit_rerun.setRange(1, 100)
        self.bit_rerun.setValue(1)
        bit_layout.addWidget(self.bit_rerun, 0, 3)
        
        # Bit Size
        bit_layout.addWidget(QLabel("Bit Size (in):"), 1, 0)
        self.bit_size = QDoubleSpinBox()
        self.bit_size.setRange(0, 30)
        self.bit_size.setDecimals(3)
        self.bit_size.setValue(8.5)
        bit_layout.addWidget(self.bit_size, 1, 1)
        
        # Bit Type
        bit_layout.addWidget(QLabel("Bit Type:"), 1, 2)
        self.bit_type = QComboBox()
        self.bit_type.addItems(["PDC", "Tricone", "Impregnated", "Diamond"])
        bit_layout.addWidget(self.bit_type, 1, 3)
        
        # Manufacturer
        bit_layout.addWidget(QLabel("Manufacturer:"), 2, 0)
        self.bit_manufacturer = QLineEdit()
        self.bit_manufacturer.setPlaceholderText("e.g., Schlumberger")
        bit_layout.addWidget(self.bit_manufacturer, 2, 1)
        
        # IADC Code
        bit_layout.addWidget(QLabel("IADC Code:"), 2, 2)
        self.iadc_code = QLineEdit()
        self.iadc_code.setPlaceholderText("e.g., M333")
        bit_layout.addWidget(self.iadc_code, 2, 3)
        
        bit_group.setLayout(bit_layout)
        content_layout.addWidget(bit_group)
        
        # ============ Nozzle Information ============
        nozzle_group = QGroupBox("🌀 Nozzle Information")
        nozzle_layout = QVBoxLayout()
        
        # جدول نازل‌ها
        self.nozzle_table = QTableWidget(0, 3)
        self.nozzle_table.setHorizontalHeaderLabels(["No.", "Size (1/32 in)", "Qty"])
        self.nozzle_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.nozzle_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nozzle_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.nozzle_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        nozzle_layout.addWidget(self.nozzle_table)
        
        # دکمه‌های کنترل جدول
        nozzle_btn_layout = QHBoxLayout()
        add_nozzle_btn = QPushButton("➕ Add Nozzle")
        add_nozzle_btn.clicked.connect(self.add_nozzle_row)
        remove_nozzle_btn = QPushButton("➖ Remove")
        remove_nozzle_btn.clicked.connect(self.remove_nozzle_row)
        calc_tfa_btn = QPushButton("🔄 Calculate TFA")
        calc_tfa_btn.clicked.connect(self.calculate_tfa)
        
        nozzle_btn_layout.addWidget(add_nozzle_btn)
        nozzle_btn_layout.addWidget(remove_nozzle_btn)
        nozzle_btn_layout.addWidget(calc_tfa_btn)
        nozzle_btn_layout.addStretch()
        nozzle_layout.addLayout(nozzle_btn_layout)
        
        # نمایش TFA
        tfa_layout = QHBoxLayout()
        tfa_layout.addWidget(QLabel("Total Flow Area (TFA):"))
        self.tfa_value = QDoubleSpinBox()
        self.tfa_value.setReadOnly(True)
        self.tfa_value.setDecimals(3)
        self.tfa_value.setSuffix(" in²")
        tfa_layout.addWidget(self.tfa_value)
        tfa_layout.addStretch()
        nozzle_layout.addLayout(tfa_layout)
        
        nozzle_group.setLayout(nozzle_layout)
        content_layout.addWidget(nozzle_group)
        
        # ============ Depth Information ============
        depth_group = QGroupBox("📏 Depth Information")
        depth_layout = QGridLayout()
        
        # Depth In
        depth_layout.addWidget(QLabel("Depth In (m):"), 0, 0)
        self.depth_in = QDoubleSpinBox()
        self.depth_in.setRange(0, 20000)
        self.depth_in.setDecimals(2)
        depth_layout.addWidget(self.depth_in, 0, 1)
        
        # Depth Out
        depth_layout.addWidget(QLabel("Depth Out (m):"), 0, 2)
        self.depth_out = QDoubleSpinBox()
        self.depth_out.setRange(0, 20000)
        self.depth_out.setDecimals(2)
        depth_layout.addWidget(self.depth_out, 0, 3)
        
        # Bit Drilled
        depth_layout.addWidget(QLabel("Bit Drilled (m):"), 1, 0)
        self.bit_drilled = QDoubleSpinBox()
        self.bit_drilled.setReadOnly(True)
        self.bit_drilled.setDecimals(2)
        depth_layout.addWidget(self.bit_drilled, 1, 1)
        
        # Cumulative Drilled
        depth_layout.addWidget(QLabel("Cumulative (m):"), 1, 2)
        self.cum_drilled = QDoubleSpinBox()
        self.cum_drilled.setRange(0, 50000)
        self.cum_drilled.setDecimals(2)
        depth_layout.addWidget(self.cum_drilled, 1, 3)
        
        # Hours on Bottom
        depth_layout.addWidget(QLabel("Hours on Bottom:"), 2, 0)
        self.hours_on_bottom = QDoubleSpinBox()
        self.hours_on_bottom.setRange(0, 1000)
        self.hours_on_bottom.setDecimals(1)
        depth_layout.addWidget(self.hours_on_bottom, 2, 1)
        
        # Cumulative Hours
        depth_layout.addWidget(QLabel("Cumulative Hours:"), 2, 2)
        self.cum_hours = QDoubleSpinBox()
        self.cum_hours.setRange(0, 10000)
        self.cum_hours.setDecimals(1)
        depth_layout.addWidget(self.cum_hours, 2, 3)
        
        depth_group.setLayout(depth_layout)
        content_layout.addWidget(depth_group)
        
        # ============ Drilling Parameters ============
        params_group = QGroupBox("⚙️ Drilling Parameters")
        params_layout = QGridLayout()
        
        # WOB
        params_layout.addWidget(QLabel("WOB Min (klb):"), 0, 0)
        self.wob_min = QDoubleSpinBox()
        self.wob_min.setRange(0, 100)
        self.wob_min.setDecimals(1)
        params_layout.addWidget(self.wob_min, 0, 1)
        
        params_layout.addWidget(QLabel("WOB Max (klb):"), 0, 2)
        self.wob_max = QDoubleSpinBox()
        self.wob_max.setRange(0, 100)
        self.wob_max.setDecimals(1)
        params_layout.addWidget(self.wob_max, 0, 3)
        
        # RPM
        params_layout.addWidget(QLabel("RPM Min:"), 1, 0)
        self.rpm_min = QDoubleSpinBox()
        self.rpm_min.setRange(0, 500)
        self.rpm_min.setDecimals(0)
        params_layout.addWidget(self.rpm_min, 1, 1)
        
        params_layout.addWidget(QLabel("RPM Max:"), 1, 2)
        self.rpm_max = QDoubleSpinBox()
        self.rpm_max.setRange(0, 500)
        self.rpm_max.setDecimals(0)
        params_layout.addWidget(self.rpm_max, 1, 3)
        
        # Torque
        params_layout.addWidget(QLabel("Torque Min (klb.ft):"), 2, 0)
        self.torque_min = QDoubleSpinBox()
        self.torque_min.setRange(0, 100)
        self.torque_min.setDecimals(1)
        params_layout.addWidget(self.torque_min, 2, 1)
        
        params_layout.addWidget(QLabel("Torque Max (klb.ft):"), 2, 2)
        self.torque_max = QDoubleSpinBox()
        self.torque_max.setRange(0, 100)
        self.torque_max.setDecimals(1)
        params_layout.addWidget(self.torque_max, 2, 3)
        
        # Pump Pressure
        params_layout.addWidget(QLabel("SPP Min (psi):"), 3, 0)
        self.pump_pressure_min = QDoubleSpinBox()
        self.pump_pressure_min.setRange(0, 5000)
        self.pump_pressure_min.setDecimals(0)
        params_layout.addWidget(self.pump_pressure_min, 3, 1)
        
        params_layout.addWidget(QLabel("SPP Max (psi):"), 3, 2)
        self.pump_pressure_max = QDoubleSpinBox()
        self.pump_pressure_max.setRange(0, 5000)
        self.pump_pressure_max.setDecimals(0)
        params_layout.addWidget(self.pump_pressure_max, 3, 3)
        
        params_group.setLayout(params_layout)
        content_layout.addWidget(params_group)
        
        # ============ Pump Parameters ============
        pump_group = QGroupBox("💧 Pump Parameters")
        pump_layout = QGridLayout()
        
        # Pump Output
        pump_layout.addWidget(QLabel("Flow Rate Min (gpm):"), 0, 0)
        self.pump_output_min = QDoubleSpinBox()
        self.pump_output_min.setRange(0, 5000)
        self.pump_output_min.setDecimals(0)
        pump_layout.addWidget(self.pump_output_min, 0, 1)
        
        pump_layout.addWidget(QLabel("Flow Rate Max (gpm):"), 0, 2)
        self.pump_output_max = QDoubleSpinBox()
        self.pump_output_max.setRange(0, 5000)
        self.pump_output_max.setDecimals(0)
        pump_layout.addWidget(self.pump_output_max, 0, 3)
        
        # Pump 1
        pump_layout.addWidget(QLabel("Pump 1 SPM:"), 1, 0)
        self.pump1_spm = QDoubleSpinBox()
        self.pump1_spm.setRange(0, 200)
        self.pump1_spm.setDecimals(1)
        pump_layout.addWidget(self.pump1_spm, 1, 1)
        
        pump_layout.addWidget(QLabel("Pump 1 SPP (psi):"), 1, 2)
        self.pump1_spp = QDoubleSpinBox()
        self.pump1_spp.setRange(0, 5000)
        self.pump1_spp.setDecimals(0)
        pump_layout.addWidget(self.pump1_spp, 1, 3)
        
        # Pump 2
        pump_layout.addWidget(QLabel("Pump 2 SPM:"), 2, 0)
        self.pump2_spm = QDoubleSpinBox()
        self.pump2_spm.setRange(0, 200)
        self.pump2_spm.setDecimals(1)
        pump_layout.addWidget(self.pump2_spm, 2, 1)
        
        pump_layout.addWidget(QLabel("Pump 2 SPP (psi):"), 2, 2)
        self.pump2_spp = QDoubleSpinBox()
        self.pump2_spp.setRange(0, 5000)
        self.pump2_spp.setDecimals(0)
        pump_layout.addWidget(self.pump2_spp, 2, 3)
        
        pump_group.setLayout(pump_layout)
        content_layout.addWidget(pump_group)
        
        # ============ Calculations ============
        calc_group = QGroupBox("🧮 Calculations")
        calc_layout = QGridLayout()
        
        # Average ROP
        calc_layout.addWidget(QLabel("Avg ROP (m/hr):"), 0, 0)
        self.avg_rop = QDoubleSpinBox()
        self.avg_rop.setReadOnly(True)
        self.avg_rop.setDecimals(2)
        calc_layout.addWidget(self.avg_rop, 0, 1)
        
        # HSI
        calc_layout.addWidget(QLabel("HSI:"), 0, 2)
        self.hsi = QDoubleSpinBox()
        self.hsi.setReadOnly(True)
        self.hsi.setDecimals(2)
        calc_layout.addWidget(self.hsi, 0, 3)
        
        # Annular Velocity
        calc_layout.addWidget(QLabel("Annular Velocity (ft/min):"), 1, 0)
        self.annular_velocity = QDoubleSpinBox()
        self.annular_velocity.setReadOnly(True)
        self.annular_velocity.setDecimals(1)
        calc_layout.addWidget(self.annular_velocity, 1, 1)
        
        # Bit Revolution
        calc_layout.addWidget(QLabel("Bit Revolution (k.rev):"), 1, 2)
        self.bit_revolution = QDoubleSpinBox()
        self.bit_revolution.setReadOnly(True)
        self.bit_revolution.setDecimals(0)
        calc_layout.addWidget(self.bit_revolution, 1, 3)
        
        calc_group.setLayout(calc_layout)
        content_layout.addWidget(calc_group)
        
        # ============ Action Buttons ============
        btn_layout = QHBoxLayout()
        self.calculate_all_btn = QPushButton("🔄 Calculate All")
        self.calculate_all_btn.clicked.connect(self.calculate_all)
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_data)
        self.load_btn = QPushButton("📂 Load")
        self.load_btn.clicked.connect(self.load_data)
        
        btn_layout.addWidget(self.calculate_all_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addStretch()
        
        content_layout.addLayout(btn_layout)
        content_layout.addStretch()
        
        # تنظیم اسکرول
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # اضافه کردن ردیف‌های پیش‌فرض به جدول نازل‌ها
        self.add_nozzle_row(16, 1)
        self.add_nozzle_row(16, 1)
        self.add_nozzle_row(14, 1)
    
    def setup_connections(self):
        """اتصال سیگنال‌ها برای تب پارامترهای حفاری"""
        # اتصال برای محاسبات خودکار عمق
        self.depth_in.valueChanged.connect(self.calculate_bit_drilled)
        self.depth_out.valueChanged.connect(self.calculate_bit_drilled)
        self.hours_on_bottom.valueChanged.connect(self.calculate_rop)
        
        # اتصال برای محاسبه HSI
        self.pump_pressure_min.valueChanged.connect(self.calculate_hsi)
        self.pump_pressure_max.valueChanged.connect(self.calculate_hsi)
        self.pump_output_min.valueChanged.connect(self.calculate_hsi)
        self.pump_output_max.valueChanged.connect(self.calculate_hsi)
        self.bit_size.valueChanged.connect(self.calculate_hsi)
        
        # اتصال تغییرات RPM برای محاسبه دور مته
        self.rpm_min.valueChanged.connect(self.calculate_bit_revolution)
        self.rpm_max.valueChanged.connect(self.calculate_bit_revolution)
        self.nozzle_table.cellChanged.connect(self.calculate_tfa)
        
        # اتصال تغییرات flow rate برای محاسبه سرعت حلقوی
        self.pump_output_min.valueChanged.connect(self.calculate_annular_velocity)
        self.pump_output_max.valueChanged.connect(self.calculate_annular_velocity)
        self.bit_size.valueChanged.connect(self.calculate_annular_velocity)
        
        self.cum_drilled.valueChanged.connect(self.update_cumulative_info)
        
        self.bit_type.currentTextChanged.connect(self.on_bit_type_changed)
        
        self.iadc_code.textChanged.connect(self.on_iadc_code_changed)
    
    # ============ Nozzle Methods ============
    def setup_connections_for_nozzle_table(self):
        """اتصال سیگنال‌ها برای جدول نازل‌ها"""
        # از آنجایی که جدول دارای ویجت است، باید به روش دیگری اتصال ایجاد کنیم
        # این تابع را در add_nozzle_row فراخوانی کنید
        pass

    # در تابع add_nozzle_row:
    def add_nozzle_row(self, size=16, quantity=1):
        """اضافه کردن ردیف به جدول نازل‌ها"""
        row = self.nozzle_table.rowCount()
        self.nozzle_table.insertRow(row)
        
        # شماره نازل
        no_item = QTableWidgetItem(str(row + 1))
        no_item.setTextAlignment(Qt.AlignCenter)
        no_item.setFlags(Qt.ItemIsEnabled)
        self.nozzle_table.setItem(row, 0, no_item)
        
        # سایز
        size_spin = QSpinBox()
        size_spin.setRange(1, 100)
        size_spin.setValue(size)
        size_spin.setSuffix("/32")
        # اتصال سیگنال برای محاسبه TFA
        size_spin.valueChanged.connect(self.calculate_tfa)
        self.nozzle_table.setCellWidget(row, 1, size_spin)
        
        # تعداد
        qty_spin = QSpinBox()
        qty_spin.setRange(1, 10)
        qty_spin.setValue(quantity)
        # اتصال سیگنال برای محاسبه TFA
        qty_spin.valueChanged.connect(self.calculate_tfa)
        self.nozzle_table.setCellWidget(row, 2, qty_spin)
        
    def remove_nozzle_row(self):
        """حذف ردیف انتخاب شده از جدول نازل‌ها"""
        current_row = self.nozzle_table.currentRow()
        if current_row >= 0:
            self.nozzle_table.removeRow(current_row)
            self.calculate_tfa()
            # شماره‌گذاری مجدد
            for row in range(self.nozzle_table.rowCount()):
                item = QTableWidgetItem(str(row + 1))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsEnabled)
                self.nozzle_table.setItem(row, 0, item)
    
    def calculate_tfa(self):
        """محاسبه Total Flow Area"""
        try:
            total_tfa = 0.0
            
            for row in range(self.nozzle_table.rowCount()):
                size_widget = self.nozzle_table.cellWidget(row, 1)
                qty_widget = self.nozzle_table.cellWidget(row, 2)
                
                if size_widget and qty_widget:
                    size_32 = size_widget.value()
                    quantity = qty_widget.value()
                    
                    # تبدیل به اینچ و محاسبه مساحت
                    diameter_inch = size_32 / 32.0
                    area_per_nozzle = 3.1416 * (diameter_inch / 2.0) ** 2
                    total_tfa += area_per_nozzle * quantity
            
            self.tfa_value.setValue(round(total_tfa, 3))
            
        except Exception as e:
            logger.error(f"Error calculating TFA: {e}")
    
    # ============ Calculation Methods ============
    def calculate_bit_drilled(self):
        """محاسبه عمق حفاری شده"""
        try:
            bit_drilled = self.depth_out.value() - self.depth_in.value()
            if bit_drilled < 0:
                bit_drilled = 0
            self.bit_drilled.setValue(round(bit_drilled, 2))
            self.calculate_rop()
        except Exception as e:
            logger.error(f"Error calculating bit drilled: {e}")
    
    def calculate_rop(self):
        """محاسبه Rate of Penetration"""
        try:
            bit_drilled = self.bit_drilled.value()
            hours = self.hours_on_bottom.value()
            
            if hours > 0:
                rop = bit_drilled / hours
            else:
                rop = 0
            
            self.avg_rop.setValue(round(rop, 2))
        except Exception as e:
            logger.error(f"Error calculating ROP: {e}")
    
    def calculate_hsi(self):
        """محاسبه Hydraulic Horsepower per Square Inch"""
        try:
            pump_pressure = (self.pump_pressure_min.value() + self.pump_pressure_max.value()) / 2
            flow_rate = (self.pump_output_min.value() + self.pump_output_max.value()) / 2
            tfa = self.tfa_value.value()
            
            if tfa > 0:
                # HSI = (P × Q) / (TFA × 1714)
                hsi_value = (pump_pressure * flow_rate) / (tfa * 1714)
            else:
                hsi_value = 0
            
            self.hsi.setValue(round(hsi_value, 2))
        except Exception as e:
            logger.error(f"Error calculating HSI: {e}")
    
    def calculate_all(self):
        """انجام تمام محاسبات"""
        try:
            self.calculate_tfa()
            self.calculate_bit_drilled()
            self.calculate_rop()
            self.calculate_hsi()
            
            # TODO: محاسبات اضافی
            self.calculate_annular_velocity()
            self.calculate_bit_revolution()
            
            logger.info("All calculations completed")
            
        except Exception as e:
            logger.error(f"Error in calculate_all: {e}")
    
    def calculate_annular_velocity(self):
        """محاسبه سرعت حلقوی"""
        # پیاده‌سازی ساده
        try:
            flow_rate = (self.pump_output_min.value() + self.pump_output_max.value()) / 2
            bit_size = self.bit_size.value()
            
            if bit_size > 0:
                # فرمول ساده‌شده
                av = flow_rate * 0.5 / bit_size
                self.annular_velocity.setValue(round(av, 1))
        except Exception as e:
            logger.error(f"Error calculating annular velocity: {e}")
    
    def calculate_bit_revolution(self):
        """محاسبه دور تجمعی مته"""
        try:
            rpm_avg = (self.rpm_min.value() + self.rpm_max.value()) / 2
            hours = self.hours_on_bottom.value()
            
            bit_rev = rpm_avg * hours * 60  # تبدیل به دقیقه
            self.bit_revolution.setValue(round(bit_rev, 0))
        except Exception as e:
            logger.error(f"Error calculating bit revolution: {e}")
    
    # ============ Data Methods ============
    def set_current_well(self, well_id):
        """تنظیم چاه جاری"""
        self.current_well = well_id
    
    def save_data(self):
        """ذخیره داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for saving")
            return False
        
        try:
            # جمع‌آوری داده‌های نازل‌ها
            nozzles_data = []
            for row in range(self.nozzle_table.rowCount()):
                size_widget = self.nozzle_table.cellWidget(row, 1)
                qty_widget = self.nozzle_table.cellWidget(row, 2)
                
                if size_widget and qty_widget:
                    nozzle_info = {
                        'row': row + 1,
                        'size_32nd': size_widget.value(),
                        'quantity': qty_widget.value(),
                        'diameter_inch': size_widget.value() / 32.0
                    }
                    nozzles_data.append(nozzle_info)
            
            # آماده کردن داده‌ها
            drilling_data = {
                'well_id': self.current_well,
                'report_date': datetime.now().date(),
                'bit_no': self.bit_no.text(),
                'bit_rerun': self.bit_rerun.value(),
                'bit_size': self.bit_size.value(),
                'bit_type': self.bit_type.currentText(),
                'manufacturer': self.bit_manufacturer.text(),
                'iadc_code': self.iadc_code.text(),
                'nozzles_json': json.dumps(nozzles_data, indent=2),
                'tfa': self.tfa_value.value(),
                'depth_in': self.depth_in.value(),
                'depth_out': self.depth_out.value(),
                'bit_drilled': self.bit_drilled.value(),
                'cum_drilled': self.cum_drilled.value(),
                'hours_on_bottom': self.hours_on_bottom.value(),
                'cum_hours': self.cum_hours.value(),
                'wob_min': self.wob_min.value(),
                'wob_max': self.wob_max.value(),
                'rpm_min': self.rpm_min.value(),
                'rpm_max': self.rpm_max.value(),
                'torque_min': self.torque_min.value(),
                'torque_max': self.torque_max.value(),
                'pump_pressure_min': self.pump_pressure_min.value(),
                'pump_pressure_max': self.pump_pressure_max.value(),
                'pump_output_min': self.pump_output_min.value(),
                'pump_output_max': self.pump_output_max.value(),
                'pump1_spm': self.pump1_spm.value(),
                'pump1_spp': self.pump1_spp.value(),
                'pump2_spm': self.pump2_spm.value(),
                'pump2_spp': self.pump2_spp.value(),
                'avg_rop': self.avg_rop.value(),
                'hsi': self.hsi.value(),
                'annular_velocity': self.annular_velocity.value(),
                'bit_revolution': self.bit_revolution.value()
            }
            
            # ذخیره در دیتابیس
            if self.db_manager:
                result = self.db_manager.save_drilling_parameters(drilling_data)
                if result:
                    logger.info(f"Drilling parameters saved with ID: {result}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving drilling parameters: {e}")
            return False
    
    def load_data(self):
        """بارگذاری داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for loading")
            return False
        
        try:
            if self.db_manager:
                # دریافت آخرین داده‌ها برای این چاه
                data = self.db_manager.get_drilling_parameters(self.current_well)
                
                if data:
                    self.load_from_dict(data)
                    logger.info("Drilling parameters loaded successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading drilling parameters: {e}")
            return False
    
    def load_from_dict(self, data: dict):
        """بارگذاری داده‌ها از دیکشنری"""
        try:
            self.bit_no.setText(data.get('bit_no', ''))
            self.bit_rerun.setValue(data.get('bit_rerun', 1))
            self.bit_size.setValue(data.get('bit_size', 0))
            
            bit_type = data.get('bit_type', '')
            if bit_type:
                index = self.bit_type.findText(bit_type)
                if index >= 0:
                    self.bit_type.setCurrentIndex(index)
            
            self.bit_manufacturer.setText(data.get('manufacturer', ''))
            self.iadc_code.setText(data.get('iadc_code', ''))
            
            # بارگذاری نازل‌ها
            nozzles_json = data.get('nozzles_json')
            if nozzles_json:
                self.nozzle_table.setRowCount(0)
                nozzles_data = json.loads(nozzles_json)
                for nozzle in nozzles_data:
                    self.add_nozzle_row(
                        nozzle.get('size_32nd', 16),
                        nozzle.get('quantity', 1)
                    )
            
            self.tfa_value.setValue(data.get('tfa', 0))
            self.depth_in.setValue(data.get('depth_in', 0))
            self.depth_out.setValue(data.get('depth_out', 0))
            self.bit_drilled.setValue(data.get('bit_drilled', 0))
            self.cum_drilled.setValue(data.get('cum_drilled', 0))
            self.hours_on_bottom.setValue(data.get('hours_on_bottom', 0))
            self.cum_hours.setValue(data.get('cum_hours', 0))
            self.wob_min.setValue(data.get('wob_min', 0))
            self.wob_max.setValue(data.get('wob_max', 0))
            self.rpm_min.setValue(data.get('rpm_min', 0))
            self.rpm_max.setValue(data.get('rpm_max', 0))
            self.torque_min.setValue(data.get('torque_min', 0))
            self.torque_max.setValue(data.get('torque_max', 0))
            self.pump_pressure_min.setValue(data.get('pump_pressure_min', 0))
            self.pump_pressure_max.setValue(data.get('pump_pressure_max', 0))
            self.pump_output_min.setValue(data.get('pump_output_min', 0))
            self.pump_output_max.setValue(data.get('pump_output_max', 0))
            self.pump1_spm.setValue(data.get('pump1_spm', 0))
            self.pump1_spp.setValue(data.get('pump1_spp', 0))
            self.pump2_spm.setValue(data.get('pump2_spm', 0))
            self.pump2_spp.setValue(data.get('pump2_spp', 0))
            self.avg_rop.setValue(data.get('avg_rop', 0))
            self.hsi.setValue(data.get('hsi', 0))
            self.annular_velocity.setValue(data.get('annular_velocity', 0))
            self.bit_revolution.setValue(data.get('bit_revolution', 0))
            
        except Exception as e:
            logger.error(f"Error loading from dict: {e}")
    
    def clear_form(self):
        """پاک کردن فرم"""
        self.bit_no.clear()
        self.bit_rerun.setValue(1)
        self.bit_size.setValue(8.5)
        self.bit_type.setCurrentIndex(0)
        self.bit_manufacturer.clear()
        self.iadc_code.clear()
        
        self.nozzle_table.setRowCount(0)
        self.add_nozzle_row(16, 1)
        self.add_nozzle_row(16, 1)
        self.add_nozzle_row(14, 1)
        
        self.tfa_value.setValue(0)
        self.depth_in.setValue(0)
        self.depth_out.setValue(0)
        self.bit_drilled.setValue(0)
        self.cum_drilled.setValue(0)
        self.hours_on_bottom.setValue(0)
        self.cum_hours.setValue(0)
        self.wob_min.setValue(0)
        self.wob_max.setValue(0)
        self.rpm_min.setValue(0)
        self.rpm_max.setValue(0)
        self.torque_min.setValue(0)
        self.torque_max.setValue(0)
        self.pump_pressure_min.setValue(0)
        self.pump_pressure_max.setValue(0)
        self.pump_output_min.setValue(0)
        self.pump_output_max.setValue(0)
        self.pump1_spm.setValue(0)
        self.pump1_spp.setValue(0)
        self.pump2_spm.setValue(0)
        self.pump2_spp.setValue(0)
        self.avg_rop.setValue(0)
        self.hsi.setValue(0)
        self.annular_velocity.setValue(0)
        self.bit_revolution.setValue(0)

    def on_bit_type_changed(self, text):
        """هنگام تغییر نوع مته"""
        try:
            # می‌توانید تنظیمات پیش‌فرض برای هر نوع مته را اعمال کنید
            bit_type_defaults = {
                "PDC": {"iadc_code": "M333", "bit_size": 8.5},
                "Tricone": {"iadc_code": "S333", "bit_size": 8.5},
                "Impregnated": {"iadc_code": "M444", "bit_size": 8.5},
                "Diamond": {"iadc_code": "D666", "bit_size": 8.5}
            }
            
            if text in bit_type_defaults:
                defaults = bit_type_defaults[text]
                if not self.iadc_code.text():  # اگر خالی است
                    self.iadc_code.setText(defaults["iadc_code"])
                
                logger.info(f"Bit type changed to: {text}")
        except Exception as e:
            logger.error(f"Error in on_bit_type_changed: {e}")

    def on_iadc_code_changed(self, text):
        """هنگام تغییر کد IADC"""
        try:
            # اعتبارسنجی فرمت کد IADC (مثال: M333, S444, etc.)
            if text and len(text) >= 3:
                # کد باید با حرف انگلیسی شروع شود
                if text[0].isalpha():
                    logger.info(f"IADC code changed to: {text}")
                else:
                    logger.warning(f"Invalid IADC code format: {text}")
        except Exception as e:
            logger.error(f"Error in on_iadc_code_changed: {e}")

    def update_cumulative_info(self):
        """به‌روزرسانی اطلاعات تجمعی"""
        try:
            # می‌توانید محاسبات اضافی انجام دهید
            cum_drilled = self.cum_drilled.value()
            cum_hours = self.cum_hours.value()
            
            if cum_hours > 0:
                cum_rop = cum_drilled / cum_hours
                # اگر فیلد نمایش ROP تجمعی دارید:
                # self.cum_rop.setValue(cum_rop)
            
            logger.debug(f"Cumulative info updated: Drilled={cum_drilled}m, Hours={cum_hours}hr")
        except Exception as e:
            logger.error(f"Error in update_cumulative_info: {e}")

    def update_bit_info(self):
        """به‌روزرسانی اطلاعات مته (اگر لازم است)"""
        try:
            # این تابع را می‌توانید برای بارگذاری مشخصات مته از دیتابیس استفاده کنید
            bit_no = self.bit_no.text()
            if bit_no:
                logger.info(f"Looking up bit info for: {bit_no}")
                # در اینجا می‌توانید از دیتابیس مشخصات مته را بگیرید
        except Exception as e:
            logger.error(f"Error in update_bit_info: {e}")

    def update_bit_specifications(self):
        """به‌روزرسانی مشخصات مته بر اساس کد IADC"""
        try:
            iadc_code = self.iadc_code.text()
            if iadc_code and len(iadc_code) >= 3:
                # در اینجا می‌توانید مشخصات مته را از جدول مشخصات بارگذاری کنید
                logger.info(f"Updating bit specs for IADC: {iadc_code}")
        except Exception as e:
            logger.error(f"Error in update_bit_specifications: {e}")
        
# ==================== CLASS 2: MudReportTab ====================
class MudReportTab(QWidget):
    """تب گزارش گل حفاری"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        
        self.current_well = None
        self.current_data = {}
        
        self.init_ui()
        self.setup_connections()
        
        logger.info("MudReportTab initialized")
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ایجاد اسکرول‌ایریا
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        # ============ Mud Properties ============
        properties_group = QGroupBox("🧪 Mud Properties")
        properties_layout = QGridLayout()
        
        # Mud Type
        properties_layout.addWidget(QLabel("Mud Type:"), 0, 0)
        self.mud_type = QComboBox()
        self.mud_type.addItems(["WBM", "OBM", "SOBM", "Pseudo Oil", "Synthetic"])
        properties_layout.addWidget(self.mud_type, 0, 1)
        
        # Sample Time
        properties_layout.addWidget(QLabel("Sample Time:"), 0, 2)
        self.sample_time = QTimeEdit()
        self.sample_time.setTime(QTime.currentTime())
        properties_layout.addWidget(self.sample_time, 0, 3)
        
        # MW (Mud Weight)
        properties_layout.addWidget(QLabel("MW (pcf):"), 1, 0)
        self.mw = QDoubleSpinBox()
        self.mw.setRange(0, 200)
        self.mw.setDecimals(1)
        self.mw.setValue(65.0)
        properties_layout.addWidget(self.mw, 1, 1)
        
        # PV (Plastic Viscosity)
        properties_layout.addWidget(QLabel("PV (cp):"), 1, 2)
        self.pv = QDoubleSpinBox()
        self.pv.setRange(0, 200)
        self.pv.setDecimals(1)
        properties_layout.addWidget(self.pv, 1, 3)
        
        # YP (Yield Point)
        properties_layout.addWidget(QLabel("YP (lb/100ft²):"), 2, 0)
        self.yp = QDoubleSpinBox()
        self.yp.setRange(0, 100)
        self.yp.setDecimals(1)
        properties_layout.addWidget(self.yp, 2, 1)
        
        # Funnel Viscosity
        properties_layout.addWidget(QLabel("Funnel Viscosity (sec/qt):"), 2, 2)
        self.funnel_vis = QDoubleSpinBox()
        self.funnel_vis.setRange(0, 200)
        self.funnel_vis.setDecimals(1)
        properties_layout.addWidget(self.funnel_vis, 2, 3)
        
        # Gel 10s
        properties_layout.addWidget(QLabel("Gel 10s:"), 3, 0)
        self.gel_10s = QDoubleSpinBox()
        self.gel_10s.setRange(0, 100)
        self.gel_10s.setDecimals(1)
        properties_layout.addWidget(self.gel_10s, 3, 1)
        
        # Gel 10m
        properties_layout.addWidget(QLabel("Gel 10m:"), 3, 2)
        self.gel_10m = QDoubleSpinBox()
        self.gel_10m.setRange(0, 100)
        self.gel_10m.setDecimals(1)
        properties_layout.addWidget(self.gel_10m, 3, 3)
        
        # FL (Fluid Loss)
        properties_layout.addWidget(QLabel("FL (cc/30min):"), 4, 0)
        self.fl = QDoubleSpinBox()
        self.fl.setRange(0, 50)
        self.fl.setDecimals(1)
        properties_layout.addWidget(self.fl, 4, 1)
        
        # Cake Thickness
        properties_layout.addWidget(QLabel("Cake Thickness (mm):"), 4, 2)
        self.cake_thickness = QDoubleSpinBox()
        self.cake_thickness.setRange(0, 20)
        self.cake_thickness.setDecimals(1)
        properties_layout.addWidget(self.cake_thickness, 4, 3)
        
        # pH
        properties_layout.addWidget(QLabel("pH:"), 5, 0)
        self.ph = QDoubleSpinBox()
        self.ph.setRange(0, 14)
        self.ph.setDecimals(1)
        self.ph.setValue(9.5)
        properties_layout.addWidget(self.ph, 5, 1)
        
        # Temperature
        properties_layout.addWidget(QLabel("Temperature (°C):"), 5, 2)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0, 200)
        self.temperature.setDecimals(1)
        self.temperature.setValue(25.0)
        properties_layout.addWidget(self.temperature, 5, 3)
        
        properties_group.setLayout(properties_layout)
        content_layout.addWidget(properties_group)
        
        # ============ Solids Analysis ============
        solids_group = QGroupBox("🔬 Solids Analysis")
        solids_layout = QGridLayout()
        
        # Solids Percent
        solids_layout.addWidget(QLabel("Solids (%):"), 0, 0)
        self.solid_percent = QDoubleSpinBox()
        self.solid_percent.setRange(0, 100)
        self.solid_percent.setDecimals(1)
        solids_layout.addWidget(self.solid_percent, 0, 1)
        
        # Oil Percent
        solids_layout.addWidget(QLabel("Oil (%):"), 0, 2)
        self.oil_percent = QDoubleSpinBox()
        self.oil_percent.setRange(0, 100)
        self.oil_percent.setDecimals(1)
        solids_layout.addWidget(self.oil_percent, 0, 3)
        
        # Water Percent
        solids_layout.addWidget(QLabel("Water (%):"), 1, 0)
        self.water_percent = QDoubleSpinBox()
        self.water_percent.setRange(0, 100)
        self.water_percent.setDecimals(1)
        solids_layout.addWidget(self.water_percent, 1, 1)
        
        # Chloride
        solids_layout.addWidget(QLabel("Chloride (ppm):"), 1, 2)
        self.chloride = QDoubleSpinBox()
        self.chloride.setRange(0, 50000)
        self.chloride.setDecimals(0)
        solids_layout.addWidget(self.chloride, 1, 3)
        
        solids_group.setLayout(solids_layout)
        content_layout.addWidget(solids_group)
        
        # ============ Volumes ============
        volumes_group = QGroupBox("📊 Volumes")
        volumes_layout = QGridLayout()
        
        # Volume in Hole
        volumes_layout.addWidget(QLabel("Volume in Hole (bbl):"), 0, 0)
        self.volume_hole = QDoubleSpinBox()
        self.volume_hole.setRange(0, 10000)
        self.volume_hole.setDecimals(1)
        volumes_layout.addWidget(self.volume_hole, 0, 1)
        
        # Total Circulated
        volumes_layout.addWidget(QLabel("Total Circulated (bbl):"), 0, 2)
        self.total_circulated = QDoubleSpinBox()
        self.total_circulated.setRange(0, 20000)
        self.total_circulated.setDecimals(1)
        volumes_layout.addWidget(self.total_circulated, 0, 3)
        
        # Downhole Loss
        volumes_layout.addWidget(QLabel("Downhole Loss (bbl):"), 1, 0)
        self.loss_downhole = QDoubleSpinBox()
        self.loss_downhole.setRange(0, 5000)
        self.loss_downhole.setDecimals(1)
        volumes_layout.addWidget(self.loss_downhole, 1, 1)
        
        # Surface Loss
        volumes_layout.addWidget(QLabel("Surface Loss (bbl):"), 1, 2)
        self.loss_surface = QDoubleSpinBox()
        self.loss_surface.setRange(0, 5000)
        self.loss_surface.setDecimals(1)
        volumes_layout.addWidget(self.loss_surface, 1, 3)
        
        volumes_group.setLayout(volumes_layout)
        content_layout.addWidget(volumes_group)
        
        # ============ Mud Chemicals ============
        chemicals_group = QGroupBox("🧪 Mud Chemicals")
        chemicals_layout = QVBoxLayout()
        
        # جدول مواد شیمیایی
        self.chemicals_table = QTableWidget(0, 6)
        self.chemicals_table.setHorizontalHeaderLabels([
            "Product", "Type", "Received", "Used", "Stock", "Unit"
        ])
        self.chemicals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.chemicals_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chemicals_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.chemicals_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        chemicals_layout.addWidget(self.chemicals_table)
        
        # دکمه‌های کنترل جدول
        chem_btn_layout = QHBoxLayout()
        add_chem_btn = QPushButton("➕ Add Chemical")
        add_chem_btn.clicked.connect(self.add_chemical_row)
        remove_chem_btn = QPushButton("➖ Remove")
        remove_chem_btn.clicked.connect(self.remove_chemical_row)
        calc_stock_btn = QPushButton("🔄 Calculate Stock")
        calc_stock_btn.clicked.connect(self.calculate_stock)
        
        chem_btn_layout.addWidget(add_chem_btn)
        chem_btn_layout.addWidget(remove_chem_btn)
        chem_btn_layout.addWidget(calc_stock_btn)
        chem_btn_layout.addStretch()
        chemicals_layout.addLayout(chem_btn_layout)
        
        chemicals_group.setLayout(chemicals_layout)
        content_layout.addWidget(chemicals_group)
        
        # ============ Mud Summary ============
        summary_group = QGroupBox("📝 Mud Summary")
        summary_layout = QVBoxLayout()
        
        self.mud_summary = QTextEdit()
        self.mud_summary.setMaximumHeight(100)
        self.mud_summary.setPlaceholderText("Enter mud condition summary...")
        summary_layout.addWidget(self.mud_summary)
        
        summary_group.setLayout(summary_layout)
        content_layout.addWidget(summary_group)
        
        # ============ Action Buttons ============
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_data)
        self.load_btn = QPushButton("📂 Load")
        self.load_btn.clicked.connect(self.load_data)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addStretch()
        
        content_layout.addLayout(btn_layout)
        content_layout.addStretch()
        
        # تنظیم اسکرول
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # اضافه کردن ردیف‌های نمونه
        self.add_chemical_row("Bentonite", "Viscosifier", 100, 50, 50, "kg")
        self.add_chemical_row("Barite", "Weight Material", 200, 100, 100, "kg")
        self.add_chemical_row("Caustic Soda", "Alkalinity", 50, 20, 30, "kg")
    
    def setup_connections(self):
        """اتصال سیگنال‌ها برای تب گزارش گل"""
        # اتصال تغییرات درصدها برای محاسبه کل
        self.solid_percent.valueChanged.connect(self.check_percentages_total)
        self.oil_percent.valueChanged.connect(self.check_percentages_total)
        self.water_percent.valueChanged.connect(self.check_percentages_total)
        
        # اتصال تغییرات حجم‌ها - اصلاح توابع
        self.volume_hole.valueChanged.connect(self.update_mud_volumes)
        self.total_circulated.valueChanged.connect(self.update_mud_volumes)
        self.loss_downhole.valueChanged.connect(self.update_mud_losses)  # تغییر نام تابع
        self.loss_surface.valueChanged.connect(self.update_mud_losses)  # تغییر نام تابع
        
        # اتصال تغییرات خواص گل
        self.mw.valueChanged.connect(self.update_mud_properties)
        self.pv.valueChanged.connect(self.update_mud_properties)
        self.yp.valueChanged.connect(self.update_mud_properties)
        self.ph.valueChanged.connect(self.update_ph_balance)  # تغییر نام تابع
        self.temperature.valueChanged.connect(self.update_temperature_effects)
        
        # اتصال تغییرات نوع گل
        self.mud_type.currentTextChanged.connect(self.update_mud_formulation)
        
        # اتصال تغییرات نمونه‌گیری
        self.sample_time.timeChanged.connect(self.update_sample_time)
    
    # ============ Chemicals Table Methods ============
    def add_chemical_row(self, product="", product_type="", received=0, used=0, stock=0, unit="kg"):
        """اضافه کردن ردیف به جدول مواد شیمیایی"""
        row = self.chemicals_table.rowCount()
        self.chemicals_table.insertRow(row)
        
        # Product - اصلاح شده
        product_edit = QLineEdit()
        if product and isinstance(product, str):
            product_edit.setText(str(product))
        else:
            product_edit.setText(f"Chemical_{row+1}")
        
        # اتصال تغییرات محصول
        product_edit.textChanged.connect(lambda text, r=row: self.on_chemical_product_changed(r, text))
        self.chemicals_table.setCellWidget(row, 0, product_edit)
        
        # Type
        type_combo = QComboBox()
        type_items = ["Viscosifier", "Weight Material", "Alkalinity", 
                      "Filtration Control", "Lubricant", "Shale Inhibitor"]
        type_combo.addItems(type_items)
        
        if product_type and product_type in type_items:
            index = type_combo.findText(product_type)
            if index >= 0:
                type_combo.setCurrentIndex(index)
        else:
            type_combo.setCurrentIndex(0)
        
        # اتصال تغییرات نوع
        type_combo.currentTextChanged.connect(lambda text, r=row: self.on_chemical_type_changed(r, text))
        self.chemicals_table.setCellWidget(row, 1, type_combo)
        
        # Received
        received_spin = QDoubleSpinBox()
        received_spin.setRange(0, 10000)
        received_spin.setValue(received)
        received_spin.valueChanged.connect(self.calculate_stock)
        self.chemicals_table.setCellWidget(row, 2, received_spin)
        
        # Used
        used_spin = QDoubleSpinBox()
        used_spin.setRange(0, 10000)
        used_spin.setValue(used)
        used_spin.valueChanged.connect(self.calculate_stock)
        self.chemicals_table.setCellWidget(row, 3, used_spin)
        
        # Stock (read-only)
        stock_spin = QDoubleSpinBox()
        stock_spin.setRange(-10000, 10000)
        stock_spin.setValue(stock)
        stock_spin.setReadOnly(True)
        self.chemicals_table.setCellWidget(row, 4, stock_spin)
        
        # Unit
        unit_combo = QComboBox()
        unit_items = ["kg", "lb", "bbl", "gal", "l", "m³"]
        unit_combo.addItems(unit_items)
        
        if unit and unit in unit_items:
            index = unit_combo.findText(unit)
            if index >= 0:
                unit_combo.setCurrentIndex(index)
        else:
            unit_combo.setCurrentIndex(0)
        
        # اتصال تغییرات واحد
        unit_combo.currentTextChanged.connect(lambda text, r=row: self.on_chemical_unit_changed(r, text))
        self.chemicals_table.setCellWidget(row, 5, unit_combo)
    
    def on_chemical_product_changed(self, row, product_name):
        """هنگام تغییر نام محصول شیمیایی"""
        logger.debug(f"Chemical product at row {row} changed to: {product_name}")

    def on_chemical_type_changed(self, row, type_name):
        """هنگام تغییر نوع ماده شیمیایی"""
        logger.debug(f"Chemical type at row {row} changed to: {type_name}")

    def on_chemical_unit_changed(self, row, unit_name):
        """هنگام تغییر واحد ماده شیمیایی"""
        logger.debug(f"Chemical unit at row {row} changed to: {unit_name}")
        
    def remove_chemical_row(self):
        """حذف ردیف انتخاب شده از جدول مواد شیمیایی"""
        current_row = self.chemicals_table.currentRow()
        if current_row >= 0:
            self.chemicals_table.removeRow(current_row)
    
    def calculate_stock(self):
        """محاسبه موجودی مواد شیمیایی"""
        for row in range(self.chemicals_table.rowCount()):
            try:
                received_widget = self.chemicals_table.cellWidget(row, 2)
                used_widget = self.chemicals_table.cellWidget(row, 3)
                stock_widget = self.chemicals_table.cellWidget(row, 4)
                
                if received_widget and used_widget and stock_widget:
                    received = received_widget.value()
                    used = used_widget.value()
                    stock = received - used
                    stock_widget.setValue(stock)
            except Exception as e:
                logger.error(f"Error calculating stock for row {row}: {e}")
    
    def check_percentages_total(self):
        """بررسی مجموع درصدها (اگر در تب گل استفاده می‌شود)"""
        try:
            # برای تب MudReportTab مناسب است
            total = (self.solid_percent.value() + 
                    self.oil_percent.value() + 
                    self.water_percent.value())
            
            if abs(total - 100.0) > 0.1:  # تحمل خطا
                logger.warning(f"Percentages total is {total:.1f}%, should be 100%")
                return False
            return True
        except Exception as e:
            logger.error(f"Error in check_percentages_total: {e}")
            return False

    def update_volumes(self):
        """به‌روزرسانی محاسبات حجم (برای تب گل)"""
        try:
            volume_hole = self.volume_hole.value()
            total_circulated = self.total_circulated.value()
            
            # اگر فیلدی برای اختلاف حجم دارید
            # volume_diff = total_circulated - volume_hole
            # self.volume_diff.setValue(volume_diff)
            
            logger.debug(f"Volumes updated: Hole={volume_hole}, Circulated={total_circulated}")
        except Exception as e:
            logger.error(f"Error in update_volumes: {e}")
    
    def check_percentages_total(self):
        """بررسی اینکه مجموع درصدها 100 باشد"""
        try:
            total = (self.solid_percent.value() + 
                    self.oil_percent.value() + 
                    self.water_percent.value())
            
            if abs(total - 100.0) > 0.1:
                logger.warning(f"Total percentages = {total:.1f}% (should be 100%)")
                return False
            return True
        except Exception as e:
            logger.error(f"Error in check_percentages_total: {e}")
            return False

    def update_mud_volumes(self):
        """به‌روزرسانی محاسبات حجم گل"""
        try:
            volume_hole = self.volume_hole.value()
            total_circulated = self.total_circulated.value()
            
            # محاسبه اختلاف
            volume_difference = total_circulated - volume_hole
            
            # می‌توانید این را در یک label نمایش دهید
            logger.debug(f"Mud volumes - Hole: {volume_hole}, Circulated: {total_circulated}, Diff: {volume_difference}")
            
            return volume_difference
        except Exception as e:
            logger.error(f"Error in update_mud_volumes: {e}")
            return 0

    def update_mud_losses(self):
        """به‌روزرسانی محاسبات تلفات گل"""
        try:
            loss_downhole = self.loss_downhole.value()
            loss_surface = self.loss_surface.value()
            total_loss = loss_downhole + loss_surface
            
            # محاسبه درصد تلفات نسبت به حجم چاه
            volume_hole = self.volume_hole.value()
            if volume_hole > 0:
                loss_percentage = (total_loss / volume_hole) * 100
                logger.debug(f"Mud losses - Downhole: {loss_downhole}, Surface: {loss_surface}, Total: {total_loss}, %: {loss_percentage:.1f}%")
            
            return total_loss
        except Exception as e:
            logger.error(f"Error in update_mud_losses: {e}")
            return 0

    def update_mud_properties(self):
        """به‌روزرسانی خواص گل"""
        try:
            # محاسبه نسبت YP/PV
            pv = self.pv.value()
            yp = self.yp.value()
            
            if pv > 0:
                yp_pv_ratio = yp / pv
                logger.debug(f"Mud properties - PV: {pv}, YP: {yp}, YP/PV ratio: {yp_pv_ratio:.2f}")
            
            # محاسبه وزن گل معادل
            mw = self.mw.value()
            if mw > 0:
                emw_ppg = mw / 7.48  # تبدیل از pcf به ppg
                logger.debug(f"Mud weight - PCF: {mw}, PPG: {emw_ppg:.2f}")
            
            return True
        except Exception as e:
            logger.error(f"Error in update_mud_properties: {e}")
            return False

    def update_ph_balance(self):
        """به‌روزرسانی تعادل pH"""
        try:
            ph_value = self.ph.value()
            
            # بررسی محدوده مناسب pH
            if ph_value < 8.0 or ph_value > 11.0:
                logger.warning(f"pH value {ph_value} is outside recommended range (8.0-11.0)")
            
            # پیشنهاد مواد شیمیایی بر اساس pH
            if ph_value < 8.5:
                logger.info("Low pH detected. Consider adding caustic soda (NaOH)")
            elif ph_value > 10.5:
                logger.info("High pH detected. Consider dilution or acid addition")
            
            return ph_value
        except Exception as e:
            logger.error(f"Error in update_ph_balance: {e}")
            return 0

    def update_temperature_effects(self):
        """به‌روزرسانی اثرات دما"""
        try:
            temp = self.temperature.value()
            
            # تصحیح ویسکوزیته بر اساس دما
            # فرمول ساده: ویسکوزیته در دمای بالاتر کاهش می‌یابد
            base_temp = 25.0  # دمای پایه
            funnel_vis = self.funnel_vis.value()
            
            if temp > base_temp and funnel_vis > 0:
                # کاهش تقریبی ویسکوزیته به ازای هر 10 درجه افزایش دما
                temp_diff = temp - base_temp
                corrected_vis = funnel_vis * (1 - (temp_diff * 0.02))  # 2% کاهش به ازای هر درجه
                logger.debug(f"Temperature correction - Actual: {funnel_vis}s, Corrected (@{base_temp}°C): {corrected_vis:.1f}s")
            
            return temp
        except Exception as e:
            logger.error(f"Error in update_temperature_effects: {e}")
            return 0

    def update_mud_formulation(self, mud_type):
        """به‌روزرسانی فرمولاسیون گل بر اساس نوع"""
        try:
            logger.info(f"Mud type changed to: {mud_type}")
            
            # تنظیمات پیش‌فرض بر اساس نوع گل
            defaults = {
                "WBM": {
                    "ph": 9.5,
                    "mw": 65.0,
                    "solid_percent": 15.0,
                    "water_percent": 85.0,
                    "oil_percent": 0.0
                },
                "OBM": {
                    "ph": 8.5,
                    "mw": 75.0,
                    "solid_percent": 20.0,
                    "water_percent": 10.0,
                    "oil_percent": 70.0
                },
                "SOBM": {
                    "ph": 8.0,
                    "mw": 80.0,
                    "solid_percent": 25.0,
                    "water_percent": 5.0,
                    "oil_percent": 70.0
                },
                "Pseudo Oil": {
                    "ph": 8.2,
                    "mw": 70.0,
                    "solid_percent": 18.0,
                    "water_percent": 15.0,
                    "oil_percent": 67.0
                },
                "Synthetic": {
                    "ph": 8.8,
                    "mw": 68.0,
                    "solid_percent": 16.0,
                    "water_percent": 20.0,
                    "oil_percent": 64.0
                }
            }
            
            if mud_type in defaults:
                default_values = defaults[mud_type]
                logger.info(f"Default values for {mud_type}: {default_values}")
                
                # می‌توانید مقادیر پیش‌فرض را اعمال کنید (اختیاری)
                # self.ph.setValue(default_values["ph"])
                # self.mw.setValue(default_values["mw"])
            
            return mud_type
        except Exception as e:
            logger.error(f"Error in update_mud_formulation: {e}")
            return ""

    def update_sample_time(self):
        """به‌روزرسانی زمان نمونه‌گیری"""
        try:
            sample_time = self.sample_time.time()
            logger.debug(f"Sample time updated: {sample_time.toString()}")
            return sample_time
        except Exception as e:
            logger.error(f"Error in update_sample_time: {e}")
            return QTime.currentTime()

    def update_chemical_consumption(self):
        """به‌روزرسانی مصرف مواد شیمیایی"""
        try:
            # محاسبه کل مواد شیمیایی مصرف شده
            total_used = 0
            for row in range(self.chemicals_table.rowCount()):
                used_widget = self.chemicals_table.cellWidget(row, 3)
                if used_widget:
                    total_used += used_widget.value()
            
            logger.debug(f"Total chemicals used: {total_used}")
            return total_used
        except Exception as e:
            logger.error(f"Error in update_chemical_consumption: {e}")
            return 0
    
    def calculate_stock(self):
        """محاسبه موجودی مواد شیمیایی"""
        try:
            for row in range(self.chemicals_table.rowCount()):
                received_widget = self.chemicals_table.cellWidget(row, 2)
                used_widget = self.chemicals_table.cellWidget(row, 3)
                stock_widget = self.chemicals_table.cellWidget(row, 4)
                
                if received_widget and used_widget and stock_widget:
                    received = received_widget.value()
                    used = used_widget.value()
                    stock = received - used
                    
                    # فقط اگر مقدار تغییر کرده باشد، آپدیت کنیم
                    if abs(stock_widget.value() - stock) > 0.001:
                        stock_widget.setValue(stock)
                    
                    # تغییر رنگ بر اساس سطح موجودی
                    if stock < 0:
                        stock_widget.setStyleSheet("color: red;")
                    elif stock < 10:
                        stock_widget.setStyleSheet("color: orange;")
                    else:
                        stock_widget.setStyleSheet("color: black;")
            
            # به‌روزرسانی مصرف کل
            self.update_chemical_consumption()
            
            return True
        except Exception as e:
            logger.error(f"Error calculating stock: {e}")
            return False
            
    # ============ Data Methods ============
    def set_current_well(self, well_id):
        """تنظیم چاه جاری"""
        self.current_well = well_id
    
    def save_data(self):
        """ذخیره داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for saving")
            return False
        
        try:
            # جمع‌آوری داده‌های جدول مواد شیمیایی
            chemicals_data = []
            for row in range(self.chemicals_table.rowCount()):
                row_data = {}
                
                product_widget = self.chemicals_table.cellWidget(row, 0)
                if product_widget:
                    row_data['product'] = product_widget.text()
                
                type_widget = self.chemicals_table.cellWidget(row, 1)
                if type_widget:
                    row_data['type'] = type_widget.currentText()
                
                received_widget = self.chemicals_table.cellWidget(row, 2)
                if received_widget:
                    row_data['received'] = received_widget.value()
                
                used_widget = self.chemicals_table.cellWidget(row, 3)
                if used_widget:
                    row_data['used'] = used_widget.value()
                
                stock_widget = self.chemicals_table.cellWidget(row, 4)
                if stock_widget:
                    row_data['stock'] = stock_widget.value()
                
                unit_widget = self.chemicals_table.cellWidget(row, 5)
                if unit_widget:
                    row_data['unit'] = unit_widget.currentText()
                
                chemicals_data.append(row_data)
            
            # آماده کردن داده‌های گل
            mud_data = {
                'well_id': self.current_well,
                'report_date': datetime.now().date(),
                'mud_type': self.mud_type.currentText(),
                'sample_time': self.sample_time.time().toString(),
                'mw': self.mw.value(),
                'pv': self.pv.value(),
                'yp': self.yp.value(),
                'funnel_vis': self.funnel_vis.value(),
                'gel_10s': self.gel_10s.value(),
                'gel_10m': self.gel_10m.value(),
                'fl': self.fl.value(),
                'cake_thickness': self.cake_thickness.value(),
                'ph': self.ph.value(),
                'temperature': self.temperature.value(),
                'solid_percent': self.solid_percent.value(),
                'oil_percent': self.oil_percent.value(),
                'water_percent': self.water_percent.value(),
                'chloride': self.chloride.value(),
                'volume_hole': self.volume_hole.value(),
                'total_circulated': self.total_circulated.value(),
                'loss_downhole': self.loss_downhole.value(),
                'loss_surface': self.loss_surface.value(),
                'chemicals_json': json.dumps(chemicals_data, indent=2),
                'summary': self.mud_summary.toPlainText()
            }
            
            # ذخیره در دیتابیس
            if self.db_manager:
                result = self.db_manager.save_mud_report(mud_data)
                if result:
                    logger.info(f"Mud report saved with ID: {result}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving mud report: {e}")
            return False
    
    def load_data(self):
        """بارگذاری داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for loading")
            return False
        
        try:
            if self.db_manager:
                # دریافت آخرین داده‌ها برای این چاه
                data = self.db_manager.get_mud_report(self.current_well)
                
                if data:
                    self.load_from_dict(data)
                    logger.info("Mud report loaded successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading mud report: {e}")
            return False
    
    def load_from_dict(self, data: dict):
        """بارگذاری داده‌ها از دیکشنری"""
        try:
            mud_type = data.get('mud_type', '')
            if mud_type:
                index = self.mud_type.findText(mud_type)
                if index >= 0:
                    self.mud_type.setCurrentIndex(index)
            
            sample_time = data.get('sample_time', '')
            if sample_time:
                time = QTime.fromString(sample_time)
                self.sample_time.setTime(time)
            
            self.mw.setValue(data.get('mw', 0))
            self.pv.setValue(data.get('pv', 0))
            self.yp.setValue(data.get('yp', 0))
            self.funnel_vis.setValue(data.get('funnel_vis', 0))
            self.gel_10s.setValue(data.get('gel_10s', 0))
            self.gel_10m.setValue(data.get('gel_10m', 0))
            self.fl.setValue(data.get('fl', 0))
            self.cake_thickness.setValue(data.get('cake_thickness', 0))
            self.ph.setValue(data.get('ph', 0))
            self.temperature.setValue(data.get('temperature', 0))
            self.solid_percent.setValue(data.get('solid_percent', 0))
            self.oil_percent.setValue(data.get('oil_percent', 0))
            self.water_percent.setValue(data.get('water_percent', 0))
            self.chloride.setValue(data.get('chloride', 0))
            self.volume_hole.setValue(data.get('volume_hole', 0))
            self.total_circulated.setValue(data.get('total_circulated', 0))
            self.loss_downhole.setValue(data.get('loss_downhole', 0))
            self.loss_surface.setValue(data.get('loss_surface', 0))
            self.mud_summary.setPlainText(data.get('summary', ''))
            
            # بارگذاری مواد شیمیایی
            chemicals_json = data.get('chemicals_json')
            if chemicals_json:
                self.chemicals_table.setRowCount(0)
                chemicals_data = json.loads(chemicals_json)
                for chem in chemicals_data:
                    self.add_chemical_row(
                        chem.get('product', ''),
                        chem.get('type', ''),
                        chem.get('received', 0),
                        chem.get('used', 0),
                        chem.get('stock', 0),
                        chem.get('unit', 'kg')
                    )
            
        except Exception as e:
            logger.error(f"Error loading from dict: {e}")
    
    def clear_form(self):
        """پاک کردن فرم"""
        self.mud_type.setCurrentIndex(0)
        self.sample_time.setTime(QTime.currentTime())
        self.mw.setValue(65.0)
        self.pv.setValue(0)
        self.yp.setValue(0)
        self.funnel_vis.setValue(0)
        self.gel_10s.setValue(0)
        self.gel_10m.setValue(0)
        self.fl.setValue(0)
        self.cake_thickness.setValue(0)
        self.ph.setValue(9.5)
        self.temperature.setValue(25.0)
        self.solid_percent.setValue(0)
        self.oil_percent.setValue(0)
        self.water_percent.setValue(0)
        self.chloride.setValue(0)
        self.volume_hole.setValue(0)
        self.total_circulated.setValue(0)
        self.loss_downhole.setValue(0)
        self.loss_surface.setValue(0)
        
        self.chemicals_table.setRowCount(0)
        self.add_chemical_row("Bentonite", "Viscosifier", 100, 50, 50, "kg")
        self.add_chemical_row("Barite", "Weight Material", 200, 100, 100, "kg")
        
        self.mud_summary.clear()

# ==================== CLASS 3: CementReportTab ====================
class CementReportTab(QWidget):
    """تب گزارش سیمان"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        
        self.current_well = None
        self.current_data = {}
        
        self.init_ui()
        self.setup_connections()
        
        logger.info("CementReportTab initialized")
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ایجاد اسکرول‌ایریا
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        # ============ Cement Header ============
        header_group = QGroupBox("🏗️ Cement Job Information")
        header_layout = QGridLayout()
        
        header_layout.addWidget(QLabel("Report Name:"), 0, 0)
        self.report_name = QLineEdit()
        self.report_name.setPlaceholderText("Enter cement report name...")
        header_layout.addWidget(self.report_name, 0, 1)
        
        header_layout.addWidget(QLabel("Cement Type:"), 0, 2)
        self.cement_type = QComboBox()
        self.cement_type.addItems(["Class G", "Class H", "Class A", "Class C", "Special"])
        header_layout.addWidget(self.cement_type, 0, 3)
        
        header_layout.addWidget(QLabel("Job Type:"), 1, 0)
        self.job_type = QComboBox()
        self.job_type.addItems([
            "Primary Cementing", 
            "Squeeze", 
            "Plug Back", 
            "Liner", 
            "Stage Cementing"
        ])
        header_layout.addWidget(self.job_type, 1, 1)
        
        header_layout.addWidget(QLabel("Date:"), 1, 2)
        self.report_date = QDateEdit()
        self.report_date.setDate(QDate.currentDate())
        self.report_date.setCalendarPopup(True)
        header_layout.addWidget(self.report_date, 1, 3)
        
        header_group.setLayout(header_layout)
        content_layout.addWidget(header_group)
        
        # ============ Cement Materials ============
        materials_group = QGroupBox("🧱 Cement Materials")
        materials_layout = QVBoxLayout()
        
        # جدول مواد سیمان
        self.materials_table = QTableWidget(0, 7)
        self.materials_table.setHorizontalHeaderLabels([
            "Material", "Type", "Received", "Consumed", "Backload", "Inventory", "Unit"
        ])
        self.materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.materials_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.materials_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.materials_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        materials_layout.addWidget(self.materials_table)
        
        # دکمه‌های کنترل جدول
        materials_btn_layout = QHBoxLayout()
        add_material_btn = QPushButton("➕ Add Material")
        add_material_btn.clicked.connect(self.add_material_row)
        remove_material_btn = QPushButton("➖ Remove")
        remove_material_btn.clicked.connect(self.remove_material_row)
        calc_inv_btn = QPushButton("🔄 Calculate Inventory")
        calc_inv_btn.clicked.connect(self.calculate_inventory)
        
        materials_btn_layout.addWidget(add_material_btn)
        materials_btn_layout.addWidget(remove_material_btn)
        materials_btn_layout.addWidget(calc_inv_btn)
        materials_btn_layout.addStretch()
        materials_layout.addLayout(materials_btn_layout)
        
        materials_group.setLayout(materials_layout)
        content_layout.addWidget(materials_group)
        
        # ============ Cement Parameters ============
        params_group = QGroupBox("⚙️ Cement Job Parameters")
        params_layout = QGridLayout()
        
        # Slurry Density
        params_layout.addWidget(QLabel("Slurry Density (pcf):"), 0, 0)
        self.slurry_density = QDoubleSpinBox()
        self.slurry_density.setRange(0, 200)
        self.slurry_density.setDecimals(1)
        self.slurry_density.setValue(120.0)
        params_layout.addWidget(self.slurry_density, 0, 1)
        
        # Slurry Yield
        params_layout.addWidget(QLabel("Slurry Yield (ft³/sk):"), 0, 2)
        self.slurry_yield = QDoubleSpinBox()
        self.slurry_yield.setRange(0, 10)
        self.slurry_yield.setDecimals(2)
        self.slurry_yield.setValue(1.18)
        params_layout.addWidget(self.slurry_yield, 0, 3)
        
        # Mix Water
        params_layout.addWidget(QLabel("Mix Water (gal/sk):"), 1, 0)
        self.mix_water = QDoubleSpinBox()
        self.mix_water.setRange(0, 20)
        self.mix_water.setDecimals(1)
        self.mix_water.setValue(5.2)
        params_layout.addWidget(self.mix_water, 1, 1)
        
        # Thickening Time
        params_layout.addWidget(QLabel("Thickening Time (hr:min):"), 1, 2)
        thickening_layout = QHBoxLayout()
        self.thickening_hours = QSpinBox()
        self.thickening_hours.setRange(0, 24)
        self.thickening_hours.setValue(4)
        thickening_layout.addWidget(self.thickening_hours)
        thickening_layout.addWidget(QLabel("hr"))
        
        self.thickening_minutes = QSpinBox()
        self.thickening_minutes.setRange(0, 59)
        self.thickening_minutes.setValue(30)
        thickening_layout.addWidget(self.thickening_minutes)
        thickening_layout.addWidget(QLabel("min"))
        thickening_layout.addStretch()
        params_layout.addLayout(thickening_layout, 1, 3)
        
        # Compressive Strength
        params_layout.addWidget(QLabel("Compressive Strength (psi):"), 2, 0)
        self.compressive_strength = QDoubleSpinBox()
        self.compressive_strength.setRange(0, 10000)
        self.compressive_strength.setDecimals(0)
        self.compressive_strength.setValue(2500)
        params_layout.addWidget(self.compressive_strength, 2, 1)
        
        # Fluid Loss
        params_layout.addWidget(QLabel("Fluid Loss (cc/30min):"), 2, 2)
        self.fluid_loss = QDoubleSpinBox()
        self.fluid_loss.setRange(0, 500)
        self.fluid_loss.setDecimals(0)
        params_layout.addWidget(self.fluid_loss, 2, 3)
        
        params_group.setLayout(params_layout)
        content_layout.addWidget(params_group)
        
        # ============ Cement Volumes ============
        volumes_group = QGroupBox("📊 Cement Volumes")
        volumes_layout = QGridLayout()
        
        # Cement Volume
        volumes_layout.addWidget(QLabel("Cement Volume (sacks):"), 0, 0)
        self.cement_volume = QDoubleSpinBox()
        self.cement_volume.setRange(0, 10000)
        self.cement_volume.setDecimals(0)
        volumes_layout.addWidget(self.cement_volume, 0, 1)
        
        # Displacement Volume
        volumes_layout.addWidget(QLabel("Displacement Volume (bbl):"), 0, 2)
        self.displacement_volume = QDoubleSpinBox()
        self.displacement_volume.setRange(0, 5000)
        self.displacement_volume.setDecimals(1)
        volumes_layout.addWidget(self.displacement_volume, 0, 3)
        
        # Top of Cement
        volumes_layout.addWidget(QLabel("Top of Cement (m):"), 1, 0)
        self.top_of_cement = QDoubleSpinBox()
        self.top_of_cement.setRange(0, 20000)
        self.top_of_cement.setDecimals(2)
        volumes_layout.addWidget(self.top_of_cement, 1, 1)
        
        # Bottom of Cement
        volumes_layout.addWidget(QLabel("Bottom of Cement (m):"), 1, 2)
        self.bottom_of_cement = QDoubleSpinBox()
        self.bottom_of_cement.setRange(0, 20000)
        self.bottom_of_cement.setDecimals(2)
        volumes_layout.addWidget(self.bottom_of_cement, 1, 3)
        
        volumes_group.setLayout(volumes_layout)
        content_layout.addWidget(volumes_group)
        
        # ============ Cement Summary ============
        summary_group = QGroupBox("📝 Cement Job Summary")
        summary_layout = QVBoxLayout()
        
        self.cement_summary = QTextEdit()
        self.cement_summary.setMaximumHeight(150)
        self.cement_summary.setPlaceholderText("Enter cement job summary...")
        summary_layout.addWidget(self.cement_summary)
        
        summary_group.setLayout(summary_layout)
        content_layout.addWidget(summary_group)
        
        # ============ Action Buttons ============
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_data)
        self.load_btn = QPushButton("📂 Load")
        self.load_btn.clicked.connect(self.load_data)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addStretch()
        
        content_layout.addLayout(btn_layout)
        content_layout.addStretch()
        
        # تنظیم اسکرول
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # اضافه کردن ردیف‌های نمونه
        self.add_material_row("Class G Cement", "Cement", 1000, 800, 200, 1000, "sacks")
        self.add_material_row("Silica Flour", "Additive", 500, 300, 200, 500, "kg")
        self.add_material_row("Retarder", "Additive", 100, 50, 50, 100, "kg")
    
    def setup_connections(self):
        """اتصال سیگنال‌ها برای تب گزارش سیمان"""
        # اتصال تغییرات حجم سیمان - اصلاح نام توابع
        self.cement_volume.valueChanged.connect(self.update_cement_volume_calcs)
        self.displacement_volume.valueChanged.connect(self.update_displacement_calcs)
        
        # اتصال تغییرات slurry properties - اصلاح نام توابع
        self.slurry_density.valueChanged.connect(self.update_slurry_properties)
        self.slurry_yield.valueChanged.connect(self.update_slurry_properties)
        self.mix_water.valueChanged.connect(self.update_water_requirements)
        
        # اتصال تغییرات زمان thickening
        self.thickening_hours.valueChanged.connect(self.update_thickening_time_display)
        self.thickening_minutes.valueChanged.connect(self.update_thickening_time_display)
        
        # اتصال تغییرات compressive strength
        self.compressive_strength.valueChanged.connect(self.update_strength_properties)
        
        # اتصال تغییرات fluid loss
        self.fluid_loss.valueChanged.connect(self.update_fluid_loss_info)
        
        # اتصال تغییرات عمق سیمان
        self.top_of_cement.valueChanged.connect(self.update_cement_depth_info)
        self.bottom_of_cement.valueChanged.connect(self.update_cement_depth_info)
        
        # اتصال تغییرات نوع سیمان
        self.cement_type.currentTextChanged.connect(self.update_cement_type_info)
        
        # اتصال تغییرات نوع job
        self.job_type.currentTextChanged.connect(self.update_job_type_info)
    
    # ============ Materials Table Methods ============
    def add_material_row(self, material="", material_type="", received=0, consumed=0, 
                         backload=0, inventory=0, unit="kg"):
        """اضافه کردن ردیف به جدول مواد سیمان"""
        row = self.materials_table.rowCount()
        self.materials_table.insertRow(row)
        
        # Material
        material_edit = QLineEdit()
        if material and isinstance(material, str):
            material_edit.setText(str(material))
        else:
            material_edit.setText(f"Material_{row+1}")
        
        # اتصال تغییرات نام ماده
        material_edit.textChanged.connect(lambda text, r=row: self.on_material_name_changed(r, text))
        self.materials_table.setCellWidget(row, 0, material_edit)
        
        # Type
        type_combo = QComboBox()
        type_items = ["Cement", "Additive", "Mix Water", "Spacer", 
                      "Chemical", "Pre-flush", "Post-flush"]
        type_combo.addItems(type_items)
        
        if material_type and material_type in type_items:
            index = type_combo.findText(material_type)
            if index >= 0:
                type_combo.setCurrentIndex(index)
        else:
            type_combo.setCurrentIndex(0)
        
        # اتصال تغییرات نوع
        type_combo.currentTextChanged.connect(lambda text, r=row: self.on_material_type_changed(r, text))
        self.materials_table.setCellWidget(row, 1, type_combo)
        
        # Received
        received_spin = QDoubleSpinBox()
        received_spin.setRange(0, 10000)
        received_spin.setValue(received)
        received_spin.valueChanged.connect(self.calculate_inventory)
        self.materials_table.setCellWidget(row, 2, received_spin)
        
        # Consumed
        consumed_spin = QDoubleSpinBox()
        consumed_spin.setRange(0, 10000)
        consumed_spin.setValue(consumed)
        consumed_spin.valueChanged.connect(self.calculate_inventory)
        self.materials_table.setCellWidget(row, 3, consumed_spin)
        
        # Backload
        backload_spin = QDoubleSpinBox()
        backload_spin.setRange(0, 10000)
        backload_spin.setValue(backload)
        # اتصال تغییرات backload
        backload_spin.valueChanged.connect(lambda value, r=row: self.on_backload_changed(r, value))
        self.materials_table.setCellWidget(row, 4, backload_spin)
        
        # Inventory (read-only)
        inventory_spin = QDoubleSpinBox()
        inventory_spin.setRange(-10000, 10000)
        inventory_spin.setValue(inventory)
        inventory_spin.setReadOnly(True)
        self.materials_table.setCellWidget(row, 5, inventory_spin)
        
        # Unit
        unit_combo = QComboBox()
        unit_items = ["sacks", "kg", "lb", "bbl", "gal", "m³"]
        unit_combo.addItems(unit_items)
        
        if unit and unit in unit_items:
            index = unit_combo.findText(unit)
            if index >= 0:
                unit_combo.setCurrentIndex(index)
        else:
            unit_combo.setCurrentIndex(0)
        
        # اتصال تغییرات واحد
        unit_combo.currentTextChanged.connect(lambda text, r=row: self.on_material_unit_changed(r, text))
        self.materials_table.setCellWidget(row, 6, unit_combo)
    
    def remove_material_row(self):
        """حذف ردیف انتخاب شده از جدول مواد سیمان"""
        current_row = self.materials_table.currentRow()
        if current_row >= 0:
            self.materials_table.removeRow(current_row)
    
    def calculate_inventory(self):
        """محاسبه موجودی مواد سیمان"""
        try:
            for row in range(self.materials_table.rowCount()):
                received_widget = self.materials_table.cellWidget(row, 2)
                consumed_widget = self.materials_table.cellWidget(row, 3)
                inventory_widget = self.materials_table.cellWidget(row, 5)
                
                if received_widget and consumed_widget and inventory_widget:
                    received = received_widget.value()
                    consumed = consumed_widget.value()
                    inventory = received - consumed
                    
                    # فقط اگر مقدار تغییر کرده باشد، آپدیت کنیم
                    if abs(inventory_widget.value() - inventory) > 0.001:
                        inventory_widget.setValue(inventory)
                    
                    # تغییر رنگ بر اساس سطح موجودی
                    if inventory < 0:
                        inventory_widget.setStyleSheet("color: red; font-weight: bold;")
                    elif inventory < 50:
                        inventory_widget.setStyleSheet("color: orange;")
                    else:
                        inventory_widget.setStyleSheet("color: black;")
            
            return True
        except Exception as e:
            logger.error(f"Error calculating inventory: {e}")
            return False
        
    def update_cement_volume_calcs(self):
        """به‌روزرسانی محاسبات حجم سیمان"""
        try:
            cement_volume = self.cement_volume.value()
            
            # اگر slurry yield مشخص باشد، حجم slurry را محاسبه کن
            slurry_yield = self.slurry_yield.value()
            if slurry_yield > 0:
                slurry_volume = cement_volume * slurry_yield  # ft³
                logger.debug(f"Cement volume: {cement_volume} sacks, Slurry volume: {slurry_volume:.2f} ft³")
            
            # اگر mix water مشخص باشد، حجم آب را محاسبه کن
            mix_water_per_sk = self.mix_water.value()
            if mix_water_per_sk > 0:
                total_water = cement_volume * mix_water_per_sk  # gallons
                logger.debug(f"Total mix water required: {total_water:.1f} gallons")
            
            return cement_volume
        except Exception as e:
            logger.error(f"Error in update_cement_volume_calcs: {e}")
            return 0

    def update_displacement_calcs(self):
        """به‌روزرسانی محاسبات حجم جابجایی"""
        try:
            displacement_volume = self.displacement_volume.value()
            
            # محاسبات مربوط به حجم جابجایی
            # می‌توانید محاسبات اضافی انجام دهید
            logger.debug(f"Displacement volume: {displacement_volume:.1f} bbl")
            
            return displacement_volume
        except Exception as e:
            logger.error(f"Error in update_displacement_calcs: {e}")
            return 0

    def update_slurry_properties(self):
        """به‌روزرسانی خواص slurry"""
        try:
            slurry_density = self.slurry_density.value()
            slurry_yield = self.slurry_yield.value()
            
            # محاسبات مربوط به slurry
            if slurry_density > 0 and slurry_yield > 0:
                # محاسبه وزن کل slurry
                cement_volume = self.cement_volume.value()
                if cement_volume > 0:
                    total_slurry_weight = slurry_density * cement_volume * slurry_yield
                    logger.debug(f"Slurry density: {slurry_density} pcf, Yield: {slurry_yield} ft³/sk, Total weight: {total_slurry_weight:.0f} lb")
            
            return slurry_density, slurry_yield
        except Exception as e:
            logger.error(f"Error in update_slurry_properties: {e}")
            return 0, 0

    def update_water_requirements(self):
        """به‌روزرسانی نیازهای آب"""
        try:
            mix_water = self.mix_water.value()
            cement_volume = self.cement_volume.value()
            
            # محاسبه کل آب مورد نیاز
            total_water = cement_volume * mix_water  # gallons
            total_water_bbl = total_water / 42.0  # تبدیل به بشکه
            
            logger.debug(f"Mix water: {mix_water} gal/sk, Total water: {total_water:.1f} gal ({total_water_bbl:.2f} bbl)")
            
            return total_water
        except Exception as e:
            logger.error(f"Error in update_water_requirements: {e}")
            return 0

    def update_thickening_time_display(self):
        """به‌روزرسانی نمایش زمان thickening"""
        try:
            hours = self.thickening_hours.value()
            minutes = self.thickening_minutes.value()
            
            # محاسبه کل دقیقه
            total_minutes = hours * 60 + minutes
            
            # فرمت نمایش
            display_text = f"{hours:02d}:{minutes:02d}"
            logger.debug(f"Thickening time: {display_text} (Total: {total_minutes} minutes)")
            
            # بررسی محدوده مناسب
            if total_minutes < 120:  # کمتر از 2 ساعت
                logger.warning("Thickening time is less than 2 hours - may be too short")
            elif total_minutes > 480:  # بیشتر از 8 ساعت
                logger.warning("Thickening time is more than 8 hours - may be too long")
            
            return display_text, total_minutes
        except Exception as e:
            logger.error(f"Error in update_thickening_time_display: {e}")
            return "00:00", 0

    def update_strength_properties(self):
        """به‌روزرسانی خواص مقاومتی"""
        try:
            compressive_strength = self.compressive_strength.value()
            
            # بررسی محدوده مقاومت
            if compressive_strength < 1000:
                logger.warning(f"Compressive strength {compressive_strength} psi is very low")
            elif compressive_strength > 5000:
                logger.info(f"High compressive strength: {compressive_strength} psi")
            
            # محاسبه مقاومت بر حسب MPa (اختیاری)
            strength_mpa = compressive_strength * 0.00689476
            logger.debug(f"Compressive strength: {compressive_strength} psi ({strength_mpa:.2f} MPa)")
            
            return compressive_strength
        except Exception as e:
            logger.error(f"Error in update_strength_properties: {e}")
            return 0

    def update_fluid_loss_info(self):
        """به‌روزرسانی اطلاعات fluid loss"""
        try:
            fluid_loss = self.fluid_loss.value()
            
            # بررسی محدوده مناسب
            if fluid_loss < 50:
                logger.info(f"Low fluid loss: {fluid_loss} cc/30min (excellent control)")
            elif fluid_loss > 200:
                logger.warning(f"High fluid loss: {fluid_loss} cc/30min (may need additives)")
            
            return fluid_loss
        except Exception as e:
            logger.error(f"Error in update_fluid_loss_info: {e}")
            return 0

    def update_cement_depth_info(self):
        """به‌روزرسانی اطلاعات عمق سیمان"""
        try:
            top = self.top_of_cement.value()
            bottom = self.bottom_of_cement.value()
            
            # محاسبه ارتفاع ستون سیمان
            if bottom > top:
                cement_height = bottom - top
                logger.debug(f"Cement column - Top: {top}m, Bottom: {bottom}m, Height: {cement_height}m")
            else:
                logger.warning(f"Bottom of cement ({bottom}m) should be deeper than top ({top}m)")
                cement_height = 0
            
            return top, bottom, cement_height
        except Exception as e:
            logger.error(f"Error in update_cement_depth_info: {e}")
            return 0, 0, 0

    def update_cement_type_info(self, cement_type):
        """به‌روزرسانی اطلاعات نوع سیمان"""
        try:
            logger.info(f"Cement type changed to: {cement_type}")
            
            # تنظیمات پیش‌فرض بر اساس نوع سیمان
            defaults = {
                "Class G": {
                    "slurry_density": 119.0,
                    "slurry_yield": 1.18,
                    "mix_water": 5.2,
                    "compressive_strength": 2500
                },
                "Class H": {
                    "slurry_density": 118.0,
                    "slurry_yield": 1.16,
                    "mix_water": 5.0,
                    "compressive_strength": 2400
                },
                "Class A": {
                    "slurry_density": 117.0,
                    "slurry_yield": 1.15,
                    "mix_water": 5.8,
                    "compressive_strength": 2200
                },
                "Class C": {
                    "slurry_density": 120.0,
                    "slurry_yield": 1.20,
                    "mix_water": 6.0,
                    "compressive_strength": 2600
                },
                "Special": {
                    "slurry_density": 125.0,
                    "slurry_yield": 1.05,
                    "mix_water": 4.5,
                    "compressive_strength": 3000
                }
            }
            
            if cement_type in defaults:
                default_values = defaults[cement_type]
                logger.info(f"Default values for {cement_type}: {default_values}")
                
                # می‌توانید مقادیر پیش‌فرض را اعمال کنید (اختیاری)
                # self.slurry_density.setValue(default_values["slurry_density"])
                # self.slurry_yield.setValue(default_values["slurry_yield"])
            
            return cement_type
        except Exception as e:
            logger.error(f"Error in update_cement_type_info: {e}")
            return ""

    def update_job_type_info(self, job_type):
        """به‌روزرسانی اطلاعات نوع کار"""
        try:
            logger.info(f"Job type changed to: {job_type}")
            
            # تنظیمات بر اساس نوع کار
            job_requirements = {
                "Primary Cementing": {
                    "description": "Primary cementing of casing string",
                    "typical_thickening": "4-6 hours",
                    "fluid_loss_limit": 150
                },
                "Squeeze": {
                    "description": "Squeeze cementing to repair or isolate zones",
                    "typical_thickening": "2-4 hours",
                    "fluid_loss_limit": 100
                },
                "Plug Back": {
                    "description": "Plug back operation to abandon zone",
                    "typical_thickening": "3-5 hours",
                    "fluid_loss_limit": 120
                },
                "Liner": {
                    "description": "Liner cementing operation",
                    "typical_thickening": "4-7 hours",
                    "fluid_loss_limit": 140
                },
                "Stage Cementing": {
                    "description": "Multiple stage cementing operation",
                    "typical_thickening": "3-6 hours per stage",
                    "fluid_loss_limit": 130
                }
            }
            
            if job_type in job_requirements:
                requirements = job_requirements[job_type]
                logger.info(f"Requirements for {job_type}: {requirements}")
            
            return job_type
        except Exception as e:
            logger.error(f"Error in update_job_type_info: {e}")
            return ""
            
    def on_material_name_changed(self, row, material_name):
        """هنگام تغییر نام ماده"""
        logger.debug(f"Material name at row {row} changed to: {material_name}")

    def on_material_type_changed(self, row, type_name):
        """هنگام تغییر نوع ماده"""
        logger.debug(f"Material type at row {row} changed to: {type_name}")
        
        # می‌توانید تنظیمات پیش‌فرض بر اساس نوع اعمال کنید
        if type_name == "Cement":
            logger.info(f"Row {row}: Cement material selected")

    def on_backload_changed(self, row, backload_value):
        """هنگام تغییر مقدار backload"""
        logger.debug(f"Backload at row {row} changed to: {backload_value}")
        
        # محاسبه inventory با در نظر گرفتن backload
        received_widget = self.materials_table.cellWidget(row, 2)
        consumed_widget = self.materials_table.cellWidget(row, 3)
        
        if received_widget and consumed_widget:
            received = received_widget.value()
            consumed = consumed_widget.value()
            inventory = received - consumed - backload_value
            
            inventory_widget = self.materials_table.cellWidget(row, 5)
            if inventory_widget:
                inventory_widget.setValue(inventory)

    def on_material_unit_changed(self, row, unit_name):
        """هنگام تغییر واحد ماده"""
        logger.debug(f"Material unit at row {row} changed to: {unit_name}")
        
        # می‌توانید تبدیل واحد انجام دهید
        if unit_name == "kg":
            logger.info(f"Row {row}: Using metric units (kg)")
        elif unit_name == "lb":
            logger.info(f"Row {row}: Using imperial units (lb)")
            
    # ============ Data Methods ============
    def set_current_well(self, well_id):
        """تنظیم چاه جاری"""
        self.current_well = well_id
    
    def save_data(self):
        """ذخیره داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for saving")
            return False
        
        try:
            # جمع‌آوری داده‌های جدول مواد سیمان
            materials_data = []
            for row in range(self.materials_table.rowCount()):
                row_data = {}
                
                material_widget = self.materials_table.cellWidget(row, 0)
                if material_widget:
                    row_data['material'] = material_widget.text()
                
                type_widget = self.materials_table.cellWidget(row, 1)
                if type_widget:
                    row_data['type'] = type_widget.currentText()
                
                received_widget = self.materials_table.cellWidget(row, 2)
                if received_widget:
                    row_data['received'] = received_widget.value()
                
                consumed_widget = self.materials_table.cellWidget(row, 3)
                if consumed_widget:
                    row_data['consumed'] = consumed_widget.value()
                
                backload_widget = self.materials_table.cellWidget(row, 4)
                if backload_widget:
                    row_data['backload'] = backload_widget.value()
                
                inventory_widget = self.materials_table.cellWidget(row, 5)
                if inventory_widget:
                    row_data['inventory'] = inventory_widget.value()
                
                unit_widget = self.materials_table.cellWidget(row, 6)
                if unit_widget:
                    row_data['unit'] = unit_widget.currentText()
                
                materials_data.append(row_data)
            
            # محاسبه زمان thickening
            thickening_time = f"{self.thickening_hours.value():02d}:{self.thickening_minutes.value():02d}"
            
            # آماده کردن داده‌های سیمان
            cement_data = {
                'well_id': self.current_well,
                'report_date': self.report_date.date().toPyDate(),
                'report_name': self.report_name.text(),
                'cement_type': self.cement_type.currentText(),
                'job_type': self.job_type.currentText(),
                'materials_json': json.dumps(materials_data, indent=2),
                'slurry_density': self.slurry_density.value(),
                'slurry_yield': self.slurry_yield.value(),
                'mix_water': self.mix_water.value(),
                'thickening_time': thickening_time,
                'compressive_strength': self.compressive_strength.value(),
                'fluid_loss': self.fluid_loss.value(),
                'cement_volume': self.cement_volume.value(),
                'displacement_volume': self.displacement_volume.value(),
                'top_of_cement': self.top_of_cement.value(),
                'bottom_of_cement': self.bottom_of_cement.value(),
                'summary': self.cement_summary.toPlainText()
            }
            
            # ذخیره در دیتابیس
            if self.db_manager:
                result = self.db_manager.save_cement_report(cement_data)
                if result:
                    logger.info(f"Cement report saved with ID: {result}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving cement report: {e}")
            return False
    
    def load_data(self):
        """بارگذاری داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for loading")
            return False
        
        try:
            if self.db_manager:
                # دریافت آخرین داده‌ها برای این چاه
                data = self.db_manager.get_cement_report(self.current_well)
                
                if data:
                    self.load_from_dict(data)
                    logger.info("Cement report loaded successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading cement report: {e}")
            return False
    
    def load_from_dict(self, data: dict):
        """بارگذاری داده‌ها از دیکشنری"""
        try:
            self.report_name.setText(data.get('report_name', ''))
            
            cement_type = data.get('cement_type', '')
            if cement_type:
                index = self.cement_type.findText(cement_type)
                if index >= 0:
                    self.cement_type.setCurrentIndex(index)
            
            job_type = data.get('job_type', '')
            if job_type:
                index = self.job_type.findText(job_type)
                if index >= 0:
                    self.job_type.setCurrentIndex(index)
            
            report_date = data.get('report_date')
            if report_date:
                self.report_date.setDate(report_date)
            
            self.slurry_density.setValue(data.get('slurry_density', 0))
            self.slurry_yield.setValue(data.get('slurry_yield', 0))
            self.mix_water.setValue(data.get('mix_water', 0))
            
            thickening_time = data.get('thickening_time', '00:00')
            if thickening_time:
                parts = thickening_time.split(':')
                if len(parts) == 2:
                    self.thickening_hours.setValue(int(parts[0]))
                    self.thickening_minutes.setValue(int(parts[1]))
            
            self.compressive_strength.setValue(data.get('compressive_strength', 0))
            self.fluid_loss.setValue(data.get('fluid_loss', 0))
            self.cement_volume.setValue(data.get('cement_volume', 0))
            self.displacement_volume.setValue(data.get('displacement_volume', 0))
            self.top_of_cement.setValue(data.get('top_of_cement', 0))
            self.bottom_of_cement.setValue(data.get('bottom_of_cement', 0))
            self.cement_summary.setPlainText(data.get('summary', ''))
            
            # بارگذاری مواد سیمان
            materials_json = data.get('materials_json')
            if materials_json:
                self.materials_table.setRowCount(0)
                materials_data = json.loads(materials_json)
                for material in materials_data:
                    self.add_material_row(
                        material.get('material', ''),
                        material.get('type', ''),
                        material.get('received', 0),
                        material.get('consumed', 0),
                        material.get('backload', 0),
                        material.get('inventory', 0),
                        material.get('unit', 'kg')
                    )
            
        except Exception as e:
            logger.error(f"Error loading from dict: {e}")
    
    def clear_form(self):
        """پاک کردن فرم"""
        self.report_name.clear()
        self.cement_type.setCurrentIndex(0)
        self.job_type.setCurrentIndex(0)
        self.report_date.setDate(QDate.currentDate())
        self.slurry_density.setValue(120.0)
        self.slurry_yield.setValue(1.18)
        self.mix_water.setValue(5.2)
        self.thickening_hours.setValue(4)
        self.thickening_minutes.setValue(30)
        self.compressive_strength.setValue(2500)
        self.fluid_loss.setValue(0)
        self.cement_volume.setValue(0)
        self.displacement_volume.setValue(0)
        self.top_of_cement.setValue(0)
        self.bottom_of_cement.setValue(0)
        
        self.materials_table.setRowCount(0)
        self.add_material_row("Class G Cement", "Cement", 1000, 800, 200, 1000, "sacks")
        self.add_material_row("Silica Flour", "Additive", 500, 300, 200, 500, "kg")
        
        self.cement_summary.clear()

# ==================== CLASS 4: CasingReportTab ====================
class CasingReportTab(QWidget):
    """تب گزارش کیسینگ"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        
        self.current_well = None
        self.current_data = {}
        
        self.init_ui()
        self.setup_connections()
        
        logger.info("CasingReportTab initialized")
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ایجاد اسکرول‌ایریا
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        # ============ Casing Header ============
        header_group = QGroupBox("🔩 Casing Job Information")
        header_layout = QGridLayout()
        
        header_layout.addWidget(QLabel("Report Name:"), 0, 0)
        self.report_name = QLineEdit()
        self.report_name.setPlaceholderText("Enter casing report name...")
        header_layout.addWidget(self.report_name, 0, 1)
        
        header_layout.addWidget(QLabel("Casing Type:"), 0, 2)
        self.casing_type = QComboBox()
        self.casing_type.addItems(["Surface", "Intermediate", "Production", "Liner", "Tieback"])
        header_layout.addWidget(self.casing_type, 0, 3)
        
        header_layout.addWidget(QLabel("Date:"), 1, 0)
        self.report_date = QDateEdit()
        self.report_date.setDate(QDate.currentDate())
        self.report_date.setCalendarPopup(True)
        header_layout.addWidget(self.report_date, 1, 1)
        
        header_group.setLayout(header_layout)
        content_layout.addWidget(header_group)
        
        # ============ Casing String Design ============
        design_group = QGroupBox("📐 Casing String Design")
        design_layout = QVBoxLayout()
        
        # جدول طراحی کیسینگ
        self.casing_table = QTableWidget(0, 10)
        self.casing_table.setHorizontalHeaderLabels([
            "Size (in)", "OD (in)", "ID (in)", "Weight (#)", "Grade", 
            "Connection", "From (m)", "To (m)", "Shoe (m)", "Remarks"
        ])
        self.casing_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.casing_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.casing_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.casing_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        design_layout.addWidget(self.casing_table)
        
        # دکمه‌های کنترل جدول
        casing_btn_layout = QHBoxLayout()
        add_casing_btn = QPushButton("➕ Add Casing")
        add_casing_btn.clicked.connect(self.add_casing_row)
        remove_casing_btn = QPushButton("➖ Remove")
        remove_casing_btn.clicked.connect(self.remove_casing_row)
        
        casing_btn_layout.addWidget(add_casing_btn)
        casing_btn_layout.addWidget(remove_casing_btn)
        casing_btn_layout.addStretch()
        design_layout.addLayout(casing_btn_layout)
        
        design_group.setLayout(design_layout)
        content_layout.addWidget(design_group)
        
        # ============ Casing Properties ============
        props_group = QGroupBox("⚙️ Casing Properties")
        props_layout = QGridLayout()
        
        # Burst Pressure
        props_layout.addWidget(QLabel("Burst Pressure (psi):"), 0, 0)
        self.burst_pressure = QDoubleSpinBox()
        self.burst_pressure.setRange(0, 20000)
        self.burst_pressure.setDecimals(0)
        props_layout.addWidget(self.burst_pressure, 0, 1)
        
        # Collapse Pressure
        props_layout.addWidget(QLabel("Collapse Pressure (psi):"), 0, 2)
        self.collapse_pressure = QDoubleSpinBox()
        self.collapse_pressure.setRange(0, 20000)
        self.collapse_pressure.setDecimals(0)
        props_layout.addWidget(self.collapse_pressure, 0, 3)
        
        # Tensile Strength
        props_layout.addWidget(QLabel("Tensile Strength (klb):"), 1, 0)
        self.tensile_strength = QDoubleSpinBox()
        self.tensile_strength.setRange(0, 5000)
        self.tensile_strength.setDecimals(0)
        props_layout.addWidget(self.tensile_strength, 1, 1)
        
        # Make-up Torque
        props_layout.addWidget(QLabel("Make-up Torque (lb-ft):"), 1, 2)
        self.makeup_torque = QDoubleSpinBox()
        self.makeup_torque.setRange(0, 50000)
        self.makeup_torque.setDecimals(0)
        props_layout.addWidget(self.makeup_torque, 1, 3)
        
        # Drift Diameter
        props_layout.addWidget(QLabel("Drift Diameter (in):"), 2, 0)
        self.drift_diameter = QDoubleSpinBox()
        self.drift_diameter.setRange(0, 100)
        self.drift_diameter.setDecimals(3)
        props_layout.addWidget(self.drift_diameter, 2, 1)
        
        # Internal Yield
        props_layout.addWidget(QLabel("Internal Yield (psi):"), 2, 2)
        self.internal_yield = QDoubleSpinBox()
        self.internal_yield.setRange(0, 20000)
        self.internal_yield.setDecimals(0)
        props_layout.addWidget(self.internal_yield, 2, 3)
        
        props_group.setLayout(props_layout)
        content_layout.addWidget(props_group)
        
        # ============ Running Parameters ============
        running_group = QGroupBox("🏃 Running Parameters")
        running_layout = QGridLayout()
        
        # Running Speed
        running_layout.addWidget(QLabel("Running Speed (joints/hr):"), 0, 0)
        self.running_speed = QDoubleSpinBox()
        self.running_speed.setRange(0, 50)
        self.running_speed.setDecimals(1)
        running_layout.addWidget(self.running_speed, 0, 1)
        
        # Fill-up Frequency
        running_layout.addWidget(QLabel("Fill-up Frequency (joints):"), 0, 2)
        self.fillup_frequency = QSpinBox()
        self.fillup_frequency.setRange(0, 100)
        running_layout.addWidget(self.fillup_frequency, 0, 3)
        
        # Centralizer Spacing
        running_layout.addWidget(QLabel("Centralizer Spacing (m):"), 1, 0)
        self.centralizer_spacing = QDoubleSpinBox()
        self.centralizer_spacing.setRange(0, 100)
        self.centralizer_spacing.setDecimals(1)
        running_layout.addWidget(self.centralizer_spacing, 1, 1)
        
        # Scratcher Spacing
        running_layout.addWidget(QLabel("Scratcher Spacing (m):"), 1, 2)
        self.scratcher_spacing = QDoubleSpinBox()
        self.scratcher_spacing.setRange(0, 100)
        self.scratcher_spacing.setDecimals(1)
        running_layout.addWidget(self.scratcher_spacing, 1, 3)
        
        running_group.setLayout(running_layout)
        content_layout.addWidget(running_group)
        
        # ============ Casing Summary ============
        summary_group = QGroupBox("📝 Casing Job Summary")
        summary_layout = QVBoxLayout()
        
        self.casing_summary = QTextEdit()
        self.casing_summary.setMaximumHeight(150)
        self.casing_summary.setPlaceholderText("Enter casing job summary...")
        summary_layout.addWidget(self.casing_summary)
        
        summary_group.setLayout(summary_layout)
        content_layout.addWidget(summary_group)
        
        # ============ Action Buttons ============
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_data)
        self.load_btn = QPushButton("📂 Load")
        self.load_btn.clicked.connect(self.load_data)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addStretch()
        
        content_layout.addLayout(btn_layout)
        content_layout.addStretch()
        
        # تنظیم اسکرول
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # اضافه کردن ردیف‌های نمونه
        self.add_casing_row(13.375, 14.375, 12.415, 61, "P-110", "Premium", 0, 100, 100, "Surface")
        self.add_casing_row(9.625, 10.625, 8.835, 47, "L-80", "BTC", 100, 500, 500, "Intermediate")
    
    def setup_connections(self):
        """اتصال سیگنال‌ها برای تب گزارش کیسینگ"""
        # اتصال تغییرات فشارها - اصلاح نام توابع
        self.burst_pressure.valueChanged.connect(self.update_pressure_info)
        self.collapse_pressure.valueChanged.connect(self.update_pressure_info)
        self.internal_yield.valueChanged.connect(self.update_pressure_info)
        
        # اتصال تغییرات tensile strength
        self.tensile_strength.valueChanged.connect(self.update_strength_info)
        
        # اتصال تغییرات torque
        self.makeup_torque.valueChanged.connect(self.update_torque_info)
        
        # اتصال تغییرات drift diameter
        self.drift_diameter.valueChanged.connect(self.update_drift_info)
        
        # اتصال تغییرات running parameters
        self.running_speed.valueChanged.connect(self.update_running_info)
        self.fillup_frequency.valueChanged.connect(self.update_fillup_info)
        self.centralizer_spacing.valueChanged.connect(self.update_centralizer_info)
        self.scratcher_spacing.valueChanged.connect(self.update_scratcher_info)
        
        # اتصال تغییرات نوع کیسینگ
        self.casing_type.currentTextChanged.connect(self.update_casing_type_info)
    
        
        for row in range(self.casing_table.rowCount()):
            connection_widget = self.casing_table.cellWidget(row, 5)
            if connection_widget:
                connection_widget.currentTextChanged.connect(
                    lambda text, r=row: self.update_connection_requirements(r, text)
                )
        
    # ============ Casing Table Methods ============
    def add_casing_row(self, size=0, od=0, id_size=0, weight=0, grade="", 
                      connection="", from_depth=0, to_depth=0, shoe=0, remarks=""):
        """اضافه کردن ردیف به جدول کیسینگ"""
        row = self.casing_table.rowCount()
        self.casing_table.insertRow(row)
        
        # Size
        size_spin = QDoubleSpinBox()
        size_spin.setRange(0, 100)
        size_spin.setValue(size)
        size_spin.setDecimals(3)
        size_spin.valueChanged.connect(self.update_casing_string_calculations)
        self.casing_table.setCellWidget(row, 0, size_spin)
        
        # OD
        od_spin = QDoubleSpinBox()
        od_spin.setRange(0, 100)
        od_spin.setValue(od)
        od_spin.setDecimals(3)
        od_spin.valueChanged.connect(self.update_casing_string_calculations)
        self.casing_table.setCellWidget(row, 1, od_spin)
        
        # ID
        id_spin = QDoubleSpinBox()
        id_spin.setRange(0, 100)
        id_spin.setValue(id_size)
        id_spin.setDecimals(3)
        id_spin.valueChanged.connect(self.update_casing_string_calculations)
        self.casing_table.setCellWidget(row, 2, id_spin)
        
        # Weight
        weight_spin = QDoubleSpinBox()
        weight_spin.setRange(0, 1000)
        weight_spin.setValue(weight)
        weight_spin.setDecimals(1)
        weight_spin.valueChanged.connect(self.update_casing_string_calculations)
        self.casing_table.setCellWidget(row, 3, weight_spin)
        
        # Grade
        grade_combo = QComboBox()
        grade_items = ["H-40", "J-55", "K-55", "N-80", "L-80", 
                      "C-90", "C-95", "P-110", "Q-125", "V-150"]
        grade_combo.addItems(grade_items)
        
        if grade and grade in grade_items:
            index = grade_combo.findText(grade)
            if index >= 0:
                grade_combo.setCurrentIndex(index)
        else:
            grade_combo.setCurrentIndex(0)
        
        # اتصال تغییرات grade
        grade_combo.currentTextChanged.connect(
            lambda text, r=row: self.on_grade_changed(r, text)
        )
        self.casing_table.setCellWidget(row, 4, grade_combo)
        
        # Connection
        connection_combo = QComboBox()
        connection_items = ["BTC", "LTC", "STC", "Premium", "Integral", 
                           "Buttress", "Extreme Line", "Other"]
        connection_combo.addItems(connection_items)
        
        if connection and connection in connection_items:
            index = connection_combo.findText(connection)
            if index >= 0:
                connection_combo.setCurrentIndex(index)
        else:
            connection_combo.setCurrentIndex(0)
        
        # اتصال تغییرات connection
        connection_combo.currentTextChanged.connect(
            lambda text, r=row: self.on_connection_type_changed(r, text)
        )
        self.casing_table.setCellWidget(row, 5, connection_combo)
        
        # From
        from_spin = QDoubleSpinBox()
        from_spin.setRange(0, 20000)
        from_spin.setValue(from_depth)
        from_spin.setDecimals(2)
        from_spin.valueChanged.connect(self.update_casing_string_calculations)
        self.casing_table.setCellWidget(row, 6, from_spin)
        
        # To
        to_spin = QDoubleSpinBox()
        to_spin.setRange(0, 20000)
        to_spin.setValue(to_depth)
        to_spin.setDecimals(2)
        to_spin.valueChanged.connect(self.update_casing_string_calculations)
        self.casing_table.setCellWidget(row, 7, to_spin)
        
        # Shoe
        shoe_spin = QDoubleSpinBox()
        shoe_spin.setRange(0, 20000)
        shoe_spin.setValue(shoe)
        shoe_spin.setDecimals(2)
        shoe_spin.valueChanged.connect(lambda value, r=row: self.on_shoe_depth_changed(r, value))
        self.casing_table.setCellWidget(row, 8, shoe_spin)
        
        # Remarks
        remarks_edit = QLineEdit(remarks)
        remarks_edit.textChanged.connect(lambda text, r=row: self.on_remarks_changed(r, text))
        self.casing_table.setCellWidget(row, 9, remarks_edit)
    
    def remove_casing_row(self):
        """حذف ردیف انتخاب شده از جدول کیسینگ"""
        current_row = self.casing_table.currentRow()
        if current_row >= 0:
            self.casing_table.removeRow(current_row)
    
    def update_pressure_info(self):
        """به‌روزرسانی اطلاعات فشار"""
        try:
            burst = self.burst_pressure.value()
            collapse = self.collapse_pressure.value()
            internal_yield = self.internal_yield.value()
            
            # محاسبه نسبت فشارها
            if burst > 0 and collapse > 0:
                burst_collapse_ratio = burst / collapse
                logger.debug(f"Pressure info - Burst: {burst}, Collapse: {collapse}, Ratio: {burst_collapse_ratio:.2f}")
            
            # بررسی محدوده‌های ایمنی
            if burst < 2000:
                logger.warning(f"Low burst pressure: {burst} psi")
            if collapse < 1500:
                logger.warning(f"Low collapse pressure: {collapse} psi")
            
            return burst, collapse, internal_yield
        except Exception as e:
            logger.error(f"Error in update_pressure_info: {e}")
            return 0, 0, 0

    def update_strength_info(self):
        """به‌روزرسانی اطلاعات مقاومت کششی"""
        try:
            tensile_strength = self.tensile_strength.value()
            
            # تبدیل به واحدهای مختلف
            tensile_kn = tensile_strength * 4.44822  # تبدیل klb به kN
            
            logger.debug(f"Tensile strength: {tensile_strength} klb ({tensile_kn:.0f} kN)")
            
            # بررسی حداقل مقاومت
            if tensile_strength < 500:
                logger.warning(f"Low tensile strength: {tensile_strength} klb")
            
            return tensile_strength
        except Exception as e:
            logger.error(f"Error in update_strength_info: {e}")
            return 0

    def update_torque_info(self):
        """به‌روزرسانی اطلاعات گشتاور"""
        try:
            makeup_torque = self.makeup_torque.value()
            
            # تبدیل به واحدهای مختلف
            torque_nm = makeup_torque * 1.35582  # تبدیل lb-ft به N-m
            
            logger.debug(f"Make-up torque: {makeup_torque} lb-ft ({torque_nm:.0f} N-m)")
            
            # بررسی محدوده مناسب
            if makeup_torque < 1000:
                logger.warning(f"Low make-up torque: {makeup_torque} lb-ft")
            elif makeup_torque > 30000:
                logger.info(f"High make-up torque: {makeup_torque} lb-ft")
            
            return makeup_torque
        except Exception as e:
            logger.error(f"Error in update_torque_info: {e}")
            return 0

    def update_drift_info(self):
        """به‌روزرسانی اطلاعات drift diameter"""
        try:
            drift_diameter = self.drift_diameter.value()
            
            # بررسی نسبت drift به ID
            # اگر ID در جدول موجود باشد، می‌توانید محاسبه کنید
            drift_ratio = 0
            if hasattr(self, 'casing_table') and self.casing_table.rowCount() > 0:
                # به عنوان مثال، از اولین ردیف جدول استفاده کنید
                id_widget = self.casing_table.cellWidget(0, 2)
                if id_widget:
                    id_value = id_widget.value()
                    if id_value > 0:
                        drift_ratio = (drift_diameter / id_value) * 100
                        logger.debug(f"Drift diameter: {drift_diameter} in, ID: {id_value} in, Ratio: {drift_ratio:.1f}%")
            
            # حداقل drift معمول
            if drift_diameter < 2.0:
                logger.warning(f"Small drift diameter: {drift_diameter} in")
            
            return drift_diameter
        except Exception as e:
            logger.error(f"Error in update_drift_info: {e}")
            return 0

    def update_running_info(self):
        """به‌روزرسانی اطلاعات Running"""
        try:
            running_speed = self.running_speed.value()
            
            # محاسبه زمان تخمینی
            # اگر تعداد مفاصل مشخص باشد
            if hasattr(self, 'casing_table'):
                joint_count = self.casing_table.rowCount()
                if joint_count > 0 and running_speed > 0:
                    estimated_time = joint_count / running_speed  # ساعت
                    logger.debug(f"Running speed: {running_speed} joints/hr, Estimated time: {estimated_time:.1f} hours")
            
            # بررسی محدوده مناسب
            if running_speed > 30:
                logger.warning(f"High running speed: {running_speed} joints/hr")
            elif running_speed < 5:
                logger.info(f"Slow running speed: {running_speed} joints/hr")
            
            return running_speed
        except Exception as e:
            logger.error(f"Error in update_running_info: {e}")
            return 0

    def update_fillup_info(self):
        """به‌روزرسانی اطلاعات Fill-up"""
        try:
            fillup_frequency = self.fillup_frequency.value()
            
            # محاسبه فواصل fill-up
            if fillup_frequency > 0:
                logger.debug(f"Fill-up frequency: every {fillup_frequency} joints")
            
            # بررسی محدوده مناسب
            if fillup_frequency > 30:
                logger.warning(f"Infrequent fill-up: every {fillup_frequency} joints")
            elif fillup_frequency < 5:
                logger.info(f"Frequent fill-up: every {fillup_frequency} joints")
            
            return fillup_frequency
        except Exception as e:
            logger.error(f"Error in update_fillup_info: {e}")
            return 0

    def update_centralizer_info(self):
        """به‌روزرسانی اطلاعات Centralizer"""
        try:
            centralizer_spacing = self.centralizer_spacing.value()
            
            # محاسبه تعداد centralizer مورد نیاز
            # اگر طول کیسینگ مشخص باشد
            if hasattr(self, 'casing_table') and self.casing_table.rowCount() > 0:
                total_length = 0
                for row in range(self.casing_table.rowCount()):
                    from_widget = self.casing_table.cellWidget(row, 6)
                    to_widget = self.casing_table.cellWidget(row, 7)
                    if from_widget and to_widget:
                        length = to_widget.value() - from_widget.value()
                        total_length += length
                
                if total_length > 0 and centralizer_spacing > 0:
                    centralizer_count = total_length / centralizer_spacing
                    logger.debug(f"Centralizer spacing: {centralizer_spacing} m, Required: {centralizer_count:.0f} pcs")
            
            return centralizer_spacing
        except Exception as e:
            logger.error(f"Error in update_centralizer_info: {e}")
            return 0

    def update_scratcher_info(self):
        """به‌روزرسانی اطلاعات Scratcher"""
        try:
            scratcher_spacing = self.scratcher_spacing.value()
            
            # مشابه centralizer، محاسبه تعداد scratcher
            if hasattr(self, 'casing_table') and self.casing_table.rowCount() > 0:
                total_length = 0
                for row in range(self.casing_table.rowCount()):
                    from_widget = self.casing_table.cellWidget(row, 6)
                    to_widget = self.casing_table.cellWidget(row, 7)
                    if from_widget and to_widget:
                        length = to_widget.value() - from_widget.value()
                        total_length += length
                
                if total_length > 0 and scratcher_spacing > 0:
                    scratcher_count = total_length / scratcher_spacing
                    logger.debug(f"Scratcher spacing: {scratcher_spacing} m, Required: {scratcher_count:.0f} pcs")
            
            return scratcher_spacing
        except Exception as e:
            logger.error(f"Error in update_scratcher_info: {e}")
            return 0

    def update_casing_type_info(self, casing_type):
        """به‌روزرسانی اطلاعات نوع کیسینگ"""
        try:
            logger.info(f"Casing type changed to: {casing_type}")
            
            # تنظیمات پیش‌فرض بر اساس نوع کیسینگ
            defaults = {
                "Surface": {
                    "burst_pressure": 1500,
                    "collapse_pressure": 1200,
                    "tensile_strength": 800,
                    "makeup_torque": 15000
                },
                "Intermediate": {
                    "burst_pressure": 5000,
                    "collapse_pressure": 4000,
                    "tensile_strength": 1500,
                    "makeup_torque": 25000
                },
                "Production": {
                    "burst_pressure": 7000,
                    "collapse_pressure": 6000,
                    "tensile_strength": 2000,
                    "makeup_torque": 30000
                },
                "Liner": {
                    "burst_pressure": 6000,
                    "collapse_pressure": 5000,
                    "tensile_strength": 1800,
                    "makeup_torque": 20000
                },
                "Tieback": {
                    "burst_pressure": 4000,
                    "collapse_pressure": 3500,
                    "tensile_strength": 1200,
                    "makeup_torque": 18000
                }
            }
            
            if casing_type in defaults:
                default_values = defaults[casing_type]
                logger.info(f"Default values for {casing_type}: {default_values}")
            
            return casing_type
        except Exception as e:
            logger.error(f"Error in update_casing_type_info: {e}")
            return ""
    
    def update_casing_string_calculations(self):
        """به‌روزرسانی محاسبات رشته کیسینگ"""
        try:
            if not hasattr(self, 'casing_table'):
                return
            
            total_length = 0
            total_weight = 0
            
            for row in range(self.casing_table.rowCount()):
                # محاسبه طول هر بخش
                from_widget = self.casing_table.cellWidget(row, 6)
                to_widget = self.casing_table.cellWidget(row, 7)
                weight_widget = self.casing_table.cellWidget(row, 3)
                
                if from_widget and to_widget and weight_widget:
                    from_depth = from_widget.value()
                    to_depth = to_widget.value()
                    weight = weight_widget.value()
                    
                    if to_depth > from_depth:
                        length = to_depth - from_depth
                        total_length += length
                        
                        # وزن بر حسب lb/ft به کل وزن تبدیل شود
                        total_weight += weight * length * 3.28084  # تبدیل متر به فوت
            
            logger.debug(f"Casing string - Total length: {total_length:.1f} m, Total weight: {total_weight:.0f} lb")
            
            return total_length, total_weight
        except Exception as e:
            logger.error(f"Error in update_casing_string_calculations: {e}")
            return 0, 0

    def on_connection_type_changed(self, row, connection_type):
        """هنگام تغییر نوع اتصال در جدول"""
        try:
            logger.debug(f"Row {row}: Connection type changed to: {connection_type}")
            
            # تنظیمات گشتاور بر اساس نوع اتصال
            torque_values = {
                "BTC": {"min": 5000, "max": 15000},
                "LTC": {"min": 8000, "max": 20000},
                "STC": {"min": 6000, "max": 18000},
                "Premium": {"min": 12000, "max": 30000},
                "Integral": {"min": 15000, "max": 35000},
                "Buttress": {"min": 10000, "max": 25000},
                "Extreme Line": {"min": 20000, "max": 40000},
                "Other": {"min": 0, "max": 0}
            }
            
            if connection_type in torque_values:
                torque_range = torque_values[connection_type]
                logger.info(f"Row {row}: {connection_type} torque range: {torque_range['min']}-{torque_range['max']} lb-ft")
            
            return connection_type
        except Exception as e:
            logger.error(f"Error in on_connection_type_changed: {e}")
            return ""    
    
    def on_grade_changed(self, row, grade):
        """هنگام تغییر گرید کیسینگ"""
        try:
            logger.debug(f"Row {row}: Grade changed to: {grade}")
            
            # تنظیمات پیش‌فرض بر اساس گرید
            grade_properties = {
                "H-40": {"yield_strength": 40000, "color": "Green"},
                "J-55": {"yield_strength": 55000, "color": "Blue"},
                "K-55": {"yield_strength": 55000, "color": "Blue"},
                "N-80": {"yield_strength": 80000, "color": "Red"},
                "L-80": {"yield_strength": 80000, "color": "Red"},
                "C-90": {"yield_strength": 90000, "color": "Purple"},
                "C-95": {"yield_strength": 95000, "color": "Purple"},
                "P-110": {"yield_strength": 110000, "color": "Brown"},
                "Q-125": {"yield_strength": 125000, "color": "Black"},
                "V-150": {"yield_strength": 150000, "color": "Gold"}
            }
            
            if grade in grade_properties:
                properties = grade_properties[grade]
                logger.info(f"Row {row}: {grade} properties - Yield: {properties['yield_strength']} psi")
            
            return grade
        except Exception as e:
            logger.error(f"Error in on_grade_changed: {e}")
            return ""

    def on_shoe_depth_changed(self, row, shoe_depth):
        """هنگام تغییر عمق شو"""
        try:
            logger.debug(f"Row {row}: Shoe depth changed to: {shoe_depth}")
            
            # بررسی اینکه shoe depth بین from و to باشد
            from_widget = self.casing_table.cellWidget(row, 6)
            to_widget = self.casing_table.cellWidget(row, 7)
            
            if from_widget and to_widget:
                from_depth = from_widget.value()
                to_depth = to_widget.value()
                
                if shoe_depth < from_depth or shoe_depth > to_depth:
                    logger.warning(f"Row {row}: Shoe depth {shoe_depth} is outside casing interval {from_depth}-{to_depth}")
            
            return shoe_depth
        except Exception as e:
            logger.error(f"Error in on_shoe_depth_changed: {e}")
            return 0

    def on_remarks_changed(self, row, remarks):
        """هنگام تغییر remarks"""
        logger.debug(f"Row {row}: Remarks changed to: {remarks}")
        return remarks
    # ============ Data Methods ============
    def set_current_well(self, well_id):
        """تنظیم چاه جاری"""
        self.current_well = well_id
    
    def save_data(self):
        """ذخیره داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for saving")
            return False
        
        try:
            # جمع‌آوری داده‌های جدول کیسینگ
            casing_data = []
            for row in range(self.casing_table.rowCount()):
                row_data = {}
                
                size_widget = self.casing_table.cellWidget(row, 0)
                if size_widget:
                    row_data['size'] = size_widget.value()
                
                od_widget = self.casing_table.cellWidget(row, 1)
                if od_widget:
                    row_data['od'] = od_widget.value()
                
                id_widget = self.casing_table.cellWidget(row, 2)
                if id_widget:
                    row_data['id'] = id_widget.value()
                
                weight_widget = self.casing_table.cellWidget(row, 3)
                if weight_widget:
                    row_data['weight'] = weight_widget.value()
                
                grade_widget = self.casing_table.cellWidget(row, 4)
                if grade_widget:
                    row_data['grade'] = grade_widget.currentText()
                
                connection_widget = self.casing_table.cellWidget(row, 5)
                if connection_widget:
                    row_data['connection'] = connection_widget.currentText()
                
                from_widget = self.casing_table.cellWidget(row, 6)
                if from_widget:
                    row_data['from'] = from_widget.value()
                
                to_widget = self.casing_table.cellWidget(row, 7)
                if to_widget:
                    row_data['to'] = to_widget.value()
                
                shoe_widget = self.casing_table.cellWidget(row, 8)
                if shoe_widget:
                    row_data['shoe'] = shoe_widget.value()
                
                remarks_widget = self.casing_table.cellWidget(row, 9)
                if remarks_widget:
                    row_data['remarks'] = remarks_widget.text()
                
                casing_data.append(row_data)
            
            # آماده کردن داده‌های کیسینگ
            casing_report_data = {
                'well_id': self.current_well,
                'report_date': self.report_date.date().toPyDate(),
                'report_name': self.report_name.text(),
                'casing_type': self.casing_type.currentText(),
                'casing_json': json.dumps(casing_data, indent=2),
                'burst_pressure': self.burst_pressure.value(),
                'collapse_pressure': self.collapse_pressure.value(),
                'tensile_strength': self.tensile_strength.value(),
                'makeup_torque': self.makeup_torque.value(),
                'drift_diameter': self.drift_diameter.value(),
                'internal_yield': self.internal_yield.value(),
                'running_speed': self.running_speed.value(),
                'fillup_frequency': self.fillup_frequency.value(),
                'centralizer_spacing': self.centralizer_spacing.value(),
                'scratcher_spacing': self.scratcher_spacing.value(),
                'summary': self.casing_summary.toPlainText()
            }
            
            # ذخیره در دیتابیس
            if self.db_manager:
                result = self.db_manager.save_casing_report(casing_report_data)
                if result:
                    logger.info(f"Casing report saved with ID: {result}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving casing report: {e}")
            return False
    
    def load_data(self):
        """بارگذاری داده‌ها"""
        if not self.current_well:
            logger.warning("No well selected for loading")
            return False
        
        try:
            if self.db_manager:
                # دریافت آخرین داده‌ها برای این چاه
                data = self.db_manager.get_casing_report(self.current_well)
                
                if data:
                    self.load_from_dict(data)
                    logger.info("Casing report loaded successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading casing report: {e}")
            return False
    
    def load_from_dict(self, data: dict):
        """بارگذاری داده‌ها از دیکشنری"""
        try:
            self.report_name.setText(data.get('report_name', ''))
            
            casing_type = data.get('casing_type', '')
            if casing_type:
                index = self.casing_type.findText(casing_type)
                if index >= 0:
                    self.casing_type.setCurrentIndex(index)
            
            report_date = data.get('report_date')
            if report_date:
                self.report_date.setDate(report_date)
            
            self.burst_pressure.setValue(data.get('burst_pressure', 0))
            self.collapse_pressure.setValue(data.get('collapse_pressure', 0))
            self.tensile_strength.setValue(data.get('tensile_strength', 0))
            self.makeup_torque.setValue(data.get('makeup_torque', 0))
            self.drift_diameter.setValue(data.get('drift_diameter', 0))
            self.internal_yield.setValue(data.get('internal_yield', 0))
            self.running_speed.setValue(data.get('running_speed', 0))
            self.fillup_frequency.setValue(data.get('fillup_frequency', 0))
            self.centralizer_spacing.setValue(data.get('centralizer_spacing', 0))
            self.scratcher_spacing.setValue(data.get('scratcher_spacing', 0))
            self.casing_summary.setPlainText(data.get('summary', ''))
            
            # بارگذاری داده‌های کیسینگ
            casing_json = data.get('casing_json')
            if casing_json:
                self.casing_table.setRowCount(0)
                casing_data = json.loads(casing_json)
                for casing in casing_data:
                    self.add_casing_row(
                        casing.get('size', 0),
                        casing.get('od', 0),
                        casing.get('id', 0),
                        casing.get('weight', 0),
                        casing.get('grade', ''),
                        casing.get('connection', ''),
                        casing.get('from', 0),
                        casing.get('to', 0),
                        casing.get('shoe', 0),
                        casing.get('remarks', '')
                    )
            
        except Exception as e:
            logger.error(f"Error loading from dict: {e}")
    
    def clear_form(self):
        """پاک کردن فرم"""
        self.report_name.clear()
        self.casing_type.setCurrentIndex(0)
        self.report_date.setDate(QDate.currentDate())
        self.burst_pressure.setValue(0)
        self.collapse_pressure.setValue(0)
        self.tensile_strength.setValue(0)
        self.makeup_torque.setValue(0)
        self.drift_diameter.setValue(0)
        self.internal_yield.setValue(0)
        self.running_speed.setValue(0)
        self.fillup_frequency.setValue(0)
        self.centralizer_spacing.setValue(0)
        self.scratcher_spacing.setValue(0)
        
        self.casing_table.setRowCount(0)
        self.add_casing_row(13.375, 14.375, 12.415, 61, "P-110", "Premium", 0, 100, 100, "Surface")
        
        self.casing_summary.clear()

# ------------------------ Casing Tally Widget ------------------------
class CasingTallyWidget(QWidget):
    """ویجت کامل Casing Tally شامل تمام بخش‌ها"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_well = None
        
        self.stats_labels = {}
        
        self.init_ui()
        self.setup_connections()
        
        logger.info("CasingTallyWidget initialized")
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری کامل"""
        main_layout = QVBoxLayout(self)
        
        # ============ نوار ابزار ============
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        
        # دکمه‌های اصلی
        save_btn = QAction("💾 Save Tally", self)
        save_btn.triggered.connect(self.save_tally_report)
        toolbar.addAction(save_btn)
        
        load_btn = QAction("📂 Load Tally", self)
        load_btn.triggered.connect(self.load_tally_report)
        toolbar.addAction(load_btn)
        
        export_btn = QAction("📤 Export Tally", self)
        export_btn.triggered.connect(self.export_tally_data)
        toolbar.addAction(export_btn)
        
        import_btn = QAction("📥 Import Tally", self)
        import_btn.triggered.connect(self.import_tally_data)
        toolbar.addAction(import_btn)
        
        calculate_btn = QAction("🔄 Calculate All", self)
        calculate_btn.triggered.connect(self.calculate_all)
        toolbar.addAction(calculate_btn)
        
        toolbar.addSeparator()
        
        # نشانگر چاه جاری
        self.current_well_label = QLabel("No well selected")
        toolbar.addWidget(self.current_well_label)
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        main_layout.addWidget(toolbar)
        
        # ============ تب‌های اصلی ============
        self.tab_widget = QTabWidget()
        
        # تب 1: Casing Specifications
        specs_tab = self.create_specifications_tab()
        self.tab_widget.addTab(specs_tab, "🔧 Specifications")
        
        # تب 2: Tally Details
        tally_tab = self.create_tally_details_tab()
        self.tab_widget.addTab(tally_tab, "📊 Tally Details")
        
        # تب 3: Summary Report
        summary_tab = self.create_summary_tab()
        self.tab_widget.addTab(summary_tab, "📝 Summary")
        
        main_layout.addWidget(self.tab_widget)
        
        # ============ نوار وضعیت ============
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        main_layout.addWidget(self.status_bar)
    
    def create_specifications_tab(self):
        """ایجاد تب مشخصات کیسینگ"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # هدر
        header_label = QLabel("Casing Specifications")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(header_label)
        
        # اسکرول برای محتوای طولانی
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 1. جدول مشخصات
        specs_group = QGroupBox("Casing Specifications")
        specs_layout = QVBoxLayout()
        
        self.specs_table = QTableWidget(0, 12)
        self.specs_table.setHorizontalHeaderLabels([
            "Size (in)", "ID (in)", "Weight (lb/ft)", "Drift ID (in)", 
            "Make Up Torque (lb-ft)", "Burst (psi)", "Collapse (psi)", 
            "Tensile (lbs)", "Coupling", "Nominal OD (in)", "Grade", "Connection"
        ])
        self.specs_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.specs_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.specs_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        # تنظیم عرض ستون‌ها
        column_widths = [80, 80, 100, 100, 120, 100, 100, 100, 100, 100, 80, 120]
        for i, width in enumerate(column_widths):
            self.specs_table.setColumnWidth(i, width)
        
        self.specs_table.setAlternatingRowColors(True)
        specs_layout.addWidget(self.specs_table)
        
        # دکمه‌های کنترل جدول
        specs_btn_layout = QHBoxLayout()
        add_spec_btn = QPushButton("➕ Add Specification")
        remove_spec_btn = QPushButton("➖ Remove Selected")
        import_specs_btn = QPushButton("📥 Import Specs")
        export_specs_btn = QPushButton("📤 Export Specs")
        
        add_spec_btn.clicked.connect(self.add_specification_row)
        remove_spec_btn.clicked.connect(self.remove_specification_row)
        import_specs_btn.clicked.connect(self.import_specifications)
        export_specs_btn.clicked.connect(self.export_specifications)
        
        specs_btn_layout.addWidget(add_spec_btn)
        specs_btn_layout.addWidget(remove_spec_btn)
        specs_btn_layout.addWidget(import_specs_btn)
        specs_btn_layout.addWidget(export_specs_btn)
        specs_btn_layout.addStretch()
        
        specs_layout.addLayout(specs_btn_layout)
        specs_group.setLayout(specs_layout)
        content_layout.addWidget(specs_group)
        
        # 2. پارامترهای محاسباتی
        params_group = QGroupBox("Calculation Parameters")
        params_layout = QGridLayout()
        
        # RT Depth
        params_layout.addWidget(QLabel("RT Depth (m):"), 0, 0)
        self.rt_depth = QDoubleSpinBox()
        self.rt_depth.setRange(0, 20000)
        self.rt_depth.setValue(3000)
        self.rt_depth.setSuffix(" m")
        params_layout.addWidget(self.rt_depth, 0, 1)
        
        # Mud Weight
        params_layout.addWidget(QLabel("Mud Weight (pcf):"), 0, 2)
        self.mud_weight = QDoubleSpinBox()
        self.mud_weight.setRange(0, 200)
        self.mud_weight.setValue(65)
        self.mud_weight.setSuffix(" pcf")
        params_layout.addWidget(self.mud_weight, 0, 3)
        
        # Steel Density
        params_layout.addWidget(QLabel("Steel Density (lb/ft³):"), 1, 0)
        self.steel_density = QDoubleSpinBox()
        self.steel_density.setRange(0, 500)
        self.steel_density.setValue(490)
        self.steel_density.setSuffix(" lb/ft³")
        params_layout.addWidget(self.steel_density, 1, 1)
        
        # Buoyancy Factor
        params_layout.addWidget(QLabel("Buoyancy Factor:"), 1, 2)
        self.buoyancy_factor = QDoubleSpinBox()
        self.buoyancy_factor.setReadOnly(True)
        self.buoyancy_factor.setRange(0, 1)
        self.buoyancy_factor.setDecimals(3)
        params_layout.addWidget(self.buoyancy_factor, 1, 3)
        
        params_group.setLayout(params_layout)
        content_layout.addWidget(params_group)
        
        # اضافه کردن ردیف‌های نمونه
        self.add_sample_specifications()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return tab
    
    def create_tally_details_tab(self):
        """ایجاد تب جزئیات Tally"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # هدر
        header_label = QLabel("Casing Tally Details")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(header_label)
        
        # اسکرول
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # جدول Tally Details
        tally_group = QGroupBox("Casing Tally Joint-by-Joint")
        tally_layout = QVBoxLayout()
        
        self.tally_table = QTableWidget(0, 12)
        self.tally_table.setHorizontalHeaderLabels([
            "No.", "Size (in)", "Grade", "Order No.", "Joint Len (m)", 
            "Cum Length (m)", "Dist to RT (m)", "M/D Weight (Klbs)", 
            "String Cap (bbl)", "Centralizers", "IN/OUT", "Remarks"
        ])
        self.tally_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tally_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tally_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        # تنظیم عرض ستون‌ها
        tally_widths = [50, 80, 80, 100, 100, 100, 100, 100, 100, 100, 80, 150]
        for i, width in enumerate(tally_widths):
            self.tally_table.setColumnWidth(i, width)
        
        self.tally_table.setAlternatingRowColors(True)
        tally_layout.addWidget(self.tally_table)
        
        # دکمه‌های کنترل
        tally_btn_layout = QHBoxLayout()
        add_joint_btn = QPushButton("➕ Add Joint")
        remove_joint_btn = QPushButton("➖ Remove Joint")
        clear_all_btn = QPushButton("🗑️ Clear All")
        auto_fill_btn = QPushButton("🔄 Auto Fill")
        
        add_joint_btn.clicked.connect(self.add_tally_row)
        remove_joint_btn.clicked.connect(self.remove_tally_row)
        clear_all_btn.clicked.connect(self.clear_tally_table)
        auto_fill_btn.clicked.connect(self.auto_fill_tally)
        
        tally_btn_layout.addWidget(add_joint_btn)
        tally_btn_layout.addWidget(remove_joint_btn)
        tally_btn_layout.addWidget(clear_all_btn)
        tally_btn_layout.addWidget(auto_fill_btn)
        tally_btn_layout.addStretch()
        
        tally_layout.addLayout(tally_btn_layout)
        tally_group.setLayout(tally_layout)
        content_layout.addWidget(tally_group)
        
        # اضافه کردن ردیف‌های نمونه
        self.add_sample_tally_rows()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return tab
    
    def create_summary_tab(self):
        """ایجاد تب خلاصه گزارش"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # هدر
        header_label = QLabel("Tally Summary Report")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(header_label)
        
        # بخش گزارش
        report_group = QGroupBox("Tally Summary")
        report_layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setMinimumHeight(300)
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("Summary report will be generated here...")
        report_layout.addWidget(self.summary_text)
        
        # دکمه‌های گزارش
        report_btn_layout = QHBoxLayout()
        generate_btn = QPushButton("📊 Generate Summary")
        export_report_btn = QPushButton("📤 Export Report")
        print_btn = QPushButton("🖨️ Print Report")
        
        generate_btn.clicked.connect(self.generate_summary_report)
        export_report_btn.clicked.connect(self.export_summary_report)
        print_btn.clicked.connect(self.print_report)
        
        report_btn_layout.addWidget(generate_btn)
        report_btn_layout.addWidget(export_report_btn)
        report_btn_layout.addWidget(print_btn)
        report_btn_layout.addStretch()
        
        report_layout.addLayout(report_btn_layout)
        report_group.setLayout(report_layout)
        layout.addWidget(report_group)
        
        # بخش آمار
        stats_group = QGroupBox("Quick Statistics")
        stats_layout = QGridLayout()
        
        # آمارهای مختلف
        stats_data = [
            ("Total Joints:", "total_joints"),
            ("Total Length:", "total_length"),
            ("Total Weight:", "total_weight"),
            ("Total Capacity:", "total_capacity"),
            ("IN Joints:", "in_joints"),
            ("OUT Joints:", "out_joints"),
            ("Avg Joint Length:", "avg_length"),
            ("Buoyancy Factor:", "buoyancy_factor")
        ]
        
        # ایجاد و ذخیره labelها
        self.stats_labels = {}
        for i, (label_text, key) in enumerate(stats_data):
            row = i // 2
            col = (i % 2) * 2
            
            # Label نام
            name_label = QLabel(label_text)
            stats_layout.addWidget(name_label, row, col)
            
            # Label مقدار
            value_label = QLabel("0")
            value_label.setStyleSheet("font-weight: bold; color: #0078d4;")
            stats_layout.addWidget(value_label, row, col + 1)
            
            # ذخیره در دیکشنری
            self.stats_labels[key] = value_label
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        return tab
    
    # ============ SETUP CONNECTIONS ============
    def setup_connections(self):
        """اتصال سیگنال‌ها برای ویجت Casing Tally"""
        # اتصال تغییرات پارامترها برای محاسبات
        self.rt_depth.valueChanged.connect(self.calculate_tally)
        self.mud_weight.valueChanged.connect(self.calculate_buoyancy_and_tally)
        self.steel_density.valueChanged.connect(self.calculate_buoyancy_and_tally)
        
        # اتصال تغییرات جدول specifications
        self.specs_table.cellChanged.connect(self.on_specs_table_changed)
        
        # اتصال تغییرات جدول tally
        self.tally_table.cellChanged.connect(self.calculate_tally)
    
    # ============ CORE CALCULATION METHODS ============
    def calculate_buoyancy_and_tally(self):
        """محاسبه buoyancy و سپس tally"""
        self.calculate_buoyancy()
        self.calculate_tally()
    
    def calculate_buoyancy(self):
        """محاسبه ضریب buoyancy"""
        try:
            mud = self.mud_weight.value()
            steel = self.steel_density.value()
            
            if steel > 0:
                buoyancy = 1 - (mud / steel)
                self.buoyancy_factor.setValue(buoyancy)
                
                # به‌روزرسانی آمار
                if "buoyancy_factor" in self.stats_labels:
                    self.stats_labels["buoyancy_factor"].setText(f"{buoyancy:.3f}")
                
                logger.debug(f"Buoyancy factor: {buoyancy:.3f}")
                return buoyancy
            else:
                self.buoyancy_factor.setValue(0)
                return 0
        except Exception as e:
            logger.error(f"Error in calculate_buoyancy: {e}")
            return 0
    
    def calculate_tally(self):
        """محاسبه Tally"""
        try:
            rt_depth = self.rt_depth.value()
            buoyancy = self.buoyancy_factor.value()
            
            cumulative_length = 0.0
            cumulative_weight = 0.0
            cumulative_capacity = 0.0
            
            for row in range(self.tally_table.rowCount()):
                # دریافت مقادیر
                size_combo = self.tally_table.cellWidget(row, 1)
                length_widget = self.tally_table.cellWidget(row, 4)
                inout_combo = self.tally_table.cellWidget(row, 10)
                
                if not all([size_combo, length_widget, inout_combo]):
                    continue
                
                size_text = size_combo.currentText()
                joint_length = length_widget.value()
                in_out = inout_combo.currentText()
                
                # اگر OUT باشد، مقادیر صفر
                if in_out == "OUT":
                    self.tally_table.item(row, 5).setText(f"{cumulative_length:.2f}")
                    self.tally_table.item(row, 6).setText(f"{rt_depth - cumulative_length:.2f}")
                    self.tally_table.item(row, 7).setText(f"{cumulative_weight:.2f}")
                    self.tally_table.item(row, 8).setText(f"{cumulative_capacity:.3f}")
                    continue
                
                # پیدا کردن مشخصات برای این سایز
                weight_ppf = 0.0
                id_inch = 0.0
                
                for spec_row in range(self.specs_table.rowCount()):
                    spec_size = self.specs_table.cellWidget(spec_row, 0).value()
                    if abs(spec_size - float(size_text)) < 0.001:
                        weight_ppf = self.specs_table.cellWidget(spec_row, 2).value()
                        id_inch = self.specs_table.cellWidget(spec_row, 1).value()
                        break
                
                # اگر پیدا نشد، مقادیر پیش‌فرض
                if weight_ppf == 0:
                    weight_ppf = float(size_text) * 4.5
                    id_inch = float(size_text) - 0.5
                
                # محاسبات
                cumulative_length += joint_length
                distance_to_rt = rt_depth - cumulative_length
                
                # وزن
                joint_length_ft = joint_length * 3.28084
                air_weight_lbs = weight_ppf * joint_length_ft
                buoyant_weight_klbs = (air_weight_lbs / 1000.0) * buoyancy
                cumulative_weight += buoyant_weight_klbs
                
                # ظرفیت
                id_ft = id_inch / 12.0
                volume_cu_ft = 3.1416 * (id_ft / 2.0) ** 2 * joint_length_ft
                volume_bbl = volume_cu_ft / 5.615
                cumulative_capacity += volume_bbl
                
                # به‌روزرسانی
                self.tally_table.item(row, 5).setText(f"{cumulative_length:.2f}")
                self.tally_table.item(row, 6).setText(f"{distance_to_rt:.2f}")
                self.tally_table.item(row, 7).setText(f"{cumulative_weight:.2f}")
                self.tally_table.item(row, 8).setText(f"{cumulative_capacity:.3f}")
            
            # به‌روزرسانی آمار
            self.update_statistics()
            
            return True
        except Exception as e:
            logger.error(f"Error calculating tally: {e}")
            return False
    
    def update_statistics(self):
        """به‌روزرسانی آمار"""
        try:
            if not hasattr(self, 'stats_labels') or not self.stats_labels:
                return
            
            total_joints = self.tally_table.rowCount()
            in_joints = 0
            out_joints = 0
            
            for row in range(self.tally_table.rowCount()):
                inout_combo = self.tally_table.cellWidget(row, 10)
                if inout_combo and inout_combo.currentText() == "IN":
                    in_joints += 1
                else:
                    out_joints += 1
            
            total_length = 0
            total_weight = 0
            total_capacity = 0
            
            if self.tally_table.rowCount() > 0:
                last_row = self.tally_table.rowCount() - 1
                item = self.tally_table.item(last_row, 5)
                if item and item.text():
                    total_length = float(item.text())
                
                item = self.tally_table.item(last_row, 7)
                if item and item.text():
                    total_weight = float(item.text())
                
                item = self.tally_table.item(last_row, 8)
                if item and item.text():
                    total_capacity = float(item.text())
            
            avg_length = total_length / in_joints if in_joints > 0 else 0
            
            # به‌روزرسانی labels
            if "total_joints" in self.stats_labels:
                self.stats_labels["total_joints"].setText(str(total_joints))
            
            if "total_length" in self.stats_labels:
                self.stats_labels["total_length"].setText(f"{total_length:.2f} m")
            
            if "total_weight" in self.stats_labels:
                self.stats_labels["total_weight"].setText(f"{total_weight:.2f} Klbs")
            
            if "total_capacity" in self.stats_labels:
                self.stats_labels["total_capacity"].setText(f"{total_capacity:.3f} bbl")
            
            if "in_joints" in self.stats_labels:
                self.stats_labels["in_joints"].setText(str(in_joints))
            
            if "out_joints" in self.stats_labels:
                self.stats_labels["out_joints"].setText(str(out_joints))
            
            if "avg_length" in self.stats_labels:
                self.stats_labels["avg_length"].setText(f"{avg_length:.2f} m")
            
            return True
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            return False
    
    # ============ EVENT HANDLERS ============
    def on_specs_table_changed(self, row, column):
        """هنگام تغییر سلول در جدول specifications"""
        try:
            logger.debug(f"Specs table changed: Row {row}, Column {column}")
            
            # اگر سایز یا ID تغییر کرده، tally را به‌روزرسانی کن
            if column in [0, 1, 2]:  # Size, ID, Weight
                self.calculate_tally()
            
            return row, column
        except Exception as e:
            logger.error(f"Error in on_specs_table_changed: {e}")
            return -1, -1
    
    def on_joint_size_changed(self, row, size):
        """هنگام تغییر سایز مفصل"""
        logger.debug(f"Row {row}: Joint size changed to: {size}")
        self.calculate_tally()
        return size
    
    def on_joint_grade_changed(self, row, grade):
        """هنگام تغییر گرید مفصل"""
        logger.debug(f"Row {row}: Joint grade changed to: {grade}")
        return grade
    
    def on_order_no_changed(self, row, order_no):
        """هنگام تغییر شماره سفارش"""
        logger.debug(f"Row {row}: Order number changed to: {order_no}")
        return order_no
    
    def on_joint_status_changed(self, row, status):
        """هنگام تغییر وضعیت IN/OUT مفصل"""
        logger.debug(f"Row {row}: Joint status changed to: {status}")
        self.calculate_tally()
        return status
    
    def on_centralizer_info_changed(self, row, centralizer_status):
        """هنگام تغییر وضعیت centralizer"""
        logger.debug(f"Row {row}: Centralizer status changed to: {centralizer_status}")
        return centralizer_status
    
    def on_remarks_changed(self, row, remarks):
        """هنگام تغییر remarks"""
        logger.debug(f"Row {row}: Remarks changed to: {remarks}")
        return remarks
    
    # ============ TABLE MANAGEMENT METHODS ============
    def add_sample_specifications(self):
        """اضافه کردن مشخصات نمونه"""
        sample_specs = [
            (13.375, 12.415, 61, 12.347, 22700, 6070, 4810, 1126000, "BTC", 14.375, "P-110", "Premium"),
            (9.625, 8.835, 47, 8.729, 17300, 6070, 7530, 1225000, "BTC", 10.625, "L-80", "Premium"),
            (7.000, 6.276, 29, 6.184, 12500, 6070, 10810, 924000, "BTC", 7.625, "L-80", "VAM"),
            (5.500, 4.778, 20, 4.670, 8900, 6070, 15370, 588000, "BTC", 6.050, "L-80", "Hydril")
        ]
        
        for spec in sample_specs:
            self.add_specification_row(*spec)
    
    def add_specification_row(self, size=13.375, id_size=12.415, weight=61, 
                            drift_id=12.347, torque=22700, burst=6070, 
                            collapse=4810, tensile=1126000, coupling="BTC",
                            nominal_od=14.375, grade="P-110", connection="Premium"):
        """اضافه کردن ردیف مشخصات"""
        row = self.specs_table.rowCount()
        self.specs_table.insertRow(row)
        
        # Size
        size_spin = QDoubleSpinBox()
        size_spin.setRange(0, 100)
        size_spin.setValue(size)
        size_spin.setDecimals(3)
        size_spin.valueChanged.connect(lambda: self.calculate_tally())
        self.specs_table.setCellWidget(row, 0, size_spin)
        
        # ID
        id_spin = QDoubleSpinBox()
        id_spin.setRange(0, 100)
        id_spin.setValue(id_size)
        id_spin.setDecimals(3)
        id_spin.valueChanged.connect(lambda: self.calculate_tally())
        self.specs_table.setCellWidget(row, 1, id_spin)
        
        # Weight
        weight_spin = QDoubleSpinBox()
        weight_spin.setRange(0, 1000)
        weight_spin.setValue(weight)
        weight_spin.setDecimals(2)
        weight_spin.valueChanged.connect(lambda: self.calculate_tally())
        self.specs_table.setCellWidget(row, 2, weight_spin)
        
        # Drift ID
        drift_spin = QDoubleSpinBox()
        drift_spin.setRange(0, 100)
        drift_spin.setValue(drift_id)
        drift_spin.setDecimals(3)
        self.specs_table.setCellWidget(row, 3, drift_spin)
        
        # Torque
        torque_spin = QDoubleSpinBox()
        torque_spin.setRange(0, 100000)
        torque_spin.setValue(torque)
        torque_spin.setDecimals(0)
        self.specs_table.setCellWidget(row, 4, torque_spin)
        
        # Burst
        burst_spin = QDoubleSpinBox()
        burst_spin.setRange(0, 20000)
        burst_spin.setValue(burst)
        burst_spin.setDecimals(0)
        self.specs_table.setCellWidget(row, 5, burst_spin)
        
        # Collapse
        collapse_spin = QDoubleSpinBox()
        collapse_spin.setRange(0, 20000)
        collapse_spin.setValue(collapse)
        collapse_spin.setDecimals(0)
        self.specs_table.setCellWidget(row, 6, collapse_spin)
        
        # Tensile
        tensile_spin = QDoubleSpinBox()
        tensile_spin.setRange(0, 5000000)
        tensile_spin.setValue(tensile)
        tensile_spin.setDecimals(0)
        self.specs_table.setCellWidget(row, 7, tensile_spin)
        
        # Coupling
        coupling_combo = QComboBox()
        coupling_combo.addItems(["BTC", "LTC", "STC", "Premium", "Integral", "Buttress"])
        coupling_combo.setCurrentText(coupling)
        self.specs_table.setCellWidget(row, 8, coupling_combo)
        
        # Nominal OD
        od_spin = QDoubleSpinBox()
        od_spin.setRange(0, 100)
        od_spin.setValue(nominal_od)
        od_spin.setDecimals(3)
        self.specs_table.setCellWidget(row, 9, od_spin)
        
        # Grade
        grade_combo = QComboBox()
        grade_combo.addItems(["H-40", "J-55", "K-55", "N-80", "L-80", "C-90", "C-95", "P-110", "Q-125"])
        grade_combo.setCurrentText(grade)
        self.specs_table.setCellWidget(row, 10, grade_combo)
        
        # Connection
        connection_combo = QComboBox()
        connection_combo.addItems(["VAM", "Hydril", "Grant", "Tenaris", "Premium", "Other"])
        connection_combo.setCurrentText(connection)
        self.specs_table.setCellWidget(row, 11, connection_combo)
    
    def remove_specification_row(self):
        """حذف ردیف مشخصات انتخاب شده"""
        current_row = self.specs_table.currentRow()
        if current_row >= 0:
            self.specs_table.removeRow(current_row)
    
    def add_sample_tally_rows(self):
        """اضافه کردن ردیف‌های نمونه Tally"""
        for i in range(10):
            self.add_tally_row(i + 1)
    
    def add_tally_row(self, joint_no=None):
        """اضافه کردن ردیف Tally"""
        if joint_no is None:
            joint_no = self.tally_table.rowCount() + 1
        
        row = self.tally_table.rowCount()
        self.tally_table.insertRow(row)
        
        # شماره
        no_item = QTableWidgetItem(str(joint_no))
        no_item.setTextAlignment(Qt.AlignCenter)
        self.tally_table.setItem(row, 0, no_item)
        
        # Size
        size_combo = QComboBox()
        size_combo.addItems(["13.375", "9.625", "7.000", "5.500"])
        size_combo.currentTextChanged.connect(
            lambda text, r=row: self.on_joint_size_changed(r, text)
        )
        self.tally_table.setCellWidget(row, 1, size_combo)
        
        # Grade
        grade_combo = QComboBox()
        grade_combo.addItems(["P-110", "L-80", "N-80", "K-55"])
        grade_combo.currentTextChanged.connect(
            lambda text, r=row: self.on_joint_grade_changed(r, text)
        )
        self.tally_table.setCellWidget(row, 2, grade_combo)
        
        # Order No.
        order_edit = QLineEdit(f"ORD-{joint_no:03d}")
        order_edit.textChanged.connect(
            lambda text, r=row: self.on_order_no_changed(r, text)
        )
        self.tally_table.setCellWidget(row, 3, order_edit)
        
        # Joint Length
        length_spin = QDoubleSpinBox()
        length_spin.setRange(0, 50)
        length_spin.setValue(12.0)
        length_spin.setDecimals(2)
        length_spin.valueChanged.connect(self.calculate_tally)
        self.tally_table.setCellWidget(row, 4, length_spin)
        
        # Cumulative Length
        cum_item = QTableWidgetItem("0.00")
        cum_item.setTextAlignment(Qt.AlignCenter)
        self.tally_table.setItem(row, 5, cum_item)
        
        # Distance to RT
        dist_item = QTableWidgetItem("0.00")
        dist_item.setTextAlignment(Qt.AlignCenter)
        self.tally_table.setItem(row, 6, dist_item)
        
        # M/D Weight
        weight_item = QTableWidgetItem("0.00")
        weight_item.setTextAlignment(Qt.AlignCenter)
        self.tally_table.setItem(row, 7, weight_item)
        
        # String Capacity
        cap_item = QTableWidgetItem("0.00")
        cap_item.setTextAlignment(Qt.AlignCenter)
        self.tally_table.setItem(row, 8, cap_item)
        
        # Centralizers
        central_combo = QComboBox()
        central_combo.addItems(["Yes", "No"])
        central_combo.currentTextChanged.connect(
            lambda text, r=row: self.on_centralizer_info_changed(r, text)
        )
        self.tally_table.setCellWidget(row, 9, central_combo)
        
        # IN/OUT
        inout_combo = QComboBox()
        inout_combo.addItems(["IN", "OUT"])
        inout_combo.currentTextChanged.connect(
            lambda text, r=row: self.on_joint_status_changed(r, text)
        )
        self.tally_table.setCellWidget(row, 10, inout_combo)
        
        # Remarks
        remarks_edit = QLineEdit()
        remarks_edit.textChanged.connect(
            lambda text, r=row: self.on_remarks_changed(r, text)
        )
        self.tally_table.setCellWidget(row, 11, remarks_edit)
        
        # محاسبه اولیه
        self.calculate_tally()
        
        return row
    
    def remove_tally_row(self):
        """حذف ردیف Tally انتخاب شده"""
        current_row = self.tally_table.currentRow()
        if current_row >= 0:
            self.tally_table.removeRow(current_row)
            self.renumber_tally_rows()
            self.calculate_tally()
    
    def renumber_tally_rows(self):
        """شماره‌گذاری مجدد ردیف‌های Tally"""
        for row in range(self.tally_table.rowCount()):
            self.tally_table.item(row, 0).setText(str(row + 1))
    
    def clear_tally_table(self):
        """پاک کردن تمام ردیف‌های Tally"""
        reply = QMessageBox.question(
            self, "Clear Table", 
            "Are you sure you want to clear the entire tally table?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.tally_table.setRowCount(0)
    
    # ============ UTILITY METHODS ============
    def set_current_well(self, well_id, well_name=None):
        """تنظیم چاه جاری"""
        self.current_well = well_id
        
        if hasattr(self, 'current_well_label'):
            if well_name:
                self.current_well_label.setText(f"Current Well: {well_name} (ID: {well_id})")
            else:
                self.current_well_label.setText(f"Current Well ID: {well_id}")
        
        logger.info(f"CasingTallyWidget: Current well set to {well_id}")
    
    def auto_fill_tally(self):
        """پر کردن خودکار Tally"""
        reply = QMessageBox.question(
            self, "Auto Fill", 
            "This will add 20 sample joints. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for i in range(20):
                self.add_tally_row(self.tally_table.rowCount() + 1)
            self.calculate_tally()
            self.status_bar.showMessage("Auto fill completed", 3000)
    
    def calculate_all(self):
        """انجام تمام محاسبات"""
        self.calculate_buoyancy()
        self.calculate_tally()
        self.generate_summary_report()
        self.status_bar.showMessage("All calculations completed", 3000)
    
    def generate_summary_report(self):
        """تولید خلاصه گزارش"""
        try:
            if not hasattr(self, 'summary_text'):
                return
            
            # استفاده از آمارهای موجود
            summary = f"""📊 CASING TALLY SUMMARY REPORT
====================================
📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌐 Well ID: {self.current_well if self.current_well else "Not Selected"}

📈 BASIC STATISTICS:
• Total Joints: {self.stats_labels.get('total_joints', QLabel('0')).text()}
• IN Joints: {self.stats_labels.get('in_joints', QLabel('0')).text()}
• OUT Joints: {self.stats_labels.get('out_joints', QLabel('0')).text()}
• Total Length: {self.stats_labels.get('total_length', QLabel('0')).text()}
• Total Buoyant Weight: {self.stats_labels.get('total_weight', QLabel('0')).text()}
• Total String Capacity: {self.stats_labels.get('total_capacity', QLabel('0')).text()}
• Average Joint Length: {self.stats_labels.get('avg_length', QLabel('0')).text()}
• Buoyancy Factor: {self.stats_labels.get('buoyancy_factor', QLabel('0')).text()}

⚙️ INPUT PARAMETERS:
• RT Depth: {self.rt_depth.value():.2f} m
• Mud Weight: {self.mud_weight.value():.1f} pcf
• Steel Density: {self.steel_density.value():.0f} lb/ft³

📋 CASING SPECIFICATIONS:
"""
            
            # اضافه کردن مشخصات
            spec_count = min(5, self.specs_table.rowCount())
            for row in range(spec_count):
                size_widget = self.specs_table.cellWidget(row, 0)
                grade_widget = self.specs_table.cellWidget(row, 10)
                weight_widget = self.specs_table.cellWidget(row, 2)
                
                if size_widget and grade_widget and weight_widget:
                    size = size_widget.value()
                    grade = grade_widget.currentText()
                    weight = weight_widget.value()
                    
                    summary += f"• {size}\" {grade} - {weight} lb/ft\n"
            
            summary += "\n🔧 RECOMMENDATIONS:"
            summary += "\n1. Verify all IN/OUT status before running in hole."
            summary += "\n2. Check centralizer placement according to design."
            summary += "\n3. Record actual make-up torque for each connection."
            summary += "\n4. Perform pressure test after installation."
            summary += "\n5. Update tally after each joint is run in hole."
            
            self.summary_text.setPlainText(summary)
            self.status_bar.showMessage("Summary generated successfully", 3000)
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            self.status_bar.showMessage(f"Error generating summary: {str(e)}", 5000)
    
    # ============ IMPORT/EXPORT METHODS ============
    def import_specifications(self):
        """وارد کردن مشخصات"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Specifications", 
            "", "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if file_name:
            try:
                import pandas as pd
                
                if file_name.endswith('.csv'):
                    df = pd.read_csv(file_name)
                else:
                    df = pd.read_excel(file_name)
                
                self.specs_table.setRowCount(0)
                
                for _, row in df.iterrows():
                    self.add_specification_row(
                        row.get('Size', 13.375),
                        row.get('ID', 12.415),
                        row.get('Weight', 61),
                        row.get('Drift_ID', 12.347),
                        row.get('Torque', 22700),
                        row.get('Burst', 6070),
                        row.get('Collapse', 4810),
                        row.get('Tensile', 1126000),
                        row.get('Coupling', 'BTC'),
                        row.get('Nominal_OD', 14.375),
                        row.get('Grade', 'P-110'),
                        row.get('Connection', 'Premium')
                    )
                
                self.status_bar.showMessage(f"Imported {len(df)} specifications", 3000)
                
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import: {str(e)}")
    
    def export_specifications(self):
        """خروجی گرفتن از مشخصات"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Specifications",
            "casing_specifications.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if file_name:
            try:
                import pandas as pd
                
                data = []
                for row in range(self.specs_table.rowCount()):
                    row_data = {}
                    for col in range(self.specs_table.columnCount()):
                        widget = self.specs_table.cellWidget(row, col)
                        if isinstance(widget, QComboBox):
                            row_data[col] = widget.currentText()
                        elif isinstance(widget, QDoubleSpinBox):
                            row_data[col] = widget.value()
                    data.append(row_data)
                
                df = pd.DataFrame(data)
                df.columns = [
                    "Size (in)", "ID (in)", "Weight (lb/ft)", "Drift ID (in)",
                    "Make Up Torque (lb-ft)", "Burst (psi)", "Collapse (psi)",
                    "Tensile (lbs)", "Coupling", "Nominal OD (in)", "Grade", "Connection"
                ]
                
                if file_name.endswith('.csv'):
                    df.to_csv(file_name, index=False)
                else:
                    df.to_excel(file_name, index=False)
                
                self.status_bar.showMessage(f"Exported to {file_name}", 3000)
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
    
    def import_tally_data(self):
        """وارد کردن داده‌های Tally"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Tally Data",
            "", "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if file_name:
            try:
                import pandas as pd
                
                if file_name.endswith('.csv'):
                    df = pd.read_csv(file_name)
                else:
                    df = pd.read_excel(file_name)
                
                self.tally_table.setRowCount(0)
                
                for i, row in df.iterrows():
                    self.add_tally_row(i + 1)
                    
                    # پر کردن مقادیر
                    size_combo = self.tally_table.cellWidget(i, 1)
                    if size_combo:
                        size_combo.setCurrentText(str(row.get('Size', '13.375')))
                    
                    grade_combo = self.tally_table.cellWidget(i, 2)
                    if grade_combo:
                        grade_combo.setCurrentText(str(row.get('Grade', 'P-110')))
                    
                    order_edit = self.tally_table.cellWidget(i, 3)
                    if order_edit:
                        order_edit.setText(str(row.get('Order_No', f'ORD-{i+1:03d}')))
                    
                    length_spin = self.tally_table.cellWidget(i, 4)
                    if length_spin:
                        length_spin.setValue(float(row.get('Joint_Len', 12.0)))
                    
                    central_combo = self.tally_table.cellWidget(i, 9)
                    if central_combo:
                        central_combo.setCurrentText(str(row.get('Centralizers', 'Yes')))
                    
                    inout_combo = self.tally_table.cellWidget(i, 10)
                    if inout_combo:
                        inout_combo.setCurrentText(str(row.get('IN_OUT', 'IN')))
                    
                    remarks_edit = self.tally_table.cellWidget(i, 11)
                    if remarks_edit:
                        remarks_edit.setText(str(row.get('Remarks', '')))
                
                self.calculate_tally()
                self.status_bar.showMessage(f"Imported {len(df)} tally rows", 3000)
                
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import: {str(e)}")
    
    def export_tally_data(self):
        """خروجی گرفتن از داده‌های Tally"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Tally Data",
            "casing_tally.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if file_name:
            try:
                import pandas as pd
                
                data = []
                for row in range(self.tally_table.rowCount()):
                    row_data = {}
                    
                    # مقادیر ورودی
                    row_data['No'] = self.tally_table.item(row, 0).text()
                    
                    size_combo = self.tally_table.cellWidget(row, 1)
                    if size_combo:
                        row_data['Size'] = size_combo.currentText()
                    
                    grade_combo = self.tally_table.cellWidget(row, 2)
                    if grade_combo:
                        row_data['Grade'] = grade_combo.currentText()
                    
                    order_edit = self.tally_table.cellWidget(row, 3)
                    if order_edit:
                        row_data['Order_No'] = order_edit.text()
                    
                    length_spin = self.tally_table.cellWidget(row, 4)
                    if length_spin:
                        row_data['Joint_Len'] = length_spin.value()
                    
                    # مقادیر محاسبه شده
                    for col, key in [(5, 'Cum_Length'), (6, 'Dist_to_RT'), 
                                   (7, 'MD_Weight'), (8, 'String_Cap')]:
                        item = self.tally_table.item(row, col)
                        if item:
                            row_data[key] = item.text()
                    
                    central_combo = self.tally_table.cellWidget(row, 9)
                    if central_combo:
                        row_data['Centralizers'] = central_combo.currentText()
                    
                    inout_combo = self.tally_table.cellWidget(row, 10)
                    if inout_combo:
                        row_data['IN_OUT'] = inout_combo.currentText()
                    
                    remarks_edit = self.tally_table.cellWidget(row, 11)
                    if remarks_edit:
                        row_data['Remarks'] = remarks_edit.text()
                    
                    data.append(row_data)
                
                df = pd.DataFrame(data)
                
                if file_name.endswith('.csv'):
                    df.to_csv(file_name, index=False)
                else:
                    df.to_excel(file_name, index=False)
                
                self.status_bar.showMessage(f"Exported {len(data)} rows", 3000)
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
    
    def save_tally_report(self):
        """ذخیره گزارش Tally در دیتابیس"""
        if not self.current_well:
            QMessageBox.warning(self, "Warning", "Please select a well first.")
            return
        
        try:
            from datetime import datetime
            import json
            
            # جمع‌آوری داده‌های مشخصات
            specs_data = []
            for row in range(self.specs_table.rowCount()):
                row_data = {}
                for col in range(self.specs_table.columnCount()):
                    widget = self.specs_table.cellWidget(row, col)
                    if isinstance(widget, QComboBox):
                        row_data[col] = widget.currentText()
                    elif isinstance(widget, QDoubleSpinBox):
                        row_data[col] = widget.value()
                specs_data.append(row_data)
            
            # جمع‌آوری داده‌های Tally
            tally_data = []
            for row in range(self.tally_table.rowCount()):
                row_data = {}
                
                # مقادیر ورودی
                row_data['no'] = self.tally_table.item(row, 0).text()
                
                for col, widget_type in [(1, 'size'), (2, 'grade'), (3, 'order_no'), 
                                       (4, 'joint_length'), (9, 'centralizers'), 
                                       (10, 'in_out'), (11, 'remarks')]:
                    widget = self.tally_table.cellWidget(row, col)
                    if widget:
                        if isinstance(widget, QComboBox):
                            row_data[widget_type] = widget.currentText()
                        elif isinstance(widget, QDoubleSpinBox):
                            row_data[widget_type] = widget.value()
                        elif isinstance(widget, QLineEdit):
                            row_data[widget_type] = widget.text()
                
                # مقادیر محاسبه شده
                for col, key in [(5, 'cum_length'), (6, 'dist_to_rt'), 
                               (7, 'md_weight'), (8, 'string_cap')]:
                    item = self.tally_table.item(row, col)
                    if item:
                        row_data[key] = item.text()
                
                tally_data.append(row_data)
            
            # پارامترهای محاسباتی
            input_params = {
                'rt_depth': self.rt_depth.value(),
                'mud_weight': self.mud_weight.value(),
                'steel_density': self.steel_density.value(),
                'buoyancy_factor': self.buoyancy_factor.value()
            }
            
            logger.info(f"Casing Tally data prepared for well {self.current_well}")
            QMessageBox.information(self, "Success", "Tally report prepared successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    def load_tally_report(self):
        """بارگذاری گزارش Tally از دیتابیس"""
        if not self.current_well:
            QMessageBox.warning(self, "Warning", "Please select a well first.")
            return
        
        QMessageBox.information(self, "Info", "Load functionality will be implemented with database integration.")
    
    def export_summary_report(self):
        """خروجی گرفتن از گزارش خلاصه"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Summary Report",
            "casing_tally_summary.txt",
            "Text Files (*.txt);;PDF Files (*.pdf);;Word Documents (*.docx)"
        )
        
        if file_name:
            try:
                if file_name.endswith('.txt'):
                    with open(file_name, 'w', encoding='utf-8') as f:
                        f.write(self.summary_text.toPlainText())
                
                self.status_bar.showMessage(f"Summary exported to {file_name}", 3000)
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
    
    def print_report(self):
        """چاپ گزارش"""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QPrintDialog.Accepted:
            document = QTextDocument()
            document.setPlainText(self.summary_text.toPlainText())
            document.print_(printer)
            
            self.status_bar.showMessage("Report sent to printer", 3000)            
# ==================== CLASS 5: WellboreSchematicTab ====================
class WellboreSchematicTab(QWidget):
    """تب حرفه‌ای شماتیک چاه - سطح نرم‌افزارهای صنعتی"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent = parent
        
        self.current_well = None
        self.well_data = {}
        self.schematic_elements = []
        self.selected_items = []
        
        # مدیریت زوم و پن
        self.zoom_factor = 1.0
        self.is_panning = False
        self.last_mouse_pos = None
        
        # تنظیم current_tool برای جلوگیری از خطا
        self.current_tool = "select"
        
        # رنگ‌های استاندارد صنعتی
        self.standard_colors = {
            'casing': QColor(100, 100, 100),
            'open_hole': QColor(210, 180, 140),
            'cement': QColor(220, 220, 220),
            'formation': QColor(139, 69, 19),
            'reservoir': QColor(255, 100, 100),
            'water': QColor(100, 149, 237),
            'oil': QColor(255, 215, 0),
            'gas': QColor(144, 238, 144),
            'tubing': QColor(70, 130, 180),
            'packer': QColor(178, 34, 34),
            'perforation': QColor(255, 69, 0),
            'bit': QColor(30, 30, 30),
            'bha': QColor(60, 60, 60)
        }
        
        self.init_ui()
        self.setup_connections()
        self.setup_shortcuts()
        
        logger.info("WellboreSchematicTab initialized")
    def init_ui(self):
        """راه‌اندازی رابط کاربری با اسکرول"""
        # ============ ایجاد Layout اصلی با اسکرول ============
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_area = scroll
        # ویجت محتوای اصلی
        content_widget = QWidget()
        self.main_layout = QVBoxLayout(content_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ============ نوار ابزار اصلی ============
        self.create_main_toolbar()
        self.main_layout.addWidget(self.main_toolbar)
        
        # ============ Splitter اصلی ============
        self.splitter = QSplitter(Qt.Horizontal)
        
        # ایجاد پنل‌ها
        left_panel = self.create_left_panel()
        center_panel = self.create_center_panel()
        right_panel = self.create_right_panel()
        
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(center_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([200, 500, 200])
        self.splitter.setMinimumWidth(900) 
        
        self.main_layout.addWidget(self.splitter)
        
        # ============ نوار وضعیت ============
        self.create_main_status_bar()
        if self.status_bar:
            self.main_layout.addWidget(self.status_bar)
        
        # ============ تنظیم اسکرول ============
        content_widget.setMinimumSize(1300, 750)  # حداقل اندازه
        scroll.setWidget(content_widget)
        
        # ============ تنظیم layout نهایی ============
        final_layout = QVBoxLayout(self)
        final_layout.setContentsMargins(0, 0, 0, 0)
        final_layout.setSpacing(0)
        final_layout.addWidget(self.scroll_area)        


        # اعمال استایل
        self.apply_scroll_styles() 
        
        # تنظیم splitter
        QTimer.singleShot(100, self.adjust_splitter_for_scroll)
        
    
    def create_main_status_bar(self):
        """ایجاد نوار وضعیت اصلی"""
        self.status_bar = QStatusBar()
        
        # بخش‌های مختلف status bar
        self.status_bar.addWidget(QLabel("Status: Ready"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.memory_label = QLabel("Memory: --")
        self.status_bar.addPermanentWidget(self.memory_label)
        
        self.fps_label = QLabel("FPS: --")
        self.status_bar.addPermanentWidget(self.fps_label)
    # ============ متدهای جدید برای اسکرول ============
    
    def setup_ui_optimizations(self):
        """تنظیمات بهینه‌سازی UI برای اسکرول"""
        # تنظیم پالیسی اندازه‌گیری
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # فعال کردن اسکرول نرم (Smooth Scrolling)
        if self.scroll_area:
            self.scroll_area.verticalScrollBar().setSingleStep(20)
            self.scroll_area.horizontalScrollBar().setSingleStep(20)
        
        # تنظیم حداقل و حداکثر اندازه‌ها
        self.setMinimumSize(800, 600)
    
    def resizeEvent(self, event):
        """هنگام تغییر اندازه ویندوز"""
        # آپدیت layout
        self.updateGeometry()
        # فراخوانی متد والد
        super().resizeEvent(event)
    
    def adjust_splitter_for_scroll(self):
        """تنظیم splitter برای سازگاری با اسکرول"""
        if not self.splitter:
            return
            
        # وقتی اسکرول فعال است، splitter باید انعطاف‌پذیر باشد
        self.splitter.setChildrenCollapsible(False)
        
        # تنظیم حداقل اندازه برای پنل‌ها
        self.splitter.setMinimumSize(1000, 600)
        
        # اجازه تغییر اندازه پنل‌ها
        for i in range(self.splitter.count()):
            widget = self.splitter.widget(i)
            if widget:
                widget.setMinimumWidth(150)
    
    def apply_scroll_styles(self):
        """اعمال استایل compact"""
        style = """
        /* پنل‌ها */
        QWidget {
            font-size: 11px;
        }
        
        /* دکمه‌ها */
        QPushButton {
            padding: 4px 8px;
            font-size: 11px;
            border-radius: 3px;
        }
        
        /* جداول */
        QTableWidget {
            font-size: 10px;
        }
        
        QTableWidget::item {
            padding: 2px;
        }
        
        /* تب‌ها */
        QTabWidget::pane {
            border: 1px solid #ccc;
        }
        
        QTabBar::tab {
            padding: 4px 8px;
            margin: 1px;
        }
        
        /* Splitter */
        QSplitter::handle {
            background-color: #ddd;
            width: 3px;
        }
        
        QSplitter::handle:hover {
            background-color: #aaa;
        }
        
        /* Scrollbars */
        QScrollBar:vertical, QScrollBar:horizontal {
            width: 10px;
            height: 10px;
        }
        """
        
        self.setStyleSheet(style)
    
    def create_left_panel(self):
        """ایجاد پنل چپ compact"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # عناصر چاه (کم حجم)
        elements_btn = QPushButton("🏗️ Elements")
        elements_btn.setToolTip("Well elements")
        elements_btn.clicked.connect(self.show_elements_dialog)
        layout.addWidget(elements_btn)
        
        # لیست عناصر (اضافه شده)
        self.elements_list = QListWidget()
        
        # اضافه کردن عناصر نمونه
        elements = [
            ("🔧 Casing", "casing"),
            ("🔄 Tubing", "tubing"),
            ("📌 Packer", "packer"),
            ("🎯 Perforation", "perforation"),
            ("⛏️ Bit", "bit"),
            ("🔩 BHA", "bha")
        ]
        
        for name, element_type in elements:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, element_type)
            self.elements_list.addItem(item)
        
        layout.addWidget(self.elements_list)
        
        # لایه‌ها (کم حجم)
        layers_btn = QPushButton("🏔️ Layers")
        layers_btn.setToolTip("Formation layers")
        layers_btn.clicked.connect(self.show_layers_dialog)
        layout.addWidget(layers_btn)
        
        # پارامترها (کم حجم)
        params_btn = QPushButton("⚙️ Params")
        params_btn.setToolTip("Well parameters")
        params_btn.clicked.connect(self.show_parameters_dialog)
        layout.addWidget(params_btn)
        
        layout.addStretch()
        
        widget.setMinimumWidth(150)
        widget.setMaximumWidth(250)
        
        return widget

    def create_center_panel(self):
        """ایجاد پنل مرکزی compact"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # نوار ابزار View - اصلاح شده
        view_toolbar = self.create_view_toolbar()  # بدون پارامتر
        if view_toolbar:
            layout.addWidget(view_toolbar)
        
        # View گرافیکی
        self.create_graphics_view(layout)
        
        # نوار وضعیت گرافیکی
        self.create_graphics_status_bar(layout)
        
        widget.setMinimumWidth(400)
        
        return widget

    def create_right_panel(self):
        """ایجاد پنل راست compact"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # Properties (تب‌بندی)
        self.properties_tabs = QTabWidget()
        self.properties_tabs.setTabPosition(QTabWidget.West)  # تب‌ها در سمت چپ
        
        # تب Properties
        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)
        self.properties_table = QTableWidget(0, 2)
        self.properties_table.horizontalHeader().setStretchLastSection(True)
        props_layout.addWidget(self.properties_table)
        self.properties_tabs.addTab(props_widget, "📋")
        
        # تب Layers
        layers_widget = QWidget()
        layers_layout = QVBoxLayout(layers_widget)
        self.layers_list = QListWidget()
        layers_layout.addWidget(self.layers_list)
        self.properties_tabs.addTab(layers_widget, "📁")
        
        layout.addWidget(self.properties_tabs)
        
        widget.setMinimumWidth(150)
        widget.setMaximumWidth(250)
        
        return widget
    
    def create_main_toolbar(self):
        """ایجاد نوار ابزار اصلی"""
        self.main_toolbar = QToolBar("Main Tools")
        self.main_toolbar.setIconSize(QSize(28, 28))
        
        # فایل
        self.main_toolbar.addAction(self.create_action("📁 New", "New Schematic", 
                                                      self.new_schematic, "Ctrl+N"))
        self.main_toolbar.addAction(self.create_action("📂 Open", "Open Schematic", 
                                                      self.load_schematic, "Ctrl+O"))
        self.main_toolbar.addAction(self.create_action("💾 Save", "Save Schematic", 
                                                      self.save_schematic, "Ctrl+S"))
        self.main_toolbar.addSeparator()
        
        # ابزارهای طراحی
        self.tool_actions = {}
        tools = [
            ("🔍", "select", "Select Tool", "S"),
            ("📏", "line", "Line Tool", "L"),
            ("⬜", "rectangle", "Rectangle Tool", "R"),
            ("⚪", "ellipse", "Ellipse Tool", "E"),
            ("🔧", "casing", "Casing Tool", "C"),
            ("⛏️", "bit", "Bit Tool", "B"),
            ("📌", "packer", "Packer Tool", "P"),
            ("🔄", "perforation", "Perforation Tool", "F"),
            ("📝", "text", "Text Tool", "T"),
            ("📊", "chart", "Chart Tool", "H")
        ]
        
        for icon, tool_id, tooltip, shortcut in tools:
            action = QAction(icon, self)
            action.setToolTip(f"{tooltip} ({shortcut})")
            action.setCheckable(True)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda checked, t=tool_id: self.set_tool(t))
            self.tool_actions[tool_id] = action
            self.main_toolbar.addAction(action)
        
        self.tool_actions["select"].setChecked(True)
        
        self.main_toolbar.addSeparator()
        
        # تنظیمات نمایش
        display_group = QActionGroup(self)
        display_actions = [
            ("🎨", "colors", "Color Display", self.set_display_mode),
            ("⬛", "grayscale", "Grayscale Display", self.set_display_mode),
            ("📐", "wireframe", "Wireframe Display", self.set_display_mode)
        ]
        
        for icon, mode, tooltip, slot in display_actions:
            action = QAction(icon, self)
            action.setToolTip(tooltip)
            action.setCheckable(True)
            action.setData(mode)
            action.triggered.connect(lambda checked, a=action: slot(a.data()))
            display_group.addAction(action)
            self.main_toolbar.addAction(action)
        
        display_group.actions()[0].setChecked(True)
        
        self.main_toolbar.addSeparator()
        
        # Import/Export
        self.main_toolbar.addAction(self.create_action("📤 Import", "Import from CAD", 
                                                      self.import_cad, "Ctrl+I"))
        self.main_toolbar.addAction(self.create_action("📥 Export", "Export to PDF/DXF", 
                                                      self.export_drawing, "Ctrl+E"))
        self.main_toolbar.addAction(self.create_action("🖨️ Print", "Print Schematic", 
                                                      self.print_schematic, "Ctrl+P"))
    
    def show_elements_dialog(self):
        """نمایش دیالوگ عناصر چاه"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("🏗️ Well Elements")
            dialog.setModal(True)
            dialog.setMinimumSize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # لیست عناصر
            elements_list = QListWidget()
            elements = [
                ("🔧 Casing", self.standard_colors['casing']),
                ("⛏️ Open Hole", self.standard_colors['open_hole']),
                ("🏗️ Cement", self.standard_colors['cement']),
                ("🔄 Tubing", self.standard_colors['tubing']),
                ("📌 Packer", self.standard_colors['packer']),
                ("🎯 Perforation", self.standard_colors['perforation']),
                ("⛏️ Bit", self.standard_colors['bit']),
                ("🔩 BHA", self.standard_colors['bha'])
            ]
            
            for name, color in elements:
                item = QListWidgetItem(name)
                item.setForeground(color)
                elements_list.addItem(item)
            
            layout.addWidget(elements_list)
            
            # دکمه‌ها
            btn_layout = QHBoxLayout()
            insert_btn = QPushButton("Insert Selected")
            insert_btn.clicked.connect(lambda: self.insert_selected_element(elements_list.currentItem()))
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(insert_btn)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing elements dialog: {e}")
            QMessageBox.warning(self, "Error", f"Failed to show elements dialog: {str(e)}")

    def show_layers_dialog(self):
        """نمایش دیالوگ لایه‌ها"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("🏔️ Formation Layers")
            dialog.setModal(True)
            dialog.setMinimumSize(600, 500)
            
            layout = QVBoxLayout(dialog)
            
            # جدول لایه‌ها (از formation_table استفاده می‌کنیم)
            table = QTableWidget(0, 4)
            table.setHorizontalHeaderLabels(["Depth (m)", "Thickness (m)", "Type", "Color"])
            table.horizontalHeader().setStretchLastSection(True)
            
            # نمونه داده‌ها
            sample_data = [
                [0, 500, "Top Soil", QColor(210, 180, 140)],
                [500, 300, "Shale", QColor(160, 120, 80)],
                [800, 400, "Sandstone", QColor(120, 100, 60)],
                [1200, 600, "Limestone", QColor(80, 60, 40)]
            ]
            
            table.setRowCount(len(sample_data))
            for i, (depth, thickness, type_name, color) in enumerate(sample_data):
                table.setItem(i, 0, QTableWidgetItem(str(depth)))
                table.setItem(i, 1, QTableWidgetItem(str(thickness)))
                table.setItem(i, 2, QTableWidgetItem(type_name))
                
                color_item = QTableWidgetItem()
                color_item.setBackground(color)
                table.setItem(i, 3, color_item)
            
            layout.addWidget(table)
            
            # دکمه‌ها
            btn_layout = QHBoxLayout()
            add_btn = QPushButton("➕ Add Layer")
            add_btn.clicked.connect(lambda: self.add_layer_from_dialog(table))
            
            delete_btn = QPushButton("➖ Delete")
            delete_btn.clicked.connect(lambda: table.removeRow(table.currentRow()))
            
            apply_btn = QPushButton("Apply to Schematic")
            apply_btn.clicked.connect(lambda: self.apply_layers_to_schematic(table))
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(add_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.addWidget(apply_btn)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing layers dialog: {e}")
            QMessageBox.warning(self, "Error", f"Failed to show layers dialog: {str(e)}")

    def show_parameters_dialog(self):
        """نمایش دیالوگ پارامترها"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("⚙️ Well Parameters")
            dialog.setModal(True)
            dialog.setMinimumSize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            form_layout = QFormLayout()
            
            # عمق چاه
            depth_spin = QDoubleSpinBox()
            depth_spin.setRange(0, 20000)
            depth_spin.setValue(self.well_depth.value() if hasattr(self, 'well_depth') else 3000)
            depth_spin.setSuffix(" m")
            form_layout.addRow("Well Depth:", depth_spin)
            
            # سایز حفره
            hole_spin = QDoubleSpinBox()
            hole_spin.setRange(0, 50)
            hole_spin.setValue(self.hole_size.value() if hasattr(self, 'hole_size') else 8.5)
            hole_spin.setSuffix(" in")
            form_layout.addRow("Hole Size:", hole_spin)
            
            # مقیاس
            scale_combo = QComboBox()
            scale_combo.addItems(["1:100", "1:200", "1:500", "1:1000"])
            if hasattr(self, 'vertical_scale'):
                index = scale_combo.findText(self.vertical_scale.currentText())
                if index >= 0:
                    scale_combo.setCurrentIndex(index)
            form_layout.addRow("Vertical Scale:", scale_combo)
            
            layout.addLayout(form_layout)
            
            # دکمه‌ها
            btn_layout = QHBoxLayout()
            apply_btn = QPushButton("Apply")
            apply_btn.clicked.connect(lambda: self.apply_parameters_from_dialog(
                depth_spin.value(), 
                hole_spin.value(), 
                scale_combo.currentText()
            ))
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(apply_btn)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing parameters dialog: {e}")
            QMessageBox.warning(self, "Error", f"Failed to show parameters dialog: {str(e)}")
    
    def insert_selected_element(self, item):
        """درج عنصر انتخاب شده"""
        if item:
            element_name = item.text()
            logger.info(f"Inserting element: {element_name}")
            # در اینجا کد درج عنصر به شماتیک را اضافه کنید
            QMessageBox.information(self, "Info", f"Element '{element_name}' will be inserted")

    def add_layer_from_dialog(self, table):
        """اضافه کردن لایه از دیالوگ"""
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem("0"))
        table.setItem(row, 1, QTableWidgetItem("100"))
        table.setItem(row, 2, QTableWidgetItem("New Layer"))
        
        color_item = QTableWidgetItem()
        color_item.setBackground(QColor(200, 200, 200))
        table.setItem(row, 3, color_item)

    def apply_layers_to_schematic(self, table):
        """اعمال لایه‌ها به شماتیک"""
        layer_count = table.rowCount()
        logger.info(f"Applying {layer_count} layers to schematic")
        QMessageBox.information(self, "Info", f"{layer_count} layers will be applied to schematic")

    def apply_parameters_from_dialog(self, depth, hole_size, scale):
        """اعمال پارامترها از دیالوگ"""
        if hasattr(self, 'well_depth'):
            self.well_depth.setValue(depth)
        if hasattr(self, 'hole_size'):
            self.hole_size.setValue(hole_size)
        if hasattr(self, 'vertical_scale'):
            index = self.vertical_scale.findText(scale)
            if index >= 0:
                self.vertical_scale.setCurrentIndex(index)
    
        logger.info(f"Parameters applied: Depth={depth}m, Hole={hole_size}in, Scale={scale}")
        QMessageBox.information(self, "Success", "Parameters applied successfully")
    
    
    def create_view_toolbar(self):
        """ایجاد نوار ابزار View - اصلاح شده"""
        try:
            view_toolbar = QToolBar()
            view_toolbar.setIconSize(QSize(22, 22))
            
            # کنترل‌های زوم
            zoom_out_action = QAction("➖", self)
            zoom_out_action.setToolTip("Zoom Out")
            zoom_out_action.triggered.connect(self.zoom_out)
            view_toolbar.addAction(zoom_out_action)
            
            self.zoom_label = QLabel("100%")
            self.zoom_label.setMinimumWidth(60)
            view_toolbar.addWidget(self.zoom_label)
            
            zoom_in_action = QAction("➕", self)
            zoom_in_action.setToolTip("Zoom In")
            zoom_in_action.triggered.connect(self.zoom_in)
            view_toolbar.addAction(zoom_in_action)
            
            fit_action = QAction("🔍", self)
            fit_action.setToolTip("Fit to View")
            fit_action.triggered.connect(self.fit_to_view)
            view_toolbar.addAction(fit_action)
            
            view_toolbar.addSeparator()
            
            # Grid Controls
            grid_action = QAction("🗺️", self)
            grid_action.setToolTip("Toggle Grid")
            grid_action.setCheckable(True)
            grid_action.setChecked(True)
            grid_action.triggered.connect(self.toggle_grid)
            view_toolbar.addAction(grid_action)
            
            snap_action = QAction("🧲", self)
            snap_action.setToolTip("Toggle Snap to Grid")
            snap_action.setCheckable(True)
            snap_action.setChecked(True)
            snap_action.triggered.connect(self.toggle_snap)
            view_toolbar.addAction(snap_action)
            
            view_toolbar.addSeparator()
            
            # Layers Visibility
            self.show_casing_action = QAction("🔧", self)
            self.show_casing_action.setToolTip("Show/Hide Casing")
            self.show_casing_action.setCheckable(True)
            self.show_casing_action.setChecked(True)
            self.show_casing_action.triggered.connect(lambda: self.toggle_layer_visibility('casing'))
            view_toolbar.addAction(self.show_casing_action)
            
            self.show_formation_action = QAction("🏔️", self)
            self.show_formation_action.setToolTip("Show/Hide Formation")
            self.show_formation_action.setCheckable(True)
            self.show_formation_action.setChecked(True)
            self.show_formation_action.triggered.connect(lambda: self.toggle_layer_visibility('formation'))
            view_toolbar.addAction(self.show_formation_action)
            
            # ذخیره actions برای استفاده بعدی
            self.zoom_out_btn = zoom_out_action
            self.zoom_in_btn = zoom_in_action
            self.fit_btn = fit_action
            
            return view_toolbar
            
        except Exception as e:
            logger.error(f"Error creating view toolbar: {e}")
            return None
        
    def create_graphics_view(self, layout):
        """ایجاد View گرافیکی حرفه‌ای"""
        # ایجاد Scene
        self.graphics_scene = QGraphicsScene()
        self.graphics_scene.setBackgroundBrush(QBrush(QColor(245, 245, 245)))
        
        # ایجاد View
        self.graphics_view = EnhancedGraphicsView(self.graphics_scene, self)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setRenderHint(QPainter.TextAntialiasing, True)
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.graphics_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.graphics_view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
        
        # ایجاد Grid
        self.grid_item = QGraphicsPathItem()
        self.grid_item.setZValue(-1000)
        self.graphics_scene.addItem(self.grid_item)
        self.update_grid()
        
        layout.addWidget(self.graphics_view)
    
    def create_graphics_status_bar(self, layout):
        """ایجاد نوار وضعیت گرافیکی"""
        status_layout = QHBoxLayout()
        
        self.coords_label = QLabel("X: 0.00, Y: 0.00")
        self.coords_label.setMinimumWidth(150)
        status_layout.addWidget(self.coords_label)
        
        self.scale_label = QLabel("Scale: 1:100")
        status_layout.addWidget(self.scale_label)
        
        self.selected_label = QLabel("Selected: None")
        status_layout.addWidget(self.selected_label)
        
        status_layout.addStretch()
        
        self.undo_label = QLabel("Undo: 0")
        status_layout.addWidget(self.undo_label)
        
        self.redo_label = QLabel("Redo: 0")
        status_layout.addWidget(self.redo_label)
        
        container = QWidget()
        container.setLayout(status_layout)
        container.setMaximumHeight(30)
        layout.addWidget(container)
    
    def create_properties_inspector(self, layout):
        """ایجاد Properties Inspector"""
        properties_group = QGroupBox("📋 Properties Inspector")
        properties_layout = QVBoxLayout()
        
        self.properties_table = QTableWidget(0, 2)
        self.properties_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.properties_table.setAlternatingRowColors(True)
        
        properties_layout.addWidget(self.properties_table)
        
        # دکمه‌های Properties
        prop_btn_layout = QHBoxLayout()
        apply_prop_btn = QPushButton("Apply")
        apply_prop_btn.clicked.connect(self.apply_properties)
        
        reset_prop_btn = QPushButton("Reset")
        reset_prop_btn.clicked.connect(self.reset_properties)
        
        prop_btn_layout.addWidget(apply_prop_btn)
        prop_btn_layout.addWidget(reset_prop_btn)
        properties_layout.addLayout(prop_btn_layout)
        
        properties_group.setLayout(properties_layout)
        layout.addWidget(properties_group)
    
    def create_layers_panel(self, layout):
        """ایجاد پنل لایه‌ها"""
        layers_group = QGroupBox("📁 Layers")
        layers_layout = QVBoxLayout()
        
        self.layers_list = QListWidget()
        self.layers_list.setAlternatingRowColors(True)
        
        # ایجاد لایه‌های پیش‌فرض
        default_layers = [
            ("Background", True, 0),
            ("Grid", True, 1),
            ("Formation", True, 2),
            ("Casing", True, 3),
            ("Tubing", True, 4),
            ("Completion", True, 5),
            ("Labels", True, 6),
            ("Dimensions", True, 7)
        ]
        
        for name, visible, zvalue in default_layers:
            item = QListWidgetItem(name)
            item.setCheckState(Qt.Checked if visible else Qt.Unchecked)
            item.setData(Qt.UserRole, zvalue)
            self.layers_list.addItem(item)
        
        layers_layout.addWidget(self.layers_list)
        
        # دکمه‌های مدیریت لایه‌ها
        layers_btn_layout = QHBoxLayout()
        add_layer_btn = QPushButton("New Layer")
        delete_layer_btn = QPushButton("Delete")
        move_up_btn = QPushButton("▲")
        move_down_btn = QPushButton("▼")
        
        add_layer_btn.clicked.connect(self.add_new_layer)
        delete_layer_btn.clicked.connect(self.delete_layer)
        move_up_btn.clicked.connect(self.move_layer_up)
        move_down_btn.clicked.connect(self.move_layer_down)
        
        layers_btn_layout.addWidget(add_layer_btn)
        layers_btn_layout.addWidget(delete_layer_btn)
        layers_btn_layout.addStretch()
        layers_btn_layout.addWidget(move_up_btn)
        layers_btn_layout.addWidget(move_down_btn)
        
        layers_layout.addLayout(layers_btn_layout)
        
        layers_group.setLayout(layers_layout)
        layout.addWidget(layers_group)
    
    def create_main_status_bar(self):
        """ایجاد نوار وضعیت اصلی"""
        self.status_bar = QStatusBar()
        
        # بخش‌های مختلف status bar
        self.status_bar.addWidget(QLabel("Status: Ready"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.memory_label = QLabel("Memory: --")
        self.status_bar.addPermanentWidget(self.memory_label)
        
        self.fps_label = QLabel("FPS: --")
        self.status_bar.addPermanentWidget(self.fps_label)
    
    def create_action(self, text, tooltip, slot, shortcut=None):
        """ایجاد Action استاندارد"""
        action = QAction(text, self)
        action.setToolTip(tooltip)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        return action
    
    def setup_connections(self):
        """اتصال سیگنال‌ها برای تب شماتیک"""
        # اتصال تغییرات well parameters - باید بعد از ایجاد بررسی شود
        if hasattr(self, 'well_depth'):
            self.well_depth.valueChanged.connect(self.update_schematic_scale)
        
        if hasattr(self, 'hole_size'):
            self.hole_size.valueChanged.connect(self.update_hole_geometry)
        
        if hasattr(self, 'vertical_scale'):
            self.vertical_scale.currentTextChanged.connect(self.update_schematic_scale)
        
        if hasattr(self, 'display_units'):
            self.display_units.currentTextChanged.connect(self.convert_units)
        
        # اتصال تغییرات formation layers
        if hasattr(self, 'formation_table'):
            self.formation_table.cellChanged.connect(self.update_formation_layers)
        
        # اتصال تایمر برای آپدیت وضعیت
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # هر ثانیه
    
    def setup_shortcuts(self):
        """تنظیم میانبرهای حرفه‌ای"""
        shortcuts = {
            Qt.Key_Delete: self.delete_selected,
            Qt.Key_Escape: self.clear_selection,
            Qt.Key_F1: self.show_help,
            Qt.Key_F5: self.refresh_view,
            Qt.Key_F11: self.toggle_fullscreen,
            Qt.Key_Space: self.toggle_pan_mode,
            Qt.Key_G: lambda: self.toggle_grid(),
            Qt.Key_Plus: self.zoom_in,
            Qt.Key_Minus: self.zoom_out,
            Qt.Key_0: self.zoom_reset,
            Qt.Key_C: lambda: self.set_tool("casing"),
            Qt.Key_B: lambda: self.set_tool("bit"),
            Qt.Key_T: lambda: self.set_tool("text"),
            Qt.Key_V: lambda: self.set_display_mode("colors"),
            Qt.Key_W: lambda: self.set_display_mode("wireframe"),
            Qt.Key_F: self.fit_to_view,
            Qt.Key_Z: self.undo,
            Qt.Key_Y: self.redo
        }
        
        for key, slot in shortcuts.items():
            QShortcut(key, self).activated.connect(slot)
    
            
    
    def create_sample_well(self):
        """ایجاد چاه نمونه صنعتی"""
        # ایجاد زمین
        self.create_ground_layer()
        
        # ایجاد لایه‌های زمین
        self.create_formation_layers()
        
        # ایجاد چاه و casing
        self.create_well_casing()
        
        # ایجاد completion
        self.create_completion_elements()
        
        # ایجاد برچسب‌ها و ابعاد
        self.create_labels_and_dimensions()
    
    def create_ground_layer(self):
        """ایجاد لایه زمین"""
        ground = QGraphicsRectItem(-400, -50, 800, 100)
        ground.setBrush(QBrush(QColor(139, 69, 19)))  # قهوه‌ای
        ground.setPen(QPen(Qt.black, 2))
        ground.setZValue(0)
        ground.setToolTip("Ground Surface")
        self.graphics_scene.addItem(ground)
        
        # برچسب سطح زمین
        label = QGraphicsTextItem("Ground Surface (0 m)")
        label.setPos(-380, -70)
        label.setDefaultTextColor(Qt.black)
        label.setZValue(100)
        self.graphics_scene.addItem(label)
    
    def create_formation_layers(self):
        """ایجاد لایه‌های زمین‌شناسی"""
        formations = [
            {"depth": 0, "thickness": 500, "name": "Top Soil", "color": QColor(210, 180, 140)},
            {"depth": 500, "thickness": 300, "name": "Shale", "color": QColor(160, 120, 80)},
            {"depth": 800, "thickness": 400, "name": "Sandstone", "color": QColor(120, 100, 60)},
            {"depth": 1200, "thickness": 600, "name": "Limestone", "color": QColor(80, 60, 40)},
            {"depth": 1800, "thickness": 800, "name": "Dolomite", "color": QColor(60, 50, 30)},
            {"depth": 2600, "thickness": 400, "name": "Reservoir", "color": QColor(255, 100, 100)}
        ]
        
        for i, formation in enumerate(formations):
            layer = QGraphicsRectItem(-350, formation["depth"]/10, 700, formation["thickness"]/10)
            layer.setBrush(QBrush(formation["color"]))
            layer.setPen(QPen(Qt.black, 1))
            layer.setZValue(1)
            layer.setToolTip(f"{formation['name']}: {formation['depth']}-{formation['depth']+formation['thickness']} m")
            self.graphics_scene.addItem(layer)
            
            # برچسب لایه
            label = QGraphicsTextItem(f"{formation['name']}\n{formation['depth']} - {formation['depth']+formation['thickness']} m")
            label.setPos(-380, formation["depth"]/10 + formation["thickness"]/20 - 15)
            label.setDefaultTextColor(Qt.black)
            label.setZValue(101)
            self.graphics_scene.addItem(label)
            
            # خط جداکننده
            line = QGraphicsLineItem(-350, (formation["depth"]+formation["thickness"])/10, 
                                    350, (formation["depth"]+formation["thickness"])/10)
            line.setPen(QPen(Qt.black, 2))
            line.setZValue(2)
            self.graphics_scene.addItem(line)
    
    def create_well_casing(self):
        """ایجاد Casing چاه"""
        # Surface Casing (20")
        surface_casing = QGraphicsRectItem(-40, 0, 80, 500/10)
        surface_casing.setBrush(QBrush(self.standard_colors['casing']))
        surface_casing.setPen(QPen(Qt.black, 2))
        surface_casing.setZValue(10)
        surface_casing.setToolTip("Surface Casing: 20\" @ 0-500 m")
        self.graphics_scene.addItem(surface_casing)
        
        # Intermediate Casing (13-3/8")
        intermediate_casing = QGraphicsRectItem(-30, 500/10, 60, 1500/10)
        intermediate_casing.setBrush(QBrush(self.standard_colors['casing'].lighter(120)))
        intermediate_casing.setPen(QPen(Qt.black, 2))
        intermediate_casing.setZValue(11)
        intermediate_casing.setToolTip("Intermediate Casing: 13-3/8\" @ 500-2000 m")
        self.graphics_scene.addItem(intermediate_casing)
        
        # Production Casing (9-5/8")
        production_casing = QGraphicsRectItem(-20, 2000/10, 40, 1000/10)
        production_casing.setBrush(QBrush(self.standard_colors['casing'].lighter(150)))
        production_casing.setPen(QPen(Qt.black, 2))
        production_casing.setZValue(12)
        production_casing.setToolTip("Production Casing: 9-5/8\" @ 2000-3000 m")
        self.graphics_scene.addItem(production_casing)
        
        # Open Hole (8-1/2")
        open_hole = QGraphicsRectItem(-15, 3000/10, 30, 100/10)
        open_hole.setBrush(QBrush(self.standard_colors['open_hole']))
        open_hole.setPen(QPen(Qt.black, 2))
        open_hole.setZValue(13)
        open_hole.setToolTip("Open Hole: 8-1/2\" @ 3000-3100 m")
        self.graphics_scene.addItem(open_hole)
        
        # Cement
        cement_thickness = 10
        cement = QGraphicsRectItem(-50, 0, 100, 3000/10)
        cement.setBrush(QBrush(self.standard_colors['cement']))
        cement.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
        cement.setZValue(5)
        cement.setOpacity(0.3)
        self.graphics_scene.addItem(cement)
    
    def create_completion_elements(self):
        """ایجاد عناصر Completion"""
        # Tubing (3-1/2")
        tubing = QGraphicsRectItem(-10, 0, 20, 2800/10)
        tubing.setBrush(QBrush(self.standard_colors['tubing']))
        tubing.setPen(QPen(Qt.black, 1))
        tubing.setZValue(20)
        tubing.setToolTip("Tubing: 3-1/2\"")
        self.graphics_scene.addItem(tubing)
        
        # Packers
        packer_positions = [2500, 2700, 2900]  # متر
        for pos in packer_positions:
            packer = QGraphicsEllipseItem(-15, pos/10 - 5, 30, 10)
            packer.setBrush(QBrush(self.standard_colors['packer']))
            packer.setPen(QPen(Qt.black, 1))
            packer.setZValue(21)
            packer.setToolTip(f"Packer @ {pos} m")
            self.graphics_scene.addItem(packer)
        
        # Perforations
        perforation_interval = {"top": 2950, "bottom": 3050}
        for depth in range(perforation_interval["top"], perforation_interval["bottom"], 10):
            perf = QGraphicsLineItem(-25, depth/10, -35, depth/10)
            perf.setPen(QPen(self.standard_colors['perforation'], 3))
            perf.setZValue(22)
            self.graphics_scene.addItem(perf)
            
            perf = QGraphicsLineItem(25, depth/10, 35, depth/10)
            perf.setPen(QPen(self.standard_colors['perforation'], 3))
            perf.setZValue(22)
            self.graphics_scene.addItem(perf)
        
        # Bit
        bit = QGraphicsEllipseItem(-20, 3100/10 - 10, 40, 20)
        bit.setBrush(QBrush(self.standard_colors['bit']))
        bit.setPen(QPen(Qt.black, 2))
        bit.setZValue(30)
        bit.setToolTip("Drill Bit")
        self.graphics_scene.addItem(bit)
    
    def create_labels_and_dimensions(self):
        """ایجاد برچسب‌ها و ابعاد"""
        # عمق‌ها
        depths = [0, 500, 1000, 1500, 2000, 2500, 3000, 3100]
        for depth in depths:
            line = QGraphicsLineItem(-400, depth/10, -380, depth/10)
            line.setPen(QPen(Qt.black, 1))
            line.setZValue(100)
            self.graphics_scene.addItem(line)
            
            label = QGraphicsTextItem(f"{depth} m")
            label.setPos(-370, depth/10 - 8)
            label.setDefaultTextColor(Qt.black)
            label.setZValue(101)
            self.graphics_scene.addItem(label)
    
    def create_coordinate_system(self):
        """ایجاد سیستم مختصات"""
        # محور Y (عمق)
        y_axis = QGraphicsLineItem(0, -100, 0, 350)
        y_axis.setPen(QPen(Qt.black, 3))
        y_axis.setZValue(1000)
        self.graphics_scene.addItem(y_axis)
        
        # فلش محور
        arrow = QGraphicsPolygonItem()
        arrow.setBrush(QBrush(Qt.black))
        arrow.setPolygon(QPolygonF([QPointF(0, -100), 
                                   QPointF(-5, -90), 
                                   QPointF(5, -90)]))
        arrow.setZValue(1001)
        self.graphics_scene.addItem(arrow)
        
        # برچسب محور
        axis_label = QGraphicsTextItem("Depth (m)")
        axis_label.setPos(-30, -120)
        axis_label.setDefaultTextColor(Qt.black)
        axis_label.setZValue(1002)
        self.graphics_scene.addItem(axis_label)
    
    def create_legend(self):
        """ایجاد Legend"""
        legend_items = [
            ("Casing", self.standard_colors['casing']),
            ("Cement", self.standard_colors['cement']),
            ("Open Hole", self.standard_colors['open_hole']),
            ("Tubing", self.standard_colors['tubing']),
            ("Packer", self.standard_colors['packer']),
            ("Perforation", self.standard_colors['perforation']),
            ("Reservoir", self.standard_colors['reservoir'])
        ]
        
        legend_x = 400
        legend_y = 50
        
        legend_bg = QGraphicsRectItem(legend_x - 10, legend_y - 10, 180, len(legend_items)*30 + 40)
        legend_bg.setBrush(QBrush(QColor(255, 255, 255, 220)))
        legend_bg.setPen(QPen(Qt.black, 1))
        legend_bg.setZValue(2000)
        self.graphics_scene.addItem(legend_bg)
        
        title = QGraphicsTextItem("LEGEND")
        title.setPos(legend_x, legend_y)
        title.setDefaultTextColor(Qt.darkBlue)
        title.setFont(QFont("Arial", 10, QFont.Bold))
        title.setZValue(2001)
        self.graphics_scene.addItem(title)
        
        for i, (text, color) in enumerate(legend_items):
            # رنگ
            color_box = QGraphicsRectItem(legend_x, legend_y + 30 + i*30, 20, 20)
            color_box.setBrush(QBrush(color))
            color_box.setPen(QPen(Qt.black, 1))
            color_box.setZValue(2001)
            self.graphics_scene.addItem(color_box)
            
            # متن
            label = QGraphicsTextItem(text)
            label.setPos(legend_x + 30, legend_y + 30 + i*30)
            label.setDefaultTextColor(Qt.black)
            label.setZValue(2001)
            self.graphics_scene.addItem(label)
    
    def create_scale_bar(self):
        """ایجاد Scale Bar"""
        scale_x = 400
        scale_y = 300
        
        scale_length = 100  # پیکسل‌ها
        actual_length = 1000  # متر (مقیاس 1:10)
        
        scale_bar = QGraphicsRectItem(scale_x, scale_y, scale_length, 10)
        scale_bar.setBrush(QBrush(Qt.black))
        scale_bar.setPen(QPen(Qt.black, 1))
        scale_bar.setZValue(2000)
        self.graphics_scene.addItem(scale_bar)
        
        # تقسیم‌بندی
        for i in range(0, 6):
            x = scale_x + i * (scale_length / 5)
            line = QGraphicsLineItem(x, scale_y, x, scale_y + 20)
            line.setPen(QPen(Qt.black, 1))
            line.setZValue(2001)
            self.graphics_scene.addItem(line)
            
            if i % 2 == 0:
                label = QGraphicsTextItem(f"{i * (actual_length / 5)}")
                label.setPos(x - 10, scale_y + 25)
                label.setDefaultTextColor(Qt.black)
                label.setZValue(2001)
                self.graphics_scene.addItem(label)
        
        # برچسب scale
        scale_label = QGraphicsTextItem(f"Scale: 1:10 (1 cm = {actual_length/100} m)")
        scale_label.setPos(scale_x, scale_y - 30)
        scale_label.setDefaultTextColor(Qt.darkBlue)
        scale_label.setZValue(2001)
        self.graphics_scene.addItem(scale_label)
    
    def update_grid(self):
        """آپدیت Grid"""
        grid_size = 50
        view_rect = self.graphics_view.mapToScene(self.graphics_view.viewport().rect()).boundingRect()
        
        path = QPainterPath()
        
        # خطوط عمودی
        x_start = int(view_rect.left() / grid_size) * grid_size
        x_end = int(view_rect.right() / grid_size) * grid_size
        
        for x in range(x_start, x_end + 1, grid_size):
            path.moveTo(x, view_rect.top())
            path.lineTo(x, view_rect.bottom())
        
        # خطوط افقی
        y_start = int(view_rect.top() / grid_size) * grid_size
        y_end = int(view_rect.bottom() / grid_size) * grid_size
        
        for y in range(y_start, y_end + 1, grid_size):
            path.moveTo(view_rect.left(), y)
            path.lineTo(view_rect.right(), y)
        
        if self.grid_item is None:
            # اگر وجود ندارد، جدید بساز و به صحنه اضافه کن
            self.grid_item = QGraphicsPathItem()
            self.grid_item.setZValue(-1000)
            self.graphics_scene.addItem(self.grid_item)
        
        # حالا مسیر را تنظیم کن
        self.grid_item.setPath(path)
        self.grid_item.setPen(QPen(QColor(200, 200, 200, 100), 0.5))
    
    def on_mouse_move(self, event):
        """مدیریت حرکت ماوس"""
        scene_pos = self.graphics_view.mapToScene(event.pos())
        if hasattr(self, 'coords_label'):
            self.coords_label.setText(f"X: {scene_pos.x():.2f}, Y: {scene_pos.y():.2f}")
        
        if self.is_panning:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            self.graphics_view.horizontalScrollBar().setValue(
                self.graphics_view.horizontalScrollBar().value() - delta.x())
            self.graphics_view.verticalScrollBar().setValue(
                self.graphics_view.verticalScrollBar().value() - delta.y())
        else:
            QGraphicsView.mouseMoveEvent(self.graphics_view, event)

    def on_mouse_press(self, event):
        """مدیریت کلیک ماوس"""
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self.current_tool == "pan"):
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.graphics_view.setCursor(Qt.ClosedHandCursor)
        else:
            QGraphicsView.mousePressEvent(self.graphics_view, event)

    def on_mouse_release(self, event):
        """مدیریت رها کردن ماوس"""
        if self.is_panning:
            self.is_panning = False
            self.graphics_view.setCursor(Qt.ArrowCursor)
        else:
            QGraphicsView.mouseReleaseEvent(self.graphics_view, event)

    def on_wheel_event(self, event):
        """مدیریت اسکرول ماوس برای زوم"""
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.zoom_factor *= factor
        
        self.graphics_view.scale(factor, factor)
        if hasattr(self, 'zoom_label'):
            self.zoom_label.setText(f"{self.zoom_factor*100:.0f}%")
        
        self.update_grid()
    def on_selection_changed(self):
        """مدیریت تغییر انتخاب"""
        selected_items = self.graphics_scene.selectedItems()
        self.selected_label.setText(f"Selected: {len(selected_items)} items")
        
        if selected_items:
            self.update_properties_inspector(selected_items[0])
    
    def on_layer_changed(self, item):
        """مدیریت تغییر لایه"""
        layer_name = item.text()
        visible = item.checkState() == Qt.Checked
        
        # اعمال تغییرات بر روی عناصر لایه
        for element in self.schematic_elements:
            if element.get('layer') == layer_name:
                element['item'].setVisible(visible)
    
    def on_element_double_clicked(self, item):
        """دابل کلیک روی عنصر برای درج"""
        element_type = item.data(Qt.UserRole)
        self.set_tool(element_type)
    
    def set_tool(self, tool_id):
        self.current_tool = tool_id
        
        # تغییر cursor - استفاده از cursor استاندارد Qt
        cursors = {
            "select": Qt.ArrowCursor,
            "line": Qt.CrossCursor,
            "rectangle": Qt.CrossCursor,
            "ellipse": Qt.CrossCursor,
            "casing": Qt.CrossCursor,  # بجای آیکن سفارشی
            "bit": Qt.CrossCursor,
            "packer": Qt.CrossCursor,
            "text": Qt.IBeamCursor,
            "chart": Qt.CrossCursor,
            "pan": Qt.OpenHandCursor
        }
        
        cursor = cursors.get(tool_id, Qt.ArrowCursor)
        self.graphics_view.setCursor(cursor)
    def set_display_mode(self, mode):
        """تنظیم حالت نمایش"""
        if mode == "colors":
            # حالت رنگی
            for item in self.graphics_scene.items():
                if hasattr(item, 'original_brush'):
                    item.setBrush(item.original_brush)
        elif mode == "grayscale":
            # حالت خاکستری
            for item in self.graphics_scene.items():
                if isinstance(item, QAbstractGraphicsShapeItem):
                    color = item.brush().color()
                    gray = qGray(color.rgb())
                    item.setBrush(QBrush(QColor(gray, gray, gray)))
        elif mode == "wireframe":
            # حالت wireframe
            for item in self.graphics_scene.items():
                if isinstance(item, QAbstractGraphicsShapeItem):
                    item.setBrush(Qt.NoBrush)
                    item.setPen(QPen(Qt.black, 1))
    
    def zoom_in(self):
        """زوم این"""
        self.graphics_view.scale(1.25, 1.25)
        self.zoom_factor *= 1.25
        self.zoom_label.setText(f"{self.zoom_factor*100:.0f}%")
        self.update_grid()
    
    def zoom_out(self):
        """زوم اوت"""
        self.graphics_view.scale(0.8, 0.8)
        self.zoom_factor *= 0.8
        self.zoom_label.setText(f"{self.zoom_factor*100:.0f}%")
        self.update_grid()
    
    def zoom_reset(self):
        """ریست زوم"""
        self.graphics_view.resetTransform()
        self.zoom_factor = 1.0
        self.zoom_label.setText("100%")
        self.update_grid()
    
    def fit_to_view(self):
        """تنظیم View برای نمایش تمام محتوا"""
        self.graphics_view.fitInView(self.graphics_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.update_grid()
    
    def toggle_grid(self):
        """تغییر وضعیت Grid"""
        visible = not self.grid_item.isVisible()
        self.grid_item.setVisible(visible)
    
    def toggle_snap(self):
        """تغییر وضعیت Snap"""
        pass  # پیاده‌سازی snap to grid
    
    def toggle_layer_visibility(self, layer_type):
        """تغییر وضعیت نمایش لایه"""
        pass  # پیاده‌سازی نمایش/مخفی کردن لایه
    
    def auto_generate_schematic(self):
        """تولید خودکار شماتیک از داده‌های چاه"""
        if not self.current_well:
            QMessageBox.warning(self, "Warning", "Please select a well first")
            return
        
        try:
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            
            # شبیه‌سازی بارگیری داده‌ها
            for i in range(0, 101, 10):
                QTimer.singleShot(i*50, lambda v=i: self.progress_bar.setValue(v))
            
            QTimer.singleShot(600, self._finish_auto_generate)
            
        except Exception as e:
            logger.error(f"Auto generate error: {e}")
    
    def _finish_auto_generate(self):
        """پایان تولید خودکار"""
        self.progress_bar.hide()
        
        
        self.status_bar.showMessage("Schematic auto-generated successfully", 3000)
    
    def update_properties_inspector(self, item):
        """آپدیت Properties Inspector برای آیتم انتخاب شده"""
        self.properties_table.setRowCount(0)
        
        properties = [
            ("Type", type(item).__name__),
            ("Position", f"({item.pos().x():.2f}, {item.pos().y():.2f})"),
            ("Z-Value", str(item.zValue())),
            ("Visible", str(item.isVisible())),
            ("Selectable", str(item.flags() & QGraphicsItem.ItemIsSelectable))
        ]
        
        # ویژگی‌های خاص بر اساس نوع
        if isinstance(item, QGraphicsRectItem):
            rect = item.rect()
            properties.extend([
                ("Width", f"{rect.width():.2f}"),
                ("Height", f"{rect.height():.2f}"),
                ("Area", f"{rect.width() * rect.height():.2f}")
            ])
        
        self.properties_table.setRowCount(len(properties))
        
        for i, (name, value) in enumerate(properties):
            name_item = QTableWidgetItem(name)
            value_item = QTableWidgetItem(str(value))
            
            self.properties_table.setItem(i, 0, name_item)
            self.properties_table.setItem(i, 1, value_item)
    
    def apply_properties(self):
        """اعمال تغییرات Properties"""
        # پیاده‌سازی تغییرات Properties
        pass
    
    def reset_properties(self):
        """ریست Properties"""
        self.properties_table.setRowCount(0)
    
    def add_new_layer(self):
        """اضافه کردن لایه جدید"""
        name, ok = QInputDialog.getText(self, "New Layer", "Enter layer name:")
        if ok and name:
            item = QListWidgetItem(name)
            item.setCheckState(Qt.Checked)
            self.layers_list.addItem(item)
    
    def delete_layer(self):
        """حذف لایه"""
        current = self.layers_list.currentRow()
        if current >= 0:
            self.layers_list.takeItem(current)
    
    def move_layer_up(self):
        """حرکت لایه به بالا"""
        current = self.layers_list.currentRow()
        if current > 0:
            item = self.layers_list.takeItem(current)
            self.layers_list.insertItem(current - 1, item)
            self.layers_list.setCurrentRow(current - 1)
    
    def move_layer_down(self):
        """حرکت لایه به پایین"""
        current = self.layers_list.currentRow()
        if current < self.layers_list.count() - 1:
            item = self.layers_list.takeItem(current)
            self.layers_list.insertItem(current + 1, item)
            self.layers_list.setCurrentRow(current + 1)
    
    def update_schematic_scale(self):
        """آپدیت مقیاس شماتیک"""
        scale_text = self.vertical_scale.currentText()
        if scale_text == "Custom":
            scale, ok = QInputDialog.getDouble(self, "Custom Scale", 
                                             "Enter scale (e.g., 100 for 1:100):", 
                                             100, 10, 10000, 0)
            if ok:
                scale_text = f"1:{scale}"
        
        self.scale_label.setText(f"Scale: {scale_text}")
    
    def convert_units(self):
        """تبدیل واحدها"""
        units = self.display_units.currentText()
        if units == "Imperial":
            # تبدیل متر به فوت
            pass
        else:
            # تبدیل فوت به متر
            pass
    
    def apply_parameters(self):
        """اعمال پارامترها"""
        depth = self.well_depth.value()
        hole_size = self.hole_size.value()
        
        # آپدیت شماتیک بر اساس پارامترهای جدید
        self.status_bar.showMessage(f"Parameters applied: Depth={depth}m, Hole={hole_size}\"", 3000)
    
    def add_formation_layer(self):
        """اضافه کردن لایه زمین‌شناسی"""
        dialog = FormationLayerDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            row = self.formation_table.rowCount()
            self.formation_table.insertRow(row)
            
            self.formation_table.setItem(row, 0, QTableWidgetItem(str(data['depth'])))
            self.formation_table.setItem(row, 1, QTableWidgetItem(str(data['thickness'])))
            self.formation_table.setItem(row, 2, QTableWidgetItem(data['type']))
            
            color_item = QTableWidgetItem()
            color_item.setBackground(data['color'])
            self.formation_table.setItem(row, 3, color_item)
            
            # دکمه حذف
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda: self.formation_table.removeRow(row))
            self.formation_table.setCellWidget(row, 4, delete_btn)
    
    def import_las_file(self):
        """وارد کردن فایل LAS"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import LAS File", "", 
            "LAS Files (*.las *.LAS);;All Files (*.*)"
        )
        
        if file_name:
            try:
                # در اینجا فایل LAS خوانده می‌شود
                # برای نمونه فقط یک پیام نمایش می‌دهیم
                QMessageBox.information(self, "Import LAS", 
                                      f"LAS file '{os.path.basename(file_name)}' will be processed")
                
                # شبیه‌سازی پردازش
                self.progress_bar.show()
                for i in range(0, 101, 10):
                    QTimer.singleShot(i*100, lambda v=i: self.progress_bar.setValue(v))
                
                QTimer.singleShot(1100, lambda: self.progress_bar.hide())
                
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import LAS: {str(e)}")
    
    def import_cad(self):
        """وارد کردن از CAD"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import CAD File", "",
            "DXF Files (*.dxf);;DWG Files (*.dwg);;All Files (*.*)"
        )
        
        if file_name:
            QMessageBox.information(self, "Import CAD", 
                                  "CAD import feature requires additional libraries")
    
    def export_drawing(self):
        """اکسپورت به فرمت‌های مختلف"""
        formats = ["PDF", "DXF", "SVG", "PNG", "JPG"]
        format_choice, ok = QInputDialog.getItem(
            self, "Export Format", "Select format:", formats, 0, False
        )
        
        if ok and format_choice:
            if format_choice == "PDF":
                self.export_to_pdf()
            elif format_choice == "DXF":
                self.export_to_dxf()
            elif format_choice == "SVG":
                self.export_to_svg()
            else:
                self.export_image(format_choice.lower())
    
    def export_to_pdf(self):
        """اکسپورت به PDF"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "wellbore_schematic.pdf", "PDF Files (*.pdf)"
        )
        
        if file_name:
            try:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_name)
                printer.setPageSize(QPrinter.A4)
                printer.setPageOrientation(QPrinter.Landscape)
                
                painter = QPainter(printer)
                painter.setRenderHint(QPainter.Antialiasing)
                
                self.graphics_scene.render(painter)
                painter.end()
                
                QMessageBox.information(self, "Success", f"PDF exported to {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")
    
    def export_to_dxf(self):
        """اکسپورت به DXF"""
        QMessageBox.information(self, "Export DXF", 
                              "DXF export requires ezdxf library")
    
    def export_to_svg(self):
        """اکسپورت به SVG"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export SVG", "wellbore_schematic.svg", "SVG Files (*.svg)"
        )
        
        if file_name:
            try:
                svg_generator = QSvgGenerator()
                svg_generator.setFileName(file_name)
                svg_generator.setSize(self.graphics_view.size())
                svg_generator.setViewBox(QRectF(self.graphics_scene.sceneRect()))
                
                painter = QPainter(svg_generator)
                self.graphics_scene.render(painter)
                painter.end()
                
                QMessageBox.information(self, "Success", f"SVG exported to {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export SVG: {str(e)}")
    
    def export_image(self, format="png"):
        """اکسپورت به تصویر"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, f"Export {format.upper()}", 
            f"wellbore_schematic.{format}",
            f"{format.upper()} Files (*.{format})"
        )
        
        if file_name:
            image = QImage(self.graphics_scene.sceneRect().size().toSize(), 
                         QImage.Format_ARGB32)
            image.fill(Qt.white)
            
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            self.graphics_scene.render(painter)
            painter.end()
            
            image.save(file_name)
            QMessageBox.information(self, "Success", f"Image exported to {file_name}")
    
    def print_schematic(self):
        """چاپ شماتیک"""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # تنظیم مقیاس مناسب برای چاپ
            rect = self.graphics_scene.sceneRect()
            x_scale = printer.pageRect().width() / rect.width()
            y_scale = printer.pageRect().height() / rect.height()
            scale = min(x_scale, y_scale) * 0.9
            
            painter.scale(scale, scale)
            painter.translate(-rect.left(), -rect.top())
            
            self.graphics_scene.render(painter)
            painter.end()
    
    def new_schematic(self):
        """شماتیک جدید"""
        reply = QMessageBox.question(
            self, "New Schematic",
            "Create new schematic? Current changes will be lost.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.graphics_scene.clear()
            self.schematic_elements.clear()

    def zoom_out(self):
        """زوم اوت"""
        self.graphics_view.scale(0.8, 0.8)
        self.zoom_factor *= 0.8
        if hasattr(self, 'zoom_label'):
            self.zoom_label.setText(f"{self.zoom_factor*100:.0f}%")
        self.update_grid()

    def zoom_in(self):
        """زوم این"""
        self.graphics_view.scale(1.25, 1.25)
        self.zoom_factor *= 1.25
        if hasattr(self, 'zoom_label'):
            self.zoom_label.setText(f"{self.zoom_factor*100:.0f}%")
        self.update_grid()

    def fit_to_view(self):
        """تنظیم View برای نمایش تمام محتوا"""
        self.graphics_view.fitInView(self.graphics_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.update_grid()

    def toggle_grid(self):
        """تغییر وضعیت Grid"""
        if hasattr(self, 'grid_item'):
            visible = not self.grid_item.isVisible()
            self.grid_item.setVisible(visible)

    def toggle_snap(self):
        """تغییر وضعیت Snap"""
        # پیاده‌سازی snap to grid
        logger.info("Toggle snap to grid")

    def toggle_layer_visibility(self, layer_type):
        """تغییر وضعیت نمایش لایه"""
        logger.info(f"Toggle {layer_type} visibility")

    def update_schematic_scale(self):
        """آپدیت مقیاس شماتیک"""
        if hasattr(self, 'vertical_scale') and hasattr(self, 'scale_label'):
            scale_text = self.vertical_scale.currentText()
            if scale_text == "Custom":
                scale, ok = QInputDialog.getDouble(self, "Custom Scale", 
                                                 "Enter scale (e.g., 100 for 1:100):", 
                                                 100, 10, 10000, 0)
                if ok:
                    scale_text = f"1:{scale}"
            
            self.scale_label.setText(f"Scale: {scale_text}")

    def update_hole_geometry(self):
        """به‌روزرسانی هندسه چاه"""
        if hasattr(self, 'hole_size'):
            logger.info(f"Hole size updated: {self.hole_size.value()}")

    def convert_units(self):
        """تبدیل واحدها"""
        if hasattr(self, 'display_units'):
            units = self.display_units.currentText()
            logger.info(f"Convert units to: {units}")

    def update_formation_layers(self):
        """به‌روزرسانی لایه‌های زمین‌شناسی"""
        if hasattr(self, 'formation_table'):
            logger.info("Formation layers updated")

    def update_status(self):
        """آپدیت وضعیت"""
        # آپدیت memory usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            if hasattr(self, 'memory_label'):
                self.memory_label.setText(f"Memory: {memory_mb:.1f} MB")
        except ImportError:
            pass
        
        # آپدیت FPS
        if hasattr(self, 'fps_label'):
            self.fps_label.setText("FPS: 60")
    
    def save_schematic(self):
        """ذخیره شماتیک"""
        if not self.current_well:
            QMessageBox.warning(self, "Warning", "Please select a well first")
            return
        
        try:
            # ذخیره به عنوان تصویر
            image = QImage(self.graphics_scene.sceneRect().size().toSize(), 
                         QImage.Format_ARGB32)
            image.fill(Qt.white)
            
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            self.graphics_scene.render(painter)
            painter.end()
            
            # تبدیل به بایت‌ها
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            image.save(buffer, "PNG")
            
            # ذخیره در دیتابیس
            if self.db_manager:
                schematic_data = {
                    'well_id': self.current_well,
                    'schematic_date': datetime.now().date(),
                    'image_data': byte_array.data(),
                    'image_format': 'PNG',
                    'parameters': {
                        'well_depth': self.well_depth.value(),
                        'hole_size': self.hole_size.value(),
                        'vertical_scale': self.vertical_scale.currentText()
                    }
                }
                
                result = self.db_manager.save_wellbore_schematic(schematic_data)
                if result:
                    QMessageBox.information(self, "Success", 
                                          "Schematic saved successfully")
                    return True
            
            return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
            return False
    
    def load_schematic(self):
        """بارگذاری شماتیک"""
        if not self.current_well:
            QMessageBox.warning(self, "Warning", "Please select a well first")
            return
        
        try:
            if self.db_manager:
                data = self.db_manager.get_wellbore_schematic(self.current_well)
                
                if data and data.get('image_data'):
                    self.graphics_scene.clear()
                    
                    byte_array = QByteArray(data['image_data'])
                    pixmap = QPixmap()
                    pixmap.loadFromData(byte_array, data.get('image_format', 'PNG'))
                    
                    if not pixmap.isNull():
                        pixmap_item = QGraphicsPixmapItem(pixmap)
                        self.graphics_scene.addItem(pixmap_item)
                        
                        self.graphics_view.fitInView(pixmap_item, Qt.KeepAspectRatio)
                        
                        # بارگذاری پارامترها
                        params = data.get('parameters', {})
                        if params:
                            self.well_depth.setValue(params.get('well_depth', 3000))
                            self.hole_size.setValue(params.get('hole_size', 8.5))
                            
                            scale = params.get('vertical_scale', '1:100')
                            index = self.vertical_scale.findText(scale)
                            if index >= 0:
                                self.vertical_scale.setCurrentIndex(index)
                        
                        QMessageBox.information(self, "Success", 
                                              "Schematic loaded successfully")
                        return True
            
            QMessageBox.information(self, "Info", "No schematic found for this well")
            return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")
            return False
    
    def clear_schematic(self):
        """پاک کردن شماتیک"""
        reply = QMessageBox.question(
            self, "Clear Schematic",
            "Clear entire schematic? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.graphics_scene.clear()
            self.schematic_elements.clear()
            self.update_grid()
    
    def delete_selected(self):
        """حذف آیتم‌های انتخاب شده"""
        for item in self.graphics_scene.selectedItems():
            self.graphics_scene.removeItem(item)
    
    def clear_selection(self):
        """پاک کردن انتخاب"""
        self.graphics_scene.clearSelection()
    
    def show_help(self):
        """نمایش راهنما"""
        help_text = """
        🎯 Professional Wellbore Schematic Editor
        
        🔧 MAIN TOOLS:
        • Select (S): Select and move objects
        • Line (L): Draw lines
        • Rectangle (R): Draw rectangles
        • Ellipse (E): Draw ellipses
        • Casing (C): Draw casing strings
        • Bit (B): Add drill bit
        • Packer (P): Add packer
        • Text (T): Add text labels
        • Chart (H): Add charts and graphs
        
        🎨 DISPLAY MODES:
        • Colors: Full color display
        • Grayscale: Grayscale display
        • Wireframe: Wireframe display
        
        🚀 QUICK ACTIONS:
        • Space: Toggle pan mode
        • Mouse Wheel: Zoom in/out
        • Middle Click: Pan
        • Delete: Delete selected
        • F: Fit to view
        • G: Toggle grid
        • Z: Undo
        • Y: Redo
        
        📊 DATA INTEGRATION:
        • Auto-generate from well data
        • Import from LAS files
        • Import from CAD (DXF/DWG)
        • Export to PDF/DXF/SVG/Image
        
        🌐 REAL-TIME FEATURES:
        • Live coordinates display
        • Properties inspector
        • Layer management
        • Dynamic grid
        • Snap to grid
        • Multiple undo/redo
        """
        
        QMessageBox.information(self, "Help - Professional Schematic Editor", help_text)
    
    def refresh_view(self):
        """رفرش View"""
        self.graphics_view.viewport().update()
        self.update_grid()
    
    def toggle_fullscreen(self):
        """تغییر حالت تمام‌صفحه"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def toggle_pan_mode(self):
        """تغییر حالت Pan"""
        self.current_tool = "pan" if self.current_tool != "pan" else "select"
        
        if self.current_tool == "pan":
            self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
            self.graphics_view.setCursor(Qt.OpenHandCursor)
        else:
            self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
            self.graphics_view.setCursor(Qt.ArrowCursor)
    
    def undo(self):
        """Undo"""
        # پیاده‌سازی undo stack
        pass
    
    def redo(self):
        """Redo"""
        # پیاده‌سازی redo stack
        pass
    
    def update_status(self):
        """آپدیت وضعیت"""
        # آپدیت memory usage
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_label.setText(f"Memory: {memory_mb:.1f} MB")
        
        # آپدیت FPS (شبیه‌سازی)
        self.fps_label.setText(f"FPS: 60")
    
    def set_current_well(self, well_id, well_data=None):
        """تنظیم چاه جاری"""
        self.current_well = well_id
        self.well_data = well_data or {}
        
        if well_id:
            self.status_bar.showMessage(f"Current well: {well_id} - Loaded", 3000)
            # بارگذاری خودکار شماتیک اگر وجود دارد
            QTimer.singleShot(500, self.load_schematic)
        else:
            self.status_bar.showMessage("No well selected")


# ==================== Enhanced Graphics View ====================
class EnhancedGraphicsView(QGraphicsView):
    """View گرافیکی پیشرفته با قابلیت‌های بیشتر"""
    
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.parent_tab = parent
        
        # تنظیمات پیشرفته
        self.setOptimizationFlags(
            QGraphicsView.DontAdjustForAntialiasing |
            QGraphicsView.DontSavePainterState
        )
        
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # فعال کردن OpenGL برای performance بهتر
        try:
            from PySide6.QtOpenGLWidgets import QOpenGLWidget
            gl_widget = QOpenGLWidget()
            gl_widget.setFormat(QSurfaceFormat.defaultFormat())
            self.setViewport(gl_widget)
            logger.info("OpenGL acceleration enabled")
        except ImportError:
            logger.warning("OpenGL not available, using standard viewport")
    
    def drawBackground(self, painter, rect):
        """رسم پس‌زمینه سفارشی"""
        super().drawBackground(painter, rect)
        
        # اضافه کردن gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(240, 240, 245))
        gradient.setColorAt(1, QColor(230, 230, 235))
        painter.fillRect(rect, gradient)


# ==================== Formation Layer Dialog ====================
class FormationLayerDialog(QDialog):
    """دیالوگ برای اضافه کردن لایه زمین‌شناسی"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Formation Layer")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(0, 20000)
        self.depth_spin.setSuffix(" m")
        form_layout.addRow("Top Depth:", self.depth_spin)
        
        self.thickness_spin = QDoubleSpinBox()
        self.thickness_spin.setRange(1, 5000)
        self.thickness_spin.setSuffix(" m")
        form_layout.addRow("Thickness:", self.thickness_spin)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Shale", "Sandstone", "Limestone", "Dolomite", 
            "Salt", "Anhydrite", "Coal", "Reservoir", "Other"
        ])
        form_layout.addRow("Formation Type:", self.type_combo)
        
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(40, 40)
        self.color_btn.setStyleSheet("background-color: #8B4513;")
        self.color_btn.clicked.connect(self.choose_color)
        form_layout.addRow("Color:", self.color_btn)
        
        self.color = QColor(139, 69, 19)  # قهوه‌ای پیش‌فرض
        
        layout.addLayout(form_layout)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def choose_color(self):
        """انتخاب رنگ"""
        color = QColorDialog.getColor(self.color, self, "Choose Formation Color")
        if color.isValid():
            self.color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")
    
    def get_data(self):
        """دریافت داده‌های وارد شده"""
        return {
            'depth': self.depth_spin.value(),
            'thickness': self.thickness_spin.value(),
            'type': self.type_combo.currentText(),
            'color': self.color
        }