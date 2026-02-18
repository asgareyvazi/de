"""
UI Utilities - توابع کمکی برای رابط کاربری
"""
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *


def create_styled_button(text, color="#0078d4", icon=None, tooltip=""):
    """ایجاد دکمه با استایل"""
    btn = QPushButton(text)
    
    if icon:
        btn.setIcon(QIcon(icon))
    
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: white;
            border: 1px solid {color};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        }}
        QPushButton:hover {{
            background-color: #106ebe;
            border-color: #106ebe;
        }}
        QPushButton:pressed {{
            background-color: #005a9e;
            border-color: #005a9e;
        }}
        QPushButton:disabled {{
            background-color: #6c757d;
            border-color: #6c757d;
        }}
    """)
    
    if tooltip:
        btn.setToolTip(tooltip)
    
    return btn


def show_success_message(parent, message):
    """نمایش پیام موفقیت"""
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("✅ Success")
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()


def show_error_message(parent, message):
    """نمایش پیام خطا"""
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("❌ Error")
    msg_box.setText(message)
    msg_box.setDetailedText(str(message))
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()


def show_warning_message(parent, message):
    """نمایش پیام هشدار"""
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setWindowTitle("⚠️ Warning")
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()


def center_on_screen(widget):
    """مرتب کردن ویجت در وسط صفحه"""
    screen = QApplication.primaryScreen().geometry()
    size = widget.geometry()
    widget.move(
        (screen.width() - size.width()) // 2,
        (screen.height() - size.height()) // 2
    )