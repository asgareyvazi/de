"""
Daily Report Tab - گزارش روزانه با استفاده از توابع مرکزی
"""

import logging
from datetime import datetime, date, time, timedelta

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from core.managers import (
    StatusBarManager,
    AutoSaveManager,
    TableButtonManager,
    ExportManager,
)
from core.database import DatabaseManager, Well, DailyReport, TimeLog24H, TimeLogMorning

logger = logging.getLogger(__name__)


class TimeEdit24(QTimeEdit):
    """QTimeEdit با پشتیبانی کامل از 24:00"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTimeRange(QTime(0, 0), QTime(23, 59))
        self.setButtonSymbols(QTimeEdit.UpDownArrows)
        
        # property برای تشخیص 24:00
        self._is_2400 = False
        
        # اتصال سیگنال برای تشخیص تغییرات
        self.timeChanged.connect(self._on_time_changed)
    
    def _on_time_changed(self):
        """وقتی زمان تغییر کرد"""
        current_time = self.time()
        
        # اگر 23:59 است و _is_2400 فعال است، نمایش را به 24:00 تغییر بده
        if self._is_2400 and (current_time.hour() != 23 or current_time.minute() != 59):
            self._is_2400 = False
    
    def setTime2400(self, enabled=True):
        """تنظیم زمان به 24:00"""
        self._is_2400 = enabled
        if enabled:
            super().setTime(QTime(23, 59))
        elif self.time().hour() == 23 and self.time().minute() == 59:
            # اگر 23:59 بود و می‌خواهیم 24:00 نباشد، به 23:58 تغییر می‌دهیم
            super().setTime(QTime(23, 58))
    
    def is2400(self):
        """آیا زمان 24:00 است؟"""
        return self._is_2400
    
    def getDisplayTime(self):
        """زمان نمایشی را برمی‌گرداند"""
        if self._is_2400:
            return "24:00"
        else:
            return self.time().toString("HH:mm")
    
    def getPythonTime(self):
        """زمان به فرمت پایتون"""
        if self._is_2400:
            return time(0, 0)  # 24:00 به صورت 00:00 ذخیره می‌شود
        else:
            t = self.time()
            return time(t.hour(), t.minute())
    
    def keyPressEvent(self, event):
        """مدیریت کلیدهای بالا/پایین"""
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            current_time = self.time()
            
            # اگر 24:00 فعال است
            if self._is_2400:
                if event.key() == Qt.Key_Down:
                    # پایین بردن از 24:00 به 23:59
                    self._is_2400 = False
                    super().setTime(QTime(23, 59))
                elif event.key() == Qt.Key_Up:
                    # 24:00 بالاتر نمی‌رود
                    pass
            # اگر 23:59 است و بالا می‌رود
            elif current_time.hour() == 23 and current_time.minute() == 59 and event.key() == Qt.Key_Up:
                self._is_2400 = True
                super().setTime(QTime(23, 59))
            else:
                # حالت عادی
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def getDatabaseTime(self):
        """زمان برای ذخیره در دیتابیس"""
        if self._is_2400:
            return time(0, 0), True  # به صورت 00:00 با flag 24:00
        else:
            t = self.time()
            return time(t.hour(), t.minute()), False
    
    def setDatabaseTime(self, db_time, is_2400=False):
        """تنظیم زمان از دیتابیس"""
        self._is_2400 = is_2400
        if is_2400:
            super().setTime(QTime(23, 59))  # نمایش 23:59 اما flag 24:00
        else:
            super().setTime(QTime(db_time.hour, db_time.minute))
            
class DailyReportWidget(QWidget):
    """تب گزارش روزانه با استفاده از توابع مرکزی"""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent
        
        # متغیرهای حالت
        self.current_well = None
        self.current_section = None
        self.current_report = None 
        self.current_report_id = None
        self.current_section_id = None
        self.current_daily_report_id = None
        self.current_tab_data = {}
        
        # مدیرها
        self.status_manager = StatusBarManager()
        self.status_manager.register_widget("DailyReport", self)
        
        self.export_manager = ExportManager(self)
        
        # دیکشنری کدهای فعالیت
        self.main_codes_dict = {
            "Rig Up/ Tear Down / Move ": [
                "Rig Moving/Positioning",
                "Rig Up",
                "Rig Down",
                "Tear Out",
                "Rig Skid",
            ],
            "Drilling ": [
                "Vertical Drilling",
                "Directional Drilling (Rotating)",
                "Directional Drilling (Sliding)",
            ],
            "Reaming": [
                "Reaming / Back Reaming",
                "Wash Down",
                "Under reaming/ Hole Opening/ Hole Enlargement",
                "Drill Out Cement/ Shoe track",
            ],
            "Coring": [
                "Trip in for Coring",
                "Trip out for Coring",
                "Coring Operation",
                "Core Recovery",
            ],
            "Circulate & Condition": [
                "Hole displacement",
                "Circulate/ Condition Mud",
                "Coiled Tubing Ops.",
                "Loss control",
            ],
            "Trips": [
                "R/U & R/D Pipe Handling Equip.",
                "PU/LD BHA",
                "Pick up Drill Pipe",
                "Lay Down Drill Pipe",
                "Run in Hole",
                "Pull Out Of Hole",
                "POOH with Pumping",
                "Wiper/ Condition Trip",
                "Wear Bushing",
            ],
            "Service/ Maintain Rig": ["Rig Lubricate"],
            "Repair Rig": [
                "Circulating System",
                "Power System",
                "Hoisting System",
                "Rotating System",
                "Well Control System",
                "Other",
            ],
            "Replacing Drill Line": ["Slip & Cut of Drill Line"],
            "Deviation Survey": ["Performing Survey Operation"],
            "Logging": [
                "R/U & R/D Logging Equip.",
                "Wire line logging",
                "TLC Logging",
                "CT Logging",
            ],
            "Run Casing/ Liner": [
                "R/U & R/D Handling Equip.",
                "CSG Running",
                "Pulling Casing",
                "CSG/Liner Integrity Test",
                "Liner Running",
                "Liner Tie back Operation",
                "Pull out Liner hanger setting tools and L/D",
                "Other Related Casing/Liner Activities",
                "Nipple up/down Wellhead",
            ],
            "Cementing": [
                "Casing/ Liner Cementing",
                "Plug Back",
                "Squeeze CMT",
                "Balance Plug",
                "Other",
            ],
            "Wait on Cement": ["for Casing/ Liner", "for Cement plug", "Other"],
            "Rig Up/Down BOP": ["Nipple up/down BOP", "Test BOP", "Pressure Test BOPs"],
            "Drill Stem Test": ["Conventional DST", "Full Bore DST", "Dry test"],
            "Fishing": [
                "Fishing Job",
                "Milling",
                "Coiled Tubing Ops.",
                "Work on Stuck",
            ],
            "Specialized Directional Work": [
                "RIH/ POOH Side-Track equip.",
                "Side-Tracking in Open Hole",
                "Side-Tracking in Cased Hole",
                "Other",
            ],
            "Operation Status (Waiting)": [
                "Waiting on Client",
                "Waiting on Operator Company",
                "Waiting on Rig Contractor",
                "Waiting on Service companies",
                "Waiting on Weather",
                "Waiting on Logistics/ Fuel",
            ],
            "Safety": ["Pre Job Safety Meeting (PJSM)", "Drills", "Other"],
            "Perforating": ["Wire line Perforation", "TCP Perforatin", "CT Perforatin"],
            "Completion/XMT": [
                "Completion Trips",
                "Completion Test",
                "Fluid displacement",
                "Slick line jobs",
                "Coiled Tubing Ops.",
                "Nipple up/down XMT",
                "XMT Test",
            ],
            "Treating": ["Acidizing", "N2 Lifting", "Coiled Tubing Ops."],
            "Swabbing": ["Swabbing"],
            "Surface Testing": ["Surface Testing", "Clean Up"],
            "Well Control": [
                "Kill the well",
                "Take S.C.R",
                "FIT/ LOT",
                "Flow Check",
                "Strip In / Out",
                "Coiled Tubing Ops.",
            ],
            "Other": ["Other"],
            "Subsea Operation": ["Run/ Retrieve Riser Equip.", "Subsea Installation"],
        }
        
        self.init_ui()
        self.setup_connections()
        self.setup_managers()
        self.load_companies()
        logger.info("DailyReportWidget initialized")
        
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========== Header Section ==========
        header_group = QGroupBox("📋 Report Header")
        header_layout = QGridLayout()
        header_layout.setSpacing(10)

        # Row 0 - Company and Project
        header_layout.addWidget(QLabel("🏢 Company:"), 0, 0)
        self.company_combo = QComboBox()
        self.company_combo.setMinimumWidth(150)
        self.company_combo.currentIndexChanged.connect(self.on_company_changed)
        header_layout.addWidget(self.company_combo, 0, 1)

        header_layout.addWidget(QLabel("📁 Project:"), 0, 2)
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(150)
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        header_layout.addWidget(self.project_combo, 0, 3)

        # Row 1 - Well and Section
        header_layout.addWidget(QLabel("🛢️ Well:"), 1, 0)
        self.well_combo = QComboBox()
        self.well_combo.setMinimumWidth(200)
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        header_layout.addWidget(self.well_combo, 1, 1)

        header_layout.addWidget(QLabel("📊 Section:"), 1, 2)
        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(150)
        self.section_combo.currentIndexChanged.connect(self.on_section_changed)
        header_layout.addWidget(self.section_combo, 1, 3)

        # Row 2 - Report Date and Report Number
        header_layout.addWidget(QLabel("📅 Report Date:"), 2, 0)
        self.report_date = QDateEdit()
        self.report_date.setDate(QDate.currentDate())
        self.report_date.setCalendarPopup(True)
        self.report_date.setDisplayFormat("yyyy-MM-dd")
        header_layout.addWidget(self.report_date, 2, 1)

        header_layout.addWidget(QLabel("🔢 Report No.:"), 2, 2)
        self.report_number = QSpinBox()
        self.report_number.setRange(1, 9999)
        self.report_number.setValue(1)
        header_layout.addWidget(self.report_number, 2, 3)

        # Row 3 - Rig Day and Status
        header_layout.addWidget(QLabel("🔢 Rig Day:"), 3, 0)
        self.rig_day = QSpinBox()
        self.rig_day.setRange(1, 365)
        self.rig_day.setValue(1)
        header_layout.addWidget(self.rig_day, 3, 1)

        header_layout.addWidget(QLabel("📊 Status:"), 3, 2)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Draft", "Submitted", "Approved"])
        header_layout.addWidget(self.status_combo, 3, 3)

        # Row 4 - Depth measurements
        header_layout.addWidget(QLabel("📏 Depth @ 00:00 (m):"), 4, 0)
        self.depth_0000 = QDoubleSpinBox()
        self.depth_0000.setRange(0, 20000)
        self.depth_0000.setDecimals(2)
        self.depth_0000.setSuffix(" m")
        header_layout.addWidget(self.depth_0000, 4, 1)

        header_layout.addWidget(QLabel("📏 Depth @ 06:00 (m):"), 4, 2)
        self.depth_0600 = QDoubleSpinBox()
        self.depth_0600.setRange(0, 20000)
        self.depth_0600.setDecimals(2)
        self.depth_0600.setSuffix(" m")
        header_layout.addWidget(self.depth_0600, 4, 3)

        # Row 5 - Depth at 24:00 and Calculate button
        header_layout.addWidget(QLabel("📏 Depth @ 24:00 (m):"), 5, 0)
        self.depth_2400 = QDoubleSpinBox()
        self.depth_2400.setRange(0, 20000)
        self.depth_2400.setDecimals(2)
        self.depth_2400.setSuffix(" m")
        header_layout.addWidget(self.depth_2400, 5, 1)

        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)
        
        # ========== Time Log Tabs ==========
        self.time_log_tabs = QTabWidget()

        # 24 Hours Tab
        self.time_24_tab = QWidget()
        self.time_24_layout = QVBoxLayout(self.time_24_tab)
        self.time_24_layout.setContentsMargins(5, 5, 5, 5)
        self.time_24_layout.setSpacing(10)

        # عنوان
        title_24_label = QLabel("<h3>🕒 Rig Activity in Last 24 Hours</h3>")
        title_24_label.setFixedHeight(40)
        title_24_label.setAlignment(Qt.AlignCenter)
        self.time_24_layout.addWidget(title_24_label)

        #جدول - بزرگ و قابل گسترش
        self.time_24_table = QTableWidget(0, 9)
        self.setup_time_log_table(self.time_24_table)
        self.time_24_table.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.time_24_table.setMinimumHeight(400)
        self.time_24_table.horizontalHeader().setStretchLastSection(True)
        self.time_24_table.verticalHeader().setDefaultSectionSize(30)
        self.time_24_layout.addWidget(self.time_24_table, 1)

        # دکمه‌های 24 ساعت
        btn_24_layout = QHBoxLayout()
        add_24_btn = QPushButton("➕ Add Row")
        remove_24_btn = QPushButton("➖ Remove Row")
        export_24_btn = QPushButton("📤 Export")

        add_24_btn.clicked.connect(lambda: self.add_time_log_row(self.time_24_table))
        remove_24_btn.clicked.connect(lambda: self.remove_time_log_row(self.time_24_table))
        export_24_btn.clicked.connect(lambda: self.export_manager.export_table_with_dialog(
            self.time_24_table, "24h_time_log"
        ))

        btn_24_layout.addWidget(add_24_btn)
        btn_24_layout.addWidget(remove_24_btn)
        btn_24_layout.addWidget(export_24_btn)
        btn_24_layout.addStretch()

        self.time_24_layout.addLayout(btn_24_layout)


        # Morning Tour Tab
        self.morning_tab = QWidget()
        self.morning_layout = QVBoxLayout(self.morning_tab)
        self.morning_layout.setContentsMargins(5, 5, 5, 5)
        self.morning_layout.setSpacing(10)

        # عنوان
        morning_title = QLabel("<h3>☀️ Rig Activity in Morning Tour</h3>")
        morning_title.setAlignment(Qt.AlignCenter)
        morning_title.setFixedHeight(40)
        self.morning_layout.addWidget(morning_title)

        # جدول
        self.morning_table = QTableWidget(0, 9)
        self.setup_time_log_table(self.morning_table)
        self.morning_table.setMinimumHeight(400)
        self.morning_layout.addWidget(self.morning_table)

        # دکمه‌های Morning Tour
        btn_morning_layout = QHBoxLayout()
        add_morning_btn = QPushButton("➕ Add Row")
        remove_morning_btn = QPushButton("➖ Remove Row")
        export_morning_btn = QPushButton("📤 Export")

        add_morning_btn.clicked.connect(lambda: self.add_time_log_row(self.morning_table))
        remove_morning_btn.clicked.connect(lambda: self.remove_time_log_row(self.morning_table))
        export_morning_btn.clicked.connect(lambda: self.export_manager.export_table_with_dialog(
            self.morning_table, "morning_time_log"
        ))

        btn_morning_layout.addWidget(add_morning_btn)
        btn_morning_layout.addWidget(remove_morning_btn)
        btn_morning_layout.addWidget(export_morning_btn)
        btn_morning_layout.addStretch()

        self.morning_layout.addLayout(btn_morning_layout)

        # Add tabs
        self.time_log_tabs.addTab(self.time_24_tab, "🕒 24 Hours")
        self.time_log_tabs.addTab(self.morning_tab, "☀️ Morning Tour")

        main_layout.addWidget(self.time_log_tabs)
        
        # ========== Summary Section ==========
        summary_group = QGroupBox("📝 Daily Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setPlaceholderText(
            "Enter daily activities summary, observations, notes..."
        )
        summary_layout.addWidget(self.summary_text)
        
        # Character counter
        self.char_counter = QLabel("0/2000 characters")
        self.char_counter.setAlignment(Qt.AlignRight)
        self.char_counter.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        summary_layout.addWidget(self.char_counter)
        
        # Connect text changed signal
        self.summary_text.textChanged.connect(self.update_char_counter)
        
        summary_group.setLayout(summary_layout)
        main_layout.addWidget(summary_group)

        # ========== Action Buttons ==========
        button_layout = QHBoxLayout()
        
        # دکمه جدید: ایجاد گزارش روزانه
        self.create_report_btn = QPushButton("📅 Create Daily Report")
        self.create_report_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        self.create_report_btn.clicked.connect(self.create_daily_report_for_current_section)
        self.create_report_btn.setEnabled(False)
        button_layout.addWidget(self.create_report_btn)
        
        self.save_btn = QPushButton("💾 Save Report")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.save_btn.clicked.connect(self.save_report)
        
        self.load_btn = QPushButton("📂 Load Report")
        self.load_btn.clicked.connect(self.load_report_dialog)
        
        self.new_btn = QPushButton("🆕 New Report")
        self.new_btn.clicked.connect(self.new_report)
        
        self.copy_prev_btn = QPushButton("📋 Copy Previous Day")
        self.copy_prev_btn.clicked.connect(self.copy_previous_day)
        
        self.print_btn = QPushButton("🖨️ Print")
        self.print_btn.clicked.connect(self.print_report)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.copy_prev_btn)
        button_layout.addWidget(self.print_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)

        # ========== Statistics ==========
        stats_layout = QHBoxLayout()
        
        self.total_time_label = QLabel("Total Time: 0.0h")
        self.total_npt_label = QLabel("NPT Time: 0.0h")
        self.productivity_label = QLabel("Productivity: 100%")
        
        for label in [self.total_time_label, self.total_npt_label, self.productivity_label]:
            label.setStyleSheet("""
                QLabel {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-weight: bold;
                }
            """)
            stats_layout.addWidget(label)
        
        stats_layout.addStretch()
        main_layout.addLayout(stats_layout)

        self.setLayout(main_layout)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        # ایجاد scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(central_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # برای بهتر شدن عملکرد روی سیستم‌های مختلف
        scroll_area.setFrameShape(QFrame.NoFrame)

        # ایجاد layout اصلی برای self
        main_container_layout = QVBoxLayout()
        main_container_layout.addWidget(scroll_area)
        self.setLayout(main_container_layout)
        
    # ========== Methods 24:00 ==========
    
    def create_time_edit(self, default_time=None, is_2400=False):
        """ایجاد TimeEdit با پشتیبانی 24:00"""
        time_edit = TimeEdit24()
        
        if default_time:
            if isinstance(default_time, QTime):
                time_edit.setTime(default_time)
            elif isinstance(default_time, time):
                time_edit.setTime(QTime(default_time.hour, default_time.minute))
        
        # تنظیم 24:00 اگر لازم باشد
        if is_2400:
            time_edit.setTime2400(True)
        
        return time_edit
    
    def get_time_edit_display_text(self, time_edit):
        """متن نمایشی TimeEdit را برمی‌گرداند"""
        if isinstance(time_edit, TimeEdit24):
            return time_edit.getDisplayTime()
        else:
            return time_edit.time().toString("HH:mm")
    
    def on_time_edit_changed(self, time_edit, table, row):
        """وقتی زمان تغییر کرد"""
        # اگر TimeEdit24 است و 24:00 است
        if isinstance(time_edit, TimeEdit24) and time_edit.is2400():
            # متن سلول را به 24:00 تغییر می‌دهیم
            time_item = QTableWidgetItem("24:00")
            time_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0 if time_edit == table.cellWidget(row, 0) else 1, time_item)
        else:
            # متن عادی
            time_item = QTableWidgetItem(time_edit.time().toString("HH:mm"))
            time_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0 if time_edit == table.cellWidget(row, 0) else 1, time_item)
        
        # محاسبه مدت زمان
        self.calculate_row_duration(table, row)
    
    def calculate_row_duration(self, table, row):
        """محاسبه مدت زمان برای یک سطر با پشتیبانی 24:00"""
        from_widget = table.cellWidget(row, 0)
        to_widget = table.cellWidget(row, 1)
        duration_widget = table.cellWidget(row, 2)
        
        if not (from_widget and to_widget and duration_widget):
            return
        
        try:
            # محاسبه زمان شروع
            if isinstance(from_widget, TimeEdit24) and from_widget.is2400():
                from_minutes = 24 * 60  # 24:00 = 1440 دقیقه
            else:
                from_time = from_widget.time()
                from_minutes = from_time.hour() * 60 + from_time.minute()
            
            # محاسبه زمان پایان
            if isinstance(to_widget, TimeEdit24) and to_widget.is2400():
                to_minutes = 24 * 60  # 24:00 = 1440 دقیقه
            else:
                to_time = to_widget.time()
                to_minutes = to_time.hour() * 60 + to_time.minute()
            
            # محاسبه مدت زمان
            if to_minutes < from_minutes:
                # عبور از نیمه شب
                duration_minutes = (24 * 60 - from_minutes) + to_minutes
            else:
                duration_minutes = to_minutes - from_minutes
            
            hours = duration_minutes / 60.0
            
            # نمایش در label
            duration_widget.setText(f"{hours:.2f}")
            
            # چک کردن محدودیت‌های زمانی
            is_morning = (table is self.morning_table)
            max_hours = 6.0 if is_morning else 24.0
            
            # چک برای هشدار
            if hours > max_hours:
                tab_name = "Morning Tour" if is_morning else "24 Hours"
                
                # هایلایت ردیف
                for col in range(table.columnCount()):
                    widget = table.cellWidget(row, col)
                    if widget:
                        npt_widget = table.cellWidget(row, 7)
                        is_npt = npt_widget.isChecked() if npt_widget else False
                        if not is_npt:
                            widget.setStyleSheet("background-color: #ffcccc;")
                
                if not hasattr(self, f'_limit_warning_{id(table)}_{row}'):
                    setattr(self, f'_limit_warning_{id(table)}_{row}', True)
                    QTimer.singleShot(100, lambda: self.status_manager.show_warning(
                        "DailyReport", 
                        f"⚠️ Row {row + 1} in {tab_name} exceeds {max_hours}h limit! ({hours:.2f}h)"
                    ))
            else:
                # حذف هایلایت
                npt_widget = table.cellWidget(row, 7)
                is_npt = npt_widget.isChecked() if npt_widget else False
                
                for col in range(table.columnCount()):
                    widget = table.cellWidget(row, col)
                    if widget and not is_npt:
                        widget.setStyleSheet("")
                
                if hasattr(self, f'_limit_warning_{id(table)}_{row}'):
                    delattr(self, f'_limit_warning_{id(table)}_{row}')
            
            # Update statistics
            QTimer.singleShot(100, self.update_statistics)
            
        except Exception as e:
            logger.error(f"Error calculating duration: {e}")
    
    def connect_time_signals(self, table, row):
        """اتصال سیگنال‌های تغییر زمان"""
        from_widget = table.cellWidget(row, 0)
        to_widget = table.cellWidget(row, 1)
        
        if from_widget:
            # حذف connection قبلی اگر وجود داشت
            try:
                from_widget.timeChanged.disconnect()
            except:
                pass
            
            from_widget.timeChanged.connect(lambda: self.on_time_edit_changed(from_widget, table, row))
        
        if to_widget:
            # حذف connection قبلی اگر وجود داشت
            try:
                to_widget.timeChanged.disconnect()
            except:
                pass
            
            to_widget.timeChanged.connect(lambda: self.on_time_edit_changed(to_widget, table, row))
    
    # ========== Rest of the methods (unchanged) ==========
    
    def on_section_changed(self):
        """هنگام تغییر سکشن"""
        section_id = self.section_combo.currentData()
        
        if section_id == -1:  # Create new section
            self.create_new_section()
        elif section_id:
            # وقتی سکشن تغییر کرد
            well_id = self.well_combo.currentData()
            if well_id:
                self.auto_calculate_report_info()
            
            # Load reports for this section
            self.load_reports_for_section(section_id)
            
            # فعال کردن دکمه ایجاد گزارش
            self.create_report_btn.setEnabled(True)
            self.create_report_btn.setToolTip(f"Create daily report for selected section")
        else:
            # غیرفعال کردن دکمه
            self.create_report_btn.setEnabled(False)
            self.create_report_btn.setToolTip("Select a section first")
    
    def set_current_daily_report(self, daily_report_id):
        """تنظیم دیلی ریپورت جاری و لود تمام تب‌های مرتبط"""
        self.current_daily_report_id = daily_report_id
        self.load_all_tabs_for_report(daily_report_id)
        
    def load_all_tabs_for_report(self, daily_report_id):
        """لود تمام تب‌های مرتبط با یک دیلی ریپورت"""
        # 1. لود Time Log 24h
        self.load_time_logs(daily_report_id, self.time_24_table, is_morning=False)
        
        # 2. لود Time Log Morning
        self.load_time_logs(daily_report_id, self.morning_table, is_morning=True)
        
    def save_all_tabs_for_report(self):
        """ذخیره تمام تب‌های مربوط به دیلی ریپورت جاری"""
        if not self.current_daily_report_id:
            return False
            
        # 1. ذخیره Time Log 24h
        time_logs_24h = self.collect_time_log_data(self.time_24_table)
        self.db_manager.save_time_logs_for_report(
            self.current_daily_report_id, 
            time_logs_24h, 
            is_morning=False
        )
        
        # 2. ذخیره Time Log Morning
        time_logs_morning = self.collect_time_log_data(self.morning_table)
        self.db_manager.save_time_logs_for_report(
            self.current_daily_report_id, 
            time_logs_morning, 
            is_morning=True
        )
        
        return True    
        
    def create_daily_report_for_current_section(self):
        """ایجاد گزارش روزانه جدید برای سکشن جاری"""
        section_id = self.section_combo.currentData()
        
        if not section_id or section_id == -1:
            self.status_manager.show_error("DailyReport", "Please select a section first")
            return
        
        try:
            # ایمپورت دیالوگ
            from dialogs.hierarchy_dialogs import NewDailyReportDialog
            
            # ایجاد دیالوگ
            dialog = NewDailyReportDialog(self.db_manager, self.parent_window, section_id)
            
            if dialog.exec():
                # گزارش ایجاد شد، فرم رو رفرش کن
                self.new_report()
                
                # شماره گزارش جدید رو ست کن
                well_id = self.well_combo.currentData()
                self.calculate_report_number()
                
                self.status_manager.show_success(
                    "DailyReport", 
                    "Daily report created successfully!"
                )
            
        except ImportError as e:
            logger.error(f"Error importing dialog: {e}")
            self.status_manager.show_error(
                "DailyReport", 
                "Cannot create dialog. Make sure hierarchy_dialogs.py is updated."
            )

    def setup_managers(self):
        """تنظیم managerها"""
        # AutoSave Manager
        self.auto_save_manager = AutoSaveManager()
        self.auto_save_manager.enable_for_widget(
            "DailyReportWidget", self, interval_minutes=10
        )
        
        logger.info("Managers setup complete for DailyReportWidget")

    def setup_connections(self):
        """تنظیم اتصالات سیگنال‌ها"""
        # Well selection change
        self.well_combo.currentIndexChanged.connect(self.on_well_changed)
        
        # Report date change
        self.report_date.dateChanged.connect(self.on_date_changed)
        
        # Tab change
        self.time_log_tabs.currentChanged.connect(self.on_tab_changed)

    def setup_time_log_table(self, table):
        """تنظیم ساختار جدول لاگ زمانی"""
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "🕐 From", "🕒 To", "⏱️ Duration", 
            "📊 Main Phase", "🏷️ Main Code", "🏷️ Sub Code",
            "📈 Status", "⚠️ NPT", "📝 Description"
        ])
        
        # Set column properties
        table.setColumnWidth(0, 100)   # From
        table.setColumnWidth(1, 100)   # To
        table.setColumnWidth(2, 80)    # Duration
        table.setColumnWidth(3, 120)   # Main Phase
        table.setColumnWidth(4, 150)   # Main Code
        table.setColumnWidth(5, 150)   # Sub Code
        table.setColumnWidth(6, 100)   # Status
        table.setColumnWidth(7, 60)    # NPT
        # Description column will stretch
        
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        
    def load_companies(self):
        """بارگذاری لیست شرکت‌ها"""
        try:
            self.company_combo.clear()
            self.company_combo.addItem("-- Select Company --", None)
            
            session = self.db_manager.create_session()
            try:
                from core.database import Company
                companies = session.query(Company).order_by(Company.name).all()
                for company in companies:
                    self.company_combo.addItem(f"{company.name}", company.id)
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error loading companies: {e}")

    def load_projects(self, company_id):
        """بارگذاری پروژه‌های یک شرکت"""
        try:
            self.project_combo.clear()
            self.project_combo.addItem("-- Select Project --", None)
            
            if not company_id:
                return
                
            session = self.db_manager.create_session()
            try:
                from core.database import Project
                projects = session.query(Project).filter(
                    Project.company_id == company_id
                ).order_by(Project.name).all()
                
                for project in projects:
                    self.project_combo.addItem(f"{project.name} ({project.code})", project.id)
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error loading projects: {e}")

    def load_wells(self, project_id):
        """بارگذاری چاه‌های یک پروژه"""
        try:
            self.well_combo.clear()
            self.well_combo.addItem("-- Select Well --", None)
            self.section_combo.clear()
            self.section_combo.addItem("-- Select Section --", None)
            
            if not project_id:
                return
                
            session = self.db_manager.create_session()
            try:
                from core.database import Well
                wells = session.query(Well).filter(
                    Well.project_id == project_id
                ).order_by(Well.name).all()
                
                for well in wells:
                    display_text = f"{well.name} ({well.code})"
                    self.well_combo.addItem(display_text, well.id)
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error loading wells: {e}")

    def load_sections(self, well_id):
        """بارگذاری سکشن‌های یک چاه"""
        try:
            self.section_combo.clear()
            self.section_combo.addItem("-- Select Section --", None)
            self.section_combo.addItem("➕ Create New Section", -1)  # گزینه ایجاد جدید
            
            if not well_id:
                return
                
            sections = self.db_manager.get_sections_by_well(well_id)
            for section in sections:
                display_text = f"{section['name']}"
                if section['code']:
                    display_text += f" ({section['code']})"
                self.section_combo.addItem(display_text, section['id'])
                
        except Exception as e:
            logger.error(f"Error loading sections: {e}")

    def on_company_changed(self):
        """هنگام تغییر شرکت"""
        company_id = self.company_combo.currentData()
        self.load_projects(company_id)
        
    def on_project_changed(self):
        """هنگام تغییر پروژه"""
        project_id = self.project_combo.currentData()
        self.load_wells(project_id)
        
    def on_well_changed(self):
        """هنگام تغییر چاه"""
        well_id = self.well_combo.currentData()
        self.load_sections(well_id)
        
        if well_id:
            # محاسبه خودکار اطلاعات گزارش
            self.auto_calculate_report_info()
            
            self.status_manager.show_message(
                "DailyReport", 
                f"Selected well: {self.well_combo.currentText()}",
                2000
            )

    def create_new_section(self):
        """ایجاد سکشن جدید"""
        well_id = self.well_combo.currentData()
        if not well_id:
            self.status_manager.show_error("DailyReport", "Please select a well first")
            self.section_combo.setCurrentIndex(0)
            return
            
        try:
            from dialogs.hierarchy_dialogs import NewSectionDialog
            dialog = NewSectionDialog(self.db_manager, self, well_id)
            
            if dialog.exec():
                # Refresh sections after creation
                self.load_sections(well_id)
                
                # Select the newly created section
                session = self.db_manager.create_session()
                try:
                    from core.database import Section
                    new_section = session.query(Section).filter(
                        Section.well_id == well_id
                    ).order_by(Section.created_at.desc()).first()
                    
                    if new_section:
                        for i in range(self.section_combo.count()):
                            if self.section_combo.itemData(i) == new_section.id:
                                self.section_combo.setCurrentIndex(i)
                                break
                finally:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error creating section: {e}")
            self.section_combo.setCurrentIndex(0)
    
    def calculate_report_number(self):
        """محاسبه خودکار شماره گزارش"""
        well_id = self.well_combo.currentData()
        section_id = self.section_combo.currentData()
        
        if not well_id or not section_id or section_id == -1:
            return
            
        try:
            session = self.db_manager.create_session()
            try:
                from core.database import DailyReport
                # تعداد گزارش‌های موجود برای این سکشن
                count = session.query(DailyReport).filter(
                    DailyReport.well_id == well_id,
                    DailyReport.section_id == section_id
                ).count()
                
                # شماره گزارش جدید = تعداد + 1
                self.report_number.setValue(count + 1)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating report number: {e}")
    
    # ========== Core Methods ==========
    def calculate_next_start_time(self, table, position=None):
        """محاسبه زمان شروع خودکار برای ردیف جدید"""
        row_count = table.rowCount()
        
        if row_count == 0:
            # اگر جدول خالی است، از 00:00 شروع کن
            return QTime(0, 0)
        
        # اگر position مشخص شده (برای درج بین سطرها)
        if position is not None and 0 <= position < row_count:
            if position == 0:
                # اگر در ابتدا می‌خواهیم درج کنیم
                return QTime(0, 0)
            else:
                # زمان پایان سطر قبلی را بگیر
                prev_end_widget = table.cellWidget(position - 1, 1)
                if prev_end_widget:
                    if isinstance(prev_end_widget, TimeEdit24) and prev_end_widget.is2400():
                        # اگر 24:00 است، به 00:00 برگرد
                        return QTime(0, 0)
                    else:
                        prev_end_time = prev_end_widget.time()
                        return prev_end_time
                else:
                    return QTime(0, 0)
        else:
            # اگر در انتها اضافه می‌کنیم
            last_row = row_count - 1
            last_end_widget = table.cellWidget(last_row, 1)
            
            if last_end_widget:
                if isinstance(last_end_widget, TimeEdit24) and last_end_widget.is2400():
                    # اگر 24:00 است، به 00:00 برگرد
                    return QTime(0, 0)
                else:
                    last_end_time = last_end_widget.time()
                    return last_end_time
            else:
                return QTime(0, 0)
                
    def calculate_suggested_end_time(self, start_time):
        """محاسبه زمان پایان پیشنهادی (پیشفرض 8 ساعت)"""
        # اضافه کردن 8 ساعت
        end_time = start_time.addSecs(8 * 3600)
        
        # اگر از 23:59 گذشت، روی 23:59 محدود کن
        if end_time.hour() >= 24:
            end_time = QTime(23, 59)
        
        return end_time
    
    def add_time_log_row(self, table, log_data=None):
        """اضافه کردن سطر جدید به جدول"""
        current_row = table.currentRow()
        
        if current_row >= 0 and not log_data:
            insert_position = current_row + 1
        else:
            insert_position = table.rowCount()
        
        table.insertRow(insert_position)
        
        # 🕐 From Time
        from_time = None
        if log_data:
            # تنظیم زمان از دیتابیس
            from_time = self.create_time_edit()
            if log_data.get('is_from_2400'):
                from_time.setTime2400(True)
            else:
                t = log_data.get('time_from')
                if t:
                    from_time.setTime(QTime(t.hour, t.minute))
        else:
            # محاسبه زمان شروع خودکار
            start_time = self.calculate_next_start_time(table, insert_position)
            from_time = self.create_time_edit(default_time=start_time)
        
        table.setCellWidget(insert_position, 0, from_time)
        
        # 🕒 To Time
        to_time = None
        if log_data:
            # تنظیم زمان از دیتابیس
            to_time = self.create_time_edit()
            if log_data.get('is_to_2400'):
                to_time.setTime2400(True)
            else:
                t = log_data.get('time_to')
                if t:
                    to_time.setTime(QTime(t.hour, t.minute))
        else:
            # محاسبه زمان پایان خودکار
            if log_data and log_data.get('time_from'):
                start_qtime = QTime(log_data['time_from'].hour, log_data['time_from'].minute)
            else:
                start_qtime = from_time.time()
            
            end_time = self.calculate_suggested_end_time(start_qtime)
            to_time = self.create_time_edit(default_time=end_time)
        
        table.setCellWidget(insert_position, 1, to_time)
        
        
        # ⏱️ Duration
        duration_label = QLabel("0.00")
        duration_label.setAlignment(Qt.AlignCenter)
        table.setCellWidget(insert_position, 2, duration_label)
        
        # 📊 Main Phase
        main_phase_combo = QComboBox()
        phases = [
            "MOV - Moving", "DRL - Drilling", "LOG - Logging", 
            "CSG - Casing/Liner", "COM - Completion", "FTS - Formation Testing",
            "PIH - Pilot Hole", "COR - Coring", "REE - Re-Entry", "ABD - Abandonment"
        ]
        main_phase_combo.addItems(phases)
        if log_data and hasattr(log_data, 'main_phase'):
            index = main_phase_combo.findText(log_data.main_phase, Qt.MatchContains)
            if index >= 0:
                main_phase_combo.setCurrentIndex(index)
        table.setCellWidget(insert_position, 3, main_phase_combo)
        
        # 🏷️ Main Code
        main_code_combo = QComboBox()
        main_code_combo.addItems(list(self.main_codes_dict.keys()))
        if log_data and hasattr(log_data, 'main_code'):
            index = main_code_combo.findText(log_data.main_code)
            if index >= 0:
                main_code_combo.setCurrentIndex(index)
        
        main_code_combo.currentTextChanged.connect(
            lambda text, r=insert_position, t=table: self.update_sub_codes(t, r, text)
        )
        table.setCellWidget(insert_position, 4, main_code_combo)
        
        # 🏷️ Sub Code
        sub_code_combo = QComboBox()
        current_main = main_code_combo.currentText()
        sub_codes = self.main_codes_dict.get(current_main, [])
        sub_code_combo.addItems(sub_codes)
        if log_data and hasattr(log_data, 'sub_code'):
            index = sub_code_combo.findText(log_data.sub_code)
            if index >= 0:
                sub_code_combo.setCurrentIndex(index)
        table.setCellWidget(insert_position, 5, sub_code_combo)
        
        # 📈 Status
        status_combo = QComboBox()
        status_combo.addItems(["Normal", "Delayed", "Completed", "In Progress", "On Hold"])
        if log_data and hasattr(log_data, 'status'):
            index = status_combo.findText(log_data.status)
            if index >= 0:
                status_combo.setCurrentIndex(index)
        table.setCellWidget(insert_position, 6, status_combo)
        
        # ⚠️ NPT Checkbox
        npt_checkbox = QCheckBox()
        if log_data and hasattr(log_data, 'is_npt'):
            npt_checkbox.setChecked(bool(log_data.is_npt))
        
        npt_checkbox.stateChanged.connect(
            lambda state, r=insert_position, t=table: self.highlight_npt_row(t, r, state)
        )
        table.setCellWidget(insert_position, 7, npt_checkbox)
        
        # 📝 Description
        desc_edit = QLineEdit()
        if log_data and hasattr(log_data, 'activity_description'):
            desc_edit.setText(str(log_data.activity_description or ""))
        desc_edit.setPlaceholderText("Enter activity description...")
        table.setCellWidget(insert_position, 8, desc_edit)
        
        # Connect time signals
        self.connect_time_signals(table, insert_position)
        
        # Create table items for display
        if isinstance(from_time, TimeEdit24) and from_time.is2400():
            from_item = QTableWidgetItem("24:00")
        else:
            from_item = QTableWidgetItem(from_time.time().toString("HH:mm"))
        from_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(insert_position, 0, from_item)
        
        if isinstance(to_time, TimeEdit24) and to_time.is2400():
            to_item = QTableWidgetItem("24:00")
        else:
            to_item = QTableWidgetItem(to_time.time().toString("HH:mm"))
        to_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(insert_position, 1, to_item)
        
        # Calculate initial duration
        self.calculate_row_duration(table, insert_position)
        
        # Highlight if NPT
        if log_data and hasattr(log_data, 'is_npt') and log_data.is_npt:
            self.highlight_npt_row(table, insert_position, 2)
        
        # فقط اگر از کاربر اضافه شده، به‌روزرسانی کن
        if not log_data:
            self.status_manager.show_message(
                "DailyReport", 
                f"Row added at position {insert_position + 1}", 
                2000
            )
        
        return insert_position
    
    def remove_time_log_row(self, table):
        """حذف سطر انتخاب شده و به‌روزرسانی خودکار زمان‌ها"""
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
            
            # به‌روزرسانی آمار
            self.update_statistics()
            self.status_manager.show_message("DailyReport", "Row removed", 2000)
        else:
            self.status_manager.show_error("DailyReport", "Please select a row to remove")

    def calculate_all_durations(self, table):
        """محاسبه مدت زمان برای همه سطرها"""
        for row in range(table.rowCount()):
            self.calculate_row_duration(table, row)
        
        self.update_statistics()
        self.status_manager.show_success("DailyReport", "Durations calculated")

    def update_sub_codes(self, table, row, main_code):
        """به‌روزرسانی کدهای فرعی هنگام تغییر کد اصلی"""
        sub_combo = table.cellWidget(row, 5)
        if sub_combo and main_code in self.main_codes_dict:
            current_text = sub_combo.currentText()
            sub_combo.clear()
            sub_codes = self.main_codes_dict[main_code]
            sub_combo.addItems(sub_codes)
            
            # Try to restore previous selection
            if current_text in sub_codes:
                index = sub_combo.findText(current_text)
                if index >= 0:
                    sub_combo.setCurrentIndex(index)

    def highlight_npt_row(self, table, row, state):
        """هایلایت سطرهای NPT"""
        is_npt = (state == 2)  # Qt.Checked
        
        for col in range(table.columnCount()):
            widget = table.cellWidget(row, col)
            if widget:
                if is_npt:
                    widget.setStyleSheet("background-color: #ffcccc;")
                else:
                    widget.setStyleSheet("")
        
        self.update_statistics()

    # ========== Database Operations ==========

    def save_report(self):
        """ذخیره گزارش در دیتابیس"""
        try:
            # اعتبارسنجی فرم
            errors = self.validate_form()
            if errors:
                error_msg = "\n".join(errors)
                self.status_manager.show_error("DailyReport", error_msg)
                QMessageBox.warning(self, "Validation Error", error_msg)
                return False
            
            well_id = self.well_combo.currentData()
            section_id = self.section_combo.currentData()
            
            if not well_id:
                self.status_manager.show_error("DailyReport", "Please select a well")
                return False
                
            if not section_id or section_id == -1:
                self.status_manager.show_error("DailyReport", "Please select a section")
                return False
                
            report_date = self.report_date.date().toPython()
            report_number = self.report_number.value()
            
            # چک برای گزارش تکراری
            if not self.current_daily_report_id:
                existing_report = self.db_manager.get_daily_report_by_date_section(
                    section_id, report_date
                )
                if existing_report:
                    reply = QMessageBox.question(
                        self, "Duplicate Report",
                        f"A report already exists for this section on {report_date}.\n"
                        "Do you want to overwrite it?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return False
            
            # Collect data from tables
            time_logs_24h = self.collect_time_log_data(self.time_24_table)
            time_logs_morning = self.collect_time_log_data(self.morning_table)
            
            # Prepare report data
            report_data = {
                "well_id": well_id,
                "section_id": section_id,
                "report_date": report_date,
                "report_number": report_number,
                "rig_day": self.rig_day.value(),
                "depth_0000": self.depth_0000.value(),
                "depth_0600": self.depth_0600.value(),
                "depth_2400": self.depth_2400.value(),
                "summary": self.summary_text.toPlainText(),
                "status": self.status_combo.currentText(),
                "created_by": self.parent_window.user['id'] if hasattr(self.parent_window, 'user') else None,
                "time_logs_24h": time_logs_24h,
                "time_logs_morning": time_logs_morning
            }
            
            # If editing existing report, add ID
            if self.current_report:
                report_data["id"] = self.current_report["id"]
            
            # Save to database
            result = self.db_manager.save_daily_report(report_data)
            
            if result:
                # ذخیره تمام تب‌های مرتبط
                self.save_all_tabs_for_report()
        
            if result:
                self.status_manager.show_success(
                    "DailyReport", 
                    f"Report #{report_number} saved successfully!"
                )
                return True
            else:
                self.status_manager.show_error("DailyReport", "Failed to save report")
                return False
                
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            self.status_manager.show_error("DailyReport", f"Error: {str(e)[:100]}")
            return False

    def collect_time_log_data(self, table):
        """جمع‌آوری داده‌های لاگ زمانی از جدول با پشتیبانی از 24:00"""
        time_logs = []
        
        for row in range(table.rowCount()):
            from_widget = table.cellWidget(row, 0)
            to_widget = table.cellWidget(row, 1)
            main_phase_widget = table.cellWidget(row, 3)
            main_code_widget = table.cellWidget(row, 4)
            sub_code_widget = table.cellWidget(row, 5)
            status_widget = table.cellWidget(row, 6)
            npt_widget = table.cellWidget(row, 7)
            desc_widget = table.cellWidget(row, 8)
            
            if all(widget is not None for widget in [
                from_widget, to_widget, main_phase_widget, main_code_widget,
                sub_code_widget, status_widget, npt_widget, desc_widget
            ]):
                # زمان شروع
                if isinstance(from_widget, TimeEdit24):
                    from_time, is_from_2400 = from_widget.getDatabaseTime()
                else:
                    t = from_widget.time()
                    from_time = time(t.hour(), t.minute())
                    is_from_2400 = False
                
                # زمان پایان
                if isinstance(to_widget, TimeEdit24):
                    to_time, is_to_2400 = to_widget.getDatabaseTime()
                else:
                    t = to_widget.time()
                    to_time = time(t.hour(), t.minute())
                    is_to_2400 = False
                
                # محاسبه مدت زمان
                duration = self.calculate_duration(
                    from_time, is_from_2400,
                    to_time, is_to_2400
                )
                
                time_log = {
                    "time_from": from_time,
                    "time_to": to_time,
                    "is_from_2400": is_from_2400,  # 🆕
                    "is_to_2400": is_to_2400,      # 🆕
                    "main_phase": main_phase_widget.currentText(),
                    "main_code": main_code_widget.currentText(),
                    "sub_code": sub_code_widget.currentText(),
                    "status": status_widget.currentText(),
                    "is_npt": npt_widget.isChecked(),
                    "activity_description": desc_widget.text(),
                    "duration": duration
                }
                time_logs.append(time_log)
        
        return time_logs
      
    def calculate_duration(self, from_time, is_from_2400, to_time, is_to_2400):
        """محاسبه مدت زمان با پشتیبانی 24:00"""
        # تبدیل به دقیقه
        if is_from_2400:
            from_minutes = 24 * 60
        else:
            from_minutes = from_time.hour * 60 + from_time.minute
        
        if is_to_2400:
            to_minutes = 24 * 60
        else:
            to_minutes = to_time.hour * 60 + to_time.minute
        
        # محاسبه مدت زمان
        if to_minutes < from_minutes:
            duration_minutes = (24 * 60 - from_minutes) + to_minutes
        else:
            duration_minutes = to_minutes - from_minutes
        
        return duration_minutes / 60.0  # تبدیل به ساعت
    
    def load_report_dialog(self):
        """دیالوگ بارگذاری گزارش"""
        well_id = self.well_combo.currentData()
        if not well_id:
            self.status_manager.show_error("DailyReport", "Please select a well first")
            return
        
        try:
            # Get reports for selected well
            reports = self.db_manager.get_daily_reports_by_well(well_id)
            
            if not reports:
                self.status_manager.show_message("DailyReport", "No reports found for this well")
                return
            
            # Create selection dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("📂 Load Report")
            dialog.setFixedSize(600, 400)
            
            layout = QVBoxLayout()
            
            # Table for reports
            table = QTableWidget(len(reports), 4)
            table.setHorizontalHeaderLabels(["Date", "Rig Day", "Status", "Summary"])
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            
            for i, report in enumerate(reports):
                # Date
                date_item = QTableWidgetItem(str(report["report_date"]))
                date_item.setData(Qt.UserRole, report["id"])
                table.setItem(i, 0, date_item)
                
                # Rig Day
                table.setItem(i, 1, QTableWidgetItem(str(report["rig_day"])))
                
                # Status
                table.setItem(i, 2, QTableWidgetItem(report["status"]))
                
                # Summary
                summary = report["summary"] or ""
                if len(summary) > 50:
                    summary = summary[:50] + "..."
                table.setItem(i, 3, QTableWidgetItem(summary))
            
            table.resizeColumnsToContents()
            table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(table)
            
            # Buttons
            button_layout = QHBoxLayout()
            load_btn = QPushButton("📥 Load Selected")
            cancel_btn = QPushButton("❌ Cancel")
            
            load_btn.clicked.connect(lambda: self.load_selected_report(dialog, table))
            cancel_btn.clicked.connect(dialog.reject)
            
            button_layout.addWidget(load_btn)
            button_layout.addWidget(cancel_btn)
            button_layout.addStretch()
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            if dialog.exec():
                self.status_manager.show_success("DailyReport", "Report loaded")
            
        except Exception as e:
            logger.error(f"Error loading reports dialog: {e}")
            self.status_manager.show_error("DailyReport", f"Error: {str(e)[:100]}")

    def load_selected_report(self, dialog, table):
        """بارگذاری گزارش انتخاب شده"""
        selected_items = table.selectedItems()
        if not selected_items:
            self.status_manager.show_error("DailyReport", "Please select a report")
            return
        
        report_id = selected_items[0].data(Qt.UserRole)
        self.load_report_by_id(report_id)
        dialog.accept()

    def load_report_by_id(self, report_id):
        """بارگذاری گزارش با ID - نسخه بهبودیافته"""
        try:
            if not report_id:
                self.status_manager.show_error("DailyReport", "Invalid report ID")
                return
                
            # Get report data
            report_data = self.db_manager.get_daily_report_by_id(report_id)
                    
            if not report_data:
                self.status_manager.show_error("DailyReport", "Report not found")
                return
                
            self.current_report = report_data
            
            # بارگذاری خودکار شماره گزارش
            self.calculate_report_number_from_spud_date()
            
            # Set basic fields
            if 'report_date' in report_data and report_data["report_date"]:
                self.report_date.setDate(report_data["report_date"])
            
            # سایر فیلدها
            for field, widget in [
                ('rig_day', self.rig_day),
                ('depth_0000', self.depth_0000),
                ('depth_0600', self.depth_0600),
                ('depth_2400', self.depth_2400)
            ]:
                if field in report_data and report_data[field] is not None:
                    widget.setValue(report_data[field])
            
            # خلاصه
            if 'summary' in report_data:
                self.summary_text.setPlainText(report_data["summary"] or "")
            
            # وضعیت
            if 'status' in report_data:
                index = self.status_combo.findText(report_data["status"])
                if index >= 0:
                    self.status_combo.setCurrentIndex(index)
            
            # بارگذاری چاه و سکشن مرتبط
            well_id = report_data.get("well_id")
            section_id = report_data.get("section_id")
            
            if well_id:
                # پیدا کردن چاه
                for i in range(self.well_combo.count()):
                    if self.well_combo.itemData(i) == well_id:
                        self.well_combo.setCurrentIndex(i)
                        break
                
                # اگر سکشن هم داشت، انتخابش کن
                if section_id:
                    # تاخیر برای اطمینان از لود شدن سکشن‌ها
                    QTimer.singleShot(100, lambda: self.select_section(section_id))
            
            # Load time logs
            self.load_time_logs(report_id, self.time_24_table, is_morning=False)
            self.load_time_logs(report_id, self.morning_table, is_morning=True)
            
            self.current_daily_report_id = report_id
            
            # نمایش اطلاعات
            report_num = report_data.get('report_number', 'N/A')
            self.status_manager.show_success(
                "DailyReport", 
                f"Report #{report_num} loaded successfully"
            )
            
        except Exception as e:
            logger.error(f"Error loading report {report_id}: {e}")
            self.status_manager.show_error("DailyReport", f"Error loading: {str(e)[:100]}")
            
    def select_section(self, section_id):
        """انتخاب یک سکشن در combobox"""
        for i in range(self.section_combo.count()):
            if self.section_combo.itemData(i) == section_id:
                self.section_combo.setCurrentIndex(i)
                break
    
    def load_time_logs(self, report_id, table, is_morning=False):
        """بارگذاری لاگ‌های زمانی"""
        try:
            table.setRowCount(0)
            
            if not report_id:
                logger.warning(f"No report ID provided for loading time logs")
                return
                
            # غیرفعال کردن به‌روزرسانی‌های UI برای عملکرد بهتر
            table.setUpdatesEnabled(False)
            
            if is_morning:
                logs = self.db_manager.get_time_logs_morning(report_id)
            else:
                logs = self.db_manager.get_time_logs_24h(report_id)
            
            for log in logs:
                self.add_time_log_row(table, log)
                
            table.setUpdatesEnabled(True)
            
        except Exception as e:
            logger.error(f"Error loading time logs: {e}")
            if table:
                table.setUpdatesEnabled(True)
                
    # ========== Helper Methods ==========
    def get_current_report_info(self):
        """دریافت اطلاعات دیلی ریپورت جاری"""
        if self.current_daily_report_id:
            return {
                'id': self.current_daily_report_id,
                'report_number': self.report_number.value(),
                'report_date': self.report_date.date().toString('yyyy-MM-dd'),
                'well': self.well_combo.currentText(),
                'section': self.section_combo.currentText()
            }
        return None
    
    def update_statistics(self):
        """به‌روزرسانی آمار با چک کردن محدودیت‌ها"""
        try:
            total_time = 0.0
            total_npt = 0.0
            
            # محاسبه برای هر دو تب
            for table, tab_name in [(self.time_24_table, "24 Hours"), (self.morning_table, "Morning Tour")]:
                tab_total = 0.0
                
                for row in range(table.rowCount()):
                    duration_widget = table.cellWidget(row, 2)
                    npt_widget = table.cellWidget(row, 7)
                    
                    if duration_widget:
                        try:
                            duration = float(duration_widget.text())
                            tab_total += duration
                            
                            if npt_widget and npt_widget.isChecked():
                                total_npt += duration
                        except:
                            pass
                
                # چک کردن محدودیت کلی تب
                if tab_name == "24 Hours" and tab_total > 24.0:
                    self.status_manager.show_warning(
                        "DailyReport", 
                        f"⚠️ Total time in 24 Hours tab exceeds 24 hours! ({tab_total:.1f}h)",
                        5000
                    )
                elif tab_name == "Morning Tour" and tab_total > 6.0:
                    self.status_manager.show_warning(
                        "DailyReport", 
                        f"⚠️ Total time in Morning Tour tab exceeds 6 hours! ({tab_total:.1f}h)",
                        5000
                    )
                
                total_time += tab_total
            
            # Update labels
            self.total_time_label.setText(f"Total Time: {total_time:.1f}h")
            self.total_npt_label.setText(f"NPT Time: {total_npt:.1f}h")
            
            # Calculate productivity
            if total_time > 0:
                productivity = ((total_time - total_npt) / total_time) * 100
                self.productivity_label.setText(f"Productivity: {productivity:.1f}%")
                
                # Color code based on productivity
                if productivity >= 90:
                    color = "#27ae60"  # Green
                elif productivity >= 70:
                    color = "#f39c12"  # Orange
                else:
                    color = "#e74c3c"  # Red
                
                self.productivity_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {color};
                        color: white;
                        border: 1px solid {color};
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-weight: bold;
                    }}
                """)
                
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
          
    def check_time_limits(self, table, row, duration_hours):
        """چک کردن محدودیت‌های زمانی و نمایش هشدار"""
        # تشخیص اینکه کدام تب فعال است
        is_morning = (table is self.morning_table)
        
        if is_morning:
            # محدودیت Morning Tour: 6 ساعت
            max_hours = 6.0
            tab_name = "Morning Tour"
        else:
            # محدودیت 24 Hours: 24 ساعت
            max_hours = 24.0
            tab_name = "24 Hours"
        
        # چک کردن محدودیت
        if duration_hours > max_hours:
            # هایلایت ردیف
            for col in range(table.columnCount()):
                widget = table.cellWidget(row, col)
                if widget:
                    widget.setStyleSheet("background-color: #ffcccc; border: 1px solid #ff0000;")
            
            # نمایش هشدار
            warning_msg = f"⚠️ Row {row + 1} in {tab_name} exceeds {max_hours} hours limit! ({duration_hours:.2f}h)"
            
            # فقط یک بار نمایش بده (برای جلوگیری از اسپم)
            if not hasattr(self, f'_warning_shown_{id(table)}_{row}'):
                setattr(self, f'_warning_shown_{id(table)}_{row}', True)
                
                QTimer.singleShot(100, lambda: self.show_time_warning(warning_msg))
        else:
            # حذف هایلایت
            for col in range(table.columnCount()):
                widget = table.cellWidget(row, col)
                if widget:
                    # اگر NPT نیست، هایلایت رو بردار
                    if col != 7 or not self.is_npt_row(table, row):
                        widget.setStyleSheet("")
            
            # ریست فلگ هشدار
            if hasattr(self, f'_warning_shown_{id(table)}_{row}'):
                delattr(self, f'_warning_shown_{id(table)}_{row}')

    def is_npt_row(self, table, row):
        """چک کردن آیا ردیف NPT است"""
        npt_widget = table.cellWidget(row, 7)
        if npt_widget and isinstance(npt_widget, QCheckBox):
            return npt_widget.isChecked()
        return False

    def show_time_warning(self, message):
        """نمایش هشدار زمان"""
        # فقط در status bar نمایش بده (نه popup که مزاحم باشد)
        self.status_manager.show_error("DailyReport", message)
        
        # همچنین در console هم log کن
        logger.warning(message)
        
    def update_char_counter(self):
        """به‌روزرسانی شمارنده کاراکترها"""
        text = self.summary_text.toPlainText()
        char_count = len(text)
        self.char_counter.setText(f"{char_count}/2000 characters")
        
        # Change color if approaching limit
        if char_count > 1900:
            self.char_counter.setStyleSheet("color: #e74c3c; font-size: 10px;")
        elif char_count > 1500:
            self.char_counter.setStyleSheet("color: #f39c12; font-size: 10px;")
        else:
            self.char_counter.setStyleSheet("color: #7f8c8d; font-size: 10px;")

    def copy_previous_day(self):
        """کپی داده‌ها از گزارش روز قبل"""
        well_id = self.well_combo.currentData()
        section_id = self.section_combo.currentData()
        
        if not well_id:
            self.status_manager.show_error("DailyReport", "Please select a well")
            return
            
        if not section_id or section_id == -1:
            self.status_manager.show_error("DailyReport", "Please select a section")
            return
        
        try:
            current_date = self.report_date.date().toPython()
            previous_date = current_date - timedelta(days=1)
            
            # ابتدا شماره گزارش را از اسپاد دیت محاسبه کن
            self.calculate_report_number_from_spud_date()
            
            # سپس داده‌ها را از روز قبل کپی کن
            session = self.db_manager.create_session()
            try:
                from core.database import DailyReport
                previous_report = session.query(DailyReport).filter(
                    DailyReport.well_id == well_id,
                    DailyReport.section_id == section_id,
                    DailyReport.report_date == previous_date
                ).first()
                
                if previous_report:
                    # فقط عمق‌ها و خلاصه را کپی کن (شماره گزارش از اسپاد محاسبه شده)
                    self.depth_0000.setValue(previous_report.depth_2400 or 0)
                    self.depth_0600.setValue(previous_report.depth_2400 or 0)
                    
                    # ریگ دی را محاسبه کن
                    self.rig_day.setValue((previous_report.rig_day or 0) + 1)
                    
                    # خلاصه را کپی کن
                    self.summary_text.setPlainText(previous_report.summary or "")
                    
                    self.status_manager.show_success(
                        "DailyReport", 
                        f"📋 Copied data from report #{previous_report.report_number} ({previous_date})"
                    )
                else:
                    self.status_manager.show_message(
                        "DailyReport", 
                        "No report found for previous day in this section",
                        3000
                    )
                    
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error copying previous day: {e}")
            self.status_manager.show_error("DailyReport", f"Error: {str(e)[:100]}")
            
    def new_report(self):
        """ایجاد گزارش جدید"""
        self.current_report = None
        
        # Reset form
        self.report_date.setDate(QDate.currentDate())
        self.rig_day.setValue(1)
        self.depth_0000.setValue(0)
        self.depth_0600.setValue(0)
        self.depth_2400.setValue(0)
        self.summary_text.clear()
        self.status_combo.setCurrentText("Draft")
        
        # Clear tables
        self.time_24_table.setRowCount(0)
        self.morning_table.setRowCount(0)
        
        # Add initial rows
        self.add_time_log_row(self.time_24_table)
        self.add_time_log_row(self.morning_table)
        
        self.status_manager.show_success("DailyReport", "📝 New report created")

    def print_report(self):
        """چاپ گزارش"""
        if not self.current_report:
            self.status_manager.show_error("DailyReport", "No report to print")
            return
        
        try:
            printer = QPrinter()
            dialog = QPrintDialog(printer, self)
            
            if dialog.exec():
                # Create HTML for printing
                html = self.create_print_html()
                
                # Print using QTextDocument
                from PySide6.QtGui import QTextDocument
                document = QTextDocument()
                document.setHtml(html)
                document.print_(printer)
                
                self.status_manager.show_success("DailyReport", "🖨️ Report sent to printer")
                
        except Exception as e:
            logger.error(f"Error printing: {e}")
            self.status_manager.show_error("DailyReport", f"Print error: {str(e)[:100]}")

    def create_print_html(self):
        """ایجاد HTML برای چاپ"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Daily Drilling Report</h1>
            <p><strong>Well:</strong> {self.well_combo.currentText()}</p>
            <p><strong>Date:</strong> {self.report_date.date().toString('yyyy-MM-dd')}</p>
            <p><strong>Rig Day:</strong> {self.rig_day.value()}</p>
        </body>
        </html>
        """
        return html

    # ========== Event Handlers ==========
    def on_date_changed(self):
        """هنگام تغییر تاریخ گزارش"""
        well_id = self.well_combo.currentData()
        
        if well_id:
            # وقتی تاریخ تغییر کرد، شماره گزارش را از اسپاد دیت محاسبه کن
            self.calculate_report_number_from_spud_date()
            
            # همچنین ریگ دی را بر اساس سکشن انتخابی محاسبه کن
            section_id = self.section_combo.currentData()
            if section_id and section_id != -1:
                self.calculate_rig_day_for_section(section_id)
        
        self.status_manager.show_message(
            "DailyReport", 
            f"Report date: {self.report_date.date().toString('yyyy-MM-dd')}",
            1500
        )
        
    def on_tab_changed(self, index):
        """هنگام تغییر تب"""
        tab_names = ["24 Hours", "Morning Tour"]
        if 0 <= index < len(tab_names):
            self.status_manager.show_message(
                "DailyReport", 
                f"Viewing: {tab_names[index]}",
                1000
            )

    def calculate_report_number_from_spud_date(self):
        """محاسبه شماره گزارش بر اساس اختلاف تاریخ اسپاد و تاریخ گزارش"""
        well_id = self.well_combo.currentData()
        
        if not well_id:
            return
            
        try:
            session = self.db_manager.create_session()
            try:
                from core.database import Well
                well = session.query(Well).filter(Well.id == well_id).first()
                
                if well and well.spud_date:
                    report_date = self.report_date.date().toPython()
                    spud_date = well.spud_date
                    
                    # محاسبه اختلاف روزها
                    if report_date >= spud_date:
                        delta_days = (report_date - spud_date).days
                        # شماره گزارش = روز اسپاد + 1 (روز اسپاد = گزارش شماره 1)
                        report_number = delta_days + 1
                        
                        # فقط اگر شماره گزارش بزرگتر از صفر باشد ست کن
                        if report_number > 0:
                            self.report_number.setValue(report_number)
                            logger.info(f"Report number calculated: {report_number} (Spud: {spud_date}, Report: {report_date})")
                    else:
                        # اگر تاریخ گزارش قبل از اسپاد باشد
                        self.status_manager.show_message(
                            "DailyReport",
                            "Report date is before spud date. Using default report number.",
                            3000
                        )
                else:
                    # اگر چاه اسپاد دیت نداشته باشد
                    self.status_manager.show_message(
                        "DailyReport",
                        "Well has no spud date. Using default report number.",
                        3000
                    )
                    
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating report number from spud date: {e}")

    def auto_calculate_report_info(self):
        """محاسبه خودکار اطلاعات گزارش (شماره و روز حفاری)"""
        well_id = self.well_combo.currentData()
        section_id = self.section_combo.currentData()
        
        if not well_id:
            return
            
        # 1. ابتدا شماره گزارش را از اسپاد دیت محاسبه کن
        self.calculate_report_number_from_spud_date()
        
        # 2. سپس ریگ دی را بر اساس گزارش‌های قبلی محاسبه کن
        if section_id and section_id != -1:
            self.calculate_rig_day_for_section(section_id)
        else:
            self.calculate_rig_day_for_well(well_id)

    def calculate_rig_day_for_section(self, section_id):
        """محاسبه روز حفاری برای یک سکشن خاص"""
        try:
            session = self.db_manager.create_session()
            try:
                from core.database import DailyReport
                report_date = self.report_date.date().toPython()
                
                # بررسی وجود گزارش برای این تاریخ در این سکشن
                existing_report = session.query(DailyReport).filter(
                    DailyReport.section_id == section_id,
                    DailyReport.report_date == report_date
                ).first()
                
                if existing_report:
                    # اگر گزارش برای امروز وجود دارد، همان ریگ دی را استفاده کن
                    self.rig_day.setValue(existing_report.rig_day or 1)
                    logger.info(f"Using existing rig day: {existing_report.rig_day}")
                else:
                    # پیدا کردن آخرین گزارش این سکشن
                    last_report = session.query(DailyReport).filter(
                        DailyReport.section_id == section_id
                    ).order_by(DailyReport.report_date.desc()).first()
                    
                    if last_report:
                        # ریگ دی = آخرین ریگ دی + 1
                        self.rig_day.setValue((last_report.rig_day or 0) + 1)
                    else:
                        # اولین گزارش این سکشن
                        self.rig_day.setValue(1)
                        
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating rig day for section: {e}")

    def calculate_rig_day_for_well(self, well_id):
        """محاسبه روز حفاری برای کل چاه (اگر سکشن انتخاب نشده)"""
        try:
            session = self.db_manager.create_session()
            try:
                from core.database import DailyReport
                report_date = self.report_date.date().toPython()
                
                # بررسی وجود گزارش برای این تاریخ در این چاه
                existing_report = session.query(DailyReport).filter(
                    DailyReport.well_id == well_id,
                    DailyReport.report_date == report_date
                ).first()
                
                if existing_report:
                    self.rig_day.setValue(existing_report.rig_day or 1)
                else:
                    # پیدا کردن آخرین گزارش این چاه
                    last_report = session.query(DailyReport).filter(
                        DailyReport.well_id == well_id
                    ).order_by(DailyReport.report_date.desc()).first()
                    
                    if last_report:
                        self.rig_day.setValue((last_report.rig_day or 0) + 1)
                    else:
                        self.rig_day.setValue(1)
                        
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating rig day for well: {e}")
    
    def show_spud_date_info(self):
        """نمایش اطلاعات اسپاد دیت در status bar"""
        well_id = self.well_combo.currentData()
        
        if not well_id:
            return
            
        try:
            session = self.db_manager.create_session()
            try:
                from core.database import Well
                well = session.query(Well).filter(Well.id == well_id).first()
                
                if well and well.spud_date:
                    report_date = self.report_date.date().toPython()
                    delta_days = (report_date - well.spud_date).days
                    
                    if delta_days >= 0:
                        self.status_manager.show_message(
                            "DailyReport",
                            f"Spud Date: {well.spud_date} | Day {delta_days + 1} of drilling",
                            5000
                        )
                    else:
                        self.status_manager.show_message(
                            "DailyReport",
                            f"Spud Date: {well.spud_date} | Report date is before spud date",
                            5000
                        )
                        
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error showing spud date info: {e}")
    
    # ========== Base Methods ==========

    def save_data(self):
        """ذخیره داده‌ها - برای AutoSaveManager"""
        if not self.current_well:
            self.status_manager.show_message(
                "DailyReportWidget",
                "No well selected for saving",
                3000
            )
            return False
        
        # اگر current_report وجود ندارد، یک گزارش جدید ایجاد کنید
        if not self.current_report and hasattr(self, 'report_id_input'):
            report_id = self.report_id_input.text()
            if report_id and report_id.isdigit():
                self.current_report = int(report_id)
        return self.save_report()
        
    def load_reports_for_section(self, section_id):
        """بارگذاری گزارش‌های یک سکشن"""
        if not section_id or section_id == -1:
            return
            
        try:
            reports = self.db_manager.get_daily_reports_by_section(section_id)
            
            # می‌توانید گزارش‌ها را در یک لیست نمایش دهید
            if reports:
                # Auto-load the latest report
                latest_report = reports[0]  # First one is latest
                self.load_report_by_id(latest_report["id"])
        except Exception as e:
            logger.error(f"Error loading reports: {e}")
      
    def refresh(self):
        """رفرش ویجت"""
        self.load_wells()
        if self.current_report:
            self.load_report_by_id(self.current_report["id"])
        self.status_manager.show_success("DailyReport", "Data refreshed")

    def cleanup(self):
        """پاکسازی منابع"""
        logger.info("DailyReportWidget cleanup completed")

    def setup_shortcuts(self):
        """تنظیم کلیدهای میانبر"""
        # Ctrl+S برای ذخیره
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_report)
        
        # Ctrl+N برای گزارش جدید
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self.new_report)
        
        # Ctrl+L برای بارگذاری
        load_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        load_shortcut.activated.connect(self.load_report_dialog)
    
    def validate_form(self):
        """اعتبارسنجی فرم قبل از ذخیره"""
        errors = []
        
        # چک چاه
        if not self.well_combo.currentData():
            errors.append("Please select a well")
        
        # چک سکشن
        section_id = self.section_combo.currentData()
        if not section_id or section_id == -1:
            errors.append("Please select a section")
        
        # چک تاریخ
        if not self.report_date.date().isValid():
            errors.append("Invalid report date")
        
        # چک عمق‌ها
        if self.depth_2400.value() < self.depth_0000.value():
            errors.append("Depth at 24:00 must be greater than or equal to depth at 00:00")
        
        # چک لاگ‌های زمانی
        if self.time_24_table.rowCount() == 0:
            errors.append("Please add at least one activity to 24-hour time log")
        
        return errors
        
    def convert_legacy_times(self):
        """تبدیل زمان‌های قدیمی 00:00 به 24:00 (در صورت نیاز)"""
        # این تابع زمانی استفاده می‌شود که می‌خواهید
        # زمان‌های قدیمی 00:00 را به 24:00 تبدیل کنید
        
        for table in [self.time_24_table, self.morning_table]:
            for row in range(table.rowCount()):
                from_widget = table.cellWidget(row, 0)
                to_widget = table.cellWidget(row, 1)
                
                if isinstance(from_widget, TimeEdit24):
                    if from_widget.time().hour() == 0 and from_widget.time().minute() == 0:
                        from_widget.setTime2400(True)
                
                if isinstance(to_widget, TimeEdit24):
                    if to_widget.time().hour() == 0 and to_widget.time().minute() == 0:
                        to_widget.setTime2400(True)