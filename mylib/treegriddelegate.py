#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""ARUP - Another bulk Rename Utility with Python
Author: cdhigh <https://github.com/cdhigh>
"""
from PyQt5.QtWidgets import QStyle, QStyledItemDelegate
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtCore import Qt

#Add a grid to QTreeView/QTreeWidget, more like a table
class TreeGridDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        pen = QPen()
        pen.setWidth(1)
        pen.setColor(QColor(0xc6, 0xdb, 0xb5))
        painter.setPen(pen)
        painter.drawRect(option.rect)
    
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if (option.state & QStyle.State_Selected):
            option.font.setBold(True)

        row = index.row()
        col = index.column()
        model = index.model()
        if col != 0 and model.data(model.index(row, 0), Qt.CheckStateRole) == Qt.Unchecked:
            option.font.setStrikeOut(True)
