import sys

from PySide6.QtWidgets import QApplication

from app import AppController


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Reactor Simulator")
    controller = AppController(app)
    app._controller = controller
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
