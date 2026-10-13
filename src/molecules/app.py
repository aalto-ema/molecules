"""Desktop entry point."""

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from molecules.ui.window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Molecules")
    app.setOrganizationName("Molecules")
    window = MainWindow()
    window.show()
    return app.exec()
