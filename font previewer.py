import sys
import os
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from functools import partial

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QScrollArea, QLabel,
    QPushButton, QLineEdit, QFileDialog, QProgressDialog, QSpinBox,
    QHBoxLayout, QMenu, QToolButton, QFrame, QMessageBox
)
from PySide6.QtGui import QFont, QFontDatabase, QAction, QIcon
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtWidgets import QScroller

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('font_previewer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class FontPreviewConfig:
    """Configuration settings for font preview"""
    default_text: str = "Hello مرحبا"
    default_size: int = 24
    min_size: int = 6
    max_size: int = 96
    chunk_size: int = 10
    window_size: tuple = (800, 600)

class ThreadBase(QThread):
    """Base class for all worker threads"""
    def __init__(self):
        super().__init__()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

class FontLoadingThread(ThreadBase):
    """Thread for loading system fonts"""
    finished = Signal(list)

    def run(self):
        try:
            fonts = QFontDatabase.families()
            if not self._is_cancelled:
                self.finished.emit(fonts)
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")
            self.finished.emit([])

class FontFolderLoadingThread(ThreadBase):
    """Thread for loading fonts from a specified folder"""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path
    
    def run(self):
        try:
            loaded_fonts = []
            font_path = Path(self.folder_path)
            
            if not font_path.exists():
                self.error.emit("Specified folder does not exist")
                return

            for file in font_path.glob("*.[tToOfF][tToOfF][fFnN]"):
                if self._is_cancelled:
                    break
                    
                font_id = QFontDatabase.addApplicationFont(str(file))
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    loaded_fonts.extend(families)
                else:
                    logger.warning(f"Failed to load font: {file}")
            
            self.finished.emit(loaded_fonts)
        except Exception as e:
            logger.error(f"Error loading fonts from folder: {e}")
            self.error.emit(str(e))

class PreviewUpdateThread(ThreadBase):
    """Thread for updating font previews"""
    font_processed = Signal(str, str, int)
    finished = Signal()

    def __init__(self, fonts: List[str], preview_text: str, chunk_size: int = 10):
        super().__init__()
        self.fonts = fonts
        self.preview_text = preview_text
        self.chunk_size = chunk_size

    def run(self):
        try:
            for i in range(0, len(self.fonts), self.chunk_size):
                if self._is_cancelled:
                    break
                
                chunk = self.fonts[i:i + self.chunk_size]
                for font_name in chunk:
                    if self._is_cancelled:
                        break
                    self.font_processed.emit(font_name, self.preview_text, i)
                
                self.msleep(10)  # Prevent GUI freezing
            
            self.finished.emit()
        except Exception as e:
            logger.error(f"Error updating previews: {e}")
            self.finished.emit()

class FontPreviewContainer(QFrame):
    """Custom widget for displaying font previews"""
    def __init__(self, font_name: str, preview_text: str, font_size: int, parent=None):
        super().__init__(parent)
        self.setup_ui(font_name, preview_text, font_size)
        
    def setup_ui(self, font_name: str, preview_text: str, font_size: int):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            FontPreviewContainer {
                padding: 5px;
                border-radius: 3px;
                border: none;
            }
            FontPreviewContainer:hover {
                background-color: #505050;
            }
            FontPreviewContainer[selected="true"] {
                background-color: #cce8ff;
                border: 1px solid #fff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)

        # Font name label
        self.name_label = QLabel(font_name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.name_label)

        # Preview label
        self.preview_label = QLabel(preview_text)
        font = QFont(font_name, font_size)
        self.preview_label.setFont(font)
        
        # Handle RTL text
        if any(ord(char) in range(0x0600, 0x06FF) for char in preview_text):
            self.preview_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        layout.addWidget(self.preview_label)

class FontPreviewer(QMainWindow):
    """Main application window"""
    def __init__(self, config: FontPreviewConfig = FontPreviewConfig()):
        super().__init__()
        self.config = config
        self.setup_ui()
        self.load_system_fonts()

    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Font Previewer")
        self.setMinimumSize(*self.config.window_size)
        
        try:
            self.setWindowIcon(QIcon(self.get_resource_path("Icon.ico")))
        except Exception as e:
            logger.warning(f"Failed to load window icon: {e}")

        # Main layout setup
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        
        self.setup_control_panel()
        self.setup_scroll_area()
        self.setup_status_area()

    def setup_control_panel(self):
        """Set up the control panel with input fields and buttons"""
        control_layout = QHBoxLayout()
        self.main_layout.addLayout(control_layout)

        # Text input
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text to preview...")
        self.text_input.setText(self.config.default_text)
        control_layout.addWidget(self.text_input)

        # Font size input
        self.size_input = QSpinBox()
        self.size_input.setRange(self.config.min_size, self.config.max_size)
        self.size_input.setValue(self.config.default_size)
        self.size_input.setPrefix("Size: ")
        self.size_input.setSuffix("pt")
        self.size_input.setFixedWidth(120)
        control_layout.addWidget(self.size_input)

        # Search functionality
        self.setup_search_widgets(control_layout)

        # Load fonts button
        load_button = QPushButton("Load Fonts from Folder")
        load_button.clicked.connect(self.load_fonts_from_folder)
        self.main_layout.addWidget(load_button)

    def setup_scroll_area(self):
        """Set up the scrollable area for font previews"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # Enable smooth scrolling
        QScroller.grabGesture(
            self.scroll_area.viewport(),
            QScroller.ScrollerGestureType.TouchGesture
        )
        QScroller.grabGesture(
            self.scroll_area.viewport(),
            QScroller.ScrollerGestureType.LeftMouseButtonGesture
        )

    def setup_status_area(self):
        """Set up the status area for loading messages and update button"""
        self.loading_label = QLabel("Loading fonts...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.loading_label)

        self.update_button = QPushButton("Update Preview")
        self.update_button.clicked.connect(self.start_update_previews)
        self.main_layout.addWidget(self.update_button)

    def setup_search_widgets(self, parent_layout: QHBoxLayout):
        """Set up search-related widgets"""
        self.search_button = QToolButton()
        try:
            self.search_button.setIcon(QIcon(self.get_resource_path("search.png")))
        except Exception as e:
            logger.warning(f"Failed to load search icon: {e}")
            self.search_button.setText("🔍")

        self.search_button.clicked.connect(self.toggle_search)
        parent_layout.addWidget(self.search_button)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search fonts...")
        self.search_input.returnPressed.connect(self.filter_fonts)
        self.search_input.hide()
        parent_layout.addWidget(self.search_input)

    def load_system_fonts(self):
        """Start loading system fonts"""
        self.load_fonts_thread = FontLoadingThread()
        self.load_fonts_thread.finished.connect(self.on_fonts_loaded)
        self.load_fonts_thread.start()

    def on_fonts_loaded(self, fonts: List[str]):
        """Handle completion of font loading"""
        self.fonts = fonts
        self.all_fonts = fonts.copy()
        self.loading_label.hide()
        self.start_update_previews()

    def load_fonts_from_folder(self):
        """Handle loading fonts from a selected folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        self.loading_label.setText("Loading fonts from folder...")
        self.loading_label.show()
        
        self.folder_loading_thread = FontFolderLoadingThread(folder)
        self.folder_loading_thread.finished.connect(self.on_folder_fonts_loaded)
        self.folder_loading_thread.error.connect(self.show_error_message)
        self.folder_loading_thread.start()

    def on_folder_fonts_loaded(self, new_fonts: List[str]):
        """Handle completion of folder font loading"""
        self.fonts = new_fonts
        self.all_fonts = new_fonts.copy()
        self.loading_label.hide()
        self.start_update_previews()

    def start_update_previews(self):
        """Begin updating font previews"""
        preview_text = self.text_input.text() or self.config.default_text
        self.clear_previews()
        
        self.setup_progress_dialog()
        
        self.update_thread = PreviewUpdateThread(
            self.fonts,
            preview_text,
            self.config.chunk_size
        )
        self.update_thread.font_processed.connect(self.add_font_preview)
        self.update_thread.finished.connect(self.update_finished)
        self.update_thread.start()

    def setup_progress_dialog(self):
        """Set up the progress dialog for preview updates"""
        self.progress_dialog = QProgressDialog(
            "Updating previews...", 
            "Cancel", 
            0, 
            len(self.fonts), 
            self
        )
        self.progress_dialog.setWindowTitle("Updating Previews")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.canceled.connect(self.cancel_update)

    def clear_previews(self):
        """Clear existing font previews"""
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def add_font_preview(self, font_name: str, preview_text: str, progress: int):
        """Add a new font preview to the scroll area"""
        if self.progress_dialog:
            self.progress_dialog.setValue(progress)

        container = FontPreviewContainer(
            font_name,
            preview_text,
            self.size_input.value(),
            self
        )
        self.add_context_menu(container, font_name)
        
        self.scroll_layout.addWidget(container)
        
        # Add spacing
        spacer = QLabel()
        spacer.setFixedHeight(10)
        self.scroll_layout.addWidget(spacer)

    def add_context_menu(self, widget: QWidget, font_name: str):
        """Add context menu to a widget"""
        def show_context_menu(point):
            context_menu = QMenu(self)
            copy_action = QAction("Copy Font Name", self)
            copy_action.triggered.connect(
                lambda: QApplication.clipboard().setText(font_name)
            )
            context_menu.addAction(copy_action)
            context_menu.exec(widget.mapToGlobal(point))

        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(show_context_menu)

    def cancel_update(self):
        """Cancel the current preview update operation"""
        if self.update_thread:
            self.update_thread.cancel()

    def update_finished(self):
        """Handle completion of preview updates"""
        if self.progress_dialog:
            self.progress_dialog.close()
        self.update_thread = None
        self.progress_dialog = None

    def toggle_search(self):
        """Toggle search functionality"""
        if self.search_input.isHidden():
            self.search_input.show()
            try:
                self.search_button.setIcon(QIcon(self.get_resource_path("x.png")))
            except Exception as e:
                logger.warning(f"Failed to load close icon: {e}")
                self.search_button.setText("✕")
            self.search_input.setFocus()
        else:
            self.search_input.hide()
            self.search_input.clear()
            try:
                self.search_button.setIcon(QIcon(self.get_resource_path("search.png")))
            except Exception as e:
                logger.warning(f"Failed to load search icon: {e}")
                self.search_button.setText("🔍")
            self.fonts = self.all_fonts.copy()
            self.start_update_previews()

    def filter_fonts(self):
        """Filter fonts based on search text"""
        search_text = self.search_input.text().lower()
        if search_text:
            self.fonts = [
                font for font in self.all_fonts 
                if search_text in font.lower()
            ]
        else:
            self.fonts = self.all_fonts.copy()
        self.start_update_previews()

    def show_error_message(self, message: str):
        """Show error message to user"""
        QMessageBox.critical(self, "Error", message)

    @staticmethod
    def get_resource_path(resource_name: str) -> str:
        """Get the absolute path to a resource file"""
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(base_path, 'resources', resource_name)
        except Exception as e:
            logger.error(f"Error getting resource path: {e}")
            return resource_name

def main():
    """Main entry point of the application"""
    try:
        app = QApplication(sys.argv)
        
        # Apply any global application settings
        app.setOrganizationName("YourOrganization")
        app.setApplicationName("Font Previewer")
        
        # Create and show the main window
        window = FontPreviewer()
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()