import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPdfWriter, QPageSize, QPageLayout, QPainter, QColor, QFont
from PyQt5.QtCore import QSizeF, QMarginsF

app = QApplication(sys.argv)
pdf = QPdfWriter("test.pdf")
pdf.setPageSize(QPageSize(QSizeF(210.0, 297.0), QPageSize.Millimeter))
pdf.setPageMargins(QMarginsF(0, 0, 0, 0))
pdf.setResolution(300)

painter = QPainter(pdf)
painter.fillRect(0, 0, int(210 * 300 / 25.4), int(297 * 300 / 25.4), QColor("red"))
painter.end()
print("Saved test.pdf")
