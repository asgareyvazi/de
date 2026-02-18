"""
Database - SQLAlchemy ORM setup and DatabaseManager class
"""

import logging
from datetime import datetime, date, timedelta
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    ForeignKey,JSON,
    Text,
    Time,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
import json
logger = logging.getLogger(__name__)

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), unique=True)
    address = Column(Text)
    contact_person = Column(String(100))
    contact_email = Column(String(100))
    contact_phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship(
        "Project", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}')>"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True)
    location = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(50), default="Active")
    manager = Column(String(100))
    budget = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="projects")
    wells = relationship("Well", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"

class Well(Base):
    __tablename__ = "wells"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True)

    # فیلدهای اصلی
    field_name = Column(String(100))
    location = Column(Text)
    coordinates = Column(String(100))
    elevation = Column(Float, default=0.0)
    water_depth = Column(Float, default=0.0)
    spud_date = Column(Date)
    target_depth = Column(Float, default=0.0)
    status = Column(String(50), default="Planning")
    well_type = Column(String(50))
    purpose = Column(String(100))

    well_type_field = Column(String(50), default="Onshore")  # Onshore/Offshore
    section_name = Column(String(100))
    client = Column(String(100))
    client_rep = Column(String(100))
    operator = Column(String(100))
    project_name = Column(String(100))
    rig_name = Column(String(100))
    drilling_contractor = Column(String(100))
    report_no = Column(String(100))
    rig_type = Column(String(50))  # Land, Jackup, etc.
    well_shape = Column(String(50))  # Vertical, Deviated, etc.
    gle_msl = Column(Float)
    rte_msl = Column(Float)
    gle_rte = Column(Float)
    estimated_final_depth = Column(Float)
    derrick_height = Column(Integer)
    lta_day = Column(Integer)
    actual_rig_days = Column(Integer)
    rig_heading = Column(Float)
    kop1 = Column(Float)
    kop2 = Column(Float)
    formation = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    northing = Column(Float)
    easting = Column(Float)
    start_hole_date = Column(Date)
    rig_move_date = Column(Date)
    report_date = Column(Date)
    operation_manager = Column(String(100))
    superintendent = Column(String(100))
    supervisor_day = Column(String(100))
    supervisor_night = Column(String(100))
    geologist1 = Column(String(100))
    geologist2 = Column(String(100))
    tool_pusher_day = Column(String(100))
    tool_pusher_night = Column(String(100))
    objectives = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="wells")
    sections = relationship("Section", back_populates="well", cascade="all, delete-orphan")
    daily_reports = relationship("DailyReport", backref="daily_report_well", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Well(id={self.id}, name='{self.name}')>"

class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)
    well_id = Column(
        Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    code = Column(String(50))
    depth_from = Column(Float, default=0.0)
    depth_to = Column(Float, default=0.0)
    diameter = Column(Float) 
    hole_size = Column(Float) 
    purpose = Column(String(100))
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    well = relationship("Well", back_populates="sections")
    daily_reports = relationship(
        "DailyReport", 
        back_populates="section", 
        cascade="all, delete-orphan"
    )
    def __repr__(self):
        return f"<Section(id={self.id}, name='{self.name}', well_id={self.well_id})>"

class DailyReport(Base):
    __tablename__ = 'daily_reports'

    id = Column(Integer, primary_key=True)
    well_id = Column(
        Integer, ForeignKey('wells.id', ondelete='CASCADE'), nullable=False
    )
    section_id = Column(
        Integer, ForeignKey('sections.id', ondelete='CASCADE'), nullable=True
    )
    report_date = Column(Date, nullable=False)
    report_number = Column(Integer, default=1)  # شماره گزارش
    
    rig_day = Column(Integer, default=1)
    # فیلدهای جدید برای ساختار سلسله مراتبی
    report_title = Column(String(200))  # عنوان گزارش: "01 Daily Report, Project name, date"
    
    # داده‌های گزارش‌های مختلف
    drilling_data = Column(JSON, nullable=True)
    mud_data = Column(JSON, nullable=True)
    equipment_data = Column(JSON, nullable=True)
    downhole_data = Column(JSON, nullable=True)
    trajectory_data = Column(JSON, nullable=True)
    logistics_data = Column(JSON, nullable=True)
    safety_data = Column(JSON, nullable=True)
    services_data = Column(JSON, nullable=True)
    analysis_data = Column(JSON, nullable=True)
    planning_data = Column(JSON, nullable=True)  
    export_data = Column(JSON, nullable=True)   
    
    # Depth measurements (ابقا)
    depth_0000 = Column(Float, default=0.0)
    depth_0600 = Column(Float, default=0.0)
    depth_2400 = Column(Float, default=0.0)

    # Summary (ابقا)
    summary = Column(Text)

    # Status (ابقا)
    status = Column(String(50), default='Draft')

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))

    # Relationships
    section = relationship("Section", back_populates="daily_reports")
    creator = relationship("User", foreign_keys=[created_by])
    
    # رابطه‌های قدیمی
    time_logs_24h = relationship(
        "TimeLog24H", back_populates="report", cascade="all, delete-orphan"
    )
    time_logs_morning = relationship(
        "TimeLogMorning", back_populates="report", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<DailyReport(id={self.id}, report_number={self.report_number}, date={self.report_date})>"

class DailyReportDetail(Base):
    """جزئیات هر تب از گزارش روزانه"""
    __tablename__ = 'daily_report_details'
    
    id = Column(Integer, primary_key=True)
    report_id = Column(
        Integer, ForeignKey('daily_reports.id', ondelete='CASCADE'), nullable=False
    )
    tab_type = Column(String(50), nullable=False) 
    tab_name = Column(String(100), nullable=False)
    tab_data = Column(JSON, nullable=True) 
    
    # فیلدهای جدید برای ساختار سلسله مراتبی
    parent_tab_id = Column(Integer, ForeignKey('daily_report_details.id'), nullable=True)
    tab_order = Column(Integer, default=0) 
    tab_level = Column(Integer, default=0)
    widget_class = Column(String(100)) 
    icon = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    report = relationship("DailyReport", backref="tab_details")
    parent = relationship("DailyReportDetail", remote_side=[id], backref="children")
    
    def __repr__(self):
        return f"<DailyReportDetail(id={self.id}, report_id={self.report_id}, tab_type='{self.tab_type}')>"
        
class TimeLog24H(Base):
    __tablename__ = "time_logs_24h"

    id = Column(Integer, primary_key=True)
    report_id = Column(
        Integer, ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False
    )

    # Time information
    time_from = Column(Time, nullable=False)
    time_to = Column(Time, nullable=False)
    duration = Column(Float)  # in hours
    
    # Flags for 24:00 support
    is_from_2400 = Column(Boolean, default=False)  # 🆕 این خط را اضافه کنید
    is_to_2400 = Column(Boolean, default=False)    # 🆕 این خط را اضافه کنید

    # Activity codes
    main_phase = Column(String(100))
    main_code = Column(String(100))
    sub_code = Column(String(100))

    # Status and flags
    status = Column(String(50))
    is_npt = Column(Boolean, default=False)  # Non-Productive Time

    # Description
    activity_description = Column(Text)

    # Relationships
    report = relationship("DailyReport", back_populates="time_logs_24h")

    def __repr__(self):
        from_str = "24:00" if self.is_from_2400 else self.time_from.strftime("%H:%M")
        to_str = "24:00" if self.is_to_2400 else self.time_to.strftime("%H:%M")
        return f"<TimeLog24H(id={self.id}, from={from_str}, to={to_str})>"


class TimeLogMorning(Base):
    __tablename__ = "time_logs_morning"

    id = Column(Integer, primary_key=True)
    report_id = Column(
        Integer, ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False
    )

    # Time information
    time_from = Column(Time, nullable=False)
    time_to = Column(Time, nullable=False)
    duration = Column(Float)  # in hours
    
    # Flags for 24:00 support
    is_from_2400 = Column(Boolean, default=False)  # 🆕 این خط را اضافه کنید
    is_to_2400 = Column(Boolean, default=False)    # 🆕 این خط را اضافه کنید

    # Activity codes
    main_phase = Column(String(100))
    main_code = Column(String(100))
    sub_code = Column(String(100))

    # Status and flags
    status = Column(String(50))
    is_npt = Column(Boolean, default=False)  # Non-Productive Time

    # Description
    activity_description = Column(Text)

    # Relationships
    report = relationship("DailyReport", back_populates="time_logs_morning")

    def __repr__(self):
        from_str = "24:00" if self.is_from_2400 else self.time_from.strftime("%H:%M")
        to_str = "24:00" if self.is_to_2400 else self.time_to.strftime("%H:%M")
        return f"<TimeLogMorning(id={self.id}, from={from_str}, to={to_str})>"
        
class DrillingParameters(Base):
    """پارامترهای حفاری"""

    __tablename__ = "drilling_parameters"

    id = Column(Integer, primary_key=True)
    well_id = Column(
        Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False
    )
    report_date = Column(Date, nullable=False)

    # ============ Bit Information ============
    bit_no = Column(String(50))
    bit_rerun = Column(Integer, default=1)
    bit_size = Column(Float)  # inches
    bit_type = Column(String(50))
    manufacturer = Column(String(100))
    iadc_code = Column(String(50))
    nozzles_json = Column(Text)  # JSON array of nozzles
    tfa = Column(Float)  # Total Flow Area in²

    # ============ Depth Information ============
    depth_in = Column(Float)
    depth_out = Column(Float)
    bit_drilled = Column(Float)
    cum_drilled = Column(Float)

    # ============ Time Information ============
    hours_on_bottom = Column(Float)
    cum_hours = Column(Float)

    # ============ Drilling Parameters ============
    wob_min = Column(Float)  # klb
    wob_max = Column(Float)  # klb
    rpm_min = Column(Float)
    rpm_max = Column(Float)
    torque_min = Column(Float)  # klb.ft
    torque_max = Column(Float)  # klb.ft
    pump_pressure_min = Column(Float)  # psi
    pump_pressure_max = Column(Float)  # psi

    # ============ Pump Parameters ============
    pump_output_min = Column(Float)  # gpm
    pump_output_max = Column(Float)  # gpm
    pump1_spm = Column(Float)
    pump1_spp = Column(Float)  # psi
    pump2_spm = Column(Float)
    pump2_spp = Column(Float)  # psi

    # ============ Calculations ============
    avg_rop = Column(Float)  # m/hr
    hsi = Column(Float)  # Hydraulic horsepower per square inch
    annular_velocity = Column(Float)  # ft/min
    bit_revolution = Column(Float)  # k.rev

    # ============ Metadata ============
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    # ============ Relationships ============
    well = relationship("Well", backref="drilling_parameters")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<DrillingParameters(id={self.id}, well_id={self.well_id}, date={self.report_date})>"

class MudReport(Base):
    """گزارش گل حفاری"""

    __tablename__ = "mud_reports"

    id = Column(Integer, primary_key=True)
    well_id = Column(
        Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False
    )
    report_date = Column(Date, nullable=False)

    # ============ Mud Properties ============
    mud_type = Column(String(50))
    sample_time = Column(Time)
    mw = Column(Float)  # pcf
    pv = Column(Float)  # cp
    yp = Column(Float)  # lb/100ft²
    funnel_vis = Column(Float)
    gel_10s = Column(Float)
    gel_10m = Column(Float)
    fl = Column(Float)  # cc/30min
    cake_thickness = Column(Float)  # mm
    ph = Column(Float)
    temperature = Column(Float)  # °C
    solid_percent = Column(Float)
    oil_percent = Column(Float)
    water_percent = Column(Float)
    chloride = Column(Float)  # ppm

    # ============ Volumes ============
    volume_hole = Column(Float)  # bbl
    total_circulated = Column(Float)  # bbl
    loss_downhole = Column(Float)  # bbl
    loss_surface = Column(Float)  # bbl

    # ============ Mud Chemicals (JSON) ============
    chemicals_json = Column(Text)

    # ============ Metadata ============
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    # ============ Relationships ============
    well = relationship("Well", backref="mud_reports")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<MudReport(id={self.id}, well_id={self.well_id}, date={self.report_date})>"

class CementReport(Base):
    """گزارش سیمان"""

    __tablename__ = "cement_reports"

    id = Column(Integer, primary_key=True)
    well_id = Column(
        Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False
    )
    report_date = Column(Date, nullable=False)
    report_name = Column(String(100))

    # ============ Cement Materials (JSON) ============
    materials_json = Column(Text)

    # ============ Summary ============
    summary = Column(Text)

    # ============ Metadata ============
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    # ============ Relationships ============
    well = relationship("Well", backref="cement_reports")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<CementReport(id={self.id}, well_id={self.well_id}, name='{self.report_name}')>"

class CasingReport(Base):
    """گزارش کیسینگ"""

    __tablename__ = "casing_reports"

    id = Column(Integer, primary_key=True)
    well_id = Column(
        Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False
    )
    report_date = Column(Date, nullable=False)
    report_name = Column(String(100))

    # ============ Casing Data (JSON) ============
    casing_json = Column(Text)  # جدول کامل کیسینگ
    tally_json = Column(Text)  # جدول Casing Tally

    # ============ Summary ============
    summary = Column(Text)

    # ============ Metadata ============
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    # ============ Relationships ============
    well = relationship("Well", backref="casing_reports")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<CasingReport(id={self.id}, well_id={self.well_id}, name='{self.report_name}')>"

class WellboreSchematic(Base):
    """شماتیک چاه"""

    __tablename__ = "wellbore_schematics"

    id = Column(Integer, primary_key=True)
    well_id = Column(
        Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False
    )
    report_date = Column(Date, nullable=False)
    schematic_name = Column(String(100))

    # ============ Schematic Data ============
    image_data = Column(Text)  # Base64 encoded image or path
    layers_json = Column(Text)  # JSON for layers
    elements_json = Column(Text)  # JSON for graphical elements

    # ============ Metadata ============
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    # ============ Relationships ============
    well = relationship("Well", backref="wellbore_schematics")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<WellboreSchematic(id={self.id}, well_id={self.well_id}, name='{self.schematic_name}')>"

class TripSheetEntry(Base):
    """ورودی‌های Trip Sheet"""
    __tablename__ = 'trip_sheet_entries'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    time = Column(Time, nullable=False)
    activity = Column(String(200), nullable=False)
    depth = Column(Float, default=0.0)  # در متر
    cum_trip = Column(Float, default=0.0)  # تجمعی
    duration = Column(Float, default=0.0)  # در ساعت
    remarks = Column(Text)
    supervisor = Column(String(100))
    verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="trip_sheet_entries")
    section = relationship("Section", backref="trip_sheet_entries")
    report = relationship("DailyReport", backref="trip_sheet_entries")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<TripSheetEntry(id={self.id}, time={self.time}, activity='{self.activity}')>"

class SurveyPoint(Base):
    """نقاط سروی تراژکتوری"""
    __tablename__ = 'survey_points'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    calculation_id = Column(Integer, ForeignKey('trajectory_calculations.id'), nullable=True)
    
    # داده‌های اصلی
    md = Column(Float, nullable=False)  # Measured Depth (m)
    inc = Column(Float, nullable=False)  # Inclination (°)
    azi = Column(Float, nullable=False)  # Azimuth (°)
    
    # محاسبات
    tvd = Column(Float, default=0.0)  # True Vertical Depth (m)
    north = Column(Float, default=0.0)  # North coordinate (m)
    east = Column(Float, default=0.0)  # East coordinate (m)
    vs = Column(Float, default=0.0)  # Vertical Section (m)
    hd = Column(Float, default=0.0)  # Horizontal Displacement (m)
    dls = Column(Float, default=0.0)  # Dog Leg Severity (°/30m)
    
    # اطلاعات اضافی
    tool = Column(String(50), default='MWD')  # ابزار اندازه‌گیری
    remarks = Column(Text)
    measured_at = Column(DateTime)  # زمان اندازه‌گیری
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="survey_points")
    section = relationship("Section", backref="survey_points")
    calculation = relationship("TrajectoryCalculation", backref="survey_points")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<SurveyPoint(id={self.id}, MD={self.md}, Inc={self.inc}, Azi={self.azi})>"

class TrajectoryCalculation(Base):
    """محاسبات تراژکتوری"""
    __tablename__ = 'trajectory_calculations'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    
    # پارامترهای محاسبه
    method = Column(String(50), default='Minimum Curvature')  # روش محاسبه
    calculation_date = Column(Date, nullable=False)
    
    # ورودی‌های محاسبه
    parameters_json = Column(JSON, nullable=True)  # پارامترهای ورودی به صورت JSON
    
    # نتایج
    results_json = Column(JSON, nullable=True)  # نتایج محاسبه به صورت JSON
    target_north = Column(Float)
    target_east = Column(Float)
    target_tvd = Column(Float)
    total_hd = Column(Float)
    total_tvd = Column(Float)
    total_md = Column(Float)
    
    # اطلاعات
    calculated_by = Column(Integer, ForeignKey('users.id'))
    description = Column(Text)
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    well = relationship("Well", backref="trajectory_calculations")
    section = relationship("Section", backref="trajectory_calculations")
    calculator = relationship("User", foreign_keys=[calculated_by])
    
    def __repr__(self):
        return f"<TrajectoryCalculation(id={self.id}, method='{self.method}', date={self.calculation_date})>"

class TrajectoryPlot(Base):
    """ذخیره نمودارهای تراژکتوری"""
    __tablename__ = 'trajectory_plots'
    
    id = Column(Integer, primary_key=True)
    calculation_id = Column(Integer, ForeignKey('trajectory_calculations.id'))
    
    # نوع نمودار
    plot_type = Column(String(50))  # '2d_plan', '2d_side', '3d'
    title = Column(String(200))
    
    # داده‌های نمودار
    plot_data_json = Column(JSON)  # داده‌های نقاط
    
    # تصویر
    image_data = Column(Text)  # Base64 encoded image
    image_format = Column(String(10))  # 'png', 'jpg'
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    calculation = relationship("TrajectoryCalculation", backref="plots")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<TrajectoryPlot(id={self.id}, type='{self.plot_type}', title='{self.title}')>"

class BitReport(Base):
    """گزارش مته‌ها"""
    __tablename__ = 'bit_reports'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    report_date = Column(Date, nullable=False)
    report_name = Column(String(200))
    bit_records_json = Column(JSON)  # ذخیره رکوردهای مته
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    well = relationship("Well", backref="bit_reports")

class BHAReport(Base):
    """گزارش BHA"""
    __tablename__ = 'bha_reports'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    bha_name = Column(String(100), nullable=False)
    bha_data_json = Column(JSON)  # ذخیره پیکربندی BHA
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    well = relationship("Well", backref="bha_reports")

class DownholeEquipment(Base):
    """تجهیزات زیر سطحی"""
    __tablename__ = 'downhole_equipment'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    equipment_data_json = Column(JSON)  # ذخیره داده‌های تجهیزات
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    well = relationship("Well", backref="downhole_equipment")

class FormationReport(Base):
    """گزارش سازندها"""
    __tablename__ = 'formation_reports'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    report_name = Column(String(200))
    formations_json = Column(JSON)  # ذخیره داده‌های سازندها
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    well = relationship("Well", backref="formation_reports")
            
class LogisticsPersonnel(Base):
    """پرسنل و خدمه لجستیک"""
    __tablename__ = 'logistics_personnel'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    # اطلاعات شخصی
    name = Column(String(100), nullable=False)
    position = Column(String(100))
    company = Column(String(100))
    arrival_date = Column(Date)
    departure_date = Column(Date)
    contact_info = Column(String(200))
    remarks = Column(Text)
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="logistics_personnel")
    section = relationship("Section", backref="logistics_personnel")
    report = relationship("DailyReport", backref="logistics_personnel")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<LogisticsPersonnel(id={self.id}, name='{self.name}', position='{self.position}')>"

class ServiceCompanyPOB(Base):
    """خدمات شرکت‌ها و POB"""
    __tablename__ = 'service_company_pob'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    # اطلاعات شرکت
    company_name = Column(String(100), nullable=False)
    service_type = Column(String(100))
    personnel_count = Column(Integer, default=0)
    date_in = Column(Date)
    date_out = Column(Date)
    remarks = Column(Text)
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="service_company_pob")
    section = relationship("Section", backref="service_company_pob")
    report = relationship("DailyReport", backref="service_company_pob")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ServiceCompanyPOB(id={self.id}, company='{self.company_name}', count={self.personnel_count})>"

class FuelWaterInventory(Base):
    """موجودی سوخت و آب"""
    __tablename__ = 'fuel_water_inventory'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    report_date = Column(Date, nullable=False)
    
    # سوخت
    fuel_type = Column(String(50), default='Diesel')
    fuel_consumed = Column(Float, default=0.0)  # لیتر
    fuel_stock = Column(Float, default=0.0)  # لیتر
    fuel_received = Column(Float, default=0.0)  # لیتر
    
    # آب
    water_consumed = Column(Float, default=0.0)  # لیتر
    water_stock = Column(Float, default=0.0)  # لیتر
    water_received = Column(Float, default=0.0)  # لیتر
    
    # محاسبات
    fuel_remaining = Column(Float, default=0.0)
    water_remaining = Column(Float, default=0.0)
    days_remaining_fuel = Column(Float, default=0.0)
    days_remaining_water = Column(Float, default=0.0)
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="fuel_water_inventory")
    section = relationship("Section", backref="fuel_water_inventory")
    report = relationship("DailyReport", backref="fuel_water_inventory")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<FuelWaterInventory(id={self.id}, date={self.report_date}, fuel={self.fuel_stock}, water={self.water_stock})>"

class BulkMaterials(Base):
    """مواد عمده"""
    __tablename__ = 'bulk_materials'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    report_date = Column(Date, nullable=False)
    
    # اطلاعات ماده
    material_name = Column(String(100), nullable=False)
    unit = Column(String(50), default='kg')
    initial_stock = Column(Float, default=0.0)
    received = Column(Float, default=0.0)
    used = Column(Float, default=0.0)
    current_stock = Column(Float, default=0.0)
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="bulk_materials")
    section = relationship("Section", backref="bulk_materials")
    report = relationship("DailyReport", backref="bulk_materials")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<BulkMaterials(id={self.id}, material='{self.material_name}', stock={self.current_stock})>"

class TransportLog(Base):
    """لاگ حمل و نقل (قایق و هلیکوپتر)"""
    __tablename__ = 'transport_logs'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    log_date = Column(Date, nullable=False)
    
    # اطلاعات وسیله نقلیه
    vehicle_type = Column(String(50), nullable=False)  # 'boat' یا 'chopper'
    vehicle_name = Column(String(100), nullable=False)
    vehicle_id = Column(String(50))
    
    # زمان‌بندی
    arrival_time = Column(Time)
    departure_time = Column(Time)
    duration = Column(Float)  # ساعت
    
    # اطلاعات مسافر/بار
    passengers_in = Column(Integer, default=0)
    passengers_out = Column(Integer, default=0)
    cargo_description = Column(Text)
    
    # وضعیت
    status = Column(String(50), default='Scheduled')
    purpose = Column(String(200))
    remarks = Column(Text)
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="transport_logs")
    section = relationship("Section", backref="transport_logs")
    report = relationship("DailyReport", backref="transport_logs")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<TransportLog(id={self.id}, type='{self.vehicle_type}', name='{self.vehicle_name}', status='{self.status}')>"

class TransportNotes(Base):
    """یادداشت‌های حمل و نقل"""
    __tablename__ = 'transport_notes'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    note_date = Column(Date, nullable=False)
    
    # محتوای یادداشت
    title = Column(String(200))
    content = Column(Text, nullable=False)
    category = Column(String(50), default='General')
    priority = Column(String(20), default='Normal')  # Low, Normal, High, Critical
    
    # متادیتا
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="transport_notes")
    section = relationship("Section", backref="transport_notes")
    report = relationship("DailyReport", backref="transport_notes")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<TransportNotes(id={self.id}, date={self.note_date}, category='{self.category}')>"
        
class SafetyReport(Base):
    """Safety reports and incidents database model"""
    __tablename__ = 'safety_reports'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    # Report metadata
    report_date = Column(Date, nullable=False)
    report_type = Column(String(50), default='Daily')  # Daily, Weekly, Monthly, Incident
    title = Column(String(200))
    
    # Safety drills
    last_fire_drill = Column(Date)
    last_bop_drill = Column(Date)
    last_h2s_drill = Column(Date)
    days_without_lti = Column(Integer, default=0)
    lti_count = Column(Integer, default=0)
    near_miss_count = Column(Integer, default=0)
    
    # BOP tests
    last_rams_test = Column(Date)
    test_pressure = Column(Float, default=0.0)
    last_koomey_test = Column(Date)
    days_since_last_test = Column(Integer, default=0)
    
    # BOP stack data (JSON)
    bop_stack_json = Column(JSON)
    
    # Waste management
    recycled_volume = Column(Float, default=0.0)
    waste_ph = Column(Float, default=7.0)
    turbidity = Column(String(100))
    hardness = Column(String(100))
    cutting_volume = Column(Float, default=0.0)
    oil_content = Column(Float, default=0.0)
    waste_type = Column(String(100))
    disposal_method = Column(String(100))
    
    # Waste management history (JSON)
    waste_history_json = Column(JSON)
    
    # Other safety data
    safety_observations = Column(Text)
    incidents_json = Column(JSON)
    equipment_checks = Column(JSON)
    
    # Status
    status = Column(String(50), default='Draft')
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="safety_reports")
    section = relationship("Section", backref="safety_reports")
    report = relationship("DailyReport", backref="safety_reports")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<SafetyReport(id={self.id}, well_id={self.well_id}, date={self.report_date})>"

class SafetyIncident(Base):
    """Safety incidents database model"""
    __tablename__ = 'safety_incidents'
    
    id = Column(Integer, primary_key=True)
    safety_report_id = Column(Integer, ForeignKey('safety_reports.id'), nullable=False)
    
    # Incident details
    incident_date = Column(Date, nullable=False)
    incident_time = Column(Time, nullable=False)
    incident_type = Column(String(100), nullable=False)  # Fire, Injury, Spill, etc.
    severity = Column(String(50), default='Minor')  # Minor, Moderate, Major, Critical
    
    # Location and description
    location = Column(String(200))
    description = Column(Text, nullable=False)
    
    # Personnel involved
    personnel_involved = Column(Text)
    injuries = Column(Text)
    
    # Response and actions
    immediate_response = Column(Text)
    corrective_actions = Column(Text)
    
    # Investigation
    root_cause = Column(Text)
    investigator = Column(String(100))
    
    # Status
    status = Column(String(50), default='Open')
    resolved_date = Column(Date)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    safety_report = relationship("SafetyReport", backref="incidents")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<SafetyIncident(id={self.id}, type='{self.incident_type}', date={self.incident_date})>"

class BOPComponent(Base):
    """BOP Components database model"""
    __tablename__ = 'bop_components'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    safety_report_id = Column(Integer, ForeignKey('safety_reports.id'), nullable=True)
    
    # Component details
    component_name = Column(String(100), nullable=False)
    component_type = Column(String(50), nullable=False)  # Annular, Pipe Rams, Shear Rams, etc.
    working_pressure = Column(Float, nullable=False)  # psi
    size = Column(String(50))  # inches
    ram_type = Column(String(100))  # For rams
    manufacturer = Column(String(100))
    serial_number = Column(String(100))
    
    # Testing and maintenance
    last_test_date = Column(Date)
    next_test_due = Column(Date)
    test_pressure = Column(Float)
    test_result = Column(String(50), default='Pass')  # Pass, Fail, Needs Attention
    
    # Status
    status = Column(String(50), default='Operational')  # Operational, Under Maintenance, Out of Service
    remarks = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="bop_components")
    safety_report = relationship("SafetyReport", backref="bop_components")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<BOPComponent(id={self.id}, name='{self.component_name}', type='{self.component_type}')>"

class WasteRecord(Base):
    """Waste management records database model"""
    __tablename__ = 'waste_records'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    safety_report_id = Column(Integer, ForeignKey('safety_reports.id'), nullable=True)
    
    # Waste details
    record_date = Column(Date, nullable=False)
    waste_type = Column(String(100), nullable=False)
    volume = Column(Float, nullable=False)  # in BBL
    unit = Column(String(20), default='BBL')
    
    # Chemical properties
    ph = Column(Float)
    turbidity = Column(String(100))
    hardness = Column(String(100))
    oil_content = Column(Float)  # ppm
    
    # Disposal
    disposal_method = Column(String(100))
    disposal_date = Column(Date)
    disposal_company = Column(String(100))
    
    # Documentation
    waste_ticket_number = Column(String(100))
    manifest_number = Column(String(100))
    
    # Remarks
    remarks = Column(Text)
    
    # Status
    status = Column(String(50), default='Pending Disposal')
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="waste_records")
    safety_report = relationship("SafetyReport", backref="waste_records")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<WasteRecord(id={self.id}, type='{self.waste_type}', volume={self.volume})>"

class ServiceCompany(Base):
    """Service Company Database Model"""
    __tablename__ = 'service_companies'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    company_name = Column(String(200), nullable=False)
    service_type = Column(String(100))
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    contact_person = Column(String(100))
    contact_phone = Column(String(50))
    contact_email = Column(String(100))
    equipment_used = Column(Text)
    personnel_count = Column(Integer, default=1)
    status = Column(String(50), default='Active')
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="service_companies")
    section = relationship("Section", backref="service_companies")
    report = relationship("DailyReport", backref="service_companies")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ServiceCompany(id={self.id}, name='{self.company_name}', type='{self.service_type}')>"

class ServiceNote(Base):
    """Service Note Database Model"""
    __tablename__ = 'service_notes'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    note_number = Column(Integer, nullable=False)
    note_type = Column(String(50), default='General')
    content = Column(Text, nullable=False)
    priority = Column(String(20), default='Medium')
    status = Column(String(50), default='Active')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="service_notes")
    section = relationship("Section", backref="service_notes")
    report = relationship("DailyReport", backref="service_notes")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ServiceNote(id={self.id}, note_number={self.note_number}, type='{self.note_type}')>"

class MaterialRequest(Base):
    """Material Request Database Model"""
    __tablename__ = 'material_requests'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    request_date = Column(Date, nullable=False)
    requested_items = Column(Text)
    requested_quantity = Column(Float, default=0.0)
    requested_unit = Column(String(50), default='units')
    outstanding_items = Column(Text)
    outstanding_quantity = Column(Float, default=0.0)
    received_items = Column(Text)
    received_quantity = Column(Float, default=0.0)
    received_date = Column(Date)
    backload_items = Column(Text)
    backload_quantity = Column(Float, default=0.0)
    backload_date = Column(Date)
    remarks = Column(Text)
    status = Column(String(50), default='Pending')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="material_requests")
    section = relationship("Section", backref="material_requests")
    report = relationship("DailyReport", backref="material_requests")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<MaterialRequest(id={self.id}, date={self.request_date}, status='{self.status}')>"

class EquipmentLog(Base):
    """Equipment Log Database Model"""
    __tablename__ = 'equipment_logs'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    equipment_type = Column(String(100))
    equipment_name = Column(String(200), nullable=False)
    equipment_id = Column(String(100))
    manufacturer = Column(String(100))
    serial_number = Column(String(100))
    service_date = Column(Date)
    service_type = Column(String(100))
    service_provider = Column(String(200))
    hours_worked = Column(Float, default=0.0)
    status = Column(String(50), default='Operational')
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="equipment_logs")
    section = relationship("Section", backref="equipment_logs")
    report = relationship("DailyReport", backref="equipment_logs")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<EquipmentLog(id={self.id}, name='{self.equipment_name}', type='{self.equipment_type}')>"

class SevenDaysLookahead(Base):
    """Seven Days Lookahead planning"""
    __tablename__ = 'seven_days_lookahead'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    # Planning info
    plan_date = Column(Date, nullable=False)
    day_number = Column(Integer, nullable=False)  # 1-7
    activity = Column(Text, nullable=False)
    tools = Column(Text)
    responsible = Column(String(200))
    remarks = Column(Text)
    
    # Status
    status = Column(String(50), default='Planned')
    priority = Column(String(20), default='Normal')
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="lookahead_plans")
    section = relationship("Section", backref="lookahead_plans")
    report = relationship("DailyReport", backref="lookahead_plans")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<SevenDaysLookahead(id={self.id}, day={self.day_number}, activity='{self.activity[:30]}...')>"

class NPTReport(Base):
    """Non-Productive Time reports"""
    __tablename__ = 'npt_reports'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'), nullable=True)
    
    # NPT details
    npt_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_hours = Column(Float, nullable=False)
    
    # Classification
    npt_category = Column(String(100), nullable=False)  # Weather, Equipment, Waiting, etc.
    npt_code = Column(String(50), nullable=False)       # WOC, WOW, EQP, etc.
    npt_description = Column(Text, nullable=False)
    
    # Responsible
    responsible_party = Column(String(200))
    department = Column(String(100))
    
    # Impact assessment
    cost_impact = Column(Float, default=0.0)
    delay_days = Column(Float, default=0.0)
    safety_incident = Column(Boolean, default=False)
    
    # Resolution
    root_cause = Column(Text)
    corrective_action = Column(Text)
    prevention_plan = Column(Text)
    
    # Status
    status = Column(String(50), default='Active')
    resolved_date = Column(Date)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="npt_reports")
    section = relationship("Section", backref="npt_reports")
    report = relationship("DailyReport", backref="npt_reports")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<NPTReport(id={self.id}, code='{self.npt_code}', duration={self.duration_hours})>"

class ActivityCode(Base):
    """Activity code management"""
    __tablename__ = 'activity_codes'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    
    # Code hierarchy
    main_phase = Column(String(100), nullable=False)  # Drilling, Tripping, Casing, etc.
    main_code = Column(String(50), nullable=False)    # DRL, TRP, CAS, etc.
    sub_code = Column(String(50), nullable=False)     # DRL-01, TRP-01, etc.
    
    # Code details
    code_name = Column(String(200), nullable=False)
    code_description = Column(Text)
    is_productive = Column(Boolean, default=True)
    is_npt = Column(Boolean, default=False)
    
    # Color coding for charts
    color_code = Column(String(10), default='#0078D4')
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    total_hours = Column(Float, default=0.0)
    last_used = Column(Date)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="activity_codes")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ActivityCode(id={self.id}, code='{self.sub_code}', name='{self.code_name}')>"

class TimeDepthData(Base):
    """Time vs Depth data for charts"""
    __tablename__ = 'time_depth_data'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    
    # Data points
    timestamp = Column(DateTime, nullable=False)
    depth = Column(Float, nullable=False)  # TVD or MD
    
    # Additional data
    activity_code = Column(String(50))
    rop = Column(Float)  # Rate of Penetration
    wob = Column(Float)  # Weight on Bit
    rpm = Column(Float)  # Revolutions per minute
    torque = Column(Float)
    
    # Calculated fields
    cumulative_time = Column(Float)  # Hours from spud
    daily_progress = Column(Float)   # Depth drilled that day
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="time_depth_data")
    section = relationship("Section", backref="time_depth_data")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<TimeDepthData(id={self.id}, time={self.timestamp}, depth={self.depth})>"

class ROPAnalysis(Base):
    """ROP Analysis and charts"""
    __tablename__ = 'rop_analysis'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey('wells.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    
    # Analysis parameters
    analysis_date = Column(Date, nullable=False)
    start_depth = Column(Float, nullable=False)
    end_depth = Column(Float, nullable=False)
    
    # ROP calculations
    avg_rop = Column(Float)
    max_rop = Column(Float)
    min_rop = Column(Float)
    rop_std_dev = Column(Float)
    
    # Factors affecting ROP
    formation_type = Column(String(100))
    bit_type = Column(String(50))
    hydraulics_efficiency = Column(Float)
    drill_string_config = Column(String(200))
    
    # Chart data (JSON format)
    rop_chart_data = Column(JSON)
    depth_chart_data = Column(JSON)
    
    # Recommendations
    recommendations = Column(Text)
    efficiency_score = Column(Integer)  # 0-100
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    well = relationship("Well", backref="rop_analysis")
    section = relationship("Section", backref="rop_analysis")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ROPAnalysis(id={self.id}, avg_rop={self.avg_rop}, depth_range={self.start_depth}-{self.end_depth})>"

class ExportTemplate(Base):
    """Export templates database model"""
    __tablename__ = 'export_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    template_type = Column(String(50))  # 'daily', 'eowr', 'batch', 'custom'
    description = Column(Text)
    
    # Template configuration
    well_selection = Column(JSON)  # Selected wells criteria
    report_selection = Column(JSON)  # Selected reports
    date_range = Column(JSON)  # Date range settings
    format_settings = Column(JSON)  # Format and output settings
    options = Column(JSON)  # Additional options
    
    # Template content
    layout_config = Column(JSON)  # Report layout configuration
    styling = Column(JSON)  # CSS/styling settings
    headers_footers = Column(JSON)  # Header/footer configuration
    
    # Metadata
    is_default = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    shared_with = Column(JSON)  # List of user IDs this template is shared with
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ExportTemplate(id={self.id}, name='{self.name}', type='{self.template_type}')>"
 
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    email = Column(String(100))
    role = Column(String(50), default="user")
    department = Column(String(100))
    phone = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
 
class DatabaseManager:
    """Manages database connection and operations"""

    def __init__(self):
        self.engine = None
        self.Session = None
        self.db_path = "drillmaster.db"

    def initialize(self):
        """Initialize database connection"""
        try:
            # Create engine with SQLite
            self.engine = create_engine(
                f"sqlite:///{self.db_path}",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )

            # Create session factory
            self.Session = sessionmaker(bind=self.engine)

            # Create tables
            Base.metadata.create_all(self.engine)

            # Create default data
            self.create_default_data()

            logger.info("Database initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return False
    
    def create_daily_report_new(self, report_data: dict):
        """ایجاد گزارش روزانه با ساختار جدید"""
        session = self.create_session()
        try:
            # اعتبارسنجی
            if not report_data.get('section_id'):
                raise Exception("Section ID is required")
                
            if not report_data.get('report_date'):
                raise Exception("Report date is required")
            
            # محاسبه شماره گزارش
            section_id = report_data['section_id']
            last_report = session.query(DailyReport).filter(
                DailyReport.section_id == section_id
            ).order_by(DailyReport.report_number.desc()).first()
            
            report_number = report_data.get('report_number', 1)
            if not report_data.get('report_number'):
                report_number = 1
                if last_report:
                    report_number = last_report.report_number + 1
            
            # ساخت عنوان
            section = session.query(Section).get(section_id)
            well = session.query(Well).get(section.well_id) if section else None
            project = session.query(Project).get(well.project_id) if well else None
            
            report_date = report_data['report_date']
            if isinstance(report_date, str):
                report_date = datetime.strptime(report_date, "%Y-%m-%d").date()
            
            report_title = f"{report_number:02d} Daily Report, {project.name if project else 'Unknown'}, {report_date}"
            
            # ایجاد گزارش
            new_report = DailyReport(
                well_id=report_data.get('well_id', section.well_id if section else None),
                section_id=section_id,
                report_date=report_date,
                report_number=report_number,
                report_title=report_title,
                status='Draft',
                created_by=report_data.get('created_by')
            )
            
            # کپی از روز قبل اگر خواسته شده
            if report_data.get('copy_previous', False):
                self._copy_from_previous_report(session, new_report, section_id, report_date)  # <-- این خط OK است
            
            session.add(new_report)
            session.commit()
            
            logger.info(f"Daily report created: ID {new_report.id}, Number {report_number}")
            
            return {
                'id': new_report.id,
                'report_number': report_number,
                'section_id': section_id
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating daily report: {e}")
            return None
        finally:
            session.close()
    
    def _copy_report_data(self, source_report, target_report):
        """کپی داده‌ها از یک گزارش به گزارش دیگر"""
        # کپی mud data بدون استاک
        if source_report.mud_data:
            mud_data = source_report.mud_data.copy()
            # حذف فیلدهای استاک
            stock_fields = ['initial_stock', 'received', 'consumed', 'final_stock']
            for field in stock_fields:
                mud_data.pop(field, None)
            target_report.mud_data = mud_data
        
        # کپی سایر داده‌ها
        for field in ['drilling_data', 'equipment_data', 'downhole_data', 
                     'trajectory_data', 'logistics_data', 'safety_data',
                     'services_data', 'planning_data', 'export_data', 
                     'analysis_data']:
            source_data = getattr(source_report, field)
            if source_data:
                setattr(target_report, field, source_data.copy())
                
    def create_session(self) -> Session:
        """Create a new database session"""
        return self.Session()

    def create_default_data(self):
        """Create default data if database is empty"""
        session = self.create_session()
        try:
            # Check if users exist
            user_count = session.query(User).count()
            if user_count == 0:
                logger.info("Creating default users...")

                # Create default users
                users = [
                    User(
                        username="admin",
                        password_hash="admin123",
                        full_name="Administrator",
                        email="admin@drillmaster.com",
                        role="admin",
                        department="Management",
                    ),
                    User(
                        username="user",
                        password_hash="user123",
                        full_name="Regular User",
                        email="user@drillmaster.com",
                        role="user",
                        department="Operations",
                    ),
                ]

                for user in users:
                    session.add(user)

                # Create default company, project, and well
                company = Company(
                    name="Default Company",
                    code="DC001",
                    address="123 Industry St, Houston, TX",
                    contact_person="John Smith",
                    contact_email="info@company.com",
                    contact_phone="+1-234-567-8900",
                )
                session.add(company)

                project = Project(
                    company=company,
                    name="Default Project",
                    code="DP001",
                    location="Gulf of Mexico",
                    start_date=datetime(2024, 1, 1).date(),
                    status="Active",
                    manager="Jane Doe",
                    budget=5000000.00,
                    currency="USD",
                )
                session.add(project)

                well = Well(
                    project=project,
                    name="Default Well",
                    code="DW001",
                    field_name="Default Field",
                    location="Block A-12",
                    coordinates="28.5, -88.5",
                    elevation=10.5,
                    water_depth=1500.0,
                    spud_date=datetime(2024, 3, 1).date(),
                    target_depth=3500.0,
                    status="Planning",
                    well_type="Exploration",
                    purpose="Oil Production",
                    well_type_field="Offshore",
                )
                session.add(well)

                session.commit()
                logger.info("✅ Default data created successfully")

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error creating default data: {str(e)}")
        finally:
            session.close()

    def authenticate_user(self, username: str, password: str):
        """Authenticate user - نسخه اصلاح شده نهایی"""
        session = self.create_session()
        try:
            user = (
                session.query(User)
                .filter(
                    User.username == username,
                    User.password_hash == password,
                    User.is_active == True,
                )
                .first()
            )

            if user:
                # ابتدا داده‌های مورد نیاز را ذخیره کن
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name if user.full_name else user.username,
                    "role": user.role if user.role else "user",
                    "email": (
                        user.email if user.email else f"{user.username}@drillmaster.com"
                    ),
                }

                # سپس last_login را به‌روزرسانی کن
                try:
                    user.last_login = datetime.utcnow()
                    session.commit()
                except Exception as update_error:
                    logger.error(f"Error updating last_login: {update_error}")
                    session.rollback()
                    # اما همچنان user_data را برمی‌گردانیم

                session.close()  # بستن session قبل از بازگشت
                return type("UserObject", (), user_data)()  # ایجاد یک object ساده
            return None

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
        finally:
            try:
                session.close()
            except:
                pass

    def get_hierarchy(self):
        """Get complete hierarchy: Company > Project > Well"""
        session = self.create_session()
        try:
            companies = session.query(Company).all()

            hierarchy = []
            for company in companies:
                company_data = {
                    "id": company.id,
                    "name": company.name,
                    "code": company.code,
                    "projects": [],
                }

                for project in company.projects:
                    project_data = {
                        "id": project.id,
                        "name": project.name,
                        "code": project.code,
                        "wells": [],
                    }

                    for well in project.wells:
                        well_data = {
                            "id": well.id,
                            "name": well.name,
                            "code": well.code,
                            "status": well.status,
                        }
                        project_data["wells"].append(well_data)

                    company_data["projects"].append(project_data)

                hierarchy.append(company_data)

            return hierarchy

        except Exception as e:
            logger.error(f"Error getting hierarchy: {str(e)}")
            return []
        finally:
            session.close()

    def get_all_projects(self):
        """Get all projects"""
        session = self.create_session()
        try:
            projects = session.query(Project).all()
            return [{"id": p.id, "name": p.name, "code": p.code} for p in projects]
        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            return []
        finally:
            session.close()

    def get_well_by_id(self, well_id: int):
        """Get well by ID"""
        session = self.create_session()
        try:
            well = session.query(Well).filter(Well.id == well_id).first()
            if well:
                return {
                    "id": well.id,
                    "project_id": well.project_id,
                    "name": well.name,
                    "code": well.code,
                    "well_type": well.well_type,
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
                    "field_name": well.field_name,
                    "location": well.location,
                    "coordinates": well.coordinates,
                    "elevation": well.elevation,
                    "water_depth": well.water_depth,
                    "spud_date": well.spud_date,
                    "target_depth": well.target_depth,
                    "status": well.status,
                    "purpose": well.purpose,
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
                }
            return None
        except Exception as e:
            logger.error(f"Error getting well: {str(e)}")
            return None
        finally:
            session.close()

    def save_well(self, well_data: dict):
        """Save well data with all fields"""
        session = self.create_session()
        try:
            if "id" in well_data and well_data["id"]:
                # Update existing well
                well = session.query(Well).filter(Well.id == well_data["id"]).first()
                if well:
                    # Update all fields
                    well.name = well_data.get("name", well.name)
                    well.code = well_data.get("code", well.code)
                    well.well_type = well_data.get("well_type", well.well_type)
                    well.well_type_field = well_data.get(
                        "well_type_field", well.well_type_field
                    )
                    well.section_name = well_data.get("section_name", well.section_name)
                    well.client = well_data.get("client", well.client)
                    well.client_rep = well_data.get("client_rep", well.client_rep)
                    well.operator = well_data.get("operator", well.operator)
                    well.project_name = well_data.get("project", well.project_name)
                    well.rig_name = well_data.get("rig_name", well.rig_name)
                    well.drilling_contractor = well_data.get(
                        "drilling_contractor", well.drilling_contractor
                    )
                    well.report_no = well_data.get("report_no", well.report_no)
                    well.rig_type = well_data.get("rig_type", well.rig_type)
                    well.well_shape = well_data.get("well_shape", well.well_shape)
                    well.gle_msl = well_data.get("gle_msl", well.gle_msl)
                    well.rte_msl = well_data.get("rte_msl", well.rte_msl)
                    well.gle_rte = well_data.get("gle_rte", well.gle_rte)
                    well.estimated_final_depth = well_data.get(
                        "estimated_depth", well.estimated_final_depth
                    )
                    well.water_depth = well_data.get("water_depth", well.water_depth)
                    well.derrick_height = well_data.get(
                        "derrick_height", well.derrick_height
                    )
                    well.lta_day = well_data.get("lta_day", well.lta_day)
                    well.actual_rig_days = well_data.get(
                        "actual_rig_days", well.actual_rig_days
                    )
                    well.rig_heading = well_data.get("rig_heading", well.rig_heading)
                    well.kop1 = well_data.get("kop1", well.kop1)
                    well.kop2 = well_data.get("kop2", well.kop2)
                    well.formation = well_data.get("formation", well.formation)
                    well.coordinates = well_data.get("coordinates", well.coordinates)
                    well.latitude = well_data.get("latitude", well.latitude)
                    well.longitude = well_data.get("longitude", well.longitude)
                    well.northing = well_data.get("northing", well.northing)
                    well.easting = well_data.get("easting", well.easting)
                    well.field_name = well_data.get("field_name", well.field_name)
                    well.location = well_data.get("location", well.location)
                    well.elevation = well_data.get("elevation", well.elevation)
                    well.target_depth = well_data.get("target_depth", well.target_depth)
                    well.status = well_data.get("status", well.status)
                    well.purpose = well_data.get("purpose", well.purpose)

                    # Parse dates
                    if well_data.get("spud_date"):
                        well.spud_date = datetime.strptime(
                            well_data["spud_date"], "%Y-%m-%d"
                        ).date()
                    if well_data.get("start_hole_date"):
                        well.start_hole_date = datetime.strptime(
                            well_data["start_hole_date"], "%Y-%m-%d"
                        ).date()
                    if well_data.get("rig_move_date"):
                        well.rig_move_date = datetime.strptime(
                            well_data["rig_move_date"], "%Y-%m-%d"
                        ).date()
                    if well_data.get("report_date"):
                        well.report_date = datetime.strptime(
                            well_data["report_date"], "%Y-%m-%d"
                        ).date()

                    well.operation_manager = well_data.get(
                        "operation_manager", well.operation_manager
                    )
                    well.superintendent = well_data.get(
                        "superintendent", well.superintendent
                    )
                    well.supervisor_day = well_data.get(
                        "supervisor_day", well.supervisor_day
                    )
                    well.supervisor_night = well_data.get(
                        "supervisor_night", well.supervisor_night
                    )
                    well.geologist1 = well_data.get("geologist1", well.geologist1)
                    well.geologist2 = well_data.get("geologist2", well.geologist2)
                    well.tool_pusher_day = well_data.get(
                        "tool_pusher_day", well.tool_pusher_day
                    )
                    well.tool_pusher_night = well_data.get(
                        "tool_pusher_night", well.tool_pusher_night
                    )
                    well.objectives = well_data.get("objectives", well.objectives)
                    well.updated_at = datetime.utcnow()
            else:
                # Create new well
                well = Well(
                    project_id=well_data.get("project_id", 1),
                    name=well_data["name"],
                    code=well_data.get("code", ""),
                    well_type=well_data.get("well_type", ""),
                    well_type_field=well_data.get("well_type_field", "Onshore"),
                    section_name=well_data.get("section_name", ""),
                    client=well_data.get("client", ""),
                    client_rep=well_data.get("client_rep", ""),
                    operator=well_data.get("operator", ""),
                    project_name=well_data.get("project", ""),
                    rig_name=well_data.get("rig_name", ""),
                    drilling_contractor=well_data.get("drilling_contractor", ""),
                    report_no=well_data.get("report_no", ""),
                    rig_type=well_data.get("rig_type", ""),
                    well_shape=well_data.get("well_shape", ""),
                    field_name=well_data.get("field_name", ""),
                    location=well_data.get("location", ""),
                    coordinates=well_data.get("coordinates", ""),
                    elevation=well_data.get("elevation", 0.0),
                    water_depth=well_data.get("water_depth", 0.0),
                    target_depth=well_data.get("target_depth", 0.0),
                    status=well_data.get("status", "Planning"),
                    purpose=well_data.get("purpose", ""),
                    gle_msl=well_data.get("gle_msl", 0.0),
                    rte_msl=well_data.get("rte_msl", 0.0),
                    gle_rte=well_data.get("gle_rte", 0.0),
                    estimated_final_depth=well_data.get("estimated_depth", 0.0),
                    derrick_height=well_data.get("derrick_height", 0),
                    lta_day=well_data.get("lta_day", 0),
                    actual_rig_days=well_data.get("actual_rig_days", 0),
                    rig_heading=well_data.get("rig_heading", 0.0),
                    kop1=well_data.get("kop1", 0.0),
                    kop2=well_data.get("kop2", 0.0),
                    formation=well_data.get("formation", ""),
                    latitude=well_data.get("latitude", 0.0),
                    longitude=well_data.get("longitude", 0.0),
                    northing=well_data.get("northing", 0.0),
                    easting=well_data.get("easting", 0.0),
                    operation_manager=well_data.get("operation_manager", ""),
                    superintendent=well_data.get("superintendent", ""),
                    supervisor_day=well_data.get("supervisor_day", ""),
                    supervisor_night=well_data.get("supervisor_night", ""),
                    geologist1=well_data.get("geologist1", ""),
                    geologist2=well_data.get("geologist2", ""),
                    tool_pusher_day=well_data.get("tool_pusher_day", ""),
                    tool_pusher_night=well_data.get("tool_pusher_night", ""),
                    objectives=well_data.get("objectives", ""),
                )

                # Parse dates
                if well_data.get("spud_date"):
                    well.spud_date = datetime.strptime(
                        well_data["spud_date"], "%Y-%m-%d"
                    ).date()
                if well_data.get("start_hole_date"):
                    well.start_hole_date = datetime.strptime(
                        well_data["start_hole_date"], "%Y-%m-%d"
                    ).date()
                if well_data.get("rig_move_date"):
                    well.rig_move_date = datetime.strptime(
                        well_data["rig_move_date"], "%Y-%m-%d"
                    ).date()
                if well_data.get("report_date"):
                    well.report_date = datetime.strptime(
                        well_data["report_date"], "%Y-%m-%d"
                    ).date()

                session.add(well)

            session.commit()
            logger.info("Well saved successfully")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving well: {str(e)}")
            return False
        finally:
            session.close()

    def delete_well(self, well_id: int):
        """Delete well"""
        session = self.create_session()
        try:
            well = session.query(Well).filter(Well.id == well_id).first()
            if well:
                session.delete(well)
                session.commit()
                logger.info(f"Well {well_id} deleted successfully")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting well: {str(e)}")
            return False
        finally:
            session.close()

    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def _save_time_logs(self, session, report_id: int, time_logs: list, model_class):
        """ذخیره لاگ‌های زمانی"""
        # Delete existing logs
        existing_logs = (
            session.query(model_class).filter(model_class.report_id == report_id).all()
        )
        for log in existing_logs:
            session.delete(log)

        # Add new logs
        for log_data in time_logs:
            time_log = model_class(
                report_id=report_id,
                time_from=log_data.get("time_from"),
                time_to=log_data.get("time_to"),
                duration=log_data.get("duration", 0.0),
                main_phase=log_data.get("main_phase"),
                main_code=log_data.get("main_code"),
                sub_code=log_data.get("sub_code"),
                status=log_data.get("status"),
                is_npt=log_data.get("is_npt", False),
                activity_description=log_data.get("activity_description", ""),
            )
            session.add(time_log)

    def get_daily_report_by_id(self, report_id: int):
        """دریافت گزارش روزانه با ID"""
        session = self.create_session()
        try:
            report = (
                session.query(DailyReport).filter(DailyReport.id == report_id).first()
            )
            if report:
                return {
                    "id": report.id,
                    "well_id": report.well_id,
                    "section_id": report.section_id,  # <-- این خط را اضافه کنید
                    "report_date": report.report_date,
                    "report_number": report.report_number,  # <-- این خط را اضافه کنید
                    "rig_day": report.rig_day,
                    "depth_0000": report.depth_0000,
                    "depth_0600": report.depth_0600,
                    "depth_2400": report.depth_2400,
                    "summary": report.summary,
                    "status": report.status,
                    "created_at": report.created_at,
                    "updated_at": report.updated_at,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting daily report: {str(e)}")
            return None
        finally:
            session.close()
    def get_daily_reports_by_well(self, well_id: int):
        """دریافت همه گزارش‌های یک چاه"""
        session = self.create_session()
        try:
            reports = (
                session.query(DailyReport)
                .filter(DailyReport.well_id == well_id)
                .order_by(DailyReport.report_date.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "report_date": r.report_date,
                    "rig_day": r.rig_day,
                    "depth_2400": r.depth_2400,
                    "summary": (
                        r.summary[:100] + "..."
                        if r.summary and len(r.summary) > 100
                        else (r.summary or "")
                    ),
                    "status": r.status,
                }
                for r in reports
            ]
        except Exception as e:
            logger.error(f"Error getting daily reports for well {well_id}: {str(e)}")
            return []
        finally:
            session.close()

    def save_time_logs_for_report(self, report_id: int, time_logs: list, is_morning: bool = False):
        """ذخیره لاگ‌های زمانی با پشتیبانی 24:00"""
        session = self.create_session()
        try:
            # حذف لاگ‌های قبلی
            if is_morning:
                existing = session.query(TimeLogMorning).filter(
                    TimeLogMorning.report_id == report_id
                ).all()
                model_class = TimeLogMorning
            else:
                existing = session.query(TimeLog24H).filter(
                    TimeLog24H.report_id == report_id
                ).all()
                model_class = TimeLog24H
            
            for log in existing:
                session.delete(log)
            
            # ذخیره لاگ‌های جدید
            for log_data in time_logs:
                # جدا کردن flag 24:00 از زمان
                from_time = log_data.get("time_from")
                to_time = log_data.get("time_to")
                
                # تنظیم flagها برای 24:00
                is_from_2400 = False
                is_to_2400 = False
                
                # اگر زمان 24:00 است
                if isinstance(from_time, str) and from_time == "24:00":
                    is_from_2400 = True
                    from_time = time(0, 0)  # به صورت 00:00 ذخیره می‌شود
                elif isinstance(from_time, time) and from_time.hour == 0 and from_time.minute == 0:
                    # بررسی کنید آیا واقعاً 24:00 است یا 00:00
                    is_from_2400 = log_data.get("is_from_2400", False)
                
                if isinstance(to_time, str) and to_time == "24:00":
                    is_to_2400 = True
                    to_time = time(0, 0)  # به صورت 00:00 ذخیره می‌شود
                elif isinstance(to_time, time) and to_time.hour == 0 and to_time.minute == 0:
                    is_to_2400 = log_data.get("is_to_2400", False)
                
                # ایجاد شیء جدید
                log_obj = model_class(
                    report_id=report_id,
                    time_from=from_time,
                    time_to=to_time,
                    is_from_2400=is_from_2400,  # 🆕
                    is_to_2400=is_to_2400,      # 🆕
                    duration=log_data.get("duration", 0.0),
                    main_phase=log_data.get("main_phase"),
                    main_code=log_data.get("main_code"),
                    sub_code=log_data.get("sub_code"),
                    status=log_data.get("status"),
                    is_npt=log_data.get("is_npt", False),
                    activity_description=log_data.get("activity_description", "")
                )
                session.add(log_obj)
            
            session.commit()
            logger.info(f"Saved {len(time_logs)} time logs for report {report_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving time logs: {e}")
            return False
        finally:
            session.close()
    
    def get_time_logs_24h(self, report_id: int):
        """دریافت لاگ‌های 24 ساعته با پشتیبانی 24:00"""
        session = self.create_session()
        try:
            logs = session.query(TimeLog24H).filter(
                TimeLog24H.report_id == report_id
            ).order_by(
                TimeLog24H.time_from,
                TimeLog24H.is_from_2400.desc()  # 24:00 در انتها
            ).all()
            
            return [
                {
                    "id": l.id,
                    "time_from": l.time_from,
                    "time_to": l.time_to,
                    "is_from_2400": l.is_from_2400,  # 🆕
                    "is_to_2400": l.is_to_2400,      # 🆕
                    "duration": l.duration,
                    "main_phase": l.main_phase,
                    "main_code": l.main_code,
                    "sub_code": l.sub_code,
                    "status": l.status,
                    "is_npt": l.is_npt,
                    "activity_description": l.activity_description,
                }
                for l in logs
            ]
        except Exception as e:
            logger.error(f"Error getting 24h time logs: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_time_logs_morning(self, report_id: int):
        """دریافت لاگ‌های صبح با پشتیبانی 24:00"""
        session = self.create_session()
        try:
            logs = session.query(TimeLogMorning).filter(
                TimeLogMorning.report_id == report_id
            ).order_by(
                TimeLogMorning.time_from,
                TimeLogMorning.is_from_2400.desc()  # 24:00 در انتها
            ).all()
            
            return [
                {
                    "id": l.id,
                    "time_from": l.time_from,
                    "time_to": l.time_to,
                    "is_from_2400": l.is_from_2400,  # 🆕
                    "is_to_2400": l.is_to_2400,      # 🆕
                    "duration": l.duration,
                    "main_phase": l.main_phase,
                    "main_code": l.main_code,
                    "sub_code": l.sub_code,
                    "status": l.status,
                    "is_npt": l.is_npt,
                    "activity_description": l.activity_description,
                }
                for l in logs
            ]
        except Exception as e:
            logger.error(f"Error getting morning time logs: {str(e)}")
            return []
        finally:
            session.close()
    
    def save_daily_report(self, report_data: dict):
        """ذخیره گزارش روزانه با پشتیبانی 24:00"""
        session = self.create_session()
        try:
            if "id" in report_data and report_data["id"]:
                # Update existing report
                report = session.query(DailyReport).filter(
                    DailyReport.id == report_data["id"]
                ).first()
                if report:
                    # به‌روزرسانی فیلدها
                    report.report_date = report_data.get("report_date", report.report_date)
                    report.report_number = report_data.get("report_number", report.report_number)
                    report.section_id = report_data.get("section_id", report.section_id)
                    report.summary = report_data.get("summary", report.summary)
                    report.status = report_data.get("status", report.status)
                    report.updated_at = datetime.utcnow()
                    
                    # ذخیره لاگ‌های زمانی
                    if "time_logs_24h" in report_data:
                        self.save_time_logs_for_report(
                            report.id, 
                            report_data["time_logs_24h"], 
                            is_morning=False
                        )
                    
                    if "time_logs_morning" in report_data:
                        self.save_time_logs_for_report(
                            report.id, 
                            report_data["time_logs_morning"], 
                            is_morning=True
                        )
                    
                    session.commit()
                    return report.id
            else:
                # Create new report
                report = DailyReport(
                    well_id=report_data["well_id"],
                    section_id=report_data.get("section_id"),
                    report_date=report_data["report_date"],
                    report_number=report_data.get("report_number", 1),
                    summary=report_data.get("summary", ""),
                    status=report_data.get("status", "Draft"),
                    created_by=report_data.get("created_by")
                )
                session.add(report)
                session.flush()  # Get the ID
                
                # ذخیره لاگ‌های زمانی
                if "time_logs_24h" in report_data:
                    self.save_time_logs_for_report(
                        report.id, 
                        report_data["time_logs_24h"], 
                        is_morning=False
                    )
                
                if "time_logs_morning" in report_data:
                    self.save_time_logs_for_report(
                        report.id, 
                        report_data["time_logs_morning"], 
                        is_morning=True
                    )
                
                session.commit()
                return report.id
                
            return None

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving daily report: {str(e)}")
            return None
        finally:
            session.close()
            
    def get_time_logs_morning(self, report_id: int):
        """دریافت لاگ‌های صبح یک گزارش"""
        session = self.create_session()
        try:
            logs = (
                session.query(TimeLogMorning)
                .filter(TimeLogMorning.report_id == report_id)
                .order_by(TimeLogMorning.time_from)
                .all()
            )
            return [
                {
                    "id": l.id,
                    "time_from": l.time_from,
                    "time_to": l.time_to,
                    "duration": l.duration,
                    "main_phase": l.main_phase,
                    "main_code": l.main_code,
                    "sub_code": l.sub_code,
                    "status": l.status,
                    "is_npt": l.is_npt,
                    "activity_description": l.activity_description,
                }
                for l in logs
            ]
        except Exception as e:
            logger.error(f"Error getting morning time logs: {str(e)}")
            return []
        finally:
            session.close()

    def delete_daily_report(self, report_id: int):
        """حذف گزارش روزانه"""
        session = self.create_session()
        try:
            report = (
                session.query(DailyReport).filter(DailyReport.id == report_id).first()
            )
            if report:
                session.delete(report)
                session.commit()
                logger.info(f"Daily report {report_id} deleted")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting daily report: {str(e)}")
            return False
        finally:
            session.close()

    def save_mud_report(self, data: dict):
        """ذخیره گزارش گل"""
        session = self.create_session()
        try:
            # بررسی وجود رکورد
            existing = (
                session.query(MudReport)
                .filter(
                    MudReport.well_id == data["well_id"],
                    MudReport.report_date == data["report_date"],
                )
                .first()
            )

            if existing:
                # به‌روزرسانی
                for key, value in data.items():
                    if hasattr(existing, key) and key not in [
                        "id",
                        "well_id",
                        "report_date",
                    ]:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # ایجاد جدید
                new_report = MudReport(**data)
                session.add(new_report)
                session.flush()
                record_id = new_report.id

            session.commit()
            logger.info(f"Mud report saved/updated: ID {record_id}")
            return record_id

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving mud report: {e}")
            return None
        finally:
            session.close()

    def save_cement_report(self, data: dict):
        """ذخیره گزارش سیمان"""
        session = self.create_session()
        try:
            # بررسی وجود رکورد
            existing = (
                session.query(CementReport)
                .filter(
                    CementReport.well_id == data["well_id"],
                    CementReport.report_date == data["report_date"],
                    CementReport.report_name == data["report_name"],
                )
                .first()
            )

            if existing:
                # به‌روزرسانی
                for key, value in data.items():
                    if hasattr(existing, key) and key not in [
                        "id",
                        "well_id",
                        "report_date",
                        "report_name",
                    ]:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # ایجاد جدید
                new_report = CementReport(**data)
                session.add(new_report)
                session.flush()
                record_id = new_report.id

            session.commit()
            logger.info(f"Cement report saved/updated: ID {record_id}")
            return record_id

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving cement report: {e}")
            return None
        finally:
            session.close()

    def save_casing_report(self, data: dict):
        """ذخیره گزارش کیسینگ"""
        session = self.create_session()
        try:
            # بررسی وجود رکورد
            existing = (
                session.query(CasingReport)
                .filter(
                    CasingReport.well_id == data["well_id"],
                    CasingReport.report_date == data["report_date"],
                    CasingReport.report_name == data["report_name"],
                )
                .first()
            )

            if existing:
                # به‌روزرسانی
                for key, value in data.items():
                    if hasattr(existing, key) and key not in [
                        "id",
                        "well_id",
                        "report_date",
                        "report_name",
                    ]:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # ایجاد جدید
                new_report = CasingReport(**data)
                session.add(new_report)
                session.flush()
                record_id = new_report.id

            session.commit()
            logger.info(f"Casing report saved/updated: ID {record_id}")
            return record_id

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving casing report: {e}")
            return None
        finally:
            session.close()

    def save_wellbore_schematic(self, data: dict):
        """ذخیره شماتیک چاه"""
        session = self.create_session()
        try:
            # بررسی وجود رکورد
            existing = (
                session.query(WellboreSchematic)
                .filter(
                    WellboreSchematic.well_id == data["well_id"],
                    WellboreSchematic.report_date == data["report_date"],
                )
                .first()
            )

            if existing:
                # به‌روزرسانی
                for key, value in data.items():
                    if hasattr(existing, key) and key not in [
                        "id",
                        "well_id",
                        "report_date",
                    ]:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # ایجاد جدید
                new_schematic = WellboreSchematic(**data)
                session.add(new_schematic)
                session.flush()
                record_id = new_schematic.id

            session.commit()
            logger.info(f"Wellbore schematic saved/updated: ID {record_id}")
            return record_id

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving wellbore schematic: {e}")
            return None
        finally:
            session.close()

    def get_mud_report(self, well_id: int, report_date: date = None):
        """دریافت گزارش گل"""
        session = self.create_session()
        try:
            query = session.query(MudReport).filter(MudReport.well_id == well_id)

            if report_date:
                query = query.filter(MudReport.report_date == report_date)

            report = query.order_by(MudReport.report_date.desc()).first()

            if report:
                return {
                    "id": report.id,
                    "well_id": report.well_id,
                    "report_date": report.report_date,
                    "mud_type": report.mud_type,
                    "sample_time": report.sample_time,
                    "mw": report.mw,
                    "pv": report.pv,
                    "yp": report.yp,
                    "funnel_vis": report.funnel_vis,
                    "gel_10s": report.gel_10s,
                    "gel_10m": report.gel_10m,
                    "fl": report.fl,
                    "cake_thickness": report.cake_thickness,
                    "ph": report.ph,
                    "temperature": report.temperature,
                    "solid_percent": report.solid_percent,
                    "oil_percent": report.oil_percent,
                    "water_percent": report.water_percent,
                    "chloride": report.chloride,
                    "volume_hole": report.volume_hole,
                    "total_circulated": report.total_circulated,
                    "loss_downhole": report.loss_downhole,
                    "loss_surface": report.loss_surface,
                    "chemicals_json": report.chemicals_json,
                    "summary": report.summary,
                    "created_at": report.created_at,
                    "updated_at": report.updated_at,
                }
            return None

        except Exception as e:
            logger.error(f"Error getting mud report: {e}")
            return None
        finally:
            session.close()

    def get_wells_by_project(self, project_id: int):
        """دریافت چاه‌های یک پروژه"""
        session = self.create_session()
        try:
            wells = session.query(Well).filter(Well.project_id == project_id).all()
            return [
                {"id": w.id, "name": w.name, "code": w.code, "status": w.status}
                for w in wells
            ]
        except Exception as e:
            logger.error(f"Error getting wells by project: {e}")
            return []
        finally:
            session.close()

    def save_drilling_parameters(self, data: dict):
        """ذخیره پارامترهای حفاری"""
        session = self.create_session()
        try:
            # بررسی وجود رکورد برای این چاه و تاریخ
            existing = (
                session.query(DrillingParameters)
                .filter(
                    DrillingParameters.well_id == data["well_id"],
                    DrillingParameters.report_date == data["report_date"],
                )
                .first()
            )

            if existing:
                # به‌روزرسانی
                for key, value in data.items():
                    if hasattr(existing, key) and key not in [
                        "id",
                        "well_id",
                        "report_date",
                    ]:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # ایجاد جدید
                new_record = DrillingParameters(**data)
                session.add(new_record)
                session.flush()
                record_id = new_record.id

            session.commit()
            logger.info(f"Drilling parameters saved/updated: ID {record_id}")
            return record_id

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving drilling parameters: {e}")
            return None
        finally:
            session.close()

    def get_drilling_parameters(self, well_id: int, report_date: date = None):
        """دریافت پارامترهای حفاری"""
        session = self.create_session()
        try:
            query = session.query(DrillingParameters).filter(
                DrillingParameters.well_id == well_id
            )

            if report_date:
                query = query.filter(DrillingParameters.report_date == report_date)

            # دریافت آخرین رکورد
            params = query.order_by(DrillingParameters.report_date.desc()).first()

            if params:
                return {
                    "id": params.id,
                    "well_id": params.well_id,
                    "report_date": params.report_date,
                    "bit_no": params.bit_no,
                    "bit_rerun": params.bit_rerun,
                    "bit_size": params.bit_size,
                    "bit_type": params.bit_type,
                    "manufacturer": params.manufacturer,
                    "iadc_code": params.iadc_code,
                    "nozzles_json": params.nozzles_json,
                    "tfa": params.tfa,
                    "depth_in": params.depth_in,
                    "depth_out": params.depth_out,
                    "bit_drilled": params.bit_drilled,
                    "cum_drilled": params.cum_drilled,
                    "hours_on_bottom": params.hours_on_bottom,
                    "cum_hours": params.cum_hours,
                    "wob_min": params.wob_min,
                    "wob_max": params.wob_max,
                    "rpm_min": params.rpm_min,
                    "rpm_max": params.rpm_max,
                    "torque_min": params.torque_min,
                    "torque_max": params.torque_max,
                    "pump_pressure_min": params.pump_pressure_min,
                    "pump_pressure_max": params.pump_pressure_max,
                    "pump_output_min": params.pump_output_min,
                    "pump_output_max": params.pump_output_max,
                    "pump1_spm": params.pump1_spm,
                    "pump1_spp": params.pump1_spp,
                    "pump2_spm": params.pump2_spm,
                    "pump2_spp": params.pump2_spp,
                    "avg_rop": params.avg_rop,
                    "hsi": params.hsi,
                    "annular_velocity": params.annular_velocity,
                    "bit_revolution": params.bit_revolution,
                    "created_at": params.created_at,
                    "updated_at": params.updated_at,
                }
            return None

        except Exception as e:
            logger.error(f"Error getting drilling parameters: {e}")
            return None
        finally:
            session.close()

    def get_cement_report(self, well_id: int, report_date: date = None):
        """دریافت گزارش سیمان"""
        session = self.create_session()
        try:
            query = session.query(CementReport).filter(CementReport.well_id == well_id)

            if report_date:
                query = query.filter(CementReport.report_date == report_date)

            report = query.order_by(CementReport.report_date.desc()).first()

            if report:
                return {
                    "id": report.id,
                    "well_id": report.well_id,
                    "report_date": report.report_date,
                    "report_name": report.report_name,
                    "cement_type": report.cement_type,
                    "job_type": report.job_type,
                    "materials_json": report.materials_json,
                    "slurry_density": report.slurry_density,
                    "slurry_yield": report.slurry_yield,
                    "mix_water": report.mix_water,
                    "thickening_time": report.thickening_time,
                    "compressive_strength": report.compressive_strength,
                    "fluid_loss": report.fluid_loss,
                    "cement_volume": report.cement_volume,
                    "displacement_volume": report.displacement_volume,
                    "top_of_cement": report.top_of_cement,
                    "bottom_of_cement": report.bottom_of_cement,
                    "summary": report.summary,
                    "created_at": report.created_at,
                    "updated_at": report.updated_at,
                }
            return None

        except Exception as e:
            logger.error(f"Error getting cement report: {e}")
            return None
        finally:
            session.close()

    def get_casing_report(self, well_id: int, report_date: date = None):
        """دریافت گزارش کیسینگ"""
        session = self.create_session()
        try:
            query = session.query(CasingReport).filter(CasingReport.well_id == well_id)

            if report_date:
                query = query.filter(CasingReport.report_date == report_date)

            report = query.order_by(CasingReport.report_date.desc()).first()

            if report:
                return {
                    "id": report.id,
                    "well_id": report.well_id,
                    "report_date": report.report_date,
                    "report_name": report.report_name,
                    "casing_type": report.casing_type,
                    "casing_json": report.casing_json,
                    "burst_pressure": report.burst_pressure,
                    "collapse_pressure": report.collapse_pressure,
                    "tensile_strength": report.tensile_strength,
                    "makeup_torque": report.makeup_torque,
                    "drift_diameter": report.drift_diameter,
                    "internal_yield": report.internal_yield,
                    "running_speed": report.running_speed,
                    "fillup_frequency": report.fillup_frequency,
                    "centralizer_spacing": report.centralizer_spacing,
                    "scratcher_spacing": report.scratcher_spacing,
                    "summary": report.summary,
                    "created_at": report.created_at,
                    "updated_at": report.updated_at,
                }
            return None

        except Exception as e:
            logger.error(f"Error getting casing report: {e}")
            return None
        finally:
            session.close()
    
    def save_tally_report(self):
        """ذخیره گزارش Tally در دیتابیس"""
        if not self.current_well:
            QMessageBox.warning(self, "Warning", "Please select a well first.")
            return
        
        try:
            # جمع‌آوری داده‌ها از جداول
            specs_data = []  # مشخصات کیسینگ
            tally_data = []  # داده‌های Tally
            
            # پارامترهای محاسباتی
            input_params = {
                'rt_depth': self.rt_depth.value(),
                'mud_weight': self.mud_weight.value(),
                'steel_density': self.steel_density.value(),
                'buoyancy_factor': self.buoyancy_factor.value()
            }
            
            # آماده‌سازی داده برای دیتابیس
            casing_data = {
                'well_id': self.current_well,
                'report_date': datetime.now().date(),
                'report_name': f"Casing Tally - {datetime.now().strftime('%Y-%m-%d')}",
                'casing_type': 'Tally',  # یا از combobox بگیرید
                'casing_json': json.dumps({
                    'specifications': specs_data,
                    'tally': tally_data,
                    'parameters': input_params
                }),
                'summary': self.summary_text.toPlainText()
            }
            
            # ذخیره در دیتابیس
            if self.db_manager:
                result = self.db_manager.save_casing_report(casing_data)
                if result:
                    self.status_bar.showMessage(f"Tally saved successfully (ID: {result})", 3000)
                    return True
                else:
                    QMessageBox.warning(self, "Warning", "Failed to save to database.")
                    return False
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
            return False

    def save_casing_tally(self, data: dict):
        """ذخیره Casing Tally"""
        session = self.create_session()
        try:
            # بررسی وجود رکورد
            existing = (
                session.query(CasingReport)
                .filter(
                    CasingReport.well_id == data["well_id"],
                    CasingReport.report_date == data["report_date"],
                    CasingReport.report_name == data["report_name"],
                )
                .first()
            )

            if existing:
                # به‌روزرسانی
                existing.tally_json = data.get("tally_json", existing.tally_json)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # ایجاد جدید
                new_report = CasingReport(**data)
                session.add(new_report)
                session.flush()
                record_id = new_report.id

            session.commit()
            logger.info(f"Casing tally saved/updated: ID {record_id}")
            return record_id

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving casing tally: {e}")
            return None
        finally:
            session.close()

    def get_casing_tally(self, well_id: int, report_date: date = None):
        """دریافت Casing Tally"""
        session = self.create_session()
        try:
            query = session.query(CasingReport).filter(CasingReport.well_id == well_id)
            
            if report_date:
                query = query.filter(CasingReport.report_date == report_date)
            
            report = query.order_by(CasingReport.report_date.desc()).first()
            
            if report and report.tally_json:
                return {
                    'id': report.id,
                    'well_id': report.well_id,
                    'report_date': report.report_date,
                    'report_name': report.report_name,
                    'tally_json': report.tally_json,
                    'created_at': report.created_at,
                    'updated_at': report.updated_at
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting casing tally: {e}")
            return None
        finally:
            session.close()

    def get_wellbore_schematic(self, well_id: int, report_date: date = None):
        """دریافت شماتیک چاه"""
        session = self.create_session()
        try:
            query = session.query(WellboreSchematic).filter(WellboreSchematic.well_id == well_id)
            
            if report_date:
                query = query.filter(WellboreSchematic.report_date == report_date)
            
            schematic = query.order_by(WellboreSchematic.report_date.desc()).first()
            
            if schematic:
                return {
                    'id': schematic.id,
                    'well_id': schematic.well_id,
                    'report_date': schematic.report_date,
                    'schematic_name': schematic.schematic_name,
                    'image_data': schematic.image_data,
                    'layers_json': schematic.layers_json,
                    'elements_json': schematic.elements_json,
                    'created_at': schematic.created_at,
                    'updated_at': schematic.updated_at
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting wellbore schematic: {e}")
            return None
        finally:
            session.close()

    def get_todays_reports_count(self):
        """Get count of reports created today"""
        session = self.create_session()
        try:
            today = date.today()
            count = session.query(DailyReport).filter(
                DailyReport.created_at >= datetime.combine(today, datetime.min.time())
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error getting today's reports count: {e}")
            return 0
        finally:
            session.close()

    def get_active_users_count(self):
        """Get count of active users (last 15 minutes)"""
        session = self.create_session()
        try:
            time_threshold = datetime.utcnow() - timedelta(minutes=15)
            count = session.query(User).filter(
                User.last_login >= time_threshold
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error getting active users count: {e}")
            return 1  # حداقل خود کاربر
        finally:
            session.close()
            
    def get_sections_by_well(self, well_id: int):
        """دریافت سکشن‌های یک چاه"""
        session = self.create_session()
        try:
            sections = session.query(Section).filter(Section.well_id == well_id).all()
            return [
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
                }
                for s in sections
            ]
        except Exception as e:
            logger.error(f"Error getting sections: {str(e)}")
            return []
        finally:
            session.close()

    def save_section(self, section_data: dict):
        """ذخیره سکشن"""
        session = self.create_session()
        try:
            if "id" in section_data and section_data["id"]:
                # Update existing section
                section = session.query(Section).filter(Section.id == section_data["id"]).first()
                if section:
                    section.name = section_data.get("name", section.name)
                    section.code = section_data.get("code", section.code)
                    section.depth_from = section_data.get("depth_from", section.depth_from)
                    section.depth_to = section_data.get("depth_to", section.depth_to)
                    section.diameter = section_data.get("diameter", section.diameter)
                    section.hole_size = section_data.get("hole_size", section.hole_size)
                    section.purpose = section_data.get("purpose", section.purpose)
                    section.description = section_data.get("description", section.description)
                    section.updated_at = datetime.utcnow()
            else:
                # Create new section
                section = Section(
                    well_id=section_data["well_id"],
                    name=section_data["name"],
                    code=section_data.get("code", ""),
                    depth_from=section_data.get("depth_from", 0.0),
                    depth_to=section_data.get("depth_to", 0.0),
                    diameter=section_data.get("diameter", 0.0),
                    hole_size=section_data.get("hole_size", 0.0),
                    purpose=section_data.get("purpose", ""),
                    description=section_data.get("description", ""),
                )
                session.add(section)

            session.commit()
            logger.info("Section saved successfully")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving section: {str(e)}")
            return False
        finally:
            session.close()

    def delete_section(self, section_id: int):
        """حذف سکشن"""
        session = self.create_session()
        try:
            section = session.query(Section).filter(Section.id == section_id).first()
            if section:
                session.delete(section)
                session.commit()
                logger.info(f"Section {section_id} deleted successfully")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting section: {str(e)}")
            return False
        finally:
            session.close()

    def get_daily_reports_by_section(self, section_id: int):
        """دریافت گزارش‌های روزانه یک سکشن"""
        session = self.create_session()
        try:
            reports = (
                session.query(DailyReport)
                .filter(DailyReport.section_id == section_id)
                .order_by(DailyReport.report_date.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "report_date": r.report_date,
                    "report_number": r.report_number,  # <-- این خط را اضافه کنید
                    "rig_day": r.rig_day,
                    "depth_2400": r.depth_2400,
                    "summary": r.summary,
                    "status": r.status,
                }
                for r in reports
            ]
        except Exception as e:
            logger.error(f"Error getting daily reports for section {section_id}: {str(e)}")
            return []
        finally:
            session.close()
    def create_daily_report(self, report_data: dict):
        """ایجاد گزارش روزانه جدید با ساختار سلسله مراتبی"""
        session = self.create_session()
        try:
            # بررسی وجود گزارش برای همین سکشن و تاریخ
            existing = session.query(DailyReport).filter(
                DailyReport.section_id == report_data['section_id'],
                DailyReport.report_date == report_data['report_date']
            ).first()
            
            if existing:
                raise Exception("گزارش برای این سکشن و تاریخ قبلاً ایجاد شده است")
            
            # محاسبه شماره گزارش جدید
            last_report = session.query(DailyReport).filter(
                DailyReport.section_id == report_data['section_id']
            ).order_by(DailyReport.report_number.desc()).first()
            
            report_number = report_data.get('report_number', 1)
            if not report_data.get('report_number'):
                report_number = 1
                if last_report:
                    report_number = last_report.report_number + 1
            
            # پیدا کردن اطلاعات سکشن و پروژه برای عنوان
            section = session.query(Section).get(report_data['section_id'])
            well = session.query(Well).get(report_data['well_id'])
            project = session.query(Project).get(well.project_id) if well else None
            
            # ساخت عنوان گزارش
            date_str = report_data['report_date']
            if isinstance(date_str, str):
                report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                report_date = date_str
                
            report_title = f"{report_number:02d} Daily Report, {project.name if project else 'Unknown Project'}, {report_date}"
            
            # ایجاد گزارش جدید
            new_report = DailyReport(
                well_id=report_data['well_id'],
                section_id=report_data['section_id'],
                report_date=report_date,
                report_number=report_number,
                report_title=report_title,
                summary=report_data.get('summary', ''),
                status='Draft',
                created_by=report_data.get('created_by')
            )
            
            session.add(new_report)
            session.flush()  # Get the ID
            
            # کپی داده‌ها از روز قبل اگر خواسته شده باشد
            if report_data.get('copy_previous', False):
                self._copy_from_previous_report(session, new_report.id, report_data['section_id'])
            
            session.commit()
            logger.info(f"Daily report created: ID {new_report.id}, Number {report_number}, Title: {report_title}")
            
            return {
                'id': new_report.id,
                'report_number': report_number,
                'section_id': new_report.section_id,
                'report_title': report_title,
                'well_id': new_report.well_id
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating daily report: {e}")
            return None
        finally:
            session.close()
    
    def _copy_from_previous_report(self, session, new_report, section_id, report_date):
            """کپی داده‌ها از گزارش روز قبل"""
            try:
                previous_date = report_date - timedelta(days=1)
                previous_report = session.query(DailyReport).filter(
                    DailyReport.section_id == section_id,
                    DailyReport.report_date == previous_date
                ).first()
                
                if previous_report:
                    # کپی فیلدهای اصلی (بدون استاک مواد)
                    new_report.depth_0000 = previous_report.depth_2400 or 0
                    new_report.depth_0600 = previous_report.depth_2400 or 0
                    
                    # ریگ دی
                    new_report.rig_day = (previous_report.rig_day or 0) + 1
                    
                    # خلاصه
                    new_report.summary = previous_report.summary or ""
                    
                    # کپی داده‌های JSON (بدون استاک)
                    if previous_report.mud_data:
                        mud_data = previous_report.mud_data.copy()
                        # حذف فیلدهای استاک
                        stock_fields = ['initial_stock', 'received', 'consumed', 'final_stock']
                        for field in stock_fields:
                            mud_data.pop(field, None)
                        new_report.mud_data = mud_data
                    
                    # کپی سایر داده‌های JSON
                    json_fields = ['drilling_data', 'equipment_data', 'downhole_data', 
                                  'trajectory_data', 'logistics_data', 'safety_data',
                                  'services_data', 'planning_data', 'export_data', 
                                  'analysis_data']
                    
                    for field in json_fields:
                        prev_data = getattr(previous_report, field)
                        if prev_data:
                            setattr(new_report, field, prev_data.copy())
                    
                    logger.info(f"Copied data from report {previous_report.id} to {new_report.id}")
                    
            except Exception as e:
                logger.error(f"Error copying from previous report: {e}")
    def get_daily_report_by_section_and_date(self, section_id: int, report_date: date):
        """دریافت گزارش روزانه بر اساس سکشن و تاریخ"""
        session = self.create_session()
        try:
            report = session.query(DailyReport).filter(
                DailyReport.section_id == section_id,
                DailyReport.report_date == report_date
            ).first()
            
            if report:
                return self._serialize_daily_report(report)  # <-- این تابع در خط 898 تعریف شده
            return None
            
        except Exception as e:
            logger.error(f"Error getting daily report: {e}")
            return None
        finally:
            session.close()
    def get_daily_report_by_id(self, report_id: int):
        """دریافت گزارش روزانه با ID"""
        session = self.create_session()
        try:
            report = session.query(DailyReport).get(report_id)
            if report:
                return self._serialize_daily_report(report)
            return None
            
        except Exception as e:
            logger.error(f"Error getting daily report by ID: {e}")
            return None
        finally:
            session.close()
    
    def _serialize_daily_report(self, report):
        """تبدیل DailyReport object به dictionary"""
        return {
            'id': report.id,
            'well_id': report.well_id,
            'section_id': report.section_id,
            'report_date': report.report_date,
            'report_number': report.report_number,
            'report_title': report.report_title,
            'drilling_data': report.drilling_data,
            'mud_data': report.mud_data,
            'equipment_data': report.equipment_data,
            'downhole_data': report.downhole_data,
            'trajectory_data': report.trajectory_data,
            'logistics_data': report.logistics_data,
            'safety_data': report.safety_data,
            'services_data': report.services_data,
            'analysis_data': report.analysis_data,
            'planning_data': report.planning_data,
            'export_data': report.export_data,
            'depth_0000': report.depth_0000,
            'depth_0600': report.depth_0600,
            'depth_2400': report.depth_2400,
            'summary': report.summary,
            'status': report.status,
            'created_at': report.created_at,
            'updated_at': report.updated_at,
            'created_by': report.created_by
        }
    
    def update_daily_report_tab_data(self, report_id: int, tab_type: str, tab_data: dict):
        """آپدیت داده‌های یک تب خاص از گزارش"""
        session = self.create_session()
        try:
            report = session.query(DailyReport).get(report_id)
            if not report:
                return False
            
            # تعیین فیلد بر اساس نوع تب
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
            if field_name:
                setattr(report, field_name, tab_data)
                report.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"Updated {tab_type} data for report {report_id}")
                return True
            
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating tab data: {e}")
            return False
        finally:
            session.close()
    def get_previous_daily_report(self, section_id: int, current_report_id: int = None):
        """دریافت گزارش روز قبل برای کپی کردن"""
        session = self.create_session()
        try:
            query = session.query(DailyReport).filter(
                DailyReport.section_id == section_id
            ).order_by(DailyReport.report_date.desc())
            
            if current_report_id:
                query = query.filter(DailyReport.id != current_report_id)
            
            previous_report = query.first()
            
            if previous_report:
                return self._serialize_daily_report(previous_report)
            return None
            
        except Exception as e:
            logger.error(f"Error getting previous daily report: {e}")
            return None
        finally:
            session.close()
    
    def delete_daily_report(self, report_id: int):
        """حذف گزارش روزانه"""
        session = self.create_session()
        try:
            report = session.query(DailyReport).get(report_id)
            if report:
                session.delete(report)
                session.commit()
                logger.info(f"Daily report {report_id} deleted")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting daily report: {e}")
            return False
        finally:
            session.close()

    def save_bit_report(self, well_id: int, report_data: dict):
        """ذخیره گزارش مته"""
        session = self.create_session()
        try:
            report = BitReport(
                well_id=well_id,
                report_date=report_data.get('report_date', date.today()),
                report_name=report_data.get('report_name', f"Bit_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                bit_records_json=report_data.get('bit_records', []),
                created_at=datetime.utcnow()
            )
            session.add(report)
            session.commit()
            return report.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving bit report: {e}")
            return None
        finally:
            session.close()

    def save_bha_report(self, well_id: int, bha_data: dict):
        """ذخیره گزارش BHA"""
        session = self.create_session()
        try:
            report = BHAReport(
                well_id=well_id,
                bha_name=bha_data.get('bha_name', 'Unnamed BHA'),
                bha_data_json=bha_data.get('bha_data', {}),
                created_at=datetime.utcnow()
            )
            session.add(report)
            session.commit()
            return report.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving BHA report: {e}")
            return None
        finally:
            session.close()

    def save_downhole_equipment(self, well_id: int, equipment_data: dict):
        """ذخیره تجهیزات زیر سطحی"""
        session = self.create_session()
        try:
            equipment = DownholeEquipment(
                well_id=well_id,
                equipment_data_json=equipment_data,
                created_at=datetime.utcnow()
            )
            session.add(equipment)
            session.commit()
            return equipment.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving downhole equipment: {e}")
            return None
        finally:
            session.close()

    def save_formation_report(self, well_id: int, formation_data: dict):
        """ذخیره گزارش سازندها"""
        session = self.create_session()
        try:
            report = FormationReport(
                well_id=well_id,
                report_name=formation_data.get('report_name', f"Formation_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                formations_json=formation_data.get('formations', []),
                created_at=datetime.utcnow()
            )
            session.add(report)
            session.commit()
            return report.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving formation report: {e}")
            return None
        finally:
            session.close()
                
    def save_trip_sheet_entries(self, entries: list):
        """ذخیره ورودی‌های Trip Sheet"""
        session = self.create_session()
        try:
            for entry_data in entries:
                # بررسی وجود ورودی
                existing = session.query(TripSheetEntry).filter(
                    TripSheetEntry.well_id == entry_data.well_id,
                    TripSheetEntry.time == entry_data.time,
                    TripSheetEntry.activity == entry_data.activity
                ).first()
                
                if existing:
                    # به‌روزرسانی
                    existing.depth = entry_data.depth
                    existing.cum_trip = entry_data.cum_trip
                    existing.duration = entry_data.duration
                    existing.remarks = entry_data.remarks
                    existing.supervisor = entry_data.supervisor
                    existing.verified = entry_data.verified
                    existing.updated_at = datetime.utcnow()
                else:
                    # ایجاد جدید
                    new_entry = TripSheetEntry(
                        well_id=entry_data.well_id,
                        section_id=entry_data.section_id,
                        time=datetime.strptime(entry_data.time, "%H:%M").time() if isinstance(entry_data.time, str) else entry_data.time,
                        activity=entry_data.activity,
                        depth=entry_data.depth,
                        cum_trip=entry_data.cum_trip,
                        duration=entry_data.duration,
                        remarks=entry_data.remarks,
                        supervisor=entry_data.supervisor,
                        verified=entry_data.verified,
                        created_by=entry_data.created_by if hasattr(entry_data, 'created_by') else None
                    )
                    session.add(new_entry)
            
            session.commit()
            logger.info(f"Saved {len(entries)} trip sheet entries")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving trip sheet entries: {e}")
            return False
        finally:
            session.close()

    def load_trip_sheet_entries(self, well_id: int = None, section_id: int = None):
        """بارگذاری ورودی‌های Trip Sheet"""
        session = self.create_session()
        try:
            query = session.query(TripSheetEntry)
            
            if well_id:
                query = query.filter(TripSheetEntry.well_id == well_id)
            if section_id:
                query = query.filter(TripSheetEntry.section_id == section_id)
            
            entries = query.order_by(TripSheetEntry.time).all()
            
            return [
                {
                    'id': e.id,
                    'well_id': e.well_id,
                    'section_id': e.section_id,
                    'time': e.time.strftime("%H:%M") if e.time else "",
                    'activity': e.activity,
                    'depth': e.depth,
                    'cum_trip': e.cum_trip,
                    'duration': e.duration,
                    'remarks': e.remarks,
                    'supervisor': e.supervisor,
                    'verified': e.verified,
                    'created_at': e.created_at,
                    'updated_at': e.updated_at
                }
                for e in entries
            ]
            
        except Exception as e:
            logger.error(f"Error loading trip sheet entries: {e}")
            return []
        finally:
            session.close()

    def save_survey_points(self, points: list):
        """ذخیره نقاط سروی"""
        session = self.create_session()
        try:
            for point_data in points:
                # بررسی وجود نقطه
                existing = session.query(SurveyPoint).filter(
                    SurveyPoint.well_id == point_data.well_id,
                    SurveyPoint.md == point_data.md
                ).first()
                
                if existing:
                    # به‌روزرسانی
                    existing.inc = point_data.inc
                    existing.azi = point_data.azi
                    existing.tvd = point_data.tvd
                    existing.north = point_data.north
                    existing.east = point_data.east
                    existing.vs = point_data.vs
                    existing.hd = point_data.hd
                    existing.dls = point_data.dls
                    existing.tool = point_data.tool
                    existing.remarks = point_data.remarks
                    existing.updated_at = datetime.utcnow()
                else:
                    # ایجاد جدید
                    new_point = SurveyPoint(
                        well_id=point_data.well_id,
                        section_id=getattr(point_data, 'section_id', None),
                        calculation_id=getattr(point_data, 'calculation_id', None),
                        md=point_data.md,
                        inc=point_data.inc,
                        azi=point_data.azi,
                        tvd=point_data.tvd,
                        north=point_data.north,
                        east=point_data.east,
                        vs=point_data.vs,
                        hd=point_data.hd,
                        dls=point_data.dls,
                        tool=point_data.tool,
                        remarks=point_data.remarks,
                        measured_at=getattr(point_data, 'measured_at', datetime.utcnow()),
                        created_by=getattr(point_data, 'created_by', None)
                    )
                    session.add(new_point)
            
            session.commit()
            logger.info(f"Saved {len(points)} survey points")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving survey points: {e}")
            return False
        finally:
            session.close()

    def load_survey_points(self, well_id: int = None, calculation_id: int = None):
        """بارگذاری نقاط سروی"""
        session = self.create_session()
        try:
            query = session.query(SurveyPoint)
            
            if well_id:
                query = query.filter(SurveyPoint.well_id == well_id)
            if calculation_id:
                query = query.filter(SurveyPoint.calculation_id == calculation_id)
            
            points = query.order_by(SurveyPoint.md).all()
            
            return [
                {
                    'id': p.id,
                    'well_id': p.well_id,
                    'section_id': p.section_id,
                    'calculation_id': p.calculation_id,
                    'md': p.md,
                    'inc': p.inc,
                    'azi': p.azi,
                    'tvd': p.tvd,
                    'north': p.north,
                    'east': p.east,
                    'vs': p.vs,
                    'hd': p.hd,
                    'dls': p.dls,
                    'tool': p.tool,
                    'remarks': p.remarks,
                    'measured_at': p.measured_at,
                    'created_at': p.created_at,
                    'updated_at': p.updated_at
                }
                for p in points
            ]
            
        except Exception as e:
            logger.error(f"Error loading survey points: {e}")
            return []
        finally:
            session.close()

    def save_trajectory_calculation(self, calculation_data: dict):
        """ذخیره محاسبه تراژکتوری"""
        session = self.create_session()
        try:
            # ایجاد محاسبه جدید
            calculation = TrajectoryCalculation(
                well_id=calculation_data['well_id'],
                section_id=calculation_data.get('section_id'),
                method=calculation_data.get('method', 'Minimum Curvature'),
                calculation_date=calculation_data.get('calculation_date', date.today()),
                parameters_json=calculation_data.get('parameters', {}),
                results_json=calculation_data.get('results', {}),
                target_north=calculation_data.get('target_north'),
                target_east=calculation_data.get('target_east'),
                target_tvd=calculation_data.get('target_tvd'),
                total_hd=calculation_data.get('total_hd'),
                total_tvd=calculation_data.get('total_tvd'),
                total_md=calculation_data.get('total_md'),
                description=calculation_data.get('description', ''),
                calculated_by=calculation_data.get('calculated_by')
            )
            
            session.add(calculation)
            session.flush()  # برای گرفتن ID
            
            # ذخیره نقاط مرتبط
            survey_points = calculation_data.get('survey_points', [])
            for point_data in survey_points:
                point = SurveyPoint(
                    well_id=calculation.well_id,
                    section_id=calculation.section_id,
                    calculation_id=calculation.id,
                    md=point_data['md'],
                    inc=point_data['inc'],
                    azi=point_data['azi'],
                    tvd=point_data.get('tvd'),
                    north=point_data.get('north'),
                    east=point_data.get('east'),
                    vs=point_data.get('vs'),
                    hd=point_data.get('hd'),
                    dls=point_data.get('dls'),
                    tool=point_data.get('tool', 'MWD'),
                    remarks=point_data.get('remarks')
                )
                session.add(point)
            
            session.commit()
            logger.info(f"Saved trajectory calculation: ID {calculation.id}")
            return calculation.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving trajectory calculation: {e}")
            return None
        finally:
            session.close()

    def load_trajectory_calculations(self, well_id: int = None):
        """بارگذاری محاسبات تراژکتوری"""
        session = self.create_session()
        try:
            query = session.query(TrajectoryCalculation)
            
            if well_id:
                query = query.filter(TrajectoryCalculation.well_id == well_id)
            
            calculations = query.order_by(TrajectoryCalculation.calculation_date.desc()).all()
            
            return [
                {
                    'id': c.id,
                    'well_id': c.well_id,
                    'section_id': c.section_id,
                    'method': c.method,
                    'calculation_date': c.calculation_date,
                    'parameters': c.parameters_json or {},
                    'results': c.results_json or {},
                    'target_north': c.target_north,
                    'target_east': c.target_east,
                    'target_tvd': c.target_tvd,
                    'total_hd': c.total_hd,
                    'total_tvd': c.total_tvd,
                    'total_md': c.total_md,
                    'description': c.description,
                    'calculated_by': c.calculated_by,
                    'created_at': c.created_at,
                    'updated_at': c.updated_at,
                    'survey_points': self.load_survey_points(calculation_id=c.id)
                }
                for c in calculations
            ]
            
        except Exception as e:
            logger.error(f"Error loading trajectory calculations: {e}")
            return []
        finally:
            session.close()

    def save_trajectory_plot(self, plot_data: dict):
        """ذخیره نمودار تراژکتوری"""
        session = self.create_session()
        try:
            plot = TrajectoryPlot(
                calculation_id=plot_data.get('calculation_id'),
                plot_type=plot_data.get('plot_type'),
                title=plot_data.get('title', 'Trajectory Plot'),
                plot_data_json=plot_data.get('plot_data', {}),
                image_data=plot_data.get('image_data'),
                image_format=plot_data.get('image_format', 'png'),
                created_by=plot_data.get('created_by')
            )
            
            session.add(plot)
            session.commit()
            logger.info(f"Saved trajectory plot: ID {plot.id}")
            return plot.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving trajectory plot: {e}")
            return None
        finally:
            session.close()

    def load_trajectory_plots(self, calculation_id: int = None):
        """بارگذاری نمودارهای تراژکتوری"""
        session = self.create_session()
        try:
            query = session.query(TrajectoryPlot)
            
            if calculation_id:
                query = query.filter(TrajectoryPlot.calculation_id == calculation_id)
            
            plots = query.order_by(TrajectoryPlot.created_at.desc()).all()
            
            return [
                {
                    'id': p.id,
                    'calculation_id': p.calculation_id,
                    'plot_type': p.plot_type,
                    'title': p.title,
                    'plot_data': p.plot_data_json or {},
                    'image_data': p.image_data,
                    'image_format': p.image_format,
                    'created_at': p.created_at
                }
                for p in plots
            ]
            
        except Exception as e:
            logger.error(f"Error loading trajectory plots: {e}")
            return []
        finally:
            session.close()

    def save_logistics_personnel(self, personnel_data: dict):
        """ذخیره اطلاعات پرسنل لجستیک"""
        session = self.create_session()
        try:
            if "id" in personnel_data and personnel_data["id"]:
                # Update existing
                personnel = session.query(LogisticsPersonnel).filter(
                    LogisticsPersonnel.id == personnel_data["id"]
                ).first()
                if personnel:
                    personnel.name = personnel_data.get("name", personnel.name)
                    personnel.position = personnel_data.get("position", personnel.position)
                    personnel.company = personnel_data.get("company", personnel.company)
                    personnel.arrival_date = personnel_data.get("arrival_date", personnel.arrival_date)
                    personnel.departure_date = personnel_data.get("departure_date", personnel.departure_date)
                    personnel.contact_info = personnel_data.get("contact_info", personnel.contact_info)
                    personnel.remarks = personnel_data.get("remarks", personnel.remarks)
                    personnel.updated_at = datetime.utcnow()
                    record_id = personnel.id
                else:
                    return None
            else:
                # Create new
                personnel = LogisticsPersonnel(
                    well_id=personnel_data["well_id"],
                    section_id=personnel_data.get("section_id"),
                    report_id=personnel_data.get("report_id"),
                    name=personnel_data["name"],
                    position=personnel_data.get("position", ""),
                    company=personnel_data.get("company", ""),
                    arrival_date=personnel_data.get("arrival_date"),
                    departure_date=personnel_data.get("departure_date"),
                    contact_info=personnel_data.get("contact_info", ""),
                    remarks=personnel_data.get("remarks", ""),
                    created_by=personnel_data.get("created_by")
                )
                session.add(personnel)
                session.flush()
                record_id = personnel.id
            
            session.commit()
            logger.info(f"Logistics personnel saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving logistics personnel: {e}")
            return None
        finally:
            session.close()


    def get_logistics_personnel(self, well_id: int = None, section_id: int = None, 
                              report_id: int = None):
        """دریافت اطلاعات پرسنل لجستیک"""
        session = self.create_session()
        try:
            query = session.query(LogisticsPersonnel)
            
            if well_id:
                query = query.filter(LogisticsPersonnel.well_id == well_id)
            if section_id:
                query = query.filter(LogisticsPersonnel.section_id == section_id)
            if report_id:
                query = query.filter(LogisticsPersonnel.report_id == report_id)
            
            personnel = query.order_by(LogisticsPersonnel.arrival_date.desc()).all()
            
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
                    "updated_at": p.updated_at
                }
                for p in personnel
            ]
            
        except Exception as e:
            logger.error(f"Error getting logistics personnel: {e}")
            return []
        finally:
            session.close()


    def delete_logistics_personnel(self, personnel_id: int):
        """حذف پرسنل لجستیک"""
        session = self.create_session()
        try:
            personnel = session.query(LogisticsPersonnel).filter(
                LogisticsPersonnel.id == personnel_id
            ).first()
            
            if personnel:
                session.delete(personnel)
                session.commit()
                logger.info(f"Logistics personnel deleted: ID {personnel_id}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting logistics personnel: {e}")
            return False
        finally:
            session.close()


    def save_service_company_pob(self, pob_data: dict):
        """ذخیره اطلاعات شرکت‌های خدماتی و POB"""
        session = self.create_session()
        try:
            if "id" in pob_data and pob_data["id"]:
                # Update existing
                pob = session.query(ServiceCompanyPOB).filter(
                    ServiceCompanyPOB.id == pob_data["id"]
                ).first()
                if pob:
                    pob.company_name = pob_data.get("company_name", pob.company_name)
                    pob.service_type = pob_data.get("service_type", pob.service_type)
                    pob.personnel_count = pob_data.get("personnel_count", pob.personnel_count)
                    pob.date_in = pob_data.get("date_in", pob.date_in)
                    pob.date_out = pob_data.get("date_out", pob.date_out)
                    pob.remarks = pob_data.get("remarks", pob.remarks)
                    pob.updated_at = datetime.utcnow()
                    record_id = pob.id
                else:
                    return None
            else:
                # Create new
                pob = ServiceCompanyPOB(
                    well_id=pob_data["well_id"],
                    section_id=pob_data.get("section_id"),
                    report_id=pob_data.get("report_id"),
                    company_name=pob_data["company_name"],
                    service_type=pob_data.get("service_type", ""),
                    personnel_count=pob_data.get("personnel_count", 0),
                    date_in=pob_data.get("date_in"),
                    date_out=pob_data.get("date_out"),
                    remarks=pob_data.get("remarks", ""),
                    created_by=pob_data.get("created_by")
                )
                session.add(pob)
                session.flush()
                record_id = pob.id
            
            session.commit()
            logger.info(f"Service company POB saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving service company POB: {e}")
            return None
        finally:
            session.close()


    def get_service_company_pob(self, well_id: int = None, section_id: int = None, 
                              report_id: int = None):
        """دریافت اطلاعات شرکت‌های خدماتی و POB"""
        session = self.create_session()
        try:
            query = session.query(ServiceCompanyPOB)
            
            if well_id:
                query = query.filter(ServiceCompanyPOB.well_id == well_id)
            if section_id:
                query = query.filter(ServiceCompanyPOB.section_id == section_id)
            if report_id:
                query = query.filter(ServiceCompanyPOB.report_id == report_id)
            
            pobs = query.order_by(ServiceCompanyPOB.date_in.desc()).all()
            
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
                    "updated_at": p.updated_at
                }
                for p in pobs
            ]
            
        except Exception as e:
            logger.error(f"Error getting service company POB: {e}")
            return []
        finally:
            session.close()


    def calculate_total_pob(self, well_id: int = None, section_id: int = None, 
                           report_id: int = None):
        """محاسبه مجموع POB"""
        session = self.create_session()
        try:
            query = session.query(ServiceCompanyPOB)
            
            if well_id:
                query = query.filter(ServiceCompanyPOB.well_id == well_id)
            if section_id:
                query = query.filter(ServiceCompanyPOB.section_id == section_id)
            if report_id:
                query = query.filter(ServiceCompanyPOB.report_id == report_id)
            
            pobs = query.all()
            total = sum(p.personnel_count for p in pobs)
            
            return total
            
        except Exception as e:
            logger.error(f"Error calculating total POB: {e}")
            return 0
        finally:
            session.close()


    def save_fuel_water_inventory(self, inventory_data: dict):
        """ذخیره موجودی سوخت و آب"""
        session = self.create_session()
        try:
            # Check for existing record for same date
            existing = session.query(FuelWaterInventory).filter(
                FuelWaterInventory.well_id == inventory_data["well_id"],
                FuelWaterInventory.report_date == inventory_data["report_date"]
            ).first()
            
            if existing:
                # Update existing
                existing.fuel_type = inventory_data.get("fuel_type", existing.fuel_type)
                existing.fuel_consumed = inventory_data.get("fuel_consumed", existing.fuel_consumed)
                existing.fuel_stock = inventory_data.get("fuel_stock", existing.fuel_stock)
                existing.fuel_received = inventory_data.get("fuel_received", existing.fuel_received)
                existing.water_consumed = inventory_data.get("water_consumed", existing.water_consumed)
                existing.water_stock = inventory_data.get("water_stock", existing.water_stock)
                existing.water_received = inventory_data.get("water_received", existing.water_received)
                
                # Calculate remaining
                existing.fuel_remaining = existing.fuel_stock - existing.fuel_consumed
                existing.water_remaining = existing.water_stock - existing.water_consumed
                
                # Calculate days remaining
                if existing.fuel_consumed > 0:
                    existing.days_remaining_fuel = existing.fuel_remaining / existing.fuel_consumed
                else:
                    existing.days_remaining_fuel = 0
                    
                if existing.water_consumed > 0:
                    existing.days_remaining_water = existing.water_remaining / existing.water_consumed
                else:
                    existing.days_remaining_water = 0
                    
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # Create new
                fuel_consumed = inventory_data.get("fuel_consumed", 0.0)
                fuel_stock = inventory_data.get("fuel_stock", 0.0)
                water_consumed = inventory_data.get("water_consumed", 0.0)
                water_stock = inventory_data.get("water_stock", 0.0)
                
                # Calculate values
                fuel_remaining = fuel_stock - fuel_consumed
                water_remaining = water_stock - water_consumed
                
                days_remaining_fuel = fuel_remaining / fuel_consumed if fuel_consumed > 0 else 0
                days_remaining_water = water_remaining / water_consumed if water_consumed > 0 else 0
                
                inventory = FuelWaterInventory(
                    well_id=inventory_data["well_id"],
                    section_id=inventory_data.get("section_id"),
                    report_id=inventory_data.get("report_id"),
                    report_date=inventory_data["report_date"],
                    fuel_type=inventory_data.get("fuel_type", "Diesel"),
                    fuel_consumed=fuel_consumed,
                    fuel_stock=fuel_stock,
                    fuel_received=inventory_data.get("fuel_received", 0.0),
                    water_consumed=water_consumed,
                    water_stock=water_stock,
                    water_received=inventory_data.get("water_received", 0.0),
                    fuel_remaining=fuel_remaining,
                    water_remaining=water_remaining,
                    days_remaining_fuel=days_remaining_fuel,
                    days_remaining_water=days_remaining_water,
                    created_by=inventory_data.get("created_by")
                )
                session.add(inventory)
                session.flush()
                record_id = inventory.id
            
            session.commit()
            logger.info(f"Fuel/water inventory saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving fuel/water inventory: {e}")
            return None
        finally:
            session.close()


    def get_fuel_water_inventory(self, well_id: int = None, report_date: date = None):
        """دریافت موجودی سوخت و آب"""
        session = self.create_session()
        try:
            query = session.query(FuelWaterInventory)
            
            if well_id:
                query = query.filter(FuelWaterInventory.well_id == well_id)
            if report_date:
                query = query.filter(FuelWaterInventory.report_date == report_date)
            
            inventories = query.order_by(FuelWaterInventory.report_date.desc()).all()
            
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
                    "fuel_remaining": i.fuel_remaining,
                    "water_consumed": i.water_consumed,
                    "water_stock": i.water_stock,
                    "water_received": i.water_received,
                    "water_remaining": i.water_remaining,
                    "days_remaining_fuel": i.days_remaining_fuel,
                    "days_remaining_water": i.days_remaining_water,
                    "created_at": i.created_at,
                    "updated_at": i.updated_at
                }
                for i in inventories
            ]
            
        except Exception as e:
            logger.error(f"Error getting fuel/water inventory: {e}")
            return []
        finally:
            session.close()


    def save_bulk_material(self, material_data: dict):
        """ذخیره مواد عمده"""
        session = self.create_session()
        try:
            # Check for existing material with same name and date
            existing = session.query(BulkMaterials).filter(
                BulkMaterials.well_id == material_data["well_id"],
                BulkMaterials.report_date == material_data["report_date"],
                BulkMaterials.material_name == material_data["material_name"]
            ).first()
            
            if existing:
                # Update existing
                existing.unit = material_data.get("unit", existing.unit)
                existing.initial_stock = material_data.get("initial_stock", existing.initial_stock)
                existing.received = material_data.get("received", existing.received)
                existing.used = material_data.get("used", existing.used)
                
                # Calculate current stock
                existing.current_stock = existing.initial_stock + existing.received - existing.used
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # Create new
                initial_stock = material_data.get("initial_stock", 0.0)
                received = material_data.get("received", 0.0)
                used = material_data.get("used", 0.0)
                current_stock = initial_stock + received - used
                
                material = BulkMaterials(
                    well_id=material_data["well_id"],
                    section_id=material_data.get("section_id"),
                    report_id=material_data.get("report_id"),
                    report_date=material_data["report_date"],
                    material_name=material_data["material_name"],
                    unit=material_data.get("unit", "kg"),
                    initial_stock=initial_stock,
                    received=received,
                    used=used,
                    current_stock=current_stock,
                    created_by=material_data.get("created_by")
                )
                session.add(material)
                session.flush()
                record_id = material.id
            
            session.commit()
            logger.info(f"Bulk material saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving bulk material: {e}")
            return None
        finally:
            session.close()


    def get_bulk_materials(self, well_id: int = None, report_date: date = None):
        """دریافت مواد عمده"""
        session = self.create_session()
        try:
            query = session.query(BulkMaterials)
            
            if well_id:
                query = query.filter(BulkMaterials.well_id == well_id)
            if report_date:
                query = query.filter(BulkMaterials.report_date == report_date)
            
            materials = query.order_by(BulkMaterials.material_name).all()
            
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
                    "updated_at": m.updated_at
                }
                for m in materials
            ]
            
        except Exception as e:
            logger.error(f"Error getting bulk materials: {e}")
            return []
        finally:
            session.close()


    def calculate_bulk_totals(self, well_id: int = None, report_date: date = None):
        """محاسبه مجموع مواد عمده"""
        session = self.create_session()
        try:
            query = session.query(BulkMaterials)
            
            if well_id:
                query = query.filter(BulkMaterials.well_id == well_id)
            if report_date:
                query = query.filter(BulkMaterials.report_date == report_date)
            
            materials = query.all()
            
            totals = {
                "total_initial_stock": 0.0,
                "total_received": 0.0,
                "total_used": 0.0,
                "total_current_stock": 0.0,
                "material_count": len(materials)
            }
            
            for material in materials:
                totals["total_initial_stock"] += material.initial_stock or 0
                totals["total_received"] += material.received or 0
                totals["total_used"] += material.used or 0
                totals["total_current_stock"] += material.current_stock or 0
            
            return totals
            
        except Exception as e:
            logger.error(f"Error calculating bulk totals: {e}")
            return {}
        finally:
            session.close()


    def save_transport_log(self, log_data: dict):
        """ذخیره لاگ حمل و نقل"""
        session = self.create_session()
        try:
            if "id" in log_data and log_data["id"]:
                # Update existing
                log = session.query(TransportLog).filter(
                    TransportLog.id == log_data["id"]
                ).first()
                if log:
                    log.vehicle_type = log_data.get("vehicle_type", log.vehicle_type)
                    log.vehicle_name = log_data.get("vehicle_name", log.vehicle_name)
                    log.vehicle_id = log_data.get("vehicle_id", log.vehicle_id)
                    log.arrival_time = log_data.get("arrival_time", log.arrival_time)
                    log.departure_time = log_data.get("departure_time", log.departure_time)
                    log.duration = log_data.get("duration", log.duration)
                    log.passengers_in = log_data.get("passengers_in", log.passengers_in)
                    log.passengers_out = log_data.get("passengers_out", log.passengers_out)
                    log.cargo_description = log_data.get("cargo_description", log.cargo_description)
                    log.status = log_data.get("status", log.status)
                    log.purpose = log_data.get("purpose", log.purpose)
                    log.remarks = log_data.get("remarks", log.remarks)
                    log.updated_at = datetime.utcnow()
                    record_id = log.id
                else:
                    return None
            else:
                # Create new
                log = TransportLog(
                    well_id=log_data["well_id"],
                    section_id=log_data.get("section_id"),
                    report_id=log_data.get("report_id"),
                    log_date=log_data["log_date"],
                    vehicle_type=log_data["vehicle_type"],
                    vehicle_name=log_data["vehicle_name"],
                    vehicle_id=log_data.get("vehicle_id"),
                    arrival_time=log_data.get("arrival_time"),
                    departure_time=log_data.get("departure_time"),
                    duration=log_data.get("duration"),
                    passengers_in=log_data.get("passengers_in", 0),
                    passengers_out=log_data.get("passengers_out", 0),
                    cargo_description=log_data.get("cargo_description", ""),
                    status=log_data.get("status", "Scheduled"),
                    purpose=log_data.get("purpose", ""),
                    remarks=log_data.get("remarks", ""),
                    created_by=log_data.get("created_by")
                )
                session.add(log)
                session.flush()
                record_id = log.id
            
            session.commit()
            logger.info(f"Transport log saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving transport log: {e}")
            return None
        finally:
            session.close()


    def get_transport_logs(self, well_id: int = None, vehicle_type: str = None, 
                          log_date: date = None):
        """دریافت لاگ‌های حمل و نقل"""
        session = self.create_session()
        try:
            query = session.query(TransportLog)
            
            if well_id:
                query = query.filter(TransportLog.well_id == well_id)
            if vehicle_type:
                query = query.filter(TransportLog.vehicle_type == vehicle_type)
            if log_date:
                query = query.filter(TransportLog.log_date == log_date)
            
            logs = query.order_by(TransportLog.log_date.desc(), TransportLog.arrival_time).all()
            
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
                    "updated_at": l.updated_at
                }
                for l in logs
            ]
            
        except Exception as e:
            logger.error(f"Error getting transport logs: {e}")
            return []
        finally:
            session.close()


    def save_transport_note(self, note_data: dict):
        """ذخیره یادداشت حمل و نقل"""
        session = self.create_session()
        try:
            if "id" in note_data and note_data["id"]:
                # Update existing
                note = session.query(TransportNotes).filter(
                    TransportNotes.id == note_data["id"]
                ).first()
                if note:
                    note.title = note_data.get("title", note.title)
                    note.content = note_data.get("content", note.content)
                    note.category = note_data.get("category", note.category)
                    note.priority = note_data.get("priority", note.priority)
                    note.updated_at = datetime.utcnow()
                    record_id = note.id
                else:
                    return None
            else:
                # Create new
                note = TransportNotes(
                    well_id=note_data["well_id"],
                    section_id=note_data.get("section_id"),
                    report_id=note_data.get("report_id"),
                    note_date=note_data["note_date"],
                    title=note_data.get("title", ""),
                    content=note_data["content"],
                    category=note_data.get("category", "General"),
                    priority=note_data.get("priority", "Normal"),
                    created_by=note_data.get("created_by")
                )
                session.add(note)
                session.flush()
                record_id = note.id
            
            session.commit()
            logger.info(f"Transport note saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving transport note: {e}")
            return None
        finally:
            session.close()


    def get_transport_notes(self, well_id: int = None, category: str = None, 
                           note_date: date = None):
        """دریافت یادداشت‌های حمل و نقل"""
        session = self.create_session()
        try:
            query = session.query(TransportNotes)
            
            if well_id:
                query = query.filter(TransportNotes.well_id == well_id)
            if category:
                query = query.filter(TransportNotes.category == category)
            if note_date:
                query = query.filter(TransportNotes.note_date == note_date)
            
            notes = query.order_by(TransportNotes.note_date.desc(), TransportNotes.priority).all()
            
            return [
                {
                    "id": n.id,
                    "well_id": n.well_id,
                    "section_id": n.section_id,
                    "report_id": n.report_id,
                    "note_date": n.note_date,
                    "title": n.title,
                    "content": n.content,
                    "category": n.category,
                    "priority": n.priority,
                    "created_at": n.created_at,
                    "updated_at": n.updated_at
                }
                for n in notes
            ]
            
        except Exception as e:
            logger.error(f"Error getting transport notes: {e}")
            return []
        finally:
            session.close()

   
    def save_safety_report(self, report_data: dict):
        """Save safety report to database"""
        session = self.create_session()
        try:
            # Check if report exists for this date and well
            existing = session.query(SafetyReport).filter(
                SafetyReport.well_id == report_data['well_id'],
                SafetyReport.report_date == report_data['report_date'],
                SafetyReport.report_type == report_data.get('report_type', 'Daily')
            ).first()
            
            if existing:
                # Update existing report
                for key, value in report_data.items():
                    if hasattr(existing, key) and key not in ['id', 'well_id', 'report_date', 'report_type']:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # Create new report
                report = SafetyReport(**report_data)
                session.add(report)
                session.flush()
                record_id = report.id
            
            session.commit()
            logger.info(f"Safety report saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving safety report: {e}")
            return None
        finally:
            session.close()
    
    def get_safety_report(self, well_id: int, report_date: date = None, report_type: str = 'Daily'):
        """Get safety report for a well and date"""
        session = self.create_session()
        try:
            query = session.query(SafetyReport).filter(
                SafetyReport.well_id == well_id,
                SafetyReport.report_type == report_type
            )
            
            if report_date:
                query = query.filter(SafetyReport.report_date == report_date)
            
            report = query.order_by(SafetyReport.report_date.desc()).first()
            
            if report:
                return {
                    'id': report.id,
                    'well_id': report.well_id,
                    'section_id': report.section_id,
                    'report_id': report.report_id,
                    'report_date': report.report_date,
                    'report_type': report.report_type,
                    'title': report.title,
                    'last_fire_drill': report.last_fire_drill,
                    'last_bop_drill': report.last_bop_drill,
                    'last_h2s_drill': report.last_h2s_drill,
                    'days_without_lti': report.days_without_lti,
                    'lti_count': report.lti_count,
                    'near_miss_count': report.near_miss_count,
                    'last_rams_test': report.last_rams_test,
                    'test_pressure': report.test_pressure,
                    'last_koomey_test': report.last_koomey_test,
                    'days_since_last_test': report.days_since_last_test,
                    'bop_stack_json': report.bop_stack_json,
                    'recycled_volume': report.recycled_volume,
                    'waste_ph': report.waste_ph,
                    'turbidity': report.turbidity,
                    'hardness': report.hardness,
                    'cutting_volume': report.cutting_volume,
                    'oil_content': report.oil_content,
                    'waste_type': report.waste_type,
                    'disposal_method': report.disposal_method,
                    'waste_history_json': report.waste_history_json,
                    'safety_observations': report.safety_observations,
                    'incidents_json': report.incidents_json,
                    'equipment_checks': report.equipment_checks,
                    'status': report.status,
                    'created_at': report.created_at,
                    'updated_at': report.updated_at,
                    'created_by': report.created_by
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting safety report: {e}")
            return None
        finally:
            session.close()
    
    def save_bop_component(self, component_data: dict):
        """Save BOP component to database"""
        session = self.create_session()
        try:
            # Check if component exists
            existing = session.query(BOPComponent).filter(
                BOPComponent.well_id == component_data['well_id'],
                BOPComponent.component_name == component_data['component_name']
            ).first()
            
            if existing:
                # Update existing component
                for key, value in component_data.items():
                    if hasattr(existing, key) and key not in ['id', 'well_id', 'component_name']:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # Create new component
                component = BOPComponent(**component_data)
                session.add(component)
                session.flush()
                record_id = component.id
            
            session.commit()
            logger.info(f"BOP component saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving BOP component: {e}")
            return None
        finally:
            session.close()
    
    def get_bop_components(self, well_id: int):
        """Get BOP components for a well"""
        session = self.create_session()
        try:
            components = session.query(BOPComponent).filter(
                BOPComponent.well_id == well_id
            ).order_by(BOPComponent.component_type, BOPComponent.component_name).all()
            
            return [
                {
                    'id': c.id,
                    'well_id': c.well_id,
                    'safety_report_id': c.safety_report_id,
                    'component_name': c.component_name,
                    'component_type': c.component_type,
                    'working_pressure': c.working_pressure,
                    'size': c.size,
                    'ram_type': c.ram_type,
                    'manufacturer': c.manufacturer,
                    'serial_number': c.serial_number,
                    'last_test_date': c.last_test_date,
                    'next_test_due': c.next_test_due,
                    'test_pressure': c.test_pressure,
                    'test_result': c.test_result,
                    'status': c.status,
                    'remarks': c.remarks,
                    'created_at': c.created_at,
                    'updated_at': c.updated_at
                }
                for c in components
            ]
            
        except Exception as e:
            logger.error(f"Error getting BOP components: {e}")
            return []
        finally:
            session.close()
    
    def save_waste_record(self, record_data: dict):
        """Save waste record to database"""
        session = self.create_session()
        try:
            # Create new record
            record = WasteRecord(**record_data)
            session.add(record)
            session.flush()
            record_id = record.id
            
            session.commit()
            logger.info(f"Waste record saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving waste record: {e}")
            return None
        finally:
            session.close()
    
    def get_waste_records(self, well_id: int, start_date: date = None, end_date: date = None):
        """Get waste records for a well within date range"""
        session = self.create_session()
        try:
            query = session.query(WasteRecord).filter(
                WasteRecord.well_id == well_id
            )
            
            if start_date:
                query = query.filter(WasteRecord.record_date >= start_date)
            if end_date:
                query = query.filter(WasteRecord.record_date <= end_date)
            
            records = query.order_by(WasteRecord.record_date.desc()).all()
            
            return [
                {
                    'id': r.id,
                    'well_id': r.well_id,
                    'safety_report_id': r.safety_report_id,
                    'record_date': r.record_date,
                    'waste_type': r.waste_type,
                    'volume': r.volume,
                    'unit': r.unit,
                    'ph': r.ph,
                    'turbidity': r.turbidity,
                    'hardness': r.hardness,
                    'oil_content': r.oil_content,
                    'disposal_method': r.disposal_method,
                    'disposal_date': r.disposal_date,
                    'disposal_company': r.disposal_company,
                    'waste_ticket_number': r.waste_ticket_number,
                    'manifest_number': r.manifest_number,
                    'remarks': r.remarks,
                    'status': r.status,
                    'created_at': r.created_at,
                    'updated_at': r.updated_at
                }
                for r in records
            ]
            
        except Exception as e:
            logger.error(f"Error getting waste records: {e}")
            return []
        finally:
            session.close()
    
    def save_safety_incident(self, incident_data: dict):
        """Save safety incident to database"""
        session = self.create_session()
        try:
            incident = SafetyIncident(**incident_data)
            session.add(incident)
            session.flush()
            record_id = incident.id
            
            session.commit()
            logger.info(f"Safety incident saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving safety incident: {e}")
            return None
        finally:
            session.close()
    
    def get_safety_incidents(self, well_id: int = None, start_date: date = None, end_date: date = None):
        """Get safety incidents within date range"""
        session = self.create_session()
        try:
            query = session.query(SafetyIncident).join(SafetyReport)
            
            if well_id:
                query = query.filter(SafetyReport.well_id == well_id)
            if start_date:
                query = query.filter(SafetyIncident.incident_date >= start_date)
            if end_date:
                query = query.filter(SafetyIncident.incident_date <= end_date)
            
            incidents = query.order_by(SafetyIncident.incident_date.desc(), SafetyIncident.incident_time.desc()).all()
            
            return [
                {
                    'id': i.id,
                    'safety_report_id': i.safety_report_id,
                    'incident_date': i.incident_date,
                    'incident_time': i.incident_time.strftime('%H:%M') if i.incident_time else '',
                    'incident_type': i.incident_type,
                    'severity': i.severity,
                    'location': i.location,
                    'description': i.description,
                    'personnel_involved': i.personnel_involved,
                    'injuries': i.injuries,
                    'immediate_response': i.immediate_response,
                    'corrective_actions': i.corrective_actions,
                    'root_cause': i.root_cause,
                    'investigator': i.investigator,
                    'status': i.status,
                    'resolved_date': i.resolved_date,
                    'created_at': i.created_at,
                    'updated_at': i.updated_at
                }
                for i in incidents
            ]
            
        except Exception as e:
            logger.error(f"Error getting safety incidents: {e}")
            return []
        finally:
            session.close()


    # ============ Service Company Methods ============
    
    def save_service_company(self, company_data: dict):
        """Save service company to database"""
        session = self.create_session()
        try:
            if "id" in company_data and company_data["id"]:
                # Update existing
                company = session.query(ServiceCompany).filter(
                    ServiceCompany.id == company_data["id"]
                ).first()
                if company:
                    company.company_name = company_data.get("company_name", company.company_name)
                    company.service_type = company_data.get("service_type", company.service_type)
                    company.start_datetime = company_data.get("start_datetime", company.start_datetime)
                    company.end_datetime = company_data.get("end_datetime", company.end_datetime)
                    company.contact_person = company_data.get("contact_person", company.contact_person)
                    company.contact_phone = company_data.get("contact_phone", company.contact_phone)
                    company.contact_email = company_data.get("contact_email", company.contact_email)
                    company.equipment_used = company_data.get("equipment_used", company.equipment_used)
                    company.personnel_count = company_data.get("personnel_count", company.personnel_count)
                    company.status = company_data.get("status", company.status)
                    company.description = company_data.get("description", company.description)
                    company.updated_at = datetime.utcnow()
                    record_id = company.id
                else:
                    return None
            else:
                # Create new
                company = ServiceCompany(
                    well_id=company_data["well_id"],
                    section_id=company_data.get("section_id"),
                    report_id=company_data.get("report_id"),
                    company_name=company_data["company_name"],
                    service_type=company_data.get("service_type", ""),
                    start_datetime=company_data.get("start_datetime"),
                    end_datetime=company_data.get("end_datetime"),
                    contact_person=company_data.get("contact_person", ""),
                    contact_phone=company_data.get("contact_phone", ""),
                    contact_email=company_data.get("contact_email", ""),
                    equipment_used=company_data.get("equipment_used", ""),
                    personnel_count=company_data.get("personnel_count", 1),
                    status=company_data.get("status", "Active"),
                    description=company_data.get("description", ""),
                    created_by=company_data.get("created_by")
                )
                session.add(company)
                session.flush()
                record_id = company.id
            
            session.commit()
            logger.info(f"Service company saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving service company: {e}")
            return None
        finally:
            session.close()
    
    def get_service_companies(self, well_id: int = None, section_id: int = None, 
                             report_id: int = None, status: str = None):
        """Get service companies"""
        session = self.create_session()
        try:
            query = session.query(ServiceCompany)
            
            if well_id:
                query = query.filter(ServiceCompany.well_id == well_id)
            if section_id:
                query = query.filter(ServiceCompany.section_id == section_id)
            if report_id:
                query = query.filter(ServiceCompany.report_id == report_id)
            if status:
                query = query.filter(ServiceCompany.status == status)
            
            companies = query.order_by(ServiceCompany.start_datetime.desc()).all()
            
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
                    "updated_at": c.updated_at
                }
                for c in companies
            ]
            
        except Exception as e:
            logger.error(f"Error getting service companies: {e}")
            return []
        finally:
            session.close()
    
    def delete_service_company(self, company_id: int):
        """Delete service company"""
        session = self.create_session()
        try:
            company = session.query(ServiceCompany).filter(
                ServiceCompany.id == company_id
            ).first()
            
            if company:
                session.delete(company)
                session.commit()
                logger.info(f"Service company deleted: ID {company_id}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting service company: {e}")
            return False
        finally:
            session.close()
    
    # ============ Service Note Methods ============
    
    def save_service_note(self, note_data: dict):
        """Save service note to database"""
        session = self.create_session()
        try:
            if "id" in note_data and note_data["id"]:
                # Update existing
                note = session.query(ServiceNote).filter(
                    ServiceNote.id == note_data["id"]
                ).first()
                if note:
                    note.note_number = note_data.get("note_number", note.note_number)
                    note.note_type = note_data.get("note_type", note.note_type)
                    note.content = note_data.get("content", note.content)
                    note.priority = note_data.get("priority", note.priority)
                    note.status = note_data.get("status", note.status)
                    note.updated_at = datetime.utcnow()
                    record_id = note.id
                else:
                    return None
            else:
                # Create new
                note = ServiceNote(
                    well_id=note_data["well_id"],
                    section_id=note_data.get("section_id"),
                    report_id=note_data.get("report_id"),
                    note_number=note_data["note_number"],
                    note_type=note_data.get("note_type", "General"),
                    content=note_data["content"],
                    priority=note_data.get("priority", "Medium"),
                    status=note_data.get("status", "Active"),
                    created_by=note_data.get("created_by")
                )
                session.add(note)
                session.flush()
                record_id = note.id
            
            session.commit()
            logger.info(f"Service note saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving service note: {e}")
            return None
        finally:
            session.close()
    
    def get_service_notes(self, well_id: int = None, section_id: int = None, 
                         report_id: int = None, note_type: str = None):
        """Get service notes"""
        session = self.create_session()
        try:
            query = session.query(ServiceNote)
            
            if well_id:
                query = query.filter(ServiceNote.well_id == well_id)
            if section_id:
                query = query.filter(ServiceNote.section_id == section_id)
            if report_id:
                query = query.filter(ServiceNote.report_id == report_id)
            if note_type:
                query = query.filter(ServiceNote.note_type == note_type)
            
            notes = query.order_by(ServiceNote.note_number).all()
            
            return [
                {
                    "id": n.id,
                    "well_id": n.well_id,
                    "section_id": n.section_id,
                    "report_id": n.report_id,
                    "note_number": n.note_number,
                    "note_type": n.note_type,
                    "content": n.content,
                    "priority": n.priority,
                    "status": n.status,
                    "created_at": n.created_at,
                    "updated_at": n.updated_at
                }
                for n in notes
            ]
            
        except Exception as e:
            logger.error(f"Error getting service notes: {e}")
            return []
        finally:
            session.close()
    
    def delete_service_note(self, note_id: int):
        """Delete service note"""
        session = self.create_session()
        try:
            note = session.query(ServiceNote).filter(
                ServiceNote.id == note_id
            ).first()
            
            if note:
                session.delete(note)
                session.commit()
                logger.info(f"Service note deleted: ID {note_id}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting service note: {e}")
            return False
        finally:
            session.close()
    
    # ============ Material Request Methods ============
    
    def save_material_request(self, request_data: dict):
        """Save material request to database"""
        session = self.create_session()
        try:
            if "id" in request_data and request_data["id"]:
                # Update existing
                request = session.query(MaterialRequest).filter(
                    MaterialRequest.id == request_data["id"]
                ).first()
                if request:
                    request.request_date = request_data.get("request_date", request.request_date)
                    request.requested_items = request_data.get("requested_items", request.requested_items)
                    request.requested_quantity = request_data.get("requested_quantity", request.requested_quantity)
                    request.requested_unit = request_data.get("requested_unit", request.requested_unit)
                    request.outstanding_items = request_data.get("outstanding_items", request.outstanding_items)
                    request.outstanding_quantity = request_data.get("outstanding_quantity", request.outstanding_quantity)
                    request.received_items = request_data.get("received_items", request.received_items)
                    request.received_quantity = request_data.get("received_quantity", request.received_quantity)
                    request.received_date = request_data.get("received_date", request.received_date)
                    request.backload_items = request_data.get("backload_items", request.backload_items)
                    request.backload_quantity = request_data.get("backload_quantity", request.backload_quantity)
                    request.backload_date = request_data.get("backload_date", request.backload_date)
                    request.remarks = request_data.get("remarks", request.remarks)
                    request.status = request_data.get("status", request.status)
                    request.updated_at = datetime.utcnow()
                    record_id = request.id
                else:
                    return None
            else:
                # Create new
                request = MaterialRequest(
                    well_id=request_data["well_id"],
                    section_id=request_data.get("section_id"),
                    report_id=request_data.get("report_id"),
                    request_date=request_data["request_date"],
                    requested_items=request_data.get("requested_items", ""),
                    requested_quantity=request_data.get("requested_quantity", 0.0),
                    requested_unit=request_data.get("requested_unit", "units"),
                    outstanding_items=request_data.get("outstanding_items", ""),
                    outstanding_quantity=request_data.get("outstanding_quantity", 0.0),
                    received_items=request_data.get("received_items", ""),
                    received_quantity=request_data.get("received_quantity", 0.0),
                    received_date=request_data.get("received_date"),
                    backload_items=request_data.get("backload_items", ""),
                    backload_quantity=request_data.get("backload_quantity", 0.0),
                    backload_date=request_data.get("backload_date"),
                    remarks=request_data.get("remarks", ""),
                    status=request_data.get("status", "Pending"),
                    created_by=request_data.get("created_by")
                )
                session.add(request)
                session.flush()
                record_id = request.id
            
            session.commit()
            logger.info(f"Material request saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving material request: {e}")
            return None
        finally:
            session.close()
    
    def get_material_requests(self, well_id: int = None, section_id: int = None, 
                             report_id: int = None, status: str = None,
                             start_date: date = None, end_date: date = None):
        """Get material requests"""
        session = self.create_session()
        try:
            query = session.query(MaterialRequest)
            
            if well_id:
                query = query.filter(MaterialRequest.well_id == well_id)
            if section_id:
                query = query.filter(MaterialRequest.section_id == section_id)
            if report_id:
                query = query.filter(MaterialRequest.report_id == report_id)
            if status:
                query = query.filter(MaterialRequest.status == status)
            if start_date:
                query = query.filter(MaterialRequest.request_date >= start_date)
            if end_date:
                query = query.filter(MaterialRequest.request_date <= end_date)
            
            requests = query.order_by(MaterialRequest.request_date.desc()).all()
            
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
                    "updated_at": r.updated_at
                }
                for r in requests
            ]
            
        except Exception as e:
            logger.error(f"Error getting material requests: {e}")
            return []
        finally:
            session.close()
    
    def calculate_material_balance(self, well_id: int = None, section_id: int = None):
        """Calculate material balance"""
        session = self.create_session()
        try:
            query = session.query(MaterialRequest)
            
            if well_id:
                query = query.filter(MaterialRequest.well_id == well_id)
            if section_id:
                query = query.filter(MaterialRequest.section_id == section_id)
            
            requests = query.all()
            
            total_requested = sum(r.requested_quantity or 0 for r in requests)
            total_received = sum(r.received_quantity or 0 for r in requests)
            total_backload = sum(r.backload_quantity or 0 for r in requests)
            
            balance = total_requested - total_received + total_backload
            
            return {
                "total_requested": total_requested,
                "total_received": total_received,
                "total_backload": total_backload,
                "balance": balance,
                "request_count": len(requests)
            }
            
        except Exception as e:
            logger.error(f"Error calculating material balance: {e}")
            return {}
        finally:
            session.close()
    
    def delete_material_request(self, request_id: int):
        """Delete material request"""
        session = self.create_session()
        try:
            request = session.query(MaterialRequest).filter(
                MaterialRequest.id == request_id
            ).first()
            
            if request:
                session.delete(request)
                session.commit()
                logger.info(f"Material request deleted: ID {request_id}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting material request: {e}")
            return False
        finally:
            session.close()
    
    # ============ Equipment Log Methods ============
    
    def save_equipment_log(self, log_data: dict):
        """Save equipment log to database"""
        session = self.create_session()
        try:
            if "id" in log_data and log_data["id"]:
                # Update existing
                log = session.query(EquipmentLog).filter(
                    EquipmentLog.id == log_data["id"]
                ).first()
                if log:
                    log.equipment_type = log_data.get("equipment_type", log.equipment_type)
                    log.equipment_name = log_data.get("equipment_name", log.equipment_name)
                    log.equipment_id = log_data.get("equipment_id", log.equipment_id)
                    log.manufacturer = log_data.get("manufacturer", log.manufacturer)
                    log.serial_number = log_data.get("serial_number", log.serial_number)
                    log.service_date = log_data.get("service_date", log.service_date)
                    log.service_type = log_data.get("service_type", log.service_type)
                    log.service_provider = log_data.get("service_provider", log.service_provider)
                    log.hours_worked = log_data.get("hours_worked", log.hours_worked)
                    log.status = log_data.get("status", log.status)
                    log.notes = log_data.get("notes", log.notes)
                    log.updated_at = datetime.utcnow()
                    record_id = log.id
                else:
                    return None
            else:
                # Create new
                log = EquipmentLog(
                    well_id=log_data["well_id"],
                    section_id=log_data.get("section_id"),
                    report_id=log_data.get("report_id"),
                    equipment_type=log_data.get("equipment_type", ""),
                    equipment_name=log_data["equipment_name"],
                    equipment_id=log_data.get("equipment_id", ""),
                    manufacturer=log_data.get("manufacturer", ""),
                    serial_number=log_data.get("serial_number", ""),
                    service_date=log_data.get("service_date"),
                    service_type=log_data.get("service_type", ""),
                    service_provider=log_data.get("service_provider", ""),
                    hours_worked=log_data.get("hours_worked", 0.0),
                    status=log_data.get("status", "Operational"),
                    notes=log_data.get("notes", ""),
                    created_by=log_data.get("created_by")
                )
                session.add(log)
                session.flush()
                record_id = log.id
            
            session.commit()
            logger.info(f"Equipment log saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving equipment log: {e}")
            return None
        finally:
            session.close()
    
    def get_equipment_logs(self, well_id: int = None, section_id: int = None, 
                          report_id: int = None, equipment_type: str = None,
                          status: str = None):
        """Get equipment logs"""
        session = self.create_session()
        try:
            query = session.query(EquipmentLog)
            
            if well_id:
                query = query.filter(EquipmentLog.well_id == well_id)
            if section_id:
                query = query.filter(EquipmentLog.section_id == section_id)
            if report_id:
                query = query.filter(EquipmentLog.report_id == report_id)
            if equipment_type:
                query = query.filter(EquipmentLog.equipment_type == equipment_type)
            if status:
                query = query.filter(EquipmentLog.status == status)
            
            logs = query.order_by(EquipmentLog.service_date.desc()).all()
            
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
                    "updated_at": l.updated_at
                }
                for l in logs
            ]
            
        except Exception as e:
            logger.error(f"Error getting equipment logs: {e}")
            return []
        finally:
            session.close()
    
    def get_equipment_summary(self, well_id: int = None, section_id: int = None):
        """Get equipment summary"""
        session = self.create_session()
        try:
            query = session.query(EquipmentLog)
            
            if well_id:
                query = query.filter(EquipmentLog.well_id == well_id)
            if section_id:
                query = query.filter(EquipmentLog.section_id == section_id)
            
            logs = query.all()
            
            summary = {
                "total_equipment": len(logs),
                "operational": 0,
                "under_maintenance": 0,
                "out_of_service": 0,
                "total_hours": 0.0,
                "by_type": {}
            }
            
            for log in logs:
                # Count by status
                if log.status == "Operational":
                    summary["operational"] += 1
                elif log.status == "Under Maintenance":
                    summary["under_maintenance"] += 1
                elif log.status == "Out of Service":
                    summary["out_of_service"] += 1
                
                # Total hours
                summary["total_hours"] += log.hours_worked or 0
                
                # Count by type
                equipment_type = log.equipment_type or "Unknown"
                if equipment_type not in summary["by_type"]:
                    summary["by_type"][equipment_type] = {
                        "count": 0,
                        "operational": 0,
                        "total_hours": 0.0
                    }
                summary["by_type"][equipment_type]["count"] += 1
                if log.status == "Operational":
                    summary["by_type"][equipment_type]["operational"] += 1
                summary["by_type"][equipment_type]["total_hours"] += log.hours_worked or 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting equipment summary: {e}")
            return {}
        finally:
            session.close()
    
    def delete_equipment_log(self, log_id: int):
        """Delete equipment log"""
        session = self.create_session()
        try:
            log = session.query(EquipmentLog).filter(
                EquipmentLog.id == log_id
            ).first()
            
            if log:
                session.delete(log)
                session.commit()
                logger.info(f"Equipment log deleted: ID {log_id}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting equipment log: {e}")
            return False
        finally:
            session.close()
    
    # ============ Batch Operations for Services ============
    
    def save_services_data(self, services_data: dict):
        """Save all services data at once"""
        try:
            results = {
                "service_companies": [],
                "service_notes": [],
                "material_requests": [],
                "equipment_logs": []
            }
            
            # Save service companies
            if "service_companies" in services_data:
                for company_data in services_data["service_companies"]:
                    company_id = self.save_service_company(company_data)
                    if company_id:
                        results["service_companies"].append(company_id)
            
            # Save service notes
            if "service_notes" in services_data:
                for note_data in services_data["service_notes"]:
                    note_id = self.save_service_note(note_data)
                    if note_id:
                        results["service_notes"].append(note_id)
            
            # Save material requests
            if "material_requests" in services_data:
                for request_data in services_data["material_requests"]:
                    request_id = self.save_material_request(request_data)
                    if request_id:
                        results["material_requests"].append(request_id)
            
            # Save equipment logs
            if "equipment_logs" in services_data:
                for log_data in services_data["equipment_logs"]:
                    log_id = self.save_equipment_log(log_data)
                    if log_id:
                        results["equipment_logs"].append(log_id)
            
            logger.info(f"Services data saved: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error saving services data: {e}")
            return None
    
    def get_services_summary(self, well_id: int = None, section_id: int = None):
        """Get summary of all services data"""
        try:
            summary = {
                "service_companies": len(self.get_service_companies(well_id, section_id)),
                "active_service_companies": len(self.get_service_companies(well_id, section_id, status="Active")),
                "service_notes": len(self.get_service_notes(well_id, section_id)),
                "material_requests": len(self.get_material_requests(well_id, section_id)),
                "pending_material_requests": len(self.get_material_requests(well_id, section_id, status="Pending")),
                "equipment_logs": len(self.get_equipment_logs(well_id, section_id)),
                "equipment_summary": self.get_equipment_summary(well_id, section_id),
                "material_balance": self.calculate_material_balance(well_id, section_id)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting services summary: {e}")
            return {}

    # ============ Planning Methods ============

    def save_seven_days_lookahead(self, lookahead_data: dict):
        """Save seven days lookahead plan"""
        session = self.create_session()
        try:
            if "id" in lookahead_data and lookahead_data["id"]:
                # Update existing
                plan = session.query(SevenDaysLookahead).filter(
                    SevenDaysLookahead.id == lookahead_data["id"]
                ).first()
                if plan:
                    plan.activity = lookahead_data.get("activity", plan.activity)
                    plan.tools = lookahead_data.get("tools", plan.tools)
                    plan.responsible = lookahead_data.get("responsible", plan.responsible)
                    plan.remarks = lookahead_data.get("remarks", plan.remarks)
                    plan.status = lookahead_data.get("status", plan.status)
                    plan.progress_percentage = lookahead_data.get("progress_percentage", plan.progress_percentage)
                    plan.updated_at = datetime.utcnow()
                    record_id = plan.id
                else:
                    return None
            else:
                # Create new
                plan = SevenDaysLookahead(
                    well_id=lookahead_data["well_id"],
                    section_id=lookahead_data.get("section_id"),
                    report_id=lookahead_data.get("report_id"),
                    plan_date=lookahead_data["plan_date"],
                    day_number=lookahead_data["day_number"],
                    activity=lookahead_data["activity"],
                    tools=lookahead_data.get("tools", ""),
                    responsible=lookahead_data.get("responsible", ""),
                    remarks=lookahead_data.get("remarks", ""),
                    status=lookahead_data.get("status", "Planned"),
                    progress_percentage=lookahead_data.get("progress_percentage", 0),
                    created_by=lookahead_data.get("created_by")
                )
                session.add(plan)
                session.flush()
                record_id = plan.id
            
            session.commit()
            logger.info(f"Seven days lookahead saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving seven days lookahead: {e}")
            return None
        finally:
            session.close()

    def get_seven_days_lookahead(self, well_id: int = None, section_id: int = None, 
                               start_date: date = None, end_date: date = None):
        """Get seven days lookahead plans"""
        session = self.create_session()
        try:
            query = session.query(SevenDaysLookahead)
            
            if well_id:
                query = query.filter(SevenDaysLookahead.well_id == well_id)
            if section_id:
                query = query.filter(SevenDaysLookahead.section_id == section_id)
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
                    "updated_at": p.updated_at
                }
                for p in plans
            ]
            
        except Exception as e:
            logger.error(f"Error getting seven days lookahead: {e}")
            return []
        finally:
            session.close()

    def save_npt_report(self, npt_data: dict):
        """Save NPT report"""
        session = self.create_session()
        try:
            if "id" in npt_data and npt_data["id"]:
                # Update existing
                report = session.query(NPTReport).filter(
                    NPTReport.id == npt_data["id"]
                ).first()
                if report:
                    report.npt_date = npt_data.get("npt_date", report.npt_date)
                    report.start_time = npt_data.get("start_time", report.start_time)
                    report.end_time = npt_data.get("end_time", report.end_time)
                    report.duration_hours = npt_data.get("duration_hours", report.duration_hours)
                    report.npt_category = npt_data.get("npt_category", report.npt_category)
                    report.npt_code = npt_data.get("npt_code", report.npt_code)
                    report.npt_description = npt_data.get("npt_description", report.npt_description)
                    report.responsible_party = npt_data.get("responsible_party", report.responsible_party)
                    report.cost_impact = npt_data.get("cost_impact", report.cost_impact)
                    report.status = npt_data.get("status", report.status)
                    report.updated_at = datetime.utcnow()
                    record_id = report.id
                else:
                    return None
            else:
                # Create new
                report = NPTReport(
                    well_id=npt_data["well_id"],
                    section_id=npt_data.get("section_id"),
                    report_id=npt_data.get("report_id"),
                    npt_date=npt_data["npt_date"],
                    start_time=npt_data["start_time"],
                    end_time=npt_data["end_time"],
                    duration_hours=npt_data["duration_hours"],
                    npt_category=npt_data["npt_category"],
                    npt_code=npt_data["npt_code"],
                    npt_description=npt_data["npt_description"],
                    responsible_party=npt_data.get("responsible_party", ""),
                    cost_impact=npt_data.get("cost_impact", 0.0),
                    status=npt_data.get("status", "Active"),
                    created_by=npt_data.get("created_by")
                )
                session.add(report)
                session.flush()
                record_id = report.id
            
            session.commit()
            logger.info(f"NPT report saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving NPT report: {e}")
            return None
        finally:
            session.close()

    def get_npt_reports(self, well_id: int = None, start_date: date = None, 
                       end_date: date = None, npt_code: str = None):
        """Get NPT reports"""
        session = self.create_session()
        try:
            query = session.query(NPTReport)
            
            if well_id:
                query = query.filter(NPTReport.well_id == well_id)
            if start_date:
                query = query.filter(NPTReport.npt_date >= start_date)
            if end_date:
                query = query.filter(NPTReport.npt_date <= end_date)
            if npt_code:
                query = query.filter(NPTReport.npt_code == npt_code)
            
            reports = query.order_by(NPTReport.npt_date.desc(), 
                                   NPTReport.start_time).all()
            
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
                    "updated_at": r.updated_at
                }
                for r in reports
            ]
            
        except Exception as e:
            logger.error(f"Error getting NPT reports: {e}")
            return []
        finally:
            session.close()

    def calculate_npt_statistics(self, well_id: int = None, start_date: date = None, 
                               end_date: date = None):
        """Calculate NPT statistics"""
        session = self.create_session()
        try:
            query = session.query(NPTReport)
            
            if well_id:
                query = query.filter(NPTReport.well_id == well_id)
            if start_date:
                query = query.filter(NPTReport.npt_date >= start_date)
            if end_date:
                query = query.filter(NPTReport.npt_date <= end_date)
            
            reports = query.all()
            
            total_npt_hours = sum(r.duration_hours or 0 for r in reports)
            total_npt_events = len(reports)
            
            # Calculate by category
            category_stats = {}
            for report in reports:
                category = report.npt_category or "Unknown"
                category_stats[category] = category_stats.get(category, 0) + (report.duration_hours or 0)
            
            # Calculate by code
            code_stats = {}
            for report in reports:
                code = report.npt_code or "Unknown"
                code_stats[code] = code_stats.get(code, 0) + (report.duration_hours or 0)
            
            return {
                "total_npt_hours": total_npt_hours,
                "total_npt_events": total_npt_events,
                "average_npt_per_event": total_npt_hours / total_npt_events if total_npt_events > 0 else 0,
                "category_stats": category_stats,
                "code_stats": code_stats,
                "reports": len(reports)
            }
            
        except Exception as e:
            logger.error(f"Error calculating NPT statistics: {e}")
            return {}
        finally:
            session.close()

    def save_activity_code(self, code_data: dict):
        """Save activity code"""
        session = self.create_session()
        try:
            # Check if code exists
            existing = session.query(ActivityCode).filter(
                ActivityCode.well_id == code_data["well_id"],
                ActivityCode.main_phase == code_data["main_phase"],
                ActivityCode.main_code == code_data["main_code"],
                ActivityCode.sub_code == code_data["sub_code"]
            ).first()
            
            if existing:
                # Update existing
                existing.code_name = code_data.get("code_name", existing.code_name)
                existing.code_description = code_data.get("code_description", existing.code_description)
                existing.is_productive = code_data.get("is_productive", existing.is_productive)
                existing.is_npt = code_data.get("is_npt", existing.is_npt)
                existing.color_code = code_data.get("color_code", existing.color_code)
                existing.updated_at = datetime.utcnow()
                record_id = existing.id
            else:
                # Create new
                code = ActivityCode(
                    well_id=code_data["well_id"],
                    main_phase=code_data["main_phase"],
                    main_code=code_data["main_code"],
                    sub_code=code_data["sub_code"],
                    code_name=code_data["code_name"],
                    code_description=code_data.get("code_description", ""),
                    is_productive=code_data.get("is_productive", True),
                    is_npt=code_data.get("is_npt", False),
                    color_code=code_data.get("color_code", "#0078D4"),
                    created_by=code_data.get("created_by")
                )
                session.add(code)
                session.flush()
                record_id = code.id
            
            session.commit()
            logger.info(f"Activity code saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving activity code: {e}")
            return None
        finally:
            session.close()

    def get_activity_codes(self, well_id: int = None, main_phase: str = None):
        """Get activity codes"""
        session = self.create_session()
        try:
            query = session.query(ActivityCode)
            
            if well_id:
                query = query.filter(ActivityCode.well_id == well_id)
            if main_phase:
                query = query.filter(ActivityCode.main_phase == main_phase)
            
            codes = query.order_by(ActivityCode.main_phase, 
                                 ActivityCode.main_code, 
                                 ActivityCode.sub_code).all()
            
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
                    "updated_at": c.updated_at
                }
                for c in codes
            ]
            
        except Exception as e:
            logger.error(f"Error getting activity codes: {e}")
            return []
        finally:
            session.close()

    def update_code_usage(self, well_id: int, code_data: list):
        """Update code usage statistics from daily reports"""
        session = self.create_session()
        try:
            for usage in code_data:
                code = session.query(ActivityCode).filter(
                    ActivityCode.well_id == well_id,
                    ActivityCode.sub_code == usage["sub_code"]
                ).first()
                
                if code:
                    code.usage_count += usage.get("count", 0)
                    code.total_hours += usage.get("hours", 0.0)
                    code.last_used = datetime.now().date()
                    code.updated_at = datetime.utcnow()
            
            session.commit()
            logger.info(f"Updated code usage for well {well_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating code usage: {e}")
            return False
        finally:
            session.close()

    def save_time_depth_data(self, data: dict):
        """Save time vs depth data"""
        session = self.create_session()
        try:
            point = TimeDepthData(
                well_id=data["well_id"],
                section_id=data.get("section_id"),
                timestamp=data["timestamp"],
                depth=data["depth"],
                activity_code=data.get("activity_code"),
                rop=data.get("rop"),
                wob=data.get("wob"),
                rpm=data.get("rpm"),
                torque=data.get("torque"),
                cumulative_time=data.get("cumulative_time"),
                daily_progress=data.get("daily_progress"),
                created_by=data.get("created_by")
            )
            session.add(point)
            session.flush()
            record_id = point.id
            
            session.commit()
            logger.info(f"Time depth data saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving time depth data: {e}")
            return None
        finally:
            session.close()

    def get_time_depth_data(self, well_id: int, start_date: datetime = None, 
                           end_date: datetime = None, min_depth: float = None, 
                           max_depth: float = None):
        """Get time vs depth data for charts"""
        session = self.create_session()
        try:
            query = session.query(TimeDepthData).filter(
                TimeDepthData.well_id == well_id
            )
            
            if start_date:
                query = query.filter(TimeDepthData.timestamp >= start_date)
            if end_date:
                query = query.filter(TimeDepthData.timestamp <= end_date)
            if min_depth:
                query = query.filter(TimeDepthData.depth >= min_depth)
            if max_depth:
                query = query.filter(TimeDepthData.depth <= max_depth)
            
            data = query.order_by(TimeDepthData.timestamp).all()
            
            return [
                {
                    "id": d.id,
                    "timestamp": d.timestamp,
                    "depth": d.depth,
                    "activity_code": d.activity_code,
                    "rop": d.rop,
                    "wob": d.wob,
                    "rpm": d.rpm,
                    "torque": d.torque,
                    "cumulative_time": d.cumulative_time,
                    "daily_progress": d.daily_progress
                }
                for d in data
            ]
            
        except Exception as e:
            logger.error(f"Error getting time depth data: {e}")
            return []
        finally:
            session.close()

    def save_rop_analysis(self, analysis_data: dict):
        """Save ROP analysis"""
        session = self.create_session()
        try:
            analysis = ROPAnalysis(
                well_id=analysis_data["well_id"],
                section_id=analysis_data.get("section_id"),
                analysis_date=analysis_data["analysis_date"],
                start_depth=analysis_data["start_depth"],
                end_depth=analysis_data["end_depth"],
                avg_rop=analysis_data.get("avg_rop"),
                max_rop=analysis_data.get("max_rop"),
                min_rop=analysis_data.get("min_rop"),
                rop_std_dev=analysis_data.get("rop_std_dev"),
                formation_type=analysis_data.get("formation_type"),
                bit_type=analysis_data.get("bit_type"),
                hydraulics_efficiency=analysis_data.get("hydraulics_efficiency"),
                drill_string_config=analysis_data.get("drill_string_config"),
                rop_chart_data=analysis_data.get("rop_chart_data"),
                depth_chart_data=analysis_data.get("depth_chart_data"),
                recommendations=analysis_data.get("recommendations"),
                efficiency_score=analysis_data.get("efficiency_score"),
                created_by=analysis_data.get("created_by")
            )
            session.add(analysis)
            session.flush()
            record_id = analysis.id
            
            session.commit()
            logger.info(f"ROP analysis saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving ROP analysis: {e}")
            return None
        finally:
            session.close()

    def get_rop_analysis(self, well_id: int = None, start_date: date = None, 
                        end_date: date = None):
        """Get ROP analysis data"""
        session = self.create_session()
        try:
            query = session.query(ROPAnalysis)
            
            if well_id:
                query = query.filter(ROPAnalysis.well_id == well_id)
            if start_date:
                query = query.filter(ROPAnalysis.analysis_date >= start_date)
            if end_date:
                query = query.filter(ROPAnalysis.analysis_date <= end_date)
            
            analyses = query.order_by(ROPAnalysis.analysis_date.desc()).all()
            
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
                    "efficiency_score": a.efficiency_score,
                    "recommendations": a.recommendations,
                    "created_at": a.created_at,
                    "updated_at": a.updated_at
                }
                for a in analyses
            ]
            
        except Exception as e:
            logger.error(f"Error getting ROP analysis: {e}")
            return []
        finally:
            session.close()

    def generate_time_depth_chart_data(self, well_id: int):
        """Generate chart data for time vs depth"""
        try:
            data = self.get_time_depth_data(well_id)
            
            if not data:
                return None
            
            # Prepare data for charts
            timestamps = [d["timestamp"] for d in data]
            depths = [d["depth"] for d in data]
            rop_values = [d["rop"] for d in data if d["rop"] is not None]
            
            chart_data = {
                "timestamps": timestamps,
                "depths": depths,
                "rop": rop_values,
                "data_points": len(data)
            }
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error generating time depth chart data: {e}")
            return None

    def generate_rop_chart_data(self, well_id: int, section_id: int = None):
        """Generate ROP chart data"""
        try:
            # Get drilling parameters
            drilling_params = self.get_drilling_parameters(well_id)
            
            if not drilling_params:
                return None
            
            # Extract ROP data
            rop_data = []
            depth_data = []
            
            # This would normally come from time series data
            # For now, create sample data
            for i in range(10):
                depth = 1000 + i * 100
                rop = 20 + (random.random() * 10)  # Random ROP between 20-30 m/hr
                rop_data.append({"depth": depth, "rop": rop})
                depth_data.append(depth)
            
            chart_data = {
                "depths": depth_data,
                "rop_values": [d["rop"] for d in rop_data],
                "avg_rop": sum([d["rop"] for d in rop_data]) / len(rop_data) if rop_data else 0,
                "max_rop": max([d["rop"] for d in rop_data]) if rop_data else 0,
                "min_rop": min([d["rop"] for d in rop_data]) if rop_data else 0
            }
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error generating ROP chart data: {e}")
            return None

    def auto_update_from_daily_report(self, report_id: int):
        """Auto-update planning data from daily report"""
        try:
            session = self.create_session()
            
            # Get daily report
            report = session.query(DailyReport).filter(
                DailyReport.id == report_id
            ).first()
            
            if not report:
                return False
            
            # Update NPT data from time logs
            npt_logs = session.query(TimeLog24H).filter(
                TimeLog24H.report_id == report_id,
                TimeLog24H.is_npt == True
            ).all()
            
            for log in npt_logs:
                npt_data = {
                    "well_id": report.well_id,
                    "section_id": report.section_id,
                    "report_id": report_id,
                    "npt_date": report.report_date,
                    "start_time": log.time_from,
                    "end_time": log.time_to,
                    "duration_hours": log.duration or 0,
                    "npt_category": "Daily Report",
                    "npt_code": log.main_code or "NPT",
                    "npt_description": log.activity_description or "NPT from daily report",
                    "responsible_party": "System",
                    "status": "Active"
                }
                self.save_npt_report(npt_data)
            
            # Update activity code usage
            all_logs = session.query(TimeLog24H).filter(
                TimeLog24H.report_id == report_id
            ).all()
            
            code_usage = {}
            for log in all_logs:
                code = log.main_code or "Unknown"
                if code not in code_usage:
                    code_usage[code] = {"count": 0, "hours": 0}
                code_usage[code]["count"] += 1
                code_usage[code]["hours"] += log.duration or 0
            
            # Convert to list for update
            usage_list = [{"sub_code": code, "count": data["count"], "hours": data["hours"]} 
                         for code, data in code_usage.items()]
            
            if usage_list:
                self.update_code_usage(report.well_id, usage_list)
            
            # Update time vs depth data
            if report.depth_2400:
                time_depth_data = {
                    "well_id": report.well_id,
                    "section_id": report.section_id,
                    "timestamp": datetime.combine(report.report_date, datetime.min.time()),
                    "depth": report.depth_2400,
                    "daily_progress": report.depth_2400 - (report.depth_0000 or 0)
                }
                self.save_time_depth_data(time_depth_data)
            
            session.close()
            logger.info(f"Auto-updated planning data from report {report_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error auto-updating from daily report: {e}")
            return False
            

    def save_export_template(self, template_data: dict):
        """Save export template to database"""
        session = self.create_session()
        try:
            if "id" in template_data and template_data["id"]:
                # Update existing template
                template = session.query(ExportTemplate).filter(
                    ExportTemplate.id == template_data["id"]
                ).first()
                if template:
                    template.name = template_data.get("name", template.name)
                    template.template_type = template_data.get("template_type", template.template_type)
                    template.description = template_data.get("description", template.description)
                    template.well_selection = template_data.get("well_selection", template.well_selection)
                    template.report_selection = template_data.get("report_selection", template.report_selection)
                    template.date_range = template_data.get("date_range", template.date_range)
                    template.format_settings = template_data.get("format_settings", template.format_settings)
                    template.options = template_data.get("options", template.options)
                    template.layout_config = template_data.get("layout_config", template.layout_config)
                    template.styling = template_data.get("styling", template.styling)
                    template.headers_footers = template_data.get("headers_footers", template.headers_footers)
                    template.is_default = template_data.get("is_default", template.is_default)
                    template.is_shared = template_data.get("is_shared", template.is_shared)
                    template.shared_with = template_data.get("shared_with", template.shared_with)
                    template.updated_at = datetime.utcnow()
                    record_id = template.id
                else:
                    return None
            else:
                # Create new template
                template = ExportTemplate(
                    name=template_data["name"],
                    template_type=template_data.get("template_type", "custom"),
                    description=template_data.get("description", ""),
                    well_selection=template_data.get("well_selection"),
                    report_selection=template_data.get("report_selection"),
                    date_range=template_data.get("date_range"),
                    format_settings=template_data.get("format_settings"),
                    options=template_data.get("options"),
                    layout_config=template_data.get("layout_config"),
                    styling=template_data.get("styling"),
                    headers_footers=template_data.get("headers_footers"),
                    is_default=template_data.get("is_default", False),
                    is_shared=template_data.get("is_shared", False),
                    shared_with=template_data.get("shared_with"),
                    created_by=template_data.get("created_by")
                )
                session.add(template)
                session.flush()
                record_id = template.id
            
            session.commit()
            logger.info(f"Export template saved: ID {record_id}")
            return record_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving export template: {e}")
            return None
        finally:
            session.close()

    def get_export_templates(self, template_type: str = None, created_by: int = None):
        """Get export templates"""
        session = self.create_session()
        try:
            query = session.query(ExportTemplate)
            
            if template_type:
                query = query.filter(ExportTemplate.template_type == template_type)
            if created_by:
                query = query.filter(
                    (ExportTemplate.created_by == created_by) | 
                    (ExportTemplate.is_shared == True)
                )
            
            templates = query.order_by(
                ExportTemplate.is_default.desc(),
                ExportTemplate.updated_at.desc()
            ).all()
            
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "template_type": t.template_type,
                    "description": t.description,
                    "well_selection": t.well_selection,
                    "report_selection": t.report_selection,
                    "date_range": t.date_range,
                    "format_settings": t.format_settings,
                    "options": t.options,
                    "layout_config": t.layout_config,
                    "styling": t.styling,
                    "headers_footers": t.headers_footers,
                    "is_default": t.is_default,
                    "is_shared": t.is_shared,
                    "shared_with": t.shared_with,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                    "created_by": t.created_by
                }
                for t in templates
            ]
            
        except Exception as e:
            logger.error(f"Error getting export templates: {e}")
            return []
        finally:
            session.close()

    def get_export_template_by_id(self, template_id: int):
        """Get export template by ID"""
        session = self.create_session()
        try:
            template = session.query(ExportTemplate).filter(
                ExportTemplate.id == template_id
            ).first()
            
            if template:
                return {
                    "id": template.id,
                    "name": template.name,
                    "template_type": template.template_type,
                    "description": template.description,
                    "well_selection": template.well_selection,
                    "report_selection": template.report_selection,
                    "date_range": template.date_range,
                    "format_settings": template.format_settings,
                    "options": template.options,
                    "layout_config": template.layout_config,
                    "styling": template.styling,
                    "headers_footers": template.headers_footers,
                    "is_default": template.is_default,
                    "is_shared": template.is_shared,
                    "shared_with": template.shared_with,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at,
                    "created_by": template.created_by
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting export template: {e}")
            return None
        finally:
            session.close()

    def delete_export_template(self, template_id: int):
        """Delete export template"""
        session = self.create_session()
        try:
            template = session.query(ExportTemplate).filter(
                ExportTemplate.id == template_id
            ).first()
            
            if template:
                session.delete(template)
                session.commit()
                logger.info(f"Export template deleted: ID {template_id}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting export template: {e}")
            return False
        finally:
            session.close()

    def set_default_template(self, template_id: int, template_type: str):
        """Set a template as default for its type"""
        session = self.create_session()
        try:
            # Clear existing default for this type
            session.query(ExportTemplate).filter(
                ExportTemplate.template_type == template_type,
                ExportTemplate.is_default == True
            ).update({"is_default": False})
            
            # Set new default
            template = session.query(ExportTemplate).filter(
                ExportTemplate.id == template_id
            ).first()
            
            if template:
                template.is_default = True
                template.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"Template {template_id} set as default for {template_type}")
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error setting default template: {e}")
            return False
        finally:
            session.close()

    def _get_default_tab_structure(self):
        """ساختار پیش‌فرض تب‌های گزارش روزانه"""
        return [
            # Tab 1: Well Info (بدون زیرتب)
            {
                'id': 1,
                'tab_type': 'wellinfo',
                'tab_name': '🛢️ Well Info',
                'tab_level': 0,
                'icon': '🛢️',
                'widget_class': 'WellInfoTab',
            },
            # Tab 2: Daily Report (با زیرتب‌های زمان)
            {
                'id': 2,
                'tab_type': 'daily',
                'tab_name': '📅 Daily Report',
                'tab_level': 0,
                'icon': '📅',
                'widget_class': 'DailyReportWidget',
                'children': [
                    {
                        'id': 21,
                        'tab_type': 'time_logs_24h',
                        'tab_name': '🕒 24 Hours',
                        'tab_level': 1,
                        'icon': '🕒',
                        'widget_class': 'time_24_tab',
                    },
                    {
                        'id': 22,
                        'tab_type': 'morning_tour',
                        'tab_name': '☀️ Morning Tour',
                        'tab_level': 1,
                        'icon': '☀️',
                        'widget_class': 'morning_tab',
                    }
                ]
            },
            # Tab 3: Drilling Report (زیرتب‌های حفاری)
            {
                'id': 3,
                'tab_type': 'drilling_report',
                'tab_name': '🧭 Drilling Report',
                'tab_level': 0,
                'icon': '🧭',
                'widget_class': 'DrillingReportWidget',
                'children': [
                    {'id': 31, 'tab_type': 'drilling_parameters', 'tab_name': '⚙️ Drilling Parameters', 'tab_level': 1, 'icon': '⚙️', 'widget_class': 'DrillingParametersTab'},
                    {'id': 32, 'tab_type': 'mud_report', 'tab_name': '🧪 Mud Report', 'tab_level': 1, 'icon': '🧪', 'widget_class': 'MudReportTab'},
                    {'id': 33, 'tab_type': 'cement_report', 'tab_name': '🏗️ Cement Report', 'tab_level': 1, 'icon': '🏗️', 'widget_class': 'CementReportTab'},
                    {'id': 34, 'tab_type': 'casing_tally', 'tab_name': '📏 Casing Tally', 'tab_level': 1, 'icon': '📏', 'widget_class': 'CasingTallyWidget'},
                    {'id': 35, 'tab_type': 'casing_report', 'tab_name': '🔩 Casing Report', 'tab_level': 1, 'icon': '🔩', 'widget_class': 'CasingReportTab'},
                    {'id': 36, 'tab_type': 'wellbore_schematic', 'tab_name': '📊 Wellbore Schematic', 'tab_level': 1, 'icon': '📊', 'widget_class': 'WellboreSchematicTab'}
                ]
            },
            # Tab 4: Downhole Widget (زیرتب‌های زیرسطحی)
            {
                'id': 4,
                'tab_type': 'downhole',
                'tab_name': '📡 Downhole',
                'tab_level': 0,
                'icon': '📡',
                'widget_class': 'DownholeWidget',
                'children': [
                    {'id': 41, 'tab_type': 'bit_record', 'tab_name': '📝 Bit Record', 'tab_level': 1, 'icon': '📝', 'widget_class': 'BitRecordManager'},
                    {'id': 42, 'tab_type': 'bha', 'tab_name': '🔧 BHA', 'tab_level': 1, 'icon': '🔧', 'widget_class': 'BHAManager'},
                    {'id': 43, 'tab_type': 'downhole_equipment', 'tab_name': '⚙️ Downhole Equipment', 'tab_level': 1, 'icon': '⚙️', 'widget_class': 'DownholeEquipmentManager'},
                    {'id': 44, 'tab_type': 'formation_evaluation', 'tab_name': '🏔️ Formation Evaluation', 'tab_level': 1, 'icon': '🏔️', 'widget_class': 'FormationManager'}
                ]
            },
            # Tab 5: Equipment Widget (زیرتب‌های تجهیزات)
            {
                'id': 5,
                'tab_type': 'equipment',
                'tab_name': '🏗️ Equipment',
                'tab_level': 0,
                'icon': '🏗️',
                'widget_class': 'EquipmentWidget',
                'children': [
                    {'id': 51, 'tab_type': 'rig_equipment', 'tab_name': '🏗️ Rig Equipment', 'tab_level': 1, 'icon': '🏗️', 'widget_class': 'RigEquipmentTab'},
                    {'id': 52, 'tab_type': 'inventory', 'tab_name': '📦 Inventory', 'tab_level': 1, 'icon': '📦', 'widget_class': 'InventoryTab'},
                    {'id': 53, 'tab_type': 'drill_pipe', 'tab_name': '🔩 Drill Pipe', 'tab_level': 1, 'icon': '🔩', 'widget_class': 'DrillPipeTab'},
                    {'id': 54, 'tab_type': 'solid_control', 'tab_name': '🔄 Solid Control', 'tab_level': 1, 'icon': '🔄', 'widget_class': 'SolidControlTab'}
                ]
            },
            # Tab 6: Trajectory Widget
            {
                'id': 6,
                'tab_type': 'trajectory',
                'tab_name': '📈 Trajectory',
                'tab_level': 0,
                'icon': '📈',
                'widget_class': 'TrajectoryWidget',
                'children': [
                    {'id': 61, 'tab_type': 'trip_sheet', 'tab_name': '📝 Trip Sheet', 'tab_level': 1, 'icon': '📝', 'widget_class': 'TripSheetTab'},
                    {'id': 62, 'tab_type': 'survey_data', 'tab_name': '🧭 Survey Data', 'tab_level': 1, 'icon': '🧭', 'widget_class': 'SurveyDataTab'},
                    {'id': 63, 'tab_type': 'trajectory_plot', 'tab_name': '📊 Trajectory Plot', 'tab_level': 1, 'icon': '📊', 'widget_class': 'TrajectoryPlotTab'}
                ]
            },
            # Tab 7: Logistics Widget
            {
                'id': 7,
                'tab_type': 'logistics',
                'tab_name': '🚚 Logistics',
                'tab_level': 0,
                'icon': '🚚',
                'widget_class': 'LogisticsWidget',
                'children': [
                    {'id': 71, 'tab_type': 'personnel_logistics', 'tab_name': '👥 Personnel & Logistics', 'tab_level': 1, 'icon': '👥', 'widget_class': 'PersonnelLogisticsTab'},
                    {'id': 72, 'tab_type': 'fuel_water', 'tab_name': '⛽ Fuel & Water', 'tab_level': 1, 'icon': '⛽', 'widget_class': 'FuelWaterTab'},
                    {'id': 73, 'tab_type': 'transport_log', 'tab_name': '🚤 Transport Log', 'tab_level': 1, 'icon': '🚤', 'widget_class': 'TransportLogTab'}
                ]
            },
            # Tab 8: Safety Widget
            {
                'id': 8,
                'tab_type': 'safety',
                'tab_name': '🛡️ Safety',
                'tab_level': 0,
                'icon': '🛡️',
                'widget_class': 'SafetyWidget',
                'children': [
                    {'id': 81, 'tab_type': 'safety_bop', 'tab_name': '🛡️ Safety & BOP', 'tab_level': 1, 'icon': '🛡️', 'widget_class': 'SafetyBOPTab'},
                    {'id': 82, 'tab_type': 'waste_management', 'tab_name': '🗑️ Waste Management', 'tab_level': 1, 'icon': '🗑️', 'widget_class': 'WasteManagementTab'}
                ]
            },
            # Tab 9: Services Widget
            {
                'id': 9,
                'tab_type': 'services',
                'tab_name': '🔌 Services',
                'tab_level': 0,
                'icon': '🔌',
                'widget_class': 'ServicesWidget',
                'children': [
                    {'id': 91, 'tab_type': 'service_company', 'tab_name': '🏢 Service Companies', 'tab_level': 1, 'icon': '🏢', 'widget_class': 'ServiceCompanyTab'},
                    {'id': 92, 'tab_type': 'material_handling', 'tab_name': '📦 Material Handling', 'tab_level': 1, 'icon': '📦', 'widget_class': 'MaterialHandlingTab'}
                ]
            },
            # Tab 10: Planning Widget
            {
                'id': 10,
                'tab_type': 'planning',
                'tab_name': '📋 Planning',
                'tab_level': 0,
                'icon': '📋',
                'widget_class': 'PlanningWidget',
                'children': [
                    {'id': 101, 'tab_type': 'seven_days_lookahead', 'tab_name': '📅 7 Days Lookahead', 'tab_level': 1, 'icon': '📅', 'widget_class': 'SevenDaysLookaheadTab'},
                    {'id': 102, 'tab_type': 'npt_report', 'tab_name': '⏱️ NPT Report', 'tab_level': 1, 'icon': '⏱️', 'widget_class': 'NPTReportTab'},
                    {'id': 103, 'tab_type': 'code_management', 'tab_name': '🏷️ Code Management', 'tab_level': 1, 'icon': '🏷️', 'widget_class': 'CodeManagementTab'},
                    {'id': 104, 'tab_type': 'time_vs_depth', 'tab_name': '📈 Time vs Depth', 'tab_level': 1, 'icon': '📈', 'widget_class': 'TimeVsDepthTab'},
                    {'id': 105, 'tab_type': 'rop_chart', 'tab_name': '📊 ROP Chart', 'tab_level': 1, 'icon': '📊', 'widget_class': 'ROPChartTab'}
                ]
            },
            # Tab 11: Export Widget
            {
                'id': 11,
                'tab_type': 'export',
                'tab_name': '📤 Export',
                'tab_level': 0,
                'icon': '📤',
                'widget_class': 'ExportWidget',
                'children': [
                    {'id': 111, 'tab_type': 'daily_export', 'tab_name': '📤 Daily Export', 'tab_level': 1, 'icon': '📤', 'widget_class': 'DailyExportTab'},
                    {'id': 112, 'tab_type': 'eowr_export', 'tab_name': '📑 End of Well Report', 'tab_level': 1, 'icon': '📑', 'widget_class': 'EOWRExportTab'},
                    {'id': 113, 'tab_type': 'batch_export', 'tab_name': '📊 Batch Export', 'tab_level': 1, 'icon': '📊', 'widget_class': 'BatchExportTab'}
                ]
            },
            # Tab 12: Analysis Widget (بدون زیرتب)
            {
                'id': 12,
                'tab_type': 'analysis',
                'tab_name': '📊 Analysis',
                'tab_level': 0,
                'icon': '📊',
                'widget_class': 'AnalysisWidget',
            }
        ]
    
    def get_report_tab_structure(self, report_id: int):
        """دریافت ساختار تب‌های یک گزارش از دیتابیس"""
        session = self.create_session()
        try:
            # اول ببین این گزارش ساختار سفارشی دارد یا نه
            details = session.query(DailyReportDetail).filter(
                DailyReportDetail.report_id == report_id
            ).order_by(DailyReportDetail.tab_level, DailyReportDetail.tab_order).all()
            
            if details:
                # ساخت درخت از تب‌های موجود
                return self._build_tab_tree(details)
            else:
                # ساختار پیش‌فرض را برگردان
                return self._get_default_tab_structure()
                
        except Exception as e:
            logger.error(f"Error getting report tab structure: {e}")
            return self._get_default_tab_structure()
        finally:
            session.close()

    def _build_tab_tree(self, details):
        """ساخت درخت تب‌ها از لیست صاف"""
        # ایجاد مپ بر اساس ID
        tab_map = {}
        root_tabs = []
        
        # اول همه تب‌ها را در مپ قرار بده
        for detail in details:
            tab_data = {
                'id': detail.id,
                'tab_type': detail.tab_type,
                'tab_name': detail.tab_name,
                'widget_class': detail.widget_class,
                'icon': detail.icon,
                'tab_level': detail.tab_level,
                'tab_order': detail.tab_order,
                'children': []
            }
            tab_map[detail.id] = tab_data
            
            if detail.tab_level == 0:
                root_tabs.append(tab_data)
        
        # سپس فرزندان را به والدین وصل کن
        for detail in details:
            if detail.parent_tab_id and detail.parent_tab_id in tab_map:
                tab_map[detail.parent_tab_id]['children'].append(tab_map[detail.id])
        
        # فرزندان را بر اساس order مرتب کن
        for tab in tab_map.values():
            if tab['children']:
                tab['children'] = sorted(tab['children'], key=lambda x: x['tab_order'])
        
        # تب‌های ریشه را مرتب کن
        return sorted(root_tabs, key=lambda x: x['tab_order'])

    def initialize_report_tabs(self, report_id: int):
        """مقداردهی اولیه تب‌های یک گزارش جدید"""
        session = self.create_session()
        try:
            # بررسی کن که آیا قبلاً تب‌ها ایجاد شده‌اند
            existing = session.query(DailyReportDetail).filter(
                DailyReportDetail.report_id == report_id
            ).count()
            
            if existing > 0:
                logger.info(f"Report {report_id} already has {existing} tabs")
                return
                
            # ساختار پیش‌فرض را بگیر
            default_structure = self._get_default_tab_structure()
            
            # تب‌ها را در دیتابیس ذخیره کن
            self._save_tab_structure_to_db(session, report_id, default_structure)
            
            session.commit()
            logger.info(f"Initialized tabs for report {report_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error initializing report tabs: {e}")
        finally:
            session.close()

    def _save_tab_structure_to_db(self, session, report_id: int, structure, parent_id=None, level=0):
        """ذخیره ساختار تب در دیتابیس"""
        for i, tab in enumerate(structure):
            # ایجاد رکورد تب
            tab_detail = DailyReportDetail(
                report_id=report_id,
                tab_type=tab['tab_type'],
                tab_name=tab['tab_name'],
                widget_class=tab.get('widget_class'),
                icon=tab.get('icon', self._get_default_icon(tab['tab_type'])),
                parent_tab_id=parent_id,
                tab_level=level,
                tab_order=i
            )
            session.add(tab_detail)
            session.flush()  # برای گرفتن ID
            
            # ذخیره فرزندان به صورت بازگشتی
            children = tab.get('children', [])
            if children:
                self._save_tab_structure_to_db(session, report_id, children, tab_detail.id, level + 1)
                
    def _get_default_icon(self, tab_type):
        """آیکون پیش‌فرض بر اساس نوع تب"""
        icon_map = {
            # Main tabs
            'wellinfo': '🛢️',
            'daily': '📅',
            'drilling_report': '🧭',
            'downhole': '📡',
            'equipment': '🏗️',
            'trajectory': '📈',
            'logistics': '🚚',
            'safety': '🛡️',
            'services': '🔌',
            'planning': '📋',
            'export': '📤',
            'analysis': '📊',
            
            # Daily Report subtabs
            'time_logs_24h': '🕒',
            'morning_tour': '☀️',
            
            # Drilling Report subtabs
            'drilling_parameters': '⚙️',
            'mud_report': '🧪',
            'cement_report': '🏗️',
            'casing_tally': '📏',
            'casing_report': '🔩',
            'wellbore_schematic': '📊',
            
            # Downhole subtabs
            'bit_record': '📝',
            'bha': '🔧',
            'downhole_equipment': '⚙️',
            'formation_evaluation': '🏔️',
            
            # Equipment subtabs
            'rig_equipment': '🏗️',
            'inventory': '📦',
            'drill_pipe': '🔩',
            'solid_control': '🔄',
            
            # Trajectory subtabs
            'trip_sheet': '📝',
            'survey_data': '🧭',
            'trajectory_plot': '📊',
            
            # Logistics subtabs
            'personnel_logistics': '👥',
            'fuel_water': '⛽',
            'transport_log': '🚤',
            
            # Safety subtabs
            'safety_bop': '🛡️',
            'waste_management': '🗑️',
            
            # Services subtabs
            'service_company': '🏢',
            'material_handling': '📦',
            
            # Planning subtabs
            'seven_days_lookahead': '📅',
            'npt_report': '⏱️',
            'code_management': '🏷️',
            'time_vs_depth': '📈',
            'rop_chart': '📊',
            
            # Export subtabs
            'daily_export': '📤',
            'eowr_export': '📑',
            'batch_export': '📊'
        }
        return icon_map.get(tab_type, '📄')  # آیکون پیش‌فرض برای تب‌های ناشناخته