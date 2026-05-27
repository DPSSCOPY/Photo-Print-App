import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QGroupBox, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QRadioButton, 
                             QCheckBox, QSlider, QGridLayout, QSizePolicy, QFileDialog)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap

class PreviewWidget(QWidget):
    """ Custom Widget សម្រាប់គូរទិដ្ឋភាពក្រដាស និងក្រឡារូបថត (Live Print Preview) """
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 500)
        self.setStyleSheet("background-color: #dbe2e9;")
        self.image_pixmap = None
        self.cols = 6
        self.rows = 6
        self.gap_px = 5

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # គូរផ្ទៃក្រដាសពណ៌សចំកណ្តាល
        paper_width = self.width() * 0.7
        paper_height = self.height() * 0.9
        paper_x = (self.width() - paper_width) / 2
        paper_y = (self.height() - paper_height) / 2
        
        painter.fillRect(int(paper_x), int(paper_y), int(paper_width), int(paper_height), QColor(255, 255, 255))
        
        # គូរបន្ទាត់គែមក្រដាស (Margins - Dashed Line)
        margin = 20
        pen = QPen(QColor(180, 180, 180), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(int(paper_x + margin), int(paper_y + margin), int(paper_width - margin*2), int(paper_height - margin*2))

        # គូរក្រឡារូបថតតូចៗ (3x4 cm ឧទាហរណ៍)
        pen = QPen(QColor(200, 200, 200), 1, Qt.SolidLine)
        painter.setPen(pen)
        
        cols, rows = self.cols, self.rows
        if cols > 0 and rows > 0:
            cell_w = (paper_width - margin*2 - (cols-1)*self.gap_px) / cols
            cell_h = (paper_height - margin*2 - (rows-1)*self.gap_px) / rows
            
            start_x = paper_x + margin
            start_y = paper_y + margin
            
            painter.setFont(QFont("Arial", 8))
            for row in range(rows):
                for col in range(cols):
                    cx = start_x + col * (cell_w + self.gap_px)
                    cy = start_y + row * (cell_h + self.gap_px)
                    
                    if self.image_pixmap and not self.image_pixmap.isNull():
                        painter.drawPixmap(QRectF(cx, cy, cell_w, cell_h).toRect(), self.image_pixmap)
                    else:
                        painter.drawRect(int(cx), int(cy), int(cell_w), int(cell_h))
                        painter.setPen(QColor(100, 100, 100))
                        painter.drawText(QRectF(cx, cy, cell_w, cell_h), Qt.AlignCenter, "3x4 cm")
                        painter.setPen(pen)

class PhotoPrintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("កម្មវិធីជំនួយការបោះពុម្ពរូបថត - Photo Print Studio")
        self.resize(1280, 720)
        self.initUI()

    def initUI(self):
        # Main Widget and Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ---------------- LEFT PANEL ----------------
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)

        title_lbl = QLabel("<b>បោះពុម្ពរូបថត / Photo Printer</b>")
        title_lbl.setFont(QFont("Khmer OS Battambang", 12))
        left_layout.addWidget(title_lbl)

        # 1. ជ្រើសរើសរូបភាព
        gb_photo = QGroupBox("១. ជ្រើសរើសរូបភាព / Choose Photo")
        gb_photo_layout = QVBoxLayout()
        self.btn_load = QPushButton("បញ្ចូលរូបភាព / Load Image")
        self.btn_load.setStyleSheet("background-color: #0084c7; color: white; padding: 10px; border-radius: 5px;")
        self.btn_load.clicked.connect(self.load_image)
        gb_photo_layout.addWidget(self.btn_load)
        self.lbl_image_status = QLabel("<i>មិនទាន់មានរូបភាព / No image loaded</i>")
        gb_photo_layout.addWidget(self.lbl_image_status)
        gb_photo.setLayout(gb_photo_layout)
        left_layout.addWidget(gb_photo)

        # 2. ទំហំក្រដាស
        gb_paper = QGroupBox("២. ទំហំក្រដាស / Paper Settings")
        gb_paper_layout = QVBoxLayout()
        gb_paper_layout.addWidget(QLabel("ទំហំក្រដាស / Size:"))
        cb_paper_size = QComboBox()
        cb_paper_size.addItem("A4 (210 x 297 mm)")
        gb_paper_layout.addWidget(cb_paper_size)
        
        h_size_layout = QHBoxLayout()
        v_width = QVBoxLayout()
        v_width.addWidget(QLabel("ទទឹង / Width (mm):"))
        self.sb_width = QDoubleSpinBox(); self.sb_width.setMaximum(1000); self.sb_width.setValue(210.0)
        self.sb_width.valueChanged.connect(self.calculate_layout)
        v_width.addWidget(self.sb_width)
        
        v_height = QVBoxLayout()
        v_height.addWidget(QLabel("កម្ពស់ / Height (mm):"))
        self.sb_height = QDoubleSpinBox(); self.sb_height.setMaximum(1000); self.sb_height.setValue(297.0)
        self.sb_height.valueChanged.connect(self.calculate_layout)
        v_height.addWidget(self.sb_height)
        
        h_size_layout.addLayout(v_width)
        h_size_layout.addLayout(v_height)
        gb_paper_layout.addLayout(h_size_layout)
        
        gb_paper_layout.addWidget(QLabel("ទិសដៅ / Orientation:"))
        h_ori_layout = QHBoxLayout()
        rb_port = QRadioButton("បញ្ឈរ / Port.")
        rb_port.setChecked(True)
        rb_land = QRadioButton("ផ្តេក / Land.")
        h_ori_layout.addWidget(rb_port)
        h_ori_layout.addWidget(rb_land)
        gb_paper_layout.addLayout(h_ori_layout)
        gb_paper.setLayout(gb_paper_layout)
        left_layout.addWidget(gb_paper)

        # 3. ទំហំរូបថត
        gb_preset = QGroupBox("៣. ទំហំរូបថត / Photo Preset")
        gb_preset_layout = QVBoxLayout()
        gb_preset_layout.addWidget(QLabel("ទំហំកាត់ / Preset:"))
        cb_preset = QComboBox()
        cb_preset.addItem("3x4 cm (កាត កាត)")
        gb_preset_layout.addWidget(cb_preset)
        
        h_preset_size = QHBoxLayout()
        v_p_width = QVBoxLayout()
        v_p_width.addWidget(QLabel("ទទឹង / Width (cm):"))
        self.sb_p_width = QDoubleSpinBox(); self.sb_p_width.setValue(3.00)
        self.sb_p_width.valueChanged.connect(self.calculate_layout)
        v_p_width.addWidget(self.sb_p_width)
        
        v_p_height = QVBoxLayout()
        v_p_height.addWidget(QLabel("កម្ពស់ / Height (cm):"))
        self.sb_p_height = QDoubleSpinBox(); self.sb_p_height.setValue(4.00)
        self.sb_p_height.valueChanged.connect(self.calculate_layout)
        v_p_height.addWidget(self.sb_p_height)
        
        h_preset_size.addLayout(v_p_width)
        h_preset_size.addLayout(v_p_height)
        gb_preset_layout.addLayout(h_preset_size)
        
        gb_preset_layout.addWidget(QCheckBox("ស្វែងរកប្រព័ន្ធសម្រួលភាពស័ក្ដិសម / Optimize Fit"))
        gb_preset.setLayout(gb_preset_layout)
        left_layout.addWidget(gb_preset)

        # ---------------- MIDDLE PANEL ----------------
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_title = QLabel("<b>ទិដ្ឋភាពបង្ហាញជាក់ស្តែង / LIVE PRINT PREVIEW</b>")
        mid_title.setAlignment(Qt.AlignCenter)
        mid_title.setFont(QFont("Khmer OS Battambang", 11))
        mid_layout.addWidget(mid_title)
        
        self.preview_canvas = PreviewWidget()
        mid_layout.addWidget(self.preview_canvas)

        # ---------------- RIGHT PANEL ----------------
        right_panel = QWidget()
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignTop)

        # 4. គម្លាត និងគែម
        gb_margin = QGroupBox("៤. គម្លាត និងគែម / Gaps Margins")
        gb_margin_layout = QVBoxLayout()
        
        h_m_layout1 = QHBoxLayout()
        h_m_layout1.addWidget(QLabel("គែមទំព័រ / Page Margin:"))
        self.sb_margin = QSpinBox(); self.sb_margin.setValue(10); self.sb_margin.setSuffix(" mm")
        self.sb_margin.valueChanged.connect(self.calculate_layout)
        h_m_layout1.addWidget(self.sb_margin)
        gb_margin_layout.addLayout(h_m_layout1)
        gb_margin_layout.addWidget(QSlider(Qt.Horizontal))
        
        h_m_layout2 = QHBoxLayout()
        h_m_layout2.addWidget(QLabel("ចន្លោះរូបថត / Photo Gap:"))
        self.sb_gap = QSpinBox(); self.sb_gap.setValue(2); self.sb_gap.setSuffix(" mm")
        self.sb_gap.valueChanged.connect(self.calculate_layout)
        h_m_layout2.addWidget(self.sb_gap)
        gb_margin_layout.addLayout(h_m_layout2)
        gb_margin_layout.addWidget(QSlider(Qt.Horizontal))
        
        gb_margin_layout.addWidget(QCheckBox("បង្ហាញបន្ទាត់សម្រាប់កាត់ / Show Border Line"))
        gb_margin.setLayout(gb_margin_layout)
        right_layout.addWidget(gb_margin)

        # 5. ការរៀបចំ និងចំនួន
        gb_layout = QGroupBox("៥. ការរៀបចំ និងចំនួន / Layout Qty")
        gb_layout_layout = QVBoxLayout()
        gb_layout_layout.addWidget(QRadioButton("ពេញក្រដាស / Max Printable (Auto)"))
        rb_custom = QRadioButton("កំណត់ចំនួន / Custom Count (Auto)")
        rb_custom.setChecked(True)
        gb_layout_layout.addWidget(rb_custom)
        
        h_qty = QHBoxLayout()
        slider_qty = QSlider(Qt.Horizontal)
        sb_qty = QSpinBox(); sb_qty.setValue(36)
        h_qty.addWidget(slider_qty)
        h_qty.addWidget(sb_qty)
        gb_layout_layout.addLayout(h_qty)
        
        gb_layout_layout.addWidget(QRadioButton("រៀបចំដោយសេរី / Manual Layout (Drag)"))
        gb_layout.setLayout(gb_layout_layout)
        right_layout.addWidget(gb_layout)

        right_layout.addStretch()

        # Action Buttons
        self.lbl_status = QLabel("<b>អាចដាក់បាន: 36 / 36 រូបភាព (បញ្ឈរ (Portrait))</b>")
        self.lbl_status.setStyleSheet("color: #16947b;")
        right_layout.addWidget(self.lbl_status)

        btn_save_pdf = QPushButton("រក្សាទុក PDF / Save PDF")
        btn_save_pdf.setStyleSheet("background-color: #128c7e; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        
        btn_print = QPushButton("បោះពុម្ព / Print")
        btn_print.setStyleSheet("background-color: #5850ec; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        
        btn_support = QPushButton("ឧបត្ថម្ភ / Support Creator")
        btn_support.setStyleSheet("background-color: #f59e0b; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")

        right_layout.addWidget(btn_save_pdf)
        right_layout.addWidget(btn_print)
        right_layout.addWidget(btn_support)

        # បញ្ចូល Panel ទាំង3 ទៅក្នុង Layout គោល
        main_layout.addWidget(left_panel)
        main_layout.addWidget(mid_panel, 1) # អនុញ្ញាតឲ្យផ្ទាំងកណ្តាលរីកធំជាងគេ
        main_layout.addWidget(right_panel)
        
        # ធ្វើការគណនាបឋមនៅពេលចាប់ផ្តើមកម្មវិធី
        self.calculate_layout()

    def load_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូបភាព / Choose Photo", "", "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        if file_name:
            self.lbl_image_status.setText(f"<i>បានជ្រើសរើស: {file_name.split('/')[-1]}</i>")
            self.preview_canvas.image_pixmap = QPixmap(file_name)
            self.preview_canvas.update()
            
    def calculate_layout(self):
        paper_w = self.sb_width.value()
        paper_h = self.sb_height.value()
        photo_w = self.sb_p_width.value() * 10  # បំប្លែង cm ទៅ mm
        photo_h = self.sb_p_height.value() * 10 # បំប្លែង cm ទៅ mm
        margin = self.sb_margin.value()
        gap = self.sb_gap.value()
        
        avail_w = paper_w - (2 * margin)
        avail_h = paper_h - (2 * margin)
        
        cols = int((avail_w + gap) // (photo_w + gap)) if photo_w > 0 else 0
        rows = int((avail_h + gap) // (photo_h + gap)) if photo_h > 0 else 0
        
        if cols < 0: cols = 0
        if rows < 0: rows = 0
        
        self.lbl_status.setText(f"<b>អាចដាក់បាន: {cols * rows} រូបភាព (បញ្ឈរ (Portrait))</b>")
        
        self.preview_canvas.cols = cols
        self.preview_canvas.rows = rows
        self.preview_canvas.gap_px = gap * 2 # ប្រហាក់ប្រហែលសម្រាប់ការបង្ហាញប៉ុណ្ណោះ
        self.preview_canvas.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # ដាក់ Font ខ្មែរជាគោល ដើម្បីជៀសវាងអក្សរខូច
    font = QFont("Khmer OS Siemreap", 9)
    app.setFont(font)
    
    window = PhotoPrintApp()
    window.show()
    sys.exit(app.exec_())
