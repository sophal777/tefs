import os
import subprocess
import sys
import time
import logging
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QFileDialog, QSpinBox, QTabWidget
)
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtGui import QFont
import pygetwindow as gw
import psutil
import emulator
from emulator.option import EmulatorOptions

LDPLAYER_PATHS_FILE = 'ldplayer_paths.txt'
CONFIG_FILE = 'config.json'
logging.basicConfig(filename='emulator_app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_ldplayer_paths(file_path):
    paths = {}
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            pass
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                path = line.strip()
                if path and os.path.exists(path) and os.path.exists(os.path.join(path, 'ldconsole.exe')):
                    label = f"LDPlayer Path {i}"
                    paths[label] = path
                else:
                    logging.warning(f"Skipping invalid LDPlayer path in file: {path}")
        return paths
    except Exception as e:
        logging.error(f"Error loading ldplayer paths: {e}")
        return {}

def find_emulator_window(emulator_name, retries=5, delay=2):
    for _ in range(retries):
        for title in gw.getAllTitles():
            if emulator_name.lower() in title.lower():
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    return windows[0]
        time.sleep(delay)
    return None

def smooth_move(win, start_x, start_y, end_x, end_y, duration=2.0, steps=50):
    dx = (end_x - start_x) / steps
    dy = (end_y - start_y) / steps
    interval = duration / steps
    for step in range(steps):
        new_x = int(start_x + dx * step)
        new_y = int(start_y + dy * step)
        win.moveTo(new_x, new_y)
        print(f"\r[⏳] Moving... step {step + 1}/{steps}", end="", flush=True)
        time.sleep(interval)
    win.moveTo(end_x, end_y)
    print(f"\n[✅] Arrived at ({end_x}, {end_y})")

def calculate_position(index, columns=5, offset_x=350, offset_y=250, start_x=0, start_y=0):
    col = index % columns
    row = index // columns
    x = start_x + col * offset_x
    y = start_y + row * offset_y
    return x, y

class Worker(QObject):
    status_update = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, ld, selected_indices, auto_arrange=False, columns=5, offset_x=350, offset_y=250, duration=2.5):
        super().__init__()
        self.ld = ld
        self.selected_indices = selected_indices
        self.auto_arrange = auto_arrange
        self.columns = columns
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.duration = duration

    def run(self):
        try:
            for grid_index, emulator_index in enumerate(self.selected_indices):
                em = self.ld.emulators[emulator_index]
                self.status_update.emit(emulator_index, "🟡 Starting")
                em.start()
                time.sleep(5)
                win = find_emulator_window(em.name)
                if not win:
                    self.status_update.emit(emulator_index, "❌ Window not found")
                    logging.warning(f"Window not found for emulator: {em.name}")
                    continue
                if self.auto_arrange:
                    self.status_update.emit(emulator_index, "🟡 Arranging")
                    start_x, start_y = win.topleft
                    end_x, end_y = calculate_position(grid_index, self.columns, self.offset_x, self.offset_y)
                    smooth_move(win, start_x, start_y, end_x, end_y, duration=self.duration)
                self.status_update.emit(emulator_index, "✅ Done")
        except Exception as e:
            logging.exception("Error in worker thread")
            self.status_update.emit(emulator_index, f"❌ Error: {e}")
        self.finished.emit()
class Code_Full:
    def initUI(self):
        # Initial settings
        self.ldplayer_paths = load_ldplayer_paths(LDPLAYER_PATHS_FILE)
        self.duration = 2.5
        self.columns = 4
        self.offset_x = 350
        self.offset_y = 250
    
        # Create tabs
        self.tabs = QTabWidget()
        self.home_tab = QWidget()
        self.settings_tab = QWidget()
        self.system_tab = QWidget()
        self.tabs.addTab(self.home_tab, "MYHOME")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.system_tab, "System")
    
        # ------------------- HOME TAB -------------------
        self.setup_home_tab()
    
        # ----------------- SETTINGS TAB -----------------
        self.setup_settings_tab()
    
        # ------------------ SYSTEM TAB ------------------
        self.setup_system_tab()
    
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
    
        # Emulator options
        self.ld = None
        self.options = EmulatorOptions()
        self.options.set_resolution(width=250, height=400, dpi=120)
    
        # Load settings and UI appearance
        self.load_settings()
        self.refresh_paths_combo()
        self.apply_font_settings()
        self.apply_color_settings()
    
    def setup_home_tab(self):
        layout = QVBoxLayout()
    
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Emulator Name', 'Status'])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
    
        self.mode_label = QLabel("Arrangement Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Manual", "Auto"])
    
        self.status_label = QLabel("Select emulators and press Start.")
        self.ld_path_combo = QComboBox()
    
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
    
        self.load_button = QPushButton("🔍 Load Emulators")
        self.load_button.clicked.connect(self.load_emulators)
    
        self.start_button = QPushButton("🚀 Launch Selected Emulators")
        self.start_button.clicked.connect(self.start_selected_emulators)
    
        self.manual_arrange_button = QPushButton("📐 Arrange Windows")
        self.manual_arrange_button.clicked.connect(self.arrange_windows_manually)
    
        layout.addWidget(self.table)
    
        controls = QHBoxLayout()
        controls.addWidget(self.mode_label)
        controls.addWidget(self.mode_combo)
        controls.addWidget(self.status_label)
        layout.addLayout(controls)
    
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.ld_path_combo)
        path_layout.addWidget(self.browse_button)
        layout.addLayout(path_layout)
    
        buttons = QHBoxLayout()
        buttons.addWidget(self.load_button)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.manual_arrange_button)
        layout.addLayout(buttons)
    
        self.home_tab.setLayout(layout)
    
    def setup_settings_tab(self):
        layout = QVBoxLayout()
    
        self.font_combo = QComboBox()
        self.font_combo.addItems([
            "Times New Roman", "Courier New", "Khmer OS Moul", "Verdana", "Tahoma",
            "Georgia", "Comic Sans MS", "Impact", "Lucida Console", "Trebuchet MS"
        ])
        self.font_combo.currentTextChanged.connect(self.apply_font_settings)
    
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setPrefix("Size: ")
        self.font_size_spin.valueChanged.connect(self.apply_font_settings)
    
        self.font_color_combo = QComboBox()
        self.bg_color_combo = QComboBox()
        self.bg_panel_combo = QComboBox()
        self.sum_color_combo = QComboBox()
        color_options = [
            "black", "white", "red", "green", "blue", "yellow", "cyan", "magenta",
            "gray", "darkGray", "lightGray"
        ]
        for combo in [self.font_color_combo, self.bg_color_combo, self.bg_panel_combo, self.sum_color_combo]:
            combo.addItems(color_options)
        self.font_color_combo.setCurrentText("black")
        self.bg_color_combo.setCurrentText("white")
        self.bg_panel_combo.setCurrentText("lightGray")
        self.sum_color_combo.setCurrentText("blue")
    
        self.font_color_combo.currentTextChanged.connect(self.apply_color_settings)
        self.bg_color_combo.currentTextChanged.connect(self.apply_color_settings)
        self.bg_panel_combo.currentTextChanged.connect(self.apply_color_settings)
        self.sum_color_combo.currentTextChanged.connect(self.apply_color_settings)
    
        self.spin_columns = QSpinBox()
        self.spin_columns.setRange(1, 10)
        self.spin_columns.setValue(self.columns)
    
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(1, 10)
        self.spin_duration.setValue(int(self.duration))
        self.spin_duration.setSuffix(" sec")
    
        self.spin_offset_x = QSpinBox()
        self.spin_offset_x.setRange(100, 1000)
        self.spin_offset_x.setValue(self.offset_x)
    
        self.spin_offset_y = QSpinBox()
        self.spin_offset_y.setRange(100, 1000)
        self.spin_offset_y.setValue(self.offset_y)
    
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
    
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_settings)
    
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel("Font:"))
        style_layout.addWidget(self.font_combo)
        style_layout.addWidget(self.font_size_spin)
        style_layout.addWidget(QLabel("Font Color:"))
        style_layout.addWidget(self.font_color_combo)
        style_layout.addWidget(QLabel("Background:"))
        style_layout.addWidget(self.bg_color_combo)
    
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Panel Color:"))
        color_layout.addWidget(self.bg_panel_combo)
        color_layout.addWidget(QLabel("Status Color:"))
        color_layout.addWidget(self.sum_color_combo)
        color_layout.addWidget(self.save_btn)
        color_layout.addWidget(self.reset_btn)
    
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("Columns:"))
        config_layout.addWidget(self.spin_columns)
        config_layout.addWidget(QLabel("Duration:"))
        config_layout.addWidget(self.spin_duration)
        config_layout.addWidget(QLabel("Offset X:"))
        config_layout.addWidget(self.spin_offset_x)
        config_layout.addWidget(QLabel("Offset Y:"))
        config_layout.addWidget(self.spin_offset_y)
    
        layout.addLayout(style_layout)
        layout.addLayout(color_layout)
        layout.addLayout(config_layout)
    
        self.settings_tab.setLayout(layout)
    
    def setup_system_tab(self):
        layout = QVBoxLayout()
    
        self.stop_button = QPushButton("🚫 Stop All Emulators")
        self.stop_button.clicked.connect(self.stop_emulators)
    
        placeholder = QLabel("System controls will be added here.")
        placeholder.setStyleSheet("color: gray;")
    
        layout.addWidget(self.stop_button)
        layout.addWidget(placeholder)
        layout.addStretch()
    
        self.system_tab.setLayout(layout)
    

    def load_settings(self):
        # Load settings from JSON file if exists
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.font_combo.setCurrentText(config.get('font', 'Verdana'))
                    self.font_size_spin.setValue(config.get('font_size', 12))
                    self.font_color_combo.setCurrentText(config.get('font_color', 'black'))
                    self.bg_color_combo.setCurrentText(config.get('bg_color', 'white'))
                    self.bg_panel_combo.setCurrentText(config.get('panel_color', 'lightGray'))
                    self.sum_color_combo.setCurrentText(config.get('sum_color', 'blue'))
                    self.spin_columns.setValue(config.get('columns', 4))
                    self.spin_duration.setValue(config.get('duration', 2))
                    self.spin_offset_x.setValue(config.get('offset_x', 350))
                    self.spin_offset_y.setValue(config.get('offset_y', 250))
                    logging.info("Loaded settings from config.json")
            else:
                logging.info("No config.json found, using default settings")
        except Exception as e:
            self.status_label.setText(f"❌ Failed to load settings: {e}")
            logging.error(f"Failed to load settings: {e}")

    def save_settings(self):
        # Save current settings to JSON file
        try:
            config = {
                'font': self.font_combo.currentText(),
                'font_size': self.font_size_spin.value(),
                'font_color': self.font_color_combo.currentText(),
                'bg_color': self.bg_color_combo.currentText(),
                'panel_color': self.bg_panel_combo.currentText(),
                'sum_color': self.sum_color_combo.currentText(),
                'columns': self.spin_columns.value(),
                'duration': self.spin_duration.value(),
                'offset_x': self.spin_offset_x.value(),
                'offset_y': self.spin_offset_y.value()
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            self.status_label.setText("✅ Settings saved.")
            logging.info("Saved settings to config.json")
        except Exception as e:
            self.status_label.setText(f"❌ Failed to save settings: {e}")
            logging.error(f"Failed to save settings: {e}")

    def reset_settings(self):
        # Reset to default settings
        self.font_combo.setCurrentText("Verdana")
        self.font_size_spin.setValue(12)
        self.font_color_combo.setCurrentText("black")
        self.bg_color_combo.setCurrentText("white")
        self.bg_panel_combo.setCurrentText("lightGray")
        self.sum_color_combo.setCurrentText("blue")
        self.spin_columns.setValue(4)
        self.spin_duration.setValue(2)
        self.spin_offset_x.setValue(350)
        self.spin_offset_y.setValue(250)
        self.apply_font_settings()
        self.apply_color_settings()
        self.status_label.setText("🔄 Settings reset to defaults.")
        logging.info("Reset settings to defaults")

    def refresh_paths_combo(self):
        self.ld_path_combo.clear()
        for label, path in self.ldplayer_paths.items():
            self.ld_path_combo.addItem(label, path)
        self.load_button.setEnabled(self.ld_path_combo.count() > 0)

    def apply_font_settings(self):
        font_name = self.font_combo.currentText()
        font_size = self.font_size_spin.value()
        font = QFont(font_name, font_size)

        # Apply font to relevant widgets
        self.setFont(font)
        self.table.setFont(font)
        self.mode_label.setFont(font)
        self.mode_combo.setFont(font)
        self.status_label.setFont(font)
        self.ld_path_combo.setFont(font)
        self.browse_button.setFont(font)
        self.load_button.setFont(font)
        self.start_button.setFont(font)
        self.manual_arrange_button.setFont(font)
        self.stop_button.setFont(font)
        self.save_btn.setFont(font)
        self.reset_btn.setFont(font)
        self.font_combo.setFont(font)
        self.font_size_spin.setFont(font)
        self.font_color_combo.setFont(font)
        self.bg_color_combo.setFont(font)
        self.bg_panel_combo.setFont(font)
        self.sum_color_combo.setFont(font)
        self.spin_columns.setFont(font)
        self.spin_duration.setFont(font)
        self.spin_offset_x.setFont(font)
        self.spin_offset_y.setFont(font)

    def apply_color_settings(self):
        font_color = self.font_color_combo.currentText()
        bg_color = self.bg_color_combo.currentText()
        panel_color = self.bg_panel_combo.currentText()
        sum_color = self.sum_color_combo.currentText()

        # Apply font color to text-based widgets
        font_style = f"color: {font_color};"
        self.mode_label.setStyleSheet(font_style)
        self.status_label.setStyleSheet(font_style + f"background-color: {sum_color};")
        self.table.setStyleSheet(f"QTableWidget {{ color: {font_color}; background-color: {panel_color}; }}")
        self.mode_combo.setStyleSheet(font_style)
        self.ld_path_combo.setStyleSheet(font_style)
        self.font_combo.setStyleSheet(font_style)
        self.font_color_combo.setStyleSheet(font_style)
        self.bg_color_combo.setStyleSheet(font_style)
        self.bg_panel_combo.setStyleSheet(font_style)
        self.sum_color_combo.setStyleSheet(font_style)
        self.spin_columns.setStyleSheet(font_style)
        self.spin_duration.setStyleSheet(font_style)
        self.spin_offset_x.setStyleSheet(font_style)
        self.spin_offset_y.setStyleSheet(font_style)

        # Apply background color to buttons and main window
        button_style = f"color: {font_color}; background-color: {bg_color};"
        self.browse_button.setStyleSheet(button_style)
        self.load_button.setStyleSheet(button_style)
        self.start_button.setStyleSheet(button_style)
        self.manual_arrange_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(button_style)
        self.save_btn.setStyleSheet(button_style)
        self.reset_btn.setStyleSheet(button_style)
        self.setStyleSheet(f"QWidget {{ background-color: {bg_color}; }}")

    def stop_emulators(self):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if ('LDPlayer' in proc.info['name']) or (proc.info['name'] in ['dnplayer.exe', 'dnplayer2.exe']):
                        proc.kill()
                        print(f"💀 Killed process: {proc.info['pid']} - {proc.info['name']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.status_label.setText("🛑 All emulators stopped.")
        except ImportError:
            self.status_label.setText("❌ psutil module not installed.")
            logging.error("psutil module not installed for stop_emulators")

    def save_ldplayer_path(self, path):
        if os.path.exists(path) and os.path.exists(os.path.join(path, 'ldconsole.exe')):
            label = f"LDPlayer Path {len(self.ldplayer_paths) + 1}"
            self.ldplayer_paths[label] = path
            with open(LDPLAYER_PATHS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{path}\n")
            self.refresh_paths_combo()
            logging.info(f"Saved LDPlayer path: {path}")
        else:
            self.status_label.setText("❌ Selected path is not a valid LDPlayer installation.")
            logging.warning(f"Invalid LDPlayer path not saved: {path}")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select LDPlayer Folder", "")
        if folder:
            if folder not in [self.ld_path_combo.itemData(i) for i in range(self.ld_path_combo.count())]:
                self.save_ldplayer_path(folder)
            self.ld_path_combo.setCurrentIndex(self.ld_path_combo.findData(folder))

    def load_emulators(self):
        selected_path = self.ld_path_combo.currentData()
        if not selected_path or not os.path.exists(selected_path) or not os.path.exists(os.path.join(selected_path, 'ldconsole.exe')):
            self.status_label.setText("❌ Invalid LDPlayer path selected. Ensure it contains ldconsole.exe.")
            logging.error("Invalid LDPlayer path: %s", selected_path)
            return
        try:
            self.ld = emulator.LDPlayer(ldplayer_dir=selected_path)
            self.table.setRowCount(len(self.ld.emulators))
            for i, em in enumerate(self.ld.emulators):
                em.setting(self.options)
                self.table.setItem(i, 0, QTableWidgetItem(em.name))
                self.table.setItem(i, 1, QTableWidgetItem("Not Started"))
                logging.info(f"Loaded emulator: {em.name}")
            self.status_label.setText("✅ Emulators loaded successfully.")
        except Exception as e:
            self.status_label.setText(f"❌ Failed to load emulators: {e}")
            logging.exception("Failed to load emulators")

    def start_selected_emulators(self):
        selected_items = self.table.selectedItems()
        selected_rows = sorted({item.row() for item in selected_items})
        if not selected_rows:
            self.status_label.setText("❌ No emulator selected.")
            return

        self.columns = self.spin_columns.value()
        self.offset_x = self.spin_offset_x.value()
        self.offset_y = self.spin_offset_y.value()
        self.duration = self.spin_duration.value()

        auto_mode = self.mode_combo.currentText() == "Auto"
        self.start_button.setEnabled(False)
        self.thread = QThread()
        self.worker = Worker(self.ld, selected_rows, auto_arrange=auto_mode,
                            columns=self.columns, offset_x=self.offset_x,
                            offset_y=self.offset_y, duration=self.duration)
        self.worker.moveToThread(self.thread)
        self.worker.status_update.connect(self.update_status)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(lambda: self.status_label.setText("✅ All done!"))
        self.worker.finished.connect(lambda: self.start_button.setEnabled(True))
        self.thread.started.connect(self.worker.run)
        self.thread.start()
        self.status_label.setText("⏳ Running...")

    def arrange_windows_manually(self):
        selected_items = self.table.selectedItems()
        selected_rows = sorted({item.row() for item in selected_items})
        if not selected_rows:
            self.status_label.setText("❌ No emulator selected.")
            return

        self.columns = self.spin_columns.value()
        self.offset_x = self.spin_offset_x.value()
        self.offset_y = self.spin_offset_y.value()
        self.duration = self.spin_duration.value()

        for grid_index, row in enumerate(selected_rows):
            em = self.ld.emulators[row]
            win = find_emulator_window(em.name)
            if win:
                start_x, start_y = win.topleft
                end_x, end_y = calculate_position(grid_index, self.columns, self.offset_x, self.offset_y)
                smooth_move(win, start_x, start_y, end_x, end_y, duration=self.duration)
                self.update_status(row, "✅ Arranged")
            else:
                self.update_status(row, "❌ Window not found")
                logging.warning(f"Window not found for emulator: {em.name}")

    def update_status(self, row, status_text):
        self.table.setItem(row, 1, QTableWidgetItem(status_text))
class MainApp(QWidget,Code_Full):



    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emulator Launcher & Mover")
        self.setGeometry(100, 100, 700, 500)

        self.initUI()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
