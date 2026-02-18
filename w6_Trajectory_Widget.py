"""
Trajectory Widget - ابزار مدیریت تراژکتوری چاه با قابلیت‌های پیشرفته
"""

import os
import csv
import math
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import pyqtgraph as pg
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

# Import database models
from core.database import (
    Well, Section, TripSheetEntry, SurveyPoint, 
    TrajectoryCalculation, TrajectoryPlot, DatabaseManager
)

# Import managers
from core.managers import (
    StatusBarManager, TableManager, ExportManager,
    TableButtonManager, setup_widget_with_managers
)

logger = logging.getLogger(__name__)

# ==================== Base Widget ====================
class DrillWidgetBase(QWidget):
    """ویجت پایه برای تمامی ابزارهای حفاری"""
    
    def __init__(self, widget_name: str, db_manager: DatabaseManager = None):
        super().__init__()
        self.widget_name = widget_name
        self.db_manager = db_manager
        self.status_manager = StatusBarManager()
        self.status_manager.register_widget(widget_name, self)
        
    def show_message(self, message: str, timeout: int = 3000):
        """نمایش پیام در status bar"""
        self.status_manager.show_message(self.widget_name, message, timeout)
    
    def show_success(self, message: str):
        """نمایش پیام موفقیت"""
        self.status_manager.show_success(self.widget_name, message)
    
    def show_error(self, message: str):
        """نمایش پیام خطا"""
        self.status_manager.show_error(self.widget_name, message)
    
    def show_progress(self, message: str):
        """نمایش پیام پیشرفت"""
        self.status_manager.show_progress(self.widget_name, message)
    
    def clear_message(self):
        """پاک کردن پیام"""
        self.status_manager.clear_message(self.widget_name)

# ==================== Trip Sheet Tab ====================
class TripSheetTab(QWidget):
    """تب Trip Sheet برای مدیریت سفرهای مته"""
    
    def __init__(self, db_manager: DatabaseManager = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_well_id = None
        self.current_section_id = None
        self.table_manager = None
        self.init_ui()
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ایجاد جدول Trip Sheet
        self.trip_table = QTableWidget(0, 9)
        self.trip_table.setHorizontalHeaderLabels([
            "ID", "Time", "Activity", "Depth (m)", "Cum. Trip (m)", 
            "Duration (hr)", "Remarks", "Supervisor", "Verified"
        ])
        
        # مخفی کردن ستون ID
        self.trip_table.hideColumn(0)
        
        # تنظیم Table Manager
        self.table_manager = TableManager(self.trip_table, self)
        
        # تنظیم Stretch برای ستون‌ها
        self.trip_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.trip_table)
        
        # دکمه‌های عملیاتی
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add Row")
        self.add_btn.setToolTip("Add new trip sheet entry")
        self.add_btn.clicked.connect(self.add_row)
        
        self.delete_btn = QPushButton("❌ Delete Row")
        self.delete_btn.setToolTip("Delete selected row")
        self.delete_btn.clicked.connect(self.delete_row)
        
        self.calculate_btn = QPushButton("🔄 Calculate Cumulative")
        self.calculate_btn.setToolTip("Calculate cumulative trip distances")
        self.calculate_btn.clicked.connect(self.calculate_cumulative)
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setToolTip("Save trip sheet data to database")
        self.save_btn.clicked.connect(self.save_data)
        
        self.load_btn = QPushButton("📂 Load")
        self.load_btn.setToolTip("Load trip sheet data from database")
        self.load_btn.clicked.connect(self.load_data)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setToolTip("Clear all data from table")
        self.clear_btn.clicked.connect(self.clear_table)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.calculate_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # تنظیم Widget
        self.setLayout(layout)
        
        # نمونه داده اولیه
        self.add_sample_data()
    
    def set_current_well(self, well_id: int, section_id: int = None):
        """تنظیم چاه و سکشن جاری"""
        self.current_well_id = well_id
        self.current_section_id = section_id
        if well_id:
            self.load_data()
    
    def add_sample_data(self):
        """اضافه کردن داده‌های نمونه"""
        sample_data = [
            ["08:00", "Start trip out", "1500", "0", "1.0", "Begin POOH", "John Doe", True],
            ["09:00", "POOH", "1400", "100", "2.0", "Tripping out 5 stands", "John Doe", True],
            ["11:00", "Break connection", "1350", "150", "0.5", "Connection break", "John Doe", True],
            ["11:30", "Continue POOH", "1300", "200", "1.5", "Continue tripping", "John Doe", False]
        ]
        
        for data in sample_data:
            self.add_row(data)
    
    def add_row(self, data=None):
        """اضافه کردن سطر جدید"""
        if data is None:
            data = [
                datetime.now().strftime("%H:%M"),
                "New Activity",
                "0.0",
                "0.0",
                "0.0",
                "",
                "",
                False
            ]
        
        row = self.table_manager.add_row(data)
        
        # ستون Verified (checkbox)
        if row >= 0:
            checkbox = QCheckBox()
            checkbox.setChecked(bool(data[7]) if len(data) > 7 else False)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            
            self.trip_table.setCellWidget(row, 8, checkbox_widget)
        
        return row
    
    def delete_row(self):
        """حذف سطر انتخاب شده"""
        if self.trip_table.currentRow() >= 0:
            self.table_manager.delete_row()
    
    def calculate_cumulative(self):
        """محاسبه مقدار تجمعی Trip"""
        try:
            cumulative = 0.0
            for row in range(self.trip_table.rowCount()):
                # ستون Depth (index 3)
                depth_item = self.trip_table.item(row, 3)
                if depth_item and depth_item.text():
                    depth = float(depth_item.text())
                    cumulative += depth
                    
                    # Update cumulative column (index 4)
                    cum_item = QTableWidgetItem(f"{cumulative:.2f}")
                    cum_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.trip_table.setItem(row, 4, cum_item)
            
            QMessageBox.information(
                self, "Success", 
                f"Cumulative calculation completed\nTotal: {cumulative:.2f} m"
            )
            
        except ValueError as e:
            QMessageBox.warning(self, "Error", f"Invalid depth values: {str(e)}")
    
    def save_data(self):
        """ذخیره داده‌ها در دیتابیس"""
        if not self.current_well_id:
            QMessageBox.warning(self, "Warning", "Please select a well first")
            return False
        
        try:
            entries = []
            for row in range(self.trip_table.rowCount()):
                # Get ID if exists
                id_item = self.trip_table.item(row, 0)
                entry_id = int(id_item.text()) if id_item and id_item.text().isdigit() else None
                
                # Collect data
                time_str = self.trip_table.item(row, 1).text() if self.trip_table.item(row, 1) else ""
                activity = self.trip_table.item(row, 2).text() if self.trip_table.item(row, 2) else ""
                depth = self.trip_table.item(row, 3).text() if self.trip_table.item(row, 3) else "0"
                cum_trip = self.trip_table.item(row, 4).text() if self.trip_table.item(row, 4) else "0"
                duration = self.trip_table.item(row, 5).text() if self.trip_table.item(row, 5) else "0"
                remarks = self.trip_table.item(row, 6).text() if self.trip_table.item(row, 6) else ""
                supervisor = self.trip_table.item(row, 7).text() if self.trip_table.item(row, 7) else ""
                
                # Get checkbox value
                checkbox_widget = self.trip_table.cellWidget(row, 8)
                verified = checkbox_widget.findChild(QCheckBox).isChecked() if checkbox_widget else False
                
                # Convert time string to time object
                try:
                    time_obj = datetime.strptime(time_str, "%H:%M").time()
                except:
                    time_obj = datetime.now().time()
                
                entry_data = {
                    'id': entry_id,
                    'well_id': self.current_well_id,
                    'section_id': self.current_section_id,
                    'time': time_obj,
                    'activity': activity,
                    'depth': float(depth) if depth else 0.0,
                    'cum_trip': float(cum_trip) if cum_trip else 0.0,
                    'duration': float(duration) if duration else 0.0,
                    'remarks': remarks,
                    'supervisor': supervisor,
                    'verified': verified
                }
                
                entries.append(entry_data)
            
            # Save to database
            if self.db_manager and entries:
                success = self.db_manager.save_trip_sheet_entries(entries)
                if success:
                    QMessageBox.information(self, "Success", f"Saved {len(entries)} entries to database")
                    # Reload to get IDs
                    self.load_data()
                    return True
                else:
                    QMessageBox.warning(self, "Error", "Failed to save to database")
                    return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")
            logger.error(f"Error saving trip sheet data: {e}")
        
        return False
    
    def load_data(self):
        """بارگذاری داده‌ها از دیتابیس"""
        if not self.current_well_id:
            return False
        
        try:
            self.clear_table()
            
            if self.db_manager:
                entries = self.db_manager.load_trip_sheet_entries(
                    well_id=self.current_well_id,
                    section_id=self.current_section_id
                )
                
                for entry in entries:
                    row = self.trip_table.rowCount()
                    self.trip_table.insertRow(row)
                    
                    # Fill data
                    self.trip_table.setItem(row, 0, QTableWidgetItem(str(entry['id'])))
                    self.trip_table.setItem(row, 1, QTableWidgetItem(entry['time']))
                    self.trip_table.setItem(row, 2, QTableWidgetItem(entry['activity']))
                    self.trip_table.setItem(row, 3, QTableWidgetItem(str(entry['depth'])))
                    self.trip_table.setItem(row, 4, QTableWidgetItem(str(entry['cum_trip'])))
                    self.trip_table.setItem(row, 5, QTableWidgetItem(str(entry['duration'])))
                    self.trip_table.setItem(row, 6, QTableWidgetItem(entry['remarks']))
                    self.trip_table.setItem(row, 7, QTableWidgetItem(entry['supervisor']))
                    
                    # Checkbox
                    checkbox = QCheckBox()
                    checkbox.setChecked(entry['verified'])
                    checkbox_widget = QWidget()
                    checkbox_layout = QHBoxLayout(checkbox_widget)
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.setAlignment(Qt.AlignCenter)
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    self.trip_table.setCellWidget(row, 8, checkbox_widget)
                
                logger.info(f"Loaded {len(entries)} trip sheet entries")
                return True
            
        except Exception as e:
            logger.error(f"Error loading trip sheet data: {e}")
        
        return False
    
    def clear_table(self):
        """پاک کردن تمامی داده‌های جدول"""
        self.trip_table.setRowCount(0)
    
    def export_data(self):
        """اکسپورت داده‌ها"""
        export_manager = ExportManager(self)
        export_manager.export_table_with_dialog(self.trip_table, "trip_sheet")
    
    def get_table_data(self) -> List[Dict]:
        """دریافت داده‌های جدول"""
        data = []
        for row in range(self.trip_table.rowCount()):
            row_data = {}
            for col in range(self.trip_table.columnCount()):
                if col == 8:  # Checkbox column
                    widget = self.trip_table.cellWidget(row, col)
                    if widget:
                        checkbox = widget.findChild(QCheckBox)
                        row_data['verified'] = checkbox.isChecked() if checkbox else False
                else:
                    item = self.trip_table.item(row, col)
                    if item:
                        row_data[f'col_{col}'] = item.text()
            data.append(row_data)
        return data

# ==================== Survey Data Tab ====================
class SurveyDataTab(QWidget):
    """تب داده‌های سروی"""
    
    def __init__(self, db_manager: DatabaseManager = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_well_id = None
        self.current_section_id = None
        self.current_calculation_id = None
        self.table_manager = None
        self.init_ui()
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ایجاد جدول Survey Data
        self.survey_table = QTableWidget(0, 12)
        self.survey_table.setHorizontalHeaderLabels([
            "ID", "MD (m)", "Inc (°)", "Azi (°)", "TVD (m)", "North (m)", "East (m)", 
            "VS (m)", "HD (m)", "DLS (°/30m)", "Tool", "Remarks"
        ])
        
        # مخفی کردن ستون ID
        self.survey_table.hideColumn(0)
        
        # تنظیم Table Manager
        self.table_manager = TableManager(self.survey_table, self)
        
        # تنظیم Stretch برای ستون‌ها
        self.survey_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.survey_table)
        
        # دکمه‌های عملیاتی
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add Row")
        self.add_btn.setToolTip("Add new survey point")
        self.add_btn.clicked.connect(self.add_row)
        
        self.delete_btn = QPushButton("❌ Delete Row")
        self.delete_btn.setToolTip("Delete selected row")
        self.delete_btn.clicked.connect(self.delete_row)
        
        self.import_btn = QPushButton("📂 Import")
        self.import_btn.setToolTip("Import survey data from CSV file")
        self.import_btn.clicked.connect(self.import_data)
        
        self.calculate_btn = QPushButton("🔄 Calculate")
        self.calculate_btn.setToolTip("Calculate trajectory using Minimum Curvature method")
        self.calculate_btn.clicked.connect(self.calculate_trajectory)
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setToolTip("Save survey data to database")
        self.save_btn.clicked.connect(self.save_data)
        
        self.load_btn = QPushButton("📂 Load")
        self.load_btn.setToolTip("Load survey data from database")
        self.load_btn.clicked.connect(self.load_data)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setToolTip("Clear all data from table")
        self.clear_btn.clicked.connect(self.clear_table)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.setToolTip("Export data to file")
        self.export_btn.clicked.connect(self.export_data)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.calculate_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # تنظیم Widget
        self.setLayout(layout)
        
        # نمونه داده اولیه
        self.add_sample_data()
    
    def set_current_well(self, well_id: int, section_id: int = None, calculation_id: int = None):
        """تنظیم چاه، سکشن و محاسبه جاری"""
        self.current_well_id = well_id
        self.current_section_id = section_id
        self.current_calculation_id = calculation_id
        if well_id:
            self.load_data()
    
    def add_sample_data(self):
        """اضافه کردن داده‌های نمونه"""
        sample_data = [
            ["1000", "5.2", "45.3", "999.8", "50.2", "30.5", "100.0", "100.0", "1.5", "MWD", "Survey point"],
            ["1100", "6.5", "48.2", "1099.5", "65.8", "45.2", "120.5", "120.0", "2.1", "MWD", "Survey point"],
            ["1200", "8.1", "52.4", "1198.9", "85.3", "62.7", "145.2", "145.0", "2.8", "MWD", "Survey point"]
        ]
        
        for data in sample_data:
            self.add_row(data)
    
    def add_row(self, data=None):
        """اضافه کردن سطر جدید"""
        if data is None:
            data = [
                "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "MWD", ""
            ]
        
        return self.table_manager.add_row(data)
    
    def delete_row(self):
        """حذف سطر انتخاب شده"""
        if self.survey_table.currentRow() >= 0:
            self.table_manager.delete_row()
    
    def import_data(self):
        """ایمپورت داده از فایل CSV"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Survey Data", "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)"
        )
        
        if filename and self.table_manager:
            success = self.table_manager.import_from_csv(filename)
            if success:
                QMessageBox.information(self, "Success", "Data imported successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to import data")
    
    def calculate_trajectory(self):
        """محاسبه تراژکتوری با روش Minimum Curvature"""
        try:
            if self.survey_table.rowCount() < 2:
                QMessageBox.warning(self, "Error", "At least 2 survey points are required")
                return False
            
            # Collect survey points
            survey_points = []
            for row in range(self.survey_table.rowCount()):
                md_item = self.survey_table.item(row, 1)
                inc_item = self.survey_table.item(row, 2)
                azi_item = self.survey_table.item(row, 3)
                
                if md_item and inc_item and azi_item:
                    try:
                        md = float(md_item.text())
                        inc = float(inc_item.text())
                        azi = float(azi_item.text())
                        survey_points.append({
                            'row': row,
                            'md': md,
                            'inc': inc,
                            'azi': azi
                        })
                    except ValueError:
                        QMessageBox.warning(self, "Error", f"Invalid data in row {row+1}")
                        return False
            
            # Sort by MD
            survey_points.sort(key=lambda x: x['md'])
            
            # Initialize
            tvd = 0.0
            north = 0.0
            east = 0.0
            vs = 0.0
            hd = 0.0
            dls = 0.0
            
            # Update surface point
            if survey_points and survey_points[0]['row'] == 0:
                self.update_row_calculations(0, tvd, north, east, vs, hd, dls)
            
            # Calculate Minimum Curvature
            for i in range(1, len(survey_points)):
                prev = survey_points[i-1]
                curr = survey_points[i]
                
                md1, inc1, azi1 = prev['md'], prev['inc'], prev['azi']
                md2, inc2, azi2 = curr['md'], curr['inc'], curr['azi']
                
                # Convert to radians
                inc1_rad = math.radians(inc1)
                inc2_rad = math.radians(inc2)
                azi1_rad = math.radians(azi1)
                azi2_rad = math.radians(azi2)
                
                # ΔMD
                delta_md = md2 - md1
                if delta_md <= 0:
                    QMessageBox.warning(self, "Error", f"MD must increase (row {curr['row']+1})")
                    return False
                
                # Calculate β (angle between vectors)
                cos_beta = (math.sin(inc1_rad) * math.sin(inc2_rad) * 
                           math.cos(azi2_rad - azi1_rad) + 
                           math.cos(inc1_rad) * math.cos(inc2_rad))
                cos_beta = max(-1.0, min(1.0, cos_beta))
                beta = math.acos(cos_beta)
                
                # Ratio Factor
                rf = 1.0 if abs(beta) < 1e-10 else 2.0 / beta * math.tan(beta / 2.0)
                
                # Calculate deltas
                delta_tvd = 0.5 * delta_md * (math.cos(inc1_rad) + math.cos(inc2_rad)) * rf
                delta_north = 0.5 * delta_md * (
                    math.sin(inc1_rad) * math.cos(azi1_rad) + 
                    math.sin(inc2_rad) * math.cos(azi2_rad)
                ) * rf
                delta_east = 0.5 * delta_md * (
                    math.sin(inc1_rad) * math.sin(azi1_rad) + 
                    math.sin(inc2_rad) * math.sin(azi2_rad)
                ) * rf
                
                # Update cumulative values
                tvd += delta_tvd
                north += delta_north
                east += delta_east
                hd = math.sqrt(north**2 + east**2)
                
                # VS (assuming reference azimuth = 0°)
                vs_ref_rad = 0.0
                vs = north * math.cos(vs_ref_rad) + east * math.sin(vs_ref_rad)
                
                # DLS
                dls = (beta * 180.0 / math.pi) / delta_md * 30.0 if delta_md > 0 else 0.0
                
                # Update row
                self.update_row_calculations(curr['row'], tvd, north, east, vs, hd, dls)
            
            # Highlight calculated cells
            self.highlight_calculated_cells()
            
            QMessageBox.information(
                self, "Success",
                f"Trajectory calculation completed\n\n"
                f"Final Results:\n"
                f"• TVD: {tvd:.2f} m\n"
                f"• North: {north:.2f} m\n"
                f"• East: {east:.2f} m\n"
                f"• HD: {hd:.2f} m\n"
                f"• VS: {vs:.2f} m\n"
                f"• DLS: {dls:.2f} °/30m"
            )
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Calculation failed: {str(e)}")
            logger.error(f"Error calculating trajectory: {e}")
            return False
    
    def update_row_calculations(self, row: int, tvd: float, north: float, east: float, 
                               vs: float, hd: float, dls: float):
        """به‌روزرسانی محاسبات برای یک سطر"""
        self.survey_table.setItem(row, 4, QTableWidgetItem(f"{tvd:.2f}"))
        self.survey_table.setItem(row, 5, QTableWidgetItem(f"{north:.2f}"))
        self.survey_table.setItem(row, 6, QTableWidgetItem(f"{east:.2f}"))
        self.survey_table.setItem(row, 7, QTableWidgetItem(f"{vs:.2f}"))
        self.survey_table.setItem(row, 8, QTableWidgetItem(f"{hd:.2f}"))
        self.survey_table.setItem(row, 9, QTableWidgetItem(f"{dls:.2f}"))
    
    def highlight_calculated_cells(self):
        """برجسته کردن سلول‌های محاسبه شده"""
        for row in range(self.survey_table.rowCount()):
            for col in range(4, 10):  # Columns 4-9 (TVD to DLS)
                item = self.survey_table.item(row, col)
                if item and item.text() and float(item.text()) != 0.0:
                    item.setBackground(QColor(220, 255, 220))
                    item.setToolTip("Calculated using Minimum Curvature Method")
    
    def save_data(self):
        """ذخیره داده‌ها در دیتابیس"""
        if not self.current_well_id:
            QMessageBox.warning(self, "Warning", "Please select a well first")
            return False
        
        try:
            points = []
            for row in range(self.survey_table.rowCount()):
                # Get ID if exists
                id_item = self.survey_table.item(row, 0)
                point_id = int(id_item.text()) if id_item and id_item.text().isdigit() else None
                
                # Collect data
                md = self.survey_table.item(row, 1).text() if self.survey_table.item(row, 1) else "0"
                inc = self.survey_table.item(row, 2).text() if self.survey_table.item(row, 2) else "0"
                azi = self.survey_table.item(row, 3).text() if self.survey_table.item(row, 3) else "0"
                tvd = self.survey_table.item(row, 4).text() if self.survey_table.item(row, 4) else "0"
                north = self.survey_table.item(row, 5).text() if self.survey_table.item(row, 5) else "0"
                east = self.survey_table.item(row, 6).text() if self.survey_table.item(row, 6) else "0"
                vs = self.survey_table.item(row, 7).text() if self.survey_table.item(row, 7) else "0"
                hd = self.survey_table.item(row, 8).text() if self.survey_table.item(row, 8) else "0"
                dls = self.survey_table.item(row, 9).text() if self.survey_table.item(row, 9) else "0"
                tool = self.survey_table.item(row, 10).text() if self.survey_table.item(row, 10) else "MWD"
                remarks = self.survey_table.item(row, 11).text() if self.survey_table.item(row, 11) else ""
                
                point_data = {
                    'id': point_id,
                    'well_id': self.current_well_id,
                    'section_id': self.current_section_id,
                    'calculation_id': self.current_calculation_id,
                    'md': float(md) if md else 0.0,
                    'inc': float(inc) if inc else 0.0,
                    'azi': float(azi) if azi else 0.0,
                    'tvd': float(tvd) if tvd else 0.0,
                    'north': float(north) if north else 0.0,
                    'east': float(east) if east else 0.0,
                    'vs': float(vs) if vs else 0.0,
                    'hd': float(hd) if hd else 0.0,
                    'dls': float(dls) if dls else 0.0,
                    'tool': tool,
                    'remarks': remarks
                }
                
                points.append(point_data)
            
            # Save to database
            if self.db_manager and points:
                success = self.db_manager.save_survey_points(points)
                if success:
                    QMessageBox.information(self, "Success", f"Saved {len(points)} survey points to database")
                    # Reload to get IDs
                    self.load_data()
                    return True
                else:
                    QMessageBox.warning(self, "Error", "Failed to save to database")
                    return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")
            logger.error(f"Error saving survey data: {e}")
        
        return False
    
    def load_data(self):
        """بارگذاری داده‌ها از دیتابیس"""
        if not self.current_well_id:
            return False
        
        try:
            self.clear_table()
            
            if self.db_manager:
                points = self.db_manager.load_survey_points(
                    well_id=self.current_well_id,
                    calculation_id=self.current_calculation_id
                )
                
                for point in points:
                    row = self.survey_table.rowCount()
                    self.survey_table.insertRow(row)
                    
                    # Fill data
                    self.survey_table.setItem(row, 0, QTableWidgetItem(str(point['id'])))
                    self.survey_table.setItem(row, 1, QTableWidgetItem(str(point['md'])))
                    self.survey_table.setItem(row, 2, QTableWidgetItem(str(point['inc'])))
                    self.survey_table.setItem(row, 3, QTableWidgetItem(str(point['azi'])))
                    self.survey_table.setItem(row, 4, QTableWidgetItem(str(point['tvd'])))
                    self.survey_table.setItem(row, 5, QTableWidgetItem(str(point['north'])))
                    self.survey_table.setItem(row, 6, QTableWidgetItem(str(point['east'])))
                    self.survey_table.setItem(row, 7, QTableWidgetItem(str(point['vs'])))
                    self.survey_table.setItem(row, 8, QTableWidgetItem(str(point['hd'])))
                    self.survey_table.setItem(row, 9, QTableWidgetItem(str(point['dls'])))
                    self.survey_table.setItem(row, 10, QTableWidgetItem(point['tool']))
                    self.survey_table.setItem(row, 11, QTableWidgetItem(point['remarks']))
                
                logger.info(f"Loaded {len(points)} survey points")
                return True
            
        except Exception as e:
            logger.error(f"Error loading survey data: {e}")
        
        return False
    
    def clear_table(self):
        """پاک کردن تمامی داده‌های جدول"""
        self.survey_table.setRowCount(0)
    
    def export_data(self):
        """اکسپورت داده‌ها"""
        export_manager = ExportManager(self)
        export_manager.export_table_with_dialog(self.survey_table, "survey_data")
    
    def validate_data(self) -> List[str]:
        """اعتبارسنجی داده‌ها"""
        errors = []
        
        for row in range(self.survey_table.rowCount()):
            md_item = self.survey_table.item(row, 1)
            inc_item = self.survey_table.item(row, 2)
            azi_item = self.survey_table.item(row, 3)
            
            if md_item and md_item.text():
                try:
                    md = float(md_item.text())
                    if md < 0:
                        errors.append(f"Row {row+1}: MD cannot be negative")
                except ValueError:
                    errors.append(f"Row {row+1}: MD must be a number")
            
            if inc_item and inc_item.text():
                try:
                    inc = float(inc_item.text())
                    if not (0 <= inc <= 180):
                        errors.append(f"Row {row+1}: Inc must be between 0-180 degrees")
                except ValueError:
                    errors.append(f"Row {row+1}: Inc must be a number")
            
            if azi_item and azi_item.text():
                try:
                    azi = float(azi_item.text())
                    if not (0 <= azi <= 360):
                        errors.append(f"Row {row+1}: Azi must be between 0-360 degrees")
                except ValueError:
                    errors.append(f"Row {row+1}: Azi must be a number")
        
        return errors

# ==================== Trajectory Plot Tab ====================
class TrajectoryPlotTab(QWidget):
    """تب نمودارهای تراژکتوری"""
    
    def __init__(self, db_manager: DatabaseManager = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_calculation_id = None
        self.plots = {}
        self.init_ui()
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        layout = QVBoxLayout(self)
        
        # ایجاد Tab Widget برای انواع نمودارها
        self.plot_tabs = QTabWidget()
        
        # نمودار 2D Plan View
        self.plot_2d_plan = pg.PlotWidget()
        self.plot_2d_plan.setBackground("w")
        self.plot_2d_plan.setLabel("left", "North (m)")
        self.plot_2d_plan.setLabel("bottom", "East (m)")
        self.plot_2d_plan.setTitle("2D Plan View")
        self.plot_2d_plan.showGrid(x=True, y=True)
        self.plot_tabs.addTab(self.plot_2d_plan, "2D Plan View")
        
        # نمودار 2D Side View
        self.plot_2d_side = pg.PlotWidget()
        self.plot_2d_side.setBackground("w")
        self.plot_2d_side.setLabel("left", "TVD (m)")
        self.plot_2d_side.setLabel("bottom", "Horizontal Displacement (m)")
        self.plot_2d_side.setTitle("2D Side View")
        self.plot_2d_side.showGrid(x=True, y=True)
        self.plot_tabs.addTab(self.plot_2d_side, "2D Side View")
        
        # نمودار 3D View
        self.plot_3d_container = QWidget()
        self.plot_3d_layout = QVBoxLayout(self.plot_3d_container)
        self.plot_3d_label = QLabel("3D Plot (requires additional 3D plotting library)")
        self.plot_3d_label.setAlignment(Qt.AlignCenter)
        self.plot_3d_layout.addWidget(self.plot_3d_label)
        self.plot_tabs.addTab(self.plot_3d_container, "3D View")
        
        layout.addWidget(self.plot_tabs)
        
        # دکمه‌های کنترل
        control_layout = QHBoxLayout()
        
        self.plot_btn = QPushButton("📊 Plot Trajectory")
        self.plot_btn.setToolTip("Plot trajectory from current data")
        self.plot_btn.clicked.connect(self.plot_trajectory)
        
        self.save_plot_btn = QPushButton("💾 Save Plot")
        self.save_plot_btn.setToolTip("Save plot as image")
        self.save_plot_btn.clicked.connect(self.save_plot)
        
        self.load_plot_btn = QPushButton("📂 Load Plot")
        self.load_plot_btn.setToolTip("Load saved plot from database")
        self.load_plot_btn.clicked.connect(self.load_plots)
        
        self.clear_plot_btn = QPushButton("🗑️ Clear Plot")
        self.clear_plot_btn.setToolTip("Clear all plots")
        self.clear_plot_btn.clicked.connect(self.clear_plots)
        
        self.export_plot_btn = QPushButton("📤 Export Data")
        self.export_plot_btn.setToolTip("Export plot data")
        self.export_plot_btn.clicked.connect(self.export_plot_data)
        
        control_layout.addWidget(self.plot_btn)
        control_layout.addWidget(self.save_plot_btn)
        control_layout.addWidget(self.load_plot_btn)
        control_layout.addWidget(self.clear_plot_btn)
        control_layout.addWidget(self.export_plot_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # تنظیم Widget
        self.setLayout(layout)
    
    def set_current_calculation(self, calculation_id: int):
        """تنظیم محاسبه جاری"""
        self.current_calculation_id = calculation_id
        if calculation_id:
            self.load_plots()
    
    def plot_trajectory(self, survey_data: List[Dict] = None):
        """رسم نمودار تراژکتوری"""
        try:
            if not survey_data:
                # اگر داده ارسال نشده، می‌تواند از parent درخواست کند
                parent = self.parent()
                while parent and not hasattr(parent, 'get_survey_data'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'get_survey_data'):
                    survey_data = parent.get_survey_data()
            
            if not survey_data or len(survey_data) < 2:
                QMessageBox.warning(self, "Warning", "No survey data available for plotting")
                return
            
            # Extract data
            mds = [point.get('md', 0) for point in survey_data]
            tvd = [point.get('tvd', 0) for point in survey_data]
            north = [point.get('north', 0) for point in survey_data]
            east = [point.get('east', 0) for point in survey_data]
            hd = [point.get('hd', 0) for point in survey_data]
            
            # Clear previous plots
            self.clear_plots()
            
            # Plot 2D Plan View
            self.plot_2d_plan.clear()
            self.plot_2d_plan.plot(east, north, pen=pg.mkPen('b', width=2), symbol='o', symbolSize=5)
            
            # Plot 2D Side View
            self.plot_2d_side.clear()
            self.plot_2d_side.plot(hd, tvd, pen=pg.mkPen('r', width=2), symbol='s', symbolSize=5)
            
            # Update 3D view label
            self.plot_3d_label.setText(f"3D Trajectory Plot\nPoints: {len(survey_data)}\nMax TVD: {max(tvd):.1f} m")
            
            # Store plot data
            self.plots = {
                '2d_plan': {'east': east, 'north': north},
                '2d_side': {'hd': hd, 'tvd': tvd},
                '3d': {'md': mds, 'north': north, 'east': east, 'tvd': tvd}
            }
            
            logger.info(f"Plotted trajectory with {len(survey_data)} points")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot trajectory: {str(e)}")
            logger.error(f"Error plotting trajectory: {e}")
    
    def save_plot(self):
        """ذخیره نمودار در دیتابیس"""
        if not self.current_calculation_id:
            QMessageBox.warning(self, "Warning", "No calculation selected")
            return False
        
        try:
            if not self.plots:
                QMessageBox.warning(self, "Warning", "No plot data to save")
                return False
            
            plot_data = {
                'calculation_id': self.current_calculation_id,
                'plot_type': '2d_plan',
                'title': f'Trajectory Plot {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                'plot_data': json.dumps(self.plots),
                'image_data': None,  # می‌توان تصویر ذخیره کرد
                'image_format': 'png'
            }
            
            if self.db_manager:
                plot_id = self.db_manager.save_trajectory_plot(plot_data)
                if plot_id:
                    QMessageBox.information(self, "Success", f"Plot saved with ID: {plot_id}")
                    return True
                else:
                    QMessageBox.warning(self, "Error", "Failed to save plot to database")
                    return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")
            logger.error(f"Error saving plot: {e}")
        
        return False
    
    def load_plots(self):
        """بارگذاری نمودارهای ذخیره شده"""
        if not self.current_calculation_id:
            return False
        
        try:
            if self.db_manager:
                plots = self.db_manager.load_trajectory_plots(self.current_calculation_id)
                
                if plots:
                    for plot in plots:
                        try:
                            plot_data = json.loads(plot.get('plot_data', '{}'))
                            
                            if plot['plot_type'] == '2d_plan':
                                east = plot_data.get('east', [])
                                north = plot_data.get('north', [])
                                if east and north:
                                    self.plot_2d_plan.clear()
                                    self.plot_2d_plan.plot(east, north, 
                                                         pen=pg.mkPen('g', width=2, style=Qt.DashLine),
                                                         name=f"Saved: {plot['title']}")
                            
                            elif plot['plot_type'] == '2d_side':
                                hd = plot_data.get('hd', [])
                                tvd = plot_data.get('tvd', [])
                                if hd and tvd:
                                    self.plot_2d_side.clear()
                                    self.plot_2d_side.plot(hd, tvd,
                                                          pen=pg.mkPen('orange', width=2, style=Qt.DashLine),
                                                          name=f"Saved: {plot['title']}")
                            
                            # می‌توان تصاویر ذخیره شده را هم بارگذاری کرد
                            if plot.get('image_data'):
                                # کد برای بارگذاری تصویر
                                pass
                                
                        except Exception as e:
                            logger.error(f"Error loading plot {plot['id']}: {e}")
                    
                    logger.info(f"Loaded {len(plots)} saved plots")
                    return True
                else:
                    logger.info("No saved plots found")
                    return False
            
        except Exception as e:
            logger.error(f"Error loading plots: {e}")
        
        return False
    
    def clear_plots(self):
        """پاک کردن تمامی نمودارها"""
        self.plot_2d_plan.clear()
        self.plot_2d_side.clear()
        self.plot_3d_label.setText("3D Plot (requires additional 3D plotting library)")
        self.plots.clear()
    
    def export_plot_data(self):
        """اکسپورت داده‌های نمودار"""
        if not self.plots:
            QMessageBox.warning(self, "Warning", "No plot data to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Plot Data", "",
            "CSV Files (*.csv);;JSON Files (*.json);;All Files (*.*)"
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.plots, f, indent=2)
                else:
                    # Export as CSV
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Type', 'Index', 'X', 'Y', 'Z'])
                        
                        # 2D Plan data
                        if '2d_plan' in self.plots:
                            east = self.plots['2d_plan'].get('east', [])
                            north = self.plots['2d_plan'].get('north', [])
                            for i, (e, n) in enumerate(zip(east, north)):
                                writer.writerow(['2D_Plan', i, e, n, 0])
                        
                        # 2D Side data
                        if '2d_side' in self.plots:
                            hd = self.plots['2d_side'].get('hd', [])
                            tvd = self.plots['2d_side'].get('tvd', [])
                            for i, (h, t) in enumerate(zip(hd, tvd)):
                                writer.writerow(['2D_Side', i, h, t, 0])
                
                QMessageBox.information(self, "Success", f"Plot data exported to {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export plot data: {str(e)}")
                logger.error(f"Error exporting plot data: {e}")
    
    def capture_plot_image(self):
        """ذخیره نمودار به عنوان تصویر"""
        if self.plot_tabs.currentIndex() == 0:
            plot_widget = self.plot_2d_plan
        elif self.plot_tabs.currentIndex() == 1:
            plot_widget = self.plot_2d_side
        else:
            QMessageBox.warning(self, "Warning", "3D plot cannot be captured as image")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Plot Image", "",
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*.*)"
        )
        
        if filename:
            try:
                # Capture plot as image
                exporter = pg.exporters.ImageExporter(plot_widget.plotItem)
                exporter.export(filename)
                QMessageBox.information(self, "Success", f"Plot saved as image: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save image: {str(e)}")

# ==================== Trajectory Calculation Manager ====================
class TrajectoryCalculationManager:
    """مدیریت محاسبات تراژکتوری"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager
        self.calculations = []
        self.current_calculation = None
    
    def create_calculation(self, well_id: int, section_id: int = None, 
                          method: str = "Minimum Curvature", 
                          description: str = "") -> int:
        """ایجاد محاسبه جدید"""
        try:
            calculation_data = {
                'well_id': well_id,
                'section_id': section_id,
                'method': method,
                'calculation_date': datetime.now().date(),
                'parameters': {},
                'results': {},
                'description': description
            }
            
            if self.db_manager:
                calc_id = self.db_manager.save_trajectory_calculation(calculation_data)
                if calc_id:
                    logger.info(f"Created trajectory calculation with ID: {calc_id}")
                    return calc_id
            
        except Exception as e:
            logger.error(f"Error creating trajectory calculation: {e}")
        
        return None
    
    def load_calculations(self, well_id: int = None) -> List[Dict]:
        """بارگذاری محاسبات"""
        try:
            if self.db_manager:
                self.calculations = self.db_manager.load_trajectory_calculations(well_id)
                return self.calculations
            
        except Exception as e:
            logger.error(f"Error loading trajectory calculations: {e}")
        
        return []
    
    def get_calculation_by_id(self, calc_id: int) -> Optional[Dict]:
        """دریافت محاسبه بر اساس ID"""
        for calc in self.calculations:
            if calc['id'] == calc_id:
                return calc
        return None

# ==================== Main Trajectory Widget ====================
class TrajectoryWidget(DrillWidgetBase):
    """ویجت اصلی تراژکتوری"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        super().__init__("TrajectoryWidget", db_manager)
        
        # Initialize components
        self.trip_sheet_tab = None
        self.survey_data_tab = None
        self.plot_tab = None
        self.calculation_manager = None
        
        # Current selections
        self.current_well_id = None
        self.current_section_id = None
        self.current_calculation_id = None
        
        # Setup UI
        self.init_ui()
        
        # Setup managers
        setup_widget_with_managers(self, self.widget_name, enable_autosave=True, 
                                  autosave_interval=5, setup_shortcuts=True)
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout(self)
        
        # Toolbar برای انتخاب چاه و سکشن
        toolbar = QHBoxLayout()
        
        self.well_combo = QComboBox()
        self.well_combo.setToolTip("Select well")
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        
        self.section_combo = QComboBox()
        self.section_combo.setToolTip("Select section")
        self.section_combo.currentIndexChanged.connect(self.on_section_changed)
        
        self.calc_combo = QComboBox()
        self.calc_combo.setToolTip("Select calculation")
        self.calc_combo.currentIndexChanged.connect(self.on_calculation_changed)
        
        new_calc_btn = QPushButton("➕ New Calculation")
        new_calc_btn.setToolTip("Create new trajectory calculation")
        new_calc_btn.clicked.connect(self.create_new_calculation)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setToolTip("Refresh data")
        refresh_btn.clicked.connect(self.refresh_data)
        
        toolbar.addWidget(QLabel("Well:"))
        toolbar.addWidget(self.well_combo)
        toolbar.addWidget(QLabel("Section:"))
        toolbar.addWidget(self.section_combo)
        toolbar.addWidget(QLabel("Calculation:"))
        toolbar.addWidget(self.calc_combo)
        toolbar.addWidget(new_calc_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        
        main_layout.addLayout(toolbar)
        
        # تب‌های اصلی
        self.tab_widget = QTabWidget()
        
        # ایجاد تب‌ها
        self.trip_sheet_tab = TripSheetTab(self.db_manager)
        self.survey_data_tab = SurveyDataTab(self.db_manager)
        self.plot_tab = TrajectoryPlotTab(self.db_manager)
        
        # اضافه کردن تب‌ها
        self.tab_widget.addTab(self.trip_sheet_tab, "Trip Sheet")
        self.tab_widget.addTab(self.survey_data_tab, "Survey Data")
        self.tab_widget.addTab(self.plot_tab, "Trajectory Plot")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
        
        # Initialize calculation manager
        self.calculation_manager = TrajectoryCalculationManager(self.db_manager)
        
        # Load initial data
        self.load_wells()
    
    def load_wells(self):
        """بارگذاری لیست چاه‌ها"""
        try:
            self.well_combo.clear()
            
            if self.db_manager:
                # Get hierarchy
                hierarchy = self.db_manager.get_hierarchy()
                
                for company in hierarchy:
                    for project in company.get('projects', []):
                        for well in project.get('wells', []):
                            display_text = f"{well['name']} ({well['code']}) - {project['name']}"
                            self.well_combo.addItem(display_text, well['id'])
                
                logger.info(f"Loaded {self.well_combo.count()} wells")
            
        except Exception as e:
            logger.error(f"Error loading wells: {e}")
    
    def load_sections(self, well_id: int):
        """بارگذاری لیست سکشن‌های چاه"""
        try:
            self.section_combo.clear()
            self.section_combo.addItem("All Sections", -1)
            
            if self.db_manager and well_id:
                sections = self.db_manager.get_sections_by_well(well_id)
                
                for section in sections:
                    display_text = f"{section['name']} ({section['code']})"
                    self.section_combo.addItem(display_text, section['id'])
                
                logger.info(f"Loaded {self.section_combo.count() - 1} sections")
            
        except Exception as e:
            logger.error(f"Error loading sections: {e}")
    
    def load_calculations(self, well_id: int):
        """بارگذاری لیست محاسبات"""
        try:
            self.calc_combo.clear()
            self.calc_combo.addItem("Select Calculation", -1)
            
            if self.calculation_manager and well_id:
                calculations = self.calculation_manager.load_calculations(well_id)
                
                for calc in calculations:
                    date_str = calc['calculation_date']
                    if isinstance(date_str, str):
                        date_str = date_str[:10]  # فقط تاریخ
                    display_text = f"{calc['method']} - {date_str}"
                    self.calc_combo.addItem(display_text, calc['id'])
                
                logger.info(f"Loaded {self.calc_combo.count() - 1} calculations")
            
        except Exception as e:
            logger.error(f"Error loading calculations: {e}")
    
    def on_well_changed(self, index: int):
        """هنگام تغییر چاه"""
        if index >= 0:
            well_id = self.well_combo.currentData()
            if well_id and well_id != self.current_well_id:
                self.current_well_id = well_id
                self.current_section_id = None
                self.current_calculation_id = None
                
                # Update sections and calculations
                self.load_sections(well_id)
                self.load_calculations(well_id)
                
                # Update tabs
                self.update_tabs()
                
                logger.info(f"Well changed to ID: {well_id}")
    
    def on_section_changed(self, index: int):
        """هنگام تغییر سکشن"""
        if index >= 0:
            section_id = self.section_combo.currentData()
            if section_id != self.current_section_id:
                self.current_section_id = section_id if section_id != -1 else None
                self.update_tabs()
                logger.info(f"Section changed to ID: {self.current_section_id}")
    
    def on_calculation_changed(self, index: int):
        """هنگام تغییر محاسبه"""
        if index >= 0:
            calc_id = self.calc_combo.currentData()
            if calc_id and calc_id != -1 and calc_id != self.current_calculation_id:
                self.current_calculation_id = calc_id
                self.update_tabs()
                logger.info(f"Calculation changed to ID: {calc_id}")
    
    def update_tabs(self):
        """به‌روزرسانی تب‌ها با داده‌های جدید"""
        # Update Trip Sheet tab
        if self.trip_sheet_tab:
            self.trip_sheet_tab.set_current_well(
                self.current_well_id, 
                self.current_section_id
            )
        
        # Update Survey Data tab
        if self.survey_data_tab:
            self.survey_data_tab.set_current_well(
                self.current_well_id,
                self.current_section_id,
                self.current_calculation_id
            )
        
        # Update Plot tab
        if self.plot_tab:
            self.plot_tab.set_current_calculation(self.current_calculation_id)
    
    def create_new_calculation(self):
        """ایجاد محاسبه جدید"""
        if not self.current_well_id:
            QMessageBox.warning(self, "Warning", "Please select a well first")
            return
        
        # دیالوگ برای ورود اطلاعات محاسبه
        method, ok = QInputDialog.getItem(
            self, "Calculation Method", "Select method:", 
            ["Minimum Curvature", "Radius of Curvature", "Tangential", "Balanced Tangential"], 
            0, False
        )
        
        if not ok:
            return
        
        description, ok = QInputDialog.getText(
            self, "Calculation Description", "Enter description:"
        )
        
        if ok:
            calc_id = self.calculation_manager.create_calculation(
                self.current_well_id,
                self.current_section_id,
                method,
                description or f"Calculation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            if calc_id:
                self.current_calculation_id = calc_id
                self.load_calculations(self.current_well_id)
                
                # Select the new calculation
                index = self.calc_combo.findData(calc_id)
                if index >= 0:
                    self.calc_combo.setCurrentIndex(index)
                
                QMessageBox.information(self, "Success", f"New calculation created with ID: {calc_id}")
    
    def refresh_data(self):
        """رفرش داده‌ها"""
        self.load_wells()
        if self.current_well_id:
            self.load_sections(self.current_well_id)
            self.load_calculations(self.current_well_id)
        self.update_tabs()
        self.show_success("Data refreshed")
    
    def get_survey_data(self) -> List[Dict]:
        """دریافت داده‌های سروی از تب Survey Data"""
        if self.survey_data_tab:
            data = []
            for row in range(self.survey_data_tab.survey_table.rowCount()):
                row_data = {}
                for col in range(1, 12):  # Skip ID column
                    item = self.survey_data_tab.survey_table.item(row, col)
                    if item and item.text():
                        try:
                            # Try to convert to float
                            value = float(item.text())
                            row_data[self.survey_data_tab.survey_table.horizontalHeaderItem(col).text()] = value
                        except ValueError:
                            row_data[self.survey_data_tab.survey_table.horizontalHeaderItem(col).text()] = item.text()
                    elif item:
                        row_data[self.survey_data_tab.survey_table.horizontalHeaderItem(col).text()] = ""
                data.append(row_data)
            return data
        return []
    
    def save_data(self):
        """ذخیره داده‌های تمامی تب‌ها"""
        try:
            self.show_progress("Saving trajectory data...")
            
            success = True
            
            # Save Trip Sheet data
            if self.trip_sheet_tab:
                if not self.trip_sheet_tab.save_data():
                    success = False
            
            # Save Survey Data
            if self.survey_data_tab:
                if not self.survey_data_tab.save_data():
                    success = False
            
            # Save Plots
            if self.plot_tab:
                if not self.plot_tab.save_plot():
                    # این یک warning است، نه error
                    logger.warning("Plot save was optional")
            
            if success:
                self.show_success("Trajectory data saved successfully")
                return True
            else:
                self.show_error("Some data could not be saved")
                return False
            
        except Exception as e:
            self.show_error(f"Error saving data: {str(e)}")
            logger.error(f"Error saving trajectory data: {e}")
            return False
        
        finally:
            self.clear_message()
    
    def load_data(self):
        """بارگذاری داده‌ها"""
        try:
            self.show_progress("Loading trajectory data...")
            
            # Tab‌ها خودشان هنگام تغییر well/section/calculation داده‌ها را بارگذاری می‌کنند
            self.refresh_data()
            
            self.show_success("Data loaded successfully")
            return True
            
        except Exception as e:
            self.show_error(f"Error loading data: {str(e)}")
            logger.error(f"Error loading trajectory data: {e}")
            return False
        
        finally:
            self.clear_message()
    
    def setup_shortcuts(self):
        """تنظیم کلیدهای میانبر"""
        shortcuts = {
            "Ctrl+S": self.save_data,
            "F5": self.refresh_data,
            "Ctrl+N": self.create_new_calculation,
            "Ctrl+P": lambda: self.plot_tab.plot_trajectory() if self.plot_tab else None,
            "Ctrl+E": self.export_all_data,
        }
        
        for key, slot in shortcuts.items():
            QShortcut(QKeySequence(key), self).activated.connect(slot)
    
    def export_all_data(self):
        """اکسپورت تمامی داده‌ها"""
        try:
            # Create export dialog
            formats = ["CSV", "Excel", "JSON"]
            format_choice, ok = QInputDialog.getItem(
                self, "Export Format", "Select export format:", formats, 0, False
            )
            
            if not ok or not format_choice:
                return
            
            # Select directory
            directory = QFileDialog.getExistingDirectory(
                self, "Select Export Directory", ""
            )
            
            if not directory:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"trajectory_export_{timestamp}"
            
            # Export Trip Sheet
            if self.trip_sheet_tab:
                trip_data = self.trip_sheet_tab.get_table_data()
                if trip_data:
                    filename = os.path.join(directory, f"{base_filename}_trip_sheet.csv")
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        # Write headers
                        headers = ["Time", "Activity", "Depth (m)", "Cum. Trip (m)", 
                                  "Duration (hr)", "Remarks", "Supervisor", "Verified"]
                        writer.writerow(headers)
                        # Write data
                        for row in trip_data:
                            writer.writerow([
                                row.get('col_1', ''),
                                row.get('col_2', ''),
                                row.get('col_3', ''),
                                row.get('col_4', ''),
                                row.get('col_5', ''),
                                row.get('col_6', ''),
                                row.get('col_7', ''),
                                row.get('verified', False)
                            ])
            
            # Export Survey Data
            if self.survey_data_tab:
                survey_data = self.get_survey_data()
                if survey_data:
                    filename = os.path.join(directory, f"{base_filename}_survey_data.csv")
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        # Write headers
                        headers = ["MD (m)", "Inc (°)", "Azi (°)", "TVD (m)", "North (m)", 
                                  "East (m)", "VS (m)", "HD (m)", "DLS (°/30m)", "Tool", "Remarks"]
                        writer.writerow(headers)
                        # Write data
                        for row in survey_data:
                            writer.writerow([
                                row.get("MD (m)", ''),
                                row.get("Inc (°)", ''),
                                row.get("Azi (°)", ''),
                                row.get("TVD (m)", ''),
                                row.get("North (m)", ''),
                                row.get("East (m)", ''),
                                row.get("VS (m)", ''),
                                row.get("HD (m)", ''),
                                row.get("DLS (°/30m)", ''),
                                row.get("Tool", ''),
                                row.get("Remarks", '')
                            ])
            
            # Export Plot Data
            if self.plot_tab and hasattr(self.plot_tab, 'plots') and self.plot_tab.plots:
                filename = os.path.join(directory, f"{base_filename}_plot_data.json")
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.plot_tab.plots, f, indent=2)
            
            self.show_success(f"Data exported to {directory}")
            
        except Exception as e:
            self.show_error(f"Export failed: {str(e)}")
            logger.error(f"Error exporting data: {e}")
