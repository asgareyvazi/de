# utils/widget_helpers.py
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

def make_scrollable(widget_class):
    """Decorator to make any widget scrollable"""
    class ScrollableWidget(QScrollArea):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.setWidgetResizable(True)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # Create the original widget
            self.content_widget = widget_class(*args, **kwargs)
            self.setWidget(self.content_widget)
            
            # Pass through attribute access
            self.__dict__.update(self.content_widget.__dict__)
            
        def __getattr__(self, name):
            # Forward attribute access to content widget
            return getattr(self.content_widget, name)
    
    return ScrollableWidget

# سپس در w10_Planning_Widget.py:
# from utils.widget_helpers import make_scrollable

# و هر کلاس تب را با دکوراتور بپوشانید:
# @make_scrollable
# class NPTReportTab(QWidget):
#     ...