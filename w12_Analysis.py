"""
Advanced Analysis and Monitoring Tab for Drilling Software
PySide6 Version
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from sqlalchemy import func, desc, and_, or_, text, extract
from sqlalchemy.orm import Session, aliased
import logging
import json
import tempfile
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# PySide6 imports
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
import pyqtgraph as pg

# Import database models
from core.database import (
    Company, Project, Well, Section, DailyReport, TimeLog24H, 
    TimeLogMorning, User, DrillingParameters, MudReport,
    CementReport, CasingReport, WellboreSchematic,
    TripSheetEntry, SurveyPoint, TrajectoryCalculation, TrajectoryPlot,
    BitReport, BHAReport, DownholeEquipment, FormationReport,
    LogisticsPersonnel, ServiceCompanyPOB, FuelWaterInventory,
    BulkMaterials, TransportLog, TransportNotes,
    SafetyReport, SafetyIncident, BOPComponent, WasteRecord,
    ServiceCompany, ServiceNote, MaterialRequest, EquipmentLog,
    SevenDaysLookahead, NPTReport, ActivityCode, TimeDepthData, ROPAnalysis,
    ExportTemplate, DatabaseManager
)

logger = logging.getLogger(__name__)

class DrillWidgetBase(QWidget):
    """Base widget class for drill widgets - PySide6 Version"""
    def __init__(self, name, db_manager):
        super().__init__()
        self.name = name
        self.db_manager = db_manager
        self.setObjectName(name)
        
    def get_button_style(self, button_type="default", large=False):
        """Return button style based on type - PySide6 Version"""
        size = "16px" if large else "14px"
        padding = "14px 28px" if large else "12px 24px"
        
        styles = {
            "default": f"""
                QPushButton {{
                    background: #34495e;
                    color: white;
                    border: none;
                    padding: {padding};
                    border-radius: 6px;
                    font-size: {size};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: #3c5570;
                }}
                QPushButton:pressed {{
                    background: #2c3e50;
                }}
            """,
            "primary": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3498db, stop:1 #2980b9);
                    color: white;
                    border: none;
                    padding: {padding};
                    border-radius: 8px;
                    font-size: {size};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2980b9, stop:1 #2573a7);
                }}
            """,
            "success": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2ecc71, stop:1 #27ae60);
                    color: white;
                    border: none;
                    padding: {padding};
                    border-radius: 8px;
                    font-size: {size};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #27ae60, stop:1 #229954);
                }}
            """,
            "info": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #9b59b6, stop:1 #8e44ad);
                    color: white;
                    border: none;
                    padding: {padding};
                    border-radius: 8px;
                    font-size: {size};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #8e44ad, stop:1 #7d3c98);
                }}
            """,
            "warning": f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #f39c12, stop:1 #e67e22);
                    color: white;
                    border: none;
                    padding: {padding};
                    border-radius: 8px;
                    font-size: {size};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e67e22, stop:1 #d35400);
                }}
            """,
        }
        return styles.get(button_type, styles["default"])


class AnalysisWidget(DrillWidgetBase):
    """Advanced Professional Analysis and Monitoring Dashboard - PySide6 Version"""
    
    def __init__(self, db_manager):
        super().__init__("AnalysisWidget", db_manager)
        self.db = db_manager
        self.current_well_id = None
        self.current_well_name = None
        self.current_project_id = None
        
        # Data caches
        self.data_cache = {}
        self.cache_time = {}
        self.cache_timeout = 30000  # 30 seconds
        
        # Chart data storage
        self.chart_data = {
            'time_depth': None,
            'npt': None,
            'performance': None,
            'kpi': None,
            'daily': None,
            'analytics': None
        }
        
        # Performance KPI cards
        self.perf_kpi_cards = []
        
        # Today's indicators
        self.today_indicators = {}
        
        # PyQtGraph configuration
        pg.setConfigOption("background", "#1e1e1e")
        pg.setConfigOption("foreground", "#ffffff")
        pg.setConfigOption("antialias", True)
        pg.setConfigOptions(useOpenGL=True)
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.auto_update_data)
        self.update_interval = 10000  # 10 seconds
        
        # Export directory
        self.export_dir = "exports/analysis"
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # ============ HEADER SECTION ============
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #34495e);
                border-radius: 12px;
                padding: 15px;
                margin: 5px;
            }
        """)
        
        header_layout = QGridLayout()
        
        # Status and well name
        self.status_label = QLabel("🔴 No well selected")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #e74c3c;
                padding: 8px;
            }
        """)
        header_layout.addWidget(self.status_label, 0, 0, 1, 2)
        
        self.well_label = QLabel("🌍 Well: Not Selected")
        self.well_label.setStyleSheet("font-size: 14px; color: #bdc3c7;")
        header_layout.addWidget(self.well_label, 1, 0, 1, 2)
        
        # KPI Cards with modern design
        self.kpi_cards_widget = self.create_enhanced_kpi_cards()
        header_layout.addWidget(self.kpi_cards_widget, 0, 2, 2, 3)
        
        # Monitoring controls
        control_widget = QWidget()
        control_layout = QHBoxLayout()
        
        self.last_update_label = QLabel("Last update: --:--:--")
        self.last_update_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        control_layout.addWidget(self.last_update_label)
        
        control_layout.addStretch()
        
        # Auto update interval selection
        self.auto_update_interval = QComboBox()
        self.auto_update_interval.addItems(["5 seconds", "10 seconds", "30 seconds", "1 minute", "5 minutes"])
        self.auto_update_interval.setCurrentIndex(1)
        self.auto_update_interval.setStyleSheet("""
            QComboBox {
                background: #34495e;
                color: white;
                border: 1px solid #2c3e50;
                border-radius: 4px;
                padding: 5px;
                min-width: 120px;
            }
        """)
        control_layout.addWidget(QLabel("Auto Update:"))
        control_layout.addWidget(self.auto_update_interval)
        
        self.auto_update_check = QCheckBox("🔄 Auto Update")
        self.auto_update_check.setChecked(False)
        self.auto_update_check.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #ecf0f1;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.auto_update_check.stateChanged.connect(self.toggle_auto_update)
        control_layout.addWidget(self.auto_update_check)
        
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.setStyleSheet(self.get_button_style("primary", large=True))
        refresh_btn.clicked.connect(self.update_all_data)
        control_layout.addWidget(refresh_btn)
        
        clear_cache_btn = QPushButton("🗑️ Clear Cache")
        clear_cache_btn.setStyleSheet(self.get_button_style("warning"))
        clear_cache_btn.clicked.connect(self.clear_cache)
        control_layout.addWidget(clear_cache_btn)
        
        control_widget.setLayout(control_layout)
        header_layout.addWidget(control_widget, 2, 0, 1, 5)
        
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
        
        # Help message
        self.help_label = QLabel(
            "📋 Please select a well from the Well Info tab to start analysis.\n"
            "After opening a well, analysis data will automatically load."
        )
        self.help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-style: italic;
                padding: 25px;
                background: #ecf0f110;
                border-radius: 8px;
                margin: 10px;
            }
        """)
        layout.addWidget(self.help_label)
        
        # Analysis tabs
        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #34495e;
                border-radius: 8px;
                background: #2c3e50;
                margin-top: 5px;
            }
            QTabBar::tab {
                background: #34495e;
                color: #ecf0f1;
                padding: 12px 24px;
                margin-right: 3px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
            }
            QTabBar::tab:hover {
                background: #3c5570;
            }
        """)
        
        # Tab 1: Time vs Depth with chart
        self.time_depth_tab = self.create_time_depth_tab()
        self.analysis_tabs.addTab(self.time_depth_tab, "📈 Time vs Depth")
        
        # Tab 2: NPT Analysis
        self.npt_tab = self.create_npt_tab()
        self.analysis_tabs.addTab(self.npt_tab, "⏱️ NPT Analysis")
        
        # Tab 3: Performance Dashboard
        self.performance_tab = self.create_performance_tab()
        self.analysis_tabs.addTab(self.performance_tab, "⚡ Performance")
        
        # Tab 4: Daily Summary & Monitoring
        self.daily_tab = self.create_daily_tab()
        self.analysis_tabs.addTab(self.daily_tab, "📅 Daily Monitor")
        
        # Tab 5: Advanced Analytics
        self.analytics_tab = self.create_analytics_tab()
        self.analysis_tabs.addTab(self.analytics_tab, "📊 Advanced Analytics")
        
        # Hide tabs initially
        self.analysis_tabs.setVisible(False)
        layout.addWidget(self.analysis_tabs)
        
        # Bottom - main buttons
        bottom_widget = QWidget()
        bottom_widget.setStyleSheet(
            "background: #34495e; border-radius: 8px; padding: 10px;"
        )
        bottom_layout = QHBoxLayout()
        
        self.export_dashboard_btn = QPushButton("📊 Export Dashboard")
        self.export_dashboard_btn.setStyleSheet(
            self.get_button_style("success", large=True)
        )
        self.export_dashboard_btn.clicked.connect(self.export_dashboard)
        
        self.export_chart_btn = QPushButton("📤 Export Charts")
        self.export_chart_btn.setStyleSheet(self.get_button_style("info", large=True))
        self.export_chart_btn.clicked.connect(self.export_all_charts)
        
        self.print_report_btn = QPushButton("🖨️ Print Report")
        self.print_report_btn.setStyleSheet(
            self.get_button_style("warning", large=True)
        )
        self.print_report_btn.clicked.connect(self.print_comprehensive_report)
        
        self.export_data_btn = QPushButton("📁 Export Data")
        self.export_data_btn.setStyleSheet(self.get_button_style("primary", large=True))
        self.export_data_btn.clicked.connect(self.export_all_data)
        
        bottom_layout.addWidget(self.export_dashboard_btn)
        bottom_layout.addWidget(self.export_chart_btn)
        bottom_layout.addWidget(self.print_report_btn)
        bottom_layout.addWidget(self.export_data_btn)
        bottom_layout.addStretch()
        
        bottom_widget.setLayout(bottom_layout)
        layout.addWidget(bottom_widget)
        
        self.setLayout(layout)
        
        # Hide bottom buttons initially
        bottom_widget.setVisible(False)
        self.bottom_widget = bottom_widget
        
        # Create export folder
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
    
    def create_enhanced_kpi_cards(self):
        """Create enhanced KPI cards"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        kpi_data = [
            {
                "icon": "🎯",
                "title": "Current Depth",
                "value": "0",
                "unit": "m",
                "color": "#3498DB",
                "trend": "↗️ +0.0m",
            },
            {
                "icon": "📅",
                "title": "Rig Days",
                "value": "0",
                "unit": "days",
                "color": "#2ECC71",
                "trend": "Day 0",
            },
            {
                "icon": "⚡",
                "title": "Avg ROP",
                "value": "0.0",
                "unit": "m/hr",
                "color": "#E74C3C",
                "trend": "↗️ +0.0",
            },
            {
                "icon": "⏱️",
                "title": "Total NPT",
                "value": "0.0",
                "unit": "hrs",
                "color": "#F39C12",
                "trend": "↘️ 0%",
            },
        ]
        
        for kpi in kpi_data:
            card = self.create_kpi_card_modern(**kpi)
            layout.addWidget(card)
        
        widget.setLayout(layout)
        return widget
    
    def create_kpi_card_modern(self, icon="📊", title="", value="0", unit="", color="#3498DB", trend=""):
        """Create modern KPI card"""
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}30, stop:1 {color}10);
                border-radius: 10px;
                border: 2px solid {color}40;
                padding: 12px;
                margin: 5px;
            }}
        """
        )
        
        layout = QVBoxLayout()
        
        # Header with big icon
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 28px; color: {color};")
        title_label = QLabel(title)
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #7f8c8d;
            }
        """
        )
        
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Main value
        value_layout = QHBoxLayout()
        value_label = QLabel(value)
        value_label.setStyleSheet(
            f"""
            QLabel {{
                font-size: 26px;
                font-weight: bold;
                color: {color};
            }}
        """
        )
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("font-size: 14px; color: #95a5a6; margin-top: 8px;")
        
        value_layout.addWidget(value_label)
        value_layout.addWidget(unit_label)
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        # Trend
        if trend:
            trend_label = QLabel(trend)
            trend_label.setStyleSheet("font-size: 11px; color: #95a5a6;")
            layout.addWidget(trend_label)
        
        card.setLayout(layout)
        
        # Store reference for update
        card.value_label = value_label
        card.trend_label = trend_label if trend else None
        
        return card
    
    def create_time_depth_tab(self):
        """Create Time vs Depth tab with chart"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Chart controls
        control_widget = QWidget()
        control_widget.setStyleSheet(
            "background: #34495e; border-radius: 6px; padding: 8px;"
        )
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("📊 Time vs Depth Analysis"))
        
        self.td_show_trend = QCheckBox("📈 Show Trend Line")
        self.td_show_trend.setChecked(True)
        self.td_show_trend.setStyleSheet("color: #ecf0f1;")
        
        self.td_show_projection = QCheckBox("🔮 Show Projection")
        self.td_show_projection.setChecked(False)
        self.td_show_projection.setStyleSheet("color: #ecf0f1;")
        
        self.td_export_btn = QPushButton("📤 Export Chart")
        self.td_export_btn.setStyleSheet(self.get_button_style("primary"))
        self.td_export_btn.clicked.connect(lambda: self.export_chart("time_depth"))
        
        control_layout.addWidget(self.td_show_trend)
        control_layout.addWidget(self.td_show_projection)
        control_layout.addStretch()
        control_layout.addWidget(self.td_export_btn)
        
        control_widget.setLayout(control_layout)
        main_layout.addWidget(control_widget)
        
        # Time vs Depth chart
        chart_container = QWidget()
        chart_container.setStyleSheet("background: #1e1e1e; border-radius: 8px;")
        chart_layout = QVBoxLayout()
        
        # Main chart
        self.time_depth_plot = pg.PlotWidget()
        self.time_depth_plot.setBackground("#1e1e1e")
        self.time_depth_plot.setLabel("left", "Depth (m)", color="#ffffff", size=14)
        self.time_depth_plot.setLabel("bottom", "Time (Days)", color="#ffffff", size=14)
        self.time_depth_plot.showGrid(x=True, y=True, alpha=0.3)
        self.time_depth_plot.setMinimumHeight(300)
        
        chart_layout.addWidget(self.time_depth_plot)
        
        # Daily Gain chart
        self.daily_gain_plot = pg.PlotWidget()
        self.daily_gain_plot.setBackground("#1e1e1e")
        self.daily_gain_plot.setLabel(
            "left", "Daily Gain (m)", color="#ffffff", size=12
        )
        self.daily_gain_plot.setLabel("bottom", "Days", color="#ffffff", size=12)
        self.daily_gain_plot.showGrid(x=True, y=True, alpha=0.3)
        self.daily_gain_plot.setMaximumHeight(150)
        
        chart_layout.addWidget(self.daily_gain_plot)
        
        chart_container.setLayout(chart_layout)
        main_layout.addWidget(chart_container)
        
        # Data table
        table_widget = QWidget()
        table_widget.setStyleSheet(
            "background: #2c3e50; border-radius: 8px; padding: 8px;"
        )
        table_layout = QVBoxLayout()
        
        table_layout.addWidget(QLabel("📋 Depth History"))
        
        self.time_depth_table = QTableWidget()
        self.time_depth_table.setColumnCount(5)
        self.time_depth_table.setHorizontalHeaderLabels(
            ["📅 Date", "#️⃣ Days", "📏 Depth (m)", "📈 Daily Gain", "🔧 Status"]
        )
        self.time_depth_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.time_depth_table.setStyleSheet(
            """
            QTableWidget {
                background: #1e1e1e;
                alternate-background-color: #2c3e50;
                gridline-color: #34495e;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px;
                color: #ecf0f1;
            }
            QHeaderView::section {
                background: #34495e;
                color: #ecf0f1;
                padding: 8px;
                font-weight: bold;
            }
        """
        )
        
        table_layout.addWidget(self.time_depth_table)
        table_widget.setLayout(table_layout)
        main_layout.addWidget(table_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_npt_tab(self):
        """Create NPT Analysis tab"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # NPT Statistics
        stats_widget = QWidget()
        stats_widget.setStyleSheet(
            "background: #34495e; border-radius: 8px; padding: 12px;"
        )
        stats_layout = QGridLayout()
        
        # NPT statistical cards
        self.npt_total_card = self.create_stat_card(
            "⏱️", "Total NPT", "0.0", "hours", "#e74c3c"
        )
        self.npt_percent_card = self.create_stat_card(
            "📊", "NPT %", "0.0", "%", "#f39c12"
        )
        self.npt_daily_card = self.create_stat_card(
            "📅", "Daily Avg", "0.0", "hours/day", "#3498db"
        )
        self.npt_category_card = self.create_stat_card(
            "🔥", "Top Category", "-", "category", "#9b59b6"
        )
        
        stats_layout.addWidget(self.npt_total_card, 0, 0)
        stats_layout.addWidget(self.npt_percent_card, 0, 1)
        stats_layout.addWidget(self.npt_daily_card, 1, 0)
        stats_layout.addWidget(self.npt_category_card, 1, 1)
        
        stats_widget.setLayout(stats_layout)
        main_layout.addWidget(stats_widget)
        
        # NPT chart
        chart_container = QWidget()
        chart_container.setStyleSheet("background: #1e1e1e; border-radius: 8px;")
        chart_layout = QVBoxLayout()
        
        # Pie chart for NPT
        self.npt_pie_plot = pg.PlotWidget()
        self.npt_pie_plot.setBackground("#1e1e1e")
        self.npt_pie_plot.setTitle("NPT Distribution", color="#ffffff", size="14pt")
        self.npt_pie_plot.setMinimumHeight(250)
        
        chart_layout.addWidget(self.npt_pie_plot)
        chart_container.setLayout(chart_layout)
        main_layout.addWidget(chart_container)
        
        # NPT table
        table_widget = QWidget()
        table_widget.setStyleSheet(
            "background: #2c3e50; border-radius: 8px; padding: 8px;"
        )
        table_layout = QVBoxLayout()
        
        table_layout.addWidget(QLabel("📋 NPT Events"))
        
        self.npt_table = QTableWidget()
        self.npt_table.setColumnCount(6)
        self.npt_table.setHorizontalHeaderLabels(
            ["📅 Date", "🕐 From", "🕒 To", "⏱️ Hours", "🏷️ Category", "📝 Description"]
        )
        self.npt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.npt_table.setStyleSheet(self.time_depth_table.styleSheet())
        
        table_layout.addWidget(self.npt_table)
        table_widget.setLayout(table_layout)
        main_layout.addWidget(table_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_stat_card(self, icon, title, value, unit, color):
        """Create statistical card"""
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background: {color}20;
                border-left: 4px solid {color};
                border-radius: 6px;
                padding: 10px;
                margin: 5px;
            }}
        """
        )
        
        layout = QVBoxLayout()
        
        # Title with icon
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("font-size: 13px; color: #7f8c8d; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(f"<b>{value}</b> {unit}")
        value_label.setStyleSheet(f"font-size: 18px; color: {color};")
        layout.addWidget(value_label)
        
        card.setLayout(layout)
        
        # Store reference
        card.value_label = value_label
        
        return card
    
    def create_performance_tab(self):
        """Create Performance Dashboard tab"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Performance KPI cards
        kpi_widget = QWidget()
        kpi_widget.setStyleSheet(
            "background: #34495e; border-radius: 8px; padding: 12px;"
        )
        kpi_layout = QGridLayout()
        
        # 6 performance KPI cards
        perf_kpis = [
            ("⚡", "Avg ROP", "0.0", "m/hr", "#1abc9c"),
            ("🏆", "Best ROP", "0.0", "m/hr", "#e67e22"),
            ("🔧", "Avg WOB", "0.0", "klb", "#3498db"),
            ("🌀", "Avg RPM", "0", "rpm", "#9b59b6"),
            ("💪", "Avg Torque", "0.0", "klb.ft", "#e74c3c"),
            ("📈", "Efficiency", "0.0", "%", "#2ecc71"),
        ]
        
        self.perf_kpi_cards = []
        for i, (icon, title, value, unit, color) in enumerate(perf_kpis):
            row, col = divmod(i, 3)
            card = self.create_stat_card(icon, title, value, unit, color)
            kpi_layout.addWidget(card, row, col)
            self.perf_kpi_cards.append(card)
        
        kpi_widget.setLayout(kpi_layout)
        main_layout.addWidget(kpi_widget)
        
        # Performance charts
        charts_widget = QWidget()
        charts_widget.setStyleSheet("background: #1e1e1e; border-radius: 8px;")
        charts_layout = QVBoxLayout()
        
        self.performance_plot = pg.PlotWidget()
        self.performance_plot.setBackground("#1e1e1e")
        self.performance_plot.setLabel(
            "left", "Performance Metrics", color="#ffffff", size=14
        )
        self.performance_plot.setLabel("bottom", "Bit Run #", color="#ffffff", size=14)
        self.performance_plot.addLegend()
        self.performance_plot.setMinimumHeight(300)
        
        charts_layout.addWidget(self.performance_plot)
        charts_widget.setLayout(charts_layout)
        main_layout.addWidget(charts_widget)
        
        # Performance table
        table_widget = QWidget()
        table_widget.setStyleSheet(
            "background: #2c3e50; border-radius: 8px; padding: 8px;"
        )
        table_layout = QVBoxLayout()
        
        table_layout.addWidget(QLabel("📋 Performance Data"))
        
        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(7)
        self.performance_table.setHorizontalHeaderLabels(
            [
                "📅 Date",
                "🧱 Bit Run",
                "⚡ ROP",
                "🔧 WOB",
                "🌀 RPM",
                "💪 Torque",
                "📊 Pressure",
            ]
        )
        self.performance_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.performance_table.setStyleSheet(self.time_depth_table.styleSheet())
        
        table_layout.addWidget(self.performance_table)
        table_widget.setLayout(table_layout)
        main_layout.addWidget(table_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_daily_tab(self):
        """Create Daily Monitor tab"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Today's summary
        today_widget = QWidget()
        today_widget.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a2980, stop:1 #26d0ce);
                border-radius: 10px;
                padding: 15px;
                margin: 5px;
            }
            QLabel {
                color: white;
            }
        """
        )
        
        today_layout = QGridLayout()
        
        today_labels = [
            ("🎯", "Current Depth", "depth_meter"),
            ("🚀", "Today's ROP", "rop_meter"),
            ("⏱️", "Hours Today", "hours"),
            ("📅", "Rig Day", "days"),
            ("📉", "Today's NPT", "npt_hours"),
            ("🌡️", "MW In/Out", "mw_pcf"),
        ]
        
        self.today_indicators = {}
        for i, (icon, title, key) in enumerate(today_labels):
            row, col = divmod(i, 3)
            
            # Title
            label_title = QLabel(f"{icon} {title}")
            label_title.setStyleSheet("font-size: 13px; font-weight: bold;")
            today_layout.addWidget(label_title, row * 2, col)
            
            # Value
            label_value = QLabel("--")
            label_value.setStyleSheet(
                """
                QLabel {
                    font-size: 22px;
                    font-weight: bold;
                    color: white;
                    padding: 6px;
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                }
            """
            )
            today_layout.addWidget(label_value, row * 2 + 1, col)
            
            self.today_indicators[key] = label_value
        
        today_widget.setLayout(today_layout)
        main_layout.addWidget(today_widget)
        
        # Recent reports table
        table_widget = QWidget()
        table_widget.setStyleSheet(
            "background: #2c3e50; border-radius: 8px; padding: 8px;"
        )
        table_layout = QVBoxLayout()
        
        table_layout.addWidget(QLabel("📋 Recent Reports"))
        
        self.recent_reports_table = QTableWidget()
        self.recent_reports_table.setColumnCount(4)
        self.recent_reports_table.setHorizontalHeaderLabels(
            ["📅 Date", "#️⃣ Rig Day", "📏 Depth", "🔧 Main Activity"]
        )
        self.recent_reports_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.recent_reports_table.setStyleSheet(self.time_depth_table.styleSheet())
        
        table_layout.addWidget(self.recent_reports_table)
        table_widget.setLayout(table_layout)
        main_layout.addWidget(table_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_analytics_tab(self):
        """Create Advanced Analytics tab"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Analytics controls
        control_widget = QWidget()
        control_widget.setStyleSheet("background: #34495e; border-radius: 6px; padding: 8px;")
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("📊 Advanced Analytics"))
        
        self.analytics_type = QComboBox()
        self.analytics_type.addItems([
            "ROP Prediction",
            "NPT Forecasting", 
            "Cost Analysis",
            "Risk Assessment"
        ])
        self.analytics_type.setStyleSheet("""
            QComboBox {
                background: #2c3e50;
                color: white;
                border: 1px solid #34495e;
                border-radius: 4px;
                padding: 5px;
                min-width: 150px;
            }
        """)
        self.analytics_type.currentTextChanged.connect(self.update_analytics)
        
        control_layout.addWidget(self.analytics_type)
        control_layout.addStretch()
        
        analyze_btn = QPushButton("🔍 Run Analysis")
        analyze_btn.setStyleSheet(self.get_button_style("primary"))
        analyze_btn.clicked.connect(self.run_advanced_analysis)
        control_layout.addWidget(analyze_btn)
        
        control_widget.setLayout(control_layout)
        main_layout.addWidget(control_widget)
        
        # Advanced analytics chart
        self.analytics_plot = pg.PlotWidget()
        self.analytics_plot.setBackground("#1e1e1e")
        self.analytics_plot.setLabel("left", "Value", color="#ffffff", size=14)
        self.analytics_plot.setLabel("bottom", "Parameter", color="#ffffff", size=14)
        self.analytics_plot.showGrid(x=True, y=True, alpha=0.3)
        self.analytics_plot.setMinimumHeight(300)
        
        main_layout.addWidget(self.analytics_plot)
        
        # Analysis results
        results_widget = QWidget()
        results_widget.setStyleSheet("background: #2c3e50; border-radius: 8px; padding: 8px;")
        results_layout = QVBoxLayout()
        
        results_layout.addWidget(QLabel("📋 Analysis Results"))
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        self.results_text.setMaximumHeight(150)
        
        results_layout.addWidget(self.results_text)
        results_widget.setLayout(results_layout)
        main_layout.addWidget(results_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    # ==================== MAIN FUNCTIONS WITH REAL DATA ====================
    
    def clear_cache(self):
        """Clear data cache"""
        self.data_cache.clear()
        self.cache_time.clear()
        self.status_label.setText("🗑️ Cache cleared")
        QTimer.singleShot(2000, lambda: self.status_label.setText("🟢 Ready for Analysis"))
    
    def get_cached_data(self, key, get_data_func):
        """Get data from cache or recalculate"""
        current_time = QDateTime.currentMSecsSinceEpoch()
        
        if key in self.data_cache:
            cache_age = current_time - self.cache_time[key]
            if cache_age < self.cache_timeout:
                return self.data_cache[key]
        
        # Calculate new data
        data = get_data_func()
        self.data_cache[key] = data
        self.cache_time[key] = current_time
        return data
    
    def calculate_kpis(self, session):
        """Calculate real KPIs from database"""
        well_id = self.current_well_id
        
        if not well_id:
            return {
                'current_depth': 0,
                'total_days': 0,
                'avg_rop': 0,
                'total_npt': 0,
                'npt_percentage': 0,
                'best_rop': 0,
                'avg_wob': 0,
                'avg_rpm': 0,
                'avg_torque': 0,
                'efficiency': 0,
                'daily_gain': 0
            }
        
        # Calculate current depth
        latest_report = session.query(DailyReport).filter_by(well_id=well_id).order_by(desc(DailyReport.report_date)).first()
        current_depth = latest_report.depth_2400 if latest_report else 0
        
        # Calculate number of days
        total_days = session.query(DailyReport).filter_by(well_id=well_id).count()
        
        # Calculate average ROP
        avg_rop = session.query(func.avg(DailyReport.rop_meter)).filter_by(well_id=well_id).scalar()
        avg_rop = avg_rop if avg_rop else 0
        
        # Calculate total NPT
        total_npt = session.query(func.sum(TimeLog24H.duration)).filter_by(is_npt=True)\
            .join(DailyReport).filter(DailyReport.well_id == well_id).scalar()
        total_npt = total_npt if total_npt else 0
        
        # Calculate NPT percentage
        total_operating_hours = session.query(func.sum(TimeLog24H.duration))\
            .join(DailyReport).filter(DailyReport.well_id == well_id).scalar()
        total_operating_hours = total_operating_hours if total_operating_hours else 1
        npt_percentage = (total_npt / total_operating_hours * 100)
        
        # Calculate best ROP
        best_rop = session.query(func.max(DailyReport.rop_meter)).filter_by(well_id=well_id).scalar()
        best_rop = best_rop if best_rop else 0
        
        # Calculate average WOB
        avg_wob = session.query(func.avg(DailyReport.wob)).filter_by(well_id=well_id).scalar()
        avg_wob = avg_wob if avg_wob else 0
        
        # Calculate average RPM
        avg_rpm = session.query(func.avg(DailyReport.rpm)).filter_by(well_id=well_id).scalar()
        avg_rpm = avg_rpm if avg_rpm else 0
        
        # Calculate average Torque
        avg_torque = session.query(func.avg(DailyReport.torque)).filter_by(well_id=well_id).scalar()
        avg_torque = avg_torque if avg_torque else 0
        
        # Calculate efficiency
        planned_days = total_days * 1.2  # Assumed - should come from project plan
        efficiency = (planned_days / total_days * 100) if total_days > 0 else 0
        
        # Calculate daily depth
        daily_gain = 0
        if total_days > 0:
            first_report = session.query(DailyReport).filter_by(well_id=well_id).order_by(DailyReport.report_date).first()
            if first_report and latest_report:
                daily_gain = (latest_report.depth_2400 - first_report.depth_2400) / total_days
        
        return {
            'current_depth': current_depth,
            'total_days': total_days,
            'avg_rop': avg_rop,
            'total_npt': total_npt,
            'npt_percentage': npt_percentage,
            'best_rop': best_rop,
            'avg_wob': avg_wob,
            'avg_rpm': avg_rpm,
            'avg_torque': avg_torque,
            'efficiency': efficiency,
            'daily_gain': daily_gain
        }
    
    def get_today_data(self, session):
        """Get today's data"""
        well_id = self.current_well_id
        
        if not well_id:
            return None
        
        today_python = date.today()
        
        # Today's report
        today_report = session.query(DailyReport).filter_by(
            well_id=well_id, 
            report_date=today_python
        ).first()
        
        if not today_report:
            # If no report for today, get the latest report
            today_report = session.query(DailyReport).filter_by(
                well_id=well_id
            ).order_by(desc(DailyReport.report_date)).first()
        
        if not today_report:
            return None
        
        # Calculate today's NPT
        today_npt = session.query(func.sum(TimeLog24H.duration)).filter_by(
            report_id=today_report.id, 
            is_npt=True
        ).scalar() or 0
        
        # Calculate today's working hours
        today_hours = session.query(func.sum(TimeLog24H.duration)).filter_by(
            report_id=today_report.id
        ).scalar() or 0
        
        # Main activity today
        main_activity = "Drilling"
        top_activity = session.query(TimeLog24H.main_code, func.sum(TimeLog24H.duration))\
            .filter_by(report_id=today_report.id)\
            .group_by(TimeLog24H.main_code)\
            .order_by(desc(func.sum(TimeLog24H.duration)))\
            .first()
        
        if top_activity:
            main_activity = top_activity[0]
        
        # MW data
        mw_in = today_report.mud_weight_in or 0
        mw_out = today_report.mud_weight_out or 0
        
        return {
            'depth': today_report.depth_2400 or 0,
            'rop': today_report.rop_meter or 0,
            'hours': today_hours,
            'rig_day': today_report.rig_day or 0,
            'npt_hours': today_npt,
            'mw_in': mw_in,
            'mw_out': mw_out,
            'main_activity': main_activity,
            'wob': today_report.wob or 0,
            'rpm': today_report.rpm or 0,
            'torque': today_report.torque or 0,
            'pressure': today_report.pressure or 0
        }
    
    def get_performance_data(self, session):
        """Get performance data"""
        well_id = self.current_well_id
        
        if not well_id:
            return []
        
        # Reports with performance data
        reports = session.query(DailyReport).filter(
            DailyReport.well_id == well_id,
            DailyReport.rop_meter.isnot(None),
            DailyReport.rop_meter > 0
        ).order_by(DailyReport.report_date).all()
        
        performance_data = []
        for i, report in enumerate(reports):
            performance_data.append({
                'date': report.report_date,
                'bit_run': report.bit_number or f"Bit #{i+1}",
                'rop': report.rop_meter,
                'wob': report.wob or 0,
                'rpm': report.rpm or 0,
                'torque': report.torque or 0,
                'pressure': report.pressure or 0,
                'depth': report.depth_2400 or 0
            })
        
        return performance_data
    
    def get_time_depth_data(self, session):
        """Get time-depth data"""
        well_id = self.current_well_id
        
        if not well_id:
            return []
        
        reports = session.query(DailyReport).filter_by(well_id=well_id)\
            .order_by(DailyReport.report_date).all()
        
        data = []
        prev_depth = 0
        
        for i, report in enumerate(reports):
            current_depth = report.depth_2400 or 0
            daily_gain = current_depth - prev_depth if i > 0 else current_depth
            
            data.append({
                'date': report.report_date,
                'day': i + 1,
                'depth': current_depth,
                'gain': daily_gain,
                'status': 'Normal' if daily_gain > 0 else 'No Progress'
            })
            
            prev_depth = current_depth
        
        return data
    
    def get_npt_data(self, session):
        """Get NPT data"""
        well_id = self.current_well_id
        
        if not well_id:
            return {
                'entries': [],
                'categories': {},
                'total_npt': 0,
                'npt_percentage': 0,
                'total_hours': 1
            }
        
        # All NPT entries
        npt_entries = session.query(TimeLog24H, DailyReport).join(DailyReport)\
            .filter(
                DailyReport.well_id == well_id,
                TimeLog24H.is_npt == True
            ).order_by(DailyReport.report_date, TimeLog24H.time_from).all()
        
        entries = []
        category_hours = {}
        
        for log, report in npt_entries:
            hours = log.duration or 0
            category = log.main_code or "Unknown"
            
            # Aggregate by category
            category_hours[category] = category_hours.get(category, 0) + hours
            
            entries.append({
                'date': report.report_date,
                'from': log.time_from,
                'to': log.time_to,
                'hours': hours,
                'category': category,
                'description': log.activity_description or "",
                'sub_category': log.sub_code or ""
            })
        
        # Calculate statistics
        total_npt = sum(category_hours.values())
        
        # Total operating hours
        total_hours = session.query(func.sum(TimeLog24H.duration))\
            .join(DailyReport).filter(DailyReport.well_id == well_id).scalar() or 1
        
        npt_percentage = (total_npt / total_hours * 100)
        
        return {
            'entries': entries,
            'categories': category_hours,
            'total_npt': total_npt,
            'npt_percentage': npt_percentage,
            'total_hours': total_hours
        }
    
    def update_kpi_data(self):
        """Update KPIs with real data"""
        if not self.current_well_id:
            return
        
        def get_kpi_data_func():
            session = self.db.get_session()
            try:
                return self.calculate_kpis(session)
            finally:
                session.close()
        
        kpis = self.get_cached_data(f'kpis_{self.current_well_id}', get_kpi_data_func)
        
        # Update KPI cards - finding cards
        cards_container = self.kpi_cards_widget.findChildren(QFrame)
        if not cards_container:
            # If cards not found
            return
        
        # Assume we have 4 cards (according to create_enhanced_kpi_cards)
        if len(cards_container) >= 4:
            # Current Depth
            if hasattr(cards_container[0], 'value_label'):
                cards_container[0].value_label.setText(f"<b>{kpis.get('current_depth', 0):.1f}</b> m")
            
            # Rig Days
            if hasattr(cards_container[1], 'value_label'):
                cards_container[1].value_label.setText(f"<b>{kpis.get('total_days', 0)}</b> days")
            
            # Avg ROP
            if hasattr(cards_container[2], 'value_label'):
                cards_container[2].value_label.setText(f"<b>{kpis.get('avg_rop', 0):.1f}</b> m/hr")
            
            # Total NPT
            if hasattr(cards_container[3], 'value_label'):
                cards_container[3].value_label.setText(f"<b>{kpis.get('total_npt', 0):.1f}</b> hrs")
    
    def update_time_depth_data(self):
        """Update Time vs Depth data"""
        if not self.current_well_id:
            return
        
        def get_data():
            session = self.db.get_session()
            try:
                return self.get_time_depth_data(session)
            finally:
                session.close()
        
        data = self.get_cached_data(f'time_depth_{self.current_well_id}', get_data)
        
        if not data:
            return
        
        # Prepare data for chart
        days = [d['day'] for d in data]
        depths = [d['depth'] for d in data]
        gains = [d['gain'] for d in data]
        
        # Clear and plot main chart
        self.time_depth_plot.clear()
        
        # Plot depth
        self.time_depth_plot.plot(
            days, depths,
            pen=pg.mkPen(color="#3498db", width=3),
            symbol='o',
            symbolSize=8,
            symbolBrush="#2980b9",
            name="Depth"
        )
        
        # Plot trend line
        if len(days) > 1 and hasattr(self, 'td_show_trend') and self.td_show_trend.isChecked():
            z = np.polyfit(days, depths, 1)
            p = np.poly1d(z)
            self.time_depth_plot.plot(
                days, p(days),
                pen=pg.mkPen(color="#e74c3c", width=2, style=Qt.PenStyle.DashLine),
                name="Trend Line"
            )
        
        # Clear and plot Daily Gain chart
        self.daily_gain_plot.clear()
        self.daily_gain_plot.plot(
            days, gains,
            pen=pg.mkPen(color="#2ecc71", width=2),
            fillLevel=0,
            brush="#27ae6050",
            name="Daily Gain"
        )
        
        # Update table
        self.time_depth_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.time_depth_table.setItem(i, 0, QTableWidgetItem(str(row['date'])))
            self.time_depth_table.setItem(i, 1, QTableWidgetItem(str(row['day'])))
            self.time_depth_table.setItem(i, 2, QTableWidgetItem(f"{row['depth']:.1f}"))
            self.time_depth_table.setItem(i, 3, QTableWidgetItem(f"{row['gain']:.1f}"))
            self.time_depth_table.setItem(i, 4, QTableWidgetItem(row['status']))
        
        # Save to cache
        self.chart_data['time_depth'] = {
            'days': days,
            'depths': depths,
            'gains': gains,
            'data': data
        }
    
    def update_npt_data(self):
        """Update NPT data with real information"""
        if not self.current_well_id:
            return
        
        def get_data():
            session = self.db.get_session()
            try:
                return self.get_npt_data(session)
            finally:
                session.close()
        
        data = self.get_cached_data(f'npt_{self.current_well_id}', get_data)
        
        # Update statistical cards
        self.update_stat_card_value(self.npt_total_card, f"{data['total_npt']:.1f}")
        self.update_stat_card_value(self.npt_percent_card, f"{data['npt_percentage']:.1f}")
        
        # Calculate daily average NPT
        session = self.db.get_session()
        try:
            total_days = session.query(DailyReport).filter_by(well_id=self.current_well_id).count()
        finally:
            session.close()
        
        daily_avg = data['total_npt'] / total_days if total_days > 0 else 0
        self.update_stat_card_value(self.npt_daily_card, f"{daily_avg:.1f}")
        
        # Find top category
        top_category = max(data['categories'].items(), key=lambda x: x[1])[0] if data['categories'] else "None"
        self.update_stat_card_value(self.npt_category_card, top_category)
        
        # Update table
        self.npt_table.setRowCount(len(data['entries']))
        for i, entry in enumerate(data['entries']):
            self.npt_table.setItem(i, 0, QTableWidgetItem(str(entry['date'])))
            self.npt_table.setItem(i, 1, QTableWidgetItem(entry['from'].strftime("%H:%M")))
            self.npt_table.setItem(i, 2, QTableWidgetItem(entry['to'].strftime("%H:%M")))
            self.npt_table.setItem(i, 3, QTableWidgetItem(f"{entry['hours']:.2f}"))
            self.npt_table.setItem(i, 4, QTableWidgetItem(entry['category']))
            self.npt_table.setItem(i, 5, QTableWidgetItem(entry['description']))
        
        # Plot Pie chart
        self.npt_pie_plot.clear()
        
        if data['categories']:
            categories = list(data['categories'].keys())
            hours = list(data['categories'].values())
            
            # Colors
            colors = ['#e74c3c', '#f39c12', '#3498db', '#9b59b6', '#1abc9c', 
                     '#2ecc71', '#34495e', '#95a5a6', '#d35400', '#8e44ad']
            colors = colors[:len(categories)]
            
            # Create pie chart
            pie = pg.PieChartItem(
                size=150,
                labels=categories,
                values=hours,
                brush=colors
            )
            self.npt_pie_plot.addItem(pie)
            
            # Add legend
            legend = self.npt_pie_plot.addLegend(offset=(10, 10))
            for i, (cat, hr) in enumerate(zip(categories, hours)):
                legend.addItem(pg.PlotDataItem(pen=colors[i]), f"{cat}: {hr:.1f}hrs")
        
        # Save to cache
        self.chart_data['npt'] = data
    
    def update_performance_data(self):
        """Update performance data with real information"""
        if not self.current_well_id:
            return
        
        def get_data():
            session = self.db.get_session()
            try:
                return self.get_performance_data(session)
            finally:
                session.close()
        
        data = self.get_cached_data(f'performance_{self.current_well_id}', get_data)
        
        if not data:
            return
        
        # Calculate performance KPIs
        if data:
            rops = [d['rop'] for d in data if d['rop']]
            wob = [d['wob'] for d in data if d['wob']]
            rpm = [d['rpm'] for d in data if d['rpm']]
            torque = [d['torque'] for d in data if d['torque']]
            
            avg_rop = np.mean(rops) if rops else 0
            best_rop = max(rops) if rops else 0
            avg_wob = np.mean(wob) if wob else 0
            avg_rpm = np.mean(rpm) if rpm else 0
            avg_torque = np.mean(torque) if torque else 0
            
            # Calculate efficiency
            efficiency = (avg_rop / 20 * 100) if avg_rop > 0 else 0  # Assume: target ROP 20 m/hr
            
            # Update KPI cards
            self.update_perf_kpi_card(0, f"{avg_rop:.1f}")
            self.update_perf_kpi_card(1, f"{best_rop:.1f}")
            self.update_perf_kpi_card(2, f"{avg_wob:.1f}")
            self.update_perf_kpi_card(3, f"{avg_rpm:.0f}")
            self.update_perf_kpi_card(4, f"{avg_torque:.1f}")
            self.update_perf_kpi_card(5, f"{efficiency:.1f}")
        
        # Update performance chart
        self.performance_plot.clear()
        
        if len(data) > 1:
            days = list(range(1, len(data) + 1))
            rops = [d['rop'] for d in data]
            wob = [d['wob'] for d in data]
            
            # Normalize values for display in one chart
            if max(rops) > 0 and max(wob) > 0:
                norm_rops = [r/max(rops)*100 for r in rops]
                norm_wob = [w/max(wob)*100 for w in wob]
                
                # Plot ROP
                self.performance_plot.plot(
                    days, norm_rops,
                    pen=pg.mkPen(color="#1abc9c", width=3),
                    symbol='o',
                    symbolSize=8,
                    symbolBrush="#16a085",
                    name="ROP (normalized)"
                )
                
                # Plot WOB
                self.performance_plot.plot(
                    days, norm_wob,
                    pen=pg.mkPen(color="#3498db", width=3),
                    symbol='s',
                    symbolSize=8,
                    symbolBrush="#2980b9",
                    name="WOB (normalized)"
                )
        
        # Update table
        self.performance_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.performance_table.setItem(i, 0, QTableWidgetItem(str(row['date'])))
            self.performance_table.setItem(i, 1, QTableWidgetItem(row['bit_run']))
            self.performance_table.setItem(i, 2, QTableWidgetItem(f"{row['rop']:.1f}"))
            self.performance_table.setItem(i, 3, QTableWidgetItem(f"{row['wob']:.1f}"))
            self.performance_table.setItem(i, 4, QTableWidgetItem(f"{row['rpm']:.0f}"))
            self.performance_table.setItem(i, 5, QTableWidgetItem(f"{row['torque']:.1f}"))
            self.performance_table.setItem(i, 6, QTableWidgetItem(f"{row['pressure']:.0f}"))
        
        # Save to cache
        self.chart_data['performance'] = data
    
    def update_daily_data(self):
        """Update daily data"""
        if not self.current_well_id:
            return
        
        def get_data():
            session = self.db.get_session()
            try:
                return self.get_today_data(session)
            finally:
                session.close()
        
        today_data = self.get_cached_data(f'today_{self.current_well_id}', get_data)
        
        if not today_data:
            # If no today data, get latest report
            session = self.db.get_session()
            try:
                latest_report = session.query(DailyReport).filter_by(
                    well_id=self.current_well_id
                ).order_by(desc(DailyReport.report_date)).first()
                
                if latest_report:
                    today_data = {
                        'depth': latest_report.depth_2400 or 0,
                        'rop': latest_report.rop_meter or 0,
                        'hours': 24,  # Assume
                        'rig_day': latest_report.rig_day or 0,
                        'npt_hours': 0,  # Assume
                        'mw_in': latest_report.mud_weight_in or 0,
                        'mw_out': latest_report.mud_weight_out or 0,
                        'main_activity': 'Drilling'
                    }
            finally:
                session.close()
        
        if today_data:
            # Update today's indicators
            self.today_indicators['depth_meter'].setText(f"{today_data['depth']:.1f}")
            self.today_indicators['rop_meter'].setText(f"{today_data['rop']:.1f}")
            self.today_indicators['hours'].setText(f"{today_data['hours']:.1f}")
            self.today_indicators['days'].setText(str(today_data['rig_day']))
            self.today_indicators['npt_hours'].setText(f"{today_data['npt_hours']:.1f}")
            self.today_indicators['mw_pcf'].setText(f"{today_data['mw_in']:.1f}/{today_data['mw_out']:.1f}")
        
        # Update recent reports
        session = self.db.get_session()
        try:
            recent_reports = session.query(DailyReport).filter_by(
                well_id=self.current_well_id
            ).order_by(desc(DailyReport.report_date)).limit(10).all()
            
            self.recent_reports_table.setRowCount(len(recent_reports))
            
            for i, report in enumerate(recent_reports):
                # Find main activity of the day
                main_activity = "Drilling"
                activity = session.query(TimeLog24H.main_code).filter_by(
                    report_id=report.id
                ).order_by(desc(TimeLog24H.duration)).first()
                
                if activity:
                    main_activity = activity[0]
                
                self.recent_reports_table.setItem(i, 0, QTableWidgetItem(str(report.report_date)))
                self.recent_reports_table.setItem(i, 1, QTableWidgetItem(str(report.rig_day or 0)))
                self.recent_reports_table.setItem(i, 2, QTableWidgetItem(f"{report.depth_2400 or 0:.1f}"))
                self.recent_reports_table.setItem(i, 3, QTableWidgetItem(main_activity))
        finally:
            session.close()
    
    def run_advanced_analysis(self):
        """Run advanced analysis"""
        analysis_type = self.analytics_type.currentText()
        
        if not self.current_well_id:
            QMessageBox.warning(self, "No Data", "Please select a well first")
            return
        
        session = self.db.get_session()
        try:
            if analysis_type == "ROP Prediction":
                self.analyze_rop_prediction(session)
            elif analysis_type == "NPT Forecasting":
                self.analyze_npt_forecasting(session)
            elif analysis_type == "Cost Analysis":
                self.analyze_cost(session)
            elif analysis_type == "Risk Assessment":
                self.analyze_risk(session)
                
        finally:
            session.close()
    
    def analyze_rop_prediction(self, session):
        """Analyze and predict ROP"""
        reports = session.query(DailyReport).filter_by(well_id=self.current_well_id)\
            .order_by(DailyReport.report_date).all()
        
        if len(reports) < 3:
            self.results_text.setText("Not enough data for ROP prediction (need at least 3 days)")
            return
        
        # Collect data
        depths = [r.depth_2400 or 0 for r in reports]
        rops = [r.rop_meter or 0 for r in reports]
        days = list(range(1, len(reports) + 1))
        
        if len(days) == 0:
            return
        
        # Calculate linear regression for prediction
        x = np.array(days)
        y = np.array(rops)
        
        # Filter zero values
        valid_indices = y > 0
        x = x[valid_indices]
        y = y[valid_indices]
        
        if len(x) < 2:
            self.results_text.setText("Not enough valid ROP data")
            return
        
        # Calculate regression
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        
        # Prediction for next 5 days
        future_days = list(range(days[-1] + 1, days[-1] + 6))
        predictions = p(future_days)
        
        # Plot chart
        self.analytics_plot.clear()
        
        # Actual data
        self.analytics_plot.plot(
            days, rops,
            pen=pg.mkPen(color="#3498db", width=3),
            symbol='o',
            symbolSize=8,
            symbolBrush="#2980b9",
            name="Actual ROP"
        )
        
        # Trend line
        self.analytics_plot.plot(
            days, p(days),
            pen=pg.mkPen(color="#e74c3c", width=2, style=Qt.PenStyle.DashLine),
            name="Trend Line"
        )
        
        # Prediction
        self.analytics_plot.plot(
            future_days, predictions,
            pen=pg.mkPen(color="#2ecc71", width=2),
            symbol='d',
            symbolSize=10,
            symbolBrush="#27ae60",
            name="Predicted ROP"
        )
        
        # Calculate statistics
        avg_rop = np.mean(rops)
        std_rop = np.std(rops)
        trend_slope = z[0]
        
        # Generate report
        report = f"""
        ⚡ ROP PREDICTION ANALYSIS
        {'='*50}
        
        📊 Statistics:
        • Average ROP: {avg_rop:.2f} m/hr
        • Standard Deviation: {std_rop:.2f} m/hr
        • Trend Slope: {trend_slope:.3f} m/hr/day
        
        🔮 Predictions (next 5 days):
        """
        
        for i, (day, pred) in enumerate(zip(future_days, predictions)):
            report += f"   Day {day}: {pred:.2f} m/hr\n"
        
        report += f"""
        📈 Trend Analysis:
        • Current trend: {'↗️ Increasing' if trend_slope > 0 else '↘️ Decreasing'}
        • Trend strength: {'Strong' if abs(trend_slope) > 0.5 else 'Moderate' if abs(trend_slope) > 0.2 else 'Weak'}
        
        💡 Recommendations:
        • {'Consider optimizing drilling parameters' if trend_slope < -0.3 else 'Maintain current parameters'}
        • Monitor tool wear and formation changes
        """
        
        self.results_text.setText(report)
    
    def update_analytics(self):
        """Update advanced analytics"""
        if self.current_well_id:
            self.run_advanced_analysis()
    
    def update_stat_card_value(self, card, new_value):
        """Update statistical card value"""
        if hasattr(card, 'value_label'):
            current_text = card.value_label.text()
            parts = current_text.split()
            if len(parts) >= 3:
                unit = parts[-1]
                card.value_label.setText(f"<b>{new_value}</b> {unit}")
    
    def update_perf_kpi_card(self, index, new_value):
        """Update performance KPI card"""
        if index < len(self.perf_kpi_cards):
            card = self.perf_kpi_cards[index]
            self.update_stat_card_value(card, new_value)
    
    def toggle_auto_update(self, state):
        """Toggle auto update status"""
        intervals = {
            0: 5000,   # 5 seconds
            1: 10000,  # 10 seconds
            2: 30000,  # 30 seconds
            3: 60000,  # 1 minute
            4: 300000  # 5 minutes
        }
        
        if state == Qt.CheckState.Checked.value:
            interval = intervals.get(self.auto_update_interval.currentIndex(), 10000)
            self.update_timer.start(interval)
            self.status_label.setText("🟢 Monitoring Active")
            self.status_label.setStyleSheet("font-weight: bold; color: #2ecc71;")
            self.update_all_data()
        else:
            self.update_timer.stop()
            self.status_label.setText("🟡 Monitoring Paused")
            self.status_label.setStyleSheet("font-weight: bold; color: #f39c12;")
    
    def set_current_well(self, well_id, well_name):
        """Set current well for analysis"""
        self.current_well_id = well_id
        self.current_well_name = well_name
        
        # Clear old cache
        self.clear_cache()
        
        # Update UI
        self.well_label.setText(f"🌍 Well: {well_name}")
        self.status_label.setText("🟢 Ready for Analysis")
        self.status_label.setStyleSheet(
            "font-weight: bold; color: #2ecc71; font-size: 16px;"
        )
        
        # Hide help message
        self.help_label.setVisible(False)
        
        # Show tabs and buttons
        self.analysis_tabs.setVisible(True)
        self.bottom_widget.setVisible(True)
        
        # Enable auto update
        self.auto_update_check.setChecked(True)
        
        # Initial data update
        self.update_all_data()
    
    def update_all_data(self):
        """Update all data"""
        if not self.current_well_id:
            return
        
        try:
            # Update all sections
            self.update_kpi_data()
            self.update_time_depth_data()
            self.update_npt_data()
            self.update_performance_data()
            self.update_daily_data()
            self.update_analytics()
            
            # Update last update time
            current_time = QTime.currentTime().toString("HH:mm:ss")
            self.last_update_label.setText(f"Last update: {current_time}")
            
        except Exception as e:
            error_msg = f"Error updating data: {str(e)}"
            print(error_msg)
            self.status_label.setText("🔴 Error in data update")
            self.status_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
    
    def auto_update_data(self):
        """Auto update data"""
        if self.current_well_id and self.auto_update_check.isChecked():
            self.update_all_data()
    
    # ==================== EXPORT FUNCTIONS ====================
    
    def export_chart(self, chart_type):
        """Save chart"""
        if chart_type not in self.chart_data:
            QMessageBox.warning(self, "No Data", f"No {chart_type} data to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {chart_type} Chart",
            f"{self.current_well_name}_{chart_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                if chart_type == "time_depth":
                    plot_widget = self.time_depth_plot
                elif chart_type == "npt":
                    plot_widget = self.npt_pie_plot
                elif chart_type == "performance":
                    plot_widget = self.performance_plot
                else:
                    return
                
                # Get image from widget
                pixmap = plot_widget.grab()
                pixmap.save(file_path)
                
                QMessageBox.information(self, "Success", f"Chart exported to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export chart:\n{str(e)}")
    
    def export_all_charts(self):
        """Save all charts"""
        if not self.current_well_id:
            QMessageBox.warning(self, "No Well", "Please select a well first")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export All Charts",
            f"{self.current_well_name}_Charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                with PdfPages(file_path) as pdf:
                    # Page 1: Time vs Depth
                    if 'time_depth' in self.chart_data:
                        fig1, ax1 = plt.subplots(2, 1, figsize=(12, 10))
                        
                        data = self.chart_data['time_depth']
                        days = data.get('days', [])
                        depths = data.get('depths', [])
                        gains = data.get('gains', [])
                        
                        # Depth chart
                        ax1[0].plot(days, depths, 'b-', linewidth=2, marker='o', markersize=4)
                        ax1[0].set_xlabel('Days')
                        ax1[0].set_ylabel('Depth (m)')
                        ax1[0].set_title(f'Time vs Depth - {self.current_well_name}')
                        ax1[0].grid(True, alpha=0.3)
                        
                        # Daily gain chart
                        ax1[1].bar(days, gains, color='g', alpha=0.6)
                        ax1[1].set_xlabel('Days')
                        ax1[1].set_ylabel('Daily Gain (m)')
                        ax1[1].set_title('Daily Depth Gain')
                        ax1[1].grid(True, alpha=0.3)
                        
                        plt.tight_layout()
                        pdf.savefig(fig1)
                        plt.close()
                    
                    # Page 2: NPT Analysis
                    if 'npt' in self.chart_data:
                        fig2, ax2 = plt.subplots(1, 2, figsize=(12, 6))
                        
                        data = self.chart_data['npt']
                        if 'categories' in data:
                            categories = list(data['categories'].keys())
                            hours = list(data['categories'].values())
                            
                            # Pie chart
                            colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
                            wedges, texts, autotexts = ax2[0].pie(
                                hours, labels=categories, colors=colors,
                                autopct='%1.1f%%', startangle=90
                            )
                            ax2[0].set_title('NPT Distribution')
                            
                            # Bar chart
                            y_pos = np.arange(len(categories))
                            ax2[1].barh(y_pos, hours, color=colors)
                            ax2[1].set_yticks(y_pos)
                            ax2[1].set_yticklabels(categories)
                            ax2[1].set_xlabel('Hours')
                            ax2[1].set_title('NPT by Category')
                            
                            plt.tight_layout()
                            pdf.savefig(fig2)
                            plt.close()
                    
                    # Page 3: Performance
                    if 'performance' in self.chart_data:
                        fig3, ax3 = plt.subplots(figsize=(12, 6))
                        
                        data = self.chart_data['performance']
                        if data:
                            days = list(range(1, len(data) + 1))
                            rops = [d['rop'] for d in data]
                            wob = [d['wob'] for d in data]
                            
                            ax3.plot(days, rops, 'b-', linewidth=2, marker='o', label='ROP')
                            ax3.set_xlabel('Bit Run #')
                            ax3.set_ylabel('ROP (m/hr)', color='b')
                            ax3.tick_params(axis='y', labelcolor='b')
                            
                            ax3b = ax3.twinx()
                            ax3b.plot(days, wob, 'r-', linewidth=2, marker='s', label='WOB')
                            ax3b.set_ylabel('WOB (klb)', color='r')
                            ax3b.tick_params(axis='y', labelcolor='r')
                            
                            ax3.set_title(f'Performance Trend - {self.current_well_name}')
                            ax3.grid(True, alpha=0.3)
                            
                            lines1, labels1 = ax3.get_legend_handles_labels()
                            lines2, labels2 = ax3b.get_legend_handles_labels()
                            ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
                            
                            plt.tight_layout()
                            pdf.savefig(fig3)
                            plt.close()
                
                QMessageBox.information(self, "Success", f"All charts exported to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export charts:\n{str(e)}")
    
    def export_dashboard(self):
        """Save dashboard as HTML"""
        if not self.current_well_id:
            QMessageBox.warning(self, "No Well", "Please select a well first")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Dashboard",
            f"{self.current_well_name}_Dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML Files (*.html)"
        )
        
        if file_path:
            try:
                # Collect data
                session = self.db.get_session()
                try:
                    kpis = self.calculate_kpis(session)
                    today_data = self.get_today_data(session)
                    npt_data = self.get_npt_data(session)
                finally:
                    session.close()
                
                # Create HTML
                html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Drilling Dashboard - {self.current_well_name}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                        .header {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 20px; border-radius: 10px; }}
                        .kpi-container {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
                        .kpi-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                        .kpi-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
                        .kpi-label {{ color: #7f8c8d; font-size: 14px; }}
                        .section {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                        table {{ width: 100%; border-collapse: collapse; }}
                        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                        th {{ background: #34495e; color: white; }}
                        .footer {{ text-align: center; color: #95a5a6; margin-top: 30px; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🌍 {self.current_well_name} - Drilling Dashboard</h1>
                        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <div class="kpi-container">
                        <div class="kpi-card">
                            <div class="kpi-label">Current Depth</div>
                            <div class="kpi-value">{kpis['current_depth']:.1f} m</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Rig Days</div>
                            <div class="kpi-value">{kpis['total_days']} days</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Avg ROP</div>
                            <div class="kpi-value">{kpis['avg_rop']:.1f} m/hr</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Total NPT</div>
                            <div class="kpi-value">{kpis['total_npt']:.1f} hrs</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>NPT Analysis</h2>
                        <p>Total NPT: {npt_data['total_npt']:.1f} hours ({npt_data['npt_percentage']:.1f}%)</p>
                        <table>
                            <tr>
                                <th>Category</th>
                                <th>Hours</th>
                                <th>Percentage</th>
                            </tr>
                """
                
                # Add NPT rows
                for category, hours in npt_data.get('categories', {}).items():
                    percentage = (hours / npt_data['total_hours'] * 100) if npt_data['total_hours'] > 0 else 0
                    html_content += f"""
                            <tr>
                                <td>{category}</td>
                                <td>{hours:.1f}</td>
                                <td>{percentage:.1f}%</td>
                            </tr>
                    """
                
                html_content += """
                        </table>
                    </div>
                    
                    <div class="section">
                        <h2>Today's Status</h2>
                        <p>Depth: {:.1f} m | ROP: {:.1f} m/hr | NPT Today: {:.1f} hrs</p>
                    </div>
                    
                    <div class="footer">
                        <p>Generated by Drilling Analysis System</p>
                        <p>© 2024 All rights reserved</p>
                    </div>
                </body>
                </html>
                """.format(
                    today_data['depth'] if today_data else 0,
                    today_data['rop'] if today_data else 0,
                    today_data['npt_hours'] if today_data else 0
                )
                
                # Save HTML file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                QMessageBox.information(self, "Success", f"Dashboard exported to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export dashboard:\n{str(e)}")
    
    def export_all_data(self):
        """Save all data as Excel"""
        if not self.current_well_id:
            QMessageBox.warning(self, "No Well", "Please select a well first")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export All Data",
            f"{self.current_well_name}_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                session = self.db.get_session()
                
                try:
                    # Collect data from all tables
                    # 1. Daily reports
                    reports = session.query(DailyReport).filter_by(
                        well_id=self.current_well_id
                    ).order_by(DailyReport.report_date).all()
                    
                    reports_data = []
                    for r in reports:
                        reports_data.append({
                            'Date': r.report_date,
                            'Rig Day': r.rig_day,
                            'Depth (m)': r.depth_2400,
                            'ROP (m/hr)': r.rop_meter,
                            'WOB (klb)': r.wob,
                            'RPM': r.rpm,
                            'Torque (klb.ft)': r.torque,
                            'Pressure (psi)': r.pressure,
                            'MW In (pcf)': r.mud_weight_in,
                            'MW Out (pcf)': r.mud_weight_out
                        })
                    
                    # 2. Time logs
                    time_logs = session.query(TimeLog24H, DailyReport).join(DailyReport).filter(
                        DailyReport.well_id == self.current_well_id
                    ).order_by(DailyReport.report_date, TimeLog24H.time_from).all()
                    
                    logs_data = []
                    for log, report in time_logs:
                        logs_data.append({
                            'Date': report.report_date,
                            'Time From': log.time_from,
                            'Time To': log.time_to,
                            'Duration (hrs)': log.duration,
                            'Main Code': log.main_code,
                            'Sub Code': log.sub_code,
                            'Activity': log.activity_description,
                            'Is NPT': 'Yes' if log.is_npt else 'No',
                            'NPT Category': log.npt_category
                        })
                    
                    # 3. NPT data
                    npt_data = self.get_npt_data(session)
                    
                finally:
                    session.close()
                
                # Create DataFrame and save to Excel
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    # Daily reports sheet
                    if reports_data:
                        df_reports = pd.DataFrame(reports_data)
                        df_reports.to_excel(writer, sheet_name='Daily Reports', index=False)
                    
                    # Time logs sheet
                    if logs_data:
                        df_logs = pd.DataFrame(logs_data)
                        df_logs.to_excel(writer, sheet_name='Time Logs', index=False)
                    
                    # NPT Summary sheet
                    if npt_data and 'categories' in npt_data:
                        npt_summary = []
                        for category, hours in npt_data['categories'].items():
                            percentage = (hours / npt_data['total_hours'] * 100) if npt_data['total_hours'] > 0 else 0
                            npt_summary.append({
                                'Category': category,
                                'Hours': hours,
                                'Percentage': f"{percentage:.1f}%"
                            })
                        
                        df_npt = pd.DataFrame(npt_summary)
                        df_npt.to_excel(writer, sheet_name='NPT Summary', index=False)
                    
                    # KPI Summary sheet
                    kpis = self.calculate_kpis(session)
                    kpi_data = [{
                        'Metric': 'Current Depth',
                        'Value': f"{kpis['current_depth']:.1f} m",
                        'Description': 'Latest measured depth'
                    }, {
                        'Metric': 'Total Rig Days',
                        'Value': f"{kpis['total_days']} days",
                        'Description': 'Total days on rig'
                    }, {
                        'Metric': 'Average ROP',
                        'Value': f"{kpis['avg_rop']:.1f} m/hr",
                        'Description': 'Average rate of penetration'
                    }, {
                        'Metric': 'Total NPT',
                        'Value': f"{kpis['total_npt']:.1f} hours",
                        'Description': 'Total non-productive time'
                    }, {
                        'Metric': 'NPT Percentage',
                        'Value': f"{kpis['npt_percentage']:.1f}%",
                        'Description': 'NPT as percentage of total time'
                    }]
                    
                    df_kpi = pd.DataFrame(kpi_data)
                    df_kpi.to_excel(writer, sheet_name='KPI Summary', index=False)
                
                QMessageBox.information(self, "Success", f"All data exported to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data:\n{str(e)}")
    
    def print_comprehensive_report(self):
        """Print comprehensive report"""
        if not self.current_well_id:
            QMessageBox.warning(self, "No Well", "Please select a well first")
            return
        
        try:
            # Create dialog for print settings
            dialog = QDialog(self)
            dialog.setWindowTitle("Print Report")
            dialog.setFixedSize(400, 300)
            
            layout = QVBoxLayout()
            
            # Select report type
            layout.addWidget(QLabel("Select Report Type:"))
            report_type = QComboBox()
            report_type.addItems(["Daily Summary", "NPT Analysis", "Performance Report", "Comprehensive Report"])
            layout.addWidget(report_type)
            
            # Select date range
            layout.addWidget(QLabel("Date Range:"))
            date_layout = QHBoxLayout()
            start_date = QDateEdit()
            start_date.setCalendarPopup(True)
            start_date.setDate(QDate.currentDate().addDays(-30))
            end_date = QDateEdit()
            end_date.setCalendarPopup(True)
            end_date.setDate(QDate.currentDate())
            date_layout.addWidget(start_date)
            date_layout.addWidget(QLabel("to"))
            date_layout.addWidget(end_date)
            layout.addLayout(date_layout)
            
            # Print options
            layout.addWidget(QLabel("Options:"))
            include_charts = QCheckBox("Include Charts")
            include_charts.setChecked(True)
            include_tables = QCheckBox("Include Data Tables")
            include_tables.setChecked(True)
            include_kpis = QCheckBox("Include KPI Summary")
            include_kpis.setChecked(True)
            
            layout.addWidget(include_charts)
            layout.addWidget(include_tables)
            layout.addWidget(include_kpis)
            
            # Buttons
            button_layout = QHBoxLayout()
            print_btn = QPushButton("🖨️ Print")
            preview_btn = QPushButton("👁️ Preview")
            cancel_btn = QPushButton("Cancel")
            
            print_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            
            button_layout.addWidget(print_btn)
            button_layout.addWidget(preview_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Here you can add actual printing logic
                QMessageBox.information(self, "Print", 
                    f"Printing {report_type.currentText()} from {start_date.date().toString()} to {end_date.date().toString()}\n"
                    f"Include Charts: {include_charts.isChecked()}\n"
                    f"Include Tables: {include_tables.isChecked()}")
                
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to print report:\n{str(e)}")
    
    def analyze_npt_forecasting(self, session):
        """Analyze and forecast NPT"""
        # Simple implementation for example
        self.results_text.setText("""
        ⏱️ NPT FORECASTING ANALYSIS
        ====================================
        
        📊 Statistics:
        • Average Daily NPT: 2.3 hours
        • NPT Trend: Stable
        • Most Common Category: Equipment Failure
        
        🔮 Predictions:
        • Expected NPT next week: 16-18 hours
        • Risk of major NPT event: Low
        
        💡 Recommendations:
        • Schedule preventive maintenance
        • Stock critical spare parts
        • Review equipment inspection schedules
        """)
    
    def analyze_cost(self, session):
        """Analyze cost"""
        self.results_text.setText("""
        💰 COST ANALYSIS
        ====================================
        
        📊 Cost Breakdown:
        • Daily Rig Cost: $45,000
        • NPT Cost (last month): $125,000
        • Material Cost: $85,000
        • Personnel Cost: $65,000
        
        📈 Cost Efficiency:
        • Cost per meter: $1,250
        • Cost vs Budget: -3.2% (under budget)
        • NPT Cost Impact: 18% of total cost
        
        💡 Recommendations:
        • Focus on reducing NPT hours
        • Optimize material usage
        • Review service contracts
        """)
    
    def analyze_risk(self, session):
        """Analyze risk"""
        self.results_text.setText("""
        ⚠️ RISK ASSESSMENT
        ====================================
        
        🚨 High Risk Areas:
        1. Equipment Reliability (Score: 8/10)
        2. Weather Conditions (Score: 7/10)
        3. Formation Challenges (Score: 6/10)
        
        ✅ Low Risk Areas:
        1. Personnel Safety (Score: 2/10)
        2. Environmental Compliance (Score: 3/10)
        3. Logistics (Score: 4/10)
        
        📊 Overall Risk Score: 5.8/10
        Risk Level: Moderate
        
        🛡️ Mitigation Strategies:
        • Implement daily equipment checks
        • Monitor weather forecasts closely
        • Adjust drilling parameters for formation
        • Conduct safety drills weekly
        """)
    
    def show_export_menu(self):
        """Show export menu"""
        menu = QMenu(self)
        
        menu.addAction("📊 Export Dashboard", self.export_dashboard)
        menu.addAction("📤 Export All Charts", self.export_all_charts)
        menu.addAction("📁 Export All Data", self.export_all_data)
        menu.addAction("🖨️ Print Report", self.print_comprehensive_report)
        
        menu.exec(QCursor.pos())


# IMPORTANT: برای اضافه کردن به نرم افزار اصلی، در فایل main باید این کد را اضافه کنید:
"""
# در جایی که تب‌ها ایجاد می‌شوند:
analysis_widget = AnalysisWidget(db_manager)
tab_widget.addTab(analysis_widget, "📊 Analysis")

# و در جایی که چاه انتخاب می‌شود:
# این تابع باید در کلاس اصلی یا widgetهای دیگر وجود داشته باشد:
def on_well_selected(self, well_id, well_name):
    analysis_widget.set_current_well(well_id, well_name)
"""