"""Widgets de grafico reutilizaveis, baseados em PyQtGraph, com tooltip,
legenda, titulo e suporte a tema claro/escuro."""
from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from config.constants import Theme
from widgets.theme import tokens_for

SERIES_COLORS = ["#4F6EF7", "#16A34A", "#D97706", "#DC2626", "#2563EB", "#9333EA"]


def configure_pyqtgraph_theme(theme: Theme) -> None:
    tokens = tokens_for(theme)
    pg.setConfigOption("background", tokens.surface)
    pg.setConfigOption("foreground", tokens.text_primary)
    pg.setConfigOptions(antialias=True)


class _CategoryAxis(pg.AxisItem):
    def __init__(self, labels: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._labels = labels

    def set_labels(self, labels: list[str]) -> None:
        self._labels = labels

    def tickStrings(self, values, scale, spacing):
        result = []
        for v in values:
            index = int(round(v))
            if 0 <= index < len(self._labels):
                result.append(self._labels[index])
            else:
                result.append("")
        return result


class BaseChartWidget(pg.PlotWidget):
    """Grafico base com titulo, legenda e tooltip ao passar o mouse."""

    def __init__(self, title: str = "", theme: Theme = Theme.LIGHT, parent=None):
        self._x_labels: list[str] = []
        self._category_axis = _CategoryAxis(self._x_labels, orientation="bottom")
        super().__init__(parent, axisItems={"bottom": self._category_axis})

        self._theme = theme
        tokens = tokens_for(theme)

        self.setMinimumHeight(240)
        self.setMenuEnabled(False)
        self.showGrid(x=False, y=True, alpha=0.15)
        self.setTitle(title, color=tokens.text_primary, size="12pt")
        self.getAxis("left").setPen(pg.mkPen(tokens.border))
        self.getAxis("bottom").setPen(pg.mkPen(tokens.border))
        self.getAxis("left").setTextPen(pg.mkPen(tokens.text_secondary))
        self.getAxis("bottom").setTextPen(pg.mkPen(tokens.text_secondary))

        self._legend = self.addLegend(offset=(10, 5))
        self._tooltip = pg.TextItem(anchor=(0, 1), color=tokens.text_primary)
        self._tooltip.setVisible(False)
        self.addItem(self._tooltip, ignoreBounds=True)

        self._proxy = pg.SignalProxy(
            self.scene().sigMouseMoved, rateLimit=30, slot=self._on_mouse_moved
        )
        self._points: list[tuple[float, float, str]] = []

    def set_x_labels(self, labels: list[str]) -> None:
        self._x_labels = labels
        self._category_axis.set_labels(labels)

    def clear_chart(self) -> None:
        self.clear()
        self._legend.clear()
        self._points = []
        self.addItem(self._tooltip, ignoreBounds=True)
        self._tooltip.setVisible(False)

    def register_points(self, points: list[tuple[float, float, str]]) -> None:
        """`points`: lista de (x, y, texto_tooltip) usada para o hover."""
        self._points.extend(points)

    def _on_mouse_moved(self, event) -> None:
        if not self._points:
            return
        pos = event[0]
        if not self.plotItem.vb.sceneBoundingRect().contains(pos):
            self._tooltip.setVisible(False)
            return
        mouse_point = self.plotItem.vb.mapSceneToView(pos)
        nearest = min(self._points, key=lambda p: abs(p[0] - mouse_point.x()))
        if abs(nearest[0] - mouse_point.x()) > 0.6:
            self._tooltip.setVisible(False)
            return
        self._tooltip.setText(nearest[2])
        self._tooltip.setPos(nearest[0], nearest[1])
        self._tooltip.setVisible(True)


class LineChartWidget(BaseChartWidget):
    """Grafico de linha, uma ou mais series (ex.: previsto x realizado)."""

    def set_series(
        self,
        x_labels: list[str],
        series: dict[str, list[float]],
        value_formatter=lambda v: f"{v:.1f}",
    ) -> None:
        self.clear_chart()
        self.set_x_labels(x_labels)
        xs = list(range(len(x_labels)))

        for idx, (name, values) in enumerate(series.items()):
            color = SERIES_COLORS[idx % len(SERIES_COLORS)]
            pen = pg.mkPen(color=color, width=2)
            self.plot(
                xs, values, pen=pen, name=name,
                symbol="o", symbolSize=6, symbolBrush=color, symbolPen=color,
            )
            points = [
                (x, y, f"{name}\n{x_labels[x]}: {value_formatter(y)}")
                for x, y in zip(xs, values)
            ]
            self.register_points(points)


class BarChartWidget(BaseChartWidget):
    """Grafico de barras agrupadas (ex.: horas normais x extras por mes)."""

    def set_series(
        self,
        x_labels: list[str],
        series: dict[str, list[float]],
        value_formatter=lambda v: f"{v:.1f}",
    ) -> None:
        self.clear_chart()
        self.set_x_labels(x_labels)
        n_series = max(len(series), 1)
        bar_width = 0.7 / n_series
        xs = list(range(len(x_labels)))

        for idx, (name, values) in enumerate(series.items()):
            color = SERIES_COLORS[idx % len(SERIES_COLORS)]
            offset = (idx - (n_series - 1) / 2) * bar_width
            positions = [x + offset for x in xs]
            bar_item = pg.BarGraphItem(
                x=positions, height=values, width=bar_width * 0.9, brush=color, pen=color
            )
            self.addItem(bar_item)
            self._legend.addItem(pg.BarGraphItem(x=[], height=[], width=1, brush=color), name)
            points = [
                (positions[i], values[i], f"{name}\n{x_labels[i]}: {value_formatter(values[i])}")
                for i in range(len(values))
            ]
            self.register_points(points)
