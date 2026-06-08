import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QGroupBox, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QRadioButton, 
                             QCheckBox, QSlider, QGridLayout, QSizePolicy, QFileDialog, QButtonGroup,
                             QTabWidget, QTextEdit, QFontComboBox, QColorDialog)
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QTransform

class PreviewWidget(QWidget):
    """ Custom Widget សម្រាប់គូរទិដ្ឋភាពក្រដាស និងក្រឡារូបថត (Live Print Preview) """
    selectionChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus) # អនុញ្ញាតឲ្យ Widget នេះអាចចាប់យក Focus ពេល Click
        self.setMinimumSize(400, 500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #dbe2e9;")
        self.default_image_pixmap = None # Changed from image_pixmap to default_image_pixmap
        self.cols = 6
        self.rows = 6
        self.paper_w = 210.0
        self.paper_h = 297.0
        self.photo_w = 30.0
        self.photo_h = 40.0
        self.size_label = "3x4 cm"
        self.optimize_fit = False
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
        self.drag_start_mouse_pos = None

        self.paper_width_px = 0
        self.paper_x_px = 0
        self.paper_y_px = 0
        self.image_mode = 'fill'
        
        self.is_panning = False
        self.last_pan_pos = None
        self.is_rubber_banding = False
        self.rubber_band_start_pos = None
        self.selection_rect = None

    def set_default_image_pixmap(self, pixmap):
        self.default_image_pixmap = pixmap

    def generate_grid(self, size_configs=None):
        """ size_configs: list of {'w': mm, 'h': mm, 'qty': int, 'label': str} """
        if size_configs is None: return

        items_to_place = []
        for config in size_configs:
            for _ in range(config['qty']):
                items_to_place.append(config)

        # តម្រៀបតាមទំហំ (កម្ពស់) ធំបំផុតមុន ដើម្បីងាយស្រួលរៀបចំ (Shelf Packing)
        items_to_place.sort(key=lambda x: max(x['w'], x['h']), reverse=True)
        old_positions = self.photo_positions.copy()
        self.photo_positions.clear()

        curr_x, curr_y = self.offset_x, self.offset_y
        max_row_h = 0
        avail_w = self.paper_w - self.margin_right
        avail_h = self.paper_h - self.margin_bottom

        for idx, item in enumerate(items_to_place):
            # item['w'] and item['h'] are the base dimensions from size_configs
            base_w, base_h = item['w'], item['h']
            old = old_positions[idx] if idx < len(old_positions) else {}
            old_angle = old.get('rotation_angle', 0)
            
            if self.is_manual:
                if old_angle == 90 or old_angle == 270:
                    cw, ch = base_h, base_w
                else:
                    cw, ch = base_w, base_h
                    
                if 'x' in old and 'y' in old:
                    px, py = old['x'], old['y']
                else:
                    px, py = curr_x, curr_y
                    curr_x += cw + self.gap
                    max_row_h = max(max_row_h, ch)
            else:
                w_for_packing, h_for_packing = base_w, base_h
                
                fits_norm = (curr_x + w_for_packing <= avail_w + 0.1)
                fits_rot = (curr_x + h_for_packing <= avail_w + 0.1)
                
                if not fits_norm and not fits_rot:
                    curr_x = self.offset_x
                    curr_y += max_row_h + self.gap
                    max_row_h = 0
                    fits_norm = (curr_x + w_for_packing <= avail_w + 0.1)
                    fits_rot = (curr_x + h_for_packing <= avail_w + 0.1)
                
                if not fits_norm and not fits_rot: break
                
                is_rotated = False
                if fits_norm:
                    cw, ch = w_for_packing, h_for_packing
                elif fits_rot and (h_for_packing <= max_row_h or curr_x == self.offset_x):
                    cw, ch = h_for_packing, w_for_packing
                    is_rotated = True
                else:
                    curr_x = self.offset_x
                    curr_y += max_row_h + self.gap
                    max_row_h = 0
                    
                    fits_norm = (curr_x + w_for_packing <= avail_w + 0.1)
                    fits_rot = (curr_x + h_for_packing <= avail_w + 0.1)
                    
                    if not fits_norm and not fits_rot: break
                    
                    if fits_norm:
                        cw, ch = w_for_packing, h_for_packing
                    else:
                        cw, ch = h_for_packing, w_for_packing
                        is_rotated = True

                if curr_y + ch > avail_h + 0.1: break

                px, py = curr_x, curr_y
                curr_x += cw + self.gap
                max_row_h = max(max_row_h, ch)
                
                if is_rotated:
                    old_angle = 90
                else:
                    old_angle = 0

            self.photo_positions.append({
                'x': px, 'y': py,
                'w': cw, 'h': ch, 'label': item['label'],
                'original_w': base_w,
                'original_h': base_h,
                'rotation_angle': old_angle,
                'scale': old.get('scale', 1.0),
                'pan_x': old.get('pan_x', 0.0),
                'pan_y': old.get('pan_y', 0.0),
                'selected': old.get('selected', False),
                'image_pixmap': old.get('image_pixmap', self.default_image_pixmap)
            })

    def rotate_selected_photos(self):
        """ បង្វិលរូបភាពដែលបានជ្រើសរើស (បង្វិលទាំងប្រអប់ជុំវិញចំណុចកណ្តាល) """
        for p in self.photo_positions:
            if p.get('selected', False):
                current_angle = p.get('rotation_angle', 0)
                new_angle = (current_angle + 90) % 360
                p['rotation_angle'] = new_angle
                
                cx = p['x'] + p['w'] / 2.0
                cy = p['y'] + p['h'] / 2.0
                
                if new_angle == 90 or new_angle == 270:
                    p['w'], p['h'] = p['h'], p['w']
                else:
                    p['w'], p['h'] = p['h'], p['w']
                    
                p['x'] = cx - p['w'] / 2.0
                p['y'] = cy - p['h'] / 2.0
        self.update()

    def nudge_selected_photos(self, dx_mm, dy_mm):
        """ រំកិលរូបភាពដែលបានជ្រើសរើសតាមចម្ងាយ x និង y (គិតជា mm) """
        moved = False
        for p in self.photo_positions:
            if p.get('selected', False):
                p['x'] += dx_mm
                p['y'] += dy_mm
                moved = True
        if moved:
            self.update()

    def pan_selected_photos(self, dx_px, dy_px):
        """ រំកិលសាច់រូបភាព (Crop) ខាងក្នុងប្រអប់ (Pan) """
        moved = False
        for p in self.photo_positions:
            if p.get('selected', False):
                p['pan_x'] = p.get('pan_x', 0.0) + dx_px
                p['pan_y'] = p.get('pan_y', 0.0) + dy_px
                moved = True
        if moved:
            self.update()

    def align_selected_left(self):
        """ តម្រឹមរូបភាពដែលបានជ្រើសរើសទៅខាងឆ្វេងបំផុតនៃក្រុម """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 2: return
        min_x = min(p['x'] for p in selected)
        for p in selected: p['x'] = min_x
        self.update()

    def align_selected_top(self):
        """ តម្រឹមរូបភាពដែលបានជ្រើសរើសទៅខាងលើបំផុតនៃក្រុម """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 2: return
        min_y = min(p['y'] for p in selected)
        for p in selected: p['y'] = min_y
        self.update()

    def align_selected_right(self):
        """ តម្រឹមរូបភាពដែលបានជ្រើសរើសទៅខាងស្តាំបំផុតនៃក្រុម """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 2: return
        max_right = max(p['x'] + p['w'] for p in selected)
        for p in selected: p['x'] = max_right - p['w']
        self.update()

    def align_selected_bottom(self):
        """ តម្រឹមរូបភាពដែលបានជ្រើសរើសទៅខាងក្រោមបំផុតនៃក្រុម """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 2: return
        max_bottom = max(p['y'] + p['h'] for p in selected)
        for p in selected: p['y'] = max_bottom - p['h']
        self.update()

    def distribute_horizontally(self):
        """ រៀបចំគម្លាតរូបភាពឱ្យស្មើគ្នាផ្ដេក (Distribute Horizontally) """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 3: return
        selected.sort(key=lambda p: p['x'])
        start_x, end_x = selected[0]['x'], selected[-1]['x'] + selected[-1]['w']
        total_w = sum(p['w'] for p in selected)
        gap = (end_x - start_x - total_w) / (len(selected) - 1)
        curr_x = start_x
        for p in selected:
            p['x'] = curr_x
            curr_x += p['w'] + gap
        self.update()

    def distribute_vertically(self):
        """ រៀបចំគម្លាតរូបភាពឱ្យស្មើគ្នាបញ្ឈរ (Distribute Vertically) """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 3: return
        selected.sort(key=lambda p: p['y'])
        start_y, end_y = selected[0]['y'], selected[-1]['y'] + selected[-1]['h']
        total_h = sum(p['h'] for p in selected)
        gap = (end_y - start_y - total_h) / (len(selected) - 1)
        curr_y = start_y
        for p in selected:
            p['y'] = curr_y
            curr_y += p['h'] + gap
        self.update()

    def center_horizontally(self):
        """ តម្រឹមរូបភាពកណ្តាលតាមផ្ដេក (Center Horizontally) ធៀបនឹងក្រដាស និង Margin """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if not selected:
            selected = self.photo_positions # បើមិនមាន Select ទេ គឺរាប់ទាំងអស់
        if not selected: return
        
        min_x = min(p['x'] for p in selected)
        max_right = max(p['x'] + p['w'] for p in selected)
        group_width = max_right - min_x
        
        # គណនាចំណុចកណ្តាលនៃក្រដាស ដោយគិត Margin
        avail_width = self.paper_w - self.margin_left - self.margin_right
        paper_center_x = self.margin_left + avail_width / 2.0
        
        group_center_x = min_x + group_width / 2.0
        shift_x = paper_center_x - group_center_x
        
        for p in selected:
            p['x'] += shift_x
        self.update()

    def center_vertically(self):
        """ តម្រឹមរូបភាពកណ្តាលតាមបញ្ឈរ (Center Vertically) ធៀបនឹងក្រដាស និង Margin """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if not selected:
            selected = self.photo_positions # បើមិនមាន Select ទេ គឺរាប់ទាំងអស់
        if not selected: return
        
        min_y = min(p['y'] for p in selected)
        max_bottom = max(p['y'] + p['h'] for p in selected)
        group_height = max_bottom - min_y
        
        # គណនាចំណុចកណ្តាលនៃក្រដាស ដោយគិត Margin
        avail_height = self.paper_h - self.margin_top - self.margin_bottom
        paper_center_y = self.margin_top + avail_height / 2.0
        
        group_center_y = min_y + group_height / 2.0
        shift_y = paper_center_y - group_center_y
        
        for p in selected:
            p['y'] += shift_y
        self.update()

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
        
        # គូរបន្ទាត់ Margin (Margin Guidelines) ជាបន្ទាត់ដាច់ៗពណ៌ក្រហមស្រាល
        margin_pen = QPen(QColor(255, 50, 50, 120), 1, Qt.DashLine)
        painter.setPen(margin_pen)
        
        m_top = paper_y + self.margin_top * scale
        m_bottom = paper_y + (self.paper_h - self.margin_bottom) * scale
        m_left = paper_x + self.margin_left * scale
        m_right = paper_x + (self.paper_w - self.margin_right) * scale
        
        # បន្ទាត់ផ្តេក (Top / Bottom)
        painter.drawLine(int(paper_x), int(m_top), int(paper_x + paper_width), int(m_top))
        painter.drawLine(int(paper_x), int(m_bottom), int(paper_x + paper_width), int(m_bottom))
        
        # បន្ទាត់បញ្ឈរ (Left / Right)
        painter.drawLine(int(m_left), int(paper_y), int(m_left), int(paper_y + paper_height))
        painter.drawLine(int(m_right), int(paper_y), int(m_right), int(paper_y + paper_height))

        # គូរក្រឡារូបថតតូចៗ (3x4 cm ឧទាហរណ៍)
        pen = QPen(QColor(200, 200, 200), 1, Qt.SolidLine)
        painter.setPen(pen)
        
        painter.setFont(QFont("Arial", 8))
        
        # -------------------------------------------------------------
        # គូររូបភាពនីមួយៗ
        # -------------------------------------------------------------
        
        for pos in self.photo_positions:
            p_w, p_h = pos.get('w', self.photo_w), pos.get('h', self.photo_h)
            cell_w = p_w * scale
            cell_h = p_h * scale
            tw, th = max(1, int(cell_w + 1)), max(1, int(cell_h + 1))

            cx = paper_x + pos['x'] * scale
            cy = paper_y + pos['y'] * scale

            current_pixmap = pos.get('image_pixmap')

            pre_scaled_cover = None
            pre_scaled_contain = None

            if current_pixmap and not current_pixmap.isNull():
                # បង្វិលរូបភាពតាមការកំណត់ដោយដៃ (ចុច R) ៩០, ១៨០, ២៧០ ដឺក្រេ
                manual_angle = pos.get('rotation_angle', 0)
                if manual_angle != 0:
                    transform = QTransform().rotate(manual_angle)
                    current_pixmap = current_pixmap.transformed(transform, Qt.SmoothTransformation)

                if self.optimize_fit:
                    img_w, img_h = current_pixmap.width(), current_pixmap.height()
                    # បង្វិលរូបភាពបើទិសដៅមិនត្រូវគ្នា (ផ្ដេក/បញ្ឈរ)
                    if img_w != img_h and cell_w != cell_h:
                        if (img_w > img_h) != (cell_w > cell_h):
                            transform = QTransform().rotate(90)
                            current_pixmap = current_pixmap.transformed(transform, Qt.SmoothTransformation)

                if self.image_mode == 'cover':
                    pre_scaled_cover = current_pixmap.scaled(tw, th, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                elif self.image_mode == 'contain':
                    pre_scaled_contain = current_pixmap.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            target_rect = QRectF(cx, cy, cell_w, cell_h).toRect()
            
            # ការពារកុំឲ្យ Error ពេលទំហំតូចជាងឬស្មើ ០
            if target_rect.width() <= 0 or target_rect.height() <= 0:
                continue
                
            if current_pixmap and not current_pixmap.isNull():
                painter.fillRect(target_rect, Qt.white) # ចាក់ផ្ទៃសពីក្រោយ ដើម្បីឲ្យ contain ស្អាតល្អ
                
                if self.image_mode == 'fill': # Stretch to fill
                    painter.drawPixmap(target_rect, current_pixmap)
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
                painter.drawText(QRectF(cx, cy, cell_w, cell_h), Qt.AlignCenter, pos.get('label', self.size_label))
                painter.setPen(pen)
                
            # គូរបន្ទាត់ពណ៌ខៀវបញ្ជាក់ថាវាត្រូវបានជ្រើសរើស (Selected)
            if pos.get('selected', False):
                painter.setPen(QPen(QColor(0, 120, 215), 3, Qt.SolidLine))
                painter.drawRect(int(cx), int(cy), int(cell_w), int(cell_h))
                painter.setPen(pen)
                
        # គូរចតុកោណកែងសម្រាប់ជ្រើសរើស (Rubber Band Selection)
        if self.is_rubber_banding and self.selection_rect:
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            painter.setBrush(QColor(0, 120, 215, 50)) # Semi-transparent blue fill
            painter.drawRect(self.selection_rect)
            painter.setBrush(Qt.NoBrush) # Reset brush
            painter.setPen(pen) # Reset pen


    def mousePressEvent(self, event):
        self.setFocus() # ចាប់យក Focus ពេលចុចលើរូបភាព ដើម្បីការពារកុំឲ្យ Arrow Key រត់ទៅ RadioButton
        scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1        
        click_x = event.x()
        click_y = event.y()
        
        if event.button() == Qt.LeftButton:
            clicked_idx = -1
            for i in range(len(self.photo_positions)-1, -1, -1):
                pos = self.photo_positions[i]
                cell_w = pos.get('w', self.photo_w) * scale
                cell_h = pos.get('h', self.photo_h) * scale
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
                self.selectionChanged.emit()
                self.update()
                
                # ប្រព័ន្ធអូសទាញ (Pan សម្រាប់ Cover ឬ Drag សម្រាប់ Manual)
                if self.image_mode == 'cover' and (event.modifiers() & Qt.ShiftModifier):
                    self.is_panning = True
                    self.last_pan_pos = event.pos()
                elif self.is_manual:
                    # រៀបចំការអូសរូបភាពដែលបាន Select ទាំងអស់
                    self.dragging_idx = clicked_idx
                    self.drag_start_mouse_pos = event.pos()
                    
                    for p in self.photo_positions:
                        if p.get('selected'):
                            p['drag_start_x'] = p['x']
                            p['drag_start_y'] = p['y']
                    
                    # នាំរូបភាពដែលជ្រើសរើសមកខាងមុខ (Bring to Front)
                    selected = [p for p in self.photo_positions if p.get('selected')]
                    others = [p for p in self.photo_positions if not p.get('selected')]
                    self.photo_positions = others + selected
            else:
                # ចាប់ផ្តើមការជ្រើសរើសដោយអូស (Rubber Band Selection)
                self.is_rubber_banding = True
                self.rubber_band_start_pos = event.pos()
                self.selection_rect = QRectF(event.pos(), event.pos())
                
                if not (event.modifiers() & Qt.ControlModifier):
                    # បើមិនចុច Ctrl ទេ ត្រូវលុបការជ្រើសរើសចាស់ទាំងអស់
                    for p in self.photo_positions:
                        p['selected'] = False
                    self.selectionChanged.emit()
                self.update() # គូរចតុកោណកែងចាប់ផ្តើម
                if self.image_mode == 'cover' and (event.modifiers() & Qt.ShiftModifier):
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
        
        if self.is_rubber_banding and self.rubber_band_start_pos:
            # កំពុងអូសដើម្បីជ្រើសរើស
            self.selection_rect = QRectF(self.rubber_band_start_pos, event.pos()).normalized()
            self.update() # គូរចតុកោណកែងដែលកំពុងអូស
            return
            
        if self.is_manual and self.dragging_idx >= 0 and self.drag_start_mouse_pos:
            scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1
            delta = event.pos() - self.drag_start_mouse_pos
            dx_mm = delta.x() / scale
            dy_mm = delta.y() / scale
            
            for p in self.photo_positions:
                if p.get('selected', False) and 'drag_start_x' in p:
                    new_x = p['drag_start_x'] + dx_mm
                    new_y = p['drag_start_y'] + dy_mm
                        
                    p['x'] = new_x
                    p['y'] = new_y
            self.update()
            return
            
    def mouseReleaseEvent(self, event):
        if self.is_panning and event.button() == Qt.LeftButton:
            self.is_panning = False
            self.last_pan_pos = None
            return
        
        if self.is_rubber_banding and event.button() == Qt.LeftButton:
            # បញ្ចប់ការជ្រើសរើសដោយអូស
            self.is_rubber_banding = False
            self.rubber_band_start_pos = None
            
            if self.selection_rect:
                # ជ្រើសរើសរូបភាពណាដែលប្រសព្វជាមួយចតុកោណកែងដែលបានអូស
                scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1
                
                for i, pos in enumerate(self.photo_positions):
                    cell_w = pos.get('w', self.photo_w) * scale
                    cell_h = pos.get('h', self.photo_h) * scale
                    cx = self.paper_x_px + pos['x'] * scale
                    cy = self.paper_y_px + pos['y'] * scale
                    photo_rect = QRectF(cx, cy, cell_w, cell_h)
                    
                    if self.selection_rect.intersects(photo_rect):
                        self.photo_positions[i]['selected'] = True
                    # ប្រសិនបើ Ctrl មិនត្រូវបានចុចទេ ការជ្រើសរើសចាស់ត្រូវបានលុបនៅក្នុង mousePressEvent រួចហើយ។
                    # ដូច្នេះ យើងគ្រាន់តែបន្ថែមរូបភាពដែលប្រសព្វគ្នា។
                
                self.selection_rect = None # លុបចតុកោណកែងដែលបានគូរ
                self.selectionChanged.emit()
                self.update()
            return
            
        if event.button() == Qt.LeftButton:
            self.dragging_idx = -1
            self.last_pan_pos = None
            self.drag_start_mouse_pos = None
            
    def wheelEvent(self, event):
        if self.image_mode == 'cover' and (event.modifiers() & Qt.ShiftModifier):
            scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1
            mouse_x = event.x()
            mouse_y = event.y()
            
            hovered_idx = -1
            for i in range(len(self.photo_positions)-1, -1, -1):
                pos = self.photo_positions[i]
                cell_w = pos.get('w', self.photo_w) * scale
                cell_h = pos.get('h', self.photo_h) * scale
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
                self.selectionChanged.emit()

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

class TextPreviewWidget(QWidget):
    """ Custom Widget សម្រាប់គូរទិដ្ឋភាពអក្សរធំ (Live Text Preview) """
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #dbe2e9;")
        
        self.paper_w = 210.0
        self.paper_h = 297.0
        self.margin_top = 10
        self.margin_bottom = 10
        self.margin_left = 10
        self.margin_right = 10
        
        self.text = ""
        self.text_font = QFont("Khmer OS Muol Light", 50)
        self.text_color = QColor(0, 0, 0)
        self.text_align = Qt.AlignCenter
        self.bg_color = QColor(255, 255, 255)
        self.auto_fit = False
        
        self.free_stretch = False
        self.text_rect_mm = None
        self.drag_mode = None
        self.drag_start_pos = None
        self.drag_start_rect = None
        self.current_scale = 1.0
        self.current_paper_x = 0
        self.current_paper_y = 0
        self.setMouseTracking(True)

    def get_handle_at(self, pos):
        if not self.free_stretch or self.text_rect_mm is None: return None
        rect_px = QRectF(self.current_paper_x + self.text_rect_mm.x() * self.current_scale, 
                         self.current_paper_y + self.text_rect_mm.y() * self.current_scale, 
                         self.text_rect_mm.width() * self.current_scale, 
                         self.text_rect_mm.height() * self.current_scale)
        hs = 10
        def hit(p):
            return QRectF(p.x() - hs/2, p.y() - hs/2, hs, hs).contains(pos)
            
        if hit(rect_px.topLeft()): return 'TL'
        if hit(rect_px.topRight()): return 'TR'
        if hit(rect_px.bottomLeft()): return 'BL'
        if hit(rect_px.bottomRight()): return 'BR'
        if hit(QPointF(rect_px.center().x(), rect_px.top())): return 'T'
        if hit(QPointF(rect_px.center().x(), rect_px.bottom())): return 'B'
        if hit(QPointF(rect_px.left(), rect_px.center().y())): return 'L'
        if hit(QPointF(rect_px.right(), rect_px.center().y())): return 'R'
        if rect_px.contains(pos): return 'C'
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.get_handle_at(event.pos())
            if handle:
                self.drag_mode = handle
                self.drag_start_pos = event.pos()
                self.drag_start_rect = QRectF(self.text_rect_mm)

    def mouseMoveEvent(self, event):
        handle = self.get_handle_at(event.pos())
        if self.drag_mode:
            handle = self.drag_mode
            
        if handle in ['TL', 'BR']:
            self.setCursor(Qt.SizeFDiagCursor)
        elif handle in ['TR', 'BL']:
            self.setCursor(Qt.SizeBDiagCursor)
        elif handle in ['L', 'R']:
            self.setCursor(Qt.SizeHorCursor)
        elif handle in ['T', 'B']:
            self.setCursor(Qt.SizeVerCursor)
        elif handle == 'C':
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        if self.drag_mode and self.drag_start_pos and self.drag_start_rect:
            delta_x = (event.x() - self.drag_start_pos.x()) / self.current_scale
            delta_y = (event.y() - self.drag_start_pos.y()) / self.current_scale
            new_rect = QRectF(self.drag_start_rect)
            
            if self.drag_mode == 'TL':
                new_rect.setTopLeft(new_rect.topLeft() + QPointF(delta_x, delta_y))
            elif self.drag_mode == 'TR':
                new_rect.setTopRight(new_rect.topRight() + QPointF(delta_x, delta_y))
            elif self.drag_mode == 'BL':
                new_rect.setBottomLeft(new_rect.bottomLeft() + QPointF(delta_x, delta_y))
            elif self.drag_mode == 'BR':
                new_rect.setBottomRight(new_rect.bottomRight() + QPointF(delta_x, delta_y))
            elif self.drag_mode == 'L':
                new_rect.setLeft(new_rect.left() + delta_x)
            elif self.drag_mode == 'R':
                new_rect.setRight(new_rect.right() + delta_x)
            elif self.drag_mode == 'T':
                new_rect.setTop(new_rect.top() + delta_y)
            elif self.drag_mode == 'B':
                new_rect.setBottom(new_rect.bottom() + delta_y)
            elif self.drag_mode == 'C':
                new_rect.translate(delta_x, delta_y)
                
            if new_rect.width() < 5: new_rect.setWidth(5)
            if new_rect.height() < 5: new_rect.setHeight(5)
            
            self.text_rect_mm = new_rect
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_mode = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

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
        
        painter.fillRect(int(paper_x), int(paper_y), int(paper_width), int(paper_height), self.bg_color)
        
        scale = paper_width / self.paper_w if self.paper_w > 0 else 1
        self.current_scale = scale
        self.current_paper_x = paper_x
        self.current_paper_y = paper_y
        
        margin_pen = QPen(QColor(255, 50, 50, 120), 1, Qt.DashLine)
        painter.setPen(margin_pen)
        m_top = paper_y + self.margin_top * scale
        m_bottom = paper_y + (self.paper_h - self.margin_bottom) * scale
        m_left = paper_x + self.margin_left * scale
        m_right = paper_x + (self.paper_w - self.margin_right) * scale
        
        painter.drawLine(int(paper_x), int(m_top), int(paper_x + paper_width), int(m_top))
        painter.drawLine(int(paper_x), int(m_bottom), int(paper_x + paper_width), int(m_bottom))
        painter.drawLine(int(m_left), int(paper_y), int(m_left), int(paper_y + paper_height))
        painter.drawLine(int(m_right), int(paper_y), int(m_right), int(paper_y + paper_height))
        
        if self.text:
            painter.setPen(self.text_color)
            
            if self.free_stretch:
                if self.text_rect_mm is None:
                    self.text_rect_mm = QRectF(self.margin_left, self.margin_top, self.paper_w - self.margin_left - self.margin_right, self.paper_h - self.margin_top - self.margin_bottom)
                
                rect_px = QRectF(paper_x + self.text_rect_mm.x() * scale, paper_y + self.text_rect_mm.y() * scale, self.text_rect_mm.width() * scale, self.text_rect_mm.height() * scale)
                
                base_font = QFont(self.text_font)
                base_font.setPixelSize(100)
                from PyQt5.QtGui import QPainterPath, QFontMetricsF, QBrush
                
                path = QPainterPath()
                fm = QFontMetricsF(base_font)
                
                lines = self.text.split('\n')
                y = fm.ascent()
                for line in lines:
                    line_w = fm.horizontalAdvance(line)
                    if self.text_align & Qt.AlignHCenter:
                        x = -line_w / 2
                    elif self.text_align & Qt.AlignRight:
                        x = -line_w
                    else:
                        x = 0
                    path.addText(x, y, base_font, line)
                    y += fm.lineSpacing()
                    
                base_rect = path.boundingRect()
                
                painter.save()
                painter.translate(rect_px.x(), rect_px.y())
                sx = rect_px.width() / base_rect.width() if base_rect.width() > 0 else 1
                sy = rect_px.height() / base_rect.height() if base_rect.height() > 0 else 1
                painter.scale(sx, sy)
                painter.translate(-base_rect.x(), -base_rect.y())
                
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.text_color))
                painter.drawPath(path)
                painter.restore()
                
                painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect_px)
                
                painter.setPen(QPen(Qt.blue, 1))
                painter.setBrush(Qt.white)
                hs = 8
                handles = [
                    rect_px.topLeft(), rect_px.topRight(), rect_px.bottomLeft(), rect_px.bottomRight(),
                    QPointF(rect_px.center().x(), rect_px.top()), QPointF(rect_px.center().x(), rect_px.bottom()),
                    QPointF(rect_px.left(), rect_px.center().y()), QPointF(rect_px.right(), rect_px.center().y())
                ]
                for p in handles:
                    painter.drawRect(QRectF(p.x() - hs/2, p.y() - hs/2, hs, hs))
                    
            else:
                scaled_font = QFont(self.text_font)
                rect = QRectF(m_left, m_top, m_right - m_left, m_bottom - m_top)
                
                if self.auto_fit:
                    from PyQt5.QtGui import QFontMetricsF
                    min_size = 1
                    max_size = 5000
                    best_size = min_size
                    
                    while min_size <= max_size:
                        mid_size = (min_size + max_size) // 2
                        scaled_font.setPixelSize(mid_size)
                        fm = QFontMetricsF(scaled_font)
                        br = fm.boundingRect(rect, self.text_align | Qt.TextWordWrap, self.text)
                        
                        if br.width() <= rect.width() and br.height() <= rect.height():
                            best_size = mid_size
                            min_size = mid_size + 1
                        else:
                            max_size = mid_size - 1
                    scaled_font.setPixelSize(best_size)
                else:
                    pt_to_mm = 25.4 / 72.0
                    size_mm = self.text_font.pointSizeF() * pt_to_mm
                    size_px = size_mm * scale
                    scaled_font.setPixelSize(int(max(1, size_px)))
                    
                painter.setFont(scaled_font)
                painter.drawText(rect, self.text_align | Qt.TextWordWrap, self.text)

class PhotoPrintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("កម្មវិធីជំនួយការបោះពុម្ពរូបថត - Photo Print Studio")
        self.default_image_pixmap = None # Added default image pixmap
        from PyQt5.QtCore import QSettings
        self.settings = QSettings("PhotoPrintApp", "Settings")
        self.default_pdf_folder = self.settings.value("default_pdf_folder", "")
        self.foxit_path = self.settings.value("foxit_path", "")
        self.resize(1366, 768)
        self.showMaximized()
        self.initUI()

    def initUI(self):
        # Main Widget and Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        self.tabs = QTabWidget(main_widget)
        
        # TAB 1: Photo Print
        self.tab1 = QWidget()
        main_layout = QHBoxLayout(self.tab1)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # បង្កើត Preview Canvas ជាមុនសិន ដើម្បីឲ្យ Panel ផ្សេងៗអាចភ្ជាប់ (connect) ទៅវាបាន
        self.preview_canvas = PreviewWidget()

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
            "ក្រដាសរូបថត (10x15 cm)",
            "ក្រដាសរូបថត (13x18 cm)",
            "Custom size / ទំហំតាមតម្រូវការ"
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

        gb_preset_layout.addWidget(QLabel("ខ្នាត / Unit:"))
        self.cb_p_unit = QComboBox()
        self.cb_p_unit.addItems(["cm", "mm", "inch", "pixel"])
        self.cb_p_unit.setCurrentIndex(1) # Default to mm
        self.cb_p_unit.currentIndexChanged.connect(self.calculate_layout)
        gb_preset_layout.addWidget(self.cb_p_unit)

        h_dpi_layout = QHBoxLayout()
        h_dpi_layout.addWidget(QLabel("គុណភាពបោះពុម្ព (DPI):"))
        self.sb_dpi = QSpinBox()
        self.sb_dpi.setRange(72, 1200)
        self.sb_dpi.setValue(300) # តម្លៃស្តង់ដារសម្រាប់បោះពុម្ពច្បាស់
        self.sb_dpi.setSuffix(" DPI")
        self.sb_dpi.valueChanged.connect(self.calculate_layout)
        h_dpi_layout.addWidget(self.sb_dpi)
        gb_preset_layout.addLayout(h_dpi_layout)
        gb_preset_layout.addWidget(QLabel("<small><i>(300 DPI គឺល្អបំផុតសម្រាប់ការបោះពុម្ព)</i></small>"))

        # បង្កើតជម្រើស ៣ ទំហំ
        self.size_groups = []
        default_sizes = [(35.0, 45.0), (27.0, 35.0), (55.5, 88.0)]
        for i in range(3):
            row_layout = QHBoxLayout()
            chk = QCheckBox(f"ទំហំ {i+1}"); chk.setChecked(i==0)
            chk.stateChanged.connect(self.calculate_layout)
            sb_w = QDoubleSpinBox(); sb_w.setValue(default_sizes[i][0]); sb_w.setMaximum(5000)
            sb_h = QDoubleSpinBox(); sb_h.setValue(default_sizes[i][1]); sb_h.setMaximum(5000)
            sb_q = QSpinBox(); sb_q.setValue(4 if i==0 else 0); sb_q.setMaximum(1000)
            
            sb_w.valueChanged.connect(self.calculate_layout)
            sb_h.valueChanged.connect(self.calculate_layout)
            sb_q.valueChanged.connect(self.calculate_layout)

            row_layout.addWidget(chk)
            row_layout.addWidget(QLabel("W:")); row_layout.addWidget(sb_w)
            row_layout.addWidget(QLabel("H:")); row_layout.addWidget(sb_h)
            row_layout.addWidget(QLabel("Qty:")); row_layout.addWidget(sb_q)
            gb_preset_layout.addLayout(row_layout)
            self.size_groups.append({'chk': chk, 'w': sb_w, 'h': sb_h, 'qty': sb_q})

        # តម្លៃ dummy សម្រាប់កុំឱ្យ error ជាមួយ function ចាស់
        self.sb_p_width = self.size_groups[0]['w']; self.sb_p_height = self.size_groups[0]['h']

        self.btn_reverse_p_size = QPushButton("ឆ្លាស់ទំហំ / Reverse Size")
        self.btn_reverse_p_size.clicked.connect(self.reverse_photo_size)
        gb_preset_layout.addWidget(self.btn_reverse_p_size)
        
        self.chk_optimize_fit = QCheckBox("ស្វែងរកប្រព័ន្ធសម្រួលភាពស័ក្ដិសម / Optimize Fit")
        self.chk_optimize_fit.setChecked(True)
        self.chk_optimize_fit.stateChanged.connect(self.calculate_layout)
        gb_preset_layout.addWidget(self.chk_optimize_fit)
        gb_preset.setLayout(gb_preset_layout)
        left_layout.addWidget(gb_preset)

        # 4. ការរៀបចំ និងចំនួន
        gb_layout = QGroupBox("៤. ការរៀបចំ និងចំនួន / Layout Qty")
        gb_layout_layout = QVBoxLayout()
        self.rb_max_qty = QRadioButton("ពេញក្រដាស / Max Printable (Auto)")
        self.rb_max_qty.setChecked(True)
        gb_layout_layout.addWidget(self.rb_max_qty)
        self.rb_max_qty.toggled.connect(self.calculate_layout)
        
        self.rb_manual_layout = QRadioButton("រៀបចំដោយសេរី / Manual Layout (Drag)")
        gb_layout_layout.addWidget(self.rb_manual_layout)

        # ប៊ូតុងតម្រឹម និងរៀបចំ (Alignment & Distribution Buttons)
        self.wg_align = QWidget()
        align_grid = QGridLayout(self.wg_align)
        align_grid.setContentsMargins(0, 0, 0, 0)
        self.btn_align_left = QPushButton("Align Left")
        self.btn_align_top = QPushButton("Align Top")
        self.btn_align_right = QPushButton("Align Right")
        self.btn_align_bottom = QPushButton("Align Bottom")
        self.btn_dist_h = QPushButton("Distribute H")
        self.btn_dist_v = QPushButton("Distribute V")

        self.btn_align_left.clicked.connect(self.preview_canvas.align_selected_left)
        self.btn_align_top.clicked.connect(self.preview_canvas.align_selected_top)
        self.btn_align_right.clicked.connect(self.preview_canvas.align_selected_right)
        self.btn_align_bottom.clicked.connect(self.preview_canvas.align_selected_bottom)
        self.btn_dist_h.clicked.connect(self.preview_canvas.distribute_horizontally)
        self.btn_dist_v.clicked.connect(self.preview_canvas.distribute_vertically)

        align_grid.addWidget(self.btn_align_left, 0, 0)
        align_grid.addWidget(self.btn_align_top, 0, 1)
        align_grid.addWidget(self.btn_align_right, 1, 0)
        align_grid.addWidget(self.btn_align_bottom, 1, 1)
        align_grid.addWidget(self.btn_dist_h, 2, 0)
        align_grid.addWidget(self.btn_dist_v, 2, 1)
        self.wg_align.setVisible(False)
        gb_layout_layout.addWidget(self.wg_align)

        self.lbl_manual_tip = QLabel("<i>💡 ប្រើម៉ៅស៍ឆ្វេង (Left Click) ទាញរូបថតដែលបានជ្រើសរើសដើម្បីផ្លាស់ទី<br>និងចុចគ្រាប់ចុច 'R' ដើម្បីបង្វិលរូបភាព។</i>")
        self.lbl_manual_tip.setStyleSheet("color: #d97706; font-size: 11px;")
        self.lbl_manual_tip.setVisible(False)
        gb_layout_layout.addWidget(self.lbl_manual_tip)
        self.rb_manual_layout.toggled.connect(self.toggle_manual_mode) # Connect ក្រោយពេលបង្កើត Tip រួច
        gb_layout.setLayout(gb_layout_layout)
        left_layout.addWidget(gb_layout)

        # ---------------- MIDDLE PANEL ----------------
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_title = QLabel("<b>ទិដ្ឋភាពបង្ហាញជាក់ស្តែង / LIVE PRINT PREVIEW</b>")
        mid_title.setAlignment(Qt.AlignCenter)
        mid_title.setFont(QFont("Khmer OS Battambang", 11))
        mid_layout.addWidget(mid_title)
        
        self.preview_canvas.selectionChanged.connect(self.update_image_adjustment_buttons)
        mid_layout.addWidget(self.preview_canvas)

        # ---------------- RIGHT PANEL ----------------
        right_panel = QWidget()
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignTop)

        # 5. គម្លាត និងគែម
        gb_margin = QGroupBox("៥. គម្លាត និងគែម / Margins & Gaps")
        gb_margin_layout = QVBoxLayout()
        
        grid_margin = QGridLayout()
        
        grid_margin.addWidget(QLabel("លើ / Top:"), 0, 0)
        self.sb_margin_top = QSpinBox(); self.sb_margin_top.setValue(0); self.sb_margin_top.setSuffix(" mm")
        self.sb_margin_top.valueChanged.connect(self.calculate_layout)
        grid_margin.addWidget(self.sb_margin_top, 0, 1)
        
        grid_margin.addWidget(QLabel("ក្រោម / Bottom:"), 0, 2)
        self.sb_margin_bottom = QSpinBox(); self.sb_margin_bottom.setValue(0); self.sb_margin_bottom.setSuffix(" mm")
        self.sb_margin_bottom.valueChanged.connect(self.calculate_layout)
        grid_margin.addWidget(self.sb_margin_bottom, 0, 3)
        
        grid_margin.addWidget(QLabel("ឆ្វេង / Left:"), 1, 0)
        self.sb_margin_left = QSpinBox(); self.sb_margin_left.setValue(0); self.sb_margin_left.setSuffix(" mm")
        self.sb_margin_left.valueChanged.connect(self.calculate_layout)
        grid_margin.addWidget(self.sb_margin_left, 1, 1)
        
        grid_margin.addWidget(QLabel("ស្តាំ / Right:"), 1, 2)
        self.sb_margin_right = QSpinBox(); self.sb_margin_right.setValue(0); self.sb_margin_right.setSuffix(" mm")
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
        self.chk_center_h.setChecked(True)
        self.chk_center_v = QCheckBox("តម្រឹមបញ្ឈរ / Auto Center V")
        self.chk_center_v.setChecked(True)
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
        
        self.lbl_cover_tip = QLabel("<i>💡 ពេលកាត់ (Cover): ចុច Shift + ម៉ៅស៍ឆ្វេង ហើយទាញ (Drag) លើរូបដើម្បីរំកិល<br>និង Shift + Scroll ម៉ៅស៍ ដើម្បីពង្រីក/ពង្រួមរូប។</i>")
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
        self.wg_selection.setVisible(True) # បង្ហាញប៊ូតុងជ្រើសរើសជានិច្ច
        
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
        
        # 7. ការកែសម្រួលរូបភាព / Image Adjustment
        gb_img_adj = QGroupBox("៧. ការកែសម្រួលរូបភាព / Image Adjustment")
        gb_img_adj_layout = QVBoxLayout()
        
        self.btn_change_selected_image = QPushButton("ផ្លាស់ប្ដូររូបភាពដែលបានជ្រើសរើស / Change Selected Image")
        self.btn_change_selected_image.clicked.connect(self.change_selected_image)
        self.btn_change_selected_image.setEnabled(False) # Enabled only when image is loaded and cover mode
        gb_img_adj_layout.addWidget(self.btn_change_selected_image)
        
        self.btn_reset_selected_image = QPushButton("កំណត់រូបភាពដើម / Reset Selected Image")
        self.btn_reset_selected_image.clicked.connect(self.reset_selected_image)
        self.btn_reset_selected_image.setEnabled(False) # Enabled only when image is loaded and cover mode
        gb_img_adj_layout.addWidget(self.btn_reset_selected_image)
        
        self.lbl_adj_tip = QLabel("<i>💡 មុខងារនេះដំណើរការនៅពេលមានរូបភាពផ្ទុកហើយ និងមានរូបថតយ៉ាងហោចណាស់មួយត្រូវបានជ្រើសរើស។</i>")
        self.lbl_adj_tip.setStyleSheet("color: #d97706; font-size: 11px;")
        gb_img_adj_layout.addWidget(self.lbl_adj_tip)
        
        gb_img_adj.setLayout(gb_img_adj_layout)
        right_layout.addWidget(gb_img_adj)

        right_layout.addStretch()

        # Action Buttons
        self.lbl_status = QLabel("<b>អាចដាក់បាន: 36 / 36 រូបភាព (បញ្ឈរ (Portrait))</b>")
        self.lbl_status.setStyleSheet("color: #16947b;")
        right_layout.addWidget(self.lbl_status)

        h_save_layout = QHBoxLayout()
        btn_save_pdf = QPushButton("រក្សាទុក PDF / Save PDF")
        btn_save_pdf.setStyleSheet("background-color: #128c7e; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_save_pdf.clicked.connect(self.save_pdf)
        
        btn_settings = QPushButton("⚙")
        btn_settings.setToolTip("កំណត់ទីតាំងរក្សាទុក PDF / Set PDF Save Folder")
        btn_settings.setStyleSheet("background-color: #64748b; color: white; padding: 12px; font-weight: bold; border-radius: 5px; font-size: 16px;")
        btn_settings.setFixedWidth(50)
        btn_settings.clicked.connect(self.open_settings)
        
        h_save_layout.addWidget(btn_save_pdf)
        h_save_layout.addWidget(btn_settings)
        
        btn_print = QPushButton("បញ្ចូនទៅ Foxit PDF/ Import to Foxit")
        btn_print.setStyleSheet("background-color: #5850ec; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_print.clicked.connect(self.import_to_foxit)
        
        btn_support = QLabel("សរសេរដោយ៖ ដែកូដថ្មី Ver.1.0.2")
        btn_support.setStyleSheet(" color: green ; padding: 12px; font-weight: bold; border-radius: 5px;")

        right_layout.addLayout(h_save_layout)
        right_layout.addWidget(btn_print)
        right_layout.addWidget(btn_support)

        # បញ្ចូល Panel ទាំង3 ទៅក្នុង Layout គោល
        main_layout.addWidget(left_panel)
        main_layout.addWidget(mid_panel, 1) # អនុញ្ញាតឲ្យផ្ទាំងកណ្តាលរីកធំជាងគេ
        main_layout.addWidget(right_panel)
        
        # TAB 2: Large Text Banner
        self.tab2 = QWidget()
        self.initTextUI(self.tab2)
        
        self.tabs.addTab(self.tab1, "១. បោះពុម្ពរូបថត / Photo Print")
        self.tabs.addTab(self.tab2, "២. សរសេរអក្សរធំ / Large Text Banner")
        
        layout = QVBoxLayout(main_widget)
        layout.addWidget(self.tabs)
        layout.setContentsMargins(0,0,0,0)
        
        # ធ្វើការគណនាបឋមនៅពេលចាប់ផ្តើមកម្មវិធី
        self.calculate_layout()

    def initTextUI(self, parent_widget):
        from PyQt5.QtWidgets import QTextEdit, QFontComboBox, QColorDialog
        layout = QHBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Panel (Controls)
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)
        
        title_lbl = QLabel("<b>សរសេរអក្សរធំ / Large Text Banner</b>")
        title_lbl.setFont(QFont("Khmer OS Battambang", 12))
        left_layout.addWidget(title_lbl)
        
        # Text Input
        gb_text = QGroupBox("១. អត្ថបទ / Text Input")
        gb_text_layout = QVBoxLayout()
        self.txt_banner = QTextEdit()
        self.txt_banner.setPlaceholderText("បញ្ចូលអត្ថបទទីនេះ...")
        font_battambang = QFont("Khmer OS Battambang", 12)
        self.txt_banner.setFont(font_battambang)
        self.txt_banner.textChanged.connect(self.update_text_preview)
        gb_text_layout.addWidget(self.txt_banner)
        gb_text.setLayout(gb_text_layout)
        left_layout.addWidget(gb_text)
        
        # Font Settings
        gb_font = QGroupBox("២. កំណត់អក្សរ / Font Settings")
        gb_font_layout = QVBoxLayout()
        
        self.cb_font = QFontComboBox()
        self.cb_font.setCurrentFont(QFont("Khmer OS Muol Light"))
        self.cb_font.currentFontChanged.connect(self.update_text_preview)
        gb_font_layout.addWidget(QLabel("ប្រភេទអក្សរ / Font Family:"))
        gb_font_layout.addWidget(self.cb_font)
        
        h_size = QHBoxLayout()
        h_size.addWidget(QLabel("ទំហំ / Size (pt):"))
        self.sb_font_size = QSpinBox()
        self.sb_font_size.setRange(8, 1000)
        self.sb_font_size.setValue(100)
        self.sb_font_size.valueChanged.connect(self.update_text_preview)
        h_size.addWidget(self.sb_font_size)
        gb_font_layout.addLayout(h_size)
        
        self.chk_auto_fit = QCheckBox("បំពេញពេញក្រដាស / Auto-Fit Paper")
        self.chk_auto_fit.setChecked(False)
        self.chk_auto_fit.stateChanged.connect(self.toggle_auto_fit)
        gb_font_layout.addWidget(self.chk_auto_fit)
        
        self.chk_free_stretch = QCheckBox("ទាញដោយសេរី / Free Stretch")
        self.chk_free_stretch.setChecked(False)
        self.chk_free_stretch.stateChanged.connect(self.toggle_free_stretch)
        gb_font_layout.addWidget(self.chk_free_stretch)
        
        self.btn_fill_paper = QPushButton("ទាញបំពេញក្រដាស / Stretch to Fill")
        self.btn_fill_paper.setEnabled(False)
        self.btn_fill_paper.clicked.connect(self.stretch_to_fill)
        gb_font_layout.addWidget(self.btn_fill_paper)
        
        h_color = QHBoxLayout()
        self.btn_text_color = QPushButton("ពណ៌អក្សរ / Text Color")
        self.btn_text_color.setStyleSheet("background-color: black; color: white;")
        self.btn_text_color.clicked.connect(self.choose_text_color)
        
        self.btn_bg_color = QPushButton("ពណ៌ផ្ទៃ / BG Color")
        self.btn_bg_color.setStyleSheet("background-color: white; color: black;")
        self.btn_bg_color.clicked.connect(self.choose_bg_color)
        
        h_color.addWidget(self.btn_text_color)
        h_color.addWidget(self.btn_bg_color)
        gb_font_layout.addLayout(h_color)
        
        h_align = QHBoxLayout()
        self.btn_align_left_t = QPushButton("Left")
        self.btn_align_center_t = QPushButton("Center")
        self.btn_align_right_t = QPushButton("Right")
        
        self.btn_align_left_t.clicked.connect(lambda: self.set_text_align(Qt.AlignLeft))
        self.btn_align_center_t.clicked.connect(lambda: self.set_text_align(Qt.AlignCenter))
        self.btn_align_right_t.clicked.connect(lambda: self.set_text_align(Qt.AlignRight))
        
        h_align.addWidget(self.btn_align_left_t)
        h_align.addWidget(self.btn_align_center_t)
        h_align.addWidget(self.btn_align_right_t)
        gb_font_layout.addLayout(h_align)
        
        gb_font.setLayout(gb_font_layout)
        left_layout.addWidget(gb_font)
        
        # Paper Settings
        gb_paper = QGroupBox("៣. ក្រដាស និងគែម / Paper & Margin")
        gb_paper_layout = QVBoxLayout()
        self.cb_t_paper = QComboBox()
        self.cb_t_paper.addItems(["A4 (210 x 297 mm)", "A3 (297 x 420 mm)", "A5 (148 x 210 mm)", "Letter (215.9 x 279.4 mm)"])
        self.cb_t_paper.currentIndexChanged.connect(self.update_text_paper)
        gb_paper_layout.addWidget(QLabel("ទំហំក្រដាស / Paper Size:"))
        gb_paper_layout.addWidget(self.cb_t_paper)
        
        h_ori = QHBoxLayout()
        self.rb_t_port = QRadioButton("បញ្ឈរ / Port.")
        self.rb_t_land = QRadioButton("ផ្តេក / Land.")
        self.rb_t_land.setChecked(True) # Text banner usually landscape
        self.rb_t_port.toggled.connect(self.update_text_paper)
        h_ori.addWidget(self.rb_t_port)
        h_ori.addWidget(self.rb_t_land)
        gb_paper_layout.addLayout(h_ori)
        
        h_margin = QHBoxLayout()
        h_margin.addWidget(QLabel("គែម / Margin (mm):"))
        self.sb_t_margin = QSpinBox()
        self.sb_t_margin.setValue(10)
        self.sb_t_margin.valueChanged.connect(self.update_text_preview)
        h_margin.addWidget(self.sb_t_margin)
        gb_paper_layout.addLayout(h_margin)
        
        gb_paper.setLayout(gb_paper_layout)
        left_layout.addWidget(gb_paper)
        
        left_layout.addStretch()
        
        # Action Buttons
        btn_save_pdf = QPushButton("រក្សាទុក PDF / Save PDF")
        btn_save_pdf.setStyleSheet("background-color: #128c7e; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_save_pdf.clicked.connect(self.save_text_pdf)
        
        btn_print = QPushButton("បញ្ចូនទៅ Foxit / Import Foxit")
        btn_print.setStyleSheet("background-color: #5850ec; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_print.clicked.connect(self.import_text_to_foxit)
        
        left_layout.addWidget(btn_save_pdf)
        left_layout.addWidget(btn_print)
        
        # Middle Panel (Preview)
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_title = QLabel("<b>ទិដ្ឋភាពបង្ហាញជាក់ស្តែង / LIVE TEXT PREVIEW</b>")
        mid_title.setAlignment(Qt.AlignCenter)
        mid_title.setFont(QFont("Khmer OS Battambang", 11))
        mid_layout.addWidget(mid_title)
        
        self.text_preview = TextPreviewWidget()
        mid_layout.addWidget(self.text_preview)
        
        layout.addWidget(left_panel)
        layout.addWidget(mid_panel, 1)
        
        self.text_color = QColor(0, 0, 0)
        self.bg_color = QColor(255, 255, 255)
        self.text_align = Qt.AlignCenter
        self.update_text_paper()

    def update_text_paper(self):
        txt = self.cb_t_paper.currentText()
        if "A4" in txt: w, h = 210.0, 297.0
        elif "A3" in txt: w, h = 297.0, 420.0
        elif "A5" in txt: w, h = 148.0, 210.0
        else: w, h = 215.9, 279.4
        
        if self.rb_t_land.isChecked():
            w, h = h, w
            
        self.text_preview.paper_w = w
        self.text_preview.paper_h = h
        self.update_text_preview()
        
    def toggle_auto_fit(self):
        self.sb_font_size.setEnabled(not self.chk_auto_fit.isChecked() and not self.chk_free_stretch.isChecked())
        self.update_text_preview()

    def toggle_free_stretch(self):
        is_free = self.chk_free_stretch.isChecked()
        self.chk_auto_fit.setEnabled(not is_free)
        self.sb_font_size.setEnabled(not is_free and not self.chk_auto_fit.isChecked())
        self.btn_fill_paper.setEnabled(is_free)
        self.text_preview.free_stretch = is_free
        self.text_preview.update()

    def stretch_to_fill(self):
        m = self.sb_t_margin.value()
        self.text_preview.text_rect_mm = QRectF(m, m, self.text_preview.paper_w - 2*m, self.text_preview.paper_h - 2*m)
        self.text_preview.update()

    def update_text_preview(self):
        self.text_preview.text = self.txt_banner.toPlainText()
        font = self.cb_font.currentFont()
        font.setPointSizeF(self.sb_font_size.value())
        self.text_preview.text_font = font
        self.text_preview.text_color = self.text_color
        self.text_preview.bg_color = self.bg_color
        self.text_preview.text_align = self.text_align
        self.text_preview.auto_fit = self.chk_auto_fit.isChecked()
        m = self.sb_t_margin.value()
        self.text_preview.margin_top = m
        self.text_preview.margin_bottom = m
        self.text_preview.margin_left = m
        self.text_preview.margin_right = m
        self.text_preview.update()
        
    def choose_text_color(self):
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.text_color, self)
        if color.isValid():
            self.text_color = color
            lum = color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
            text_col = "black" if lum > 128 else "white"
            self.btn_text_color.setStyleSheet(f"background-color: {color.name()}; color: {text_col};")
            self.update_text_preview()

    def choose_bg_color(self):
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.bg_color, self)
        if color.isValid():
            self.bg_color = color
            lum = color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
            text_col = "black" if lum > 128 else "white"
            self.btn_bg_color.setStyleSheet(f"background-color: {color.name()}; color: {text_col};")
            self.update_text_preview()

    def set_text_align(self, align):
        self.text_align = align
        self.update_text_preview()

    def save_text_pdf(self, show_msg=True):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from PyQt5.QtGui import QPdfWriter, QPageSize, QPageLayout, QPainter
        from PyQt5.QtCore import QSizeF, QMarginsF, Qt, QRectF
        import os
        from datetime import datetime
        
        file_name = ""
        if hasattr(self, 'default_pdf_folder') and self.default_pdf_folder and os.path.isdir(self.default_pdf_folder):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = os.path.join(self.default_pdf_folder, f"TextBanner_{timestamp}.pdf")
        else:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "រក្សាទុកជា PDF / Save as PDF", "", "PDF Files (*.pdf)", options=options)
            
        if not file_name: return None
        
        pdf_writer = QPdfWriter(file_name)
        paper_w = self.text_preview.paper_w
        paper_h = self.text_preview.paper_h
        
        pdf_writer.setPageSize(QPageSize(QSizeF(paper_w, paper_h), QPageSize.Millimeter))
        pdf_writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        pdf_writer.setResolution(300)
        
        painter = QPainter(pdf_writer)
        painter.setRenderHint(QPainter.Antialiasing)
        
        scale = 300 / 25.4
        
        painter.fillRect(0, 0, int(paper_w * scale), int(paper_h * scale), self.bg_color)
        
        if self.text_preview.text:
            painter.setPen(self.text_color)
            
            if self.chk_free_stretch.isChecked():
                rect_mm = self.text_preview.text_rect_mm
                if rect_mm is None:
                    m = self.sb_t_margin.value()
                    rect_mm = QRectF(m, m, paper_w - 2*m, paper_h - 2*m)
                    
                rect_px = QRectF(rect_mm.x() * scale, rect_mm.y() * scale, rect_mm.width() * scale, rect_mm.height() * scale)
                
                base_font = QFont(self.text_preview.text_font)
                base_font.setPixelSize(100)
                from PyQt5.QtGui import QPainterPath, QFontMetricsF, QBrush
                
                path = QPainterPath()
                fm = QFontMetricsF(base_font)
                
                lines = self.text_preview.text.split('\n')
                y = fm.ascent()
                for line in lines:
                    line_w = fm.horizontalAdvance(line)
                    if self.text_align & Qt.AlignHCenter:
                        x = -line_w / 2
                    elif self.text_align & Qt.AlignRight:
                        x = -line_w
                    else:
                        x = 0
                    path.addText(x, y, base_font, line)
                    y += fm.lineSpacing()
                    
                base_rect = path.boundingRect()
                
                painter.save()
                painter.translate(rect_px.x(), rect_px.y())
                sx = rect_px.width() / base_rect.width() if base_rect.width() > 0 else 1
                sy = rect_px.height() / base_rect.height() if base_rect.height() > 0 else 1
                painter.scale(sx, sy)
                painter.translate(-base_rect.x(), -base_rect.y())
                
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.text_color))
                painter.drawPath(path)
                painter.restore()
            else:
                scaled_font = QFont(self.text_preview.text_font)
                m = self.sb_t_margin.value()
                m_px = m * scale
                rect = QRectF(m_px, m_px, (paper_w - 2*m) * scale, (paper_h - 2*m) * scale)
                
                if self.chk_auto_fit.isChecked():
                    from PyQt5.QtGui import QFontMetricsF
                    min_size = 1
                    max_size = 5000
                    best_size = min_size
                    
                    while min_size <= max_size:
                        mid_size = (min_size + max_size) // 2
                        scaled_font.setPixelSize(mid_size)
                        fm = QFontMetricsF(scaled_font)
                        br = fm.boundingRect(rect, self.text_align | Qt.TextWordWrap, self.text_preview.text)
                        
                        if br.width() <= rect.width() and br.height() <= rect.height():
                            best_size = mid_size
                            min_size = mid_size + 1
                        else:
                            max_size = mid_size - 1
                    scaled_font.setPixelSize(best_size)
                else:
                    pt_to_mm = 25.4 / 72.0
                    size_mm = self.text_preview.text_font.pointSizeF() * pt_to_mm
                    size_px = size_mm * scale
                    scaled_font.setPixelSize(int(max(1, size_px)))
                    
                painter.setFont(scaled_font)
                painter.drawText(rect, self.text_align | Qt.TextWordWrap, self.text_preview.text)
            
        painter.end()
        if show_msg:
            QMessageBox.information(self, "ជោគជ័យ / Success", "ឯកសារ PDF ត្រូវបានរក្សាទុកដោយជោគជ័យ! / PDF saved successfully!")
        return file_name
        
    def import_text_to_foxit(self):
        import subprocess
        from PyQt5.QtWidgets import QMessageBox
        import os
        
        if not hasattr(self, 'foxit_path') or not self.foxit_path or not os.path.exists(self.foxit_path):
            QMessageBox.warning(self, "មិនទាន់កំណត់កម្មវិធី / Not Configured", "សូមចូលទៅកាន់ Settings (⚙) ដើម្បីកំណត់ទីតាំងកម្មវិធី Foxit PDF ជាមុនសិន។")
            return
            
        file_name = self.save_text_pdf(show_msg=False)
        if file_name:
            try:
                subprocess.Popen([self.foxit_path, file_name])
            except Exception as e:
                QMessageBox.critical(self, "កំហុស / Error", f"មិនអាចបើកកម្មវិធី Foxit PDF បានទេ:\n{str(e)}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.clear_selected_image()
        elif event.key() == Qt.Key_R:
            self.preview_canvas.rotate_selected_photos()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            if event.modifiers() & Qt.ControlModifier:
                # ប្រើ Ctrl + Arrow សម្រាប់រំកិលសាច់រូបភាព (Pan inside Cover mode)
                step = 20 if (event.modifiers() & Qt.ShiftModifier) else 5
                if event.key() == Qt.Key_Up:
                    self.preview_canvas.pan_selected_photos(0, -step)
                elif event.key() == Qt.Key_Down:
                    self.preview_canvas.pan_selected_photos(0, step)
                elif event.key() == Qt.Key_Left:
                    self.preview_canvas.pan_selected_photos(-step, 0)
                elif event.key() == Qt.Key_Right:
                    self.preview_canvas.pan_selected_photos(step, 0)
            else:
                # ប្រើ Arrow ធម្មតា សម្រាប់រំកិលប្រអប់រូបភាពនៅលើក្រដាស
                step = 5.0 if (event.modifiers() & Qt.ShiftModifier) else 0.5
                if event.key() == Qt.Key_Up:
                    self.preview_canvas.nudge_selected_photos(0, -step)
                elif event.key() == Qt.Key_Down:
                    self.preview_canvas.nudge_selected_photos(0, step)
                elif event.key() == Qt.Key_Left:
                    self.preview_canvas.nudge_selected_photos(-step, 0)
                elif event.key() == Qt.Key_Right:
                    self.preview_canvas.nudge_selected_photos(step, 0)
        else:
            super().keyPressEvent(event)

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
        elif "10x15" in size_text:
            self.sb_width.setValue(100.0)
            self.sb_height.setValue(150.0)
            self.sb_width.setEnabled(False)
            self.sb_height.setEnabled(False)
        elif "13x18" in size_text:
            self.sb_width.setValue(130.0)
            self.sb_height.setValue(180.0)
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

    def reverse_photo_size(self):
        for g in self.size_groups:
            w = g['w'].value()
            h = g['h'].value()
            g['w'].setValue(h)
            g['h'].setValue(w)

    def load_image(self):
        options = QFileDialog.Options()
        file_names, _ = QFileDialog.getOpenFileNames(self, "ជ្រើសរើសរូបភាព / Choose Photos", "", "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        
        if not file_names:
            return

        if len(file_names) == 1:
            # ករណីជ្រើសរើសរូបភាពតែ ១: កំណត់ជា Default ហើយបំពេញគ្រប់ Slot ទាំងអស់
            self.default_image_pixmap = QPixmap(file_names[0])
            self.preview_canvas.set_default_image_pixmap(self.default_image_pixmap)
            self.lbl_image_status.setText(f"<i>បានជ្រើសរើស: {file_names[0].split('/')[-1]}</i>")
            
            self.calculate_layout() # បង្កើត Grid ឡើងវិញដោយប្រើរូបភាព Default
            for p in self.preview_canvas.photo_positions:
                p['image_pixmap'] = self.default_image_pixmap
        else:
            # ករណីជ្រើសរើសច្រើន: ដាក់រូបតាមលំដាប់ ហើយទុក Slot ដែលសល់ឲ្យនៅទំនេរ (None)
            self.default_image_pixmap = None
            self.preview_canvas.set_default_image_pixmap(None)
            self.lbl_image_status.setText(f"<i>បានជ្រើសរើសរូបភាពចំនួន {len(file_names)} ឯកសារ</i>")
            
            self.calculate_layout() # Refresh grid
            
            # បញ្ចូលរូបភាពតាម Slot និងសម្អាត Slot ដែលនៅសល់
            for i, p in enumerate(self.preview_canvas.photo_positions):
                if i < len(file_names):
                    pix = QPixmap(file_names[i])
                    p['image_pixmap'] = pix if not pix.isNull() else None
                else:
                    p['image_pixmap'] = None
            
            self.update_image_adjustment_buttons()
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
        self.wg_align.setVisible(is_manual)
        self.preview_canvas.is_manual = is_manual
        self.calculate_layout()
        
    def change_image_mode(self):
        is_cover = self.rb_img_cover.isChecked()
        self.lbl_cover_tip.setVisible(is_cover)
        self.update_image_adjustment_buttons()
        
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
        
    def update_image_adjustment_buttons(self):
        # ពិនិត្យមើលថាមានរូបថតណាមួយត្រូវបាន Select ដែរឬទេ
        has_selection = any(p.get('selected', False) for p in self.preview_canvas.photo_positions)
        
        # អនុញ្ញាតឱ្យប្តូររូបភាព និងលុប ប្រសិនបើមានការ Select (មិនខ្វល់ថា Mode ណាទេ)
        self.btn_change_selected_image.setEnabled(has_selection)
        
        # កំណត់រូបភាពដើមវិញ បានលុះត្រាតែមានរូបភាពដើមដែលបាន Load រួច
        has_default = self.default_image_pixmap is not None and not self.default_image_pixmap.isNull()
        self.btn_reset_selected_image.setEnabled(has_selection and has_default)
        
        self.lbl_adj_tip.setVisible(not has_selection)

    def select_all_photos(self):
        for p in self.preview_canvas.photo_positions:
            p['selected'] = True
        self.update_image_adjustment_buttons()
        self.preview_canvas.update()
        
    def deselect_all_photos(self):
        for p in self.preview_canvas.photo_positions:
            p['selected'] = False
        self.update_image_adjustment_buttons()
        self.preview_canvas.update()
    
    def change_selected_image(self):
        options = QFileDialog.Options()
        file_names, _ = QFileDialog.getOpenFileNames(self, "ជ្រើសរើសរូបភាពថ្មី / Choose New Photos", "", "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        if file_names:
            # ទាញយក Slot ទាំងអស់ដែលបានជ្រើសរើស (Selected)
            selected_slots = [p for p in self.preview_canvas.photo_positions if p.get('selected', False)]
            
            # បញ្ចូលរូបភាពនីមួយៗទៅក្នុង Slot តាមលំដាប់ដែលបានជ្រើសរើសរូបភាព
            for i, file_path in enumerate(file_names):
                if i < len(selected_slots):
                    new_pixmap = QPixmap(file_path)
                    if not new_pixmap.isNull():
                        selected_slots[i]['image_pixmap'] = new_pixmap
            
            self.preview_canvas.update()
            self.update_image_adjustment_buttons()

    def reset_selected_image(self):
        if self.default_image_pixmap and not self.default_image_pixmap.isNull():
            for p in self.preview_canvas.photo_positions:
                if p.get('selected', False):
                    p['image_pixmap'] = self.default_image_pixmap
            self.preview_canvas.update()
            self.update_image_adjustment_buttons()
        else:
            # If no default image, clearing is the same as resetting
            self.clear_selected_image()

    def clear_selected_image(self):
        for p in self.preview_canvas.photo_positions:
            if p.get('selected', False):
                p['image_pixmap'] = None
                # Also reset pan/scale if clearing the image
                p['scale'] = 1.0
                p['pan_x'] = 0.0
                p['pan_y'] = 0.0
        self.preview_canvas.update()
        self.update_image_adjustment_buttons()



    def calculate_layout(self):
        paper_w = self.sb_width.value()
        paper_h = self.sb_height.value()

        unit = self.cb_p_unit.currentText()
        current_dpi = self.sb_dpi.value()

        active_configs = []
        total_print_qty = 0
        # តម្លៃមធ្យមសម្រាប់ប្រើក្នុងការគណនាប្លង់ (Fallback values)
        photo_w, photo_h = 30.0, 40.0
        val_w, val_h = 3.0, 4.0

        for g in self.size_groups:
            if g['chk'].isChecked() and g['qty'].value() > 0:
                vw, vh = g['w'].value(), g['h'].value()
                # បំប្លែងខ្នាតទៅ mm
                if unit == "cm": pw, ph = vw * 10, vh * 10
                elif unit == "mm": pw, ph = vw, vh
                elif unit == "inch": pw, ph = vw * 25.4, vh * 25.4
                elif unit == "pixel": pw, ph = vw * (25.4 / current_dpi), vh * (25.4 / current_dpi)
                
                active_configs.append({
                    'w': pw, 'h': ph, 
                    'qty': g['qty'].value(), 
                    'label': f"{vw:g}x{vh:g} {unit}"
                })
                total_print_qty += g['qty'].value()
                if len(active_configs) == 1:
                    photo_w, photo_h, val_w, val_h = pw, ph, vw, vh
        
        margin_t = self.sb_margin_top.value()
        margin_b = self.sb_margin_bottom.value()
        margin_l = self.sb_margin_left.value()
        margin_r = self.sb_margin_right.value()
        
        gap = self.sb_gap.value()
        
        avail_w = paper_w - (margin_l + margin_r)
        avail_h = paper_h - (margin_t + margin_b)
        
        # សម្រាប់របៀបរៀបចំថ្មី យើងប្រើការគណនាប្លង់ឆ្លាតវៃ (Smart Packing)
        # យើងនឹងព្យាយាមរកចំនួនអតិបរមា ប្រសិនបើអ្នកប្រើរើសយក "Max Printable"
        if self.rb_max_qty.isChecked() and len(active_configs) == 1:
            active_configs[0]['qty'] = 1000 # ដាក់ចំនួនធំដើម្បីឲ្យកូដរៀបចំទាល់តែពេញ

        offset_x, offset_y = margin_l, margin_t

        self.preview_canvas.paper_w = paper_w
        self.preview_canvas.paper_h = paper_h
        self.preview_canvas.photo_w = photo_w
        self.preview_canvas.photo_h = photo_h
        self.preview_canvas.size_label = f"{val_w:g}x{val_h:g} {unit}"
        
        self.preview_canvas.margin_top = margin_t
        self.preview_canvas.margin_bottom = margin_b
        self.preview_canvas.margin_left = margin_l
        self.preview_canvas.margin_right = margin_r
        self.preview_canvas.offset_x = offset_x
        self.preview_canvas.offset_y = offset_y
        self.preview_canvas.gap = gap
        self.preview_canvas.optimize_fit = self.chk_optimize_fit.isChecked()
        
        # ឥឡូវនេះ មុខងារ Manual Layout ប្រើប្រាស់ប្រព័ន្ធរៀបចំប្លង់ស្វ័យប្រវត្តិ (Optimize Fit) ជាមូលដ្ឋាន
        self.preview_canvas.generate_grid(active_configs)
        
        if self.rb_max_qty.isChecked() and len(active_configs) == 1:
            total_print_qty = len(self.preview_canvas.photo_positions)
            active_configs[0]['qty'] = total_print_qty
            
        self.preview_canvas.print_qty = total_print_qty
        
        ori_text = "បញ្ឈរ (Portrait)" if self.rb_port.isChecked() else "ផ្តេក (Landscape)"
        self.lbl_status.setText(f"<b>ចំនួនសរុប: {total_print_qty} រូបភាព ({ori_text})</b>")
        
        # អនុវត្តការតម្រឹមស្វ័យប្រវត្តិពីចំណុចទី៥ (Auto Center)
        if self.chk_center_h.isChecked():
            self.preview_canvas.center_horizontally()
        if self.chk_center_v.isChecked():
            self.preview_canvas.center_vertically()
            
        self.update_image_adjustment_buttons()
                
        self.preview_canvas.update()

    def open_settings(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle("ការកំណត់ / Settings")
        dialog.resize(400, 150)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("ទីតាំងរក្សាទុក PDF លំនាំដើម / Default PDF Save Folder:"))
        
        h_layout = QHBoxLayout()
        txt_folder = QLineEdit(self.default_pdf_folder if hasattr(self, 'default_pdf_folder') else "")
        txt_folder.setReadOnly(True)
        h_layout.addWidget(txt_folder)
        
        btn_browse = QPushButton("ជ្រើសរើស / Browse")
        def browse_folder():
            folder = QFileDialog.getExistingDirectory(dialog, "ជ្រើសរើសថតឯកសារ / Select Folder", txt_folder.text())
            if folder:
                txt_folder.setText(folder)
        btn_browse.clicked.connect(browse_folder)
        h_layout.addWidget(btn_browse)
        
        layout.addLayout(h_layout)
        
        layout.addWidget(QLabel("ទីតាំងកម្មវិធី Foxit PDF / Foxit PDF Path:"))
        
        h_foxit_layout = QHBoxLayout()
        txt_foxit = QLineEdit(self.foxit_path if hasattr(self, 'foxit_path') else "")
        txt_foxit.setReadOnly(True)
        h_foxit_layout.addWidget(txt_foxit)
        
        btn_browse_foxit = QPushButton("ជ្រើសរើស / Browse")
        def browse_foxit():
            exe_file, _ = QFileDialog.getOpenFileName(dialog, "ជ្រើសរើសកម្មវិធី Foxit / Select Foxit App", "", "Executables (*.exe)")
            if exe_file:
                txt_foxit.setText(exe_file)
        btn_browse_foxit.clicked.connect(browse_foxit)
        h_foxit_layout.addWidget(btn_browse_foxit)
        
        layout.addLayout(h_foxit_layout)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("រក្សាទុក / Save")
        def save_settings():
            self.default_pdf_folder = txt_folder.text()
            self.settings.setValue("default_pdf_folder", self.default_pdf_folder)
            self.foxit_path = txt_foxit.text()
            self.settings.setValue("foxit_path", self.foxit_path)
            dialog.accept()
        btn_save.clicked.connect(save_settings)
        btn_save.setStyleSheet("background-color: #128c7e; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        
        btn_cancel = QPushButton("បោះបង់ / Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btn_cancel.setStyleSheet("background-color: #ef4444; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
        dialog.exec_()

    def import_to_foxit(self):
        import subprocess
        from PyQt5.QtWidgets import QMessageBox
        import os
        
        if not hasattr(self, 'foxit_path') or not self.foxit_path or not os.path.exists(self.foxit_path):
            QMessageBox.warning(self, "មិនទាន់កំណត់កម្មវិធី / Not Configured", "សូមចូលទៅកាន់ Settings (⚙) ដើម្បីកំណត់ទីតាំងកម្មវិធី Foxit PDF ជាមុនសិន។")
            return
            
        file_name = self.save_pdf(show_msg=False)
        if file_name:
            try:
                subprocess.Popen([self.foxit_path, file_name])
            except Exception as e:
                QMessageBox.critical(self, "កំហុស / Error", f"មិនអាចបើកកម្មវិធី Foxit PDF បានទេ:\n{str(e)}")

    def save_pdf(self, show_msg=True):
        from PyQt5.QtWidgets import QMessageBox
        import os
        from datetime import datetime
        
        file_name = ""
        
        if hasattr(self, 'default_pdf_folder') and self.default_pdf_folder and os.path.isdir(self.default_pdf_folder):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = os.path.join(self.default_pdf_folder, f"Image_{timestamp}.pdf")
        else:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "រក្សាទុកជា PDF / Save as PDF", "", "PDF Files (*.pdf)", options=options)
            
        if not file_name:
            return
            
        from PyQt5.QtGui import QPdfWriter, QPageSize, QPageLayout, QPainter, QTransform
        from PyQt5.QtCore import QSizeF, QMarginsF, Qt, QRectF
        
        pdf_writer = QPdfWriter(file_name)
        
        paper_w = self.sb_width.value()
        paper_h = self.sb_height.value()
        
        pdf_writer.setPageSize(QPageSize(QSizeF(paper_w, paper_h), QPageSize.Millimeter))
        pdf_writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        
        dpi = self.sb_dpi.value()
        pdf_writer.setResolution(dpi)
        
        painter = QPainter(pdf_writer)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        scale = dpi / 25.4
        
        painter.fillRect(0, 0, int(paper_w * scale), int(paper_h * scale), Qt.white)
        
        for pos in self.preview_canvas.photo_positions:
            p_w, p_h = pos.get('w', self.preview_canvas.photo_w), pos.get('h', self.preview_canvas.photo_h)
            cell_w = p_w * scale
            cell_h = p_h * scale
            tw, th = max(1, int(cell_w + 1)), max(1, int(cell_h + 1))
            
            cx = pos['x'] * scale
            cy = pos['y'] * scale
            
            current_pixmap = pos.get('image_pixmap')
            target_rect = QRectF(cx, cy, cell_w, cell_h).toRect()
            
            if target_rect.width() <= 0 or target_rect.height() <= 0:
                continue
                
            if current_pixmap and not current_pixmap.isNull():
                manual_angle = pos.get('rotation_angle', 0)
                if manual_angle != 0:
                    transform = QTransform().rotate(manual_angle)
                    current_pixmap = current_pixmap.transformed(transform, Qt.SmoothTransformation)
                    
                if self.preview_canvas.optimize_fit and manual_angle == 0:
                    img_w, img_h = current_pixmap.width(), current_pixmap.height()
                    if img_w != img_h and cell_w != cell_h:
                        if (img_w > img_h) != (cell_w > cell_h):
                            transform = QTransform().rotate(90)
                            current_pixmap = current_pixmap.transformed(transform, Qt.SmoothTransformation)

                if self.preview_canvas.image_mode == 'fill':
                    painter.drawPixmap(target_rect, current_pixmap)
                elif self.preview_canvas.image_mode == 'contain':
                    pre_scaled_contain = current_pixmap.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    if pre_scaled_contain and not pre_scaled_contain.isNull():
                        x_offset = (target_rect.width() - pre_scaled_contain.width()) // 2
                        y_offset = (target_rect.height() - pre_scaled_contain.height()) // 2
                        painter.drawPixmap(target_rect.x() + x_offset, target_rect.y() + y_offset, pre_scaled_contain)
                elif self.preview_canvas.image_mode == 'cover':
                    pre_scaled_cover = current_pixmap.scaled(tw, th, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    if pre_scaled_cover and not pre_scaled_cover.isNull():
                        img_scale = pos.get('scale', 1.0)
                        pan_x = pos.get('pan_x', 0.0)
                        pan_y = pos.get('pan_y', 0.0)
                        
                        screen_scale = self.preview_canvas.paper_width_px / self.preview_canvas.paper_w if self.preview_canvas.paper_w > 0 else 1
                        pdf_pan_x = pan_x * (scale / screen_scale) if screen_scale else 0
                        pdf_pan_y = pan_y * (scale / screen_scale) if screen_scale else 0

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
                        
                        crop_x = int(max(0, min(base_crop_x - pdf_pan_x, current_cover.width() - target_rect.width())))
                        crop_y = int(max(0, min(base_crop_y - pdf_pan_y, current_cover.height() - target_rect.height())))
                        
                        cropped_pixmap = current_cover.copy(crop_x, crop_y, target_rect.width(), target_rect.height())
                        if not cropped_pixmap.isNull():
                            painter.drawPixmap(target_rect, cropped_pixmap)

                if getattr(self.preview_canvas, 'show_border', False):
                    from PyQt5.QtGui import QPen, QColor
                    painter.setPen(QPen(QColor(0, 0, 0), 2, Qt.SolidLine))
                    painter.drawRect(target_rect)
            
        painter.end()
        if show_msg:
            QMessageBox.information(self, "ជោគជ័យ / Success", "ឯកសារ PDF ត្រូវបានរក្សាទុកដោយជោគជ័យ! / PDF saved successfully!")
        return file_name

if __name__ == '__main__':
    import ctypes
    import os
    try:
        myappid = 'photoprintapp.version.1.0.2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    # ដាក់ Font ខ្មែរជាគោល ដើម្បីជៀសវាងអក្សរខូច
    font = QFont("Khmer OS Siemreap", 9)
    app.setFont(font)
    
    from PyQt5.QtGui import QIcon
    def get_resource_path(relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        return os.path.join(base_path, relative_path)
        
    icon_path = get_resource_path('Assets/Icon.ico')
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    window = PhotoPrintApp()
    window.setWindowIcon(app_icon)
    window.showMaximized()
    sys.exit(app.exec_())
