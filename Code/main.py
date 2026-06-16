import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QGroupBox, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QRadioButton, 
                             QCheckBox, QSlider, QGridLayout, QSizePolicy, QFileDialog, QButtonGroup,
                             QTabWidget, QTextEdit, QFontComboBox, QColorDialog, QDialog,
                             QGraphicsView, QGraphicsScene, QGraphicsPolygonItem, QGraphicsEllipseItem)
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QTransform, QImage
import cv2
import numpy as np
import updater
class CornerHandle(QGraphicsEllipseItem):
    def __init__(self, x, y, radius, index, parent=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2, parent)
        self.setPos(x, y)
        self.index = index
        from PyQt5.QtGui import QBrush, QColor, QPen
        from PyQt5.QtCore import Qt
        self.setBrush(QBrush(QColor(0, 120, 215, 200)))
        self.setPen(QPen(Qt.white, 2))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CrossCursor)
        self.dialog = None

    def itemChange(self, change, value):
        from PyQt5.QtWidgets import QGraphicsEllipseItem
        if change == QGraphicsEllipseItem.ItemPositionChange and self.dialog:
            self.dialog.update_polygon()
        return super().itemChange(change, value)

class MovablePolygonItem(QGraphicsPolygonItem):
    def __init__(self, dialog, parent=None):
        super().__init__(parent)
        self.dialog = dialog
        from PyQt5.QtCore import Qt
        self.setCursor(Qt.OpenHandCursor)
        self.last_pos = None

    def mousePressEvent(self, event):
        from PyQt5.QtCore import Qt
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            self.last_pos = event.scenePos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.last_pos is not None:
            delta = event.scenePos() - self.last_pos
            for handle in self.dialog.handles:
                handle.setPos(handle.pos() + delta)
            self.last_pos = event.scenePos()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        from PyQt5.QtCore import Qt
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.OpenHandCursor)
            self.last_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class PerspectiveCropDialog(QDialog):
    def __init__(self, image_path, parent=None, initial_points=None):
        super().__init__(parent)
        self.setWindowTitle("កែតម្រូវជ្រុងកាត / Adjust ID Card Corners")
        self.image_path = image_path
        self.cv_img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        self.layout = QVBoxLayout(self)
        
        lbl_info = QLabel("<b>របៀបប្រើ៖</b> សូមទាញចំណុចពណ៌ខៀវ ដើម្បីកែជ្រុង ឬទាញផ្ទៃកណ្តាល ដើម្បីរំកិលទីតាំងទាំងមូល")
        lbl_info.setStyleSheet("color: #333; padding: 5px; background: #e0f2fe; border-radius: 4px;")
        self.layout.addWidget(lbl_info)
        
        from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.layout.addWidget(self.view)
        
        self.qpixmap = QPixmap(image_path)
        self.pixmap_item = self.scene.addPixmap(self.qpixmap)
        
        if initial_points:
            self.points = initial_points
        else:
            self.points = self.detect_corners()
        
        from PyQt5.QtGui import QPolygonF, QBrush, QColor, QPen
        from PyQt5.QtCore import Qt
        self.handles = []
        
        self.polygon_item = MovablePolygonItem(self)
        self.polygon_item.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
        self.polygon_item.setBrush(QBrush(QColor(0, 120, 215, 50)))
        self.scene.addItem(self.polygon_item)
        radius = max(10, min(self.qpixmap.width(), self.qpixmap.height()) * 0.02)
        for i, pt in enumerate(self.points):
            handle = CornerHandle(pt[0], pt[1], radius, i)
            handle.dialog = self
            self.scene.addItem(handle)
            self.handles.append(handle)
            
        self.update_polygon()
        
        btn_layout = QHBoxLayout()
        
        btn_change = QPushButton("ប្តូររូបភាព / Change Image")
        btn_change.setStyleSheet("background-color: #f59e0b; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_change.clicked.connect(self.change_image)
        
        btn_crop = QPushButton("យល់ព្រម / Crop")
        btn_crop.setStyleSheet("background-color: #2b52ff; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_crop.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("បោះបង់ / Cancel")
        btn_cancel.setStyleSheet("padding: 10px; border-radius: 5px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_change)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_crop)
        self.layout.addLayout(btn_layout)
        
        self.resize(1000, 700)
        self.cropped_pixmap = None

    def change_image(self):
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtCore import Qt, QSettings
        import os
        settings = QSettings("PhotoPrintApp", "Settings")
        last_dir = settings.value("last_open_dir", "")
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូបភាពថ្មី / Select New Image", last_dir, "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        if file_name:
            settings.setValue("last_open_dir", os.path.dirname(file_name))
            self.image_path = file_name
            self.cv_img = cv2.imdecode(np.fromfile(file_name, dtype=np.uint8), cv2.IMREAD_COLOR)
            self.qpixmap = QPixmap(file_name)
            self.pixmap_item.setPixmap(self.qpixmap)
            
            self.points = self.detect_corners()
            
            radius = max(10, min(self.qpixmap.width(), self.qpixmap.height()) * 0.02)
            for i, pt in enumerate(self.points):
                if i < len(self.handles):
                    self.handles[i].setPos(pt[0], pt[1])
                    self.handles[i].setRect(-radius, -radius, radius * 2, radius * 2)
            
            self.update_polygon()
            self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)


    def showEvent(self, event):
        super().showEvent(event)
        from PyQt5.QtCore import Qt
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def update_polygon(self):
        from PyQt5.QtGui import QPolygonF
        polygon = QPolygonF()
        for handle in self.handles:
            polygon.append(handle.pos())
        self.polygon_item.setPolygon(polygon)

    def detect_corners(self):
        img = self.cv_img
        if img is None:
            return self.default_corners()
            
        orig_h, orig_w = img.shape[:2]
        ratio = orig_h / 800.0
        if ratio > 0:
            dim = (int(orig_w / ratio), 800)
            resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
        else:
            resized = img.copy()
            ratio = 1.0

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # Blur to reduce noise
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 1. Edge detection using Canny
        edged1 = cv2.Canny(gray_blur, 75, 200)
        
        # 2. Auto Canny based on median
        v = np.median(gray_blur)
        edged2 = cv2.Canny(gray_blur, int(max(0, (1.0 - 0.33) * v)), int(min(255, (1.0 + 0.33) * v)))
        
        # 3. Adaptive thresholding
        thresh = cv2.adaptiveThreshold(gray_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        # Morphological operations to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edged1_closed = cv2.morphologyEx(edged1, cv2.MORPH_CLOSE, kernel)
        edged2_closed = cv2.morphologyEx(edged2, cv2.MORPH_CLOSE, kernel)
        thresh_closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        methods = [edged1, edged2, edged1_closed, edged2_closed, thresh, thresh_closed]
        
        best_screenCnt = None
        max_area = 0
        min_area_thresh = (resized.shape[0] * resized.shape[1]) * 0.05  # At least 5% of the image

        for method in methods:
            # RETR_LIST allows finding all contours, good if document is inside another shape
            contours, _ = cv2.findContours(method, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            # Sort contours by area in descending order and keep top 10
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
            
            for c in contours:
                area = cv2.contourArea(c)
                if area < min_area_thresh:
                    continue
                    
                peri = cv2.arcLength(c, True)
                # Try different epsilon values to approximate a 4-point polygon
                for eps in [0.02, 0.03, 0.04, 0.05, 0.06]:
                    approx = cv2.approxPolyDP(c, eps * peri, True)
                    if len(approx) == 4 and area > max_area:
                        max_area = area
                        best_screenCnt = approx
                        break

        screenCnt = best_screenCnt

        if screenCnt is None:
            # Fallback: Find the largest contour and get its minAreaRect
            largest_c = None
            max_c_area = 0
            for method in methods:
                contours, _ = cv2.findContours(method, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c in contours:
                    area = cv2.contourArea(c)
                    if area > max_c_area and area > min_area_thresh:
                        max_c_area = area
                        largest_c = c
            
            if largest_c is not None:
                rect = cv2.minAreaRect(largest_c)
                box = cv2.boxPoints(rect)
                screenCnt = np.int32(box)

        if screenCnt is None:
            return self.default_corners()

        screenCnt = screenCnt.reshape(4, 2) * ratio
        
        # Order points: top-left, top-right, bottom-right, bottom-left
        rect = np.zeros((4, 2), dtype="float32")
        s = screenCnt.sum(axis=1)
        rect[0] = screenCnt[np.argmin(s)]
        rect[2] = screenCnt[np.argmax(s)]
        
        diff = np.diff(screenCnt, axis=1)
        rect[1] = screenCnt[np.argmin(diff)]
        rect[3] = screenCnt[np.argmax(diff)]
        
        return rect.tolist()

    def default_corners(self):
        w = self.qpixmap.width()
        h = self.qpixmap.height()
        mx = w * 0.1
        my = h * 0.1
        return [[mx, my], [w - mx, my], [w - mx, h - my], [mx, h - my]]

    def accept(self):
        if self.cv_img is not None:
            rect = np.array([
                [self.handles[0].pos().x(), self.handles[0].pos().y()],
                [self.handles[1].pos().x(), self.handles[1].pos().y()],
                [self.handles[2].pos().x(), self.handles[2].pos().y()],
                [self.handles[3].pos().x(), self.handles[3].pos().y()]
            ], dtype="float32")
            
            self.final_points = rect.tolist()
            (tl, tr, br, bl) = rect
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))

            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))

            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]], dtype="float32")

            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(self.cv_img, M, (maxWidth, maxHeight))
            
            if warped.shape[0] > warped.shape[1]:
                warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)

            warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
            self.cropped_cv_img = warped_rgb.copy()
            h, w, ch = warped_rgb.shape
            bytes_per_line = ch * w
            from PyQt5.QtGui import QImage
            qimg = QImage(warped_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.cropped_pixmap = QPixmap.fromImage(qimg.copy())
        super().accept()

class PdfImportDialog(QDialog):
    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("នាំចូលឯកសារ PDF / Import PDF")
        self.pdf_path = pdf_path
        self.temp_image_path = None
        
        try:
            import fitz
            self.doc = fitz.open(pdf_path)
            self.total_pages = self.doc.page_count
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"មិនអាចបើកឯកសារ PDF បានទេ:\n{e}")
            self.reject()
            return
            
        self.layout = QVBoxLayout(self)
        
        lbl_info = QLabel("<b>ជ្រើសរើសទំព័រ និងទំហំរូបភាពពី PDF</b>")
        lbl_info.setStyleSheet("color: #333; padding: 5px; background: #e0f2fe; border-radius: 4px;")
        self.layout.addWidget(lbl_info)
        
        from PyQt5.QtWidgets import QFormLayout, QSpinBox, QComboBox
        form_layout = QFormLayout()
        
        self.spin_page = QSpinBox()
        self.spin_page.setRange(1, self.total_pages)
        self.spin_page.setValue(1)
        form_layout.addRow("ទំព័រទី / Page:", self.spin_page)
        
        self.combo_res = QComboBox()
        self.combo_res.addItems([
            "Determine automatically",
            "72 pixels/inch",
            "96 pixels/inch",
            "150 pixels/inch",
            "300 pixels/inch",
            "600 pixels/inch",
            "1200 pixels/inch",
            "2400 pixels/inch"
        ])
        # Default to 300 pixels/inch (index 4)
        self.combo_res.setCurrentIndex(4)
        form_layout.addRow("កម្រិតច្បាស់ / Resolution:", self.combo_res)
        
        self.layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_accept = QPushButton("យល់ព្រម / Accept")
        btn_accept.setStyleSheet("background-color: #2b52ff; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_accept.clicked.connect(self.process_pdf)
        
        btn_cancel = QPushButton("បោះបង់ / Cancel")
        btn_cancel.setStyleSheet("padding: 10px; border-radius: 5px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_accept)
        self.layout.addLayout(btn_layout)
        self.resize(400, 200)
        
    def process_pdf(self):
        try:
            import fitz
            import tempfile
            import os
            
            page_num = self.spin_page.value() - 1
            res_text = self.combo_res.currentText()
            
            if "Determine automatically" in res_text:
                dpi = 300
            else:
                dpi = int(res_text.split(" ")[0])
                
            page = self.doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            
            fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            
            pix.save(temp_path)
            self.temp_image_path = temp_path
            self.accept()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"មិនអាចបំប្លែង PDF ទៅជារូបភាពបានទេ:\n{e}")


class PreviewWidget(QWidget):
    """ Custom Widget សម្រាប់គូរទិដ្ឋភាពក្រដាស និងក្រឡារូបថត (Live Print Preview) """
    selectionChanged = pyqtSignal()
    itemDoubleClicked = pyqtSignal(dict)
    stateChanged = pyqtSignal()

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
        self.border_weight = 0.50
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

    def generate_grid(self, items_to_place=None):
        """ items_to_place: list of dicts {'w': mm, 'h': mm, 'label': str} """
        if not items_to_place: return []

        old_positions = self.photo_positions.copy()
        self.photo_positions.clear()

        if getattr(self, 'grid_cols', 0) > 0 and getattr(self, 'grid_rows', 0) > 0 and not self.is_manual:
            cols = self.grid_cols
            rows = self.grid_rows
            
            avail_w = self.paper_w - self.margin_left - self.margin_right
            avail_h = self.paper_h - self.margin_top - self.margin_bottom
            
            cell_w = (avail_w - (cols - 1) * self.gap) / cols if cols > 0 else 10
            cell_h = (avail_h - (rows - 1) * self.gap) / rows if rows > 0 else 10
            
            placed_count = 0
            for idx, item in enumerate(items_to_place):
                if placed_count >= cols * rows:
                    return items_to_place[idx:]
                
                col = placed_count % cols
                row = placed_count // cols
                
                cx = self.offset_x + col * (cell_w + self.gap)
                cy = self.offset_y + row * (cell_h + self.gap)
                
                w = item['w'] if item.get('is_original_size') else cell_w
                h = item['h'] if item.get('is_original_size') else cell_h
                
                px = cx + (cell_w - w) / 2
                py = cy + (cell_h - h) / 2
                
                self.photo_positions.append({
                    'x': px, 'y': py,
                    'w': w, 'h': h, 'label': item.get('label', ''),
                    'scale': 1.0, 'pan_x': 0.0, 'pan_y': 0.0
                })
                placed_count += 1
                
            return []

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
                
                if not fits_norm and not fits_rot:
                    if curr_x == self.offset_x and curr_y == self.offset_y:
                        fits_norm = True
                    else:
                        return items_to_place[idx:]
                
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
                    
                    if not fits_norm and not fits_rot: return items_to_place[idx:]
                    
                    if fits_norm:
                        cw, ch = w_for_packing, h_for_packing
                    else:
                        cw, ch = h_for_packing, w_for_packing
                        is_rotated = True

                if curr_y + ch > avail_h + 0.1: return items_to_place[idx:]

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
        self.stateChanged.emit()

    def align_selected_top(self):
        """ តម្រឹមរូបភាពដែលបានជ្រើសរើសទៅខាងលើបំផុតនៃក្រុម """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 2: return
        min_y = min(p['y'] for p in selected)
        for p in selected: p['y'] = min_y
        self.update()
        self.stateChanged.emit()

    def align_selected_right(self):
        """ តម្រឹមរូបភាពដែលបានជ្រើសរើសទៅខាងស្តាំបំផុតនៃក្រុម """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 2: return
        max_right = max(p['x'] + p['w'] for p in selected)
        for p in selected: p['x'] = max_right - p['w']
        self.update()
        self.stateChanged.emit()

    def align_selected_bottom(self):
        """ តម្រឹមរូបភាពដែលបានជ្រើសរើសទៅខាងក្រោមបំផុតនៃក្រុម """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) < 2: return
        max_bottom = max(p['y'] + p['h'] for p in selected)
        for p in selected: p['y'] = max_bottom - p['h']
        self.update()
        self.stateChanged.emit()

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
        self.stateChanged.emit()

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
        self.stateChanged.emit()

    def center_horizontally(self):
        """ តម្រឹមរូបភាពកណ្តាលតាមផ្ដេក (Center Horizontally) ធៀបនឹងក្រដាស និង Margin """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) > 1:
            min_x = min(p['x'] for p in selected)
            max_right = max(p['x'] + p['w'] for p in selected)
            group_center_x = min_x + (max_right - min_x) / 2.0
            for p in selected:
                p_center = p['x'] + p['w']/2.0
                p['x'] += group_center_x - p_center
        else:
            target_group = selected if selected else self.photo_positions
            if not target_group: return
            min_x = min(p['x'] for p in target_group)
            max_right = max(p['x'] + p['w'] for p in target_group)
            group_width = max_right - min_x
            avail_width = self.paper_w - self.margin_left - self.margin_right
            paper_center_x = self.margin_left + avail_width / 2.0
            group_center_x = min_x + group_width / 2.0
            shift_x = paper_center_x - group_center_x
            for p in target_group: p['x'] += shift_x
        self.update()
        self.stateChanged.emit()

    def center_vertically(self):
        """ តម្រឹមរូបភាពកណ្តាលតាមបញ្ឈរ (Center Vertically) ធៀបនឹងក្រដាស និង Margin """
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) > 1:
            min_y = min(p['y'] for p in selected)
            max_bottom = max(p['y'] + p['h'] for p in selected)
            group_center_y = min_y + (max_bottom - min_y) / 2.0
            for p in selected:
                p_center = p['y'] + p['h']/2.0
                p['y'] += group_center_y - p_center
        else:
            target_group = selected if selected else self.photo_positions
            if not target_group: return
            min_y = min(p['y'] for p in target_group)
            max_bottom = max(p['y'] + p['h'] for p in target_group)
            group_height = max_bottom - min_y
            avail_height = self.paper_h - self.margin_top - self.margin_bottom
            paper_center_y = self.margin_top + avail_height / 2.0
            group_center_y = min_y + group_height / 2.0
            shift_y = paper_center_y - group_center_y
            for p in target_group: p['y'] += shift_y
        self.update()
        self.stateChanged.emit()

    def align_top(self):
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) > 1:
            min_y = min(p['y'] for p in selected)
            for p in selected: p['y'] = min_y
        else:
            target_group = selected if selected else self.photo_positions
            if not target_group: return
            min_y = min(p['y'] for p in target_group)
            shift_y = self.margin_top - min_y
            for p in target_group: p['y'] += shift_y
        self.update()
        self.stateChanged.emit()

    def align_bottom(self):
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) > 1:
            max_bottom = max(p['y'] + p['h'] for p in selected)
            for p in selected: p['y'] = max_bottom - p['h']
        else:
            target_group = selected if selected else self.photo_positions
            if not target_group: return
            max_bottom = max(p['y'] + p['h'] for p in target_group)
            shift_y = (self.paper_h - self.margin_bottom) - max_bottom
            for p in target_group: p['y'] += shift_y
        self.update()
        self.stateChanged.emit()

    def align_left(self):
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) > 1:
            min_x = min(p['x'] for p in selected)
            for p in selected: p['x'] = min_x
        else:
            target_group = selected if selected else self.photo_positions
            if not target_group: return
            min_x = min(p['x'] for p in target_group)
            shift_x = self.margin_left - min_x
            for p in target_group: p['x'] += shift_x
        self.update()
        self.stateChanged.emit()

    def align_right(self):
        selected = [p for p in self.photo_positions if p.get('selected')]
        if len(selected) > 1:
            max_right = max(p['x'] + p['w'] for p in selected)
            for p in selected: p['x'] = max_right - p['w']
        else:
            target_group = selected if selected else self.photo_positions
            if not target_group: return
            max_right = max(p['x'] + p['w'] for p in target_group)
            shift_x = (self.paper_w - self.margin_right) - max_right
            for p in target_group: p['x'] += shift_x
        self.update()
        self.stateChanged.emit()

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
                painter.save()
                if getattr(self, 'apply_rounded_corners', False) and getattr(self, 'is_manual', False):
                    from PyQt5.QtGui import QPainterPath
                    path = QPainterPath()
                    radius_px = 3.18 * scale
                    path.addRoundedRect(QRectF(target_rect), radius_px, radius_px)
                    painter.setClipPath(path)
                    
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

                painter.restore()

                if getattr(self, 'show_border', False):
                    border_pt = getattr(self, 'border_weight', 0.50)
                    border_px = border_pt * (25.4 / 72.0) * scale
                    painter.setPen(QPen(QColor(0, 0, 0), max(0.0, border_px), Qt.SolidLine))
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
        
        # Emitting state change for any modifications during mouse interaction
        if getattr(self, 'was_modified_during_mouse', False) or getattr(self, 'is_panning', False) or getattr(self, 'drag_start_pos', False):
            self.stateChanged.emit()
        # Just emit it to be safe for any dragging
        self.stateChanged.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            scale = self.paper_width_px / self.paper_w if self.paper_w > 0 else 1        
            click_x = event.x()
            click_y = event.y()
            for i in range(len(self.photo_positions)-1, -1, -1):
                pos = self.photo_positions[i]
                cell_w = pos.get('w', self.photo_w) * scale
                cell_h = pos.get('h', self.photo_h) * scale
                cx = self.paper_x_px + pos['x'] * scale
                cy = self.paper_y_px + pos['y'] * scale
                rect = QRectF(cx, cy, cell_w, cell_h)
                
                if rect.contains(click_x, click_y):
                    self.itemDoubleClicked.emit(pos)
                    break
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

import re

def build_mixed_html(text, font_kh, font_en, color, bg_color, is_bold, is_italic, is_underline, align, font_size_px=None):
    from PyQt5.QtCore import Qt
    align_str = "left"
    if align & Qt.AlignHCenter: align_str = "center"
    elif align & Qt.AlignRight: align_str = "right"
    elif align & Qt.AlignJustify: align_str = "justify"
    
    color_str = color.name()
    bg_str = ""
    if bg_color and bg_color.alpha() > 0:
        bg_str = f"background-color: {bg_color.name()};"
        
    style_str = f"color: {color_str}; {bg_str}"
    if is_bold: style_str += " font-weight: bold;"
    if is_italic: style_str += " font-style: italic;"
    if is_underline: style_str += " text-decoration: underline;"
    if font_size_px is not None:
        style_str += f" font-size: {font_size_px}px;"

    html = f"<div style='text-align: {align_str}; {style_str}'>"
    
    result = ""
    current_lang = None
    current_chunk = ""
    
    for char in text:
        if '\u1780' <= char <= '\u17FF' or '\u19E0' <= char <= '\u19FF':
            lang = 'kh'
        elif char.isspace():
            lang = current_lang if current_lang else 'en'
        else:
            lang = 'en'
            
        if lang != current_lang:
            if current_chunk:
                f_family = font_kh if current_lang == 'kh' else font_en
                safe_chunk = current_chunk.replace('\n', '<br>')
                result += f"<span style=\"font-family: '{f_family}';\">{safe_chunk}</span>"
            current_chunk = char
            current_lang = lang
        else:
            current_chunk += char
            
    if current_chunk:
        f_family = font_kh if current_lang == 'kh' else font_en
        safe_chunk = current_chunk.replace('\n', '<br>')
        result += f"<span style=\"font-family: '{f_family}';\">{safe_chunk}</span>"
        
    html += result + "</div>"
    return html

class TextPreviewWidget(QWidget):
    """ Custom Widget សម្រាប់គូរទិដ្ឋភាពអក្សរធំ (Live Text Preview) """
    selectionChanged = pyqtSignal(int)
    stateChanged = pyqtSignal()
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
        self.text_color = QColor(0, 0, 0)
        self.font_family_kh = "Khmer OS Muol Light"
        self.font_family_en = "Arial"
        self.base_font_size = 50.0
        self.font_bold = False
        self.font_italic = False
        self.font_underline = False
        self.text_bg_color = QColor(Qt.transparent)
        self.text_align = Qt.AlignCenter
        self.bg_color = QColor(255, 255, 255)
        self.auto_fit = False
        
        self.free_stretch = False
        self.lines_data = [] # List of dicts: {'rect': QRectF, 'font': QFont, 'color': QColor, 'bg_color': QColor}
        self.selected_line_idx = 0
        self.drag_mode = None
        self.drag_start_pos = None
        self.drag_start_rect = None
        self.current_scale = 1.0
        self.current_paper_x = 0
        self.current_paper_y = 0
        self.setMouseTracking(True)

    def set_text(self, new_text):
        self.text = new_text
        if self.free_stretch:
            lines = self.text.split('\n')
            while len(self.lines_data) < len(lines):
                if self.lines_data:
                    last_rect = self.lines_data[-1]['rect']
                    new_rect = QRectF(last_rect.x(), last_rect.y() + last_rect.height() + 5, last_rect.width(), last_rect.height())
                else:
                    new_rect = QRectF(self.margin_left, self.margin_top, self.paper_w - self.margin_left - self.margin_right, 30)
                
                self.lines_data.append({
                    'rect': new_rect,
                    'font_kh': self.font_family_kh,
                    'font_en': self.font_family_en,
                    'base_size': self.base_font_size,
                    'bold': self.font_bold,
                    'italic': self.font_italic,
                    'underline': self.font_underline,
                    'color': QColor(self.text_color),
                    'bg_color': QColor(Qt.transparent)
                })
            
            if len(self.lines_data) > len(lines):
                self.lines_data = self.lines_data[:len(lines)]
                
            if self.selected_line_idx >= len(lines):
                self.selected_line_idx = max(0, len(lines) - 1)
                self.selectionChanged.emit(self.selected_line_idx)
        self.update()

    def get_handle_at(self, pos):
        if not self.free_stretch or not self.lines_data: return None
        if self.selected_line_idx < 0 or self.selected_line_idx >= len(self.lines_data): return None
        
        sel_rect_mm = self.lines_data[self.selected_line_idx]['rect']
        rect_px = QRectF(self.current_paper_x + sel_rect_mm.x() * self.current_scale, 
                         self.current_paper_y + sel_rect_mm.y() * self.current_scale, 
                         sel_rect_mm.width() * self.current_scale, 
                         sel_rect_mm.height() * self.current_scale)
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
                self.drag_start_rect = QRectF(self.lines_data[self.selected_line_idx]['rect'])
            elif self.free_stretch and self.lines_data:
                for i, line_data in enumerate(self.lines_data):
                    rect_mm = line_data['rect']
                    rect_px = QRectF(self.current_paper_x + rect_mm.x() * self.current_scale, 
                                     self.current_paper_y + rect_mm.y() * self.current_scale, 
                                     rect_mm.width() * self.current_scale, 
                                     rect_mm.height() * self.current_scale)
                    if rect_px.contains(event.pos()):
                        if self.selected_line_idx != i:
                            self.selected_line_idx = i
                            self.selectionChanged.emit(self.selected_line_idx)
                        self.drag_mode = 'C'
                        self.drag_start_pos = event.pos()
                        self.drag_start_rect = QRectF(rect_mm)
                        self.update()
                        break

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

        if self.drag_mode and self.drag_start_pos and self.drag_start_rect and self.selected_line_idx < len(self.lines_data):
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
            
            self.lines_data[self.selected_line_idx]['rect'] = new_rect
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drag_mode is not None:
                self.stateChanged.emit()
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
                lines = self.text.split('\n')
                from PyQt5.QtGui import QTextDocument
                
                # Make sure lines_data is synchronized if not already
                if not self.lines_data:
                    self.set_text(self.text)
                    
                for i, line in enumerate(lines):
                    if i >= len(self.lines_data): break
                    line_data = self.lines_data[i]
                    rect_mm = line_data['rect']
                    rect_px = QRectF(paper_x + rect_mm.x() * scale, paper_y + rect_mm.y() * scale, rect_mm.width() * scale, rect_mm.height() * scale)
                    
                    bg_color = line_data.get('bg_color', QColor(Qt.transparent))
                    if bg_color.alpha() > 0:
                        painter.fillRect(rect_px, bg_color)
                        
                    f_kh = line_data.get('font_kh', self.font_family_kh)
                    f_en = line_data.get('font_en', self.font_family_en)
                    is_b = line_data.get('bold', False)
                    is_i = line_data.get('italic', False)
                    is_u = line_data.get('underline', False)
                    l_color = line_data.get('color', self.text_color)
                    
                    doc = QTextDocument()
                    doc.setDocumentMargin(0)
                    html = build_mixed_html(line, f_kh, f_en, l_color, None, is_b, is_i, is_u, Qt.AlignLeft, 100)
                    doc.setHtml(html)
                    
                    base_rect = doc.documentLayout().documentSize()
                    
                    painter.save()
                    painter.translate(rect_px.x(), rect_px.y())
                    sx = rect_px.width() / base_rect.width() if base_rect.width() > 0 else 1
                    sy = rect_px.height() / base_rect.height() if base_rect.height() > 0 else 1
                    painter.scale(sx, sy)
                    doc.drawContents(painter)
                    painter.restore()
                    
                    # Draw selection border and handles only for the selected line
                    if i == self.selected_line_idx:
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
                rect = QRectF(m_left, m_top, m_right - m_left, m_bottom - m_top)
                from PyQt5.QtGui import QTextDocument
                doc = QTextDocument()
                doc.setDocumentMargin(0)
                
                if hasattr(self, 'text_bg_color') and self.text_bg_color.alpha() > 0:
                    painter.fillRect(rect, self.text_bg_color)
                
                if self.auto_fit:
                    min_size = 1
                    max_size = 5000
                    best_size = min_size
                    
                    while min_size <= max_size:
                        mid_size = (min_size + max_size) // 2
                        html = build_mixed_html(self.text, self.font_family_kh, self.font_family_en, self.text_color, None, self.font_bold, self.font_italic, self.font_underline, self.text_align, mid_size)
                        doc.setHtml(html)
                        doc.setTextWidth(rect.width())
                        
                        if doc.size().height() <= rect.height():
                            best_size = mid_size
                            min_size = mid_size + 1
                        else:
                            max_size = mid_size - 1
                    html = build_mixed_html(self.text, self.font_family_kh, self.font_family_en, self.text_color, None, self.font_bold, self.font_italic, self.font_underline, self.text_align, best_size)
                    doc.setHtml(html)
                    doc.setTextWidth(rect.width())
                else:
                    pt_to_mm = 25.4 / 72.0
                    size_mm = self.base_font_size * pt_to_mm
                    size_px = size_mm * scale
                    html = build_mixed_html(self.text, self.font_family_kh, self.font_family_en, self.text_color, None, self.font_bold, self.font_italic, self.font_underline, self.text_align, int(max(1, size_px)))
                    doc.setHtml(html)
                    doc.setTextWidth(rect.width())
                    
                painter.save()
                painter.translate(rect.topLeft())
                doc.drawContents(painter)
                painter.restore()

from PyQt5.QtCore import QThread, pyqtSignal, QPointF, QRectF, Qt, QRect, QSizeF
from PyQt5.QtWidgets import QDialog, QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PyQt5.QtGui import QPen, QBrush, QColor, QMouseEvent

class CropGraphicsView(QGraphicsView):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        
        self.crop_rect_item = QGraphicsRectItem()
        self.crop_rect_item.setPen(QPen(Qt.red, 3, Qt.DashLine))
        self.crop_rect_item.setBrush(QBrush(QColor(255, 0, 0, 50)))
        self.scene.addItem(self.crop_rect_item)
        self.crop_rect_item.hide()
        
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.drawing_crop = False
        self.origin = QPointF()
        
    def wheelEvent(self, event):
        if event.modifiers() == Qt.NoModifier or event.modifiers() == Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 0.85
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ShiftModifier:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                super().mousePressEvent(event)
            else:
                self.setDragMode(QGraphicsView.NoDrag)
                self.drawing_crop = True
                self.origin = self.mapToScene(event.pos())
                self.crop_rect_item.setRect(QRectF(self.origin, QSizeF()))
                self.crop_rect_item.show()
        elif event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            mock_event = QMouseEvent(event.type(), event.localPos(), event.windowPos(), event.screenPos(),
                                     Qt.LeftButton, event.buttons() | Qt.LeftButton, event.modifiers())
            super().mousePressEvent(mock_event)
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if self.drawing_crop:
            current_point = self.mapToScene(event.pos())
            self.crop_rect_item.setRect(QRectF(self.origin, current_point).normalized())
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drawing_crop:
                self.drawing_crop = False
                self.setDragMode(QGraphicsView.ScrollHandDrag)
            else:
                super().mouseReleaseEvent(event)
        elif event.button() == Qt.MiddleButton:
            mock_event = QMouseEvent(event.type(), event.localPos(), event.windowPos(), event.screenPos(),
                                     Qt.LeftButton, event.buttons() & ~Qt.LeftButton, event.modifiers())
            super().mouseReleaseEvent(mock_event)
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            super().mouseReleaseEvent(event)
            
    def get_crop_rect(self):
        if not self.crop_rect_item.isVisible():
            return QRect()
        return self.crop_rect_item.rect().toRect().intersected(self.pixmap_item.boundingRect().toRect())

class ImageCropDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("កាត់រូបភាព / Crop Image")
        self.image_path = image_path
        
        self.layout = QVBoxLayout(self)
        self.pixmap = QPixmap(self.image_path)
        
        lbl_info = QLabel("<b>របៀបប្រើ៖</b> អូសម៉ៅស៍ឆ្វេងដើម្បីគូសប្រអប់កាត់អក្សរ | រំកិលកង់ម៉ៅស៍ ដើម្បីពង្រីក/ពង្រួម | ចុច Shift+ម៉ៅស៍ឆ្វេង ដើម្បីទាញរូបភាពចុះឡើង")
        lbl_info.setStyleSheet("color: #333; padding: 5px; background: #e0f2fe; border-radius: 4px;")
        self.layout.addWidget(lbl_info)
        
        self.crop_view = CropGraphicsView(self.pixmap)
        self.layout.addWidget(self.crop_view)
        
        btn_layout = QHBoxLayout()
        btn_crop = QPushButton("កាត់និងទាញអត្ថបទ / Crop & Extract")
        btn_crop.setStyleSheet("background-color: #2b52ff; color: white; padding: 8px; font-weight: bold;")
        btn_crop.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("បោះបង់ / Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_crop)
        self.layout.addLayout(btn_layout)
        
        self.resize(1000, 700)
        
    def showEvent(self, event):
        super().showEvent(event)
        self.crop_view.fitInView(self.crop_view.scene.sceneRect(), Qt.KeepAspectRatio)
        
    def get_cropped_image(self):
        rect = self.crop_view.get_crop_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return self.image_path
            
        cropped = self.pixmap.copy(rect)
        import tempfile, os
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "cropped_ocr_img.jpg")
        cropped.save(temp_path, "JPG")
        return temp_path

class OCRWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, image_path, api_key, model_name):
        super().__init__()
        self.image_path = image_path
        self.api_key = api_key
        self.model_name = model_name
        
    def run(self):
        try:
            from google import genai
            from PIL import Image
            import time
            
            client = genai.Client(api_key=self.api_key)
            img = Image.open(self.image_path)
            
            # Reduce image size to speed up upload and API processing
            max_size = 1024
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to RGB to ensure smaller file size (avoiding uncompressed PNG/RGBA payloads)
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            
            prompt = "Extract all the text from this image exactly as it appears. Maintain the original language (e.g., Khmer or English) and spacing. Do not add any extra commentary or markdown formatting. Just return the text."
            
            max_retries = 10  # Increase retries to handle long durations
            delay = 2
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=[img, prompt]
                    )
                    self.finished_signal.emit(response.text)
                    return
                except Exception as e:
                    err_str = str(e).lower()
                    if ("503" in err_str or "timeout" in err_str or "unavailable" in err_str) and attempt < max_retries - 1:
                        time.sleep(delay)
                        delay = min(delay * 2, 10)  # Cap delay at 10 seconds
                    else:
                        raise e
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                msg = f"សូមអភ័យទោស! ចំនួនប្រើប្រាស់ API សម្រាប់ម៉ូដែលនេះត្រូវបានអស់ហើយ (Quota Exceeded)។\n\nព័ត៌មានលម្អិត (Error Details):\n{err_str}"
                self.error_signal.emit(msg)
            else:
                self.error_signal.emit(err_str)

class HistoryManager:
    def __init__(self, limit=50):
        self.undo_stack = []
        self.redo_stack = []
        self.limit = limit
        self.is_undoing_redoing = False

    def push(self, state):
        if self.is_undoing_redoing:
            return
        if self.undo_stack and self.undo_stack[-1] == state:
            return
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.limit:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def can_undo(self):
        return len(self.undo_stack) > 1

    def can_redo(self):
        return len(self.redo_stack) > 0

    def undo(self):
        if self.can_undo():
            self.redo_stack.append(self.undo_stack.pop())
            return self.undo_stack[-1]
        return None

    def redo(self):
        if self.can_redo():
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            return state
        return None

class PhotoPrintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle("Fast Print Text Photo")
        self.default_image_pixmap = None # Added default image pixmap
        
        self.history_tab1 = HistoryManager()
        self.history_tab2 = HistoryManager()
        self.history_tab3 = HistoryManager()
        
        from PyQt5.QtCore import QSettings
        self.settings = QSettings("PhotoPrintApp", "Settings")
        self.default_pdf_folder = self.settings.value("default_pdf_folder", "")
        self.foxit_path = self.settings.value("foxit_path", "")
        self.resize(1366, 768)
        self.showMaximized()
        self.initUI()
        
        # Check for updates automatically in the background
        updater.check_for_updates(self)

        # Undo/Redo Shortcuts
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo_action)
        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.shortcut_redo.activated.connect(self.redo_action)
        self.tabs.currentChanged.connect(self.update_undo_redo_ui)

    def save_state_tab1(self):
        state = [[p.copy() for p in c.photo_positions] for c in self.preview_canvases]
        self.history_tab1.push(state)
        self.update_undo_redo_ui()

    def save_state_tab2(self):
        if not hasattr(self, 'text_preview'): return
        copied_lines = []
        for l in getattr(self.text_preview, 'lines_data', []):
            c_l = dict(l)
            if 'rect' in c_l:
                from PyQt5.QtCore import QRectF
                c_l['rect'] = QRectF(c_l['rect'])
            if 'color' in c_l:
                from PyQt5.QtGui import QColor
                c_l['color'] = QColor(c_l['color'])
            if 'bg_color' in c_l:
                from PyQt5.QtGui import QColor
                c_l['bg_color'] = QColor(c_l['bg_color'])
            copied_lines.append(c_l)
        state = {
            'text': self.text_preview.text,
            'lines_data': copied_lines
        }
        self.history_tab2.push(state)
        self.update_undo_redo_ui()

    def save_state_tab3(self):
        if not hasattr(self, 'id_preview'): return
        state = [p.copy() for p in self.id_preview.photo_positions]
        self.history_tab3.push(state)
        self.update_undo_redo_ui()

    def update_undo_redo_ui(self, index=None):
        if hasattr(self, 'btn_undo1'):
            self.btn_undo1.setEnabled(self.history_tab1.can_undo())
            self.btn_redo1.setEnabled(self.history_tab1.can_redo())
        if hasattr(self, 'btn_undo2'):
            self.btn_undo2.setEnabled(self.history_tab2.can_undo())
            self.btn_redo2.setEnabled(self.history_tab2.can_redo())
        if hasattr(self, 'btn_undo3'):
            self.btn_undo3.setEnabled(self.history_tab3.can_undo())
            self.btn_redo3.setEnabled(self.history_tab3.can_redo())

    def undo_action(self):
        idx = self.tabs.currentIndex()
        if idx == 0 and self.history_tab1.can_undo():
            self.history_tab1.is_undoing_redoing = True
            state = self.history_tab1.undo()
            if state is not None:
                for c, s in zip(self.preview_canvases, state):
                    c.photo_positions = [p.copy() for p in s]
                    c.update()
            self.history_tab1.is_undoing_redoing = False
        elif idx == 1 and self.history_tab2.can_undo():
            self.history_tab2.is_undoing_redoing = True
            state = self.history_tab2.undo()
            if state is not None:
                self.text_preview.text = state['text']
                if hasattr(self, 'txt_banner'):
                    self.txt_banner.blockSignals(True)
                    self.txt_banner.setText(state['text'])
                    self.txt_banner.blockSignals(False)
                copied_lines = []
                for l in state['lines_data']:
                    c_l = dict(l)
                    if 'rect' in c_l:
                        from PyQt5.QtCore import QRectF
                        c_l['rect'] = QRectF(c_l['rect'])
                    if 'color' in c_l:
                        from PyQt5.QtGui import QColor
                        c_l['color'] = QColor(c_l['color'])
                    if 'bg_color' in c_l:
                        from PyQt5.QtGui import QColor
                        c_l['bg_color'] = QColor(c_l['bg_color'])
                    copied_lines.append(c_l)
                self.text_preview.lines_data = copied_lines
                self.text_preview.update()
            self.history_tab2.is_undoing_redoing = False
        elif idx == 2 and self.history_tab3.can_undo():
            self.history_tab3.is_undoing_redoing = True
            state = self.history_tab3.undo()
            if state is not None:
                self.id_preview.photo_positions = [p.copy() for p in state]
                self.id_preview.update()
            self.history_tab3.is_undoing_redoing = False
        self.update_undo_redo_ui()

    def redo_action(self):
        idx = self.tabs.currentIndex()
        if idx == 0 and self.history_tab1.can_redo():
            self.history_tab1.is_undoing_redoing = True
            state = self.history_tab1.redo()
            if state is not None:
                for c, s in zip(self.preview_canvases, state):
                    c.photo_positions = [p.copy() for p in s]
                    c.update()
            self.history_tab1.is_undoing_redoing = False
        elif idx == 1 and self.history_tab2.can_redo():
            self.history_tab2.is_undoing_redoing = True
            state = self.history_tab2.redo()
            if state is not None:
                self.text_preview.text = state['text']
                if hasattr(self, 'txt_banner'):
                    self.txt_banner.blockSignals(True)
                    self.txt_banner.setText(state['text'])
                    self.txt_banner.blockSignals(False)
                copied_lines = []
                for l in state['lines_data']:
                    c_l = dict(l)
                    if 'rect' in c_l:
                        from PyQt5.QtCore import QRectF
                        c_l['rect'] = QRectF(c_l['rect'])
                    if 'color' in c_l:
                        from PyQt5.QtGui import QColor
                        c_l['color'] = QColor(c_l['color'])
                    if 'bg_color' in c_l:
                        from PyQt5.QtGui import QColor
                        c_l['bg_color'] = QColor(c_l['bg_color'])
                    copied_lines.append(c_l)
                self.text_preview.lines_data = copied_lines
                self.text_preview.update()
            self.history_tab2.is_undoing_redoing = False
        elif idx == 2 and self.history_tab3.can_redo():
            self.history_tab3.is_undoing_redoing = True
            state = self.history_tab3.redo()
            if state is not None:
                self.id_preview.photo_positions = [p.copy() for p in state]
                self.id_preview.update()
            self.history_tab3.is_undoing_redoing = False
        self.update_undo_redo_ui()

    def initUI(self):
        # Main Widget and Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        self.tabs = QTabWidget(main_widget)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 10px 20px;
                font-weight: normal;
                font-size: 12px;
                font-family: 'Khmer OS Battambang', Arial;
            }
            QTabBar::tab:selected {
                background-color: #0084c7;
                color: white;
            }
            QTabBar::tab:!selected {
                background-color: #e0e0e0;
                color: black;
            }
        """)
        
        # TAB 1: Photo Print
        self.tab1 = QWidget()
        main_layout = QHBoxLayout(self.tab1)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # បង្កើតបញ្ជី Canvas សម្រាប់ទំព័រច្រើន
        from PyQt5.QtWidgets import QScrollArea, QStackedWidget
        self.preview_canvases = []
        self.current_page_index = 0
        
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent;")
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #dbe2e9; border: none; }")
        self.scroll_area.setWidget(self.stacked_widget)

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
        h_btn_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("បញ្ចូលរូបភាព / Load Image")
        self.btn_load.setStyleSheet("background-color: #0084c7; color: white; padding: 10px; border-radius: 5px;")
        self.btn_load.clicked.connect(self.load_image)
        h_btn_layout.addWidget(self.btn_load)
        
        self.btn_clear = QPushButton("✖")
        self.btn_clear.setToolTip("លុបរូបភាព / Clear Image")
        self.btn_clear.setFixedSize(38, 38)
        self.btn_clear.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 5px; font-weight: bold; font-size: 16px;")
        self.btn_clear.clicked.connect(self.clear_image)
        self.btn_clear.setVisible(False)
        h_btn_layout.addWidget(self.btn_clear)
        
        gb_photo_layout.addLayout(h_btn_layout)
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

        self.btn_align_left.clicked.connect(self.align_selected_left)
        self.btn_align_top.clicked.connect(self.align_selected_top)
        self.btn_align_right.clicked.connect(self.align_selected_right)
        self.btn_align_bottom.clicked.connect(self.align_selected_bottom)
        self.btn_dist_h.clicked.connect(self.distribute_horizontally)
        self.btn_dist_v.clicked.connect(self.distribute_vertically)

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
        h_mid_top = QHBoxLayout()
        h_mid_top.addWidget(mid_title)
        self.btn_undo1 = QPushButton("↶ Undo (Ctrl+Z)")
        self.btn_redo1 = QPushButton("↷ Redo (Ctrl+Y)")
        self.btn_undo1.clicked.connect(self.undo_action)
        self.btn_redo1.clicked.connect(self.redo_action)
        self.btn_undo1.setEnabled(False)
        self.btn_redo1.setEnabled(False)
        h_mid_top.addWidget(self.btn_undo1)
        h_mid_top.addWidget(self.btn_redo1)
        mid_layout.addLayout(h_mid_top)
        
        mid_layout.addWidget(self.scroll_area)

        # ប៊ូតុងបញ្ជាទំព័រ (Pagination Controls)
        self.pagination_widget = QWidget()
        pag_layout = QHBoxLayout(self.pagination_widget)
        pag_layout.setContentsMargins(0, 5, 0, 0)
        
        self.btn_prev_page = QPushButton("◀ ត្រឡប់ក្រោយ / Prev")
        self.btn_prev_page.clicked.connect(self.go_to_previous_page)
        
        self.lbl_page_info = QLabel("ទំព័រ / Page: 0 / 0")
        self.lbl_page_info.setAlignment(Qt.AlignCenter)
        
        self.btn_next_page = QPushButton("ទៅមុខ / Next ▶")
        self.btn_next_page.clicked.connect(self.go_to_next_page)
        
        pag_layout.addWidget(self.btn_prev_page)
        pag_layout.addWidget(self.lbl_page_info)
        pag_layout.addWidget(self.btn_next_page)
        
        mid_layout.addWidget(self.pagination_widget)
        self.pagination_widget.setVisible(False)

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
        
        self.chk_show_border = QCheckBox("បន្ទាត់ស៊ុម / Image Outline")
        self.chk_show_border.stateChanged.connect(self.toggle_border)
        gb_margin_layout.addWidget(self.chk_show_border)
        
        h_border_weight_layout = QHBoxLayout()
        h_border_weight_layout.addWidget(QLabel("កម្រាស់ / Weight (pt):"))
        self.sl_border_weight = QSlider(Qt.Horizontal)
        self.sl_border_weight.setRange(0, 100) # 0 to 10.0 pt
        self.sl_border_weight.setValue(5) # 0.5 pt
        self.sb_border_weight = QDoubleSpinBox()
        self.sb_border_weight.setDecimals(2)
        self.sb_border_weight.setRange(0.00, 10.00)
        self.sb_border_weight.setValue(0.50)
        self.sb_border_weight.setSingleStep(0.10)
        
        self.sl_border_weight.valueChanged.connect(self.on_border_slider_changed)
        self.sb_border_weight.valueChanged.connect(self.on_border_spinbox_changed)
        
        h_border_weight_layout.addWidget(self.sl_border_weight)
        h_border_weight_layout.addWidget(self.sb_border_weight)
        gb_margin_layout.addLayout(h_border_weight_layout)
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

        # 8. ច្រើនរូបក្នុងមួយសន្លឹក (Multi-Image Grid)
        gb_grid_mode = QGroupBox("៨. ច្រើនរូបក្នុងមួយសន្លឹក / Multi-Image Grid")
        gb_grid_mode_layout = QVBoxLayout()
        
        self.chk_enable_grid = QCheckBox("ប្រើប្រាស់មុខងារនេះ / Enable Grid Mode")
        self.chk_enable_grid.stateChanged.connect(self.toggle_grid_mode)
        gb_grid_mode_layout.addWidget(self.chk_enable_grid)
        
        grid_rc_layout = QGridLayout()
        grid_rc_layout.addWidget(QLabel("ជួរឈរ (Columns):"), 0, 0)
        self.sb_grid_cols = QSpinBox(); self.sb_grid_cols.setRange(1, 100); self.sb_grid_cols.setValue(1)
        self.sb_grid_cols.valueChanged.connect(self.calculate_layout)
        self.sb_grid_cols.setEnabled(False)
        grid_rc_layout.addWidget(self.sb_grid_cols, 0, 1)
        
        grid_rc_layout.addWidget(QLabel("ជួរដេក (Rows):"), 0, 2)
        self.sb_grid_rows = QSpinBox(); self.sb_grid_rows.setRange(1, 100); self.sb_grid_rows.setValue(1)
        self.sb_grid_rows.valueChanged.connect(self.calculate_layout)
        self.sb_grid_rows.setEnabled(False)
        grid_rc_layout.addWidget(self.sb_grid_rows, 0, 3)
        
        gb_grid_mode_layout.addLayout(grid_rc_layout)
        
        self.rb_grid_same_size = QRadioButton("ធ្វើឲ្យទំហំប៉ុនគ្នា / Make same size of image")
        self.rb_grid_same_size.setChecked(True)
        self.rb_grid_same_size.setEnabled(False)
        self.rb_grid_same_size.toggled.connect(self.calculate_layout)
        
        self.rb_grid_original_size = QRadioButton("រក្សាទំហំដើម / Original size of image")
        self.rb_grid_original_size.setEnabled(False)
        self.rb_grid_original_size.toggled.connect(self.calculate_layout)
        
        gb_grid_mode_layout.addWidget(self.rb_grid_same_size)
        gb_grid_mode_layout.addWidget(self.rb_grid_original_size)
        
        gb_grid_mode.setLayout(gb_grid_mode_layout)
        right_layout.addWidget(gb_grid_mode)

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
        
        # TAB 3: ID Card Print
        self.tab3 = QWidget()
        self.initIDCardUI(self.tab3)
        
        self.tabs.addTab(self.tab1, "១. បោះពុម្ពរូបថត / Photo Print")
        self.tabs.addTab(self.tab2, "២. សរសេរអក្សរធំ / Large Text Banner")
        self.tabs.addTab(self.tab3, "៣. បោះពុម្ពកាតសម្គាល់ខ្លួន / ID Card Print")
        
        self.dark_mode_cb = QCheckBox("ងងឹត / Dark Mode")
        self.dark_mode_cb.setStyleSheet("padding: 5px; font-weight: bold; background: transparent; color: inherit;")
        self.dark_mode_cb.stateChanged.connect(self.toggle_dark_mode)
        self.tabs.setCornerWidget(self.dark_mode_cb, Qt.TopRightCorner)
        
        layout = QVBoxLayout(main_widget)
        layout.addWidget(self.tabs)
        layout.setContentsMargins(0,0,0,0)
        
        # ធ្វើការគណនាបឋមនៅពេលចាប់ផ្តើមកម្មវិធី
        self.calculate_layout()
        
        # Load theme setting
        saved_theme = self.settings.value("theme", "light")
        if saved_theme == "dark":
            self.dark_mode_cb.setChecked(True)
            self.toggle_dark_mode(Qt.Checked)

    def toggle_dark_mode(self, state):
        app = QApplication.instance()
        if state == Qt.Checked:
            self.settings.setValue("theme", "dark")
            app.setStyleSheet("""
                QWidget { background-color: #2b2b2b; color: #ffffff; }
                QGroupBox { border: 1px solid #555555; margin-top: 15px; color: #ffffff; border-radius: 5px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
                QComboBox, QSpinBox, QDoubleSpinBox { background-color: #3b3b3b; color: #ffffff; border: 1px solid #555555; padding: 2px; }
                QPushButton { background-color: #3b3b3b; color: #ffffff; border: 1px solid #555555; padding: 5px; border-radius: 4px; }
                QPushButton:hover { background-color: #4b4b4b; }
                QTabWidget::pane { border: 1px solid #555555; background: #2b2b2b; }
                QTabBar::tab { padding: 10px 20px; font-weight: normal; font-size: 12px; font-family: 'Khmer OS Battambang', Arial; background-color: #3b3b3b; color: #ffffff; border: 1px solid #555555; }
                QTabBar::tab:selected { background-color: #0084c7; color: white; }
                QTextEdit { background-color: #3b3b3b; color: #ffffff; border: 1px solid #555555; }
                QLabel { color: #ffffff; background: transparent; }
                QScrollArea { background-color: #2b2b2b; border: none; }
                QScrollBar:vertical { background: #2b2b2b; width: 15px; margin: 0px 0px 0px 0px; }
                QScrollBar::handle:vertical { background: #555555; min-height: 20px; border-radius: 7px; }
                QScrollBar::add-line:vertical { height: 0px; }
                QScrollBar::sub-line:vertical { height: 0px; }
                QScrollBar:horizontal { background: #2b2b2b; height: 15px; margin: 0px 0px 0px 0px; }
                QScrollBar::handle:horizontal { background: #555555; min-width: 20px; border-radius: 7px; }
                QScrollBar::add-line:horizontal { width: 0px; }
                QScrollBar::sub-line:horizontal { width: 0px; }
                QMenu { background-color: #2b2b2b; color: #ffffff; border: 1px solid #555555; }
                QMenu::item:selected { background-color: #0084c7; color: #ffffff; }
            """)
        else:
            self.settings.setValue("theme", "light")
            app.setStyleSheet("")
            # Restore specific styles
            self.tabs.setStyleSheet("""
                QTabBar::tab {
                    padding: 10px 20px;
                    font-weight: normal;
                    font-size: 12px;
                    font-family: 'Khmer OS Battambang', Arial;
                }
                QTabBar::tab:selected {
                    background-color: #0084c7;
                    color: white;
                }
                QTabBar::tab:!selected {
                    background-color: #e0e0e0;
                    color: black;
                }
            """)

    def initTextUI(self, parent_widget):
        from PyQt5.QtWidgets import QTextEdit, QFontComboBox, QColorDialog
        layout = QHBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Panel (Controls)
        left_panel = QWidget()
        left_panel.setFixedWidth(400)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)
        
        title_lbl = QLabel("<b>សរសេរអក្សរធំ / Large Text Banner</b>")
        title_lbl.setFont(QFont("Khmer OS Battambang", 12))
        left_layout.addWidget(title_lbl)
        
        # Text Input
        gb_text = QGroupBox("១. អត្ថបទ / Text Input")
        gb_text_layout = QVBoxLayout()
        
        h_model_layout = QHBoxLayout()
        h_model_layout.addWidget(QLabel("ម៉ូដែល AI / AI Model:"))
        self.cb_ai_model = QComboBox()
        self.cb_ai_model.addItems([
            "gemini-2.5-flash",
            "gemini-3.5-flash"
        ])
        h_model_layout.addWidget(self.cb_ai_model)
        
        self.btn_change_api = QPushButton("🔑 ផ្លាស់ប្តូរ API Key")
        self.btn_change_api.setStyleSheet("background-color: #f59e0b; color: white; padding: 5px; border-radius: 3px; font-weight: bold;")
        self.btn_change_api.clicked.connect(self.change_api_key)
        h_model_layout.addWidget(self.btn_change_api)
        
        gb_text_layout.addLayout(h_model_layout)
        
        self.btn_ai_ocr = QPushButton("ទាញអត្ថបទពីរូបភាព (AI) / Extract Text from Image")
        self.btn_ai_ocr.setStyleSheet("background-color: #2b52ff; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        self.btn_ai_ocr.clicked.connect(self.extract_text_from_image)
        gb_text_layout.addWidget(self.btn_ai_ocr)
        
        self.txt_banner = QTextEdit()
        self.txt_banner.setPlaceholderText("បញ្ចូលអត្ថបទទីនេះ...")
        font_battambang = QFont("Khmer OS Battambang", 12)
        self.txt_banner.setFont(font_battambang)
        self.txt_banner.textChanged.connect(self.update_text_preview)
        # We will save state inside update_text_preview to capture both typing and font changes
        gb_text_layout.addWidget(self.txt_banner)
        
        self.btn_clear_text = QPushButton("លុបអត្ថបទ / Clear Text")
        self.btn_clear_text.setStyleSheet("background-color: #ef4444; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        self.btn_clear_text.clicked.connect(self.txt_banner.clear)
        gb_text_layout.addWidget(self.btn_clear_text)
        gb_text.setLayout(gb_text_layout)
        left_layout.addWidget(gb_text)

        self.btn_clear_text = QPushButton("លុបអត្ថបទ / Clear Text")
        self.btn_clear_text.setStyleSheet("background-color: #ef4444; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        self.btn_clear_text.clicked.connect(self.txt_banner.clear)
        
        # Font Settings
        gb_font = QGroupBox("២. កំណត់អក្សរ / Font Settings")
        gb_font_layout = QVBoxLayout()
        
        self.cb_font_kh = QComboBox()
        self.cb_font_en = QComboBox()
        
        from PyQt5.QtCore import QSettings
        self.settings = QSettings("PhotoPrintApp", "Settings")
        
        from PyQt5.QtGui import QFontDatabase
        all_fonts = QFontDatabase().families()
        freq_fonts = ["AKbalthom Moul 4", "Khmer OS Muol Light", "Khmer OS Battambang", "Times New Roman", "Arial", "Roboto", "Inter"]
        
        h_fonts_layout = QHBoxLayout()
        
        # Khmer Font
        v_kh_layout = QVBoxLayout()
        v_kh_layout.addWidget(QLabel("អក្សរខ្មែរ (Khmer Font):"))
        self.cb_font_kh.setEditable(True)
        self.cb_font_kh.addItems(freq_fonts)
        self.cb_font_kh.insertSeparator(len(freq_fonts))
        for f in all_fonts:
            if f not in freq_fonts:
                self.cb_font_kh.addItem(f)
        saved_kh_font = self.settings.value("font_kh", "Khmer OS Muol Light")
        self.cb_font_kh.setCurrentText(saved_kh_font)
        self.cb_font_kh.currentTextChanged.connect(self.save_fonts)
        v_kh_layout.addWidget(self.cb_font_kh)
        h_fonts_layout.addLayout(v_kh_layout)
        
        # English Font
        v_en_layout = QVBoxLayout()
        v_en_layout.addWidget(QLabel("អក្សរអង់គ្លេស (English Font):"))
        self.cb_font_en.setEditable(True)
        self.cb_font_en.addItems(freq_fonts)
        self.cb_font_en.insertSeparator(len(freq_fonts))
        for f in all_fonts:
            if f not in freq_fonts:
                self.cb_font_en.addItem(f)
        saved_en_font = self.settings.value("font_en", "Arial")
        self.cb_font_en.setCurrentText(saved_en_font)
        self.cb_font_en.currentTextChanged.connect(self.save_fonts)
        v_en_layout.addWidget(self.cb_font_en)
        h_fonts_layout.addLayout(v_en_layout)
        
        gb_font_layout.addLayout(h_fonts_layout)
        
        h_font = QHBoxLayout()
        
        self.btn_bold = QPushButton("B")
        self.btn_bold.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_bold.setCheckable(True)
        self.btn_italic = QPushButton("I")
        self.btn_italic.setFont(QFont("Arial", 10, QFont.Normal, True))
        self.btn_italic.setCheckable(True)
        self.btn_underline = QPushButton("U")
        font_u = QFont("Arial", 10)
        font_u.setUnderline(True)
        self.btn_underline.setFont(font_u)
        self.btn_underline.setCheckable(True)
        
        self.btn_bold.toggled.connect(self.update_text_preview)
        self.btn_italic.toggled.connect(self.update_text_preview)
        self.btn_underline.toggled.connect(self.update_text_preview)
        
        h_font.addWidget(self.btn_bold)
        h_font.addWidget(self.btn_italic)
        h_font.addWidget(self.btn_underline)
        h_font.addStretch()
        gb_font_layout.addLayout(h_font)
        
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
        
        self.btn_text_bg_color = QPushButton("ពណ៌ផ្ទៃអក្សរ / Text BG")
        self.btn_text_bg_color.setStyleSheet("background-color: transparent; color: black;")
        self.btn_text_bg_color.clicked.connect(self.choose_text_bg_color)
        
        h_color.addWidget(self.btn_text_color)
        h_color.addWidget(self.btn_text_bg_color)
        gb_font_layout.addLayout(h_color)
        
        h_align = QHBoxLayout()
        self.btn_align_left_t = QPushButton("Left")
        self.btn_align_center_t = QPushButton("Center")
        self.btn_align_right_t = QPushButton("Right")
        
        self.btn_align_left_t.clicked.connect(lambda: self.set_text_h_align(Qt.AlignLeft))
        self.btn_align_center_t.clicked.connect(lambda: self.set_text_h_align(Qt.AlignHCenter))
        self.btn_align_right_t.clicked.connect(lambda: self.set_text_h_align(Qt.AlignRight))
        
        h_align.addWidget(self.btn_align_left_t)
        h_align.addWidget(self.btn_align_center_t)
        h_align.addWidget(self.btn_align_right_t)
        gb_font_layout.addLayout(h_align)
        
        v_align = QHBoxLayout()
        self.btn_align_top_t = QPushButton("Top")
        self.btn_align_mid_t = QPushButton("Mid")
        self.btn_align_bot_t = QPushButton("Bottom")
        
        self.btn_align_top_t.clicked.connect(lambda: self.set_text_v_align(Qt.AlignTop))
        self.btn_align_mid_t.clicked.connect(lambda: self.set_text_v_align(Qt.AlignVCenter))
        self.btn_align_bot_t.clicked.connect(lambda: self.set_text_v_align(Qt.AlignBottom))
        
        v_align.addWidget(self.btn_align_top_t)
        v_align.addWidget(self.btn_align_mid_t)
        v_align.addWidget(self.btn_align_bot_t)
        gb_font_layout.addLayout(v_align)
        
        gb_font.setLayout(gb_font_layout)
        left_layout.addWidget(gb_font)
        
        # Paper Settings
        gb_paper = QGroupBox("៣. ក្រដាស និងគែម / Paper & Margin")
        gb_paper_layout = QVBoxLayout()
        self.cb_t_paper = QComboBox()
        self.cb_t_paper.addItems(["A4 (210 x 297 mm)", "A3 (297 x 420 mm)", "A5 (148 x 210 mm)", "Letter (215.9 x 279.4 mm)", "Custom / ផ្សេងៗ"])
        self.cb_t_paper.currentIndexChanged.connect(self.on_t_paper_changed)
        gb_paper_layout.addWidget(QLabel("ទំហំក្រដាស / Paper Size:"))
        gb_paper_layout.addWidget(self.cb_t_paper)
        
        self.w_custom_t_paper = QWidget()
        h_custom = QHBoxLayout(self.w_custom_t_paper)
        h_custom.setContentsMargins(0, 0, 0, 0)
        self.sb_custom_t_w = QDoubleSpinBox()
        self.sb_custom_t_w.setRange(10, 5000)
        self.sb_custom_t_w.setValue(210)
        self.sb_custom_t_w.valueChanged.connect(self.update_text_paper)
        self.sb_custom_t_h = QDoubleSpinBox()
        self.sb_custom_t_h.setRange(10, 5000)
        self.sb_custom_t_h.setValue(297)
        self.sb_custom_t_h.valueChanged.connect(self.update_text_paper)
        h_custom.addWidget(QLabel("W(mm):"))
        h_custom.addWidget(self.sb_custom_t_w)
        h_custom.addWidget(QLabel("H(mm):"))
        h_custom.addWidget(self.sb_custom_t_h)
        self.w_custom_t_paper.hide()
        gb_paper_layout.addWidget(self.w_custom_t_paper)
        
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
        self.sb_t_margin.setValue(5)
        self.sb_t_margin.valueChanged.connect(self.update_text_preview)
        h_margin.addWidget(self.sb_t_margin)
        gb_paper_layout.addLayout(h_margin)
        
        gb_paper.setLayout(gb_paper_layout)
        left_layout.addWidget(gb_paper)
        
        left_layout.addStretch()
        
        # Action Buttons
        btn_save_pdf = QPushButton("រក្សាទុកជា PDF")
        btn_save_pdf.setStyleSheet("background-color: #128c7e; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_save_pdf.clicked.connect(self.save_text_pdf)
        
        btn_print = QPushButton("បញ្ជូនទៅ Foxit")
        btn_print.setStyleSheet("background-color: #5850ec; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_print.clicked.connect(self.import_text_to_foxit)
        
        # Right Panel (Action Buttons)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setFixedWidth(130)
        
        right_layout.addStretch()
        right_layout.addWidget(btn_save_pdf)
        right_layout.addWidget(btn_print)
        
        # Middle Panel (Preview)
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_title = QLabel("<b>ទិដ្ឋភាពបង្ហាញជាក់ស្តែង / LIVE TEXT PREVIEW</b>")
        mid_title.setAlignment(Qt.AlignCenter)
        mid_title.setFont(QFont("Khmer OS Battambang", 11))
        h_mid_top = QHBoxLayout()
        h_mid_top.addWidget(mid_title)
        self.btn_undo2 = QPushButton("↶ Undo (Ctrl+Z)")
        self.btn_redo2 = QPushButton("↷ Redo (Ctrl+Y)")
        self.btn_undo2.clicked.connect(self.undo_action)
        self.btn_redo2.clicked.connect(self.redo_action)
        self.btn_undo2.setEnabled(False)
        self.btn_redo2.setEnabled(False)
        h_mid_top.addWidget(self.btn_undo2)
        h_mid_top.addWidget(self.btn_redo2)
        mid_layout.addLayout(h_mid_top)
        
        self.text_preview = TextPreviewWidget()
        self.text_preview.selectionChanged.connect(self.on_text_selection_changed)
        self.text_preview.stateChanged.connect(self.save_state_tab2)
        mid_layout.addWidget(self.text_preview)
        
        layout.addWidget(left_panel)
        layout.addWidget(mid_panel, 1)
        layout.addWidget(right_panel)
        
        self.text_color = QColor(0, 0, 0)
        self.text_bg_color = QColor(Qt.transparent)
        self.bg_color = QColor(255, 255, 255)
        self.text_h_align = Qt.AlignHCenter
        self.text_v_align = Qt.AlignVCenter
        self.text_align = self.text_h_align | self.text_v_align
        self.update_text_paper()

    def on_t_paper_changed(self):
        txt = self.cb_t_paper.currentText()
        if "Custom" in txt:
            self.w_custom_t_paper.show()
        else:
            self.w_custom_t_paper.hide()
        self.update_text_paper()

    def update_text_paper(self):
        txt = self.cb_t_paper.currentText()
        if "A4" in txt: w, h = 210.0, 297.0
        elif "A3" in txt: w, h = 297.0, 420.0
        elif "A5" in txt: w, h = 148.0, 210.0
        elif "Custom" in txt:
            w, h = self.sb_custom_t_w.value(), self.sb_custom_t_h.value()
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
        lines = self.txt_banner.toPlainText().split('\n')
        num_lines = max(1, len(lines))
        
        avail_h = self.text_preview.paper_h - 2*m
        avail_w = self.text_preview.paper_w - 2*m
        
        gap = 5.0 # mm gap between lines
        line_h = (avail_h - gap * (num_lines - 1)) / num_lines
        
        for i, data in enumerate(self.text_preview.lines_data):
            y = m + i * (line_h + gap)
            data['rect'] = QRectF(m, y, avail_w, line_h)
            
        self.text_preview.update()

    def save_fonts(self):
        self.settings.setValue("font_kh", self.cb_font_kh.currentText())
        self.settings.setValue("font_en", self.cb_font_en.currentText())
        self.update_text_preview()

    def update_text_preview(self):
        self.text_preview.set_text(self.txt_banner.toPlainText())
        
        self.text_preview.font_family_kh = self.cb_font_kh.currentText()
        self.text_preview.font_family_en = self.cb_font_en.currentText()
        self.text_preview.base_font_size = self.sb_font_size.value()
        self.text_preview.font_bold = self.btn_bold.isChecked()
        self.text_preview.font_italic = self.btn_italic.isChecked()
        self.text_preview.font_underline = self.btn_underline.isChecked()
        
        self.text_preview.text_color = self.text_color
        self.text_preview.text_bg_color = self.text_bg_color
        self.text_preview.bg_color = self.bg_color
        self.text_preview.text_align = self.text_align
        self.text_preview.auto_fit = self.chk_auto_fit.isChecked()
        
        if self.chk_free_stretch.isChecked() and self.text_preview.lines_data:
            idx = self.text_preview.selected_line_idx
            if 0 <= idx < len(self.text_preview.lines_data):
                self.text_preview.lines_data[idx]['font_kh'] = self.cb_font_kh.currentText()
                self.text_preview.lines_data[idx]['font_en'] = self.cb_font_en.currentText()
                self.text_preview.lines_data[idx]['base_size'] = self.sb_font_size.value()
                self.text_preview.lines_data[idx]['color'] = self.text_color
                self.text_preview.lines_data[idx]['bold'] = self.btn_bold.isChecked()
                self.text_preview.lines_data[idx]['italic'] = self.btn_italic.isChecked()
                self.text_preview.lines_data[idx]['underline'] = self.btn_underline.isChecked()
                
        m = self.sb_t_margin.value()
        self.text_preview.margin_top = m
        self.text_preview.margin_bottom = m
        self.text_preview.margin_left = m
        self.text_preview.margin_right = m
        self.text_preview.update()
        if not getattr(self.history_tab2, 'is_undoing_redoing', False):
            self.save_state_tab2()
        
    def on_text_selection_changed(self, idx):
        if 0 <= idx < len(self.text_preview.lines_data):
            data = self.text_preview.lines_data[idx]
            
            self.cb_font_kh.blockSignals(True)
            self.cb_font_kh.setCurrentText(data.get('font_kh', self.cb_font_kh.currentText()))
            self.cb_font_kh.blockSignals(False)
            
            self.cb_font_en.blockSignals(True)
            self.cb_font_en.setCurrentText(data.get('font_en', self.cb_font_en.currentText()))
            self.cb_font_en.blockSignals(False)
            
            self.btn_bold.blockSignals(True)
            self.btn_bold.setChecked(data.get('bold', False))
            self.btn_bold.blockSignals(False)
            
            self.btn_italic.blockSignals(True)
            self.btn_italic.setChecked(data.get('italic', False))
            self.btn_italic.blockSignals(False)
            
            self.btn_underline.blockSignals(True)
            self.btn_underline.setChecked(data.get('underline', False))
            self.btn_underline.blockSignals(False)
            
            self.text_color = data['color']
            lum = self.text_color.red() * 0.299 + self.text_color.green() * 0.587 + self.text_color.blue() * 0.114
            text_col = "black" if lum > 128 else "white"
            self.btn_text_color.setStyleSheet(f"background-color: {self.text_color.name()}; color: {text_col};")
            
            self.text_bg_color = data.get('bg_color', QColor(Qt.transparent))
            if self.text_bg_color.alpha() == 0:
                self.btn_text_bg_color.setStyleSheet("background-color: transparent; color: black;")
            else:
                lum_bg = self.text_bg_color.red() * 0.299 + self.text_bg_color.green() * 0.587 + self.text_bg_color.blue() * 0.114
                bg_text_col = "black" if lum_bg > 128 else "white"
                self.btn_text_bg_color.setStyleSheet(f"background-color: {self.text_bg_color.name()}; color: {bg_text_col};")
                
    def choose_text_bg_color(self):
        from PyQt5.QtWidgets import QColorDialog
        init_color = self.text_bg_color if self.text_bg_color.alpha() > 0 else QColor(255, 255, 255)
        color = QColorDialog.getColor(init_color, self, "ជ្រើសរើសពណ៌ផ្ទៃអក្សរ / Text BG Color", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.text_bg_color = color
            
            lum_bg = self.text_bg_color.red() * 0.299 + self.text_bg_color.green() * 0.587 + self.text_bg_color.blue() * 0.114
            bg_text_col = "black" if lum_bg > 128 else "white"
            self.btn_text_bg_color.setStyleSheet(f"background-color: {self.text_bg_color.name()}; color: {bg_text_col};")
            
            if self.chk_free_stretch.isChecked() and self.text_preview.lines_data:
                idx = self.text_preview.selected_line_idx
                if 0 <= idx < len(self.text_preview.lines_data):
                    self.text_preview.lines_data[idx]['bg_color'] = self.text_bg_color
            
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

    def set_text_h_align(self, align):
        if self.chk_free_stretch.isChecked() and self.text_preview.lines_data:
            idx = self.text_preview.selected_line_idx
            if 0 <= idx < len(self.text_preview.lines_data):
                rect = self.text_preview.lines_data[idx]['rect']
                m = self.sb_t_margin.value()
                w = rect.width()
                if align == Qt.AlignLeft:
                    rect.moveLeft(m)
                elif align == Qt.AlignHCenter:
                    paper_w = self.text_preview.paper_w
                    avail_w = paper_w - 2*m
                    rect.moveLeft(m + (avail_w - w)/2)
                elif align == Qt.AlignRight:
                    rect.moveRight(self.text_preview.paper_w - m)
                self.text_preview.update()
        else:
            self.text_h_align = align
            self.text_align = self.text_h_align | self.text_v_align
            self.update_text_preview()

    def set_text_v_align(self, align):
        if self.chk_free_stretch.isChecked() and self.text_preview.lines_data:
            idx = self.text_preview.selected_line_idx
            if 0 <= idx < len(self.text_preview.lines_data):
                rect = self.text_preview.lines_data[idx]['rect']
                m = self.sb_t_margin.value()
                h = rect.height()
                if align == Qt.AlignTop:
                    rect.moveTop(m)
                elif align == Qt.AlignVCenter:
                    paper_h = self.text_preview.paper_h
                    avail_h = paper_h - 2*m
                    rect.moveTop(m + (avail_h - h)/2)
                elif align == Qt.AlignBottom:
                    rect.moveBottom(self.text_preview.paper_h - m)
                self.text_preview.update()
        else:
            self.text_v_align = align
            self.text_align = self.text_h_align | self.text_v_align
            self.update_text_preview()

    def change_api_key(self):
        from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox
        
        pwd, ok_pwd = QInputDialog.getText(
            self,
            "ទាមទារលេខសម្ងាត់ / Password Required",
            "សូមបញ្ចូលលេខសម្ងាត់ ដើម្បីផ្លាស់ប្តូរ API Key៖",
            QLineEdit.Password
        )
        
        if not ok_pwd:
            return
            
        if pwd != "1234":
            QMessageBox.warning(self, "បរាជ័យ / Error", "លេខសម្ងាត់មិនត្រឹមត្រូវទេ! / Incorrect Password!")
            return
            
        current_key = self.settings.value("gemini_api_key", "")
        api_key, ok = QInputDialog.getText(
            self, 
            "ផ្លាស់ប្តូរ Gemini API Key / Change API Key", 
            "សូមបញ្ចូល Google Gemini API Key ថ្មីរបស់អ្នក៖\n(ទុកចំហរទទេដើម្បីលុប Key ចាស់ចេញ)",
            QLineEdit.Password,
            current_key
        )
        if ok:
            self.settings.setValue("gemini_api_key", api_key.strip())
            QMessageBox.information(self, "ជោគជ័យ / Success", "API Key ត្រូវបានកែប្រែដោយជោគជ័យ! / API Key has been updated!")

    def process_ocr_from_file(self, file_name):
        from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox
        api_key = self.settings.value("gemini_api_key", "")
        if not api_key:
            api_key, ok = QInputDialog.getText(
                self, 
                "Gemini API Key Required", 
                "សូមបញ្ចូល Google Gemini API Key របស់អ្នក៖\n(អាចយកដោយឥតគិតថ្លៃពី aistudio.google.com/app/apikey)",
                QLineEdit.Password
            )
            if ok and api_key.strip():
                api_key = api_key.strip()
                self.settings.setValue("gemini_api_key", api_key)
            else:
                return
        
        dialog = ImageCropDialog(file_name, self)
        if dialog.exec_():
            final_image_path = dialog.get_cropped_image()
            
            self.btn_ai_ocr.setText("កំពុងទាញអត្ថបទ... / Processing...")
            self.btn_ai_ocr.setEnabled(False)
            
            selected_model = self.cb_ai_model.currentText()
            self.ocr_worker = OCRWorker(final_image_path, api_key, selected_model)
            self.ocr_worker.finished_signal.connect(self.on_ocr_success)
            self.ocr_worker.error_signal.connect(self.on_ocr_error)
            self.ocr_worker.start()

    def extract_text_from_image(self):
        from PyQt5.QtWidgets import QFileDialog, QDialog
        from PyQt5.QtCore import QSettings
        import os
        settings = QSettings("PhotoPrintApp", "Settings")
        last_dir = settings.value("last_open_dir", "")
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "ជ្រើសរើសរូបភាព ឬ PDF / Select Image or PDF",
            last_dir,
            "Images and PDF (*.png *.jpg *.jpeg *.bmp *.pdf)"
        )
        if file_name:
            settings.setValue("last_open_dir", os.path.dirname(file_name))
            if file_name.lower().endswith('.pdf'):
                dialog = PdfImportDialog(file_name, self)
                if dialog.exec_() == QDialog.Accepted and dialog.temp_image_path:
                    self.process_ocr_from_file(dialog.temp_image_path)
            else:
                self.process_ocr_from_file(file_name)

    def on_ocr_success(self, text):
        self.btn_ai_ocr.setText("ទាញអត្ថបទពីរូបភាព (AI) / Extract Text from Image")
        self.btn_ai_ocr.setEnabled(True)
        # Append or replace text. Let's append if there is already text, else replace.
        current_text = self.txt_banner.toPlainText().strip()
        if current_text:
            self.txt_banner.setText(current_text + "\n" + text.strip())
        else:
            self.txt_banner.setText(text.strip())

    def on_ocr_error(self, error_msg):
        from PyQt5.QtWidgets import QMessageBox
        self.btn_ai_ocr.setText("ទាញអត្ថបទពីរូបភាព (AI) / Extract Text from Image")
        self.btn_ai_ocr.setEnabled(True)
        
        if "API_KEY_INVALID" in error_msg or "403" in error_msg or "400" in error_msg:
            # Clear invalid key
            self.settings.remove("gemini_api_key")
            QMessageBox.critical(self, "API Key Error", "API Key មិនត្រឹមត្រូវ ឬមានបញ្ហា។ សូមសាកល្បងម្ដងទៀត។\n\n" + error_msg)
        else:
            QMessageBox.critical(self, "Error", f"មានបញ្ហាក្នុងការទាញអត្ថបទ៖\n{error_msg}")


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
                from PyQt5.QtGui import QTextDocument
                lines = self.text_preview.text.split('\n')
                
                for i, line in enumerate(lines):
                    if i >= len(self.text_preview.lines_data): break
                    line_data = self.text_preview.lines_data[i]
                    rect_mm = line_data['rect']
                    rect_px = QRectF(rect_mm.x() * scale, rect_mm.y() * scale, rect_mm.width() * scale, rect_mm.height() * scale)
                    
                    bg_color = line_data.get('bg_color', QColor(Qt.transparent))
                    if bg_color.alpha() > 0:
                        painter.fillRect(rect_px, bg_color)
                        
                    f_kh = line_data.get('font_kh', self.text_preview.font_family_kh)
                    f_en = line_data.get('font_en', self.text_preview.font_family_en)
                    is_b = line_data.get('bold', False)
                    is_i = line_data.get('italic', False)
                    is_u = line_data.get('underline', False)
                    l_color = line_data.get('color', self.text_color)
                    
                    doc = QTextDocument()
                    doc.setDocumentMargin(0)
                    html = build_mixed_html(line, f_kh, f_en, l_color, None, is_b, is_i, is_u, Qt.AlignLeft, 100)
                    doc.setHtml(html)
                    
                    base_rect = doc.documentLayout().documentSize()
                    
                    painter.save()
                    painter.translate(rect_px.x(), rect_px.y())
                    sx = rect_px.width() / base_rect.width() if base_rect.width() > 0 else 1
                    sy = rect_px.height() / base_rect.height() if base_rect.height() > 0 else 1
                    painter.scale(sx, sy)
                    doc.drawContents(painter)
                    painter.restore()
            else:
                m = self.sb_t_margin.value()
                m_px = m * scale
                rect = QRectF(m_px, m_px, (paper_w - 2*m) * scale, (paper_h - 2*m) * scale)
                
                from PyQt5.QtGui import QTextDocument
                doc = QTextDocument()
                doc.setDocumentMargin(0)
                
                if hasattr(self.text_preview, 'text_bg_color') and self.text_preview.text_bg_color.alpha() > 0:
                    painter.fillRect(rect, self.text_preview.text_bg_color)
                
                if self.chk_auto_fit.isChecked():
                    min_size = 1
                    max_size = 5000
                    best_size = min_size
                    
                    while min_size <= max_size:
                        mid_size = (min_size + max_size) // 2
                        html = build_mixed_html(self.text_preview.text, self.text_preview.font_family_kh, self.text_preview.font_family_en, self.text_preview.text_color, None, self.text_preview.font_bold, self.text_preview.font_italic, self.text_preview.font_underline, self.text_align, mid_size)
                        doc.setHtml(html)
                        doc.setTextWidth(rect.width())
                        
                        if doc.size().height() <= rect.height():
                            best_size = mid_size
                            min_size = mid_size + 1
                        else:
                            max_size = mid_size - 1
                    html = build_mixed_html(self.text_preview.text, self.text_preview.font_family_kh, self.text_preview.font_family_en, self.text_preview.text_color, None, self.text_preview.font_bold, self.text_preview.font_italic, self.text_preview.font_underline, self.text_align, best_size)
                    doc.setHtml(html)
                    doc.setTextWidth(rect.width())
                else:
                    pt_to_mm = 25.4 / 72.0
                    size_mm = self.text_preview.base_font_size * pt_to_mm
                    size_px = size_mm * scale
                    html = build_mixed_html(self.text_preview.text, self.text_preview.font_family_kh, self.text_preview.font_family_en, self.text_preview.text_color, None, self.text_preview.font_bold, self.text_preview.font_italic, self.text_preview.font_underline, self.text_align, int(max(1, size_px)))
                    doc.setHtml(html)
                    doc.setTextWidth(rect.width())
                    
                painter.save()
                painter.translate(rect.topLeft())
                doc.drawContents(painter)
                painter.restore()
            
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

    def go_to_previous_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.stacked_widget.setCurrentIndex(self.current_page_index)
            self.update_pagination_ui()

    def go_to_next_page(self):
        if self.current_page_index < len(self.preview_canvases) - 1:
            self.current_page_index += 1
            self.stacked_widget.setCurrentIndex(self.current_page_index)
            self.update_pagination_ui()

    def update_pagination_ui(self):
        total_pages = len(self.preview_canvases)
        if total_pages <= 1:
            self.pagination_widget.setVisible(False)
        else:
            self.pagination_widget.setVisible(True)
            self.lbl_page_info.setText(f"ទំព័រ / Page: {self.current_page_index + 1} / {total_pages}")
            self.btn_prev_page.setEnabled(self.current_page_index > 0)
            self.btn_next_page.setEnabled(self.current_page_index < total_pages - 1)

    def align_selected_left(self):
        for c in self.preview_canvases: c.align_left()
    def align_selected_top(self):
        for c in self.preview_canvases: c.align_top()
    def align_selected_right(self):
        for c in self.preview_canvases: c.align_right()
    def align_selected_bottom(self):
        for c in self.preview_canvases: c.align_bottom()
    def distribute_horizontally(self):
        for c in self.preview_canvases: c.distribute_horizontally()
    def distribute_vertically(self):
        for c in self.preview_canvases: c.distribute_vertically()

    def keyPressEvent(self, event):
        idx = self.tabs.currentIndex()
        if event.key() == Qt.Key_Delete:
            if idx == 0:
                self.clear_selected_image()
            elif idx == 2 and hasattr(self, 'id_preview'):
                for p in self.id_preview.photo_positions:
                    if p.get('selected', False):
                        p['image_pixmap'] = None
                        p['scale'] = 1.0
                        p['pan_x'] = 0.0
                        p['pan_y'] = 0.0
                self.id_preview.update()
        elif event.key() == Qt.Key_R:
            if idx == 0:
                for c in self.preview_canvases: c.rotate_selected_photos()
            elif idx == 2 and hasattr(self, 'id_preview'):
                self.id_preview.rotate_selected_photos()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            if event.modifiers() & Qt.ControlModifier:
                # ប្រើ Ctrl + Arrow សម្រាប់រំកិលសាច់រូបភាព (Pan inside Cover mode)
                step = 20 if (event.modifiers() & Qt.ShiftModifier) else 5
                if event.key() == Qt.Key_Up:
                    if idx == 0:
                        for c in self.preview_canvases: c.pan_selected_photos(0, -step)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.pan_selected_photos(0, -step)
                elif event.key() == Qt.Key_Down:
                    if idx == 0:
                        for c in self.preview_canvases: c.pan_selected_photos(0, step)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.pan_selected_photos(0, step)
                elif event.key() == Qt.Key_Left:
                    if idx == 0:
                        for c in self.preview_canvases: c.pan_selected_photos(-step, 0)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.pan_selected_photos(-step, 0)
                elif event.key() == Qt.Key_Right:
                    if idx == 0:
                        for c in self.preview_canvases: c.pan_selected_photos(step, 0)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.pan_selected_photos(step, 0)
            else:
                # ប្រើ Arrow ធម្មតា សម្រាប់រំកិលប្រអប់រូបភាពនៅលើក្រដាស
                step = 5.0 if (event.modifiers() & Qt.ShiftModifier) else 0.5
                if event.key() == Qt.Key_Up:
                    if idx == 0:
                        for c in self.preview_canvases: c.nudge_selected_photos(0, -step)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.nudge_selected_photos(0, -step)
                elif event.key() == Qt.Key_Down:
                    if idx == 0:
                        for c in self.preview_canvases: c.nudge_selected_photos(0, step)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.nudge_selected_photos(0, step)
                elif event.key() == Qt.Key_Left:
                    if idx == 0:
                        for c in self.preview_canvases: c.nudge_selected_photos(-step, 0)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.nudge_selected_photos(-step, 0)
                elif event.key() == Qt.Key_Right:
                    if idx == 0:
                        for c in self.preview_canvases: c.nudge_selected_photos(step, 0)
                    elif idx == 2 and hasattr(self, 'id_preview'):
                        self.id_preview.nudge_selected_photos(step, 0)
        else:
            super().keyPressEvent(event)
        
        if event.key() in (Qt.Key_Delete, Qt.Key_R, Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            if idx == 0 and not getattr(self.history_tab1, 'is_undoing_redoing', False):
                self.save_state_tab1()
            elif idx == 2 and not getattr(self.history_tab3, 'is_undoing_redoing', False):
                self.save_state_tab3()

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
        from PyQt5.QtCore import QSettings
        import os
        settings = QSettings("PhotoPrintApp", "Settings")
        last_dir = settings.value("last_open_dir", "")
        options = QFileDialog.Options()
        file_names, _ = QFileDialog.getOpenFileNames(self, "ជ្រើសរើសរូបភាព ឬ PDF / Choose Photos or PDF", last_dir, "Images and PDF (*.png *.jpg *.jpeg *.bmp *.pdf)", options=options)
        
        if not file_names:
            return
            
        settings.setValue("last_open_dir", os.path.dirname(file_names[0]))

        valid_files = []
        from PyQt5.QtWidgets import QDialog
        for f in file_names:
            if f.lower().endswith('.pdf'):
                dialog = PdfImportDialog(f, self)
                if dialog.exec_() == QDialog.Accepted and dialog.temp_image_path:
                    valid_files.append(dialog.temp_image_path)
            else:
                valid_files.append(f)

        if not valid_files:
            return

        self.loaded_images = valid_files
        self.btn_clear.setVisible(True)
        
        if len(valid_files) == 1:
            self.default_image_pixmap = QPixmap(valid_files[0])
            self.lbl_image_status.setText(f"<i>បានជ្រើសរើស: {valid_files[0].split('/')[-1]}</i>")
        else:
            self.default_image_pixmap = None
            self.lbl_image_status.setText(f"<i>បានជ្រើសរើសរូបភាពចំនួន {len(valid_files)} ឯកសារ</i>")
            
        self.calculate_layout()

    def clear_image(self):
        self.loaded_images = []
        self.default_image_pixmap = None
        self.lbl_image_status.setText("<i>មិនទាន់មានរូបភាព / No image loaded</i>")
        self.btn_clear.setVisible(False)
        self.calculate_layout()
            
    def toggle_auto_center(self):
        is_h = self.chk_center_h.isChecked()
        self.sb_margin_left.setEnabled(not is_h)
        self.sb_margin_right.setEnabled(not is_h)
        
        is_v = self.chk_center_v.isChecked()
        self.sb_margin_top.setEnabled(not is_v)
        self.sb_margin_bottom.setEnabled(not is_v)
        
        self.calculate_layout()
        
    def toggle_border(self):
        for canvas in self.preview_canvases:
            canvas.show_border = self.chk_show_border.isChecked()
            canvas.update()
            
    def on_border_slider_changed(self, value):
        self.sb_border_weight.blockSignals(True)
        self.sb_border_weight.setValue(value / 10.0)
        self.sb_border_weight.blockSignals(False)
        self.change_border_weight()

    def on_border_spinbox_changed(self, value):
        self.sl_border_weight.blockSignals(True)
        self.sl_border_weight.setValue(int(value * 10))
        self.sl_border_weight.blockSignals(False)
        self.change_border_weight()

    def change_border_weight(self):
        weight = self.sb_border_weight.value()
        for canvas in self.preview_canvases:
            canvas.border_weight = weight
            canvas.update()
        
    def toggle_manual_mode(self):
        is_manual = self.rb_manual_layout.isChecked()
        self.lbl_manual_tip.setVisible(is_manual)
        self.wg_align.setVisible(is_manual)
        for canvas in self.preview_canvases:
            canvas.is_manual = is_manual
        self.calculate_layout()
        
    def change_image_mode(self):
        is_cover = self.rb_img_cover.isChecked()
        self.lbl_cover_tip.setVisible(is_cover)
        self.update_image_adjustment_buttons()
        
        if not is_cover:
            for canvas in self.preview_canvases:
                for p in canvas.photo_positions:
                    p['selected'] = False
            
        mode = 'fill'
        if getattr(self, 'chk_enable_grid', None) and self.chk_enable_grid.isChecked() and getattr(self, 'rb_grid_original_size', None) and self.rb_grid_original_size.isChecked():
            mode = 'contain'
        else:
            if self.rb_img_fill.isChecked(): mode = 'fill'
            elif is_cover: mode = 'cover'
            elif self.rb_img_contain.isChecked(): mode = 'contain'
            
        for canvas in self.preview_canvases:
            canvas.image_mode = mode
            canvas.update()
        
    def update_image_adjustment_buttons(self):
        has_selection = any(p.get('selected', False) for canvas in self.preview_canvases for p in canvas.photo_positions)
        
        self.btn_change_selected_image.setEnabled(has_selection)
        
        has_default = hasattr(self, 'default_image_pixmap') and self.default_image_pixmap is not None and not self.default_image_pixmap.isNull()
        self.btn_reset_selected_image.setEnabled(has_selection and has_default)
        
        self.lbl_adj_tip.setVisible(not has_selection)

    def select_all_photos(self):
        for canvas in self.preview_canvases:
            for p in canvas.photo_positions:
                p['selected'] = True
            canvas.update()
        self.update_image_adjustment_buttons()
        
    def deselect_all_photos(self):
        for canvas in self.preview_canvases:
            for p in canvas.photo_positions:
                p['selected'] = False
            canvas.update()
        self.update_image_adjustment_buttons()
    
    def change_selected_image(self):
        from PyQt5.QtCore import QSettings
        import os
        settings = QSettings("PhotoPrintApp", "Settings")
        last_dir = settings.value("last_open_dir", "")
        options = QFileDialog.Options()
        file_names, _ = QFileDialog.getOpenFileNames(self, "ជ្រើសរើសរូបភាពថ្មី / Choose New Photos", last_dir, "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        if file_names:
            settings.setValue("last_open_dir", os.path.dirname(file_names[0]))
            selected_slots = [p for canvas in self.preview_canvases for p in canvas.photo_positions if p.get('selected', False)]
            for i, file_path in enumerate(file_names):
                if i < len(selected_slots):
                    new_pixmap = QPixmap(file_path)
                    if not new_pixmap.isNull():
                        selected_slots[i]['image_pixmap'] = new_pixmap
            for canvas in self.preview_canvases:
                canvas.update()
            self.update_image_adjustment_buttons()

    def reset_selected_image(self):
        if hasattr(self, 'default_image_pixmap') and self.default_image_pixmap and not self.default_image_pixmap.isNull():
            for canvas in self.preview_canvases:
                for p in canvas.photo_positions:
                    if p.get('selected', False):
                        p['image_pixmap'] = self.default_image_pixmap
                canvas.update()
            self.update_image_adjustment_buttons()
        else:
            self.clear_selected_image()

    def clear_selected_image(self):
        for canvas in self.preview_canvases:
            for p in canvas.photo_positions:
                if p.get('selected', False):
                    p['image_pixmap'] = None
                    p['scale'] = 1.0
                    p['pan_x'] = 0.0
                    p['pan_y'] = 0.0
            canvas.update()
        self.update_image_adjustment_buttons()



    def toggle_grid_mode(self):
        is_grid = self.chk_enable_grid.isChecked()
        self.sb_grid_cols.setEnabled(is_grid)
        self.sb_grid_rows.setEnabled(is_grid)
        self.rb_grid_same_size.setEnabled(is_grid)
        self.rb_grid_original_size.setEnabled(is_grid)
        
        self.cb_p_unit.setEnabled(not is_grid)
        self.sb_dpi.setEnabled(not is_grid)
        for g in self.size_groups:
            g['chk'].setEnabled(not is_grid)
            g['w'].setEnabled(not is_grid)
            g['h'].setEnabled(not is_grid)
            g['qty'].setEnabled(not is_grid)
            
        self.calculate_layout()

    def calculate_layout(self, *args):
        paper_w = self.sb_width.value()
        paper_h = self.sb_height.value()

        unit = self.cb_p_unit.currentText()
        current_dpi = self.sb_dpi.value()

        active_configs = []
        total_print_qty = 0
        # តម្លៃមធ្យមសម្រាប់ប្រើក្នុងការគណនាប្លង់ (Fallback values)
        photo_w, photo_h = 30.0, 40.0
        val_w, val_h = 3.0, 4.0
        margin_t = self.sb_margin_top.value()
        margin_b = self.sb_margin_bottom.value()
        margin_l = self.sb_margin_left.value()
        margin_r = self.sb_margin_right.value()
        
        gap = self.sb_gap.value()
        
        if getattr(self, 'chk_enable_grid', None) and self.chk_enable_grid.isChecked():
            cols = self.sb_grid_cols.value()
            rows = self.sb_grid_rows.value()
            is_orig = self.rb_grid_original_size.isChecked()
            
            if is_orig and hasattr(self, 'loaded_images') and self.loaded_images:
                avail_w = paper_w - (margin_l + margin_r) - (cols - 1) * gap
                avail_h = paper_h - (margin_t + margin_b) - (rows - 1) * gap
                
                cell_w = avail_w / cols if cols > 0 else 10.0
                cell_h = avail_h / rows if rows > 0 else 10.0

                if len(self.loaded_images) == 1:
                    active_configs.append({'w': cell_w, 'h': cell_h, 'qty': cols * rows, 'label': "Original"})
                    is_fill_single_page = True
                else:
                    active_configs.append({'w': cell_w, 'h': cell_h, 'qty': max(cols * rows, len(self.loaded_images)), 'label': "Original"})
            else:
                avail_w = paper_w - (margin_l + margin_r) - (cols - 1) * gap
                avail_h = paper_h - (margin_t + margin_b) - (rows - 1) * gap
                
                photo_w = avail_w / cols if cols > 0 else 10.0
                photo_h = avail_h / rows if rows > 0 else 10.0
                val_w, val_h = photo_w, photo_h
                
                qty = cols * rows
                active_configs.append({
                    'w': photo_w, 'h': photo_h, 
                    'qty': qty, 
                    'label': f"Grid {cols}x{rows}"
                })
                total_print_qty += qty
        else:
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
        
        avail_w = paper_w - (margin_l + margin_r)
        avail_h = paper_h - (margin_t + margin_b)
        
        # Prepare items_to_place
        items_to_place = []
        is_fill_single_page = False
        
        if self.rb_max_qty.isChecked() and len(active_configs) == 1:
            if hasattr(self, 'loaded_images') and self.loaded_images:
                if len(self.loaded_images) == 1:
                    active_configs[0]['qty'] = 1000
                    is_fill_single_page = True
                else:
                    active_configs[0]['qty'] = len(self.loaded_images)
            else:
                active_configs[0]['qty'] = 1000
                is_fill_single_page = True

        for config in active_configs:
            for _ in range(config['qty']):
                items_to_place.append(config)

        # Remove existing canvases
        while self.stacked_widget.count() > 0:
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()
        self.preview_canvases.clear()
        
        remaining_items = items_to_place
        page_index = 0
        total_placed_qty = 0
        
        while (remaining_items or page_index == 0):
            canvas = PreviewWidget()
            canvas.selectionChanged.connect(self.update_image_adjustment_buttons)
            canvas.stateChanged.connect(self.save_state_tab1)
            
            if getattr(self, 'chk_enable_grid', None) and self.chk_enable_grid.isChecked():
                canvas.grid_cols = self.sb_grid_cols.value()
                canvas.grid_rows = self.sb_grid_rows.value()
            else:
                canvas.grid_cols = 0
                canvas.grid_rows = 0
            
            canvas.paper_w = paper_w
            canvas.paper_h = paper_h
            canvas.photo_w = photo_w
            canvas.photo_h = photo_h
            canvas.size_label = f"{val_w:g}x{val_h:g} {unit}"
            
            canvas.margin_top = margin_t
            canvas.margin_bottom = margin_b
            canvas.margin_left = margin_l
            canvas.margin_right = margin_r
            canvas.offset_x = margin_l
            canvas.offset_y = margin_t
            canvas.gap = gap
            canvas.optimize_fit = self.chk_optimize_fit.isChecked()
            
            canvas.is_manual = self.rb_manual_layout.isChecked()
            
            mode = 'fill'
            if getattr(self, 'chk_enable_grid', None) and self.chk_enable_grid.isChecked() and getattr(self, 'rb_grid_original_size', None) and self.rb_grid_original_size.isChecked():
                mode = 'contain'
            else:
                if self.rb_img_cover.isChecked(): mode = 'cover'
                elif self.rb_img_contain.isChecked(): mode = 'contain'
            canvas.image_mode = mode
            
            canvas.show_border = self.chk_show_border.isChecked()
            
            if page_index == 0:
                remaining_items.sort(key=lambda x: max(x['w'], x['h']), reverse=True)
                
            remaining_items = canvas.generate_grid(remaining_items)
            
            total_placed_qty += len(canvas.photo_positions)
            
            if self.chk_center_h.isChecked():
                canvas.center_horizontally()
            if self.chk_center_v.isChecked():
                canvas.center_vertically()
                
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            container_layout.addWidget(canvas)
            
            self.stacked_widget.addWidget(container)
            self.preview_canvases.append(canvas)
            page_index += 1
            
            if is_fill_single_page:
                break
            if self.rb_manual_layout.isChecked():
                break

        # Assign images to slots
        if hasattr(self, 'loaded_images') and self.loaded_images:
            if len(self.loaded_images) == 1:
                pix = QPixmap(self.loaded_images[0])
                for canvas in self.preview_canvases:
                    for p in canvas.photo_positions:
                        p['image_pixmap'] = pix if not pix.isNull() else None
            else:
                img_idx = 0
                for canvas in self.preview_canvases:
                    for p in canvas.photo_positions:
                        if img_idx < len(self.loaded_images):
                            pix = QPixmap(self.loaded_images[img_idx])
                            p['image_pixmap'] = pix if not pix.isNull() else None
                            img_idx += 1
                        else:
                            p['image_pixmap'] = None

        if self.rb_max_qty.isChecked() and len(active_configs) == 1:
            if is_fill_single_page:
                total_print_qty = total_placed_qty
            else:
                total_print_qty = len(self.loaded_images) if hasattr(self, 'loaded_images') and self.loaded_images else total_placed_qty
        else:
            total_print_qty = total_placed_qty
        
        ori_text = "បញ្ឈរ (Portrait)" if self.rb_port.isChecked() else "ផ្តេក (Landscape)"
        self.lbl_status.setText(f"<b>ចំនួនសរុប: {total_print_qty} រូបភាព ({ori_text}) [ទំព័រ: {len(self.preview_canvases)}]</b>")
        
        self.update_image_adjustment_buttons()
        
        self.current_page_index = 0
        if self.stacked_widget.count() > 0:
            self.stacked_widget.setCurrentIndex(0)
        self.update_pagination_ui()
        if not getattr(self.history_tab1, 'is_undoing_redoing', False):
            self.save_state_tab1()

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
        
        for i, canvas in enumerate(self.preview_canvases):
            if i > 0:
                pdf_writer.newPage()
                
            painter.fillRect(0, 0, int(paper_w * scale), int(paper_h * scale), Qt.white)
            
            for pos in canvas.photo_positions:
                p_w, p_h = pos.get('w', canvas.photo_w), pos.get('h', canvas.photo_h)
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
                        
                    if canvas.optimize_fit and manual_angle == 0:
                        img_w, img_h = current_pixmap.width(), current_pixmap.height()
                        if img_w != img_h and cell_w != cell_h:
                            if (img_w > img_h) != (cell_w > cell_h):
                                transform = QTransform().rotate(90)
                                current_pixmap = current_pixmap.transformed(transform, Qt.SmoothTransformation)

                    if canvas.image_mode == 'fill':
                        painter.drawPixmap(target_rect, current_pixmap)
                    elif canvas.image_mode == 'contain':
                        pre_scaled_contain = current_pixmap.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        if pre_scaled_contain and not pre_scaled_contain.isNull():
                            x_offset = (target_rect.width() - pre_scaled_contain.width()) // 2
                            y_offset = (target_rect.height() - pre_scaled_contain.height()) // 2
                            painter.drawPixmap(target_rect.x() + x_offset, target_rect.y() + y_offset, pre_scaled_contain)
                    elif canvas.image_mode == 'cover':
                        pre_scaled_cover = current_pixmap.scaled(tw, th, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                        if pre_scaled_cover and not pre_scaled_cover.isNull():
                            img_scale = pos.get('scale', 1.0)
                            pan_x = pos.get('pan_x', 0.0)
                            pan_y = pos.get('pan_y', 0.0)
                            
                            screen_scale = canvas.paper_width_px / canvas.paper_w if canvas.paper_w > 0 else 1
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

                    if getattr(canvas, 'show_border', False):
                        from PyQt5.QtGui import QPen, QColor
                        border_pt = getattr(canvas, 'border_weight', 0.50)
                        border_px = border_pt * (25.4 / 72.0) * scale
                        painter.setPen(QPen(QColor(0, 0, 0), max(0.0, border_px), Qt.SolidLine))
                        painter.drawRect(target_rect)
            
        painter.end()
        if show_msg:
            QMessageBox.information(self, "ជោគជ័យ / Success", "ឯកសារ PDF ត្រូវបានរក្សាទុកដោយជោគជ័យ! / PDF saved successfully!")
        return file_name
    def initIDCardUI(self, parent_widget):
        from PyQt5.QtWidgets import QScrollArea
        layout = QHBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Panel (Controls)
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)
        
        title_lbl = QLabel("<b>បោះពុម្ពកាតសម្គាល់ខ្លួន / ID Card Printer</b>")
        title_lbl.setFont(QFont("Khmer OS Battambang", 12))
        left_layout.addWidget(title_lbl)
        
        gb_id = QGroupBox("១. បញ្ចូលរូបកាត / Load ID Card")
        gb_id_layout = QVBoxLayout()
        
        self.btn_load_front = QPushButton("បញ្ចូលរូបកាតមុខ / Load Front")
        self.btn_load_front.setStyleSheet("background-color: #0084c7; color: white; padding: 10px; border-radius: 5px;")
        self.btn_load_front.clicked.connect(self.load_id_front)
        
        self.lbl_info_front = QLabel("")
        self.lbl_info_front.setStyleSheet("color: gray; font-size: 11px;")
        
        self.btn_load_back = QPushButton("បញ្ចូលរូបកាតក្រោយ / Load Back")
        self.btn_load_back.setStyleSheet("background-color: #0084c7; color: white; padding: 10px; border-radius: 5px;")
        self.btn_load_back.clicked.connect(self.load_id_back)
        
        self.lbl_info_back = QLabel("")
        self.lbl_info_back.setStyleSheet("color: gray; font-size: 11px;")
        
        self.btn_swap_id = QPushButton("ឆ្លាស់ទីតាំងកាត / Swap Cards")
        self.btn_swap_id.setStyleSheet("background-color: #f59e0b; color: white; padding: 10px; border-radius: 5px;")
        self.btn_swap_id.clicked.connect(self.swap_id_cards)
        
        self.btn_clear_id = QPushButton("លុបរូបកាត / Clear ID Cards")
        self.btn_clear_id.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px; border-radius: 5px;")
        self.btn_clear_id.clicked.connect(self.clear_id_cards)
        
        self.cb_id_filter = QComboBox()
        self.cb_id_filter.addItems(["រូបដើម / Original", "ពណ៌វេទមន្ត / Magic Color", "ពណ៌ប្រផេះ / Grayscale", "ស-ខ្មៅ / B&W Scan"])
        self.cb_id_filter.currentIndexChanged.connect(self.apply_id_filters)
        
        self.chk_id_ai = QCheckBox("ប្រើប្រាស់ AI បង្កើនភាពច្បាស់ (AI Enhance)")
        self.chk_id_ai.setStyleSheet("color: #d946ef; font-weight: bold;")
        self.chk_id_ai.stateChanged.connect(self.apply_id_filters)
        
        self.chk_id_rounded = QCheckBox("✂️ កាត់ស៊ុមគែមកោងកាត (Rounded Corners)")
        self.chk_id_rounded.setChecked(True)
        self.chk_id_rounded.setStyleSheet("color: #0ea5e9; font-weight: bold;")
        self.chk_id_rounded.stateChanged.connect(self.update_id_preview)
        
        gb_id_layout.addWidget(self.btn_load_front)
        gb_id_layout.addWidget(self.lbl_info_front)
        gb_id_layout.addWidget(self.btn_load_back)
        gb_id_layout.addWidget(self.lbl_info_back)
        gb_id_layout.addWidget(self.btn_swap_id)
        gb_id_layout.addWidget(QLabel("ប្រភេទពណ៌ / Color Filter:"))
        gb_id_layout.addWidget(self.cb_id_filter)
        gb_id_layout.addWidget(self.chk_id_ai)
        gb_id_layout.addWidget(self.chk_id_rounded)
        gb_id_layout.addWidget(self.btn_clear_id)
        gb_id.setLayout(gb_id_layout)
        left_layout.addWidget(gb_id)
        
        gb_paper = QGroupBox("២. ទំហំក្រដាស / Paper Size")
        gb_paper_layout = QVBoxLayout()
        self.cb_id_paper = QComboBox()
        self.cb_id_paper.addItems(["A4 (210 x 297 mm)", "A5 (148 x 210 mm)", "ក្រដាសរូបថត (10x15 cm)"])
        self.cb_id_paper.currentIndexChanged.connect(self.update_id_preview)
        gb_paper_layout.addWidget(self.cb_id_paper)
        gb_paper.setLayout(gb_paper_layout)
        left_layout.addWidget(gb_paper)
        
        gb_size = QGroupBox("៣. ទំហំកាត / Card Size (mm)")
        gb_size_layout = QHBoxLayout()
        self.sb_id_w = QDoubleSpinBox()
        self.sb_id_w.setRange(10, 300)
        self.sb_id_w.setValue(85.6)
        self.sb_id_w.setSuffix(" mm")
        
        self.sb_id_h = QDoubleSpinBox()
        self.sb_id_h.setRange(10, 300)
        self.sb_id_h.setValue(54.0)
        self.sb_id_h.setSuffix(" mm")

        self.btn_id_ratio_lock = QPushButton("🔒")
        self.btn_id_ratio_lock.setCheckable(True)
        self.btn_id_ratio_lock.setChecked(True)
        self.btn_id_ratio_lock.setFixedWidth(30)
        self.btn_id_ratio_lock.setToolTip("ចាក់សោរទំហំ (Lock Aspect Ratio)")
        
        self.id_ratio = 85.6 / 54.0
        
        def toggle_ratio(checked):
            if checked:
                self.btn_id_ratio_lock.setText("🔒")
                if self.sb_id_h.value() > 0:
                    self.id_ratio = self.sb_id_w.value() / self.sb_id_h.value()
            else:
                self.btn_id_ratio_lock.setText("🔓")
                
        def w_changed(val):
            if self.btn_id_ratio_lock.isChecked():
                self.sb_id_h.blockSignals(True)
                self.sb_id_h.setValue(val / self.id_ratio)
                self.sb_id_h.blockSignals(False)
            self.update_id_preview()
            
        def h_changed(val):
            if self.btn_id_ratio_lock.isChecked():
                self.sb_id_w.blockSignals(True)
                self.sb_id_w.setValue(val * self.id_ratio)
                self.sb_id_w.blockSignals(False)
            self.update_id_preview()
            
        self.btn_id_ratio_lock.toggled.connect(toggle_ratio)
        self.sb_id_w.valueChanged.connect(w_changed)
        self.sb_id_h.valueChanged.connect(h_changed)
        
        gb_size_layout.addWidget(QLabel("ទទឹង (W):"))
        gb_size_layout.addWidget(self.sb_id_w)
        gb_size_layout.addWidget(self.btn_id_ratio_lock)
        gb_size_layout.addWidget(QLabel("កម្ពស់ (H):"))
        gb_size_layout.addWidget(self.sb_id_h)
        gb_size.setLayout(gb_size_layout)
        left_layout.addWidget(gb_size)
        
        gb_qty = QGroupBox("៤. ចំនួនបោះពុម្ព / Print Quantity")
        gb_qty_layout = QVBoxLayout()
        self.sb_id_qty = QSpinBox()
        self.sb_id_qty.setRange(1, 50)
        self.sb_id_qty.setValue(1)
        self.sb_id_qty.valueChanged.connect(self.update_id_preview)
        gb_qty_layout.addWidget(self.sb_id_qty)
        gb_qty.setLayout(gb_qty_layout)
        left_layout.addWidget(gb_qty)
        
        gb_margin = QGroupBox("៥. តម្រឹមកាត / Alignment & Margin")
        gb_margin_layout = QGridLayout()
        
        btn_center_h = QPushButton("កណ្តាល (ផ្ដេក)")
        btn_center_h.clicked.connect(self.id_center_h)
        btn_center_v = QPushButton("កណ្តាល (បញ្ឈរ)")
        btn_center_v.clicked.connect(self.id_center_v)
        
        btn_align_left = QPushButton("គែមឆ្វេង (Left)")
        btn_align_left.clicked.connect(self.id_align_left)
        btn_align_right = QPushButton("គែមស្តាំ (Right)")
        btn_align_right.clicked.connect(self.id_align_right)
        
        btn_align_top = QPushButton("គែមលើ (Top)")
        btn_align_top.clicked.connect(self.id_align_top)
        btn_align_bottom = QPushButton("គែមក្រោម (Bottom)")
        btn_align_bottom.clicked.connect(self.id_align_bottom)
        
        gb_margin_layout.addWidget(btn_center_h, 0, 0)
        gb_margin_layout.addWidget(btn_center_v, 0, 1)
        gb_margin_layout.addWidget(btn_align_left, 1, 0)
        gb_margin_layout.addWidget(btn_align_right, 1, 1)
        gb_margin_layout.addWidget(btn_align_top, 2, 0)
        gb_margin_layout.addWidget(btn_align_bottom, 2, 1)
        
        self.sb_id_margin_top = QDoubleSpinBox()
        self.sb_id_margin_bottom = QDoubleSpinBox()
        self.sb_id_margin_left = QDoubleSpinBox()
        self.sb_id_margin_right = QDoubleSpinBox()
        
        for sb in [self.sb_id_margin_top, self.sb_id_margin_bottom, self.sb_id_margin_left, self.sb_id_margin_right]:
            sb.setRange(0, 500)
            sb.setValue(10)
            sb.valueChanged.connect(self.update_id_preview)
            
        gb_margin_layout.addWidget(QLabel("គែមលើ (Top):"), 3, 0)
        gb_margin_layout.addWidget(self.sb_id_margin_top, 3, 1)
        gb_margin_layout.addWidget(QLabel("គែមក្រោម (Bottom):"), 4, 0)
        gb_margin_layout.addWidget(self.sb_id_margin_bottom, 4, 1)
        gb_margin_layout.addWidget(QLabel("គែមឆ្វេង (Left):"), 5, 0)
        gb_margin_layout.addWidget(self.sb_id_margin_left, 5, 1)
        gb_margin_layout.addWidget(QLabel("គែមស្តាំ (Right):"), 6, 0)
        gb_margin_layout.addWidget(self.sb_id_margin_right, 6, 1)
        
        gb_margin.setLayout(gb_margin_layout)
        left_layout.addWidget(gb_margin)
        
        layout.addWidget(left_panel)
        
        # Center Panel (Preview)
        self.id_preview = PreviewWidget()
        self.id_preview.is_manual = True
        self.id_preview.photo_positions = []
        self.id_preview.itemDoubleClicked.connect(self.on_id_preview_double_clicked)
        self.id_preview.stateChanged.connect(self.save_state_tab3)
        
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        h_mid_top = QHBoxLayout()
        mid_title = QLabel("<b>ទិដ្ឋភាពបង្ហាញជាក់ស្តែង / LIVE ID PREVIEW</b>")
        mid_title.setAlignment(Qt.AlignCenter)
        mid_title.setFont(QFont("Khmer OS Battambang", 11))
        h_mid_top.addWidget(mid_title)
        self.btn_undo3 = QPushButton("↶ Undo (Ctrl+Z)")
        self.btn_redo3 = QPushButton("↷ Redo (Ctrl+Y)")
        self.btn_undo3.clicked.connect(self.undo_action)
        self.btn_redo3.clicked.connect(self.redo_action)
        self.btn_undo3.setEnabled(False)
        self.btn_redo3.setEnabled(False)
        h_mid_top.addWidget(self.btn_undo3)
        h_mid_top.addWidget(self.btn_redo3)
        mid_layout.addLayout(h_mid_top)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: #dbe2e9; border: none; }")
        scroll_area.setWidget(self.id_preview)
        mid_layout.addWidget(scroll_area)
        layout.addWidget(mid_panel, 1)
        
        # Right Panel
        right_panel = QWidget()
        right_panel.setFixedWidth(200)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignTop)
        
        btn_print_pdf = QPushButton("រក្សាទុកជា PDF")
        btn_print_pdf.setStyleSheet("background-color: #2b52ff; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_print_pdf.clicked.connect(self.save_id_pdf)
        
        btn_print_foxit = QPushButton("បញ្ចូនទៅ Foxit PDF")
        btn_print_foxit.setStyleSheet("background-color: #5850ec; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_print_foxit.clicked.connect(self.print_id_foxit)
        
        right_layout.addWidget(btn_print_pdf)
        right_layout.addWidget(btn_print_foxit)
        
        layout.addWidget(right_panel)
        
        self.id_front_cv_img = None
        self.id_back_cv_img = None
        self.id_front_pixmap = None
        self.id_back_pixmap = None
        self.update_id_preview()

    def id_center_h(self):
        self.id_preview.center_horizontally()
        self.sb_id_margin_left.blockSignals(True)
        self.sb_id_margin_left.setValue(self.id_preview.margin_left)
        self.sb_id_margin_left.blockSignals(False)
        self.sb_id_margin_right.blockSignals(True)
        self.sb_id_margin_right.setValue(self.id_preview.margin_right)
        self.sb_id_margin_right.blockSignals(False)

    def id_center_v(self):
        self.id_preview.center_vertically()
        self.sb_id_margin_top.blockSignals(True)
        self.sb_id_margin_top.setValue(self.id_preview.margin_top)
        self.sb_id_margin_top.blockSignals(False)
        self.sb_id_margin_bottom.blockSignals(True)
        self.sb_id_margin_bottom.setValue(self.id_preview.margin_bottom)
        self.sb_id_margin_bottom.blockSignals(False)

    def id_align_left(self):
        self.id_preview.align_left()
        self.sb_id_margin_left.blockSignals(True)
        self.sb_id_margin_left.setValue(self.id_preview.margin_left)
        self.sb_id_margin_left.blockSignals(False)

    def id_align_right(self):
        self.id_preview.align_right()
        self.sb_id_margin_right.blockSignals(True)
        self.sb_id_margin_right.setValue(self.id_preview.margin_right)
        self.sb_id_margin_right.blockSignals(False)

    def id_align_top(self):
        self.id_preview.align_top()
        self.sb_id_margin_top.blockSignals(True)
        self.sb_id_margin_top.setValue(self.id_preview.margin_top)
        self.sb_id_margin_top.blockSignals(False)

    def id_align_bottom(self):
        self.id_preview.align_bottom()
        self.sb_id_margin_bottom.blockSignals(True)
        self.sb_id_margin_bottom.setValue(self.id_preview.margin_bottom)
        self.sb_id_margin_bottom.blockSignals(False)

    def apply_id_filters(self, *args):
        idx = self.cb_id_filter.currentIndex()
        do_ai = self.chk_id_ai.isChecked()
        
        def process_img(img):
            if img is None: return None
            
            base_img = img.copy()
            
            if do_ai:
                from PyQt5.QtWidgets import QApplication
                from PyQt5.QtCore import Qt
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    import os, urllib.request
                    from cv2 import dnn_superres
                    model_path = "FSRCNN_x4.pb"
                    if not os.path.exists(model_path):
                        url = "https://github.com/Saafke/FSRCNN_Tensorflow/raw/master/models/FSRCNN_x4.pb"
                        urllib.request.urlretrieve(url, model_path)
                    
                    sr = dnn_superres.DnnSuperResImpl_create()
                    sr.readModel(model_path)
                    sr.setModel("fsrcnn", 4)
                    base_img = sr.upsample(base_img)
                    
                    # Apply strong but natural Sharpening (Unsharp Mask)
                    gaussian = cv2.GaussianBlur(base_img, (0, 0), 3.0)
                    base_img = cv2.addWeighted(base_img, 1.8, gaussian, -0.8, 0)
                except Exception as e:
                    print("AI Super Resolution Error:", e)
                finally:
                    QApplication.restoreOverrideCursor()

            if idx == 0:
                res = base_img
            elif idx == 1:
                hsv = cv2.cvtColor(base_img, cv2.COLOR_RGB2HSV).astype(np.float32)
                hsv[:, :, 1] *= 1.5
                hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
                hsv[:, :, 2] *= 1.2
                hsv[:, :, 2] = np.clip(hsv[:, :, 2], 0, 255)
                res = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
            elif idx == 2:
                gray = cv2.cvtColor(base_img, cv2.COLOR_RGB2GRAY)
                # បង្កើនពន្លឺ និងកម្រិតភាពច្បាស់បន្តិចដើម្បីឱ្យផ្ទៃខាងក្រោយភ្លឺជាងមុន
                gray = cv2.convertScaleAbs(gray, alpha=1.1, beta=5)
                res = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            elif idx == 3:
                gray = cv2.cvtColor(base_img, cv2.COLOR_RGB2GRAY)
                
                # Fast Background Estimation (Mimics CamScanner)
                h_img, w_img = gray.shape
                scale = 150.0 / w_img
                if scale < 1.0:
                    small_gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
                else:
                    small_gray = gray.copy()
                
                # Use Morphological Close to erase text/dark lines from the background map
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                bg_small = cv2.morphologyEx(small_gray, cv2.MORPH_CLOSE, kernel)
                bg_small = cv2.GaussianBlur(bg_small, (11, 11), 0)
                
                # Resize background map back to original size
                bg = cv2.resize(bg_small, (w_img, h_img))
                
                # Divide image by background to make paper purely white while keeping photo details
                gray_f = gray.astype(np.float32)
                bg_f = bg.astype(np.float32) + 1 # Avoid division by zero
                scan = cv2.divide(gray_f, bg_f, scale=255.0)
                scan = np.clip(scan, 0, 255).astype(np.uint8)
                # 1. Sharpen to make details and text edges very clear
                gaussian = cv2.GaussianBlur(scan, (0, 0), 2.0)
                scan = cv2.addWeighted(scan, 1.8, gaussian, -0.8, 0)
                
                # 2. Darken midtones (gamma correction) to make text bolder (ដិត) 
                # without destroying the face highlights
                gamma = 0.65
                invGamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                scan = cv2.LUT(scan, table)
                
                # 3. Gentle contrast boost to ensure background is white and text is dark
                scan = cv2.convertScaleAbs(scan, alpha=1.2, beta=-10)
                
                res = cv2.cvtColor(scan, cv2.COLOR_GRAY2RGB)
            else:
                res = base_img
                
            h, w, ch = res.shape
            from PyQt5.QtGui import QImage, QPixmap
            qimg = QImage(res.data, w, h, ch * w, QImage.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())

        self.id_front_pixmap = process_img(self.id_front_cv_img)
        self.id_back_pixmap = process_img(self.id_back_cv_img)
        
        def update_lbl(lbl, orig_img, final_pixmap):
            if orig_img is not None and final_pixmap is not None:
                orig_h, orig_w = orig_img.shape[:2]
                fin_w, fin_h = final_pixmap.width(), final_pixmap.height()
                if orig_w == fin_w and orig_h == fin_h:
                    lbl.setText(f"ទំហំដើម: {orig_w} x {orig_h} px")
                else:
                    lbl.setText(f"ទំហំដើម: {orig_w} x {orig_h} px | ដំឡើង: {fin_w} x {fin_h} px")
            else:
                lbl.setText("")

        update_lbl(self.lbl_info_front, self.id_front_cv_img, self.id_front_pixmap)
        update_lbl(self.lbl_info_back, self.id_back_cv_img, self.id_back_pixmap)
        
        self.update_id_preview()

    def load_id_front(self):
        from PyQt5.QtWidgets import QDialog
        from PyQt5.QtCore import QSettings
        import os
        settings = QSettings("PhotoPrintApp", "Settings")
        last_dir = settings.value("last_open_dir", "")
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូបកាតមុខ ឬ PDF / Select Front ID or PDF", last_dir, "Images and PDF (*.png *.jpg *.jpeg *.bmp *.pdf)", options=options)
        if file_name:
            settings.setValue("last_open_dir", os.path.dirname(file_name))
            if file_name.lower().endswith('.pdf'):
                dialog = PdfImportDialog(file_name, self)
                if dialog.exec_() == QDialog.Accepted and dialog.temp_image_path:
                    file_name = dialog.temp_image_path
                else:
                    return
            
            self.id_front_file_name = file_name
            self.id_front_points = None
            dialog = PerspectiveCropDialog(file_name, self)
            if dialog.exec_() == QDialog.Accepted and dialog.cropped_pixmap:
                self.id_front_cv_img = dialog.cropped_cv_img
                self.id_front_points = getattr(dialog, 'final_points', None)
            else:
                img = cv2.imdecode(np.fromfile(file_name, dtype=np.uint8), cv2.IMREAD_COLOR)
                self.id_front_cv_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img is not None else None
            self.apply_id_filters()

    def load_id_back(self):
        from PyQt5.QtWidgets import QDialog
        from PyQt5.QtCore import QSettings
        import os
        settings = QSettings("PhotoPrintApp", "Settings")
        last_dir = settings.value("last_open_dir", "")
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូបកាតក្រោយ ឬ PDF / Select Back ID or PDF", last_dir, "Images and PDF (*.png *.jpg *.jpeg *.bmp *.pdf)", options=options)
        if file_name:
            settings.setValue("last_open_dir", os.path.dirname(file_name))
            if file_name.lower().endswith('.pdf'):
                dialog = PdfImportDialog(file_name, self)
                if dialog.exec_() == QDialog.Accepted and dialog.temp_image_path:
                    file_name = dialog.temp_image_path
                else:
                    return
                    
            self.id_back_file_name = file_name
            self.id_back_points = None
            dialog = PerspectiveCropDialog(file_name, self)
            if dialog.exec_() == QDialog.Accepted and dialog.cropped_pixmap:
                self.id_back_cv_img = dialog.cropped_cv_img
                self.id_back_points = getattr(dialog, 'final_points', None)
            else:
                img = cv2.imdecode(np.fromfile(file_name, dtype=np.uint8), cv2.IMREAD_COLOR)
                self.id_back_cv_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img is not None else None
            self.apply_id_filters()
            
    def swap_id_cards(self):
        self.id_front_cv_img, self.id_back_cv_img = self.id_back_cv_img, self.id_front_cv_img
        
        f_name = getattr(self, 'id_front_file_name', None)
        b_name = getattr(self, 'id_back_file_name', None)
        self.id_front_file_name, self.id_back_file_name = b_name, f_name
        
        f_pts = getattr(self, 'id_front_points', None)
        b_pts = getattr(self, 'id_back_points', None)
        self.id_front_points, self.id_back_points = b_pts, f_pts
        
        self.apply_id_filters()
            
    def clear_id_cards(self):
        self.id_front_cv_img = None
        self.id_back_cv_img = None
        self.id_front_pixmap = None
        self.id_back_pixmap = None
        self.id_front_file_name = None
        self.id_back_file_name = None
        self.id_front_points = None
        self.id_back_points = None
        self.update_id_preview()

    def on_id_preview_double_clicked(self, pos):
        label = pos.get('label', '')
        from PyQt5.QtWidgets import QDialog
        if label == 'Front' and hasattr(self, 'id_front_file_name') and self.id_front_file_name:
            dialog = PerspectiveCropDialog(self.id_front_file_name, self, initial_points=getattr(self, 'id_front_points', None))
            if dialog.exec_() == QDialog.Accepted and dialog.cropped_pixmap:
                self.id_front_cv_img = dialog.cropped_cv_img
                self.id_front_points = getattr(dialog, 'final_points', None)
                self.apply_id_filters()
        elif label == 'Back' and hasattr(self, 'id_back_file_name') and self.id_back_file_name:
            dialog = PerspectiveCropDialog(self.id_back_file_name, self, initial_points=getattr(self, 'id_back_points', None))
            if dialog.exec_() == QDialog.Accepted and dialog.cropped_pixmap:
                self.id_back_cv_img = dialog.cropped_cv_img
                self.id_back_points = getattr(dialog, 'final_points', None)
                self.apply_id_filters()

    def update_id_preview(self):
        # Update Paper Size
        paper_sizes = {
            0: (210.0, 297.0),
            1: (148.0, 210.0),
            2: (100.0, 150.0)
        }
        idx = self.cb_id_paper.currentIndex()
        pw, ph = paper_sizes.get(idx, (210.0, 297.0))
        self.id_preview.paper_w = pw
        self.id_preview.paper_h = ph
        self.id_preview.margin_left = self.sb_id_margin_left.value()
        self.id_preview.margin_right = self.sb_id_margin_right.value()
        self.id_preview.margin_top = self.sb_id_margin_top.value()
        self.id_preview.margin_bottom = self.sb_id_margin_bottom.value()
        
        self.id_preview.apply_rounded_corners = self.chk_id_rounded.isChecked()
        
        self.id_preview.photo_positions.clear()
        
        # ID Card Size from UI
        id_w = self.sb_id_w.value()
        id_h = self.sb_id_h.value()
        gap = 5.0
        
        # Default Alignment: Top Center
        cards_in_row = 0
        if self.id_front_pixmap: cards_in_row += 1
        if self.id_back_pixmap: cards_in_row += 1
        
        if cards_in_row > 0:
            total_w = cards_in_row * id_w + (cards_in_row - 1) * gap
            avail_w = pw - self.id_preview.margin_left - self.id_preview.margin_right
            start_x = self.id_preview.margin_left + (avail_w - total_w) / 2.0
        else:
            start_x = self.id_preview.margin_left
            
        start_y = self.id_preview.margin_top
        
        qty = self.sb_id_qty.value()
        
        curr_y = start_y
        for i in range(qty):
            # Check if fits on paper vertically
            if curr_y + id_h > self.id_preview.paper_h - self.id_preview.margin_bottom:
                break
            
            # Front Card
            if self.id_front_pixmap:
                self.id_preview.photo_positions.append({
                    'x': start_x, 'y': curr_y,
                    'w': id_w, 'h': id_h, 'label': 'Front',
                    'image_pixmap': self.id_front_pixmap,
                    'scale': 1.0, 'pan_x': 0.0, 'pan_y': 0.0, 'rotation_angle': 0,
                    'selected': False
                })
            
            # Back Card (side-by-side)
            if self.id_back_pixmap:
                self.id_preview.photo_positions.append({
                    'x': start_x + id_w + gap, 'y': curr_y,
                    'w': id_w, 'h': id_h, 'label': 'Back',
                    'image_pixmap': self.id_back_pixmap,
                    'scale': 1.0, 'pan_x': 0.0, 'pan_y': 0.0, 'rotation_angle': 0,
                    'selected': False
                })
            
            curr_y += id_h + gap
            
        self.id_preview.update()
        if not getattr(self.history_tab3, 'is_undoing_redoing', False):
            self.save_state_tab3()

    def save_id_pdf(self, show_msg=True):
        from PyQt5.QtWidgets import QMessageBox
        import os
        from datetime import datetime
        from PyQt5.QtGui import QPdfWriter, QPageSize, QPageLayout, QPainter, QTransform
        from PyQt5.QtCore import QSizeF, QMarginsF, Qt, QRectF
        
        file_name = ""
        if hasattr(self, 'default_pdf_folder') and self.default_pdf_folder and os.path.isdir(self.default_pdf_folder):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = os.path.join(self.default_pdf_folder, f"IDCard_{timestamp}.pdf")
        else:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "រក្សាទុកជា PDF / Save as PDF", "", "PDF Files (*.pdf)", options=options)
            
        if not file_name:
            return None
            
        pdf_writer = QPdfWriter(file_name)
        pdf_writer.setPageSize(QPageSize(QSizeF(self.id_preview.paper_w, self.id_preview.paper_h), QPageSize.Millimeter))
        pdf_writer.setPageMargins(QMarginsF(0, 0, 0, 0))
        pdf_writer.setResolution(300)
        
        painter = QPainter(pdf_writer)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        scale = 300 / 25.4
        painter.fillRect(0, 0, int(self.id_preview.paper_w * scale), int(self.id_preview.paper_h * scale), Qt.white)
        
        for pos in self.id_preview.photo_positions:
            x, y = pos['x'] * scale, pos['y'] * scale
            w, h = pos['w'] * scale, pos['h'] * scale
            rect = QRectF(x, y, w, h)
            
            painter.save()
            if getattr(self.id_preview, 'apply_rounded_corners', False):
                from PyQt5.QtGui import QPainterPath
                path = QPainterPath()
                radius_px = 3.18 * scale
                path.addRoundedRect(rect, radius_px, radius_px)
                painter.setClipPath(path)
                
            img = pos.get('image_pixmap')
            if img and not img.isNull():
                painter.drawPixmap(rect.toRect(), img)
            else:
                painter.setPen(QPen(Qt.black, 1))
                painter.drawRect(rect.toRect())
                
            painter.restore()
                
        painter.end()
        if show_msg:
            QMessageBox.information(self, "ជោគជ័យ / Success", "ឯកសារ PDF ត្រូវបានរក្សាទុកដោយជោគជ័យ! / PDF saved successfully!")
        return file_name

    def print_id_foxit(self):
        import subprocess
        from PyQt5.QtWidgets import QMessageBox
        import os
        
        if not hasattr(self, 'foxit_path') or not self.foxit_path or not os.path.exists(self.foxit_path):
            QMessageBox.warning(self, "មិនទាន់កំណត់កម្មវិធី / Not Configured", "សូមចូលទៅកាន់ Settings (⚙) ដើម្បីកំណត់ទីតាំងកម្មវិធី Foxit PDF ជាមុនសិន។")
            return
            
        file_name = self.save_id_pdf(show_msg=False)
        if file_name:
            try:
                subprocess.Popen([self.foxit_path, file_name])
            except Exception as e:
                QMessageBox.critical(self, "កំហុស / Error", f"មិនអាចបើកកម្មវិធី Foxit PDF បានទេ:\n{str(e)}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        file_names = [url.toLocalFile() for url in urls if url.isLocalFile()]
        
        valid_files = []
        from PyQt5.QtWidgets import QDialog
        for f in file_names:
            if f.lower().endswith('.pdf'):
                dialog = PdfImportDialog(f, self)
                if dialog.exec_() == QDialog.Accepted and dialog.temp_image_path:
                    valid_files.append(dialog.temp_image_path)
            elif any(f.lower().endswith(e) for e in ['.png', '.jpg', '.jpeg', '.bmp']):
                valid_files.append(f)
        
        if not valid_files:
            return
            
        current_tab = self.tabs.currentIndex()
        
        if current_tab == 0:
            self.loaded_images = valid_files
            self.btn_clear.setVisible(True)
            if len(valid_files) == 1:
                self.default_image_pixmap = QPixmap(valid_files[0])
                self.lbl_image_status.setText(f"<i>បានជ្រើសរើស: {valid_files[0].split('/')[-1]}</i>")
            else:
                self.default_image_pixmap = None
                self.lbl_image_status.setText(f"<i>បានជ្រើសរើសរូបភាពចំនួន {len(valid_files)} ឯកសារ</i>")
            self.calculate_layout()
            
        elif current_tab == 1:
            if len(valid_files) >= 1:
                self.process_ocr_from_file(valid_files[0])
            
        elif current_tab == 2:
            from PyQt5.QtWidgets import QDialog
            for i, fpath in enumerate(valid_files):
                if len(valid_files) >= 2:
                    target = 'front' if i == 0 else 'back'
                else:
                    if self.id_front_cv_img is None:
                        target = 'front'
                    elif self.id_back_cv_img is None:
                        target = 'back'
                    else:
                        target = 'front'
                
                if i > 1:
                    break

                dialog = PerspectiveCropDialog(fpath, self)
                is_accepted = dialog.exec_() == QDialog.Accepted
                
                if target == 'front':
                    self.id_front_file_name = fpath
                    self.id_front_points = None
                    if is_accepted and dialog.cropped_pixmap:
                        self.id_front_cv_img = dialog.cropped_cv_img
                        self.id_front_points = getattr(dialog, 'final_points', None)
                    else:
                        img = cv2.imdecode(np.fromfile(fpath, dtype=np.uint8), cv2.IMREAD_COLOR)
                        self.id_front_cv_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img is not None else None
                else:
                    self.id_back_file_name = fpath
                    self.id_back_points = None
                    if is_accepted and dialog.cropped_pixmap:
                        self.id_back_cv_img = dialog.cropped_cv_img
                        self.id_back_points = getattr(dialog, 'final_points', None)
                    else:
                        img = cv2.imdecode(np.fromfile(fpath, dtype=np.uint8), cv2.IMREAD_COLOR)
                        self.id_back_cv_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img is not None else None
                        
            self.apply_id_filters()

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
    app.setApplicationName("Fast Print Text Photo")
    
    window = PhotoPrintApp()
    window.setWindowIcon(app_icon)
    window.showMaximized()
    sys.exit(app.exec_())
