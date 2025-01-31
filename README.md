<p align="center">
  <img src="https://i.ibb.co/6HHkKWR/Font-Previewer-Icon.png" />
</p>

# Font Previewer
A modern, user-friendly desktop application for previewing and choosing fonts, built with PySide6 (Qt).

![image](https://i.ibb.co/M2wY20L/Font-Previewer.png)
<p align="center">
  <a href="https://github.com/Creative-Geek/Font-Previewer/releases/download/v1.0.0/Font.Previewer.exe">  <img src="https://i.ibb.co/5rqVygb/Download-Button.png" />
  </a>
</p>

## Features

- Preview system fonts and custom font files
- Support for RTL (Right-to-Left) text
- Search functionality to filter fonts
- Smooth scrolling interface (using gestures)
- Context menu for copying font names
- Support for loading fonts from custom folders

## Requirements

- Python 3.6+
- PySide6

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Font-Previewer.git
cd Font-Previewer
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application using:
```bash
python "font previewer.py"
```

### Basic Operations

- **Preview Text**: Enter custom text in the input field at the top
- **Font Size**: Adjust using the size spinner (6pt - 96pt)
- **Search**: Click the search icon to filter fonts by name
- **Custom Fonts**: Click "Load Fonts from Folder" to load additional font files
- **Font Name**: Right-click on any font preview to copy the font name

## Features in Detail

### System Fonts
- Automatically loads and displays all system fonts on startup
- Presents fonts in a scrollable interface

### Custom Font Loading
- Supports loading fonts from custom folders
- Compatible with common font formats (TTF, OTF)

### Preview Customization
- Real-time preview text updates
- Adjustable font size with range validation
- Support for both LTR and RTL text direction

### Search and Filter
- Font filtering based on search input
- Press Enter to filter the current list
- Clear search option to reset to full font list

## Technical Details

- Built with PySide6 (Qt for Python)
- Implements multi-threading for smooth performance
- Modular design with separate thread classes for different operations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the LICENSE file included in the repository.
