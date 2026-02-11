from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
from pathlib import Path
import html
from src.config.settings import CANDLE_PATTERNS
from src.utils.logger import get_logger

logger = get_logger('app')


class PatternImageDisplay(QWidget):
    """Widget to display pattern images"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pattern_name = ""
        self.image_path = None
        self.setMinimumHeight(250)
        self.setMinimumWidth(500)

    def set_pattern(self, pattern_name: str):
        """Set pattern to display"""
        self.pattern_name = pattern_name
        self.image_path = self.find_pattern_image(pattern_name)
        self.update()

    def find_pattern_image(self, pattern_name: str) -> Path:
        """Find image for the pattern"""
        # Define possible image directories
        image_dirs = [
            Path(__file__).parent.parent.parent / 'data' / 'patterns_images',
            Path(__file__).parent.parent / 'data' / 'patterns_images',
            Path('data/patterns_images'),
            Path('patterns_images')
        ]

        # Define possible image extensions
        extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']

        for image_dir in image_dirs:
            if image_dir.exists():
                for ext in extensions:
                    image_path = image_dir / f"{self.pattern_name}{ext}"
                    if image_path.exists():
                        return image_path

        return None

    def paintEvent(self, event):
        """Display pattern image or placeholder"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Clear background
        painter.fillRect(self.rect(), QColor(240, 240, 240))

        if not self.pattern_name:
            # Draw empty state
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "Select a pattern to see image")
            return

        if self.image_path and self.image_path.exists():
            try:
                # Load and display image
                pixmap = QPixmap(str(self.image_path))

                # Scale image to fit widget while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.width() - 40,
                    self.height() - 40,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                # Calculate position to center the image
                x = (self.width() - scaled_pixmap.width()) // 2
                y = (self.height() - scaled_pixmap.height()) // 2

                painter.drawPixmap(x, y, scaled_pixmap)

            except Exception as e:
                logger.error(f"Error loading image {self.image_path}: {str(e)}")
                self.draw_placeholder(painter, f"Error loading image: {str(e)}")
        else:
            # Draw placeholder if no image found
            self.draw_placeholder(painter, f"No image found for: {self.pattern_name}")

    def draw_placeholder(self, painter, message: str):
        """Draw placeholder when no image is available"""
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", 10))

        # Draw placeholder box
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawRect(20, 20, self.width() - 40, self.height() - 40)

        # Draw pattern name
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(self.rect().adjusted(0, 50, 0, 0), Qt.AlignCenter, self.pattern_name)

        # Draw message
        painter.setPen(QColor(100, 100, 100))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(self.rect().adjusted(0, 100, 0, 0), Qt.AlignCenter, message)

        # Draw instruction
        painter.setPen(QColor(50, 100, 200))
        painter.setFont(QFont("Arial", 9))
        instruction = "Place pattern image in data/patterns_images/ folder"
        painter.drawText(self.rect().adjusted(0, 150, 0, 0), Qt.AlignCenter, instruction)


class LanguageManager:
    """Manages language loading and switching"""

    def __init__(self):
        self.languages_dir = Path(__file__).parent.parent / 'data' / 'languages'
        self.languages_dir.mkdir(parents=True, exist_ok=True)
        self.current_language = "english"
        self.translations = {}
        self.available_languages = ["english", "russian", "spanish"]
        self.load_all_languages()

    def load_all_languages(self):
        """Load all language files"""
        for lang in self.available_languages:
            file_path = self.languages_dir / f"{lang}.json"
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang] = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading {lang} language: {str(e)}")
                    self.translations[lang] = {}
            else:
                logger.warning(f"Language file not found: {file_path}")
                self.translations[lang] = {}

    def get_text(self, key: str, lang: str = None) -> str:
        """Get translated text for a key"""
        if lang is None:
            lang = self.current_language

        # Try to get from current language
        if lang in self.translations:
            # Handle nested keys (e.g., "patterns.CDL2CROWS.description")
            keys = key.split('.')
            value = self.translations[lang]

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    # Fallback to English if key not found
                    if lang != "english":
                        return self.get_text(key, "english")
                    return key  # Return key itself as last resort

            # Ensure we return string, convert if needed
            if isinstance(value, (int, float)):
                return str(value)
            return value if value is not None else key

        # Fallback to English
        if lang != "english":
            return self.get_text(key, "english")

        return key

    def set_language(self, lang: str):
        """Set current language"""
        if lang in self.available_languages:
            self.current_language = lang
            return True
        return False

    def get_pattern_info(self, pattern_name: str) -> dict:
        """Get pattern information in current language"""
        base_info = {
            'description': self.get_text(f"patterns.{pattern_name}.description"),
            'interpretation': self.get_text(f"patterns.{pattern_name}.interpretation"),
            'reliability': self.get_text(f"patterns.{pattern_name}.reliability"),
            'category': self.get_text(f"patterns.{pattern_name}.category"),
            'type': self.get_text(f"patterns.{pattern_name}.type"),
            'direction': self.get_text(f"patterns.{pattern_name}.direction")
        }

        # Parse components as integer
        components_str = self.get_text(f"patterns.{pattern_name}.components")
        try:
            base_info['components'] = int(components_str)
        except (ValueError, TypeError):
            base_info['components'] = 1  # Default to 1 if cannot parse

        return base_info


class HelpWindow(QMainWindow):
    """Comprehensive help window with multi-language support and image display"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.language_manager = LanguageManager()
        self.setWindowTitle(self.language_manager.get_text("help_title"))
        self.setGeometry(150, 150, 1400, 900)

        # Store references to UI elements for easy updating
        self.ui_elements = {}

        self.init_ui()

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Left panel - Navigation
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Language selection buttons
        lang_layout = QHBoxLayout()

        # Language buttons with flags
        self.english_btn = QPushButton("🇺🇸 English")
        self.english_btn.setCheckable(True)
        self.english_btn.setChecked(True)
        self.english_btn.clicked.connect(lambda: self.change_language("english"))
        lang_layout.addWidget(self.english_btn)

        self.russian_btn = QPushButton("🇷🇺 Русский")
        self.russian_btn.setCheckable(True)
        self.russian_btn.clicked.connect(lambda: self.change_language("russian"))
        lang_layout.addWidget(self.russian_btn)

        self.spanish_btn = QPushButton("🇪🇸 Español")
        self.spanish_btn.setCheckable(True)
        self.spanish_btn.clicked.connect(lambda: self.change_language("spanish"))
        lang_layout.addWidget(self.spanish_btn)

        left_layout.addLayout(lang_layout)

        # Search box
        search_layout = QHBoxLayout()
        self.search_label = QLabel(self.language_manager.get_text("search_label"))
        search_layout.addWidget(self.search_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(self.language_manager.get_text("search_placeholder"))
        self.search_box.textChanged.connect(self.filter_patterns)
        search_layout.addWidget(self.search_box)

        left_layout.addLayout(search_layout)

        # Pattern list
        self.pattern_list = QListWidget()
        self.pattern_list.addItems(CANDLE_PATTERNS)
        self.pattern_list.itemSelectionChanged.connect(self.show_pattern_details)
        left_layout.addWidget(self.pattern_list)

        # Application help button
        self.app_help_btn = QPushButton(self.language_manager.get_text("application_help"))
        self.app_help_btn.clicked.connect(self.show_application_help)
        left_layout.addWidget(self.app_help_btn)

        left_layout.addStretch()

        # Right panel - Details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Title
        self.pattern_title = QLabel(self.language_manager.get_text("select_pattern"))
        self.pattern_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.pattern_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.pattern_title)

        # Pattern image display
        self.pattern_image = PatternImageDisplay()
        right_layout.addWidget(self.pattern_image)

        # Description text area
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setFont(QFont("Arial", 10))
        right_layout.addWidget(self.description_text)

        # Interpretation
        self.interpretation_label = QLabel(self.language_manager.get_text("interpretation"))
        self.interpretation_label.setStyleSheet("font-weight: bold; color: #555;")
        right_layout.addWidget(self.interpretation_label)

        self.interpretation_text = QTextEdit()
        self.interpretation_text.setReadOnly(True)
        self.interpretation_text.setMaximumHeight(100)
        right_layout.addWidget(self.interpretation_text)

        # Reliability and usage
        info_layout = QHBoxLayout()

        # Reliability
        self.reliability_group = QGroupBox(self.language_manager.get_text("reliability"))
        reliability_layout = QVBoxLayout()
        self.reliability_label = QLabel("N/A")
        self.reliability_label.setStyleSheet("font-size: 14px;")
        reliability_layout.addWidget(self.reliability_label)
        self.reliability_group.setLayout(reliability_layout)
        info_layout.addWidget(self.reliability_group)

        # Category
        self.category_group = QGroupBox(self.language_manager.get_text("category"))
        category_layout = QVBoxLayout()
        self.category_label = QLabel("N/A")
        self.category_label.setStyleSheet("font-size: 14px;")
        category_layout.addWidget(self.category_label)
        self.category_group.setLayout(category_layout)
        info_layout.addWidget(self.category_group)

        # Pattern Type
        self.type_group = QGroupBox(self.language_manager.get_text("type"))
        type_layout = QVBoxLayout()
        self.type_label = QLabel("N/A")
        self.type_label.setStyleSheet("font-size: 14px;")
        type_layout.addWidget(self.type_label)
        self.type_group.setLayout(type_layout)
        info_layout.addWidget(self.type_group)

        # Bullish/Bearish
        self.direction_group = QGroupBox(self.language_manager.get_text("direction"))
        direction_layout = QVBoxLayout()
        self.direction_label = QLabel("N/A")
        self.direction_label.setStyleSheet("font-size: 14px;")
        direction_layout.addWidget(self.direction_label)
        self.direction_group.setLayout(direction_layout)
        info_layout.addWidget(self.direction_group)

        right_layout.addLayout(info_layout)

        # Add panels to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 1100])

        layout.addWidget(splitter)

        # Store references for easy updating
        self.store_ui_references()

        # Select first pattern
        if self.pattern_list.count() > 0:
            self.pattern_list.setCurrentRow(0)

    def store_ui_references(self):
        """Store references to UI elements that need language updates"""
        self.ui_elements = {
            'search_label': self.search_label,
            'search_box': self.search_box,
            'app_help_btn': self.app_help_btn,
            'pattern_title': self.pattern_title,
            'interpretation_label': self.interpretation_label,
            'reliability_group': self.reliability_group,
            'category_group': self.category_group,
            'type_group': self.type_group,
            'direction_group': self.direction_group
        }

    def change_language(self, lang: str):
        """Change application language"""
        if self.language_manager.set_language(lang):
            # Update window title
            self.setWindowTitle(self.language_manager.get_text("help_title"))

            # Update UI elements
            self.ui_elements['search_label'].setText(self.language_manager.get_text("search_label"))
            self.ui_elements['search_box'].setPlaceholderText(self.language_manager.get_text("search_placeholder"))
            self.ui_elements['app_help_btn'].setText(self.language_manager.get_text("application_help"))
            self.ui_elements['pattern_title'].setText(self.language_manager.get_text("select_pattern"))
            self.ui_elements['interpretation_label'].setText(self.language_manager.get_text("interpretation"))

            # Update group boxes
            self.ui_elements['reliability_group'].setTitle(self.language_manager.get_text("reliability"))
            self.ui_elements['category_group'].setTitle(self.language_manager.get_text("category"))
            self.ui_elements['type_group'].setTitle(self.language_manager.get_text("type"))
            self.ui_elements['direction_group'].setTitle(self.language_manager.get_text("direction"))

            # Update pattern details if one is selected
            selected_items = self.pattern_list.selectedItems()
            if selected_items:
                self.show_pattern_details()

            # Update button states
            self.english_btn.setChecked(lang == "english")
            self.russian_btn.setChecked(lang == "russian")
            self.spanish_btn.setChecked(lang == "spanish")

            logger.info(f"Language changed to: {lang}")

    def filter_patterns(self):
        """Filter pattern list based on search text"""
        search_text = self.search_box.text().lower()

        self.pattern_list.clear()
        for pattern in CANDLE_PATTERNS:
            if search_text in pattern.lower():
                self.pattern_list.addItem(pattern)

    def show_pattern_details(self):
        """Show details for selected pattern"""
        selected_items = self.pattern_list.selectedItems()
        if not selected_items:
            return

        pattern_name = selected_items[0].text()

        # Get pattern info from language manager
        pattern_info = self.language_manager.get_pattern_info(pattern_name)

        # Update title
        self.pattern_title.setText(pattern_name)

        # Update image display
        self.pattern_image.set_pattern(pattern_name)

        # Update description
        description = pattern_info.get('description', 'No description available.')
        self.description_text.setHtml(f"""
        <div style="font-family: Arial; font-size: 12pt; line-height: 1.5;">
            <p><b>Description:</b></p>
            <p>{html.escape(description)}</p>
        </div>
        """)

        # Update interpretation
        interpretation = pattern_info.get('interpretation', 'No interpretation available.')
        self.interpretation_text.setHtml(f"""
        <div style="font-family: Arial; font-size: 11pt; line-height: 1.4; color: #444;">
            <p>{html.escape(interpretation)}</p>
        </div>
        """)

        # Update info labels
        self.reliability_label.setText(pattern_info.get('reliability', 'N/A'))
        self.category_label.setText(pattern_info.get('category', 'N/A'))
        self.type_label.setText(pattern_info.get('type', 'N/A'))

        # Update direction with color coding
        direction = pattern_info.get('direction', 'N/A')
        self.direction_label.setText(direction)
        if direction.lower() in ['bullish', 'бычий', 'alcista', 'long']:
            self.direction_label.setStyleSheet("color: green; font-weight: bold;")
        elif direction.lower() in ['bearish', 'медвежий', 'bajista', 'short']:
            self.direction_label.setStyleSheet("color: red; font-weight: bold;")
        elif direction.lower() in ['both', 'оба', 'ambos', 'neutral']:
            self.direction_label.setStyleSheet("color: blue; font-weight: bold;")
        else:
            self.direction_label.setStyleSheet("color: gray;")

    def show_application_help(self):
        """Show detailed application help in current language"""
        help_title = self.language_manager.get_text("app_help_title")

        # Get help content based on language
        help_content = self.get_detailed_help_content()

        # Create dialog with help text
        dialog = QDialog(self)
        dialog.setWindowTitle(help_title)
        dialog.setGeometry(200, 200, 1200, 900)

        layout = QVBoxLayout(dialog)

        # Use QTextEdit for rich text display
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(help_content)

        layout.addWidget(text_edit)

        # Close button (translated)
        close_text = self.get_close_text()
        close_btn = QPushButton(close_text)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def get_detailed_help_content(self):
        """Get detailed help content based on current language"""
        lang = self.language_manager.current_language

        if lang == "russian":
            return self.get_russian_help_content()
        elif lang == "spanish":
            return self.get_spanish_help_content()
        else:
            return self.get_english_help_content()

    def get_english_help_content(self):
        """English help content"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #3498db; margin-top: 25px; }
                h3 { color: #2980b9; margin-top: 20px; }
                .section { margin-bottom: 30px; }
                .metric { background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 15px 0; }
                .tip { background: #e8f4fd; padding: 15px; border-left: 4px solid #2980b9; margin: 15px 0; }
                .warning { background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }
                .disclaimer { background: #f8d7da; padding: 20px; border: 2px solid #dc3545; margin: 25px 0; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th { background: #3498db; color: white; padding: 12px; text-align: left; }
                td { padding: 10px; border: 1px solid #ddd; }
                tr:nth-child(even) { background: #f8f9fa; }
                .highlight { background-color: #ffffcc; padding: 5px; }
            </style>
        </head>
        <body>
            <h1>📊 MOEX & Crypto Backtest System - Complete User Guide</h1>

            <div class="section">
                <h2>1. 🎯 Application Overview</h2>
                <p>This application allows you to backtest trading strategies based on <strong>61 Japanese candlestick patterns</strong> on both <strong>MOEX (Russian stock market)</strong> and <strong>Cryptocurrency markets</strong>.</p>

                <h3>Key Capabilities:</h3>
                <ul>
                    <li>✅ Multi-market support (MOEX & Cryptocurrency)</li>
                    <li>✅ 61 candlestick patterns from TA-Lib</li>
                    <li>✅ Custom strategy creation and management</li>
                    <li>✅ Realistic backtesting with commission and slippage</li>
                    <li>✅ Comprehensive performance metrics</li>
                    <li>✅ Interactive visualization with Plotly</li>
                    <li>✅ Database storage for strategies and results</li>
                    <li>✅ Multi-language support (English, Russian, Spanish)</li>
                </ul>
            </div>

            <div class="section">
                <h2>2. 🚀 Getting Started</h2>

                <h3>Step 1: Create a Strategy</h3>
                <ol>
                    <li>Click <span class="highlight">"New"</span> in Strategy Management section</li>
                    <li>Give your strategy a descriptive name</li>
                    <li>Select patterns to include (Ctrl+Click for multiple selection)</li>
                    <li>Choose entry rule:
                        <ul>
                            <li><strong>OPEN_NEXT_CANDLE</strong> - Enter at next candle open price</li>
                            <li><strong>MIDDLE_OF_PATTERN</strong> - Enter at pattern midpoint</li>
                            <li><strong>CLOSE_PATTERN</strong> - Enter at pattern closing price</li>
                        </ul>
                    </li>
                    <li>Select exit rule:
                        <ul>
                            <li><strong>STOP_LOSS_TAKE_PROFIT</strong> - Fixed stop loss and take profit</li>
                            <li><strong>TAKE_PROFIT_ONLY</strong> - Only take profit, no stop loss</li>
                            <li><strong>OPPOSITE_PATTERN</strong> - Exit when opposite pattern appears</li>
                            <li><strong>TIMEBASED_EXIT</strong> - Exit after specified number of bars</li>
                            <li><strong>TRAILING_STOP</strong> - Dynamic trailing stop loss</li>
                        </ul>
                    </li>
                    <li>Set risk parameters (see section 5 for recommendations)</li>
                    <li>Click <span class="highlight">"Save"</span></li>
                </ol>

                <h3>Step 2: Fetch Market Data</h3>
                <ol>
                    <li>Select market type: <strong>MOEX</strong> or <strong>Cryptocurrency</strong></li>
                    <li>Enter ticker/symbol:
                        <ul>
                            <li>MOEX: SBER, GAZP, LKOH, etc.</li>
                            <li>Crypto: BTCUSDT, ETHUSDT, XRPUSDT, etc.</li>
                        </ul>
                    </li>
                    <li>Choose timeframe: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M</li>
                    <li>Set date range (minimum 3 months recommended)</li>
                    <li>Adjust pattern threshold (default 0.5)</li>
                    <li>Click <span class="highlight">"Fetch Data"</span></li>
                </ol>

                <h3>Step 3: Run Backtest</h3>
                <ol>
                    <li>Select your strategy from dropdown</li>
                    <li>Set capital parameters:
                        <ul>
                            <li>Initial Capital (default: 1,000,000 RUB)</li>
                            <li>Commission % (default: 0.1%)</li>
                            <li>Slippage % (default: 0.1%)</li>
                        </ul>
                    </li>
                    <li>Click <span class="highlight">"Run Backtest"</span></li>
                </ol>
            </div>

            <div class="section">
                <h2>3. 📊 Performance Metrics Explained</h2>

                <div class="metric">
                    <h3>📈 Return Metrics</h3>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Description</th>
                            <th>Interpretation</th>
                        </tr>
                        <tr>
                            <td><strong>Total Return %</strong></td>
                            <td>Overall return on initial capital</td>
                            <td>Above 0% = profitable, Negative = loss</td>
                        </tr>
                        <tr>
                            <td><strong>Sharpe Ratio</strong></td>
                            <td>Risk-adjusted return (annualized)</td>
                            <td>>1 = Good, >2 = Excellent, <0 = Poor</td>
                        </tr>
                        <tr>
                            <td><strong>Profit Factor</strong></td>
                            <td>Gross Profit ÷ Gross Loss</td>
                            <td>>1.5 = Good, >2 = Excellent, <1 = Losing</td>
                        </tr>
                        <tr>
                            <td><strong>Average ROI per Trade</strong></td>
                            <td>Average return per trade</td>
                            <td>Consistency indicator</td>
                        </tr>
                    </table>
                </div>

                <div class="metric">
                    <h3>⚖️ Risk Metrics</h3>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Description</th>
                            <th>Interpretation</th>
                        </tr>
                        <tr>
                            <td><strong>Maximum Drawdown %</strong></td>
                            <td>Largest peak-to-trough decline</td>
                            <td><20% = Good, <10% = Excellent, >30% = Risky</td>
                        </tr>
                        <tr>
                            <td><strong>Win Rate %</strong></td>
                            <td>Percentage of winning trades</td>
                            <td>>50% = Good, >60% = Excellent</td>
                        </tr>
                        <tr>
                            <td><strong>Average Win/Loss Ratio</strong></td>
                            <td>Avg win size ÷ Avg loss size</td>
                            <td>>1.5 = Good, >2 = Excellent</td>
                        </tr>
                        <tr>
                            <td><strong>Standard Deviation of P&L</strong></td>
                            <td>Volatility of returns</td>
                            <td>Lower = More consistent results</td>
                        </tr>
                    </table>
                </div>

                <div class="metric">
                    <h3>📋 Trade Statistics</h3>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Description</th>
                            <th>Ideal Range</th>
                        </tr>
                        <tr>
                            <td><strong>Total Trades</strong></td>
                            <td>Number of trades executed</td>
                            <td>Minimum 30 for statistical significance</td>
                        </tr>
                        <tr>
                            <td><strong>Consecutive Wins/Losses</strong></td>
                            <td>Longest winning/losing streak</td>
                            <td>Avoid >5 consecutive losses</td>
                        </tr>
                        <tr>
                            <td><strong>Average Trade Duration</strong></td>
                            <td>Average holding period</td>
                            <td>Depends on strategy timeframe</td>
                        </tr>
                        <tr>
                            <td><strong>Long/Short Distribution</strong></td>
                            <td>Ratio of long vs short trades</td>
                            <td>Balanced or market-dependent</td>
                        </tr>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2>4. 🎯 Pattern Detection Settings</h2>

                <h3>Pattern Threshold (0.0 - 1.0)</h3>
                <ul>
                    <li><strong>0.0</strong>: Maximum sensitivity - detects more patterns (more false signals)</li>
                    <li><strong>0.5</strong>: Default - standard TA-Lib detection level</li>
                    <li><strong>1.0</strong>: Minimum sensitivity - detects only strongest patterns (fewer signals)</li>
                </ul>

                <div class="tip">
                    <h4>💡 Recommendation:</h4>
                    <p>Start with default 0.5, then adjust based on results:
                    <br>• Increase threshold if too many false signals
                    <br>• Decrease threshold if missing valid signals</p>
                </div>
            </div>

            <div class="section">
                <h2>5. 🛡️ Risk Management Guidelines</h2>

                <div class="tip">
                    <h3>Position Sizing Recommendations</h3>
                    <ul>
                        <li><strong>Conservative</strong>: 1-5% of capital per trade</li>
                        <li><strong>Moderate</strong>: 5-10% of capital per trade</li>
                        <li><strong>Aggressive</strong>: 10-20% of capital per trade (not recommended)</li>
                        <li><strong>Maximum</strong>: Never exceed 25% in single position</li>
                    </ul>
                    <p><strong>Formula:</strong> Position Size = (Capital × Risk %) ÷ Entry Price</p>
                </div>

                <div class="tip">
                    <h3>Stop Loss Settings</h3>
                    <ul>
                        <li><strong>Intraday (1m-1h)</strong>: 0.5-2.0%</li>
                        <li><strong>Swing Trading (4h-1d)</strong>: 1.5-3.0%</li>
                        <li><strong>Position Trading (1w-1M)</strong>: 2.0-5.0%</li>
                        <li><strong>Cryptocurrency</strong>: Add 0.5-1.0% to above values (higher volatility)</li>
                    </ul>
                    <p><strong>Calculation:</strong> Stop Price = Entry Price × (1 - Stop Loss %)</p>
                </div>

                <div class="tip">
                    <h3>Take Profit Settings</h3>
                    <table>
                        <tr>
                            <th>Risk-Reward Ratio</th>
                            <th>Take Profit %</th>
                            <th>Minimum Win Rate Required</th>
                        </tr>
                        <tr>
                            <td>1:1</td>
                            <td>Same as Stop Loss</td>
                            <td>>50%</td>
                        </tr>
                        <tr>
                            <td>1:1.5</td>
                            <td>1.5× Stop Loss</td>
                            <td>>40%</td>
                        </tr>
                        <tr>
                            <td>1:2</td>
                            <td>2× Stop Loss</td>
                            <td>>33%</td>
                        </tr>
                        <tr>
                            <td>1:3</td>
                            <td>3× Stop Loss</td>
                            <td>>25%</td>
                        </tr>
                    </table>
                    <p><strong>Example:</strong> With 2% stop loss and 1:2 risk-reward, take profit = 4%</p>
                </div>

                <div class="tip">
                    <h3>Time-based Exit (Max Bars to Hold)</h3>
                    <ul>
                        <li><strong>Scalping (1m-5m)</strong>: 5-15 bars</li>
                        <li><strong>Day Trading (15m-1h)</strong>: 10-30 bars</li>
                        <li><strong>Swing Trading (4h-1d)</strong>: 5-20 bars</li>
                        <li><strong>Position Trading</strong>: 10-50 bars</li>
                    </ul>
                </div>
            </div>

            <div class="section">
                <h2>6. 📈 Data Analysis Best Practices</h2>

                <div class="tip">
                    <h3>🕐 Timeframe Selection</h3>
                    <ul>
                        <li><strong>Pattern reliability varies by timeframe</strong></li>
                        <li><strong>Higher timeframes</strong> (4h, 1d, 1w): More reliable signals, fewer trades</li>
                        <li><strong>Lower timeframes</strong> (1m, 5m, 15m): More signals, higher noise</li>
                        <li><strong>Recommended</strong>: Test strategy on multiple timeframes</li>
                    </ul>
                </div>

                <div class="tip">
                    <h3>📅 Data Requirements</h3>
                    <ul>
                        <li><strong>Minimum data</strong>: 3 months for intraday, 1 year for daily</li>
                        <li><strong>Ideal data</strong>: 1-2 years for statistical significance</li>
                        <li><strong>Market conditions</strong>: Include both bull and bear markets</li>
                        <li><strong>Sample size</strong>: Minimum 30 trades for reliable statistics</li>
                    </ul>
                </div>

                <div class="tip">
                    <h3>🔍 Pattern Combinations</h3>
                    <ul>
                        <li>Start with 3-5 high-reliability patterns</li>
                        <li>Combine reversal patterns (Hammer, Engulfing, Doji)</li>
                        <li>Filter with confirmation (e.g., volume, trend alignment)</li>
                        <li>Avoid using all 61 patterns - focus on proven ones</li>
                    </ul>
                </div>
            </div>

            <div class="section">
                <h2>7. 💾 Results Interpretation</h2>

                <div class="tip">
                    <h3>✅ Good Strategy Characteristics</h3>
                    <ul>
                        <li>Profit Factor > 1.5</li>
                        <li>Sharpe Ratio > 1.0</li>
                        <li>Maximum Drawdown < 20%</li>
                        <li>Win Rate > 50%</li>
                        <li>Average Win/Loss Ratio > 1.5</li>
                        <li>Consistent performance across timeframes</li>
                        <li>No excessive consecutive losses (< 5)</li>
                    </ul>
                </div>

                <div class="warning">
                    <h3>⚠️ Red Flags (Strategy Needs Improvement)</h3>
                    <ul>
                        <li>Profit Factor < 1.0 (losing strategy)</li>
                        <li>Maximum Drawdown > 30%</li>
                        <li>Sharpe Ratio < 0</li>
                        <li>Win Rate < 40% with poor risk-reward</li>
                        <li>More than 5 consecutive losses</li>
                        <li>Extreme dependence on few trades</li>
                        <li>Poor performance in different market conditions</li>
                    </ul>
                </div>
            </div>

            <div class="section">
                <h2>8. 🔧 Advanced Features</h2>

                <h3>Database Management</h3>
                <ul>
                    <li><strong>Save Strategies</strong>: Store unlimited strategies</li>
                    <li><strong>Save Results</strong>: Track historical performance</li>
                    <li><strong>Export to Excel</strong>: Complete reports with charts</li>
                    <li><strong>Compare Results</strong>: Analyze strategy evolution</li>
                </ul>

                <h3>Visualization Tools</h3>
                <ul>
                    <li><strong>Interactive Charts</strong>: Zoom, pan, hover details</li>
                    <li><strong>Technical Indicators</strong>: Toggle MACD, RSI, Volume</li>
                    <li><strong>Trade Markers</strong>: Visual entry/exit points</li>
                    <li><strong>Multi-timeframe Analysis</strong></li>
                </ul>

                <h3>Debug Mode</h3>
                <ul>
                    <li>Enable detailed logging</li>
                    <li>Track capital allocation</li>
                    <li>Monitor trade decisions</li>
                    <li>Identify calculation issues</li>
                </ul>
            </div>

            <div class="disclaimer">
                <h2>⚠️ IMPORTANT DISCLAIMER</h2>
                <p><strong>TRADING INVOLVES SUBSTANTIAL RISK OF LOSS</strong></p>

                <h3>Risk Warnings:</h3>
                <ul>
                    <li>This software is for <strong>EDUCATIONAL AND RESEARCH PURPOSES ONLY</strong></li>
                    <li><strong>Past performance does not guarantee future results</strong></li>
                    <li>Backtest results are theoretical and may not reflect actual trading</li>
                    <li>All trading decisions are your sole responsibility</li>
                    <li>Never trade with money you cannot afford to lose</li>
                    <li>Consider all risks including but not limited to:
                        <ul>
                            <li>Market risk</li>
                            <li>Liquidity risk</li>
                            <li>Systematic risk</li>
                            <li>Leverage risk</li>
                            <li>Operational risk</li>
                        </ul>
                    </li>
                </ul>

                <h3>Limitations of Backtesting:</h3>
                <ul>
                    <li><strong>Look-ahead bias</strong>: Historical data analysis may create unrealistic expectations</li>
                    <li><strong>Survivorship bias</strong>: Only successful assets are included in historical data</li>
                    <li><strong>Overfitting</strong>: Strategies may work only on historical data</li>
                    <li><strong>Market changes</strong>: Past patterns may not repeat</li>
                    <li><strong>Execution issues</strong>: Slippage, commissions, and liquidity not fully captured</li>
                </ul>

                <h3>Professional Advice:</h3>
                <p>Consult with a qualified financial advisor before making any investment decisions.
                The developers of this software are not responsible for any financial losses incurred through its use.</p>

                <p style="text-align: center; font-weight: bold; color: #dc3545; margin-top: 15px;">
                    USE AT YOUR OWN RISK • NO GUARANTEES • EDUCATIONAL PURPOSES ONLY
                </p>
            </div>

            <div class="section">
                <h2>9. 📞 Support & Troubleshooting</h2>

                <h3>Common Issues:</h3>
                <ul>
                    <li><strong>No data fetched</strong>: Check internet connection, verify ticker symbol</li>
                    <li><strong>Chart not displaying</strong>: Ensure Plotly is installed, check browser settings</li>
                    <li><strong>Pattern not detected</strong>: Adjust threshold, ensure sufficient data</li>
                    <li><strong>Database errors</strong>: Check file permissions, disk space</li>
                </ul>

                <h3>Log Files:</h3>
                <p>Check <code>logs/</code> directory for detailed information:
                <br>• <code>app.log</code> - General application logs
                <br>• <code>error.log</code> - Error details
                <br>• <code>user.log</code> - User actions</p>
            </div>

            <div class="section">
                <h2>10. 🔮 Future Development</h2>
                <ul>
                    <li>Machine learning integration for pattern prediction</li>
                    <li>Additional markets (Forex, US stocks, Futures)</li>
                    <li>Advanced analytics (Monte Carlo simulation, walk-forward analysis)</li>
                    <li>Real-time pattern detection and alerts</li>
                    <li>Enhanced visualization (3D patterns, correlation matrices)</li>
                    <li>More languages and pattern descriptions</li>
                </ul>

                <p style="text-align: center; margin-top: 30px; color: #666; font-style: italic;">
                    🤖 Developed by DeepSeek AI Assistant • 📅 Last Updated: February 2026<br>
                    ⭐ If you find this software useful, please give it a star!
                </p>
            </div>
        </body>
        </html>
        """

    def get_russian_help_content(self):
        """Russian help content"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #3498db; margin-top: 25px; }
                h3 { color: #2980b9; margin-top: 20px; }
                .section { margin-bottom: 30px; }
                .metric { background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 15px 0; }
                .tip { background: #e8f4fd; padding: 15px; border-left: 4px solid #2980b9; margin: 15px 0; }
                .warning { background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }
                .disclaimer { background: #f8d7da; padding: 20px; border: 2px solid #dc3545; margin: 25px 0; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th { background: #3498db; color: white; padding: 12px; text-align: left; }
                td { padding: 10px; border: 1px solid #ddd; }
                tr:nth-child(even) { background: #f8f9fa; }
                .highlight { background-color: #ffffcc; padding: 5px; }
            </style>
        </head>
        <body>
            <h1>📊 Система Бэктестинга MOEX и Криптовалют - Полное Руководство</h1>

            <div class="section">
                <h2>1. 🎯 Обзор Приложения</h2>
                <p>Это приложение позволяет тестировать торговые стратегии на основе <strong>61 японских свечных паттернов</strong> на рынках <strong>MOEX (Российский фондовый рынок)</strong> и <strong>Криптовалют</strong>.</p>

                <h3>Ключевые Возможности:</h3>
                <ul>
                    <li>✅ Поддержка нескольких рынков (MOEX & Криптовалюты)</li>
                    <li>✅ 61 свечной паттерн из TA-Lib</li>
                    <li>✅ Создание и управление пользовательскими стратегиями</li>
                    <li>✅ Реалистичный бэктестинг с комиссиями и проскальзыванием</li>
                    <li>✅ Комплексные метрики производительности</li>
                    <li>✅ Интерактивная визуализация с Plotly</li>
                    <li>✅ Хранение стратегий и результатов в базе данных</li>
                    <li>✅ Многоязычная поддержка (Английский, Русский, Испанский)</li>
                </ul>
            </div>

            <div class="section">
                <h2>2. 🚀 Начало Работы</h2>

                <h3>Шаг 1: Создание Стратегии</h3>
                <ol>
                    <li>Нажмите <span class="highlight">"Новая"</span> в разделе Управление стратегиями</li>
                    <li>Дайте стратегии описательное название</li>
                    <li>Выберите паттерны для включения (Ctrl+Click для множественного выбора)</li>
                    <li>Выберите правило входа:
                        <ul>
                            <li><strong>OPEN_NEXT_CANDLE</strong> - Вход по цене открытия следующей свечи</li>
                            <li><strong>MIDDLE_OF_PATTERN</strong> - Вход по средней цене паттерна</li>
                            <li><strong>CLOSE_PATTERN</strong> - Вход по цене закрытия паттерна</li>
                        </ul>
                    </li>
                    <li>Выберите правило выхода:
                        <ul>
                            <li><strong>STOP_LOSS_TAKE_PROFIT</strong> - Фиксированные стоп-лосс и тейк-профит</li>
                            <li><strong>TAKE_PROFIT_ONLY</strong> - Только тейк-профит, без стоп-лосса</li>
                            <li><strong>OPPOSITE_PATTERN</strong> - Выход при появлении противоположного паттерна</li>
                            <li><strong>TIMEBASED_EXIT</strong> - Выход после указанного количества свечей</li>
                            <li><strong>TRAILING_STOP</strong> - Динамический трейлинг-стоп</li>
                        </ul>
                    </li>
                    <li>Установите параметры риска (см. раздел 5 для рекомендаций)</li>
                    <li>Нажмите <span class="highlight">"Сохранить"</span></li>
                </ol>

                <h3>Шаг 2: Загрузка Рыночных Данных</h3>
                <ol>
                    <li>Выберите тип рынка: <strong>MOEX</strong> или <strong>Криптовалюта</strong></li>
                    <li>Введите тикер/символ:
                        <ul>
                            <li>MOEX: SBER, GAZP, LKOH и т.д.</li>
                            <li>Криптовалюта: BTCUSDT, ETHUSDT, XRPUSDT и т.д.</li>
                        </ul>
                    </li>
                    <li>Выберите таймфрейм: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M</li>
                    <li>Установите диапазон дат (рекомендуется минимум 3 месяца)</li>
                    <li>Настройте порог обнаружения паттернов (по умолчанию 0.5)</li>
                    <li>Нажмите <span class="highlight">"Загрузить Данные"</span></li>
                </ol>

                <h3>Шаг 3: Запуск Бэктестинга</h3>
                <ol>
                    <li>Выберите вашу стратегию из выпадающего списка</li>
                    <li>Установите параметры капитала:
                        <ul>
                            <li>Начальный капитал (по умолчанию: 1,000,000 RUB)</li>
                            <li>Комиссия % (по умолчанию: 0.1%)</li>
                            <li>Проскальзывание % (по умолчанию: 0.1%)</li>
                        </ul>
                    </li>
                    <li>Нажмите <span class="highlight">"Запустить Бэктестинг"</span></li>
                </ol>
            </div>

            <div class="section">
                <h2>3. 📊 Объяснение Метрик Производительности</h2>

                <div class="metric">
                    <h3>📈 Метрики Доходности</h3>
                    <table>
                        <tr>
                            <th>Метрика</th>
                            <th>Описание</th>
                            <th>Интерпретация</th>
                        </tr>
                        <tr>
                            <td><strong>Общая Доходность %</strong></td>
                            <td>Общая доходность на начальный капитал</td>
                            <td>Выше 0% = прибыльно, Отрицательная = убыток</td>
                        </tr>
                        <tr>
                            <td><strong>Коэффициент Шарпа</strong></td>
                            <td>Доходность с поправкой на риск (годовая)</td>
                            <td>>1 = Хорошо, >2 = Отлично, <0 = Плохо</td>
                        </tr>
                        <tr>
                            <td><strong>Фактор Прибыли</strong></td>
                            <td>Валовая прибыль ÷ Валовые убытки</td>
                            <td>>1.5 = Хорошо, >2 = Отлично, <1 = Убыточно</td>
                        </tr>
                        <tr>
                            <td><strong>Средняя ROI на Сделку</strong></td>
                            <td>Средняя доходность на сделку</td>
                            <td>Индикатор стабильности</td>
                        </tr>
                    </table>
                </div>

                <div class="metric">
                    <h3>⚖️ Метрики Риска</h3>
                    <table>
                        <tr>
                            <th>Метрика</th>
                            <th>Описание</th>
                            <th>Интерпретация</th>
                        </tr>
                        <tr>
                            <td><strong>Максимальная Просадка %</strong></td>
                            <td>Наибольшее снижение от пика до минимума</td>
                            <td><20% = Хорошо, <10% = Отлично, >30% = Рискованно</td>
                        </tr>
                        <tr>
                            <td><strong>Процент Успешных Сделок %</strong></td>
                            <td>Процент прибыльных сделок</td>
                            <td>>50% = Хорошо, >60% = Отлично</td>
                        </tr>
                        <tr>
                            <td><strong>Соотношение Средней Прибыли/Убытка</strong></td>
                            <td>Средняя прибыль ÷ Средний убыток</td>
                            <td>>1.5 = Хорошо, >2 = Отлично</td>
                        </tr>
                        <tr>
                            <td><strong>Стандартное Отклонение P&L</strong></td>
                            <td>Волатильность доходности</td>
                            <td>Ниже = Более стабильные результаты</td>
                        </tr>
                    </table>
                </div>

                <div class="metric">
                    <h3>📋 Статистика Сделок</h3>
                    <table>
                        <tr>
                            <th>Метрика</th>
                            <th>Описание</th>
                            <th>Идеальный Диапазон</th>
                        </tr>
                        <tr>
                            <td><strong>Всего Сделок</strong></td>
                            <td>Количество выполненных сделок</td>
                            <td>Минимум 30 для статистической значимости</td>
                        </tr>
                        <tr>
                            <td><strong>Последовательные Прибыли/Убытки</strong></td>
                            <td>Самая длинная серия прибылей/убытков</td>
                            <td>Избегать >5 последовательных убытков</td>
                        </tr>
                        <tr>
                            <td><strong>Средняя Продолжительность Сделки</strong></td>
                            <td>Средний период удержания позиции</td>
                            <td>Зависит от таймфрейма стратегии</td>
                        </tr>
                        <tr>
                            <td><strong>Распределение Лонг/Шорт</strong></td>
                            <td>Соотношение лонг и шорт сделок</td>
                            <td>Сбалансированное или зависящее от рынка</td>
                        </tr>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2>4. 🎯 Настройки Обнаружения Паттернов</h2>

                <h3>Порог Обнаружения (0.0 - 1.0)</h3>
                <ul>
                    <li><strong>0.0</strong>: Максимальная чувствительность - обнаруживает больше паттернов (больше ложных сигналов)</li>
                    <li><strong>0.5</strong>: По умолчанию - стандартный уровень обнаружения TA-Lib</li>
                    <li><strong>1.0</strong>: Минимальная чувствительность - обнаруживает только самые сильные паттерны (меньше сигналов)</li>
                </ul>

                <div class="tip">
                    <h4>💡 Рекомендация:</h4>
                    <p>Начните с 0.5, затем корректируйте на основе результатов:
                    <br>• Увеличивайте порог, если слишком много ложных сигналов
                    <br>• Уменьшайте порог, если пропускаются валидные сигналы</p>
                </div>
            </div>

            <div class="section">
                <h2>5. 🛡️ Рекомендации по Управлению Рисками</h2>

                <div class="tip">
                    <h3>Рекомендации по Размеру Позиции</h3>
                    <ul>
                        <li><strong>Консервативно</strong>: 1-5% капитала на сделку</li>
                        <li><strong>Умеренно</strong>: 5-10% капитала на сделку</li>
                        <li><strong>Агрессивно</strong>: 10-20% капитала на сделку (не рекомендуется)</li>
                        <li><strong>Максимум</strong>: Никогда не превышайте 25% в одной позиции</li>
                    </ul>
                    <p><strong>Формула:</strong> Размер позиции = (Капитал × Риск %) ÷ Цена входа</p>
                </div>

                <div class="tip">
                    <h3>Настройки Стоп-Лосса</h3>
                    <ul>
                        <li><strong>Внутридневная торговля (1m-1h)</strong>: 0.5-2.0%</li>
                        <li><strong>Свинг-трейдинг (4h-1d)</strong>: 1.5-3.0%</li>
                        <li><strong>Позиционная торговля (1w-1M)</strong>: 2.0-5.0%</li>
                        <li><strong>Криптовалюты</strong>: Добавьте 0.5-1.0% к вышеуказанным значениям (высокая волатильность)</li>
                    </ul>
                    <p><strong>Расчет:</strong> Цена стоп-лосса = Цена входа × (1 - Стоп-лосс %)</p>
                </div>

                <div class="tip">
                    <h3>Настройки Тейк-Профита</h3>
                    <table>
                        <tr>
                            <th>Соотношение Риск-Доходность</th>
                            <th>Тейк-Профит %</th>
                            <th>Минимальный % Успешных Сделок</th>
                        </tr>
                        <tr>
                            <td>1:1</td>
                            <td>Такой же как Стоп-Лосс</td>
                            <td>>50%</td>
                        </tr>
                        <tr>
                            <td>1:1.5</td>
                            <td>1.5× Стоп-Лосс</td>
                            <td>>40%</td>
                        </tr>
                        <tr>
                            <td>1:2</td>
                            <td>2× Стоп-Лосс</td>
                            <td>>33%</td>
                        </tr>
                        <tr>
                            <td>1:3</td>
                            <td>3× Стоп-Лосс</td>
                            <td>>25%</td>
                        </tr>
                    </table>
                    <p><strong>Пример:</strong> При 2% стоп-лоссе и соотношении 1:2, тейк-профит = 4%</p>
                </div>

                <div class="tip">
                    <h3>Временной Выход (Макс. свечей для удержания)</h3>
                    <ul>
                        <li><strong>Скальпинг (1m-5m)</strong>: 5-15 свечей</li>
                        <li><strong>Дейт-трейдинг (15m-1h)</strong>: 10-30 свечей</li>
                        <li><strong>Свинг-трейдинг (4h-1d)</strong>: 5-20 свечей</li>
                        <li><strong>Позиционная торговля</strong>: 10-50 свечей</li>
                    </ul>
                </div>
            </div>

            <div class="disclaimer">
                <h2>⚠️ ВАЖНОЕ ОТВЕРЖДЕНИЕ ОТВЕТСТВЕННОСТИ</h2>
                <p><strong>ТОРГОВЛЯ СВЯЗАНА С ЗНАЧИТЕЛЬНЫМ РИСКОМ ПОТЕРИ СРЕДСТВ</strong></p>

                <h3>Предупреждения о Рисках:</h3>
                <ul>
                    <li>Это программное обеспечение предназначено <strong>ТОЛЬКО ДЛЯ ОБРАЗОВАТЕЛЬНЫХ И ИССЛЕДОВАТЕЛЬСКИХ ЦЕЛЕЙ</strong></li>
                    <li><strong>ПРОШЛЫЕ РЕЗУЛЬТАТЫ НЕ ГАРАНТИРУЮТ БУДУЩИХ РЕЗУЛЬТАТОВ</strong></li>
                    <li>Результаты бэктестинга теоретические и могут не отражать реальную торговлю</li>
                    <li>Все торговые решения - ваша исключительная ответственность</li>
                    <li>Никогда не торгуйте деньгами, которые не можете позволить себе потерять</li>
                    <li>Учитывайте все риски, включая, но не ограничиваясь:
                        <ul>
                            <li>Рыночный риск</li>
                            <li>Риск ликвидности</li>
                            <li>Систематический риск</li>
                            <li>Риск кредитного плеча</li>
                            <li>Операционный риск</li>
                        </ul>
                    </li>
                </ul>

                <h3>Ограничения Бэктестинга:</h3>
                <ul>
                    <li><strong>Предвзятость задним числом</strong>: Анализ исторических данных может создавать нереалистичные ожидания</li>
                    <li><strong>Предвзятость выжившего</strong>: В исторические данные включены только успешные активы</li>
                    <li><strong>Переобучение</strong>: Стратегии могут работать только на исторических данных</li>
                    <li><strong>Изменения рынка</strong>: Прошлые паттерны могут не повторяться</li>
                    <li><strong>Проблемы исполнения</strong>: Проскальзывание, комиссии и ликвидность не полностью учитываются</li>
                </ul>

                <h3>Профессиональный Совет:</h3>
                <p>Проконсультируйтесь с квалифицированным финансовым консультантом перед принятием любых инвестиционных решений.
                Разработчики этого программного обеспечения не несут ответственности за любые финансовые потери, понесенные в результате его использования.</p>

                <p style="text-align: center; font-weight: bold; color: #dc3545; margin-top: 15px;">
                    ИСПОЛЬЗУЙТЕ НА СВОЙ СТРАХ И РИСК • НЕТ ГАРАНТИЙ • ТОЛЬКО ДЛЯ ОБРАЗОВАТЕЛЬНЫХ ЦЕЛЕЙ
                </p>
            </div>

            <p style="text-align: center; margin-top: 30px; color: #666; font-style: italic;">
                🤖 Разработано DeepSeek AI Assistant • 📅 Последнее обновление: Февраль 2026<br>
                ⭐ Если вы находите это ПО полезным, пожалуйста, поставьте звезду!
            </p>
        </body>
        </html>
        """

    def get_spanish_help_content(self):
        """Spanish help content"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #3498db; margin-top: 25px; }
                h3 { color: #2980b9; margin-top: 20px; }
                .section { margin-bottom: 30px; }
                .metric { background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 15px 0; }
                .tip { background: #e8f4fd; padding: 15px; border-left: 4px solid #2980b9; margin: 15px 0; }
                .warning { background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }
                .disclaimer { background: #f8d7da; padding: 20px; border: 2px solid #dc3545; margin: 25px 0; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th { background: #3498db; color: white; padding: 12px; text-align: left; }
                td { padding: 10px; border: 1px solid #ddd; }
                tr:nth-child(even) { background: #f8f9fa; }
                .highlight { background-color: #ffffcc; padding: 5px; }
            </style>
        </head>
        <body>
            <h1>📊 Sistema de Backtesting MOEX y Criptomonedas - Guía Completa</h1>

            <div class="section">
                <h2>1. 🎯 Descripción General de la Aplicación</h2>
                <p>Esta aplicación permite realizar backtesting de estrategias de trading basadas en <strong>61 patrones de velas japonesas</strong> en los mercados de <strong>MOEX (mercado bursátil ruso)</strong> y <strong>Criptomonedas</strong>.</p>

                <h3>Capacidades Clave:</h3>
                <ul>
                    <li>✅ Soporte multimercado (MOEX & Criptomonedas)</li>
                    <li>✅ 61 patrones de velas de TA-Lib</li>
                    <li>✅ Creación y gestión de estrategias personalizadas</li>
                    <li>✅ Backtesting realista con comisiones y deslizamiento</li>
                    <li>✅ Métricas de rendimiento completas</li>
                    <li>✅ Visualización interactiva con Plotly</li>
                    <li>✅ Almacenamiento en base de datos de estrategias y resultados</li>
                    <li>✅ Soporte multilingüe (Inglés, Ruso, Español)</li>
                </ul>
            </div>

            <div class="section">
                <h2>2. 🚀 Cómo Empezar</h2>

                <h3>Paso 1: Crear una Estrategia</h3>
                <ol>
                    <li>Haga clic en <span class="highlight">"Nueva"</span> en la sección Gestión de Estrategias</li>
                    <li>Asigne un nombre descriptivo a su estrategia</li>
                    <li>Seleccione patrones para incluir (Ctrl+Click para selección múltiple)</li>
                    <li>Elija regla de entrada:
                        <ul>
                            <li><strong>OPEN_NEXT_CANDLE</strong> - Entrada al precio de apertura de la siguiente vela</li>
                            <li><strong>MIDDLE_OF_PATTERN</strong> - Entrada al precio medio del patrón</li>
                            <li><strong>CLOSE_PATTERN</strong> - Entrada al precio de cierre del patrón</li>
                        </ul>
                    </li>
                    <li>Elija regla de salida:
                        <ul>
                            <li><strong>STOP_LOSS_TAKE_PROFIT</strong> - Stop loss y take profit fijos</li>
                            <li><strong>TAKE_PROFIT_ONLY</strong> - Solo take profit, sin stop loss</li>
                            <li><strong>OPPOSITE_PATTERN</strong> - Salida cuando aparece patrón opuesto</li>
                            <li><strong>TIMEBASED_EXIT</strong> - Salida después de número especificado de velas</li>
                            <li><strong>TRAILING_STOP</strong> - Stop loss dinámico con seguimiento</li>
                        </ul>
                    </li>
                    <li>Establezca parámetros de riesgo (ver sección 5 para recomendaciones)</li>
                    <li>Haga clic en <span class="highlight">"Guardar"</span></li>
                </ol>

                <h3>Paso 2: Obtener Datos de Mercado</h3>
                <ol>
                    <li>Seleccione tipo de mercado: <strong>MOEX</strong> o <strong>Criptomoneda</strong></li>
                    <li>Ingrese ticker/símbolo:
                        <ul>
                            <li>MOEX: SBER, GAZP, LKOH, etc.</li>
                            <li>Criptomoneda: BTCUSDT, ETHUSDT, XRPUSDT, etc.</li>
                        </ul>
                    </li>
                    <li>Elija marco temporal: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M</li>
                    <li>Establezca rango de fechas (mínimo 3 meses recomendado)</li>
                    <li>Ajuste umbral de detección de patrones (predeterminado 0.5)</li>
                    <li>Haga clic en <span class="highlight">"Obtener Datos"</span></li>
                </ol>

                <h3>Paso 3: Ejecutar Backtesting</h3>
                <ol>
                    <li>Seleccione su estrategia del menú desplegable</li>
                    <li>Establezca parámetros de capital:
                        <ul>
                            <li>Capital Inicial (predeterminado: 1,000,000 RUB)</li>
                            <li>Comisión % (predeterminado: 0.1%)</li>
                            <li>Deslizamiento % (predeterminado: 0.1%)</li>
                        </ul>
                    </li>
                    <li>Haga clic en <span class="highlight">"Ejecutar Backtesting"</span></li>
                </ol>
            </div>

            <div class="section">
                <h2>3. 📊 Explicación de Métricas de Rendimiento</h2>

                <div class="metric">
                    <h3>📈 Métricas de Rentabilidad</h3>
                    <table>
                        <tr>
                            <th>Métrica</th>
                            <th>Descripción</th>
                            <th>Interpretación</th>
                        </tr>
                        <tr>
                            <td><strong>Retorno Total %</strong></td>
                            <td>Retorno general sobre capital inicial</td>
                            <td>Superior a 0% = rentable, Negativo = pérdida</td>
                        </tr>
                        <tr>
                            <td><strong>Ratio de Sharpe</strong></td>
                            <td>Retorno ajustado al riesgo (anualizado)</td>
                            <td>>1 = Bueno, >2 = Excelente, <0 = Pobre</td>
                        </tr>
                        <tr>
                            <td><strong>Factor de Beneficio</strong></td>
                            <td>Beneficio bruto ÷ Pérdida bruta</td>
                            <td>>1.5 = Bueno, >2 = Excelente, <1 = Perdedor</td>
                        </tr>
                        <tr>
                            <td><strong>ROI Promedio por Operación</strong></td>
                            <td>Retorno promedio por operación</td>
                            <td>Indicador de consistencia</td>
                        </tr>
                    </table>
                </div>

                <div class="metric">
                    <h3>⚖️ Métricas de Riesgo</h3>
                    <table>
                        <tr>
                            <th>Métrica</th>
                            <th>Descripción</th>
                            <th>Interpretación</th>
                        </tr>
                        <tr>
                            <td><strong>Drawdown Máximo %</strong></td>
                            <td>Mayor caída de pico a valle</td>
                            <td><20% = Bueno, <10% = Excelente, >30% = Arriesgado</td>
                        </tr>
                        <tr>
                            <td><strong>Tasa de Aciertos %</strong></td>
                            <td>Porcentaje de operaciones ganadoras</td>
                            <td>>50% = Bueno, >60% = Excelente</td>
                        </tr>
                        <tr>
                            <td><strong>Ratio Ganancia/Pérdida Promedio</strong></td>
                            <td>Ganancia promedio ÷ Pérdida promedio</td>
                            <td>>1.5 = Bueno, >2 = Excelente</td>
                        </tr>
                        <tr>
                            <td><strong>Desviación Estándar de P&L</strong></td>
                            <td>Volatilidad de los retornos</td>
                            <td>Más baja = Resultados más consistentes</td>
                        </tr>
                    </table>
                </div>

                <div class="metric">
                    <h3>📋 Estadísticas de Operaciones</h3>
                    <table>
                        <tr>
                            <th>Métrica</th>
                            <th>Descripción</th>
                            <th>Rango Ideal</th>
                        </tr>
                        <tr>
                            <td><strong>Total de Operaciones</strong></td>
                            <td>Número de operaciones ejecutadas</td>
                            <td>Mínimo 30 para significancia estadística</td>
                        </tr>
                        <tr>
                            <td><strong>Ganadas/Perdidas Consecutivas</strong></td>
                            <td>Racha más larga de ganancias/pérdidas</td>
                            <td>Evitar >5 pérdidas consecutivas</td>
                        </tr>
                        <tr>
                            <td><strong>Duración Promedio de Operación</strong></td>
                            <td>Período promedio de mantenimiento de posición</td>
                            <td>Depende del marco temporal de la estrategia</td>
                        </tr>
                        <tr>
                            <td><strong>Distribución Largo/Corto</strong></td>
                            <td>Proporción de operaciones largas vs cortas</td>
                            <td>Equilibrada o dependiente del mercado</td>
                        </tr>
                    </table>
                </div>
            </div>

            <div class="disclaimer">
                <h2>⚠️ DECLARACIÓN DE EXENCIÓN DE RESPONSABILIDAD IMPORTANTE</h2>
                <p><strong>EL TRADING CONLLEVA UN RIESGO SIGNIFICATIVO DE PÉRDIDA</strong></p>

                <h3>Advertencias de Riesgo:</h3>
                <ul>
                    <li>Este software es <strong>SÓLO PARA FINES EDUCATIVOS Y DE INVESTIGACIÓN</strong></li>
                    <li><strong>LOS RESULTADOS PASADOS NO GARANTIZAN RESULTADOS FUTUROS</strong></li>
                    <li>Los resultados de backtesting son teóricos y pueden no reflejar el trading real</li>
                    <li>Todas las decisiones de trading son su exclusiva responsabilidad</li>
                    <li>Nunca opere con dinero que no pueda permitirse perder</li>
                    <li>Considere todos los riesgos, incluyendo, entre otros:
                        <ul>
                            <li>Riesgo de mercado</li>
                            <li>Riesgo de liquidez</li>
                            <li>Riesgo sistemático</li>
                            <li>Riesgo de apalancamiento</li>
                            <li>Riesgo operativo</li>
                        </ul>
                    </li>
                </ul>

                <h3>Limitaciones del Backtesting:</h3>
                <ul>
                    <li><strong>Sesgo de retrospectiva</strong>: El análisis de datos históricos puede crear expectativas poco realistas</li>
                    <li><strong>Sesgo de supervivencia</strong>: Solo se incluyen activos exitosos en datos históricos</li>
                    <li><strong>Sobreajuste</strong>: Las estrategias pueden funcionar solo en datos históricos</li>
                    <li><strong>Cambios de mercado</strong>: Los patrones pasados pueden no repetirse</li>
                    <li><strong>Problemas de ejecución</strong>: Deslizamiento, comisiones y liquidez no se capturan completamente</li>
                </ul>

                <h3>Consejo Profesional:</h3>
                <p>Consulte con un asesor financiero calificado antes de tomar cualquier decisión de inversión.
                Los desarrolladores de este software no son responsables de ninguna pérdida financiera incurrida por su uso.</p>

                <p style="text-align: center; font-weight: bold; color: #dc3545; margin-top: 15px;">
                    ÚSELO BAJO SU PROPIO RIESGO • SIN GARANTÍAS • SÓLO PARA FINES EDUCATIVOS
                </p>
            </div>

            <p style="text-align: center; margin-top: 30px; color: #666; font-style: italic;">
                🤖 Desarrollado por DeepSeek AI Assistant • 📅 Última actualización: Febrero 2026<br>
                ⭐ Si encuentra útil este software, ¡por favor dé una estrella!
            </p>
        </body>
        </html>
        """

    def get_close_text(self):
        """Get translated close text"""
        lang = self.language_manager.current_language
        if lang == "russian":
            return "Закрыть"
        elif lang == "spanish":
            return "Cerrar"
        else:
            return "Close"