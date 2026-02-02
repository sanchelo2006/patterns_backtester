from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
from pathlib import Path
import html
from src.config.settings import CANDLE_PATTERNS
from src.utils.logger import get_logger

logger = get_logger('app')


class PatternDiagram(QWidget):
    """Widget to draw accurate pattern diagrams"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pattern_name = ""
        self.pattern_data = {}
        self.setMinimumHeight(250)
        self.setMinimumWidth(500)

    def set_pattern(self, pattern_name: str, pattern_data: dict = None):
        """Set pattern to draw"""
        self.pattern_name = pattern_name
        self.pattern_data = pattern_data or {}
        self.update()

    def paintEvent(self, event):
        """Draw pattern diagram"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Clear background
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        if not self.pattern_name:
            # Draw empty state
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "Select a pattern to see diagram")
            return

        # Draw based on pattern type
        width = self.width()
        height = self.height()

        # Draw title
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(10, 25, f"Pattern: {self.pattern_name}")

        # Get pattern components
        components = self.pattern_data.get('components', 1)

        # Calculate positions for candles
        candle_width = 20
        candle_spacing = 30
        start_x = (width - (components * candle_width + (components - 1) * candle_spacing)) // 2
        center_y = height // 2 + 20

        # Draw each candle based on pattern type
        if 'DOJI' in self.pattern_name:
            self.draw_doji_pattern(painter, start_x, center_y, candle_width, self.pattern_name)
        elif 'HAMMER' in self.pattern_name:
            self.draw_hammer_pattern(painter, start_x, center_y, candle_width, self.pattern_name)
        elif 'HANGINGMAN' in self.pattern_name:
            self.draw_hangingman_pattern(painter, start_x, center_y, candle_width)
        elif 'ENGULFING' in self.pattern_name:
            self.draw_engulfing_pattern(painter, start_x, center_y, candle_width, components)
        elif 'STAR' in self.pattern_name:
            self.draw_star_pattern(painter, start_x, center_y, candle_width, components, self.pattern_name)
        elif 'MARUBOZU' in self.pattern_name:
            self.draw_marubozu_pattern(painter, start_x, center_y, candle_width, self.pattern_name)
        elif 'HARAMI' in self.pattern_name:
            self.draw_harami_pattern(painter, start_x, center_y, candle_width, components)
        elif 'CROWS' in self.pattern_name:
            self.draw_crows_pattern(painter, start_x, center_y, candle_width, components, self.pattern_name)
        elif 'SOLDIERS' in self.pattern_name:
            self.draw_soldiers_pattern(painter, start_x, center_y, candle_width, components)
        elif 'BELTHOLD' in self.pattern_name:
            self.draw_belthold_pattern(painter, start_x, center_y, candle_width, self.pattern_data.get('direction', 'Both'))
        else:
            self.draw_generic_pattern(painter, start_x, center_y, candle_width, components)

    def draw_doji_pattern(self, painter, start_x, center_y, candle_width, pattern_name):
        """Draw doji pattern"""
        if 'DRAGONFLY' in pattern_name:
            # Dragonfly Doji
            x = start_x + candle_width // 2
            # Long lower shadow
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y - 10, x, center_y + 40)
            # Small body at top
            painter.drawLine(x - 8, center_y - 10, x + 8, center_y - 10)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 40, center_y + 60, "Dragonfly Doji")

        elif 'GRAVESTONE' in pattern_name:
            # Gravestone Doji
            x = start_x + candle_width // 2
            # Long upper shadow
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y - 40, x, center_y + 10)
            # Small body at bottom
            painter.drawLine(x - 8, center_y + 10, x + 8, center_y + 10)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 40, center_y + 60, "Gravestone Doji")

        elif 'LONGLEGGED' in pattern_name:
            # Long-legged Doji
            x = start_x + candle_width // 2
            # Long upper and lower shadows
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y - 40, x, center_y + 40)
            # Small body in middle
            painter.drawLine(x - 8, center_y, x + 8, center_y)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 40, center_y + 70, "Long-legged Doji")

        else:
            # Regular Doji
            x = start_x + candle_width // 2
            # Moderate shadows
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y - 20, x, center_y + 20)
            # Cross body
            painter.drawLine(x - 10, center_y, x + 10, center_y)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 20, center_y + 50, "Doji")

    def draw_hammer_pattern(self, painter, start_x, center_y, candle_width, pattern_name):
        """Draw hammer or hanging man pattern"""
        x = start_x + candle_width // 2

        if 'INVERTED' in pattern_name:
            # Inverted Hammer (bullish)
            # Small body at bottom
            painter.setBrush(QColor(100, 255, 100))  # Green for bullish
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x - 8, center_y, 16, 10)
            # Long upper shadow
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y, x, center_y - 40)
            # Very small or no lower shadow
            painter.drawLine(x, center_y + 10, x, center_y + 15)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 50, center_y + 50, "Inverted Hammer")

        elif 'HANGINGMAN' in pattern_name:
            # Hanging Man (bearish)
            # Small body at top
            painter.setBrush(QColor(255, 100, 100))  # Red for bearish
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x - 8, center_y - 10, 16, 10)
            # Long lower shadow
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y, x, center_y + 40)
            # Very small upper shadow
            painter.drawLine(x, center_y - 10, x, center_y - 15)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 50, center_y + 50, "Hanging Man")

        else:
            # Hammer (bullish)
            # Small body at top
            painter.setBrush(QColor(100, 255, 100))  # Green for bullish
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x - 8, center_y - 10, 16, 10)
            # Long lower shadow
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y, x, center_y + 40)
            # Very small upper shadow
            painter.drawLine(x, center_y - 10, x, center_y - 15)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 30, center_y + 50, "Hammer")

    def draw_hangingman_pattern(self, painter, start_x, center_y, candle_width):
        """Draw hanging man pattern"""
        x = start_x + candle_width // 2
        # Small body at top (red for bearish)
        painter.setBrush(QColor(255, 100, 100))
        painter.setPen(QPen(QColor(200, 50, 50), 1))
        painter.drawRect(x - 8, center_y - 10, 16, 10)
        # Long lower shadow
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(x, center_y, x, center_y + 40)
        # Very small upper shadow
        painter.drawLine(x, center_y - 10, x, center_y - 15)

    def draw_engulfing_pattern(self, painter, start_x, center_y, candle_width, components):
        """Draw engulfing pattern"""
        # First candle (small)
        x1 = start_x + candle_width // 2
        if 'BULLISH' in self.pattern_name or self.pattern_data.get('direction') == 'Bullish':
            # First candle red (bearish), second green (bullish)
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x1 - 6, center_y - 15, 12, 30)

            # Second candle (engulfing, larger)
            x2 = x1 + candle_width + 30
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x2 - 10, center_y - 20, 20, 40)

            # Arrows
            painter.setPen(QPen(QColor(0, 0, 255), 2))
            painter.drawLine(x2 + 15, center_y, x2 + 30, center_y)
            painter.setBrush(QColor(0, 0, 255))
            painter.drawPolygon(QPolygon([
                QPoint(x2 + 30, center_y),
                QPoint(x2 + 25, center_y - 5),
                QPoint(x2 + 25, center_y + 5)
            ]))

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x1 - 10, center_y - 40, "1st")
            painter.drawText(x2 - 15, center_y - 45, "2nd (Engulfing)")
            painter.drawText(x2 + 35, center_y, "Bullish")
        else:
            # Bearish engulfing
            # First candle green (bullish), second red (bearish)
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x1 - 6, center_y - 15, 12, 30)

            # Second candle (engulfing, larger)
            x2 = x1 + candle_width + 30
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x2 - 10, center_y - 20, 20, 40)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x1 - 10, center_y - 40, "1st")
            painter.drawText(x2 - 15, center_y - 45, "2nd (Engulfing)")
            painter.drawText(x2 + 35, center_y, "Bearish")

    def draw_star_pattern(self, painter, start_x, center_y, candle_width, components, pattern_name):
        """Draw star pattern"""
        # First candle (long)
        x1 = start_x + candle_width // 2
        if 'EVENING' in pattern_name:
            # Evening star (bearish)
            # First candle green (bullish)
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x1 - 8, center_y - 25, 16, 50)

            # Gap
            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
            painter.drawLine(x1 + 15, center_y, x1 + 25, center_y)

            # Star candle (small, can be doji)
            x2 = x1 + candle_width + 30
            if 'DOJI' in pattern_name:
                # Doji star
                painter.setPen(QPen(QColor(0, 0, 0), 2))
                painter.drawLine(x2, center_y - 10, x2, center_y + 10)
                painter.drawLine(x2 - 8, center_y, x2 + 8, center_y)
            else:
                # Small body star
                painter.setBrush(QColor(255, 255, 200))
                painter.setPen(QPen(QColor(200, 200, 150), 1))
                painter.drawRect(x2 - 6, center_y - 10, 12, 20)

            # Gap
            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
            painter.drawLine(x2 + 15, center_y, x2 + 25, center_y)

            # Third candle (red, bearish)
            x3 = x2 + candle_width + 30
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x3 - 8, center_y - 20, 16, 40)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x1 - 20, center_y - 60, "Long Bullish")
            painter.drawText(x2 - 10, center_y - 35, "Star")
            painter.drawText(x3 - 10, center_y - 45, "Bearish")
            painter.drawText(x1 + 40, center_y + 60, "Evening Star Pattern")

        else:
            # Morning star (bullish) - opposite colors
            # First candle red (bearish)
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x1 - 8, center_y - 25, 16, 50)

            # Gap
            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
            painter.drawLine(x1 + 15, center_y, x1 + 25, center_y)

            # Star candle (small, can be doji)
            x2 = x1 + candle_width + 30
            if 'DOJI' in pattern_name:
                # Doji star
                painter.setPen(QPen(QColor(0, 0, 0), 2))
                painter.drawLine(x2, center_y - 10, x2, center_y + 10)
                painter.drawLine(x2 - 8, center_y, x2 + 8, center_y)
            else:
                # Small body star
                painter.setBrush(QColor(255, 255, 200))
                painter.setPen(QPen(QColor(200, 200, 150), 1))
                painter.drawRect(x2 - 6, center_y - 10, 12, 20)

            # Gap
            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
            painter.drawLine(x2 + 15, center_y, x2 + 25, center_y)

            # Third candle (green, bullish)
            x3 = x2 + candle_width + 30
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x3 - 8, center_y - 20, 16, 40)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x1 - 20, center_y - 60, "Long Bearish")
            painter.drawText(x2 - 10, center_y - 35, "Star")
            painter.drawText(x3 - 10, center_y - 45, "Bullish")
            painter.drawText(x1 + 40, center_y + 60, "Morning Star Pattern")

    def draw_marubozu_pattern(self, painter, start_x, center_y, candle_width, pattern_name):
        """Draw marubozu pattern"""
        x = start_x + candle_width // 2

        if 'CLOSING' in pattern_name:
            # Closing Marubozu
            if self.pattern_data.get('direction') == 'Bullish':
                painter.setBrush(QColor(100, 255, 100))
                painter.setPen(QPen(QColor(50, 200, 50), 1))
            else:
                painter.setBrush(QColor(255, 100, 100))
                painter.setPen(QPen(QColor(200, 50, 50), 1))

            # Body with shadow only on open side
            painter.drawRect(x - 10, center_y - 30, 20, 60)
            # Small shadow on opening side
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            if self.pattern_data.get('direction') == 'Bullish':
                painter.drawLine(x, center_y + 30, x, center_y + 35)
            else:
                painter.drawLine(x, center_y - 30, x, center_y - 35)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x - 40, center_y + 80, "Closing Marubozu")

        else:
            # Full Marubozu (no shadows)
            if self.pattern_data.get('direction') == 'Bullish':
                painter.setBrush(QColor(100, 255, 100))
                painter.setPen(QPen(QColor(50, 200, 50), 1))
            else:
                painter.setBrush(QColor(255, 100, 100))
                painter.setPen(QPen(QColor(200, 50, 50), 1))

            # Body with no shadows
            painter.drawRect(x - 10, center_y - 30, 20, 60)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x - 30, center_y + 80, "Marubozu (No shadows)")

    def draw_harami_pattern(self, painter, start_x, center_y, candle_width, components):
        """Draw harami pattern"""
        # First candle (large)
        x1 = start_x + candle_width // 2
        if self.pattern_data.get('direction') == 'Bullish':
            # Large bearish, small bullish inside
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x1 - 12, center_y - 30, 24, 60)

            # Second candle (small, inside)
            x2 = x1 + candle_width + 30
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x2 - 6, center_y - 15, 12, 30)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x1 - 15, center_y - 50, "Large Bearish")
            painter.drawText(x2 - 10, center_y - 40, "Small Bullish Inside")

        elif self.pattern_data.get('direction') == 'Bearish':
            # Large bullish, small bearish inside
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x1 - 12, center_y - 30, 24, 60)

            # Second candle (small, inside)
            x2 = x1 + candle_width + 30
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x2 - 6, center_y - 15, 12, 30)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x1 - 15, center_y - 50, "Large Bullish")
            painter.drawText(x2 - 10, center_y - 40, "Small Bearish Inside")

        if 'CROSS' in self.pattern_name:
            # Harami Cross - second candle is doji
            x2 = x1 + candle_width + 30
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x2, center_y - 10, x2, center_y + 10)
            painter.drawLine(x2 - 8, center_y, x2 + 8, center_y)

            painter.setFont(QFont("Arial", 8))
            painter.drawText(x1 - 15, center_y + 80, "Harami Cross Pattern")

    def draw_crows_pattern(self, painter, start_x, center_y, candle_width, components, pattern_name):
        """Draw crows patterns"""
        if '2CROWS' in pattern_name:
            # Two Crows
            x1 = start_x + candle_width // 2
            # First candle (long white)
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            painter.drawRect(x1 - 10, center_y - 25, 20, 50)

            # Gap up
            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
            painter.drawLine(x1 + 15, center_y, x1 + 25, center_y)

            # Second candle (black, opens above, closes within first)
            x2 = x1 + candle_width + 30
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawRect(x2 - 8, center_y - 20, 16, 40)

            # Third candle (black, opens within second, closes below first)
            x3 = x2 + candle_width + 30
            painter.drawRect(x3 - 8, center_y - 15, 16, 30)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x1 - 10, center_y - 40, "1st: White")
            painter.drawText(x2 - 10, center_y - 35, "2nd: Black")
            painter.drawText(x3 - 10, center_y - 30, "3rd: Black")
            painter.drawText(x1 + 20, center_y + 70, "Two Crows Pattern")

        elif '3BLACKCROWS' in pattern_name:
            # Three Black Crows
            for i in range(3):
                x = start_x + i * (candle_width + 30) + candle_width // 2
                painter.setBrush(QColor(255, 100, 100))
                painter.setPen(QPen(QColor(200, 50, 50), 1))
                # Each candle opens within previous body, closes lower
                height = 40 - i * 5
                y_offset = i * 5
                painter.drawRect(x - 8, center_y - 20 + y_offset, 16, height)

                # Shadows
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawLine(x, center_y - 20 + y_offset, x, center_y - 25 + y_offset)
                painter.drawLine(x, center_y - 20 + y_offset + height, x, center_y - 15 + y_offset + height)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(start_x - 10, center_y - 40, "Three Black Crows")

        elif 'IDENTICAL3CROWS' in pattern_name:
            # Identical Three Crows (similar size)
            for i in range(3):
                x = start_x + i * (candle_width + 30) + candle_width // 2
                painter.setBrush(QColor(255, 100, 100))
                painter.setPen(QPen(QColor(200, 50, 50), 1))
                # All candles same size
                painter.drawRect(x - 8, center_y - 20 + i * 5, 16, 40)

                # Shadows
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawLine(x, center_y - 20 + i * 5, x, center_y - 25 + i * 5)
                painter.drawLine(x, center_y - 20 + i * 5 + 40, x, center_y - 15 + i * 5 + 40)

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(start_x - 10, center_y - 50, "Identical Three Crows")

    def draw_soldiers_pattern(self, painter, start_x, center_y, candle_width, components):
        """Draw three white soldiers pattern"""
        for i in range(3):
            x = start_x + i * (candle_width + 30) + candle_width // 2
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            # Each candle opens within previous body, closes higher
            height = 40 + i * 5
            y_offset = -i * 5
            painter.drawRect(x - 8, center_y - 20 + y_offset, 16, height)

            # Shadows
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.drawLine(x, center_y - 20 + y_offset, x, center_y - 25 + y_offset)
            painter.drawLine(x, center_y - 20 + y_offset + height, x, center_y - 15 + y_offset + height)

        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(start_x - 10, center_y - 50, "Three White Soldiers")

    def draw_belthold_pattern(self, painter, start_x, center_y, candle_width, direction):
        """Draw belt hold pattern"""
        x = start_x + candle_width // 2

        if direction == 'Bullish':
            painter.setBrush(QColor(100, 255, 100))
            painter.setPen(QPen(QColor(50, 200, 50), 1))
            # Long white candle opening at low
            painter.drawRect(x - 10, center_y - 30, 20, 60)
            # No lower shadow
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y + 30, x, center_y + 35)  # Small lower shadow
            painter.drawLine(x, center_y - 30, x, center_y - 40)  # Upper shadow

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x - 30, center_y + 80, "Bullish Belt Hold")

        else:  # Bearish
            painter.setBrush(QColor(255, 100, 100))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            # Long black candle opening at high
            painter.drawRect(x - 10, center_y - 30, 20, 60)
            # No upper shadow
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y - 30, x, center_y - 35)  # Small upper shadow
            painter.drawLine(x, center_y + 30, x, center_y + 40)  # Lower shadow

            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x - 30, center_y + 80, "Bearish Belt Hold")

    def draw_generic_pattern(self, painter, start_x, center_y, candle_width, components):
        """Draw generic pattern representation"""
        # Draw specified number of generic candles
        for i in range(components):
            x = start_x + i * (candle_width + 30) + candle_width // 2

            # Alternate colors for visual clarity
            if i % 2 == 0:
                painter.setBrush(QColor(100, 255, 100))
                painter.setPen(QPen(QColor(50, 200, 50), 1))
            else:
                painter.setBrush(QColor(255, 100, 100))
                painter.setPen(QPen(QColor(200, 50, 50), 1))

            # Draw candle body
            body_height = 30 + (i * 5)
            painter.drawRect(x - 8, center_y - body_height // 2, 16, body_height)

            # Draw shadows
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawLine(x, center_y - body_height // 2, x, center_y - body_height // 2 - 10)
            painter.drawLine(x, center_y + body_height // 2, x, center_y + body_height // 2 + 10)

        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(start_x - 10, center_y - 60, f"{components}-candle Pattern")
        painter.drawText(start_x - 10, center_y + 70, self.pattern_name)


class HelpWindow(QMainWindow):
    """Comprehensive help window with pattern explanations"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help - Pattern Explanations")
        self.setGeometry(150, 150, 1400, 900)

        # Initialize pattern data first
        self.pattern_data = {}
        self.load_pattern_descriptions()

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

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search patterns...")
        self.search_box.textChanged.connect(self.filter_patterns)
        search_layout.addWidget(self.search_box)

        left_layout.addLayout(search_layout)

        # Pattern list
        self.pattern_list = QListWidget()
        self.pattern_list.addItems(CANDLE_PATTERNS)
        self.pattern_list.itemSelectionChanged.connect(self.show_pattern_details)
        left_layout.addWidget(self.pattern_list)

        # Application help button
        app_help_btn = QPushButton("Application Help")
        app_help_btn.clicked.connect(self.show_application_help)
        left_layout.addWidget(app_help_btn)

        left_layout.addStretch()

        # Right panel - Details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Title
        self.pattern_title = QLabel("Select a pattern to see details")
        self.pattern_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.pattern_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.pattern_title)

        # Description text area
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setFont(QFont("Arial", 10))
        right_layout.addWidget(self.description_text)

        # Pattern diagram
        self.pattern_diagram = PatternDiagram()
        right_layout.addWidget(self.pattern_diagram)

        # Interpretation
        interpretation_label = QLabel("Interpretation:")
        interpretation_label.setStyleSheet("font-weight: bold; color: #555;")
        right_layout.addWidget(interpretation_label)

        self.interpretation_text = QTextEdit()
        self.interpretation_text.setReadOnly(True)
        self.interpretation_text.setMaximumHeight(100)
        right_layout.addWidget(self.interpretation_text)

        # Reliability and usage
        info_layout = QHBoxLayout()

        # Reliability
        reliability_group = QGroupBox("Reliability")
        reliability_layout = QVBoxLayout()
        self.reliability_label = QLabel("N/A")
        self.reliability_label.setStyleSheet("font-size: 14px;")
        reliability_layout.addWidget(self.reliability_label)
        reliability_group.setLayout(reliability_layout)
        info_layout.addWidget(reliability_group)

        # Category
        category_group = QGroupBox("Category")
        category_layout = QVBoxLayout()
        self.category_label = QLabel("N/A")
        self.category_label.setStyleSheet("font-size: 14px;")
        category_layout.addWidget(self.category_label)
        category_group.setLayout(category_layout)
        info_layout.addWidget(category_group)

        # Pattern Type
        type_group = QGroupBox("Pattern Type")
        type_layout = QVBoxLayout()
        self.type_label = QLabel("N/A")
        self.type_label.setStyleSheet("font-size: 14px;")
        type_layout.addWidget(self.type_label)
        type_group.setLayout(type_layout)
        info_layout.addWidget(type_group)

        # Bullish/Bearish
        direction_group = QGroupBox("Direction")
        direction_layout = QVBoxLayout()
        self.direction_label = QLabel("N/A")
        self.direction_label.setStyleSheet("font-size: 14px;")
        direction_layout.addWidget(self.direction_label)
        direction_group.setLayout(direction_layout)
        info_layout.addWidget(direction_group)

        right_layout.addLayout(info_layout)

        # Add panels to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 1100])

        layout.addWidget(splitter)

        # Select first pattern
        if self.pattern_list.count() > 0:
            self.pattern_list.setCurrentRow(0)

    def load_pattern_descriptions(self):
        """Load pattern descriptions from file"""
        try:
            # Try to load from JSON file
            pattern_file = Path(__file__).parent.parent / 'data' / 'pattern_descriptions.json'

            if pattern_file.exists():
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    self.pattern_data = json.load(f)
            else:
                # Create basic descriptions
                self.pattern_data = self.create_basic_descriptions()

                # Save to file for future use
                pattern_file.parent.mkdir(exist_ok=True)
                with open(pattern_file, 'w', encoding='utf-8') as f:
                    json.dump(self.pattern_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Loaded pattern descriptions")

        except Exception as e:
            logger.error(f"Error loading pattern descriptions: {str(e)}")
            self.pattern_data = self.create_basic_descriptions()

    def create_basic_descriptions(self):
        """Create basic pattern descriptions"""
        patterns = {}

        # Pattern characteristics
        pattern_info = {
            'CDL2CROWS': {
                'description': 'Two Crows pattern: A bearish reversal pattern consisting of three candles in an uptrend.',
                'interpretation': 'Bearish reversal signal indicating potential trend change.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDL3BLACKCROWS': {
                'description': 'Three Black Crows: Three consecutive long black candles closing lower than previous.',
                'interpretation': 'Strong bearish reversal signal after an uptrend.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDL3INSIDE': {
                'description': 'Three Inside Up/Down: A three-candle reversal pattern with a harami in first two candles.',
                'interpretation': 'Bullish reversal (up) or bearish reversal (down) pattern.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Both',
                'components': 3
            },
            'CDL3LINESTRIKE': {
                'description': 'Three-Line Strike: A four-candle continuation pattern.',
                'interpretation': 'Bullish (after downtrend) or bearish (after uptrend) continuation.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Four-candle pattern',
                'direction': 'Both',
                'components': 4
            },
            'CDL3OUTSIDE': {
                'description': 'Three Outside Up/Down: Engulfing pattern followed by confirmation candle.',
                'interpretation': 'Reversal pattern with stronger confirmation.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Both',
                'components': 3
            },
            'CDL3WHITESOLDIERS': {
                'description': 'Three White Soldiers: Three consecutive long white candles with higher closes.',
                'interpretation': 'Strong bullish reversal signal after a downtrend.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bullish',
                'components': 3
            },
            'CDLABANDONEDBABY': {
                'description': 'Abandoned Baby: A doji star that gaps away from previous candle, followed by gap in opposite direction.',
                'interpretation': 'Strong reversal signal, rare but reliable.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Both',
                'components': 3
            },
            'CDLADVANCEBLOCK': {
                'description': 'Advance Block: Three white candles with consecutively smaller bodies.',
                'interpretation': 'Bearish reversal pattern in an uptrend, shows weakening bullish momentum.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDLBELTHOLD': {
                'description': 'Belt Hold: A long candle with no shadow on one side (opening at high for bullish, at low for bearish).',
                'interpretation': 'Strong reversal signal when appearing at trend extremes.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Both',
                'components': 1
            },
            'CDLBREAKAWAY': {
                'description': 'Breakaway: A five-candle pattern indicating trend continuation after brief pause.',
                'interpretation': 'Continuation pattern suggesting resumption of prevailing trend.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Five-candle pattern',
                'direction': 'Both',
                'components': 5
            },
            'CDLCLOSINGMARUBOZU': {
                'description': 'Closing Marubozu: A candle with no shadow at the closing price end.',
                'interpretation': 'Shows strong conviction in the direction of the close.',
                'reliability': 'Medium',
                'category': 'Momentum',
                'type': 'Single-candle pattern',
                'direction': 'Both',
                'components': 1
            },
            'CDLCONCEALBABYSWALL': {
                'description': 'Concealing Baby Swallow: A rare four-candle pattern with specific characteristics.',
                'interpretation': 'Bearish reversal pattern, very rare but highly reliable.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Four-candle pattern',
                'direction': 'Bearish',
                'components': 4
            },
            'CDLCOUNTERATTACK': {
                'description': 'Counterattack Lines: Two candles of opposite color with same closing price.',
                'interpretation': 'Indicates market equilibrium, potential reversal point.',
                'reliability': 'Low-Medium',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLDARKCLOUDCOVER': {
                'description': 'Dark Cloud Cover: A bearish reversal pattern with a black candle opening above then closing below midpoint of previous white candle.',
                'interpretation': 'Bearish reversal signal in an uptrend.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Bearish',
                'components': 2
            },
            'CDLDOJI': {
                'description': 'Doji: A candle where open and close are virtually equal, creating a cross or plus sign shape.',
                'interpretation': 'Indicates indecision, potential trend reversal or consolidation.',
                'reliability': 'Medium',
                'category': 'Indecision',
                'type': 'Single-candle pattern',
                'direction': 'Neutral',
                'components': 1
            },
            'CDLDOJISTAR': {
                'description': 'Doji Star: A doji that gaps away from previous candle.',
                'interpretation': 'Stronger reversal signal than regular doji, especially at trend extremes.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLDRAGONFLYDOJI': {
                'description': 'Dragonfly Doji: A doji with long lower shadow and no upper shadow.',
                'interpretation': 'Bullish reversal signal when appearing after downtrend.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Bullish',
                'components': 1
            },
            'CDLENGULFING': {
                'description': 'Engulfing Pattern: A candle that completely engulfs the body of previous candle.',
                'interpretation': 'Strong reversal signal. Bullish when white engulfs black, bearish when black engulfs white.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLEVENINGDOJISTAR': {
                'description': 'Evening Doji Star: A three-candle bearish reversal pattern with doji in middle.',
                'interpretation': 'Bearish reversal signal at the end of an uptrend.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDLEVENINGSTAR': {
                'description': 'Evening Star: A three-candle bearish reversal pattern similar to evening doji star but with small body in middle.',
                'interpretation': 'Bearish reversal signal, less strong than evening doji star.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDLGAPSIDESIDEWHITE': {
                'description': 'Up/Down-Gap Side-by-Side White Lines: Two white candles gapping in same direction.',
                'interpretation': 'Continuation pattern showing sustained momentum.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Two-candle pattern',
                'direction': 'Bullish',
                'components': 2
            },
            'CDLGRAVESTONEDOJI': {
                'description': 'Gravestone Doji: A doji with long upper shadow and no lower shadow.',
                'interpretation': 'Bearish reversal signal when appearing after uptrend.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Bearish',
                'components': 1
            },
            'CDLHAMMER': {
                'description': 'Hammer: A candle with small body at top and long lower shadow (at least twice the body length).',
                'interpretation': 'Bullish reversal signal when appearing in downtrend.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Bullish',
                'components': 1
            },
            'CDLHANGINGMAN': {
                'description': 'Hanging Man: Similar to hammer but appears in uptrend.',
                'interpretation': 'Bearish reversal signal when appearing after uptrend.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Bearish',
                'components': 1
            },
            'CDLHARAMI': {
                'description': 'Harami: A small candle completely inside range of previous large candle.',
                'interpretation': 'Potential reversal signal showing decrease in momentum.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLHARAMICROSS': {
                'description': 'Harami Cross: A harami pattern where second candle is a doji.',
                'interpretation': 'Stronger reversal signal than regular harami.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLHIGHWAVE': {
                'description': 'High Wave: A candle with very long upper and lower shadows and small body.',
                'interpretation': 'Indicates high volatility and indecision.',
                'reliability': 'Low',
                'category': 'Indecision',
                'type': 'Single-candle pattern',
                'direction': 'Neutral',
                'components': 1
            },
            'CDLHIKKAKE': {
                'description': 'Hikkake Pattern: A pattern that traps traders in false breakout then reverses.',
                'interpretation': 'Continuation pattern that fools traders before resuming trend.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Complex pattern',
                'direction': 'Both',
                'components': 3
            },
            'CDLHIKKAKEMOD': {
                'description': 'Modified Hikkake: Variation of hikkake pattern.',
                'interpretation': 'Similar to hikkake but with modified characteristics.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Complex pattern',
                'direction': 'Both',
                'components': 3
            },
            'CDLHOMINGPIGEON': {
                'description': 'Homing Pigeon: Similar to harami but both candles are black (bearish version).',
                'interpretation': 'Bullish reversal signal in downtrend.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Bullish',
                'components': 2
            },
            'CDLIDENTICAL3CROWS': {
                'description': 'Identical Three Crows: Three black candles of similar size closing consecutively lower.',
                'interpretation': 'Extremely bearish reversal pattern.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDLINNECK': {
                'description': 'In-Neck Pattern: A bearish line (black candle) that closes just into body of previous white candle.',
                'interpretation': 'Bearish continuation pattern.',
                'reliability': 'Low-Medium',
                'category': 'Continuation',
                'type': 'Two-candle pattern',
                'direction': 'Bearish',
                'components': 2
            },
            'CDLINVERTEDHAMMER': {
                'description': 'Inverted Hammer: Similar to shooting star but appears in downtrend.',
                'interpretation': 'Bullish reversal signal when appearing after downtrend.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Bullish',
                'components': 1
            },
            'CDLKICKING': {
                'description': 'Kicking: Two marubozu candles gapping in opposite directions.',
                'interpretation': 'Strong reversal signal based on gap direction.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLKICKINGBYLENGTH': {
                'description': 'Kicking by Length: Kicking pattern where second candle is longer.',
                'interpretation': 'Even stronger reversal signal than regular kicking.',
                'reliability': 'Very High',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLLADDERBOTTOM': {
                'description': 'Ladder Bottom: A five-candle pattern with specific sequence of black and white candles.',
                'interpretation': 'Bullish reversal pattern after extended downtrend.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Five-candle pattern',
                'direction': 'Bullish',
                'components': 5
            },
            'CDLLONGLEGGEDDOJI': {
                'description': 'Long-Legged Doji: A doji with very long upper and lower shadows.',
                'interpretation': 'High indecision, potential major reversal point.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Neutral',
                'components': 1
            },
            'CDLLONGLINE': {
                'description': 'Long Line (Long Day): A candle with very long body relative to recent candles.',
                'interpretation': 'Shows strong conviction in direction of candle.',
                'reliability': 'Medium',
                'category': 'Momentum',
                'type': 'Single-candle pattern',
                'direction': 'Both',
                'components': 1
            },
            'CDLMARUBOZU': {
                'description': 'Marubozu: A candle with no shadows (wicks) at either end.',
                'interpretation': 'Extreme momentum in direction of candle.',
                'reliability': 'High',
                'category': 'Momentum',
                'type': 'Single-candle pattern',
                'direction': 'Both',
                'components': 1
            },
            'CDLMATCHINGLOW': {
                'description': 'Matching Low: Two black candles with similar lows.',
                'interpretation': 'Bullish reversal signal suggesting support level.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Bullish',
                'components': 2
            },
            'CDLMATHOLD': {
                'description': 'Mat Hold: A bullish continuation pattern with gap up.',
                'interpretation': 'Bullish continuation after brief consolidation.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Five-candle pattern',
                'direction': 'Bullish',
                'components': 5
            },
            'CDLMORNINGDOJISTAR': {
                'description': 'Morning Doji Star: Bullish counterpart to evening doji star.',
                'interpretation': 'Bullish reversal signal at end of downtrend.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bullish',
                'components': 3
            },
            'CDLMORNINGSTAR': {
                'description': 'Morning Star: Bullish counterpart to evening star.',
                'interpretation': 'Bullish reversal signal, less strong than morning doji star.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bullish',
                'components': 3
            },
            'CDLONNECK': {
                'description': 'On-Neck Pattern: Similar to in-neck but closes at low of previous candle.',
                'interpretation': 'Bearish continuation pattern.',
                'reliability': 'Low',
                'category': 'Continuation',
                'type': 'Two-candle pattern',
                'direction': 'Bearish',
                'components': 2
            },
            'CDLPIERCING': {
                'description': 'Piercing Line: Bullish counterpart to dark cloud cover.',
                'interpretation': 'Bullish reversal signal in downtrend.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Bullish',
                'components': 2
            },
            'CDLRICKSHAWMAN': {
                'description': 'Rickshaw Man: Similar to long-legged doji with very long shadows.',
                'interpretation': 'Extreme indecision, often at major turning points.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Neutral',
                'components': 1
            },
            'CDLRISEFALL3METHODS': {
                'description': 'Rising/Falling Three Methods: A continuation pattern with one long candle, three small counter-trend candles, then another long candle in original direction.',
                'interpretation': 'Continuation pattern showing pause before trend resumption.',
                'reliability': 'Medium-High',
                'category': 'Continuation',
                'type': 'Five-candle pattern',
                'direction': 'Both',
                'components': 5
            },
            'CDLSEPARATINGLINES': {
                'description': 'Separating Lines: Two candles of opposite color with same opening price.',
                'interpretation': 'Continuation pattern showing trend resumption.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Two-candle pattern',
                'direction': 'Both',
                'components': 2
            },
            'CDLSHOOTINGSTAR': {
                'description': 'Shooting Star: A candle with small body at bottom, long upper shadow, and little to no lower shadow.',
                'interpretation': 'Bearish reversal signal when appearing in uptrend.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Bearish',
                'components': 1
            },
            'CDLSHORTLINE': {
                'description': 'Short Line (Short Day): A candle with very small body relative to recent candles.',
                'interpretation': 'Indicates lack of conviction, potential trend change.',
                'reliability': 'Low',
                'category': 'Indecision',
                'type': 'Single-candle pattern',
                'direction': 'Neutral',
                'components': 1
            },
            'CDLSPINNINGTOP': {
                'description': 'Spinning Top: A candle with small body and moderate shadows.',
                'interpretation': 'Indecision, potential trend pause or reversal.',
                'reliability': 'Low',
                'category': 'Indecision',
                'type': 'Single-candle pattern',
                'direction': 'Neutral',
                'components': 1
            },
            'CDLSTALLEDPATTERN': {
                'description': 'Stalled Pattern: Similar to advance block but with specific characteristics.',
                'interpretation': 'Bearish reversal showing loss of upward momentum.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDLSTICKSANDWICH': {
                'description': 'Stick Sandwich: Two black candles surrounding a white candle, all with same closing price.',
                'interpretation': 'Bullish reversal pattern.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bullish',
                'components': 3
            },
            'CDLTAKURI': {
                'description': 'Takuri (Dragonfly Doji with very long lower shadow).',
                'interpretation': 'Strong bullish reversal signal.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Single-candle pattern',
                'direction': 'Bullish',
                'components': 1
            },
            'CDLTASUKIGAP': {
                'description': 'Tasuki Gap: A continuation pattern with gap followed by counter-trend candle that doesnt fill gap.',
                'interpretation': 'Continuation pattern showing trend strength.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Three-candle pattern',
                'direction': 'Both',
                'components': 3
            },
            'CDLTHRUSTING': {
                'description': 'Thrusting Pattern: Similar to piercing line but closes below midpoint of previous candle.',
                'interpretation': 'Weaker bullish signal than piercing line.',
                'reliability': 'Low-Medium',
                'category': 'Reversal',
                'type': 'Two-candle pattern',
                'direction': 'Bullish',
                'components': 2
            },
            'CDLTRISTAR': {
                'description': 'Tristar: Three doji candles in a row.',
                'interpretation': 'Extreme indecision, major reversal likely.',
                'reliability': 'High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Both',
                'components': 3
            },
            'CDLUNIQUE3RIVER': {
                'description': 'Unique Three River: A three-candle pattern with specific sequence.',
                'interpretation': 'Bullish reversal signal after downtrend.',
                'reliability': 'Medium',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bullish',
                'components': 3
            },
            'CDLUPSIDEGAP2CROWS': {
                'description': 'Upside Gap Two Crows: A bearish reversal pattern with gap up followed by two black candles.',
                'interpretation': 'Bearish reversal signal in uptrend.',
                'reliability': 'Medium-High',
                'category': 'Reversal',
                'type': 'Three-candle pattern',
                'direction': 'Bearish',
                'components': 3
            },
            'CDLXSIDEGAP3METHODS': {
                'description': 'Upside/Downside Gap Three Methods: A continuation pattern with gap followed by consolidation.',
                'interpretation': 'Continuation pattern showing trend resumption after pause.',
                'reliability': 'Medium',
                'category': 'Continuation',
                'type': 'Complex pattern',
                'direction': 'Both',
                'components': 5
            }
        }

        # Add all patterns
        for pattern, info in pattern_info.items():
            patterns[pattern] = info

        # Add any missing patterns with generic description
        for pattern in CANDLE_PATTERNS:
            if pattern not in patterns:
                patterns[pattern] = {
                    'description': f'{pattern}: Japanese candlestick pattern for technical analysis.',
                    'interpretation': 'Trading signal based on price action analysis.',
                    'reliability': 'Medium',
                    'category': 'Technical',
                    'type': 'Candlestick pattern',
                    'direction': 'Both',
                    'components': 1
                }

        return patterns

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

        # Make sure pattern_data is loaded
        if not hasattr(self, 'pattern_data') or not self.pattern_data:
            self.load_pattern_descriptions()

        pattern_info = self.pattern_data.get(pattern_name, {})

        # Update title
        self.pattern_title.setText(pattern_name)

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
        if direction == 'Bullish':
            self.direction_label.setStyleSheet("color: green; font-weight: bold;")
        elif direction == 'Bearish':
            self.direction_label.setStyleSheet("color: red; font-weight: bold;")
        elif direction == 'Both':
            self.direction_label.setStyleSheet("color: blue; font-weight: bold;")
        else:
            self.direction_label.setStyleSheet("color: gray;")

        # Update diagram with pattern data
        self.pattern_diagram.set_pattern(pattern_name, pattern_info)

    def show_application_help(self):
        """Show application help"""
        help_text = """
        <h1>MOEX & Crypto Backtest System - Help</h1>

        <h2>1. Application Overview</h2>
        <p>This application allows you to backtest trading strategies based on Japanese candlestick patterns on MOEX and cryptocurrency markets.</p>

        <h2>2. Getting Started</h2>
        <h3>Step 1: Create a Strategy</h3>
        <ul>
            <li>Click "New" in Strategy Management</li>
            <li>Give your strategy a name</li>
            <li>Select patterns to include</li>
            <li>Choose entry and exit rules</li>
            <li>Set risk parameters</li>
            <li>Click "Save"</li>
        </ul>

        <h3>Step 2: Fetch Data</h3>
        <ul>
            <li>Select market (MOEX or Cryptocurrency)</li>
            <li>Enter ticker/symbol (e.g., SBER for MOEX, BTCUSDT for crypto)</li>
            <li>Choose timeframe (1m to Monthly)</li>
            <li>Set date range</li>
            <li>Adjust pattern detection threshold</li>
            <li>Click "Fetch Data"</li>
        </ul>

        <h3>Step 3: Run Backtest</h3>
        <ul>
            <li>Select your strategy</li>
            <li>Set capital and commission parameters</li>
            <li>Click "Run Backtest"</li>
        </ul>

        <h3>Step 4: Analyze Results</h3>
        <ul>
            <li>View performance metrics</li>
            <li>Click "Show Chart" for visual analysis</li>
            <li>Save results to Excel or Database</li>
            <li>Use "View Database" to review historical tests</li>
        </ul>

        <h2>3. Features</h2>
        <h3>Strategy Management</h3>
        <p>Create, edit, delete, and save trading strategies with custom parameters.</p>

        <h3>Multi-Market Support</h3>
        <p>Test on MOEX (Russian stock market) and cryptocurrency markets (via Bybit).</p>

        <h3>Pattern Detection</h3>
        <p>61 candlestick patterns from TA-Lib library with adjustable detection threshold.</p>

        <h3>Risk Management</h3>
        <ul>
            <li>Position sizing as percentage of capital</li>
            <li>Stop loss and take profit levels</li>
            <li>Commission and slippage calculation</li>
            <li>Multiple exit rules (time-based, opposite pattern, etc.)</li>
        </ul>

        <h3>Visualization</h3>
        <ul>
            <li>Interactive candlestick charts</li>
            <li>Trade entry/exit markers</li>
            <li>Technical indicators (MACD, RSI, Bollinger Bands)</li>
            <li>Zoom and pan functionality</li>
        </ul>

        <h3>Data Management</h3>
        <ul>
            <li>Save results to Excel with charts</li>
            <li>Store strategies and results in SQLite database</li>
            <li>Export data to CSV</li>
        </ul>

        <h2>4. Pattern Explanations</h2>
        <p>Use the left panel to browse all 61 candlestick patterns. Each pattern includes:</p>
        <ul>
            <li>Detailed description</li>
            <li>Trading interpretation</li>
            <li>Reliability rating</li>
            <li>Pattern category and type</li>
            <li>Visual representation</li>
        </ul>

        <h2>5. Tips for Effective Backtesting</h2>
        <ol>
            <li><b>Use sufficient data:</b> Test on at least 1-2 years of data for reliable results</li>
            <li><b>Consider market conditions:</b> Strategies may perform differently in bull/bear markets</li>
            <li><b>Include commissions:</b> Always account for trading costs</li>
            <li><b>Test multiple timeframes:</b> Strategies may work better on certain timeframes</li>
            <li><b>Combine patterns:</b> Using multiple patterns together can improve signal quality</li>
            <li><b>Set realistic expectations:</b> No strategy works 100% of the time</li>
        </ol>

        <h2>6. Troubleshooting</h2>
        <p><b>No data fetched:</b> Check your internet connection and ensure the ticker/symbol is correct.</p>
        <p><b>Chart not showing:</b> Make sure you have matplotlib and mplfinance installed.</p>
        <p><b>Database errors:</b> Check file permissions for the database folder.</p>
        <p><b>Pattern not detected:</b> Adjust the pattern threshold slider.</p>

        <h2>7. Support</h2>
        <p>For issues or feature requests, please check the application logs in the logs/ directory.</p>
        <p>Log files are rotated weekly and contain detailed information about errors and user actions.</p>
        """

        # Create dialog with help text
        dialog = QDialog(self)
        dialog.setWindowTitle("Application Help")
        dialog.setGeometry(200, 200, 1000, 800)

        layout = QVBoxLayout(dialog)

        # Use QTextEdit for rich text display
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(help_text)

        layout.addWidget(text_edit)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()