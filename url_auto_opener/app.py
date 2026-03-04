import sys

from PyQt6.QtWidgets import QApplication

from .state import StateRepository
from .url_service import UrlService
from .window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow(StateRepository(), UrlService())
    window.show()
    sys.exit(app.exec())
