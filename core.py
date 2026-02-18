"""
Core Functions - Centralized helper functions
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class CentralFunctions:
    """Centralized functions for repetitive tasks"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.current_selection = {"type": None, "id": None}
    
    def set_current_selection(self, item_type: str, item_id: int):
        """Set current selected item"""
        self.current_selection = {"type": item_type, "id": item_id}
    
    def get_current_well_id(self) -> Optional[int]:
        """Get current well ID if selected"""
        if self.current_selection["type"] == "well":
            return self.current_selection["id"]
        return None
    
    def validate_well_data(self, data: Dict) -> Dict[str, str]:
        """Validate well information data"""
        errors = {}
        
        # Required fields
        required_fields = ["name", "project_id", "well_type"]
        for field in required_fields:
            if not data.get(field):
                errors[field] = f"{field.replace('_', ' ').title()} is required"
        
        # Numeric field validation
        numeric_fields = ["target_depth", "elevation", "water_depth"]
        for field in numeric_fields:
            if field in data and data[field]:
                try:
                    float(data[field])
                except (ValueError, TypeError):
                    errors[field] = f"{field.replace('_', ' ').title()} must be a number"
        
        return errors
    def validate_drilling_data(self, data: Dict) -> Dict[str, str]:
        """اعتبارسنجی داده‌های حفاری"""
        return self.drilling_manager.validate_drilling_data(data) if hasattr(self, 'drilling_manager') else {}
    
    def validate_mud_data(self, data: Dict) -> Dict[str, str]:
        """اعتبارسنجی داده‌های گل"""
        errors = {}
        
        # بررسی فیلدهای ضروری
        if not data.get('mud_type'):
            errors['mud_type'] = "Mud type is required"
        
        # اعتبارسنجی مقادیر
        numeric_fields = ['mw', 'pv', 'yp', 'ph']
        for field in numeric_fields:
            value = data.get(field)
            if value is not None:
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors[field] = f"{field.upper()} must be a number"
        
        return errors
    
    def validate_date_range(self, start_date, end_date):
        """اعتبارسنجی محدوده تاریخ"""
        if start_date and end_date and start_date > end_date:
            return "Start date must be before end date"
        return ""
    def get_current_selection_info(self):
        """Get detailed info about current selection"""
        return {
            "type": self.current_selection["type"],
            "id": self.current_selection["id"],
            "name": self.get_current_item_name()  # باید پیاده‌سازی شود
        }

    def get_current_item_name(self):
        """Get name of current selected item"""
        if self.current_selection["type"] == "well" and self.current_selection["id"]:
            # از db_manager برای گرفتن نام استفاده کنید
            if self.db_manager:
                well = self.db_manager.get_well_by_id(self.current_selection["id"])
                return well.get("name", "Unknown") if well else "Unknown"
        return "None"