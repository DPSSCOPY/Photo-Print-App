from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QTransform
from PyQt5.QtCore import Qt

app = QApplication([])
pixmap = QPixmap(300, 400)
pixmap.fill(Qt.red)

transform = QTransform().rotate(90)
rotated = pixmap.transformed(transform, Qt.SmoothTransformation)
print("Original size:", pixmap.width(), pixmap.height())
print("Rotated size:", rotated.width(), rotated.height())

scaled = rotated.scaled(40, 30, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
print("Scaled size:", scaled.width(), scaled.height())
