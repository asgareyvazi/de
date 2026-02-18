"""
Home Tab - Dashboard and Overview with Real Data
"""

import logging
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QFrame,
    QScrollArea,
)
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtCore import Qt, QTimer, QDate
from core.managers import StatusBarManager, TableManager, ExportManager
from core.core import CentralFunctions

logger = logging.getLogger(__name__)


class HomeTab(QWidget):
    """Home/Dashboard Tab - Shows overview with real data"""

    def __init__(self, db_manager, central_functions):
        super().__init__()
        self.db_manager = db_manager
        self.cf = central_functions
        self.status_manager = StatusBarManager()
        self.status_manager.register_widget("HomeTab", self)

        self.last_update = None

        self.init_ui()
        self.setup_connections()
        self.load_data()

        # Setup refresh timer (every 60 seconds)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.start(60000)

    def init_ui(self):
        """Initialize user interface with scroll area"""
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Create container widget
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        self.title_label = QLabel("🏠 DrillMaster Dashboard")
        self.title_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.title_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Last update time
        self.last_update_label = QLabel("Last update: --:--")
        self.last_update_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        header_layout.addWidget(self.last_update_label)

        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setMinimumWidth(100)
        self.refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #bdc3c7;")
        main_layout.addWidget(separator)

        # Statistics Grid
        stats_group = QGroupBox("📊 Project Statistics")
        stats_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)

        # Define statistics items
        self.stats_items = {
            "companies": {
                "row": 0,
                "col": 0,
                "label": "🏢 Companies:",
                "value": "0",
                "color": "#3498db",
            },
            "projects": {
                "row": 0,
                "col": 2,
                "label": "📁 Projects:",
                "value": "0",
                "color": "#2ecc71",
            },
            "wells": {
                "row": 0,
                "col": 4,
                "label": "🛢️ Wells:",
                "value": "0",
                "color": "#e74c3c",
            },
            "active_wells": {
                "row": 1,
                "col": 0,
                "label": "🔧 Active Wells:",
                "value": "0",
                "color": "#f39c12",
            },
            "planning_wells": {
                "row": 1,
                "col": 2,
                "label": "📋 Planning Wells:",
                "value": "0",
                "color": "#9b59b6",
            },
            "completed_wells": {
                "row": 1,
                "col": 4,
                "label": "✅ Completed Wells:",
                "value": "0",
                "color": "#27ae60",
            },
        }

        # Create statistics labels
        self.stats_widgets = {}
        for key, item in self.stats_items.items():
            # Label
            label = QLabel(item["label"])
            label.setFont(QFont("Arial", 11))
            stats_layout.addWidget(label, item["row"], item["col"])

            # Value
            value_label = QLabel(item["value"])
            value_label.setFont(QFont("Arial", 16, QFont.Bold))
            value_label.setStyleSheet(f"color: {item['color']};")
            value_label.setAlignment(Qt.AlignCenter)
            stats_layout.addWidget(value_label, item["row"], item["col"] + 1)

            self.stats_widgets[key] = value_label

        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # Recent Wells Table
        wells_group = QGroupBox("🛢️ Recent Wells")
        wells_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #e74c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """
        )
        wells_layout = QVBoxLayout()

        self.wells_table = QTableWidget()
        self.wells_table.setColumnCount(5)
        self.wells_table.setHorizontalHeaderLabels(
            ["Well Name", "Project", "Status", "Type", "Last Update"]
        )
        self.wells_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.wells_table.setAlternatingRowColors(True)
        self.wells_table.setMinimumHeight(200)

        wells_layout.addWidget(self.wells_table)
        wells_group.setLayout(wells_layout)
        main_layout.addWidget(wells_group)

        # Project Progress Section
        self.progress_group = QGroupBox("📈 Project Progress")
        self.progress_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #2ecc71;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """
        )
        self.progress_layout = QVBoxLayout()
        self.progress_group.setLayout(self.progress_layout)
        main_layout.addWidget(self.progress_group)

        # System Status
        status_group = QGroupBox("🟢 System Status")
        status_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #f39c12;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """
        )
        status_layout = QGridLayout()

        self.status_items = [
            ("database", "Database", "Checking..."),
            ("autosave", "Auto-save", "Checking..."),
            ("backup", "Last Backup", "Checking..."),
            ("users", "Active Users", "Checking..."),
            ("reports", "Today's Reports", "Checking..."),
            ("storage", "Storage", "Checking..."),
        ]

        self.status_widgets = {}
        for i, (key, label, value) in enumerate(self.status_items):
            status_layout.addWidget(QLabel(f"{label}:"), i, 0)
            value_label = QLabel(value)
            value_label.setFont(QFont("Arial", 10))
            status_layout.addWidget(value_label, i, 1)
            self.status_widgets[key] = value_label

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # Quick Actions
        actions_group = QGroupBox("⚡ Quick Actions")
        actions_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """
        )
        actions_layout = QGridLayout()

        actions = [
            ("➕ New Well", "Create a new well", "#3498db", self.open_new_well_tab),
            (
                "📝 Daily Report",
                "Create daily report",
                "#2ecc71",
                self.open_daily_report,
            ),
            ("📊 Export Data", "Export project data", "#e74c3c", self.export_data),
            ("📋 Well List", "View all wells", "#f39c12", self.open_well_info_tab),
            ("📈 Analytics", "View analytics", "#9b59b6", self.open_analysis_tab),
            ("⚙️ Settings", "Application settings", "#34495e", self.open_settings_tab),
        ]

        row, col = 0, 0
        for text, tooltip, color, slot in actions:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            btn.setMinimumHeight(45)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-weight: bold;
                    border-radius: 5px;
                    padding: 8px;
                }}
                QPushButton:hover {{
                    background-color: {self.darken_color(color)};
                }}
            """
            )
            actions_layout.addWidget(btn, row, col)

            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1

        actions_group.setLayout(actions_layout)
        main_layout.addWidget(actions_group)

        # Add stretch to push everything up
        main_layout.addStretch()

        # Set container to scroll area
        scroll_area.setWidget(container)

        # Set main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

    def darken_color(self, color):
        """Darken a hex color"""
        try:
            color = color.lstrip("#")
            rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
            darkened = tuple(max(0, c - 30) for c in rgb)
            return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"
        except:
            return color

    def setup_connections(self):
        """Setup signal connections"""
        if hasattr(self, "daily_report_btn"):
            self.daily_report_btn.clicked.connect(self.open_daily_report)

    def load_data(self):
        """Load real data from database"""
        try:
            logger.info("Loading dashboard data from database...")

            # Update last update time
            self.last_update = datetime.now()
            self.last_update_label.setText(
                f"Last update: {self.last_update.strftime('%H:%M:%S')}"
            )

            # Get hierarchy from database
            hierarchy = self.db_manager.get_hierarchy()

            # Calculate real statistics
            companies_count = len(hierarchy)
            projects_count = 0
            wells_count = 0
            active_wells_count = 0
            planning_wells_count = 0
            completed_wells_count = 0

            all_wells = []

            for company in hierarchy:
                projects_count += len(company.get("projects", []))
                for project in company.get("projects", []):
                    wells = project.get("wells", [])
                    wells_count += len(wells)

                    for well in wells:
                        well["project_name"] = project.get("name", "Unknown")
                        all_wells.append(well)

                        status = well.get("status", "").lower()
                        if status in ["drilling", "active"]:
                            active_wells_count += 1
                        elif status in ["planning", "design"]:
                            planning_wells_count += 1
                        elif status in ["completed", "abandoned", "producing"]:
                            completed_wells_count += 1

            # Update statistics labels
            self.stats_widgets["companies"].setText(str(companies_count))
            self.stats_widgets["projects"].setText(str(projects_count))
            self.stats_widgets["wells"].setText(str(wells_count))
            self.stats_widgets["active_wells"].setText(str(active_wells_count))
            self.stats_widgets["planning_wells"].setText(str(planning_wells_count))
            self.stats_widgets["completed_wells"].setText(str(completed_wells_count))

            # Load recent wells (last 10)
            self.load_recent_wells(all_wells)

            # Load project progress
            self.load_project_progress(hierarchy)

            # Update system status
            self.update_system_status()

            logger.info("Dashboard data loaded successfully")

        except Exception as e:
            logger.error(f"Error loading dashboard data: {str(e)}")
            self.last_update_label.setText("Last update: Failed to load data")
            self.status_manager.show_error("HomeTab", f"Failed to load data: {str(e)[:50]}...")
            # می‌توانید مقادیر پیش‌فرض را نیز تنظیم کنید
            for key in self.stats_widgets:
                self.stats_widgets[key].setText("0")

    def load_recent_wells(self, wells):
        """Load recent wells into table"""
        try:
            # Sort wells by ID (newest first) and take last 10
            sorted_wells = sorted(wells, key=lambda x: x.get("id", 0), reverse=True)[
                :10
            ]

            self.wells_table.setRowCount(len(sorted_wells))

            for row, well in enumerate(sorted_wells):
                # Well Name
                name_item = QTableWidgetItem(well.get("name", "Unknown"))
                self.wells_table.setItem(row, 0, name_item)

                # Project
                project_item = QTableWidgetItem(well.get("project_name", "Unknown"))
                self.wells_table.setItem(row, 1, project_item)

                # Status
                status = well.get("status", "Unknown")
                status_item = QTableWidgetItem(status)

                # Color code status
                if status.lower() in ["drilling", "active"]:
                    status_item.setForeground(QColor("#27ae60"))  # Green
                elif status.lower() in ["planning", "design"]:
                    status_item.setForeground(QColor("#f39c12"))  # Orange
                elif status.lower() in ["completed"]:
                    status_item.setForeground(QColor("#3498db"))  # Blue
                elif status.lower() in ["suspended", "abandoned"]:
                    status_item.setForeground(QColor("#e74c3c"))  # Red

                self.wells_table.setItem(row, 2, status_item)

                # Type
                well_type = well.get("well_type", "Unknown")
                type_item = QTableWidgetItem(well_type)
                self.wells_table.setItem(row, 3, type_item)

                # Last Update (simulated - in real app would be from updated_at)
                last_update = "Today"  # Placeholder
                update_item = QTableWidgetItem(last_update)
                self.wells_table.setItem(row, 4, update_item)

        except Exception as e:
            logger.error(f"Error loading recent wells: {str(e)}")

    def load_project_progress(self, hierarchy):
        """Load real project progress from database"""
        try:
            # Clear existing progress bars
            while self.progress_layout.count():
                item = self.progress_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add progress bars for each project
            for company in hierarchy:
                for project in company.get("projects", []):
                    project_name = project.get("name", "Unknown")
                    wells = project.get("wells", [])

                    if wells:
                        project_layout = QHBoxLayout()

                        # Project label
                        label_text = (
                            f"{project_name} ({company.get('name', 'Unknown')})"
                        )
                        if len(label_text) > 30:
                            label_text = label_text[:27] + "..."

                        label = QLabel(f"{label_text}:")
                        label.setMinimumWidth(200)
                        label.setToolTip(
                            f"{project_name} - {company.get('name', 'Unknown')}"
                        )
                        project_layout.addWidget(label)

                        # Progress bar
                        progress_bar = QProgressBar()
                        progress_bar.setRange(0, 100)

                        # Calculate progress based on well statuses
                        total_wells = len(wells)
                        if total_wells > 0:
                            completed_wells = len(
                                [
                                    w
                                    for w in wells
                                    if w.get("status", "").lower()
                                    in ["completed", "producing"]
                                ]
                            )
                            progress = int((completed_wells / total_wells) * 100)
                        else:
                            progress = 0

                        progress_bar.setValue(progress)

                        # Set color based on progress
                        if progress < 30:
                            progress_bar.setStyleSheet(
                                """
                                QProgressBar {
                                    border: 1px solid #bdc3c7;
                                    border-radius: 5px;
                                    text-align: center;
                                }
                                QProgressBar::chunk {
                                    background-color: #e74c3c;
                                    border-radius: 5px;
                                }
                            """
                            )
                        elif progress < 70:
                            progress_bar.setStyleSheet(
                                """
                                QProgressBar {
                                    border: 1px solid #bdc3c7;
                                    border-radius: 5px;
                                    text-align: center;
                                }
                                QProgressBar::chunk {
                                    background-color: #f39c12;
                                    border-radius: 5px;
                                }
                            """
                            )
                        else:
                            progress_bar.setStyleSheet(
                                """
                                QProgressBar {
                                    border: 1px solid #bdc3c7;
                                    border-radius: 5px;
                                    text-align: center;
                                }
                                QProgressBar::chunk {
                                    background-color: #27ae60;
                                    border-radius: 5px;
                                }
                            """
                            )

                        project_layout.addWidget(progress_bar)

                        # Percentage label
                        wells_text = f"{len([w for w in wells if w.get('status', '').lower() in ['completed', 'producing']])}/{total_wells}"
                        percentage_label = QLabel(f"{progress}% ({wells_text} wells)")
                        percentage_label.setMinimumWidth(120)
                        project_layout.addWidget(percentage_label)

                        self.progress_layout.addLayout(project_layout)

            # If no projects, show message
            if self.progress_layout.count() == 0:
                no_data_label = QLabel("No project data available")
                no_data_label.setAlignment(Qt.AlignCenter)
                no_data_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
                self.progress_layout.addWidget(no_data_label)

        except Exception as e:
            logger.error(f"Error loading project progress: {str(e)}")

    def update_system_status(self):
        """Update system status with real information"""
        try:
            # Database status
            try:
                hierarchy = self.db_manager.get_hierarchy()
                db_status = "✅ Connected"
                db_color = "#27ae60"
            except:
                db_status = "❌ Disconnected"
                db_color = "#e74c3c"

            self.status_widgets["database"].setText(db_status)
            self.status_widgets["database"].setStyleSheet(
                f"color: {db_color}; font-weight: bold;"
            )

            # Auto-save status (always on for now)
            self.status_widgets["autosave"].setText("✅ Active")
            self.status_widgets["autosave"].setStyleSheet(
                "color: #27ae60; font-weight: bold;"
            )

            # Last backup (simulated)
            today = QDate.currentDate()
            backup_date = today.addDays(-1)  # Yesterday
            self.status_widgets["backup"].setText(
                f"📅 {backup_date.toString('yyyy-MM-dd')}"
            )
            self.status_widgets["backup"].setStyleSheet("color: #3498db;")

            # Active users (from session, simulated)
            self.status_widgets["users"].setText("👥 1 active")
            self.status_widgets["users"].setStyleSheet("color: #9b59b6;")

            # Today's reports (simulated - would come from daily_reports table)
            self.status_widgets["reports"].setText("📋 0 today")
            self.status_widgets["reports"].setStyleSheet("color: #f39c12;")

            # Storage (simulated)
            import os

            if os.path.exists("drillmaster.db"):
                size = os.path.getsize("drillmaster.db") / (1024 * 1024)  # MB
                self.status_widgets["storage"].setText(f"💾 {size:.1f} MB")
                self.status_widgets["storage"].setStyleSheet(
                    "color: #2ecc71;" if size < 100 else "color: #e74c3c;"
                )
            else:
                self.status_widgets["storage"].setText("💾 N/A")
                self.status_widgets["storage"].setStyleSheet("color: #7f8c8d;")

        except Exception as e:
            logger.error(f"Error updating system status: {str(e)}")

    def open_new_well_tab(self):
        """باز کردن تب ایجاد چاه جدید"""
        if hasattr(self, "parent_tab_widget"):
            # پیدا کردن تب Well Info (فرض می‌کنیم تب دوم است)
            self.parent_tab_widget.setCurrentIndex(1)  # یا index مناسب
            # اگر widget تب Well Info متد new_well داشته باشد
            current_widget = self.parent_tab_widget.currentWidget()
            if hasattr(current_widget, "new_well"):
                current_widget.new_well()

            self.status_manager.show_success("HomeTab", "Opened New Well form")

    def new_report(self):
        """Create new daily report"""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Daily Report",
            "Daily report feature will be available in the 'Daily Report' tab (coming soon)",
        )

    def export_data(self):
        """Export data"""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Export",
            "Export feature will be available in the 'Export' tab (coming soon)",
        )

    def open_well_info_tab(self):
        """باز کردن تب اطلاعات چاه‌ها"""
        if hasattr(self, "parent_tab_widget"):
            for i in range(self.parent_tab_widget.count()):
                if self.parent_tab_widget.tabText(i) == "🛢️ Well Info":
                    self.parent_tab_widget.setCurrentIndex(i)
                    break

            self.status_manager.show_message(
                "HomeTab", "Opened Well Information tab", 2000
            )

    def open_analysis_tab(self):
        """باز کردن تب تحلیل‌ها"""
        if hasattr(self, "parent_tab_widget"):
            for i in range(self.parent_tab_widget.count()):
                if self.parent_tab_widget.tabText(i) == "📊 Analysis":
                    self.parent_tab_widget.setCurrentIndex(i)
                    break

            self.status_manager.show_message("HomeTab", "Opened Analysis tab", 2000)

    def open_settings_tab(self):
        """باز کردن تب تنظیمات"""
        if hasattr(self, "parent_tab_widget"):
            for i in range(self.parent_tab_widget.count()):
                if self.parent_tab_widget.tabText(i) == "⚙️ Settings":
                    self.parent_tab_widget.setCurrentIndex(i)
                    break

            self.status_manager.show_message("HomeTab", "Opened Settings tab", 2000)

    def set_parent_tab_widget(self, tab_widget):
        """Set reference to parent tab widget for navigation"""
        self.parent_tab_widget = tab_widget

    def on_selection_changed(self, item_type, item_id):
        """Handle selection change"""
        # Home tab doesn't typically handle selection changes
        pass

    def refresh(self):
        """Refresh tab data"""
        self.load_data()

    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()

    def open_daily_report(self):
        """سوئیچ به تب Daily Report"""
        if hasattr(self.parent_window, "tab_widget"):
            # پیدا کردن index تب Daily Report
            tab_widget = self.parent_window.tab_widget

            for i in range(tab_widget.count()):
                if tab_widget.tabText(i) == "📅 Daily Report":
                    tab_widget.setCurrentIndex(i)

                    # اگر تب Daily Report ویجت خاصی دارد، آن را refresh کنید
                    daily_report_widget = tab_widget.widget(i)
                    if hasattr(daily_report_widget, "refresh"):
                        daily_report_widget.refresh()

                    self.parent_window.status_manager.show_success(
                        "HomeTab", "Opened Daily Report tab"
                    )
                    return

            # اگر تب پیدا نشد
            self.parent_window.status_manager.show_error(
                "HomeTab", "Daily Report tab not found"
            )
