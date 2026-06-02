import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QGroupBox, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QRadioButton, 
                             QCheckBox, QSlider, QGridLayout, QSizePolicy, QFileDialog, QButtonGroup)
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
        self.print_qty = 0
        
        self.is_manual = False
        self.photo_positions = []
        self.dragging_idx = -1
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.paper_width_px = 0
        self.paper_x_px = 0
        self.paper_y_px = 0
        self.image_mode = 'fill'
        
        self.is_panning = False
        self.last_pan_pos = None

    def generate_grid(self):
        old_positions = self.photo_positions.copy()
        self.photo_positions.clear()
        cols, rows = self.cols, self.rows
        start_x = self.offset_x
        start_y = self.offset_y
        count = 0
        for row in range(rows):
            for col in range(cols):
                if count < self.print_qty:
                    px = start_x + col * (self.photo_w + self.gap)
                    py = start_y + row * (self.photo_h + self.gap)
                    old = old_positions[count] if count < len(old_positions) else {}
                    self.photo_positions.append({
                        'x': px, 'y': py,
                        'scale': old.get('scale', 1.0),
                        'pan_x': old.get('pan_x', 0.0),
                        'pan_y': old.get('pan_y', 0.0),
                        'selected': old.get('selected', False)
                    })
                    count += 1

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
        
        self.paper_width_px = paper_width
        self.paper_x_px = paper_x
        self.paper_y_px = paper_y
        
        painter.fillRect(int(paper_x), int(paper_y), int(paper_width), int(paper_height), QColor(220, 220, 220))
        
        # ខ្នាតសមាមាត្រពី មីលីម៉ែត្រ ទៅ ភីកសែល (px/mm)
        scale = paper_width / self.paper_w if self.paper_w > 0 else 1
        
        # គូរក្រឡារូបថតតូចៗ (3x4 cm ឧទាហរណ៍)
        pen = QPen(QColor(200, 200, 200), 1, Qt.SolidLine)
        painter.setPen(pen)
        
        cell_w = self.photo_w * scale
        cell_h = self.photo_h * scale
        
        painter.setFont(QFont("Arial", 8))
        
        # -------------------------------------------------------------
        # បង្កើតរូបភាពទុកមុន (Pre-scale cache) មួយដង សម្រាប់រូបទាំង៣៦ 
        # ការពារការគាំងម៉ាស៊ីន (Memory/CPU Crash) ពេលវា Scale រូបធំ 36ដង
        # -------------------------------------------------------------
        pre_scaled_cover = None
        pre_scaled_contain = None
        tw, th = max(1, int(cell_w + 1)), max(1, int(cell_h + 1)) # បូក១ ដើម្បីកុំឲ្យខ្វះសាច់រូបពេល QRectF ធ្វើការបង្គត់
        
        if self.image_pixmap and not self.image_pixmap.isNull():
            if self.image_mode == 'cover':
                pre_scaled_cover = self.image_pixmap.scaled(tw, th, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            elif self.image_mode == 'contain':
                pre_scaled_contain = self.image_pixmap.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        for pos in self.photo_positions:
            cx = paper_x + pos['x'] * scale
            cy = paper_y + pos['y'] * scale
            
            target_rect = QRectF(cx, cy, cell_w, cell_h).toRect()
            
            # ការពារកុំឲ្យ Error ពេលទំហំតូចជាងឬស្មើ ០
            if target_rect.width() <= 0 or target_rect.height() <= 0:
                continue
                
            if self.image_pixmap and not self.image_pixmap.isNull():
                painter.fillRect(target_rect, Qt.white) # ចាក់ផ្ទៃសពីក្រោយ ដើម្បីឲ្យ contain ស្អាតល្អ
                
                if self.image_mode == 'fill':
                    painter.drawPixmap(target_rect, self.image_pixmap)
                elif self.image_mode == 'contain' and pre_scaled_contain and not pre_scaled_contain.isNull():
                    x_offset = (target_rect.width() - pre_scaled_contain.width()) // 2
                    y_offset = (target_rect.height() - pre_scaled_contain.height()) // 2
                    painter.drawPixmap(target_rect.x() + x_offset, target_rect.y() + y_offset, pre_scaled_contain)
                elif self.image_mode == 'cover' and pre_scaled_cover and not pre_scaled_cover.isNull():
                    img_scale = pos.get('scale', 1.0)
                    pan_x = pos.get('pan_x', 0.0)
                    pan_y = pos.get('pan_y', 0.0)
                    
                    if img_scale > 1.0:
                        new_w = int(pre_scaled_cover.width() * img_scale)
                        new_h = int(pre_scaled_cover.height() * img_scale)
                        if new_w < 8000 and new_h < 8000:
                            current_cover = pre_scaled_cover.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        else:
                            current_cover = pre_scaled_cover
                    else:
                        current_cover = pre_scaled_cover
                        
                    base_crop_x = (current_cover.width() - target_rect.width()) / 2.0
                    base_crop_y = (current_cover.height() - target_rect.height()) / 2.0
                    
                    crop_x = int(max(0, min(base_crop_x - pan_x, current_cover.width() - target_rect.width())))
                    crop_y = int(max(0, min(base_crop_y - pan_y, current_cover.height() - target_rect.height())))
                    
                    cropped_pixmap = current_cover.copy(crop_x, crop_y, target_rect.width(), target_rect.height())
                    if not cropped_pixmap.isNull():
                        painter.drawPixmap(target_rect, cropped_pixmap)

                if getattr(self, 'show_border', False):
                    painter.setPen(QPen(QColor(0, 0, 0), 0.25, Qt.SolidLine))
                    painter.drawRect(int(cx), int(cy), int(cell_w), int(cell_h))
                    painter.setPen(pen) # ត្រឡប់មក Pen ធម្មតាវិញ
            else:
                painter.drawRect(int(cx), int(cy), int(cell_w), int(cell_h))
                painter.setPen(QColor(100, 100, 100))
                painter.drawText(QRectF(cx, cy, cell_w, cell_h), Qt.AlignCenter, "3x4 cm")
                painter.setPen(pen)
                
            # គូរបន្ទាត់ពណ៌ខៀវបញ្ជាក់ថាវាត្រូវបានជ្រើសរើស (Selected)
            if pos.get('selected', False):
                painter.setPen(QPen(QColor(0, 120, 215), 3, Qt.SolidLine))
                painter.drawRect(int(cx), int(cy), int(cell_w), int(cell_h))
                painter.setPen(pen)

    def mousePressEvent(self, event):
        scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1
        cell_w = self.photo_w * scale
        cell_h = self.photo_h * scale
        
        click_x = event.x()
        click_y = event.y()
        
        if event.button() == Qt.LeftButton:
            clicked_idx = -1
            for i in range(len(self.photo_positions)-1, -1, -1):
                pos = self.photo_positions[i]
                cx = self.paper_x_px + pos['x'] * scale
                cy = self.paper_y_px + pos['y'] * scale
                rect = QRectF(cx, cy, cell_w, cell_h)
                
                if rect.contains(click_x, click_y):
                    clicked_idx = i
                    break
                    
            if clicked_idx >= 0:
                # ប្រព័ន្ធជ្រើសរើស (Selection)
                if event.modifiers() & Qt.ControlModifier:
                    self.photo_positions[clicked_idx]['selected'] = not self.photo_positions[clicked_idx].get('selected', False)
                else:
                    if not self.photo_positions[clicked_idx].get('selected', False):
                        for p in self.photo_positions:
                            p['selected'] = False
                        self.photo_positions[clicked_idx]['selected'] = True
                self.update()
                
                # ប្រព័ន្ធអូសទាញ (Pan សម្រាប់ Cover ឬ Drag សម្រាប់ Manual)
                if self.image_mode == 'cover':
                    self.is_panning = True
                    self.last_pan_pos = event.pos()
                elif self.is_manual:
                    p = self.photo_positions.pop(clicked_idx)
                    self.photo_positions.append(p)
                    self.dragging_idx = len(self.photo_positions) - 1
                    cx = self.paper_x_px + p['x'] * scale
                    cy = self.paper_y_px + p['y'] * scale
                    self.drag_offset_x = (click_x - cx) / scale
                    self.drag_offset_y = (click_y - cy) / scale
            else:
                # ចុចខាងក្រៅដើម្បីដកការជ្រើសរើស
                for p in self.photo_positions:
                    p['selected'] = False
                self.update()
                if self.image_mode == 'cover':
                    self.is_panning = True
                    self.last_pan_pos = event.pos()
                
    def mouseMoveEvent(self, event):
        if self.is_panning and self.last_pan_pos:
            delta = event.pos() - self.last_pan_pos
            has_selection = any(p.get('selected', False) for p in self.photo_positions)
            for p in self.photo_positions:
                if not has_selection or p.get('selected', False):
                    p['pan_x'] = p.get('pan_x', 0.0) + delta.x()
                    p['pan_y'] = p.get('pan_y', 0.0) + delta.y()
            self.last_pan_pos = event.pos()
            self.update()
            return
            
        if self.is_manual and self.dragging_idx >= 0:
            scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1
            new_x_mm = (event.x() - self.paper_x_px) / scale - self.drag_offset_x
            new_y_mm = (event.y() - self.paper_y_px) / scale - self.drag_offset_y
            
            self.photo_positions[self.dragging_idx]['x'] = new_x_mm
            self.photo_positions[self.dragging_idx]['y'] = new_y_mm
            self.update()
            
    def mouseReleaseEvent(self, event):
        if self.is_panning and event.button() == Qt.LeftButton:
            self.is_panning = False
            self.last_pan_pos = None
            return
            
        if event.button() == Qt.LeftButton:
            self.dragging_idx = -1
            
    def wheelEvent(self, event):
        if self.image_mode == 'cover':
            scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1
            cell_w = self.photo_w * scale
            cell_h = self.photo_h * scale
            
            mouse_x = event.x()
            mouse_y = event.y()
            
            hovered_idx = -1
            for i in range(len(self.photo_positions)-1, -1, -1):
                pos = self.photo_positions[i]
                cx = self.paper_x_px + pos['x'] * scale
                cy = self.paper_y_px + pos['y'] * scale
                rect = QRectF(cx, cy, cell_w, cell_h)
                
                if rect.contains(mouse_x, mouse_y):
                    hovered_idx = i
                    break

            factor = 1.05 if event.angleDelta().y() > 0 else 1.0 / 1.05
            
            if hovered_idx >= 0:
                if not self.photo_positions[hovered_idx].get('selected', False):
                    for p in self.photo_positions:
                        p['selected'] = False
                    self.photo_positions[hovered_idx]['selected'] = True

            has_selection = any(p.get('selected', False) for p in self.photo_positions)
            for p in self.photo_positions:
                if not has_selection or p.get('selected', False):
                    new_scale = p.get('scale', 1.0) * factor
                    if new_scale < 1.0: new_scale = 1.0
                    if new_scale > 10.0: new_scale = 10.0
                    p['scale'] = new_scale
            self.update()
        else:
            super().wheelEvent(event)

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
        self.rb_max_qty = QRadioButton("ពេញក្រដាស / Max Printable (Auto)")
        self.rb_custom_qty = QRadioButton("កំណត់ចំនួន / Custom Count (Auto)")
        self.rb_custom_qty.setChecked(True)
        gb_layout_layout.addWidget(self.rb_max_qty)
        gb_layout_layout.addWidget(self.rb_custom_qty)
        
        h_qty = QHBoxLayout()
        self.slider_qty = QSlider(Qt.Horizontal)
        self.slider_qty.setMinimum(1)
        self.sb_qty = QSpinBox()
        self.sb_qty.setMinimum(1)
        self.sb_qty.setValue(36)
        
        self.slider_qty.valueChanged.connect(self.sb_qty.setValue)
        self.sb_qty.valueChanged.connect(self.slider_qty.setValue)
        self.sb_qty.valueChanged.connect(self.calculate_layout)
        self.rb_max_qty.toggled.connect(self.calculate_layout)
        self.rb_custom_qty.toggled.connect(self.calculate_layout)
        
        h_qty.addWidget(self.slider_qty)
        h_qty.addWidget(self.sb_qty)
        gb_layout_layout.addLayout(h_qty)
        
        self.rb_manual_layout = QRadioButton("រៀបចំដោយសេរី / Manual Layout (Drag)")
        gb_layout_layout.addWidget(self.rb_manual_layout)
        
        self.lbl_manual_tip = QLabel("<i>💡 ប្រើម៉ៅស៍ឆ្វេង (Left Click) ទាញរូបថតនីមួយៗ<br>ដើម្បីផ្លាស់ទីទីតាំងតាមតម្រូវការនៅលើផ្ទៃបង្ហាញ (លើកលែងម៉ូដកាត់ Cover)។</i>")
        self.lbl_manual_tip.setStyleSheet("color: #d97706; font-size: 11px;")
        self.lbl_manual_tip.setVisible(False)
        gb_layout_layout.addWidget(self.lbl_manual_tip)
        self.rb_manual_layout.toggled.connect(self.toggle_manual_mode) # Connect ក្រោយពេលបង្កើត Tip រួច
        gb_layout.setLayout(gb_layout_layout)
        right_layout.addWidget(gb_layout)

        # 6. ការកំណត់រូបភាព / Image properties
        gb_img_prop = QGroupBox("៦. ការកំណត់រូបភាព / Image properties")
        gb_img_prop_layout = QVBoxLayout()
        self.rb_img_fill = QRadioButton("បំពេញ (លាត) / Image Fill (Stretch)")
        self.rb_img_cover = QRadioButton("គ្របដណ្តប់ (កាត់) / Image Cover (Crop)")
        self.rb_img_contain = QRadioButton("ផ្ទុក (រក្សាសមាមាត្រ) / Image Contain (Fit)")
        
        self.bg_img_mode = QButtonGroup(self)
        self.bg_img_mode.addButton(self.rb_img_fill)
        self.bg_img_mode.addButton(self.rb_img_cover)
        self.bg_img_mode.addButton(self.rb_img_contain)
        
        self.lbl_cover_tip = QLabel("<i>💡 ពេលកាត់ (Cover): ចុចម៉ៅស៍ឆ្វេងហើយទាញ (Drag) លើរូបដើម្បីរំកិល<br>និង Scroll ម៉ៅស៍ ដើម្បីពង្រីក/ពង្រួមរូប។</i>")
        self.lbl_cover_tip.setStyleSheet("color: #d97706; font-size: 11px;")
        self.lbl_cover_tip.setVisible(False)
        
        self.btn_select_all = QPushButton("ជ្រើសរើសទាំងអស់")
        self.btn_select_all.clicked.connect(self.select_all_photos)
        self.btn_deselect_all = QPushButton("ដកការជ្រើសរើស")
        self.btn_deselect_all.clicked.connect(self.deselect_all_photos)
        
        h_sel_layout = QHBoxLayout()
        h_sel_layout.setContentsMargins(0, 0, 0, 0)
        h_sel_layout.addWidget(self.btn_select_all)
        h_sel_layout.addWidget(self.btn_deselect_all)
        self.wg_selection = QWidget()
        self.wg_selection.setLayout(h_sel_layout)
        self.wg_selection.setVisible(False)
        
        self.rb_img_fill.setChecked(True)
        self.rb_img_fill.toggled.connect(self.change_image_mode)
        self.rb_img_cover.toggled.connect(self.change_image_mode)
        self.rb_img_contain.toggled.connect(self.change_image_mode)
        
        gb_img_prop_layout.addWidget(self.rb_img_fill)
        gb_img_prop_layout.addWidget(self.rb_img_cover)
        gb_img_prop_layout.addWidget(self.rb_img_contain)
        gb_img_prop_layout.addWidget(self.lbl_cover_tip)
        gb_img_prop_layout.addWidget(self.wg_selection)
        gb_img_prop.setLayout(gb_img_prop_layout)
        right_layout.addWidget(gb_img_prop)

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
        
    def toggle_manual_mode(self):
        is_manual = self.rb_manual_layout.isChecked()
        self.lbl_manual_tip.setVisible(is_manual)
        self.preview_canvas.is_manual = is_manual
        self.calculate_layout()
        
    def change_image_mode(self):
        is_cover = self.rb_img_cover.isChecked()
        self.lbl_cover_tip.setVisible(is_cover)
        self.wg_selection.setVisible(is_cover)
        
        if not is_cover:
            for p in self.preview_canvas.photo_positions:
                p['selected'] = False
            
        if self.rb_img_fill.isChecked():
            self.preview_canvas.image_mode = 'fill'
        elif is_cover:
            self.preview_canvas.image_mode = 'cover'
        elif self.rb_img_contain.isChecked():
            self.preview_canvas.image_mode = 'contain'
        self.preview_canvas.update()
        
    def select_all_photos(self):
        for p in self.preview_canvas.photo_positions:
            p['selected'] = True
        self.preview_canvas.update()
        
    def deselect_all_photos(self):
        for p in self.preview_canvas.photo_positions:
            p['selected'] = False
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
            
        max_qty = cols * rows
        
        self.sb_qty.blockSignals(True)
        self.slider_qty.blockSignals(True)
        self.sb_qty.setMaximum(max_qty if max_qty > 0 else 1)
        self.slider_qty.setMaximum(max_qty if max_qty > 0 else 1)
        self.sb_qty.blockSignals(False)
        self.slider_qty.blockSignals(False)
        
        is_manual = getattr(self, 'rb_manual_layout', None) and self.rb_manual_layout.isChecked()
        is_custom = self.rb_custom_qty.isChecked() or is_manual
        self.sb_qty.setEnabled(is_custom)
        self.slider_qty.setEnabled(is_custom)
        
        print_qty = self.sb_qty.value() if is_custom else max_qty
        if print_qty > max_qty:
            print_qty = max_qty
        
        ori_text = "បញ្ឈរ (Portrait)" if self.rb_port.isChecked() else "ផ្តេក (Landscape)"
        self.lbl_status.setText(f"<b>អាចដាក់បាន: {print_qty} / {max_qty} រូបភាព ({ori_text})</b>")
        
        self.preview_canvas.cols = cols
        self.preview_canvas.rows = rows
        self.preview_canvas.print_qty = print_qty
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
        
        if not self.preview_canvas.is_manual:
            self.preview_canvas.generate_grid()
        else:
            while len(self.preview_canvas.photo_positions) > print_qty:
                self.preview_canvas.photo_positions.pop()
            while len(self.preview_canvas.photo_positions) < print_qty:
                self.preview_canvas.photo_positions.append({
                    'x': offset_x, 
                    'y': offset_y, 
                    'scale': 1.0, 
                    'pan_x': 0.0, 
                    'pan_y': 0.0, 
                    'selected': False
                })
                
        self.preview_canvas.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # ដាក់ Font ខ្មែរជាគោល ដើម្បីជៀសវាងអក្សរខូច
    font = QFont("Khmer OS Siemreap", 9)
    app.setFont(font)
    
    window = PhotoPrintApp()
    window.show()
    sys.exit(app.exec_())
