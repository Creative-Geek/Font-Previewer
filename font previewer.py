import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QScrollArea, QLabel, QPushButton, QLineEdit, QFileDialog,
                               QProgressDialog, QSpinBox, QHBoxLayout, QMenu)
from PySide6.QtGui import QFont, QFontDatabase, QAction
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QScroller
from PySide6.QtWidgets import QFrame

class PreviewUpdateThread(QThread):
    font_processed = Signal(str, str, int)
    finished = Signal()

    def __init__(self, fonts, preview_text):
        super().__init__()
        self.fonts = fonts
        self.preview_text = preview_text
        self.is_cancelled = False

    def run(self):
        for i, font_name in enumerate(self.fonts):
            if self.is_cancelled:
                break
            self.font_processed.emit(font_name, self.preview_text, i)
        self.finished.emit()

class FontPreviewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Font Previewer")
        self.setMinimumSize(800, 600)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create horizontal layout for input fields
        input_layout = QHBoxLayout()
        layout.addLayout(input_layout)

        # Create input field for preview text
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text to preview...")
        self.text_input.setText("Hello مرحبا")  # Default text with both LTR and RTL
        input_layout.addWidget(self.text_input)

        # Create input field for font size
        self.size_input = QSpinBox()
        self.size_input.setMinimum(6)
        self.size_input.setMaximum(96)
        self.size_input.setValue(24)  # Default size
        self.size_input.setPrefix("Size: ")
        self.size_input.setSuffix("pt")
        input_layout.addWidget(self.size_input)

        # Adjust size input width
        self.size_input.setFixedWidth(120)

        # Create load fonts button
        load_button = QPushButton("Load Fonts from Folder")
        load_button.clicked.connect(self.load_fonts_from_folder)
        layout.addWidget(load_button)

        # Create scroll area for font previews
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)

        # Enable smooth scrolling
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        # Load system fonts
        self.load_system_fonts()
        self.update_previews()

        # Add update button
        update_button = QPushButton("Update Preview")
        update_button.clicked.connect(self.start_update_previews)
        layout.addWidget(update_button)

        self.progress_dialog = None
        self.update_thread = None

    def load_system_fonts(self):
        self.fonts = []
        self.fonts = QFontDatabase.families()

    def load_fonts_from_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            for file in os.listdir(folder):
                if file.lower().endswith(('.ttf', '.otf', '.fon')):
                    font_path = os.path.join(folder, file)
                    QFontDatabase.addApplicationFont(font_path)
            
            # Reload fonts and update preview
            self.load_system_fonts()
            self.update_previews()

    def start_update_previews(self):
        preview_text = self.text_input.text()
        if not preview_text:
            preview_text = "Hello مرحبا"

        # Clear existing previews
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create and show progress dialog
        self.progress_dialog = QProgressDialog("Updating previews...", "Cancel", 0, len(self.fonts), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.canceled.connect(self.cancel_update)

        # Create and start update thread
        self.update_thread = PreviewUpdateThread(self.fonts, preview_text)
        self.update_thread.font_processed.connect(self.add_font_preview)
        self.update_thread.finished.connect(self.update_finished)
        self.update_thread.start()

    def cancel_update(self):
        if self.update_thread:
            self.update_thread.is_cancelled = True

    def update_finished(self):
        if self.progress_dialog:
            self.progress_dialog.close()
        self.update_thread = None
        self.progress_dialog = None

    def add_font_preview(self, font_name, preview_text, progress):
        # Update progress
        if self.progress_dialog:
            self.progress_dialog.setValue(progress)

        # Create a container frame for the font item
        container = QFrame()
        container.setFrameShape(QFrame.Shape.StyledPanel)
        container.setStyleSheet("""
            QFrame {
                padding: 5px;
                border-radius: 3px;
                border: none;
            }
            QFrame:hover {
                background-color: #505050;
            }
            QFrame[selected="true"] {
                background-color: #cce8ff;
                border: 1px solid #fff;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(2)
        container_layout.setContentsMargins(5, 5, 5, 5)

        # Font name label
        name_label = QLabel(font_name)
        name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        container_layout.addWidget(name_label)

        # Preview label
        preview_label = QLabel(preview_text)
        font = QFont(font_name, self.size_input.value())
        preview_label.setFont(font)
        
        # Handle RTL text
        if any(ord(char) in range(0x0600, 0x06FF) for char in preview_text):
            preview_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        container_layout.addWidget(preview_label)

        # Add click handling
        # container.mousePressEvent = lambda e: self.handle_font_selection(container)
        
        # Add context menu to both labels
        self.add_context_menu(container, font_name)

        self.scroll_layout.addWidget(container)

        # Add spacing
        spacer = QLabel()
        spacer.setFixedHeight(10)
        self.scroll_layout.addWidget(spacer)
    def handle_font_selection(self, container):
        # Deselect all other containers
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, QFrame):
                widget.setProperty("selected", False)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
        
        # Select the clicked container
        container.setProperty("selected", True)
        container.style().unpolish(container)
        container.style().polish(container)

    def add_context_menu(self, widget, font_name):
        def show_context_menu(point):
            context_menu = QMenu(self)
            copy_action = QAction("Copy Font Name", self)
            copy_action.triggered.connect(lambda: QApplication.clipboard().setText(font_name))
            context_menu.addAction(copy_action)
            context_menu.exec(widget.mapToGlobal(point))

        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(show_context_menu)
    def update_previews(self):
        # This method is now deprecated but kept for reference
        pass
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FontPreviewer()
    window.show()
    sys.exit(app.exec())
