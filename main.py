import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.append(str(src_path))

from PyQt5.QtWidgets import QApplication
from src.gui.main_window import BacktestApp
from src.utils.logger import log_app_info


def main():
    """Main application entry point"""
    try:
        log_app_info("Starting application...")

        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        window = BacktestApp()
        window.show()

        log_app_info("Application GUI loaded successfully")

        sys.exit(app.exec_())

    except Exception as e:
        print(f"Failed to start application: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()