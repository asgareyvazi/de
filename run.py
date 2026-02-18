"""
DrillMaster - Runner Script
"""

import sys
import logging

# تنظیم logging برای پشتیبانی از UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("drillmaster.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from app import DrillMasterApp


def main():
    """Main entry point"""
    print("🚀 Starting DrillMaster...")

    try:
        app = DrillMasterApp(sys.argv)
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Application failed to start: {e}")
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
