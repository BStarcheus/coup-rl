from menu import *
from board import *
import sys

class Coup(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Coup')
        self.menu_widget = Menu()
        self.menu_widget.start_btn.clicked.connect(self.start_game)
        self.setCentralWidget(self.menu_widget)
        self.setFocus()

    def start_game(self):
        self.board_widget = Board()
        self.setCentralWidget(self.board_widget)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = Coup()
    main_app.show()
    sys.exit(app.exec())