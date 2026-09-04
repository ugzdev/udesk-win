import sys
import os
import json
import base64
import urllib.request
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QMessageBox, QScrollArea,
    QFrame, QListWidget, QListWidgetItem, QToolButton, QPlainTextEdit,
    QSizePolicy, QComboBox, QDialog, QGridLayout, QCheckBox, QStackedWidget,QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QFont, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer, QSvgWidget


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────
#  Tek buton için görsel ve tıklamalı editör
# ──────────────────────────────────────────────
class ButtonEditor(QFrame):
    sig_delete   = pyqtSignal(object)
    sig_move_up  = pyqtSignal(object)
    sig_move_down = pyqtSignal(object)

    def __init__(self, btn_data=None, parent=None):
        super().__init__(parent)
        self.setObjectName("ButtonEditor")
        if not btn_data:
            btn_data = {
                "id": "btn_1", "type": "icon", "label": "New Button", 
                "svg_raw": "", "has_indicator": False, 
                "action": {"type": "system", "command": "Mute/Unmute Audio"}
            }
        self._build(btn_data)

    def _build(self, data):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # --- 1. SATIR (Temel Ayarlar) ---
        top = QHBoxLayout()
        top.setSpacing(6)
        
        btn_up = QToolButton()
        btn_up.setText("▲")
        btn_up.setObjectName("ArrowBtn")
        btn_up.setFixedSize(26, 26)
        btn_up.clicked.connect(lambda: self.sig_move_up.emit(self))
        top.addWidget(btn_up)

        btn_dn = QToolButton()
        btn_dn.setText("▼")
        btn_dn.setObjectName("ArrowBtn")
        btn_dn.setFixedSize(26, 26)
        btn_dn.clicked.connect(lambda: self.sig_move_down.emit(self))
        top.addWidget(btn_dn)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Title", "Icon (SVG)"])
        self.cmb_type.setObjectName("FieldLabel")
        if data.get("type") == "icon":
            self.cmb_type.setCurrentIndex(1)
        self.cmb_type.currentIndexChanged.connect(self._toggle_type)
        top.addWidget(self.cmb_type)

        self.chk_indicator = QCheckBox("LED Indicator")
        self.chk_indicator.setObjectName("FieldLabel")
        self.chk_indicator.setChecked(data.get("has_indicator", False))
        top.addWidget(self.chk_indicator)

        self.inp_label = QLineEdit(data.get("label", ""))
        self.inp_label.setPlaceholderText("Button title")
        top.addWidget(self.inp_label, stretch=3)

        lbl_id = QLabel("ID:")
        lbl_id.setObjectName("FieldLabel")
        top.addWidget(lbl_id)

        self.inp_id = QLineEdit(data.get("id", ""))
        self.inp_id.setPlaceholderText("btn_1")
        self.inp_id.setFixedWidth(60)
        top.addWidget(self.inp_id)

        btn_del = QToolButton()
        btn_del.setText("✕")
        btn_del.setObjectName("DeleteBtn")
        btn_del.setFixedSize(28, 28)
        btn_del.clicked.connect(lambda: self.sig_delete.emit(self))
        top.addWidget(btn_del)

        root.addLayout(top)

        # --- 2. SATIR (SVG Girişi) ---
        self.inp_svg = QPlainTextEdit(data.get("svg_raw", ""))
        self.inp_svg.setObjectName("CodeEdit")
        self.inp_svg.setPlaceholderText('Paste <svg>...</svg> code here (Applies to Icon mode)')
        self.inp_svg.setFixedHeight(50)
        root.addWidget(self.inp_svg)
        self._toggle_type(self.cmb_type.currentIndex())

        # --- 3. SATIR (Eylem Seçici) ---
        action_layout = QHBoxLayout()
        lbl_act = QLabel("Action to Trigger:")
        lbl_act.setObjectName("FieldLabel")
        action_layout.addWidget(lbl_act)
        
        self.combo_action = QComboBox()
        self.combo_action.addItems([
            "1. System Control", 
            "2. Trigger Shortcut", 
            "3. Open App/Folder", 
            "4. Open Website", 
            "5. Play Audio"
        ])
        self.combo_action.currentIndexChanged.connect(self._change_action_page)
        action_layout.addWidget(self.combo_action, stretch=1)
        root.addLayout(action_layout)

        # --- 4. SATIR (Dinamik QStackedWidget) ---
        self.stack = QStackedWidget()
        
        # Sayfa 0: Sistem
        self.page_sys = QWidget()
        sys_lay = QVBoxLayout(self.page_sys)
        sys_lay.setContentsMargins(0, 0, 0, 0)
        self.combo_sys = QComboBox()
        self.combo_sys.addItems(["Mute/Unmute Audio", "Mute/Unmute Microphone", "Sleep Mode", "Lock", "Shut Down", "Restart"])
        sys_lay.addWidget(self.combo_sys)
        self.stack.addWidget(self.page_sys)

        # Sayfa 1: Kısayol
        self.page_shortcut = QWidget()
        short_lay = QVBoxLayout(self.page_shortcut)
        short_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_shortcut = QLineEdit()
        self.inp_shortcut.setPlaceholderText("Örn: ctrl+shift+s")
        short_lay.addWidget(self.inp_shortcut)
        self.stack.addWidget(self.page_shortcut)

        # Sayfa 2: Uygulama
        self.page_launch = QWidget()
        launch_lay = QHBoxLayout(self.page_launch)
        launch_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_launch = QLineEdit()
        self.inp_launch.setPlaceholderText("Selected path...")
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_path)
        launch_lay.addWidget(self.inp_launch)
        launch_lay.addWidget(btn_browse)
        self.stack.addWidget(self.page_launch)

        # Sayfa 3: Web
        self.page_web = QWidget()
        web_lay = QHBoxLayout(self.page_web)
        web_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_url = QLineEdit()
        self.inp_url.setPlaceholderText("https://youtube.com")
        self.combo_browser = QComboBox()
        self.combo_browser.addItems(["Default", "Chrome", "Edge", "Opera", "Firefox"])
        self.chk_private = QCheckBox("Private")
        web_lay.addWidget(self.inp_url, stretch=2)
        web_lay.addWidget(self.combo_browser, stretch=1)
        web_lay.addWidget(self.chk_private)
        self.stack.addWidget(self.page_web)

        # Sayfa 4: Ses
        self.page_sound = QWidget()
        sound_lay = QHBoxLayout(self.page_sound)
        sound_lay.setContentsMargins(0, 0, 0, 0)
        self.combo_sound = QComboBox()
        self._load_sounds()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._load_sounds)
        sound_lay.addWidget(self.combo_sound, stretch=1)
        sound_lay.addWidget(btn_refresh)
        self.stack.addWidget(self.page_sound)

        root.addWidget(self.stack)

        # Mevcut JSON verisini arayüze doldur
        self._populate_action_data(data.get("action", {}))

    def _toggle_type(self, idx):
        if idx == 0:
            self.inp_label.show()
            self.inp_svg.hide()
        else:
            self.inp_label.hide()
            self.inp_svg.show()

    def _change_action_page(self, index):
        self.stack.setCurrentIndex(index)

    def _browse_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select App/Folder", "", "All Files (*.*)")
        if path:
            self.inp_launch.setText(path)

    def _load_sounds(self):
        self.combo_sound.clear()
        # __file__ karmaşasını sil, direkt BASE_DIR kullan
        sound_dir = os.path.join(BASE_DIR, "sounds")
        if os.path.exists(sound_dir):
            files = [f for f in os.listdir(sound_dir) if f.endswith(('.mp3', '.wav'))]
            if files:
                self.combo_sound.addItems(files)
            else:
                self.combo_sound.addItem("No sounds in folder")
        else:
            try: os.makedirs(sound_dir, exist_ok=True)
            except: pass
            self.combo_sound.addItem("sounds folder created")

    def _populate_action_data(self, action_data):
        atype = action_data.get("type", "system")
        if atype == "system":
            self.combo_action.setCurrentIndex(0)
            idx = self.combo_sys.findText(action_data.get("command", ""))
            if idx >= 0: self.combo_sys.setCurrentIndex(idx)
        elif atype == "shortcut":
            self.combo_action.setCurrentIndex(1)
            self.inp_shortcut.setText(action_data.get("keys", ""))
        elif atype == "launch":
            self.combo_action.setCurrentIndex(2)
            self.inp_launch.setText(action_data.get("path", ""))
        elif atype == "website":
            self.combo_action.setCurrentIndex(3)
            self.inp_url.setText(action_data.get("url", ""))
            idx = self.combo_browser.findText(action_data.get("browser", "Default"))
            if idx >= 0: self.combo_browser.setCurrentIndex(idx)
            self.chk_private.setChecked(action_data.get("private", False))
        elif atype == "sound":
            self.combo_action.setCurrentIndex(4)
            idx = self.combo_sound.findText(action_data.get("file", ""))
            if idx >= 0: self.combo_sound.setCurrentIndex(idx)

    def get_data(self):
        btn_type = "text" if self.cmb_type.currentIndex() == 0 else "icon"
        svg_text = self.inp_svg.toPlainText()
        
        b64_image = ""
        if btn_type == "icon" and svg_text.strip():
            try:
                render_svg = svg_text.replace("currentColor", "#ffffff")
                renderer = QSvgRenderer(render_svg.encode('utf-8'))
                pixmap = QPixmap(100, 100)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                pixmap.save(buffer, "PNG")
                b64_image = base64.b64encode(byte_array.data()).decode('utf-8')
            except Exception:
                pass

        action_index = self.combo_action.currentIndex()
        action_data = {}
        if action_index == 0:
            action_data = {"type": "system", "command": self.combo_sys.currentText()}
        elif action_index == 1:
            action_data = {"type": "shortcut", "keys": self.inp_shortcut.text().strip()}
        elif action_index == 2:
            action_data = {"type": "launch", "path": self.inp_launch.text().strip()}
        elif action_index == 3:
            action_data = {
                "type": "website", 
                "url": self.inp_url.text().strip(), 
                "browser": self.combo_browser.currentText(),
                "private": self.chk_private.isChecked()
            }
        elif action_index == 4:
            action_data = {"type": "sound", "file": self.combo_sound.currentText()}

        return {
            "id": self.inp_id.text().strip() or "btn_1",
            "type": btn_type,
            "label": self.inp_label.text().strip() or "Button",
            "base64_image": b64_image,
            "svg_raw": svg_text,
            "has_indicator": self.chk_indicator.isChecked(),
            "action": action_data
        }

# ──────────────────────────────────────────────
#  İkon Galerisi (Değişmedi)
# ──────────────────────────────────────────────
class LucideGalleryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lucide Icon Repo")
        self.setFixedSize(540, 500)
        self.setStyleSheet(parent.styleSheet())
        self.icons_data = {}
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Icons...")
        self.search_input.setObjectName("SearchInput")
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)
        
        self.scroll = QScrollArea()
        self.scroll.setObjectName("EditorScroll")
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        self._load_lucide_icons()
        self._render_icons()

    def _load_lucide_icons(self):
        cache_file = os.path.join(BASE_DIR, "lucide_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.icons_data = json.load(f)
                return
            except: pass

        self.setWindowTitle("Lucide Icon Repository (Downloading, please wait...)")
        QApplication.processEvents()
        url = "https://unpkg.com/lucide-static/icon-nodes.json"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                raw_data = json.loads(response.read().decode('utf-8'))
            for name, nodes in raw_data.items():
                inner_html = ""
                for node in nodes:
                    tag = node[0]
                    attrs = " ".join(f'{k}="{v}"' for k, v in node[1].items())
                    inner_html += f"<{tag} {attrs} />"
                raw_svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner_html}</svg>'
                display_svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#d4d5d6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner_html}</svg>'
                self.icons_data[name] = {"raw": raw_svg, "display": display_svg}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.icons_data, f)
            self.setWindowTitle("Lucide Icon Repo")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not download icons.\nError: {e}")

    def _on_search(self, text):
        self._render_icons(text.lower().strip())

    def _render_icons(self, search_query=""):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
                
        row, col, count = 0, 0, 0
        MAX_DISPLAY = 60
        
        for name, data in self.icons_data.items():
            if search_query in name:
                btn = QWidget()
                btn.setObjectName("ButtonEditor")
                btn.setFixedSize(90, 90)
                btn_v = QVBoxLayout(btn)
                btn_v.setAlignment(Qt.AlignCenter)
                btn_v.setContentsMargins(5, 10, 5, 10)
                
                svg_view = QSvgWidget()
                svg_view.load(data["display"].encode('utf-8'))
                svg_view.setFixedSize(32, 32)
                
                lbl = QLabel(name.replace("-", " ").title())
                lbl.setObjectName("ModNameLabel")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setWordWrap(True)
                lbl.setStyleSheet("font-size: 10px;")
                
                btn_v.addWidget(svg_view, alignment=Qt.AlignCenter)
                btn_v.addWidget(lbl, alignment=Qt.AlignCenter)
                
                btn.setCursor(Qt.PointingHandCursor)
                btn.mousePressEvent = lambda event, n=name, code=data["raw"]: self._copy_to_clipboard(n, code)
                
                self.grid.addWidget(btn, row, col)
                col += 1
                if col > 4: 
                    col = 0
                    row += 1
                count += 1
                if count >= MAX_DISPLAY: break

    def _copy_to_clipboard(self, name, svg_code):
        clipboard = QApplication.clipboard()
        clipboard.setText(svg_code)
        QMessageBox.information(self, "Copied", f"'{name}' icon copied to clipboard!\nYou can paste it into the SVG box in the editor.")
        self.accept()

# ──────────────────────────────────────────────
#  Ana pencere (YENİ JSON TABANLI SİSTEM)
# ──────────────────────────────────────────────
class ModEditorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("uDesk Mod Editor")
        self.resize(1140, 780)
        self.setMinimumSize(900, 640)

        # Mod klasörünü ana kurulum dizini altındaki 'mods' olarak belirliyoruz 
        self.mods_dir = os.path.join(BASE_DIR, "mods")
        os.makedirs(self.mods_dir, exist_ok=True)

        self.current_file  = None
        self.btn_editors: list[ButtonEditor] = []

        self._build_ui()
        self._apply_theme()
        self._refresh_list()

    def _build_ui(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        root_h = QHBoxLayout(root_w)
        root_h.setContentsMargins(0, 0, 0, 0)
        root_h.setSpacing(0)

        sidebar = QWidget(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(260)
        sb_v = QVBoxLayout(sidebar)
        sb_v.setContentsMargins(12, 14, 12, 14); sb_v.setSpacing(10)

        sb_title = QLabel("JSON MODs")
        sb_title.setObjectName("SbTitle")
        sb_v.addWidget(sb_title)

        new_btn = QPushButton("＋  New Mod")
        new_btn.setObjectName("NewBtn")
        new_btn.setFixedHeight(34)
        new_btn.clicked.connect(self._new_mod)
        sb_v.addWidget(new_btn)
        
        gallery_btn = QPushButton("Find SVG Icon")
        gallery_btn.setObjectName("SecondaryBtn")
        gallery_btn.setFixedHeight(34)
        gallery_btn.clicked.connect(self._open_lucide_gallery)
        sb_v.addWidget(gallery_btn)

        self.mod_list = QListWidget()
        self.mod_list.setObjectName("ModList")
        self.mod_list.itemClicked.connect(self._open_from_list)
        sb_v.addWidget(self.mod_list)

        root_h.addWidget(sidebar)

        vline = QFrame()
        vline.setFrameShape(QFrame.VLine); vline.setObjectName("VLine")
        root_h.addWidget(vline)

        right_w = QWidget()
        right_v = QVBoxLayout(right_w)
        right_v.setContentsMargins(24, 18, 24, 18); right_v.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl_fn = QLabel("File Name:")
        lbl_fn.setObjectName("FieldLabel")
        top_row.addWidget(lbl_fn)
        self.inp_filename = QLineEdit()
        self.inp_filename.setPlaceholderText("file_name.json")
        self.inp_filename.setFixedWidth(180)
        top_row.addWidget(self.inp_filename)

        top_row.addSpacing(14)

        lbl_tl = QLabel("Title:")
        lbl_tl.setObjectName("FieldLabel")
        top_row.addWidget(lbl_tl)
        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText("Mod Title")
        top_row.addWidget(self.inp_title, stretch=1)

        top_row.addSpacing(14)

        save_btn = QPushButton("Save (JSON)")
        save_btn.setObjectName("SaveBtn")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save_mod)
        top_row.addWidget(save_btn)

        right_v.addLayout(top_row)

        hline = QFrame()
        hline.setFrameShape(QFrame.HLine); hline.setObjectName("HLine")
        right_v.addWidget(hline)

        btn_hdr = QHBoxLayout()
        sec_lbl = QLabel("Button Actions")
        sec_lbl.setObjectName("SecLabel")
        btn_hdr.addWidget(sec_lbl)
        btn_hdr.addStretch()
        add_btn = QPushButton("＋  Add Button")
        add_btn.setObjectName("AddBtn")
        add_btn.setFixedHeight(30)
        add_btn.clicked.connect(lambda: self._add_editor(None))
        btn_hdr.addWidget(add_btn)
        right_v.addLayout(btn_hdr)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("EditorScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setObjectName("EditorContainer")
        self.container_v = QVBoxLayout(self.container)
        self.container_v.setContentsMargins(2, 4, 2, 4)
        self.container_v.setSpacing(10)
        self.container_v.addStretch()

        self.scroll.setWidget(self.container)
        right_v.addWidget(self.scroll)

        root_h.addWidget(right_w, stretch=1)
        
    def _open_lucide_gallery(self):
        dialog = LucideGalleryDialog(self)
        dialog.exec_()

    def _refresh_list(self):
        self.mod_list.clear()
        try:
            for f in sorted(os.listdir(self.mods_dir)):
                if f.endswith(".json"):
                    item_widget = QWidget()
                    item_h = QHBoxLayout(item_widget)
                    item_h.setContentsMargins(6, 2, 6, 2)
                    item_h.setSpacing(4)
                    item_widget.setStyleSheet("background-color: #303030;border-radius: 4px;")
                    
                    lbl_name = QLabel(f)
                    lbl_name.setObjectName("ModNameLabel")
                    lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    item_h.addWidget(lbl_name, stretch=1)
                    
                    btn_del = QToolButton()
                    btn_del.setText("✕")
                    btn_del.setObjectName("ModDeleteBtn")
                    btn_del.setFixedSize(22, 22)
                    btn_del.setToolTip("Delete")
                    file_path = os.path.join(self.mods_dir, f)
                    btn_del.clicked.connect(lambda checked=False, fp=file_path: self._delete_mod(fp))
                    item_h.addWidget(btn_del)
                    
                    item_widget.adjustSize()
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, os.path.join(self.mods_dir, f))
                    hint = item_widget.sizeHint()
                    item.setSizeHint(QSize(max(hint.width(), 200), max(hint.height(), 50)))
                    self.mod_list.addItem(item)
                    self.mod_list.setItemWidget(item, item_widget)
                    lbl_name.mousePressEvent = lambda event, it=item: self._on_mod_item_clicked(it)
        except Exception: pass

    def _delete_mod(self, file_path: str):
        file_name = os.path.basename(file_path)
        msg = f'Are you sure you want to delete the mod "{file_name}"?\n\nThis action cannot be undone!'
        reply = QMessageBox.question(self, "Confirm Mod Deletion", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                if self.current_file == file_path:
                    self._new_mod()
                self._refresh_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", "Could not delete file:\n" + str(e))
                
    def _on_mod_item_clicked(self, item):
        self._load_mod(item.data(Qt.UserRole))
        self.mod_list.setCurrentItem(item)         
    
    def _open_from_list(self, item):
        self._load_mod(item.data(Qt.UserRole))

    def _new_mod(self):
        self.current_file = None
        self.inp_filename.clear()
        self.inp_title.setText("New Mod")
        self._clear_editors()
        self._add_editor(None)
        self.mod_list.clearSelection()

    def _load_mod(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                mod_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read JSON file:\n{e}")
            return

        self.current_file = path
        self.inp_filename.setText(os.path.basename(path))
        self.inp_title.setText(mod_data.get("title", ""))
        
        self._clear_editors()
        buttons = mod_data.get("buttons", [])
        if not buttons:
            self._add_editor(None)
        else:
            for b in buttons:
                self._add_editor(b)

    def _clear_editors(self):
        for ed in self.btn_editors:
            self.container_v.removeWidget(ed)
            ed.deleteLater()
        self.btn_editors.clear()

    def _add_editor(self, btn_data=None):
        if btn_data is None:
            used = {e.inp_id.text() for e in self.btn_editors}
            i = len(self.btn_editors) + 1
            while f"btn_{i}" in used: i += 1
            btn_data = {
                "id": f"btn_{i}", "label": f"Button {len(self.btn_editors) + 1}", 
                "type": "text", "has_indicator": False, 
                "action": {"type": "system", "command": "Mute/Unmute Audio"}
            }

        ed = ButtonEditor(btn_data, parent=self.container)
        ed.sig_delete.connect(self._remove_editor)
        ed.sig_move_up.connect(self._move_up)
        ed.sig_move_down.connect(self._move_down)

        pos = self.container_v.count() - 1
        self.container_v.insertWidget(pos, ed)
        self.btn_editors.append(ed)

    def _remove_editor(self, ed):
        if ed in self.btn_editors:
            self.btn_editors.remove(ed)
            self.container_v.removeWidget(ed)
            ed.deleteLater()

    def _move_up(self, ed):
        idx = self.btn_editors.index(ed)
        if idx == 0: return
        self.btn_editors[idx], self.btn_editors[idx - 1] = self.btn_editors[idx - 1], self.btn_editors[idx]
        self._rebuild_layout()

    def _move_down(self, ed):
        idx = self.btn_editors.index(ed)
        if idx == len(self.btn_editors) - 1: return
        self.btn_editors[idx], self.btn_editors[idx + 1] = self.btn_editors[idx + 1], self.btn_editors[idx]
        self._rebuild_layout()

    def _rebuild_layout(self):
        while self.container_v.count() > 1:
            item = self.container_v.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for ed in self.btn_editors:
            self.container_v.insertWidget(self.container_v.count() - 1, ed)
            ed.setParent(self.container)
            ed.show()

    def _save_mod(self):
        name = self.inp_filename.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "File name cannot be empty.")
            return
        if not name.endswith(".json"):
            name += ".json"

        mod_data = {
            "title": self.inp_title.text().strip() or "New Mod",
            "buttons": [ed.get_data() for ed in self.btn_editors]
        }

        path = os.path.join(self.mods_dir, name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(mod_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save:\n{e}")
            return

        self.current_file = path
        self._refresh_list()
        for i in range(self.mod_list.count()):
            if self.mod_list.item(i).text() == name:
                self.mod_list.setCurrentRow(i)
                break

        QMessageBox.information(self, "Success", f"{name} saved in JSON format!\nRefresh uDesk from Android.")

    def _apply_theme(self):
        self.setStyleSheet("""
/* ── Genel ── */
QMainWindow, QWidget               { background: #141414; color: #d4d5d6; font-family: 'Segoe UI', sans-serif; }

/* ── Sol kenar ── */
QWidget#Sidebar                    { background: #0f0f0f; }
QLabel#SbTitle                     { color: #4a5568; font-size: 10px; font-weight: bold; letter-spacing: 3px; padding: 2px 0 6px 0; }

QPushButton#NewBtn {
    background: #0e2a45; color: #29b6f6; border: 1px solid #1a4a6a; border-radius: 6px;
    font-size: 13px; font-weight: bold;
}
QPushButton#NewBtn:hover           { background: #122f4e; }

QListWidget#ModList {
    background: transparent; border: none; color: #8b949e; font-size: 12px;
}
QListWidget#ModList::item          { padding: 8px 6px; border-radius: 8px; }
QListWidget#ModList::item:hover    { background: #5e5e5e; color: #c9d1d9; }
QListWidget#ModList::item:selected { background: #3b3b3b; color: #29b6f6; }

/* ── Ayırıcılar ── */
QFrame#VLine { background: #161b22; border: none; max-width: 1px; }
QFrame#HLine { background: #21262d; border: none; max-height: 1px; margin: 4px 0; }

/* ── Genel etiket / input ── */
QLabel#FieldLabel { color: #6e7681; font-size: 12px; background: transparent;}
QLabel#SecLabel   { color: #4a5568; font-size: 10px; font-weight: bold; letter-spacing: 3px; }
QLabel#CodeLabel  { color: #6e7681; font-size: 11px; }

QLineEdit, QComboBox {
    background: #0d0d0d; color: #e6edf3; border: 1px solid #30363d; border-radius: 5px;
    padding: 5px 10px; font-size: 12px;
}
QLineEdit:focus, QComboBox:focus { border-color: #388bfd; }

/* ── Kaydet butonu ── */
QPushButton#SaveBtn {
    background: #0e2a45; color: #29b6f6; border: 1px solid #1a4a6a; border-radius: 6px;
    font-size: 13px; font-weight: bold; padding: 0 18px;
}
QPushButton#SaveBtn:hover { background: #122f4e; }

/* ── Ekle butonu ── */
QPushButton#AddBtn {
    background: #0d2818; color: #3fb950; border: 1px solid #238636; border-radius: 5px;
    font-size: 12px; font-weight: bold; padding: 0 12px;
}
QPushButton#AddBtn:hover { background: #166534; }

/* ── Scroll alanı ── */
QScrollArea#EditorScroll           { border: none; background: transparent; }
QScrollArea#EditorScroll > QWidget { background: transparent; }
QWidget#EditorContainer            { background: transparent; }

QScrollBar:vertical                { background: #090d13; width: 7px; border-radius: 3px; }
QScrollBar::handle:vertical        { background: #21262d; border-radius: 3px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Buton editör kartı ── */
QFrame#ButtonEditor {
    background: #0f0f0f; border: 1px solid #212121; border-radius: 9px;
}

QToolButton#ArrowBtn {
    background: #0d0d0d; color: #8b949e; border: 1px solid #30363d; border-radius: 4px; font-size: 10px;
}
QToolButton#ArrowBtn:hover { background: #2d3748; color: #c9d1d9; }

QToolButton#DeleteBtn {
    background: #1c2333; color: #f85149; border: 1px solid #30363d; border-radius: 4px; font-size: 12px;
}
QToolButton#DeleteBtn:hover { background: #3d1a1a; }

QPlainTextEdit#CodeEdit {
    background: #0d0d0d; color: #3fb950; border: 1px solid #4f4f4f; border-radius: 5px;
    selection-background-color: #1f3d5c;
}

QLineEdit { selection-background-color: #1f3d5c; }

QLabel#ModNameLabel { color: #bdbdbd; font-size: 12px; background: transparent; }
QListWidget#ModList::item:selected QLabel#ModNameLabel { color: #bdbdbd; }
QToolButton#ModDeleteBtn {
    background: transparent; color: #8b949e; border: none; border-radius: 3px;
    font-size: 10px; font-weight: bold; padding: 0px; margin: 0px;
}
QToolButton#ModDeleteBtn:hover { background: #3d1a1a; color: #f85149; }
QPushButton#SecondaryBtn {
    background: #1c2128; color: #adbac7; border: 1px solid #444c56; border-radius: 6px;
    font-size: 13px; font-weight: bold;
}
QPushButton#SecondaryBtn:hover { background: #2d333b; border-color: #768390; }
QLineEdit#SearchInput {
    background: #0d0d0d; color: #66c0f4; border: 1px solid #1a4a6a; border-radius: 8px;
    padding: 10px 14px; font-size: 14px; font-weight: bold;
}
QLineEdit#SearchInput:focus { border-color: #29b6f6; background: #121212; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ModEditorApp()
    win.show()
    sys.exit(app.exec_())