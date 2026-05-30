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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #dbe2e9;")
        self.image_pixmap = None
        self.cols = 6
        self.rows = 6
        self.paper_w = 210.0
        self.paper_h = 297.0
        self.photo_w = 30.0
        self.photo_h = 40.0
        self.margin_top = 10
        self.margin_bottom = 10
        self.margin_left = 10
        self.margin_right = 10
        self.offset_x = 10
        self.offset_y = 10
        self.gap = 2
        self.show_border = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # គូរផ្ទៃក្រដាសពណ៌សចំកណ្តាល ដោយរក្សាសមាមាត្រតាមទំហំក្រដាសពិត
        padding = 10
        avail_w = self.width() - padding * 2
        avail_h = self.height() - padding * 2
        
        if self.paper_h <= 0: return
        aspect_ratio = self.paper_w / self.paper_h
        
        paper_height = avail_h
        paper_width = paper_height * aspect_ratio
        if paper_width > avail_w:
            paper_width = avail_w
            paper_height = paper_width / aspect_ratio
            
        paper_x = (self.width() - paper_width) / 2
        paper_y = (self.height() - paper_height) / 2
        
        painter.fillRect(int(paper_x), int(paper_y), int(paper_width), int(paper_height), QColor(220, 220, 220))
        
        # ខ្នាតសមាមាត្រពី មីលីម៉ែត្រ ទៅ ភីកសែល (px/mm)
        scale = paper_width / self.paper_w if self.paper_w > 0 else 1
        
        # គូរក្រឡារូបថតតូចៗ (3x4 cm ឧទាហរណ៍)
        pen = QPen(QColor(200, 200, 200), 1, Qt.SolidLine)
        painter.setPen(pen)
        
        cols, rows = self.cols, self.rows
        gap_px = self.gap * scale
        
        if cols > 0 and rows > 0:
            cell_w = self.photo_w * scale
            cell_h = self.photo_h * scale
            
            start_x = paper_x + self.offset_x * scale
            start_y = paper_y + self.offset_y * scale
            
            painter.setFont(QFont("Arial", 8))
            for row in range(rows):
                for col in range(cols):
                    cx = start_x + col * (cell_w + gap_px)
                    cy = start_y + row * (cell_h + gap_px)
                    
                    if self.image_pixmap and not self.image_pixmap.isNull():
                        painter.drawPixmap(QRectF(cx, cy, cell_w, cell_h).toRect(), self.image_pixmap)
                        if self.show_border:
                            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
                            painter.drawRect(int(cx), int(cy), int(cell_w), int(cell_h))
                            painter.setPen(pen) # ត្រឡប់មក Pen ធម្មតាវិញ
                    else:
                        painter.drawRect(int(cx), int(cy), int(cell_w), int(cell_h))
                        painter.setPen(QColor(100, 100, 100))
                        painter.drawText(QRectF(cx, cy, cell_w, cell_h), Qt.AlignCenter, "3x4 cm")
                        painter.setPen(pen)

class PhotoPrintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("កម្មវិធីជំនួយការបោះពុម្ពរូបថត - Photo Print Studio")
        self.resize(1366, 768)
        self.showMaximized()
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
        self.cb_paper_size = QComboBox()
        self.cb_paper_size.addItems([
            "A4 (210 x 297 mm)",
            "A3 (297 x 420 mm)",
            "A5 (148 x 210 mm)",
            "Letter (215.9 x 279.4 mm)",
            "Custom size"
        ])
        gb_paper_layout.addWidget(self.cb_paper_size)
        
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
        
        self.cb_paper_size.currentIndexChanged.connect(self.change_paper_size)
        self.sb_width.setEnabled(False)
        self.sb_height.setEnabled(False)

        h_size_layout.addLayout(v_width)
        h_size_layout.addLayout(v_height)
        gb_paper_layout.addLayout(h_size_layout)
        
        gb_paper_layout.addWidget(QLabel("ទិសដៅ / Orientation:"))
        h_ori_layout = QHBoxLayout()
        self.rb_port = QRadioButton("បញ្ឈរ / Port.")
        self.rb_port.setChecked(True)
        self.rb_land = QRadioButton("ផ្តេក / Land.")
        self.rb_port.toggled.connect(self.change_orientation)
        
        h_ori_layout.addWidget(self.rb_port)
        h_ori_layout.addWidget(self.rb_land)
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
        gb_margin = QGroupBox("៤. គម្លាត និងគែម / Margins & Gaps")
        gb_margin_layout = QVBoxLayout()
        
        grid_margin = QGridLayout()
        
        grid_margin.addWidget(QLabel("លើ / Top:"), 0, 0)
        self.sb_margin_top = QSpinBox(); self.sb_margin_top.setValue(10); self.sb_margin_top.setSuffix(" mm")
        self.sb_margin_top.valueChanged.connect(self.calculate_layout)
        grid_margin.addWidget(self.sb_margin_top, 0, 1)
        
        grid_margin.addWidget(QLabel("ក្រោម / Bottom:"), 0, 2)
        self.sb_margin_bottom = QSpinBox(); self.sb_margin_bottom.setValue(10); self.sb_margin_bottom.setSuffix(" mm")
        self.sb_margin_bottom.valueChanged.connect(self.calculate_layout)
        grid_margin.addWidget(self.sb_margin_bottom, 0, 3)
        
        grid_margin.addWidget(QLabel("ឆ្វេង / Left:"), 1, 0)
        self.sb_margin_left = QSpinBox(); self.sb_margin_left.setValue(10); self.sb_margin_left.setSuffix(" mm")
        self.sb_margin_left.valueChanged.connect(self.calculate_layout)
        grid_margin.addWidget(self.sb_margin_left, 1, 1)
        
        grid_margin.addWidget(QLabel("ស្តាំ / Right:"), 1, 2)
        self.sb_margin_right = QSpinBox(); self.sb_margin_right.setValue(10); self.sb_margin_right.setSuffix(" mm")
        self.sb_margin_right.valueChanged.connect(self.calculate_layout)
        grid_margin.addWidget(self.sb_margin_right, 1, 3)
        
        gb_margin_layout.addLayout(grid_margin)
        
        h_gap_layout = QHBoxLayout()
        h_gap_layout.addWidget(QLabel("ចន្លោះរូបថត / Photo Gap:"))
        self.sb_gap = QSpinBox(); self.sb_gap.setValue(2); self.sb_gap.setSuffix(" mm")
        self.sb_gap.valueChanged.connect(self.calculate_layout)
        h_gap_layout.addWidget(self.sb_gap)
        gb_margin_layout.addLayout(h_gap_layout)
        
        h_center_layout = QHBoxLayout()
        self.chk_center_h = QCheckBox("តម្រឹមផ្ដេក / Auto Center H")
        self.chk_center_v = QCheckBox("តម្រឹមបញ្ឈរ / Auto Center V")
        self.chk_center_h.stateChanged.connect(self.toggle_auto_center)
        self.chk_center_v.stateChanged.connect(self.toggle_auto_center)
        h_center_layout.addWidget(self.chk_center_h)
        h_center_layout.addWidget(self.chk_center_v)
        gb_margin_layout.addLayout(h_center_layout)
        
        self.chk_show_border = QCheckBox("បង្ហាញបន្ទាត់សម្រាប់កាត់ / Show Border Line")
        self.chk_show_border.stateChanged.connect(self.toggle_border)
        gb_margin_layout.addWidget(self.chk_show_border)
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

    def change_paper_size(self):
        size_text = self.cb_paper_size.currentText()
        if "A4" in size_text:
            self.sb_width.setValue(210.0)
            self.sb_height.setValue(297.0)
            self.sb_width.setEnabled(False)
            self.sb_height.setEnabled(False)
        elif "A3" in size_text:
            self.sb_width.setValue(297.0)
            self.sb_height.setValue(420.0)
            self.sb_width.setEnabled(False)
            self.sb_height.setEnabled(False)
        elif "A5" in size_text:
            self.sb_width.setValue(148.0)
            self.sb_height.setValue(210.0)
            self.sb_width.setEnabled(False)
            self.sb_height.setEnabled(False)
        elif "Letter" in size_text:
            self.sb_width.setValue(215.9)
            self.sb_height.setValue(279.4)
            self.sb_width.setEnabled(False)
            self.sb_height.setEnabled(False)
        else: # Custom size
            self.sb_width.setEnabled(True)
            self.sb_height.setEnabled(True)
            
        self.change_orientation() # ពេលប្តូរក្រដាស ត្រូវពិនិត្យទិសដៅឡើងវិញ

    def change_orientation(self):
        w = self.sb_width.value()
        h = self.sb_height.value()
        if self.rb_port.isChecked() and w > h:
            self.sb_width.setValue(h)
            self.sb_height.setValue(w)
        elif self.rb_land.isChecked() and h > w:
            self.sb_width.setValue(h)
            self.sb_height.setValue(w)

    def load_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូបភាព / Choose Photo", "", "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        if file_name:
            self.lbl_image_status.setText(f"<i>បានជ្រើសរើស: {file_name.split('/')[-1]}</i>")
            self.preview_canvas.image_pixmap = QPixmap(file_name)
            self.preview_canvas.update()
            
    def toggle_auto_center(self):
        is_h = self.chk_center_h.isChecked()
        self.sb_margin_left.setEnabled(not is_h)
        self.sb_margin_right.setEnabled(not is_h)
        
        is_v = self.chk_center_v.isChecked()
        self.sb_margin_top.setEnabled(not is_v)
        self.sb_margin_bottom.setEnabled(not is_v)
        
        self.calculate_layout()
        
    def toggle_border(self):
        self.preview_canvas.show_border = self.chk_show_border.isChecked()
        self.preview_canvas.update()
            
    def calculate_layout(self):
        paper_w = self.sb_width.value()
        paper_h = self.sb_height.value()
        photo_w = self.sb_p_width.value() * 10  # បំប្លែង cm ទៅ mm
        photo_h = self.sb_p_height.value() * 10 # បំប្លែង cm ទៅ mm
        
        margin_t = self.sb_margin_top.value()
        margin_b = self.sb_margin_bottom.value()
        margin_l = self.sb_margin_left.value()
        margin_r = self.sb_margin_right.value()
        
        gap = self.sb_gap.value()
        
        avail_w = paper_w - (margin_l + margin_r)
        avail_h = paper_h - (margin_t + margin_b)
        
        cols = int((avail_w + gap) // (photo_w + gap)) if photo_w > 0 else 0
        rows = int((avail_h + gap) // (photo_h + gap)) if photo_h > 0 else 0
        
        if cols < 0: cols = 0
        if rows < 0: rows = 0
        
        offset_x = margin_l
        offset_y = margin_t
        
        # អនុវត្តការតម្រឹមស្វ័យប្រវត្តិ (Auto Center)
        if self.chk_center_h.isChecked() and cols > 0:
            block_w = cols * photo_w + (cols - 1) * gap
            offset_x = (paper_w - block_w) / 2.0
            
        if self.chk_center_v.isChecked() and rows > 0:
            block_h = rows * photo_h + (rows - 1) * gap
            offset_y = (paper_h - block_h) / 2.0
        
        ori_text = "បញ្ឈរ (Portrait)" if self.rb_port.isChecked() else "ផ្តេក (Landscape)"
        self.lbl_status.setText(f"<b>អាចដាក់បាន: {cols * rows} រូបភាព ({ori_text})</b>")
        
        self.preview_canvas.cols = cols
        self.preview_canvas.rows = rows
        self.preview_canvas.paper_w = paper_w
        self.preview_canvas.paper_h = paper_h
        self.preview_canvas.photo_w = photo_w
        self.preview_canvas.photo_h = photo_h
        
        self.preview_canvas.margin_top = margin_t
        self.preview_canvas.margin_bottom = margin_b
        self.preview_canvas.margin_left = margin_l
        self.preview_canvas.margin_right = margin_r
        self.preview_canvas.offset_x = offset_x
        self.preview_canvas.offset_y = offset_y
        self.preview_canvas.gap = gap
        
        self.preview_canvas.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # ដាក់ Font ខ្មែរជាគោល ដើម្បីជៀសវាងអក្សរខូច
    font = QFont("Khmer OS Siemreap", 9)
    app.setFont(font)
    
    window = PhotoPrintApp()
    window.show()
    sys.exit(app.exec_())
