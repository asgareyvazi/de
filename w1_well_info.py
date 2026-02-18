"""
Well Information Tab
"""
import logging
from datetime import datetime

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# Import utilities
try:
    from ui.utils import create_styled_button, show_success_message, show_error_message
except ImportError:
    # Fallback functions
    def create_styled_button(text, color="#0078d4", icon=None, tooltip=""):
        btn = QPushButton(text)
        if tooltip:
            btn.setToolTip(tooltip)
        return btn
    
    def show_success_message(parent, message):
        QMessageBox.information(parent, "Success", message)
    
    def show_error_message(parent, message):
        QMessageBox.critical(parent, "Error", message)

logger = logging.getLogger(__name__)


class WellInfoTab(QWidget):
    """Well Information Tab"""
    
    # Signals
    data_saved = Signal()
    well_deleted = Signal()
    data_changed = Signal()
    
    def __init__(self, db_manager, main_window):
        super().__init__()
        self.db_manager = db_manager
        self.main_window = main_window
        self.current_well = None
        self.is_loading = False
        
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        """Initialize user interface based on your code"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Well Type
        well_type_group = QGroupBox("Well Type")
        type_layout = QHBoxLayout()
        self.well_type_onshore = QRadioButton("Onshore")
        self.well_type_offshore = QRadioButton("Offshore")
        self.well_type_onshore.setChecked(True)
        type_layout.addWidget(self.well_type_onshore)
        type_layout.addWidget(self.well_type_offshore)
        well_type_group.setLayout(type_layout)
        layout.addWidget(well_type_group)
        
        # Basic Information Form
        form_group = QGroupBox("Basic Information")
        form_layout = QFormLayout()
        
        # Section
        section_layout = QHBoxLayout()
        section_layout.addWidget(QLabel("Section:"))
        self.section_name = QLineEdit()
        self.section_name.setPlaceholderText("Enter section name (e.g., XYZ-01)")
        section_layout.addWidget(self.section_name)
        section_layout.addStretch()
        form_layout.addRow(section_layout)
        
        # Row 1
        row1_layout = QHBoxLayout()
        self.client = QLineEdit()
        self.client.setPlaceholderText("Client")
        self.client_rep = QLineEdit()
        self.client_rep.setPlaceholderText("Client Representative")
        row1_layout.addWidget(QLabel("Client:"))
        row1_layout.addWidget(self.client)
        row1_layout.addWidget(QLabel("Client Rep:"))
        row1_layout.addWidget(self.client_rep)
        form_layout.addRow(row1_layout)
        
        # Row 2
        row2_layout = QHBoxLayout()
        self.operator = QLineEdit()
        self.operator.setPlaceholderText("Operator")
        self.project = QLineEdit()
        self.project.setPlaceholderText("Project")
        row2_layout.addWidget(QLabel("Operator:"))
        row2_layout.addWidget(self.operator)
        row2_layout.addWidget(QLabel("Project:"))
        row2_layout.addWidget(self.project)
        form_layout.addRow(row2_layout)
        
        # Row 3
        row3_layout = QHBoxLayout()
        self.well_name = QLineEdit()
        self.well_name.setPlaceholderText("Well Name")
        self.rig_name = QLineEdit()
        self.rig_name.setPlaceholderText("Rig Name")
        row3_layout.addWidget(QLabel("Well Name:"))
        row3_layout.addWidget(self.well_name)
        row3_layout.addWidget(QLabel("Rig Name:"))
        row3_layout.addWidget(self.rig_name)
        form_layout.addRow(row3_layout)
        
        # Row 4
        row4_layout = QHBoxLayout()
        self.drilling_contractor = QLineEdit()
        self.drilling_contractor.setPlaceholderText("Drilling Contractor")
        self.report_no = QLineEdit()
        self.report_no.setPlaceholderText("Report No.")
        row4_layout.addWidget(QLabel("Drilling Contractor:"))
        row4_layout.addWidget(self.drilling_contractor)
        row4_layout.addWidget(QLabel("Report No:"))
        row4_layout.addWidget(self.report_no)
        form_layout.addRow(row4_layout)
        
        # Rig Type and Shape
        row5_layout = QHBoxLayout()
        self.rig_type = QComboBox()
        self.rig_type.addItems(
            ["Land", "Jackup", "SemiSub", "Platform", "Barge", "Other"]
        )
        self.well_shape = QComboBox()
        self.well_shape.addItems(
            ["Vertical", "Deviated", "Horizontal", "J-Shape", "S-Shape"]
        )
        row5_layout.addWidget(QLabel("Rig Type:"))
        row5_layout.addWidget(self.rig_type)
        row5_layout.addWidget(QLabel("Well Shape:"))
        row5_layout.addWidget(self.well_shape)
        form_layout.addRow(row5_layout)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Depths and Measurements
        depths_group = QGroupBox("Depths & Measurements")
        depths_layout = QGridLayout()
        
        row = 0
        # GLE-MSL
        depths_layout.addWidget(QLabel("GLE-MSL (m):"), row, 0)
        self.gle_msl = QDoubleSpinBox()
        self.gle_msl.setRange(-10000, 10000)
        self.gle_msl.setSuffix(" m")
        depths_layout.addWidget(self.gle_msl, row, 1)
        
        # RTE-MSL
        depths_layout.addWidget(QLabel("RTE-MSL (m):"), row, 2)
        self.rte_msl = QDoubleSpinBox()
        self.rte_msl.setRange(-10000, 10000)
        self.rte_msl.setSuffix(" m")
        depths_layout.addWidget(self.rte_msl, row, 3)
        
        row += 1
        # GLE-RTE
        depths_layout.addWidget(QLabel("GLE-RTE (m):"), row, 0)
        self.gle_rte = QDoubleSpinBox()
        self.gle_rte.setRange(-1000, 1000)
        self.gle_rte.setSuffix(" m")
        depths_layout.addWidget(self.gle_rte, row, 1)
        
        # Estimated Final Depth
        depths_layout.addWidget(QLabel("Estimated Final Depth MD (m):"), row, 2)
        self.estimated_depth = QDoubleSpinBox()
        self.estimated_depth.setRange(0, 10000)
        self.estimated_depth.setSuffix(" m")
        depths_layout.addWidget(self.estimated_depth, row, 3)
        
        row += 1
        # Derrick Height
        depths_layout.addWidget(QLabel("Derrick Height:"), row, 0)
        self.derrick_height = QSpinBox()
        self.derrick_height.setRange(0, 300)
        self.derrick_height.setSuffix(" ft")
        depths_layout.addWidget(self.derrick_height, row, 1)
        
        # Water Depth
        depths_layout.addWidget(QLabel("Water Depth (m):"), row, 2)
        self.water_depth = QDoubleSpinBox()
        self.water_depth.setRange(0, 5000)
        self.water_depth.setSuffix(" m")
        depths_layout.addWidget(self.water_depth, row, 3)
        
        row += 1
        # LTA (Day)
        depths_layout.addWidget(QLabel("LTA (Day):"), row, 0)
        self.lta_day = QSpinBox()
        self.lta_day.setRange(0, 365)
        depths_layout.addWidget(self.lta_day, row, 1)
        
        # Actual Rig Days
        depths_layout.addWidget(QLabel("Actual Rig Days:"), row, 2)
        self.actual_rig_days = QSpinBox()
        self.actual_rig_days.setRange(0, 365)
        depths_layout.addWidget(self.actual_rig_days, row, 3)
        
        row += 1
        # Rig Heading
        depths_layout.addWidget(QLabel("Rig Heading (°):"), row, 0)
        self.rig_heading = QDoubleSpinBox()
        self.rig_heading.setRange(0, 360)
        self.rig_heading.setSuffix(" °")
        depths_layout.addWidget(self.rig_heading, row, 1)
        
        # KOP #1
        depths_layout.addWidget(QLabel("KOP #1:"), row, 2)
        self.kop1 = QDoubleSpinBox()
        self.kop1.setRange(0, 10000)
        self.kop1.setSuffix(" m")
        depths_layout.addWidget(self.kop1, row, 3)
        
        row += 1
        # KOP #2
        depths_layout.addWidget(QLabel("KOP #2:"), row, 0)
        self.kop2 = QDoubleSpinBox()
        self.kop2.setRange(0, 10000)
        self.kop2.setSuffix(" m")
        depths_layout.addWidget(self.kop2, row, 1)
        
        # Formation
        depths_layout.addWidget(QLabel("Formation:"), row, 2)
        self.formation = QLineEdit()
        depths_layout.addWidget(self.formation, row, 3)
        
        depths_group.setLayout(depths_layout)
        layout.addWidget(depths_group)
        
        # Coordinates
        coords_group = QGroupBox("Coordinates")
        coords_layout = QGridLayout()
        
        coords_layout.addWidget(QLabel("Latitude:"), 0, 0)
        self.latitude = QDoubleSpinBox()
        self.latitude.setRange(-90, 90)
        self.latitude.setDecimals(6)
        coords_layout.addWidget(self.latitude, 0, 1)
        
        coords_layout.addWidget(QLabel("Longitude:"), 0, 2)
        self.longitude = QDoubleSpinBox()
        self.longitude.setRange(-180, 180)
        self.longitude.setDecimals(6)
        coords_layout.addWidget(self.longitude, 0, 3)
        
        coords_layout.addWidget(QLabel("Northing (m):"), 1, 0)
        self.northing = QDoubleSpinBox()
        self.northing.setRange(-1000000, 1000000)
        coords_layout.addWidget(self.northing, 1, 1)
        
        coords_layout.addWidget(QLabel("Easting (m):"), 1, 2)
        self.easting = QDoubleSpinBox()
        self.easting.setRange(-1000000, 1000000)
        coords_layout.addWidget(self.easting, 1, 3)
        
        coords_group.setLayout(coords_layout)
        layout.addWidget(coords_group)
        
        # Dates
        dates_group = QGroupBox("Dates")
        dates_layout = QGridLayout()
        
        dates_layout.addWidget(QLabel("Spud Date:"), 0, 0)
        self.spud_date = QDateEdit()
        self.spud_date.setCalendarPopup(True)
        self.spud_date.setDate(QDate.currentDate())
        dates_layout.addWidget(self.spud_date, 0, 1)
        
        dates_layout.addWidget(QLabel("Start Hole Date:"), 0, 2)
        self.start_hole_date = QDateEdit()
        self.start_hole_date.setCalendarPopup(True)
        self.start_hole_date.setDate(QDate.currentDate())
        dates_layout.addWidget(self.start_hole_date, 0, 3)
        
        dates_layout.addWidget(QLabel("Rig Move Date:"), 1, 0)
        self.rig_move_date = QDateEdit()
        self.rig_move_date.setCalendarPopup(True)
        self.rig_move_date.setDate(QDate.currentDate())
        dates_layout.addWidget(self.rig_move_date, 1, 1)
        
        dates_layout.addWidget(QLabel("Report Date:"), 1, 2)
        self.report_date = QDateEdit()
        self.report_date.setCalendarPopup(True)
        self.report_date.setDate(QDate.currentDate())
        dates_layout.addWidget(self.report_date, 1, 3)
        
        dates_group.setLayout(dates_layout)
        layout.addWidget(dates_group)
        
        # Personnel
        personnel_group = QGroupBox("Personnel")
        personnel_layout = QGridLayout()
        
        personnel_layout.addWidget(QLabel("Operation Manager:"), 0, 0)
        self.operation_manager = QLineEdit()
        personnel_layout.addWidget(self.operation_manager, 0, 1)
        
        personnel_layout.addWidget(QLabel("Superintendent:"), 0, 2)
        self.superintendent = QLineEdit()
        personnel_layout.addWidget(self.superintendent, 0, 3)
        
        personnel_layout.addWidget(QLabel("Supervisor (Day):"), 1, 0)
        self.supervisor_day = QLineEdit()
        personnel_layout.addWidget(self.supervisor_day, 1, 1)
        
        personnel_layout.addWidget(QLabel("Supervisor (Night):"), 1, 2)
        self.supervisor_night = QLineEdit()
        personnel_layout.addWidget(self.supervisor_night, 1, 3)
        
        personnel_layout.addWidget(QLabel("Geologist 1:"), 2, 0)
        self.geologist1 = QLineEdit()
        personnel_layout.addWidget(self.geologist1, 2, 1)
        
        personnel_layout.addWidget(QLabel("Geologist 2:"), 2, 2)
        self.geologist2 = QLineEdit()
        personnel_layout.addWidget(self.geologist2, 2, 3)
        
        personnel_layout.addWidget(QLabel("Tool Pusher (Day):"), 3, 0)
        self.tool_pusher_day = QLineEdit()
        personnel_layout.addWidget(self.tool_pusher_day, 3, 1)
        
        personnel_layout.addWidget(QLabel("Tool Pusher (Night):"), 3, 2)
        self.tool_pusher_night = QLineEdit()
        personnel_layout.addWidget(self.tool_pusher_night, 3, 3)
        
        personnel_group.setLayout(personnel_layout)
        layout.addWidget(personnel_group)
        
        # Objectives
        objectives_group = QGroupBox("Objectives")
        objectives_layout = QVBoxLayout()
        self.objectives = QTextEdit()
        self.objectives.setMaximumHeight(150)
        objectives_layout.addWidget(self.objectives)
        objectives_group.setLayout(objectives_layout)
        layout.addWidget(objectives_group)
                
        # Buttons with new styling
        button_layout = QHBoxLayout()
        
        self.save_btn = create_styled_button("💾 Save Well Info", color="#28a745")
        self.load_btn = create_styled_button("📂 Load Well", color="#007bff")
        self.clear_btn = create_styled_button("🗑️ Clear", color="#6c757d")
        self.delete_btn = create_styled_button("🗑️ Delete Well", color="#dc3545")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
                
        container.setLayout(layout)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect buttons
        self.save_btn.clicked.connect(self.save_data)
        self.load_btn.clicked.connect(self.load_well_dialog)
        self.delete_btn.clicked.connect(self.delete_well)
        self.clear_btn.clicked.connect(self.clear_form_fields)
        
        # Connect data change signals
        text_fields = [
            self.section_name, self.client, self.client_rep, self.operator,
            self.project, self.well_name, self.rig_name, self.drilling_contractor,
            self.report_no, self.formation, self.operation_manager, self.superintendent,
            self.supervisor_day, self.supervisor_night, self.geologist1,
            self.geologist2, self.tool_pusher_day, self.tool_pusher_night
        ]
        
        for field in text_fields:
            field.textChanged.connect(self.on_data_changed)
        
        # Connect combos
        self.rig_type.currentTextChanged.connect(self.on_data_changed)
        self.well_shape.currentTextChanged.connect(self.on_data_changed)
        
        # Connect radio buttons
        self.well_type_onshore.toggled.connect(self.on_data_changed)
        self.well_type_offshore.toggled.connect(self.on_data_changed)
        
        # Connect spin boxes
        spin_boxes = [
            self.gle_msl, self.rte_msl, self.gle_rte, self.estimated_depth,
            self.water_depth, self.derrick_height, self.lta_day, self.actual_rig_days,
            self.rig_heading, self.kop1, self.kop2, self.latitude, self.longitude,
            self.northing, self.easting
        ]
        
        for spin in spin_boxes:
            spin.valueChanged.connect(self.on_data_changed)
        
        # Connect dates
        self.spud_date.dateChanged.connect(self.on_data_changed)
        self.start_hole_date.dateChanged.connect(self.on_data_changed)
        self.rig_move_date.dateChanged.connect(self.on_data_changed)
        self.report_date.dateChanged.connect(self.on_data_changed)
        
        # Connect text edit
        self.objectives.textChanged.connect(self.on_data_changed)
    
    def on_data_changed(self):
        """Handle data change"""
        if not self.is_loading:
            self.data_changed.emit()
 
    def load_data(self):
        """Load data from database"""
        if not self.current_well:
            return
        
        try:
            self.is_loading = True
            
            # Load well data from database
            well_data = self.db_manager.get_well_by_id(self.current_well['id'] if isinstance(self.current_well, dict) else self.current_well.id)
            
            if not well_data:
                logger.warning("Well data not found")
                return
            
            # Helper function to safely get data
            def safe_float(value, default=0.0):
                """Safely convert value to float"""
                if value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            def safe_int(value, default=0):
                """Safely convert value to int"""
                if value is None:
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default
            
            def get_value(key, default=None):
                if isinstance(well_data, dict):
                    value = well_data.get(key, default)
                else:
                    value = getattr(well_data, key, default)
                return value
            
            # Well Name
            self.well_name.setText(str(get_value('name', '')))
            
            # Well Type
            well_type = get_value('well_type', 'Onshore')
            if well_type == 'Onshore':
                self.well_type_onshore.setChecked(True)
            else:
                self.well_type_offshore.setChecked(True)
            
            # Section/Code
            self.section_name.setText(str(get_value('section_name', '')))
            
            # Client and Rep
            self.client.setText(str(get_value('client', '')))
            self.client_rep.setText(str(get_value('client_rep', '')))
            
            # Operator and Project
            self.operator.setText(str(get_value('operator', '')))
            self.project.setText(str(get_value('project_name', '')))
            
            # Rig and Contractor
            self.rig_name.setText(str(get_value('rig_name', '')))
            self.drilling_contractor.setText(str(get_value('drilling_contractor', '')))
            self.report_no.setText(str(get_value('report_no', '')))
            
            # Rig Type and Well Shape
            rig_type = get_value('rig_type', 'Land')
            index = self.rig_type.findText(str(rig_type))
            if index >= 0:
                self.rig_type.setCurrentIndex(index)
            
            well_shape = get_value('well_shape', 'Vertical')
            index = self.well_shape.findText(str(well_shape))
            if index >= 0:
                self.well_shape.setCurrentIndex(index)
            
            # Depths and Measurements - استفاده از توابع safe
            self.gle_msl.setValue(safe_float(get_value('gle_msl')))
            self.rte_msl.setValue(safe_float(get_value('rte_msl')))
            self.gle_rte.setValue(safe_float(get_value('gle_rte')))
            self.estimated_depth.setValue(safe_float(get_value('estimated_final_depth')))
            self.derrick_height.setValue(safe_int(get_value('derrick_height')))
            self.water_depth.setValue(safe_float(get_value('water_depth')))
            self.lta_day.setValue(safe_int(get_value('lta_day')))
            self.actual_rig_days.setValue(safe_int(get_value('actual_rig_days')))
            self.rig_heading.setValue(safe_float(get_value('rig_heading')))
            self.kop1.setValue(safe_float(get_value('kop1')))
            self.kop2.setValue(safe_float(get_value('kop2')))
            self.formation.setText(str(get_value('formation', '')))
            
            # Coordinates
            self.latitude.setValue(safe_float(get_value('latitude')))
            self.longitude.setValue(safe_float(get_value('longitude')))
            self.northing.setValue(safe_float(get_value('northing')))
            self.easting.setValue(safe_float(get_value('easting')))
            
            # Dates
            def safe_set_date(date_edit, date_value):
                """Safely set date value"""
                if not date_value:
                    return
                
                try:
                    if isinstance(date_value, str):
                        if date_value.strip():
                            date_obj = datetime.strptime(date_value, "%Y-%m-%d").date()
                            date_edit.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
                    elif hasattr(date_value, 'year'):
                        date_edit.setDate(QDate(date_value.year, date_value.month, date_value.day))
                except Exception as e:
                    logger.warning(f"Error setting date: {e}")
            
            safe_set_date(self.spud_date, get_value('spud_date'))
            safe_set_date(self.start_hole_date, get_value('start_hole_date'))
            safe_set_date(self.rig_move_date, get_value('rig_move_date'))
            safe_set_date(self.report_date, get_value('report_date'))
            
            # Personnel
            self.operation_manager.setText(str(get_value('operation_manager', '')))
            self.superintendent.setText(str(get_value('superintendent', '')))
            self.supervisor_day.setText(str(get_value('supervisor_day', '')))
            self.supervisor_night.setText(str(get_value('supervisor_night', '')))
            self.geologist1.setText(str(get_value('geologist1', '')))
            self.geologist2.setText(str(get_value('geologist2', '')))
            self.tool_pusher_day.setText(str(get_value('tool_pusher_day', '')))
            self.tool_pusher_night.setText(str(get_value('tool_pusher_night', '')))
            
            # Objectives
            self.objectives.setText(str(get_value('objectives', '')))
            
            logger.info("Well data loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load well data: {str(e)}")
        finally:
            self.is_loading = False
            
    def load_well_by_id(self, well_id):
        """Load well by ID"""
        try:
            well_data = self.db_manager.get_well_by_id(well_id)
            if well_data:
                self.current_well = well_data
                self.load_data()
                logger.info(f"Well {well_id} loaded successfully")
                
                # Update main window status if available
                if hasattr(self.main_window, 'status_manager'):
                    self.main_window.status_manager.show_success(
                        "WellInfoTab",
                        f"Well '{well_data.get('name', 'Unknown')}' loaded"
                    )
                return True
            else:
                logger.warning(f"Well {well_id} not found")
                if hasattr(self.main_window, 'status_manager'):
                    self.main_window.status_manager.show_error(
                        "WellInfoTab",
                        f"Well ID {well_id} not found"
                    )
                return False
        except Exception as e:
            logger.error(f"Error loading well {well_id}: {str(e)}")
            # Show more detailed error message
            error_msg = str(e)
            if "NoneType" in error_msg:
                error_msg = "Database contains invalid NULL values for this well. Please check the well data."
            
            if hasattr(self.main_window, 'status_manager'):
                self.main_window.status_manager.show_error(
                    "WellInfoTab",
                    f"Failed to load well: {error_msg[:100]}"
                )
            return False
    
    def save_data(self):
        """Save well information"""
        try:
            # Collect data from form
            well_data = self.get_form_data()
            
            # Validate required fields
            if not well_data['name']:
                show_error_message(self, "Well name is required!")
                return False
            
            # Save to database
            if self.current_well:
                well_data['id'] = self.current_well['id'] if isinstance(self.current_well, dict) else self.current_well.id
            
            if self.db_manager.save_well(well_data):
                show_success_message(self, "Well information saved successfully!")
                self.data_saved.emit()
                
                # به‌روزرسانی status bar اگر main_window دارد
                if hasattr(self.main_window, 'status_manager'):
                    self.main_window.status_manager.show_success(
                        "WellInfoTab",
                        "Well information saved"
                    )
                
                return True
            else:
                show_error_message(self, "Failed to save well information!")
                return False
            
        except Exception as e:
            logger.error(f"Failed to save well: {str(e)}")
            show_error_message(self, f"Failed to save well: {str(e)}")
            return False
    
    def get_form_data(self):
        """Get data from form"""
        # Well type
        well_type = "Onshore" if self.well_type_onshore.isChecked() else "Offshore"
        
        # Coordinates
        lat = self.latitude.value()
        lon = self.longitude.value()
        coordinates = f"{lat}, {lon}" if lat != 0 or lon != 0 else ""
        
        # Spud date
        spud_date = self.spud_date.date().toString("yyyy-MM-dd")
        
        data = {
            "name": self.well_name.text().strip(),
            "code": self.section_name.text().strip(),
            "well_type": well_type,
            "operator": self.operator.text().strip(),
            "client": self.client.text().strip(),
            "client_rep": self.client_rep.text().strip(),
            "project": self.project.text().strip(),
            "rig_name": self.rig_name.text().strip(),
            "drilling_contractor": self.drilling_contractor.text().strip(),
            "report_no": self.report_no.text().strip(),
            "rig_type": self.rig_type.currentText(),
            "well_shape": self.well_shape.currentText(),
            "gle_msl": self.gle_msl.value(),
            "rte_msl": self.rte_msl.value(),
            "gle_rte": self.gle_rte.value(),
            "estimated_depth": self.estimated_depth.value(),
            "water_depth": self.water_depth.value(),
            "derrick_height": self.derrick_height.value(),
            "lta_day": self.lta_day.value(),
            "actual_rig_days": self.actual_rig_days.value(),
            "rig_heading": self.rig_heading.value(),
            "kop1": self.kop1.value(),
            "kop2": self.kop2.value(),
            "formation": self.formation.text().strip(),
            "coordinates": coordinates,
            "latitude": self.latitude.value(),
            "longitude": self.longitude.value(),
            "northing": self.northing.value(),
            "easting": self.easting.value(),
            "spud_date": spud_date,
            "start_hole_date": self.start_hole_date.date().toString("yyyy-MM-dd"),
            "rig_move_date": self.rig_move_date.date().toString("yyyy-MM-dd"),
            "report_date": self.report_date.date().toString("yyyy-MM-dd"),
            "operation_manager": self.operation_manager.text().strip(),
            "superintendent": self.superintendent.text().strip(),
            "supervisor_day": self.supervisor_day.text().strip(),
            "supervisor_night": self.supervisor_night.text().strip(),
            "geologist1": self.geologist1.text().strip(),
            "geologist2": self.geologist2.text().strip(),
            "tool_pusher_day": self.tool_pusher_day.text().strip(),
            "tool_pusher_night": self.tool_pusher_night.text().strip(),
            "objectives": self.objectives.toPlainText().strip()
        }
        
        return data
    
    def delete_well(self):
        """Delete current well from database"""
        if not self.current_well:
            QMessageBox.warning(self, "No Well", "Please select a well first")
            return
        
        well_name = self.current_well.get('name', 'Unknown') if isinstance(self.current_well, dict) else getattr(self.current_well, 'name', 'Unknown')
        
        reply = QMessageBox.question(
            self,
            "Delete Well",
            f"Are you sure you want to delete well '{well_name}'?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply == QMessageBox.No:
            return
        
        well_id = self.current_well['id'] if isinstance(self.current_well, dict) else self.current_well.id
        
        if self.db_manager.delete_well(well_id):
            QMessageBox.information(self, "Success", "Well deleted successfully!")
            self.clear_form_fields()
            self.current_well = None
            self.well_deleted.emit()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete well!")
    
    def clear_form_fields(self):
        """Clear all form fields"""
        self.is_loading = True
        
        # Reset radio buttons
        self.well_type_onshore.setChecked(True)
        
        # Clear text fields
        self.section_name.clear()
        self.client.clear()
        self.client_rep.clear()
        self.operator.clear()
        self.project.clear()
        self.well_name.clear()
        self.rig_name.clear()
        self.drilling_contractor.clear()
        self.report_no.clear()
        self.formation.clear()
        
        # Reset comboboxes
        self.rig_type.setCurrentIndex(0)
        self.well_shape.setCurrentIndex(0)
        
        # Reset spinboxes
        self.gle_msl.setValue(0)
        self.rte_msl.setValue(0)
        self.gle_rte.setValue(0)
        self.estimated_depth.setValue(0)
        self.derrick_height.setValue(0)
        self.water_depth.setValue(0)
        self.lta_day.setValue(0)
        self.actual_rig_days.setValue(0)
        self.rig_heading.setValue(0)
        self.kop1.setValue(0)
        self.kop2.setValue(0)
        self.latitude.setValue(0)
        self.longitude.setValue(0)
        self.northing.setValue(0)
        self.easting.setValue(0)
        
        # Reset dates
        current_date = QDate.currentDate()
        self.spud_date.setDate(current_date)
        self.start_hole_date.setDate(current_date)
        self.rig_move_date.setDate(current_date)
        self.report_date.setDate(current_date)
        
        # Clear personnel fields
        self.operation_manager.clear()
        self.superintendent.clear()
        self.supervisor_day.clear()
        self.supervisor_night.clear()
        self.geologist1.clear()
        self.geologist2.clear()
        self.tool_pusher_day.clear()
        self.tool_pusher_night.clear()
        
        # Clear objectives
        self.objectives.clear()
        
        self.is_loading = False
    

    def load_well_dialog(self):
        """Open dialog to select a well to load"""
        try:
            # Get hierarchy from database
            hierarchy = self.db_manager.get_hierarchy()
            
            if not hierarchy:
                show_error_message(self, "No wells found in database.")
                return
            
            dialog = QDialog(self)
            dialog.setWindowTitle("📂 Select Well")
            dialog.setFixedSize(500, 400)
            
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Select a well to load:"))
            
            list_widget = QListWidget()
            
            # Add wells from hierarchy
            for company in hierarchy:
                for project in company.get('projects', []):
                    for well in project.get('wells', []):
                        display_name = f"{well['name']}"
                        if well.get('code'):
                            display_name += f" ({well['code']})"
                        if project.get('name'):
                            display_name += f" - {project['name']}"
                        
                        item = QListWidgetItem(display_name)
                        item.setData(Qt.UserRole, well['id'])
                        list_widget.addItem(item)
            
            layout.addWidget(list_widget)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec():
                selected_items = list_widget.selectedItems()
                if selected_items:
                    well_id = selected_items[0].data(Qt.UserRole)
                    well_data = self.db_manager.get_well_by_id(well_id)
                    
                    if well_data:
                        self.current_well = well_data
                        self.load_data()
                        
                        # نمایش پیام
                        if hasattr(self.main_window, 'status_manager'):
                            self.main_window.status_manager.show_success(
                                "WellInfoTab", 
                                f"Loaded well: {well_data['name']}"
                            )
                        
        except Exception as e:
            logger.error(f"Error loading well dialog: {str(e)}")
            show_error_message(self, f"Failed to load wells: {str(e)}")
            
    def on_selection_changed(self, item_type, item_id):
        """Handle external selection change"""
        if item_type == "well":
            self.load_well_by_id(item_id)
    def refresh(self):
        """Refresh tab data"""
        if self.current_well:
            self.load_data()
    
    def cleanup(self):
        """Cleanup resources"""
        self.clear_form_fields()