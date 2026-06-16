class TextPreviewWidget(QWidget):
    """ Custom Widget សម្រាប់គូរទិដ្ឋភាពអក្សរធំ (Live Text Preview) """
    selectionChanged = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet('background-color: #dbe2e9;')
        self.paper_w = 210.0
        self.paper_h = 297.0
        self.margin_top = 10
        self.margin_bottom = 10
        self.margin_left = 10
        self.margin_right = 10
        self.text = ''
        self.text_color = QColor(0, 0, 0)
        self.font_family_kh = 'Khmer OS Muol Light'
        self.font_family_en = 'Arial'
        self.base_font_size = 50.0
        self.font_bold = False
        self.font_italic = False
        self.font_underline = False
        self.text_bg_color = QColor(Qt.transparent)
        self.text_align = Qt.AlignCenter
        self.bg_color = QColor(255, 255, 255)
        self.auto_fit = False
        self.free_stretch = False
        self.lines_data = []
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
                self.lines_data.append({'rect': new_rect, 'font_kh': self.font_family_kh, 'font_en': self.font_family_en, 'base_size': self.base_font_size, 'bold': self.font_bold, 'italic': self.font_italic, 'underline': self.font_underline, 'color': QColor(self.text_color), 'bg_color': QColor(Qt.transparent)})
            if len(self.lines_data) > len(lines):
                self.lines_data = self.lines_data[:len(lines)]
            if self.selected_line_idx >= len(lines):
                self.selected_line_idx = max(0, len(lines) - 1)
                self.selectionChanged.emit(self.selected_line_idx)
        self.update()

    def get_handle_at(self, pos):
        if not self.free_stretch or not self.lines_data:
            return None
        if self.selected_line_idx < 0 or self.selected_line_idx >= len(self.lines_data):
            return None
        sel_rect_mm = self.lines_data[self.selected_line_idx]['rect']
        rect_px = QRectF(self.current_paper_x + sel_rect_mm.x() * self.current_scale, self.current_paper_y + sel_rect_mm.y() * self.current_scale, sel_rect_mm.width() * self.current_scale, sel_rect_mm.height() * self.current_scale)
        hs = 10

        def hit(p):
            return QRectF(p.x() - hs / 2, p.y() - hs / 2, hs, hs).contains(pos)
        if hit(rect_px.topLeft()):
            return 'TL'
        if hit(rect_px.topRight()):
            return 'TR'
        if hit(rect_px.bottomLeft()):
            return 'BL'
        if hit(rect_px.bottomRight()):
            return 'BR'
        if hit(QPointF(rect_px.center().x(), rect_px.top())):
            return 'T'
        if hit(QPointF(rect_px.center().x(), rect_px.bottom())):
            return 'B'
        if hit(QPointF(rect_px.left(), rect_px.center().y())):
            return 'L'
        if hit(QPointF(rect_px.right(), rect_px.center().y())):
            return 'R'
        if rect_px.contains(pos):
            return 'C'
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
                    rect_px = QRectF(self.current_paper_x + rect_mm.x() * self.current_scale, self.current_paper_y + rect_mm.y() * self.current_scale, rect_mm.width() * self.current_scale, rect_mm.height() * self.current_scale)
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
        if self.drag_mode and self.drag_start_pos and self.drag_start_rect and (self.selected_line_idx < len(self.lines_data)):
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
            if new_rect.width() < 5:
                new_rect.setWidth(5)
            if new_rect.height() < 5:
                new_rect.setHeight(5)
            self.lines_data[self.selected_line_idx]['rect'] = new_rect
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
        if self.paper_h <= 0:
            return
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
                if not self.lines_data:
                    self.set_text(self.text)
                for i, line in enumerate(lines):
                    if i >= len(self.lines_data):
                        break
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
                    if i == self.selected_line_idx:
                        painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
                        painter.setBrush(Qt.NoBrush)
                        painter.drawRect(rect_px)
                        painter.setPen(QPen(Qt.blue, 1))
                        painter.setBrush(Qt.white)
                        hs = 8
                        handles = [rect_px.topLeft(), rect_px.topRight(), rect_px.bottomLeft(), rect_px.bottomRight(), QPointF(rect_px.center().x(), rect_px.top()), QPointF(rect_px.center().x(), rect_px.bottom()), QPointF(rect_px.left(), rect_px.center().y()), QPointF(rect_px.right(), rect_px.center().y())]
                        for p in handles:
                            painter.drawRect(QRectF(p.x() - hs / 2, p.y() - hs / 2, hs, hs))
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