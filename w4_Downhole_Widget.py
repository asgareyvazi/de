"""
Downhole Widget - ابزار مدیریت تجهیزات زیر سطحی
"""

import logging
import json
from datetime import datetime, date
import pandas as pd
import lasio

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from core.database import DatabaseManager
from core.managers import StatusBarManager, TableManager

logger = logging.getLogger(__name__)


# ==================== DrillWidgetBase ====================
class DrillWidgetBase(QWidget):
    """کلاس پایه برای ویجت‌های حفاری"""
    
    def __init__(self, widget_name, db_manager=None):
        super().__init__()
        self.widget_name = widget_name
        self.db = db_manager
        self.status_manager = StatusBarManager()
        self.status_manager.register_widget(self.widget_name, self)
        
        # متغیرهای حالت
        self.current_well = None
        self.current_report = None
        self.current_section = None
        
        # تایمر برای auto-save
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setInterval(300000)  # 5 دقیقه
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.save_debounce_timer = QTimer()
        self.save_debounce_timer.setSingleShot(True)
        self.save_debounce_timer.setInterval(1000)  # 1 ثانیه تاخیر
        self.save_debounce_timer.timeout.connect(self.debounced_save)
        
    def on_data_changed(self):
        """وقتی داده تغییر کرد"""
        self.save_debounce_timer.start()
    
    def debounced_save(self):
        """ذخیره با تاخیر"""
        self.save_tab_data()
        
    def setup_connections(self):
        """تنظیم اتصالات - برای override"""
        pass
    
    def load_tab_data(self, report_id, tab_type=None):
        """لود داده‌های تب از گزارش"""
        try:
            if self.db:
                report_data = self.db.get_daily_report_by_id(report_id)
                if report_data:
                    self.current_report = report_id
                    
                    # یافتن well_id از report
                    if hasattr(self, 'current_well') and not self.current_well:
                        self.current_well = report_data.get('well_id')
                    
                    # لود داده‌های مخصوص این تب
                    if tab_type:
                        field_map = {
                            'drilling': 'drilling_data',
                            'mud': 'mud_data',
                            'equipment': 'equipment_data',
                            'downhole': 'downhole_data',
                            'trajectory': 'trajectory_data',
                            'logistics': 'logistics_data',
                            'safety': 'safety_data',
                            'services': 'services_data',
                            'analysis': 'analysis_data',
                            'planning': 'planning_data',
                            'export': 'export_data'
                        }
                        
                        field_name = field_map.get(tab_type)
                        if field_name and field_name in report_data:
                            tab_data = report_data[field_name]
                            if tab_data:
                                self.load_from_report_data(tab_data)
                    
                    self.status_manager.show_success(
                        self.widget_name,
                        f"Data loaded from report #{report_id}"
                    )
                    return True
        except Exception as e:
            logger.error(f"Error loading tab data: {e}")
            self.status_manager.show_error(
                self.widget_name,
                f"Failed to load data: {str(e)}"
            )
        return False
    
    def load_from_report_data(self, report_data):
        """لود داده‌های خاص تب از report_data - برای override"""
        pass
    
    def save_to_report_data(self):
        """ذخیره داده‌های تب در report_data - برای override"""
        return {}
    
    def save_tab_data(self):
        """ذخیره داده‌های تب در دیتابیس"""
        try:
            if self.current_report and self.db:
                tab_data = self.save_to_report_data()
                if tab_data:
                    # تشخیص نوع تب از نام کلاس
                    tab_type = self.__class__.__name__.lower().replace('widget', '')
                    if 'downhole' in tab_type:
                        tab_type = 'downhole'
                    elif 'drilling' in tab_type:
                        tab_type = 'drilling'
                    # و بقیه...
                    
                    success = self.db.update_daily_report_tab_data(
                        self.current_report,
                        tab_type,
                        tab_data
                    )
                    
                    if success:
                        self.status_manager.show_success(
                            self.widget_name,
                            "Data saved successfully"
                        )
                        return True
        except Exception as e:
            logger.error(f"Error saving tab data: {e}")
            self.status_manager.show_error(
                self.widget_name,
                f"Failed to save data: {str(e)}"
            )
        return False
    
    def auto_save(self):
        """ذخیره خودکار"""
        if hasattr(self, 'auto_save_enabled') and self.auto_save_enabled:
            self.save_tab_data()
    
    def refresh(self):
        """رفرش داده‌ها"""
        self.status_manager.show_message(self.widget_name, "Refreshing data...", 2000)
    
    def clear_data(self):
        """پاک کردن داده‌ها"""
        pass
    
    def export_data(self):
        """اکسپورت داده‌ها"""
        pass
    
    def show_help(self):
        """نمایش راهنما"""
        help_text = f"""
        <h3>{self.widget_name} Help</h3>
        <p>This tab manages downhole equipment and formations.</p>
        <p>Features:</p>
        <ul>
        <li>Bit Record Management</li>
        <li>BHA Configuration</li>
        <li>Downhole Equipment Tracking</li>
        <li>Formation Evaluation</li>
        </ul>
        """
        QMessageBox.information(self, f"{self.widget_name} Help", help_text)


# ==================== Bit Record Manager ====================
class BitRecordManager:
    """مدیریت رکوردهای مته"""
    
    def __init__(self, table_widget):
        self.table = table_widget
        self.manager = TableManager(table_widget)
        self.data_cache = []  # کش داده‌ها
        self.current_page = 0
        self.page_size = 100  # لود کردن صفحه‌ای
        
    def load_page(self, page):
        """لود کردن داده‌ها به صورت صفحه‌ای"""
        start_idx = page * self.page_size
        end_idx = start_idx + self.page_size
        
        self.table.setRowCount(0)
        for row in self.data_cache[start_idx:end_idx]:
            self.add_row(row)
            
    def setup_table(self):
        """تنظیم جدول رکوردهای مته"""
        headers = [
            "Bit No", "Size (in)", "Manufacture", "BHA No", "Type", "IADC Code",
            "Serial No", "Jets", "CMT", "Depth In (m)", "Depth Out (m)", "Formation",
            "Metres Drilled", "Hours", "ROP (m/hr)", "WOB Min (klb)", "WOB Max (klb)",
            "RPM Min", "RPM Max", "Pump Press Min (psi)", "Pump Press Max (psi)",
            "GPM Min", "GPM Max", "Mud Weight (pcf)", "TFA (in²)", "Bit Press Loss (psi)",
            "Bit HHP", "Bit H.S.I", "IR", "OR", "DC", "Loc", "B/S", "G/16", "OC",
            "Reason Pulled", "Remarks"
        ]
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # تنظیم عرض ستون‌ها
        for col in range(len(headers)):
            if col < 10:
                self.table.setColumnWidth(col, 90)
            elif col < 20:
                self.table.setColumnWidth(col, 100)
            elif col < 30:
                self.table.setColumnWidth(col, 110)
            else:
                self.table.setColumnWidth(col, 120)
        
        # فعال کردن کشیدن و رها کردن برای مرتب‌سازی
        self.table.setDragDropMode(QAbstractItemView.InternalMove)
        
    def add_default_row(self):
        """اضافه کردن سطر پیش‌فرض"""
        row_count = self.table.rowCount()
        row_data = {
            "Bit No": str(row_count + 1),
            "Size (in)": "8.5",
            "Manufacture": "Halliburton",
            "BHA No": f"BHA-{(row_count // 3) + 1:03d}",
            "Type": "PDC",
            "IADC Code": "M323",
            "Serial No": f"SN{row_count + 1:03d}",
            "Jets": "3x16",
            "CMT": "New",
            "Depth In (m)": "0.0",
            "Depth Out (m)": "0.0",
            "Formation": "Shale",
            "Metres Drilled": "0.0",
            "Hours": "0.0",
            "ROP (m/hr)": "0.0",
            "WOB Min (klb)": "0.0",
            "WOB Max (klb)": "0.0",
            "RPM Min": "0",
            "RPM Max": "0",
            "Pump Press Min (psi)": "0.0",
            "Pump Press Max (psi)": "0.0",
            "GPM Min": "0.0",
            "GPM Max": "0.0",
            "Mud Weight (pcf)": "75.0",
            "TFA (in²)": "0.25",
            "Bit Press Loss (psi)": "0.0",
            "Bit HHP": "0.0",
            "Bit H.S.I": "0.0",
            "IR": "",
            "OR": "",
            "DC": "",
            "Loc": "",
            "B/S": "",
            "G/16": "",
            "OC": "",
            "Reason Pulled": "",
            "Remarks": ""
        }
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        for col, (header, value) in enumerate(row_data.items()):
            item = QTableWidgetItem(str(value))
            
            # تراز مناسب برای ستون‌های عددی
            if any(keyword in header for keyword in ["No", "Size", "Depth", "Metres", 
                                                     "Hours", "ROP", "WOB", "RPM", 
                                                     "Press", "GPM", "Weight", "TFA",
                                                     "HHP", "H.S.I"]):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            self.table.setItem(row, col, item)
        
        return row
    
    def calculate_rop(self, row):
        """محاسبه ROP برای سطر"""
        try:
            metres_item = self.table.item(row, 12)  # Metres Drilled
            hours_item = self.table.item(row, 13)   # Hours
            
            if metres_item and hours_item:
                metres = float(metres_item.text() or 0)
                hours = float(hours_item.text() or 0)
                
                if hours > 0:
                    rop = metres / hours
                    rop_item = self.table.item(row, 14)  # ROP
                    if rop_item:
                        rop_item.setText(f"{rop:.2f}")
                    return rop
        except:
            pass
        return 0.0
    
    def get_all_data(self):
        """دریافت تمام داده‌های جدول"""
        data = []
        headers = []
        
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())
        
        for row in range(self.table.rowCount()):
            row_data = {}
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data[headers[col]] = item.text() if item else ""
            data.append(row_data)
        
        return data
    
    def load_data(self, data):
        """لود داده در جدول"""
        self.table.setRowCount(0)
        
        if not data:
            return
        
        for row_data in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            for col, (header, value) in enumerate(row_data.items()):
                if col < self.table.columnCount():
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(row, col, item)


# ==================== BHA Manager ====================
class BHAManager:
    """مدیریت BHA"""
    
    def __init__(self, table_widget):
        self.table = table_widget
        self.manager = TableManager(table_widget)
        self.saved_bhas = {}
        
    def setup_table(self):
        """تنظیم جدول BHA"""
        headers = [
            "Tool Type", "OD (in)", "ID (in)", "Length (m)", "Serial No",
            "Weight (kg)", "Connection Type", "Make-up Torque (ft-lb)", "Remarks"
        ]
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # تنظیم عرض ستون‌ها
        column_widths = [150, 80, 80, 100, 120, 100, 120, 120, 200]
        for col, width in enumerate(column_widths):
            self.table.setColumnWidth(col, width)
        
        # تنظیم ستون‌های عددی برای ویرایش آسان
        for col in [1, 2, 3, 5, 7]:  # ستون‌های عددی
            for row in range(self.table.rowCount()):
                if not self.table.item(row, col):
                    item = QTableWidgetItem("0.00")
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(row, col, item)
    
    def add_default_row(self, tool_type=""):
        """اضافه کردن سطر پیش‌فرض"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # داده‌های پیش‌فرض بر اساس نوع ابزار
        defaults = {
            "Bit": ["PDC Bit", "8.5", "2.5", "0.3", "", "150", "API Reg", "25000", "New bit"],
            "Drill Collar": ["Drill Collar", "8.0", "2.8", "9.0", "", "2500", "API NC", "32000", "Heavy weight"],
            "MWD": ["MWD Tool", "6.75", "2.5", "4.5", "", "120", "API FH", "18000", "Directional"],
            "Stabilizer": ["Stabilizer", "8.25", "3.0", "1.5", "", "350", "API Reg", "22000", "Full gauge"],
            "Shock Sub": ["Shock Sub", "8.0", "3.0", "3.0", "", "450", "API NC", "28000", "Vibration dampener"]
        }
        
        default_data = defaults.get(tool_type, ["", "0.00", "0.00", "0.00", "", "0", "", "0", ""])
        
        for col, value in enumerate(default_data):
            item = QTableWidgetItem(str(value))
            if col in [1, 2, 3, 5, 7]:  # ستون‌های عددی
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, col, item)
        
        return row
    
    def calculate_totals(self):
        """محاسبه مجموع طول و وزن"""
        total_length = 0.0
        total_weight = 0.0
        
        for row in range(self.table.rowCount()):
            # طول
            length_item = self.table.item(row, 3)
            if length_item and length_item.text():
                try:
                    total_length += float(length_item.text())
                except:
                    pass
            
            # وزن
            weight_item = self.table.item(row, 5)
            if weight_item and weight_item.text():
                try:
                    total_weight += float(weight_item.text())
                except:
                    pass
        
        return total_length, total_weight
    
    def get_bha_summary(self):
        """دریافت خلاصه BHA"""
        total_length, total_weight = self.calculate_totals()
        
        summary = {
            "total_tools": self.table.rowCount(),
            "total_length_m": round(total_length, 2),
            "total_weight_kg": round(total_weight, 2),
            "average_od": self.calculate_average_od(),
            "tools_by_type": self.count_tools_by_type()
        }
        
        return summary
    
    def calculate_average_od(self):
        """محاسبه میانگین OD"""
        total_od = 0.0
        count = 0
        
        for row in range(self.table.rowCount()):
            od_item = self.table.item(row, 1)
            if od_item and od_item.text():
                try:
                    total_od += float(od_item.text())
                    count += 1
                except:
                    pass
        
        return round(total_od / count, 2) if count > 0 else 0.0
    
    def count_tools_by_type(self):
        """شمردن ابزارها بر اساس نوع"""
        tool_counts = {}
        
        for row in range(self.table.rowCount()):
            tool_type_item = self.table.item(row, 0)
            if tool_type_item and tool_type_item.text():
                tool_type = tool_type_item.text()
                tool_counts[tool_type] = tool_counts.get(tool_type, 0) + 1
        
        return tool_counts
    
    def save_bha(self, bha_name):
        """ذخیره BHA با نام مشخص"""
        if not bha_name:
            return False
        
        bha_data = self.get_all_data()
        self.saved_bhas[bha_name] = bha_data
        return True
    
    def load_bha(self, bha_name):
        """لود BHA با نام مشخص"""
        if bha_name in self.saved_bhas:
            self.load_data(self.saved_bhas[bha_name])
            return True
        return False
    
    def get_all_data(self):
        """دریافت تمام داده‌های BHA"""
        data = []
        headers = []
        
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())
        
        for row in range(self.table.rowCount()):
            row_data = {}
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data[headers[col]] = item.text() if item else ""
            data.append(row_data)
        
        return data
    
    def load_data(self, data):
        """لود داده در جدول"""
        self.table.setRowCount(0)
        
        if not data:
            return
        
        for row_data in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            for col, (header, value) in enumerate(row_data.items()):
                if col < self.table.columnCount():
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(row, col, item)


# ==================== Downhole Equipment Manager ====================
class DownholeEquipmentManager:
    """مدیریت تجهیزات زیر سطحی"""
    
    def __init__(self, table_widget):
        self.table = table_widget
        self.manager = TableManager(table_widget)
        
    def setup_table(self):
        """تنظیم جدول تجهیزات"""
        headers = [
            "Equipment Name", "Type", "Serial No", "ID", "Manufacturer",
            "Install Date", "Sliding Hours", "Rotation Hours", "Pumping Hours",
            "Total Hours", "Cycles", "Last Service", "Next Service", "Status", "Remarks"
        ]
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # تنظیم عرض ستون‌ها
        column_widths = [150, 100, 120, 80, 120, 100, 100, 100, 100, 100, 80, 100, 100, 80, 150]
        for col, width in enumerate(column_widths):
            self.table.setColumnWidth(col, width)
        
        # ستون تاریخ
        date_columns = [5, 11, 12]
        for col in date_columns:
            for row in range(self.table.rowCount()):
                if not self.table.item(row, col):
                    item = QTableWidgetItem(date.today().strftime("%Y-%m-%d"))
                    self.table.setItem(row, col, item)
    
    def add_default_row(self):
        """اضافه کردن سطر پیش‌فرض"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        default_data = [
            "", "", f"SN{row + 1:03d}", f"EQ{row + 1:03d}", "",
            date.today().strftime("%Y-%m-%d"), "0.0", "0.0", "0.0", "0.0",
            "0", date.today().strftime("%Y-%m-%d"), 
            (date.today() + pd.Timedelta(days=30)).strftime("%Y-%m-%d"),
            "Active", ""
        ]
        
        for col, value in enumerate(default_data):
            item = QTableWidgetItem(str(value))
            
            # تراز برای ستون‌های عددی
            if col in [6, 7, 8, 9, 10]:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            self.table.setItem(row, col, item)
        
        return row
    
    def calculate_hours(self):
        """محاسبه ساعات کاری"""
        totals = {
            "sliding": 0.0,
            "rotation": 0.0,
            "pumping": 0.0,
            "total": 0.0
        }
        
        for row in range(self.table.rowCount()):
            for i, key in enumerate(["sliding", "rotation", "pumping", "total"]):
                col = 6 + i  # شروع از ستون Sliding Hours
                item = self.table.item(row, col)
                if item and item.text():
                    try:
                        totals[key] += float(item.text())
                    except:
                        pass
        
        return totals
    
    def update_total_hours(self, row):
        """آپدیت ساعات کل برای سطر"""
        try:
            sliding = float(self.table.item(row, 6).text() or 0)
            rotation = float(self.table.item(row, 7).text() or 0)
            pumping = float(self.table.item(row, 8).text() or 0)
            
            total = sliding + rotation + pumping
            
            total_item = self.table.item(row, 9)
            if total_item:
                total_item.setText(f"{total:.1f}")
            
            return total
        except:
            return 0.0
    
    def check_service_due(self):
        """بررسی تجهیزاتی که نیاز به سرویس دارند"""
        due_equipment = []
        today = date.today()
        
        for row in range(self.table.rowCount()):
            next_service_item = self.table.item(row, 12)  # Next Service
            if next_service_item and next_service_item.text():
                try:
                    next_service = datetime.strptime(next_service_item.text(), "%Y-%m-%d").date()
                    if next_service <= today:
                        name_item = self.table.item(row, 0)
                        equipment_name = name_item.text() if name_item else f"Equipment {row + 1}"
                        due_equipment.append({
                            "name": equipment_name,
                            "next_service": next_service_item.text(),
                            "row": row
                        })
                except:
                    pass
        
        return due_equipment
    
    def get_all_data(self):
        """دریافت تمام داده‌های تجهیزات"""
        data = []
        headers = []
        
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())
        
        for row in range(self.table.rowCount()):
            row_data = {}
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data[headers[col]] = item.text() if item else ""
            data.append(row_data)
        
        return data
    
    def load_data(self, data):
        """لود داده در جدول"""
        self.table.setRowCount(0)
        
        if not data:
            return
        
        for row_data in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            for col, (header, value) in enumerate(row_data.items()):
                if col < self.table.columnCount():
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(row, col, item)


# ==================== Formation Manager ====================
class FormationManager:
    """مدیریت سازندها"""
    
    def __init__(self, table_widget):
        self.table = table_widget
        self.manager = TableManager(table_widget)
        self.current_color = "#FFFFFF"
        
    def setup_table(self):
        """تنظیم جدول سازندها"""
        headers = [
            "Formation Name", "Lithology", "Age", "Top MD (m)", "Base MD (m)",
            "Thickness (m)", "Top TVD (m)", "Color", "Description", "Properties"
        ]
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # تنظیم عرض ستون‌ها
        column_widths = [150, 100, 80, 100, 100, 100, 100, 80, 200, 150]
        for col, width in enumerate(column_widths):
            self.table.setColumnWidth(col, width)
        
        # ستون رنگ
        self.table.setColumnWidth(7, 60)
    
    def add_formation_row(self, formation_data=None):
        """اضافه کردن سطر سازند"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        if formation_data is None:
            formation_data = {
                "Formation Name": f"Formation {row + 1}",
                "Lithology": "Shale",
                "Age": "Cretaceous",
                "Top MD (m)": str(row * 100),
                "Base MD (m)": str((row + 1) * 100),
                "Thickness (m)": "100",
                "Top TVD (m)": str(row * 95),
                "Color": "#8B4513",  # قهوه‌ای
                "Description": "",
                "Properties": ""
            }
        
        for col, header in enumerate([
            "Formation Name", "Lithology", "Age", "Top MD (m)", "Base MD (m)",
            "Thickness (m)", "Top TVD (m)", "Color", "Description", "Properties"
        ]):
            value = formation_data.get(header, "")
            item = QTableWidgetItem(str(value))
            
            # ستون‌های عددی
            if col in [3, 4, 5, 6]:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # ستون رنگ
            if col == 7:
                item.setBackground(QColor(value))
                item.setText(value)
            
            self.table.setItem(row, col, item)
        
        # محاسبه ضخامت
        self.calculate_thickness(row)
        
        return row
    
    def calculate_thickness(self, row):
        """محاسبه ضخامت سازند"""
        try:
            top_item = self.table.item(row, 3)  # Top MD
            base_item = self.table.item(row, 4)  # Base MD
            
            if top_item and base_item:
                top = float(top_item.text() or 0)
                base = float(base_item.text() or 0)
                
                thickness = base - top
                if thickness < 0:
                    thickness = 0
                
                thickness_item = self.table.item(row, 5)  # Thickness
                if thickness_item:
                    thickness_item.setText(f"{thickness:.1f}")
                
                return thickness
        except:
            pass
        return 0.0
    
    def choose_color(self):
        """انتخاب رنگ برای سازند"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_color = color.name()
            return self.current_color
        return None
    
    def set_row_color(self, row, color_hex):
        """تنظیم رنگ برای سطر"""
        if 0 <= row < self.table.rowCount():
            color_item = self.table.item(row, 7)
            if color_item:
                color_item.setBackground(QColor(color_hex))
                color_item.setText(color_hex)
    
    def get_formation_at_depth(self, depth):
        """یافتن سازند در عمق مشخص"""
        for row in range(self.table.rowCount()):
            try:
                top_item = self.table.item(row, 3)  # Top MD
                base_item = self.table.item(row, 4)  # Base MD
                
                if top_item and base_item:
                    top = float(top_item.text() or 0)
                    base = float(base_item.text() or 0)
                    
                    if top <= depth <= base:
                        formation_data = {}
                        for col in range(self.table.columnCount()):
                            header_item = self.table.horizontalHeaderItem(col)
                            cell_item = self.table.item(row, col)
                            if header_item and cell_item:
                                formation_data[header_item.text()] = cell_item.text()
                        return formation_data
            except:
                continue
        return None
    
    def export_to_las(self, filepath):
        """اکسپورت داده‌های سازند به فایل LAS"""
        try:
            # ایجاد فایل LAS ساده
            las = lasio.LASFile()
            
            # اضافه کردن اطلاعات سازندها به عنوان curves
            depths = []
            formations = []
            lithologies = []
            
            for row in range(self.table.rowCount()):
                top_item = self.table.item(row, 3)
                base_item = self.table.item(row, 4)
                name_item = self.table.item(row, 0)
                lith_item = self.table.item(row, 1)
                
                if all([top_item, base_item, name_item, lith_item]):
                    try:
                        top = float(top_item.text())
                        base = float(base_item.text())
                        name = name_item.text()
                        lith = lith_item.text()
                        
                        # اضافه کردن نقاط میانی
                        mid_depth = (top + base) / 2
                        depths.append(mid_depth)
                        formations.append(name)
                        lithologies.append(lith)
                    except:
                        continue
            
            if depths:
                # مرتب‌سازی بر اساس عمق
                sorted_data = sorted(zip(depths, formations, lithologies))
                depths, formations, lithologies = zip(*sorted_data)
                
                # اضافه کردن curves
                las.add_curve("DEPT", depths, unit="m", descr="Depth")
                las.add_curve("FORMATION", formations, descr="Formation Name")
                las.add_curve("LITH", lithologies, descr="Lithology")
                
                # ذخیره فایل
                las.write(filepath, version=2.0)
                return True
        
        except Exception as e:
            logger.error(f"Error exporting to LAS: {e}")
        
        return False
    
    def import_from_las(self, filepath):
        """ایمپورت داده‌های سازند از فایل LAS"""
        try:
            las = lasio.read(filepath)
            
            # پاک کردن جدول موجود
            self.table.setRowCount(0)
            
            # بررسی وجود curves مورد نیاز
            if "DEPT" in las.curves and "FORMATION" in las.curves:
                depths = las.curves["DEPT"].data
                formations = las.curves["FORMATION"].data
                
                # گروه‌بندی سازندها بر اساس نام
                formation_groups = {}
                for depth, formation in zip(depths, formations):
                    if formation not in formation_groups:
                        formation_groups[formation] = []
                    formation_groups[formation].append(depth)
                
                # ایجاد سطر برای هر سازند
                for formation_name, depth_values in formation_groups.items():
                    if depth_values:
                        top_depth = min(depth_values)
                        base_depth = max(depth_values)
                        
                        formation_data = {
                            "Formation Name": str(formation_name),
                            "Lithology": "",
                            "Age": "",
                            "Top MD (m)": f"{top_depth:.1f}",
                            "Base MD (m)": f"{base_depth:.1f}",
                            "Color": self.generate_color_for_formation(formation_name),
                            "Description": f"Imported from LAS: {filepath}",
                            "Properties": ""
                        }
                        
                        self.add_formation_row(formation_data)
                
                return True
        
        except Exception as e:
            logger.error(f"Error importing from LAS: {e}")
        
        return False
    
    def generate_color_for_formation(self, formation_name):
        """تولید رنگ بر اساس نام سازند"""
        import hashlib
        
        # استفاده از hash برای تولید رنگ ثابت برای هر نام سازند
        hash_obj = hashlib.md5(formation_name.encode())
        hash_hex = hash_obj.hexdigest()[:6]
        
        # اطمینان از روشن بودن رنگ
        r = int(hash_hex[0:2], 16) % 200 + 55
        g = int(hash_hex[2:4], 16) % 200 + 55
        b = int(hash_hex[4:6], 16) % 200 + 55
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def get_all_data(self):
        """دریافت تمام داده‌های سازندها"""
        data = []
        headers = []
        
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())
        
        for row in range(self.table.rowCount()):
            row_data = {}
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data[headers[col]] = item.text() if item else ""
            data.append(row_data)
        
        return data
    
    def load_data(self, data):
        """لود داده در جدول"""
        self.table.setRowCount(0)
        
        if not data:
            return
        
        for row_data in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            for col, (header, value) in enumerate(row_data.items()):
                if col < self.table.columnCount():
                    item = QTableWidgetItem(str(value))
                    
                    # ستون رنگ
                    if col == 7 and value.startswith("#"):
                        item.setBackground(QColor(value))
                    
                    self.table.setItem(row, col, item)


# ==================== Main Downhole Widget ====================
class DownholeWidget(DrillWidgetBase):
    """ویجت اصلی مدیریت تجهیزات زیر سطحی"""
    
    def __init__(self, db_manager=None):
        super().__init__("DownholeWidget", db_manager)
        
        # متغیرهای حالت
        self.current_well = None
        self.current_report = None
        self.current_section = None
        
        # مدیرها
        self.bit_manager = None
        self.bha_manager = None
        self.equipment_manager = None
        self.formation_manager = None
        
        # داده‌های محلی
        self.bha_data = {}  # ذخیره BHAها
        self.saved_formations = {}  # ذخیره سازندها
        
        # راه‌اندازی UI
        self.init_ui()
        self.setup_managers()
        self.setup_connections()
        
        logger.info("DownholeWidget initialized")
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ایجاد تب‌ها
        self.tab_widget = QTabWidget()
        
        # تب رکوردهای مته
        self.bit_tab = self.create_bit_tab()
        self.tab_widget.addTab(self.bit_tab, "📝 Bit Record")
        
        # تب BHA
        self.bha_tab = self.create_bha_tab()
        self.tab_widget.addTab(self.bha_tab, "🔧 BHA")
        
        # تب تجهیزات
        self.equipment_tab = self.create_equipment_tab()
        self.tab_widget.addTab(self.equipment_tab, "⚙️ Downhole Equipment")
        
        # تب سازندها
        self.formation_tab = self.create_formation_tab()
        self.tab_widget.addTab(self.formation_tab, "🏔️ Formation Evaluation")
        
        main_layout.addWidget(self.tab_widget)
        
        # نوار وضعیت
        self.status_layout = QHBoxLayout()
        
        self.well_label = QLabel("Well: Not Selected")
        self.well_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.status_layout.addWidget(self.well_label)
        
        self.status_layout.addStretch()
        
        self.save_status_label = QLabel("💾 Auto-save: ON")
        self.status_layout.addWidget(self.save_status_label)
        
        main_layout.addLayout(self.status_layout)
        
        self.setLayout(main_layout)
    
    def create_bit_tab(self):
        """ایجاد تب رکوردهای مته"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # هدر تب
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Bit Record Management</h3>"))
        header_layout.addStretch()
        
        # دکمه‌های عملیاتی
        btn_layout = QHBoxLayout()
        
        self.add_bit_btn = QPushButton("➕ Add Bit Record")
        self.add_bit_btn.setToolTip("Add new bit record")
        
        self.remove_bit_btn = QPushButton("➖ Remove Selected")
        self.remove_bit_btn.setToolTip("Remove selected bit record")
        
        self.calculate_rop_btn = QPushButton("🧮 Calculate ROP")
        self.calculate_rop_btn.setToolTip("Calculate ROP for all bits")
        
        self.generate_report_btn = QPushButton("📄 Generate Report")
        self.generate_report_btn.setToolTip("Generate bit report")
        
        self.export_bit_btn = QPushButton("📤 Export Data")
        self.export_bit_btn.setToolTip("Export bit records")
        
        self.import_bit_btn = QPushButton("📂 Import Data")
        self.import_bit_btn.setToolTip("Import bit records")
        
        btn_layout.addWidget(self.add_bit_btn)
        btn_layout.addWidget(self.remove_bit_btn)
        btn_layout.addWidget(self.calculate_rop_btn)
        btn_layout.addWidget(self.generate_report_btn)
        btn_layout.addWidget(self.export_bit_btn)
        btn_layout.addWidget(self.import_bit_btn)
        btn_layout.addStretch()
        
        # جدول رکوردهای مته
        self.bit_table = QTableWidget()
        self.bit_table.setAlternatingRowColors(True)
        self.bit_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # اضافه کردن به layout
        layout.addLayout(header_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.bit_table)
        
        tab.setLayout(layout)
        return tab
    
    def create_bha_tab(self):
        """ایجاد تب BHA"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # هدر تب با انتخاب BHA
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>BHA Configuration</h3>"))
        header_layout.addStretch()
        
        bha_selection_layout = QHBoxLayout()
        bha_selection_layout.addWidget(QLabel("BHA Name:"))
        
        self.bha_name_input = QLineEdit()
        self.bha_name_input.setPlaceholderText("Enter BHA name...")
        self.bha_name_input.setMinimumWidth(200)
        bha_selection_layout.addWidget(self.bha_name_input)
        
        bha_selection_layout.addWidget(QLabel("Saved BHAs:"))
        
        self.bha_selector = QComboBox()
        self.bha_selector.addItem("-- Select BHA --")
        self.bha_selector.setMinimumWidth(150)
        bha_selection_layout.addWidget(self.bha_selector)
        
        bha_selection_layout.addStretch()
        
        # دکمه‌های عملیاتی BHA
        btn_layout = QHBoxLayout()
        
        self.add_bha_tool_btn = QPushButton("➕ Add Tool")
        self.add_bha_tool_btn.setToolTip("Add tool to BHA")
        
        self.remove_bha_tool_btn = QPushButton("➖ Remove Tool")
        self.remove_bha_tool_btn.setToolTip("Remove selected tool")
        
        self.save_bha_btn = QPushButton("💾 Save BHA")
        self.save_bha_btn.setToolTip("Save current BHA configuration")
        
        self.load_bha_btn = QPushButton("📂 Load BHA")
        self.load_bha_btn.setToolTip("Load saved BHA")
        
        self.delete_bha_btn = QPushButton("🗑️ Delete BHA")
        self.delete_bha_btn.setToolTip("Delete saved BHA")
        
        self.calculate_bha_btn = QPushButton("🧮 Calculate Totals")
        self.calculate_bha_btn.setToolTip("Calculate BHA totals")
        
        self.export_bha_btn = QPushButton("📤 Export BHA")
        self.export_bha_btn.setToolTip("Export BHA data")
        
        btn_layout.addWidget(self.add_bha_tool_btn)
        btn_layout.addWidget(self.remove_bha_tool_btn)
        btn_layout.addWidget(self.save_bha_btn)
        btn_layout.addWidget(self.load_bha_btn)
        btn_layout.addWidget(self.delete_bha_btn)
        btn_layout.addWidget(self.calculate_bha_btn)
        btn_layout.addWidget(self.export_bha_btn)
        btn_layout.addStretch()
        
        # جدول BHA
        self.bha_table = QTableWidget()
        self.bha_table.setAlternatingRowColors(True)
        self.bha_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # اضافه کردن به layout
        layout.addLayout(header_layout)
        layout.addLayout(bha_selection_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.bha_table)
        
        tab.setLayout(layout)
        return tab
    
    def create_equipment_tab(self):
        """ایجاد تب تجهیزات"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # هدر تب
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Downhole Equipment Management</h3>"))
        header_layout.addStretch()
        
        # دکمه‌های عملیاتی
        btn_layout = QHBoxLayout()
        
        self.add_equipment_btn = QPushButton("➕ Add Equipment")
        self.add_equipment_btn.setToolTip("Add new equipment")
        
        self.remove_equipment_btn = QPushButton("➖ Remove Equipment")
        self.remove_equipment_btn.setToolTip("Remove selected equipment")
        
        self.calculate_hours_btn = QPushButton("🔄 Calculate Hours")
        self.calculate_hours_btn.setToolTip("Calculate equipment hours")
        
        self.check_service_btn = QPushButton("🔍 Check Service Due")
        self.check_service_btn.setToolTip("Check equipment due for service")
        
        self.save_equipment_btn = QPushButton("💾 Save Equipment")
        self.save_equipment_btn.setToolTip("Save equipment data")
        
        self.export_equipment_btn = QPushButton("📤 Export Data")
        self.export_equipment_btn.setToolTip("Export equipment data")
        
        self.import_equipment_btn = QPushButton("📂 Import Data")
        self.import_equipment_btn.setToolTip("Import equipment data")
        
        btn_layout.addWidget(self.add_equipment_btn)
        btn_layout.addWidget(self.remove_equipment_btn)
        btn_layout.addWidget(self.calculate_hours_btn)
        btn_layout.addWidget(self.check_service_btn)
        btn_layout.addWidget(self.save_equipment_btn)
        btn_layout.addWidget(self.export_equipment_btn)
        btn_layout.addWidget(self.import_equipment_btn)
        btn_layout.addStretch()
        
        # جدول تجهیزات
        self.equipment_table = QTableWidget()
        self.equipment_table.setAlternatingRowColors(True)
        self.equipment_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # اضافه کردن به layout
        layout.addLayout(header_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.equipment_table)
        
        tab.setLayout(layout)
        return tab
    
    def create_formation_tab(self):
        """ایجاد تب سازندها"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # هدر تب
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Formation Evaluation</h3>"))
        header_layout.addStretch()
        
        # فرم اضافه کردن سازند
        form_group = QGroupBox("Add New Formation")
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("Formation Name:"), 0, 0)
        self.formation_name_input = QLineEdit()
        self.formation_name_input.setPlaceholderText("e.g., Upper Shale")
        form_layout.addWidget(self.formation_name_input, 0, 1)
        
        form_layout.addWidget(QLabel("Lithology:"), 0, 2)
        self.lithology_input = QLineEdit()
        self.lithology_input.setPlaceholderText("e.g., Shale, Sandstone")
        form_layout.addWidget(self.lithology_input, 0, 3)
        
        form_layout.addWidget(QLabel("Top MD (m):"), 1, 0)
        self.top_md_input = QDoubleSpinBox()
        self.top_md_input.setRange(0, 20000)
        self.top_md_input.setDecimals(1)
        form_layout.addWidget(self.top_md_input, 1, 1)
        
        form_layout.addWidget(QLabel("Base MD (m):"), 1, 2)
        self.base_md_input = QDoubleSpinBox()
        self.base_md_input.setRange(0, 20000)
        self.base_md_input.setDecimals(1)
        form_layout.addWidget(self.base_md_input, 1, 3)
        
        form_layout.addWidget(QLabel("Color:"), 2, 0)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 30)
        self.color_btn.setStyleSheet("background-color: #8B4513;")
        form_layout.addWidget(self.color_btn, 2, 1)
        
        form_layout.addWidget(QLabel("Description:"), 2, 2)
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Formation description...")
        form_layout.addWidget(self.description_input, 2, 3)
        
        form_group.setLayout(form_layout)
        
        # دکمه‌های عملیاتی سازندها
        btn_layout = QHBoxLayout()
        
        self.add_formation_btn = QPushButton("➕ Add Formation")
        self.add_formation_btn.setToolTip("Add new formation")
        
        self.remove_formation_btn = QPushButton("➖ Remove Formation")
        self.remove_formation_btn.setToolTip("Remove selected formation")
        
        self.save_formations_btn = QPushButton("💾 Save Formations")
        self.save_formations_btn.setToolTip("Save formation data")
        
        self.load_formations_btn = QPushButton("📂 Load Formations")
        self.load_formations_btn.setToolTip("Load saved formations")
        
        self.export_formations_btn = QPushButton("📤 Export to CSV")
        self.export_formations_btn.setToolTip("Export formations to CSV")
        
        self.import_las_btn = QPushButton("📊 Import LAS")
        self.import_las_btn.setToolTip("Import from LAS file")
        
        self.export_las_btn = QPushButton("📊 Export LAS")
        self.export_las_btn.setToolTip("Export to LAS file")
        
        btn_layout.addWidget(self.add_formation_btn)
        btn_layout.addWidget(self.remove_formation_btn)
        btn_layout.addWidget(self.save_formations_btn)
        btn_layout.addWidget(self.load_formations_btn)
        btn_layout.addWidget(self.export_formations_btn)
        btn_layout.addWidget(self.import_las_btn)
        btn_layout.addWidget(self.export_las_btn)
        btn_layout.addStretch()
        
        # جدول سازندها
        self.formation_table = QTableWidget()
        self.formation_table.setAlternatingRowColors(True)
        self.formation_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # اضافه کردن به layout
        layout.addLayout(header_layout)
        layout.addWidget(form_group)
        layout.addLayout(btn_layout)
        layout.addWidget(self.formation_table)
        
        tab.setLayout(layout)
        return tab
    
    def setup_managers(self):
        """تنظیم مدیرها"""
        # مدیر رکوردهای مته
        self.bit_manager = BitRecordManager(self.bit_table)
        self.bit_manager.setup_table()
        
        # مدیر BHA
        self.bha_manager = BHAManager(self.bha_table)
        self.bha_manager.setup_table()
        
        # مدیر تجهیزات
        self.equipment_manager = DownholeEquipmentManager(self.equipment_table)
        self.equipment_manager.setup_table()
        
        # مدیر سازندها
        self.formation_manager = FormationManager(self.formation_table)
        self.formation_manager.setup_table()
        
        logger.info("All managers setup complete")
    
    def setup_connections(self):
        """تنظیم اتصالات"""
        try:
            # Bit Tab Connections
            self.add_bit_btn.clicked.connect(self.add_bit_record)
            self.remove_bit_btn.clicked.connect(self.remove_bit_record)
            self.calculate_rop_btn.clicked.connect(self.calculate_all_rop)
            self.generate_report_btn.clicked.connect(self.generate_bit_report)
            self.export_bit_btn.clicked.connect(self.export_bit_data)
            self.import_bit_btn.clicked.connect(self.import_bit_data)
            
            # BHA Tab Connections
            self.add_bha_tool_btn.clicked.connect(self.add_bha_tool)
            self.remove_bha_tool_btn.clicked.connect(self.remove_bha_tool)
            self.save_bha_btn.clicked.connect(self.save_bha_config)
            self.load_bha_btn.clicked.connect(self.load_bha_config)
            self.delete_bha_btn.clicked.connect(self.delete_bha_config)
            self.calculate_bha_btn.clicked.connect(self.calculate_bha_totals)
            self.export_bha_btn.clicked.connect(self.export_bha_data)
            self.bha_selector.currentTextChanged.connect(self.on_bha_selected)
            
            # Equipment Tab Connections
            self.add_equipment_btn.clicked.connect(self.add_equipment)
            self.remove_equipment_btn.clicked.connect(self.remove_equipment)
            self.calculate_hours_btn.clicked.connect(self.calculate_equipment_hours)
            self.check_service_btn.clicked.connect(self.check_service_due)
            self.save_equipment_btn.clicked.connect(self.save_equipment_data)
            self.export_equipment_btn.clicked.connect(self.export_equipment_data)
            self.import_equipment_btn.clicked.connect(self.import_equipment_data)
            
            # Formation Tab Connections
            self.add_formation_btn.clicked.connect(self.add_formation)
            self.remove_formation_btn.clicked.connect(self.remove_formation)
            self.save_formations_btn.clicked.connect(self.save_formations)
            self.load_formations_btn.clicked.connect(self.load_formations)
            self.export_formations_btn.clicked.connect(self.export_formations_csv)
            self.import_las_btn.clicked.connect(self.import_las_file)
            self.export_las_btn.clicked.connect(self.export_las_file)
            self.color_btn.clicked.connect(self.choose_formation_color)
            
            # جدول رویدادها
            self.bit_table.itemChanged.connect(self.on_bit_data_changed)
            self.bha_table.itemChanged.connect(self.on_bha_data_changed)
            self.equipment_table.itemChanged.connect(self.on_equipment_data_changed)
            self.formation_table.itemChanged.connect(self.on_formation_data_changed)
            
            logger.info("All connections setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up connections: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to setup connections: {str(e)}"
            )
    
    # ==================== Bit Tab Methods ====================
    def add_bit_record(self):
        """اضافه کردن رکورد مته جدید"""
        try:
            row = self.bit_manager.add_default_row()
            self.bit_table.scrollToItem(self.bit_table.item(row, 0))
            self.status_manager.show_success(
                "DownholeWidget",
                f"Bit record #{row + 1} added"
            )
        except Exception as e:
            logger.error(f"Error adding bit record: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to add bit record: {str(e)}"
            )
    
    def remove_bit_record(self):
        """حذف رکورد مته انتخاب شده"""
        current_row = self.bit_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self,
                "Remove Bit Record",
                f"Are you sure you want to remove bit record #{current_row + 1}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.bit_table.removeRow(current_row)
                self.status_manager.show_success(
                    "DownholeWidget",
                    "Bit record removed"
                )
        else:
            self.status_manager.show_message(
                "DownholeWidget",
                "Please select a bit record to remove",
                2000
            )
    
    def calculate_all_rop(self):
        """محاسبه ROP برای تمام مته‌ها"""
        try:
            for row in range(self.bit_table.rowCount()):
                self.bit_manager.calculate_rop(row)
            
            self.status_manager.show_success(
                "DownholeWidget",
                f"ROP calculated for {self.bit_table.rowCount()} bits"
            )
        except Exception as e:
            logger.error(f"Error calculating ROP: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to calculate ROP: {str(e)}"
            )
    
    def generate_bit_report(self):
        """تولید گزارش مته‌ها"""
        try:
            if self.bit_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No bit records to generate report",
                    3000
                )
                return
            
            from datetime import datetime
            import pandas as pd
            
            # جمع‌آوری داده‌ها
            data = self.bit_manager.get_all_data()
            
            # ایجاد DataFrame
            df = pd.DataFrame(data)
            
            # ذخیره در فایل
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Bit Report",
                f"bit_report_{timestamp}.xlsx",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            
            if filename:
                if filename.endswith('.xlsx'):
                    df.to_excel(filename, index=False)
                else:
                    df.to_csv(filename, index=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Bit report saved: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error generating bit report: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to generate report: {str(e)}"
            )
    
    def export_bit_data(self):
        """اکسپورت داده‌های مته"""
        try:
            if self.bit_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No bit data to export",
                    3000
                )
                return
            
            data = self.bit_manager.get_all_data()
            
            # ذخیره در فایل JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Bit Data",
                f"bit_data_{timestamp}.json",
                "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Bit data exported: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error exporting bit data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to export data: {str(e)}"
            )
    
    def import_bit_data(self):
        """ایمپورت داده‌های مته"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Import Bit Data",
                "",
                "JSON Files (*.json);;CSV Files (*.csv);;Excel Files (*.xlsx)"
            )
            
            if filename:
                if filename.endswith('.json'):
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                elif filename.endswith('.csv'):
                    import pandas as pd
                    df = pd.read_csv(filename)
                    data = df.to_dict('records')
                else:  # Excel
                    import pandas as pd
                    df = pd.read_excel(filename)
                    data = df.to_dict('records')
                
                # لود داده در جدول
                self.bit_manager.load_data(data)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Bit data imported: {len(data)} records"
                )
        
        except Exception as e:
            logger.error(f"Error importing bit data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to import data: {str(e)}"
            )
    
    # ==================== BHA Tab Methods ====================
    def add_bha_tool(self):
        """اضافه کردن ابزار به BHA"""
        try:
            # دیالوگ انتخاب نوع ابزار
            tool_types = ["Bit", "Drill Collar", "MWD", "Stabilizer", "Shock Sub", "Other"]
            tool_type, ok = QInputDialog.getItem(
                self,
                "Select Tool Type",
                "Choose tool type:",
                tool_types,
                0,
                False
            )
            
            if ok and tool_type:
                row = self.bha_manager.add_default_row(tool_type)
                self.bha_table.scrollToItem(self.bha_table.item(row, 0))
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"{tool_type} added to BHA"
                )
        
        except Exception as e:
            logger.error(f"Error adding BHA tool: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to add tool: {str(e)}"
            )
    
    def remove_bha_tool(self):
        """حذف ابزار از BHA"""
        current_row = self.bha_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self,
                "Remove Tool",
                "Are you sure you want to remove this tool from BHA?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.bha_table.removeRow(current_row)
                self.status_manager.show_success(
                    "DownholeWidget",
                    "Tool removed from BHA"
                )
        else:
            self.status_manager.show_message(
                "DownholeWidget",
                "Please select a tool to remove",
                2000
            )
    
    def save_bha_config(self):
        """ذخیره پیکربندی BHA"""
        try:
            bha_name = self.bha_name_input.text().strip()
            if not bha_name:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "Please enter BHA name",
                    3000
                )
                return
            
            if self.bha_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "BHA is empty",
                    3000
                )
                return
            
            # ذخیره BHA
            if self.bha_manager.save_bha(bha_name):
                self.bha_data[bha_name] = self.bha_manager.get_all_data()
                self.update_bha_selector()
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"BHA '{bha_name}' saved"
                )
            else:
                self.status_manager.show_error(
                    "DownholeWidget",
                    "Failed to save BHA"
                )
        
        except Exception as e:
            logger.error(f"Error saving BHA: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to save BHA: {str(e)}"
            )
    
    def load_bha_config(self):
        """لود پیکربندی BHA"""
        try:
            bha_name = self.bha_name_input.text().strip()
            if not bha_name:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "Please enter BHA name",
                    3000
                )
                return
            
            if self.bha_manager.load_bha(bha_name):
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"BHA '{bha_name}' loaded"
                )
            else:
                self.status_manager.show_error(
                    "DownholeWidget",
                    f"BHA '{bha_name}' not found"
                )
        
        except Exception as e:
            logger.error(f"Error loading BHA: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to load BHA: {str(e)}"
            )
    
    def delete_bha_config(self):
        """حذف پیکربندی BHA"""
        try:
            bha_name = self.bha_name_input.text().strip()
            if not bha_name:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "Please enter BHA name",
                    3000
                )
                return
            
            if bha_name in self.bha_data:
                reply = QMessageBox.question(
                    self,
                    "Delete BHA",
                    f"Are you sure you want to delete BHA '{bha_name}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    del self.bha_data[bha_name]
                    self.update_bha_selector()
                    self.bha_name_input.clear()
                    self.bha_table.setRowCount(0)
                    
                    self.status_manager.show_success(
                        "DownholeWidget",
                        f"BHA '{bha_name}' deleted"
                    )
            else:
                self.status_manager.show_message(
                    "DownholeWidget",
                    f"BHA '{bha_name}' not found",
                    3000
                )
        
        except Exception as e:
            logger.error(f"Error deleting BHA: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to delete BHA: {str(e)}"
            )
    
    def calculate_bha_totals(self):
        """محاسبه مجموع BHA"""
        try:
            total_length, total_weight = self.bha_manager.calculate_totals()
            
            QMessageBox.information(
                self,
                "BHA Summary",
                f"Total Tools: {self.bha_table.rowCount()}\n"
                f"Total Length: {total_length:.2f} m\n"
                f"Total Weight: {total_weight:.0f} kg"
            )
        
        except Exception as e:
            logger.error(f"Error calculating BHA totals: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to calculate totals: {str(e)}"
            )
    
    def export_bha_data(self):
        """اکسپورت داده‌های BHA"""
        try:
            if self.bha_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No BHA data to export",
                    3000
                )
                return
            
            data = self.bha_manager.get_all_data()
            
            # ذخیره در فایل JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export BHA Data",
                f"bha_data_{timestamp}.json",
                "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"BHA data exported: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error exporting BHA data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to export data: {str(e)}"
            )
    
    def update_bha_selector(self):
        """آپدیت انتخابگر BHA"""
        self.bha_selector.clear()
        self.bha_selector.addItem("-- Select BHA --")
        self.bha_selector.addItems(self.bha_data.keys())
    
    def on_bha_selected(self, bha_name):
        """وقتی BHA انتخاب شد"""
        if bha_name != "-- Select BHA --":
            self.bha_name_input.setText(bha_name)
            self.load_bha_config()
    
    # ==================== Equipment Tab Methods ====================
    def add_equipment(self):
        """اضافه کردن تجهیز جدید"""
        try:
            row = self.equipment_manager.add_default_row()
            self.equipment_table.scrollToItem(self.equipment_table.item(row, 0))
            
            self.status_manager.show_success(
                "DownholeWidget",
                f"Equipment #{row + 1} added"
            )
        
        except Exception as e:
            logger.error(f"Error adding equipment: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to add equipment: {str(e)}"
            )
    
    def remove_equipment(self):
        """حذف تجهیز انتخاب شده"""
        current_row = self.equipment_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self,
                "Remove Equipment",
                "Are you sure you want to remove this equipment?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.equipment_table.removeRow(current_row)
                self.status_manager.show_success(
                    "DownholeWidget",
                    "Equipment removed"
                )
        else:
            self.status_manager.show_message(
                "DownholeWidget",
                "Please select equipment to remove",
                2000
            )
    
    def calculate_equipment_hours(self):
        """محاسبه ساعات تجهیزات"""
        try:
            totals = self.equipment_manager.calculate_hours()
            
            QMessageBox.information(
                self,
                "Equipment Hours Summary",
                f"Total Sliding Hours: {totals['sliding']:.1f}\n"
                f"Total Rotation Hours: {totals['rotation']:.1f}\n"
                f"Total Pumping Hours: {totals['pumping']:.1f}\n"
                f"Total Overall Hours: {totals['total']:.1f}\n"
                f"Number of Equipment: {self.equipment_table.rowCount()}"
            )
        
        except Exception as e:
            logger.error(f"Error calculating equipment hours: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to calculate hours: {str(e)}"
            )
    
    def check_service_due(self):
        """بررسی تجهیزاتی که نیاز به سرویس دارند"""
        try:
            due_equipment = self.equipment_manager.check_service_due()
            
            if due_equipment:
                message = "Equipment due for service:\n\n"
                for eq in due_equipment:
                    message += f"• {eq['name']} (Next Service: {eq['next_service']})\n"
                
                QMessageBox.warning(
                    self,
                    "Service Due Alert",
                    message
                )
            else:
                QMessageBox.information(
                    self,
                    "Service Status",
                    "All equipment are up-to-date with service."
                )
        
        except Exception as e:
            logger.error(f"Error checking service due: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to check service: {str(e)}"
            )
    
    def save_equipment_data(self):
        """ذخیره داده‌های تجهیزات"""
        try:
            if self.equipment_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No equipment data to save",
                    3000
                )
                return
            
            data = self.equipment_manager.get_all_data()
            
            # ذخیره در فایل JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Equipment Data",
                f"equipment_data_{timestamp}.json",
                "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Equipment data saved: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error saving equipment data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to save data: {str(e)}"
            )
    
    def export_equipment_data(self):
        """اکسپورت داده‌های تجهیزات"""
        try:
            if self.equipment_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No equipment data to export",
                    3000
                )
                return
            
            data = self.equipment_manager.get_all_data()
            
            # ذخیره در فایل CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Equipment Data",
                f"equipment_export_{timestamp}.csv",
                "CSV Files (*.csv);;Excel Files (*.xlsx)"
            )
            
            if filename:
                df = pd.DataFrame(data)
                if filename.endswith('.csv'):
                    df.to_csv(filename, index=False)
                else:
                    df.to_excel(filename, index=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Equipment data exported: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error exporting equipment data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to export data: {str(e)}"
            )
    
    def import_equipment_data(self):
        """ایمپورت داده‌های تجهیزات"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Import Equipment Data",
                "",
                "JSON Files (*.json);;CSV Files (*.csv);;Excel Files (*.xlsx)"
            )
            
            if filename:
                if filename.endswith('.json'):
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                elif filename.endswith('.csv'):
                    df = pd.read_csv(filename)
                    data = df.to_dict('records')
                else:  # Excel
                    df = pd.read_excel(filename)
                    data = df.to_dict('records')
                
                # لود داده در جدول
                self.equipment_manager.load_data(data)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Equipment data imported: {len(data)} records"
                )
        
        except Exception as e:
            logger.error(f"Error importing equipment data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to import data: {str(e)}"
            )
    
    # ==================== Formation Tab Methods ====================
    def choose_formation_color(self):
        """انتخاب رنگ برای سازند"""
        try:
            color = self.formation_manager.choose_color()
            if color:
                self.color_btn.setStyleSheet(f"background-color: {color};")
        except Exception as e:
            logger.error(f"Error choosing color: {e}")
    
    def add_formation(self):
        """اضافه کردن سازند جدید"""
        try:
            formation_name = self.formation_name_input.text().strip()
            lithology = self.lithology_input.text().strip()
            top_md = self.top_md_input.value()
            base_md = self.base_md_input.value()
            description = self.description_input.text().strip()
            
            if not formation_name:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "Please enter formation name",
                    3000
                )
                return
            
            if base_md <= top_md:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "Base MD must be greater than Top MD",
                    3000
                )
                return
            
            # بررسی همپوشانی عمق
            formation_at_depth = self.formation_manager.get_formation_at_depth(top_md)
            if formation_at_depth:
                reply = QMessageBox.question(
                    self,
                    "Depth Overlap",
                    f"Depth overlaps with existing formation: {formation_at_depth.get('Formation Name')}\n"
                    "Do you want to continue?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # ایجاد داده سازند
            formation_data = {
                "Formation Name": formation_name,
                "Lithology": lithology,
                "Age": "",
                "Top MD (m)": f"{top_md:.1f}",
                "Base MD (m)": f"{base_md:.1f}",
                "Color": self.formation_manager.current_color,
                "Description": description,
                "Properties": ""
            }
            
            # اضافه کردن به جدول
            row = self.formation_manager.add_formation_row(formation_data)
            self.formation_table.scrollToItem(self.formation_table.item(row, 0))
            
            # پاک کردن فرم
            self.formation_name_input.clear()
            self.lithology_input.clear()
            self.top_md_input.setValue(0)
            self.base_md_input.setValue(0)
            self.description_input.clear()
            
            self.status_manager.show_success(
                "DownholeWidget",
                f"Formation '{formation_name}' added"
            )
        
        except Exception as e:
            logger.error(f"Error adding formation: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to add formation: {str(e)}"
            )
    
    def remove_formation(self):
        """حذف سازند انتخاب شده"""
        current_row = self.formation_table.currentRow()
        if current_row >= 0:
            formation_name = self.formation_table.item(current_row, 0).text()
            
            reply = QMessageBox.question(
                self,
                "Remove Formation",
                f"Are you sure you want to remove formation '{formation_name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.formation_table.removeRow(current_row)
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Formation '{formation_name}' removed"
                )
        else:
            self.status_manager.show_message(
                "DownholeWidget",
                "Please select a formation to remove",
                2000
            )
    
    def save_formations(self):
        """ذخیره داده‌های سازندها"""
        try:
            if self.formation_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No formation data to save",
                    3000
                )
                return
            
            data = self.formation_manager.get_all_data()
            
            # ذخیره در فایل JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Formation Data",
                f"formation_data_{timestamp}.json",
                "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Formation data saved: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error saving formation data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to save data: {str(e)}"
            )
    
    def load_formations(self):
        """لود داده‌های سازندها"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Load Formation Data",
                "",
                "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # لود داده در جدول
                self.formation_manager.load_data(data)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Formation data loaded: {len(data)} records"
                )
        
        except Exception as e:
            logger.error(f"Error loading formation data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to load data: {str(e)}"
            )
    
    def export_formations_csv(self):
        """اکسپورت سازندها به CSV"""
        try:
            if self.formation_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No formation data to export",
                    3000
                )
                return
            
            data = self.formation_manager.get_all_data()
            
            # ذخیره در فایل CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Formation Data",
                f"formations_{timestamp}.csv",
                "CSV Files (*.csv);;Excel Files (*.xlsx)"
            )
            
            if filename:
                df = pd.DataFrame(data)
                if filename.endswith('.csv'):
                    df.to_csv(filename, index=False)
                else:
                    df.to_excel(filename, index=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"Formation data exported: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error exporting formation data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to export data: {str(e)}"
            )
    
    def import_las_file(self):
        """ایمپورت فایل LAS"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Import LAS File",
                "",
                "LAS Files (*.las)"
            )
            
            if filename:
                if self.formation_manager.import_from_las(filename):
                    self.status_manager.show_success(
                        "DownholeWidget",
                        f"LAS file imported: {filename}"
                    )
                else:
                    self.status_manager.show_error(
                        "DownholeWidget",
                        f"Failed to import LAS file: {filename}"
                    )
        
        except Exception as e:
            logger.error(f"Error importing LAS file: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to import LAS: {str(e)}"
            )
    
    def export_las_file(self):
        """اکسپورت به فایل LAS"""
        try:
            if self.formation_table.rowCount() == 0:
                self.status_manager.show_message(
                    "DownholeWidget",
                    "No formation data to export",
                    3000
                )
                return
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export to LAS",
                f"formations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.las",
                "LAS Files (*.las)"
            )
            
            if filename:
                if self.formation_manager.export_to_las(filename):
                    self.status_manager.show_success(
                        "DownholeWidget",
                        f"Formation data exported to LAS: {filename}"
                    )
                else:
                    self.status_manager.show_error(
                        "DownholeWidget",
                        f"Failed to export to LAS: {filename}"
                    )
        
        except Exception as e:
            logger.error(f"Error exporting to LAS: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to export to LAS: {str(e)}"
            )
    
    # ==================== Event Handlers ====================
    def on_bit_data_changed(self, item):
        """وقتی داده‌های مته تغییر کرد"""
        if item.column() in [12, 13]:  # Metres Drilled یا Hours
            row = item.row()
            self.bit_manager.calculate_rop(row)
    
    def on_bha_data_changed(self, item):
        """وقتی داده‌های BHA تغییر کرد"""
        pass
    
    def on_equipment_data_changed(self, item):
        """وقتی داده‌های تجهیزات تغییر کرد"""
        if item.column() in [6, 7, 8]:  # Sliding, Rotation, یا Pumping Hours
            row = item.row()
            self.equipment_manager.update_total_hours(row)
    
    def on_formation_data_changed(self, item):
        """وقتی داده‌های سازند تغییر کرد"""
        if item.column() in [3, 4]:  # Top MD یا Base MD
            row = item.row()
            self.formation_manager.calculate_thickness(row)
    
    # ==================== Base Class Methods ====================
    def load_from_report_data(self, report_data):
        """لود داده‌های تب از report_data"""
        try:
            if isinstance(report_data, dict):
                # Bit Records
                if 'bit_records' in report_data:
                    self.bit_manager.load_data(report_data['bit_records'])
                
                # BHA Configurations
                if 'bha_configs' in report_data:
                    self.bha_data = report_data['bha_configs']
                    self.update_bha_selector()
                
                # Equipment Data
                if 'equipment_data' in report_data:
                    self.equipment_manager.load_data(report_data['equipment_data'])
                
                # Formations
                if 'formations' in report_data:
                    self.formation_manager.load_data(report_data['formations'])
                
                logger.info("Downhole data loaded from report")
        except Exception as e:
            logger.error(f"Error loading from report data: {e}")
    
    def save_to_report_data(self):
        """ذخیره داده‌های تب در report_data"""
        try:
            report_data = {
                'bit_records': self.bit_manager.get_all_data(),
                'bha_configs': self.bha_data,
                'equipment_data': self.equipment_manager.get_all_data(),
                'formations': self.formation_manager.get_all_data(),
                'last_updated': datetime.now().isoformat()
            }
            return report_data
        except Exception as e:
            logger.error(f"Error saving to report data: {e}")
            return {}
    
    def load_tab_data_from_report(self, report_id):
        """لود داده‌های تب از گزارش - برای استفاده در MainWindow"""
        return self.load_tab_data(report_id, 'downhole')
    
    def refresh(self):
        """رفرش داده‌ها"""
        super().refresh()
        
        # آپدیت انتخابگر BHA
        self.update_bha_selector()
        
        # آپدیت وضعیت
        self.status_manager.show_success(
            "DownholeWidget",
            "Data refreshed"
        )
    
    def clear_data(self):
        """پاک کردن تمام داده‌ها"""
        reply = QMessageBox.question(
            self,
            "Clear All Data",
            "Are you sure you want to clear all downhole data?\n\n"
            "This will clear:\n"
            "- All bit records\n"
            "- All BHA configurations\n"
            "- All equipment data\n"
            "- All formation data",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.bit_table.setRowCount(0)
            self.bha_table.setRowCount(0)
            self.equipment_table.setRowCount(0)
            self.formation_table.setRowCount(0)
            
            self.bha_data.clear()
            self.update_bha_selector()
            self.bha_name_input.clear()
            
            self.status_manager.show_success(
                "DownholeWidget",
                "All data cleared"
            )
    
    def export_data(self):
        """اکسپورت تمام داده‌ها"""
        try:
            # جمع‌آوری تمام داده‌ها
            all_data = {
                'bit_records': self.bit_manager.get_all_data(),
                'bha_configs': self.bha_data,
                'equipment_data': self.equipment_manager.get_all_data(),
                'formations': self.formation_manager.get_all_data(),
                'export_date': datetime.now().isoformat(),
                'well_name': self.current_well['name'] if self.current_well else 'Unknown'
            }
            
            # ذخیره در فایل JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export All Downhole Data",
                f"downhole_export_{timestamp}.json",
                "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, indent=2, ensure_ascii=False)
                
                self.status_manager.show_success(
                    "DownholeWidget",
                    f"All data exported: {filename}"
                )
        
        except Exception as e:
            logger.error(f"Error exporting all data: {e}")
            self.status_manager.show_error(
                "DownholeWidget",
                f"Failed to export all data: {str(e)}"
            )
    
    def set_current_well(self, well_data):
        """تنظیم چاه جاری"""
        self.current_well = well_data
        if well_data:
            self.well_label.setText(f"Well: {well_data.get('name', 'Unknown')}")
        else:
            self.well_label.setText("Well: Not Selected")
    
    def set_current_report(self, report_id):
        """تنظیم گزارش جاری"""
        self.current_report = report_id
        if report_id:
            self.status_manager.show_message(
                "DownholeWidget",
                f"Linked to report #{report_id}",
                3000
            )
    
    def cleanup(self):
        """پاکسازی منابع"""
        if self.auto_save_timer.isActive():
            self.auto_save_timer.stop()
            self.auto_save_timer.deleteLater()
            
        self.bit_manager = None
        self.bha_manager = None
        
        logger.info("DownholeWidget cleanup complete")


# ==================== Utility Functions ====================
    def create_downhole_widget(parent=None, db_manager=None):
        """تابع کمکی برای ایجاد ویجت Downhole"""
        widget = DownholeWidget(db_manager)
        
        if parent:
            widget.setParent(parent)
        
        return widget