"""
Tabs Package - شامل تمام تب‌های برنامه
"""

from .home_tab import HomeTab
from .w1_well_info import WellInfoTab
from .w2_daily_report import DailyReportWidget
from .w3_drilling_report import DrillingReportWidget

__all__ = [
    'HomeTab',
    'WellInfoTab',
    'DailyReportWidget',
    'DrillingReportWidget'
]