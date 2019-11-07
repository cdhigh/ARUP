#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""ARUP - Another bulk Rename Utility with embedded Python interpreter
Snippets Manager
Author: cdhigh <https://github.com/cdhigh>
"""
import os, shutil
from PyQt5.QtCore import Qt, pyqtSignal, QItemSelectionModel
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QMessageBox, QInputDialog, QMenu
from ui.ui_dlgSnippetsMgr import Ui_dlgSnippetsMgr
from mylib.commutils import str_to_int, str_to_float, local_time
from mylib.highlighter import PythonHighlighter, CODE_FONT_FAMILY, CODE_FONT_SIZE
from mylib.treegriddelegate import TreeGridDelegate
from dbmodule import *

class SnippetsMgrDialog(QDialog, Ui_dlgSnippetsMgr):
    sigUseCodeSnippet = pyqtSignal(str) #Send a signal to the caller to use a code snippet

    COL_ITEM_ID = 0
    COL_ITEM_NO = 1
    COL_ITEM_NAME = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.Dialog | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.initListAndCodeWidget()
        self.populateListWidget()
        self.connectSignals()

    #Init trePreview widget
    def initListAndCodeWidget(self):
        self.spltListAndCode.setStretchFactor(0, 4)
        self.spltListAndCode.setStretchFactor(1, 6)
        self.spltCodeAndDesc.setStretchFactor(0, 7)
        self.spltCodeAndDesc.setStretchFactor(1, 3)
        self.treSnippets.setColumnCount(3)
        self.treSnippets.setHeaderLabels(['Id', 'No', 'Name'])
        self.treSnippets.setColumnHidden(self.COL_ITEM_ID, True)
        self.treSnippets.setColumnWidth(self.COL_ITEM_NO, 70)
        self.treeGridDelegateforPreview = TreeGridDelegate(self)
        self.treSnippets.setItemDelegate(self.treeGridDelegateforPreview)
        
        font = QFont(CODE_FONT_FAMILY, CODE_FONT_SIZE)
        metrics = QFontMetrics(font)
        self.txtCode.setFont(font)
        self.txtCode.setTabStopWidth(4 * metrics.width(' ')) #set tab stop with 4 spaces
        self.highlighter = PythonHighlighter(self.txtCode.document())
        
    def populateListWidget(self, searchTxt=None):
        self.treSnippets.clear()
        
        if not searchTxt:
            itemList = list(Snippet.select().order_by(Snippet.last_used.desc()))
        elif searchTxt.startswith('inname:'):
            searchTxt = searchTxt[len('inname:'):]
            itemList = list(Snippet.select().where(Snippet.name.contains(searchTxt)).order_by(Snippet.last_used.desc()))
        elif searchTxt.startswith('incode:'):
            searchTxt = searchTxt[len('incode:'):]
            itemList = list(Snippet.select().where(Snippet.code.contains(searchTxt)).order_by(Snippet.last_used.desc()))
        elif searchTxt.startswith('indesc:'):
            searchTxt = searchTxt[len('indesc:'):]
            itemList = list(Snippet.select().where(Snippet.description.contains(searchTxt)).order_by(Snippet.last_used.desc()))
        else: #Auto
            itemList = list(Snippet.select().where(Snippet.name.contains(searchTxt)).order_by(Snippet.last_used.desc()))
            if len(itemList) == 0:
                itemList = list(Snippet.select().where(Snippet.code.contains(searchTxt) | Snippet.name.contains(searchTxt)).order_by(Snippet.last_used.desc()))

        for idx, item in enumerate(itemList):
            widgetItem = QTreeWidgetItem([str(item.id), str(idx + 1), item.name])
            self.treSnippets.addTopLevelItem(widgetItem)

        if self.treSnippets.topLevelItemCount() > 0:
            model = self.treSnippets.model()
            self.txtCode.document().setModified(False)
            self.txtDesc.document().setModified(False)
            self.treSnippets_currentItemChanged(self.treSnippets.topLevelItem(0))
            self.treSnippets.selectionModel().select(model.index(0, 0), QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

    #connect signals of widgets
    def connectSignals(self):
        self.btnSave.pressed.connect(self.btnSave_pressed)
        self.btnUse.pressed.connect(self.btnUse_pressed)
        self.btnRename.pressed.connect(self.btnRename_pressed)
        self.btnDelete.pressed.connect(self.btnDelete_pressed)
        self.btnClose.pressed.connect(self.btnClose_pressed)
        self.txtSearch.textChanged.connect(self.txtSearch_textChanged)
        self.treSnippets.currentItemChanged.connect(self.treSnippets_currentItemChanged)
        
    def btnSave_pressed(self):
        self.saveCurrentItem()

    #Use this code snippet for rename
    def btnUse_pressed(self):
        item = self.treSnippets.currentItem()
        if not item:
            return

        id_ = int(item.text(self.COL_ITEM_ID))
        dbItem = Snippet.getById(id_)
        if not dbItem:
            return

        if self.txtCode.document().isModified() or self.txtDesc.document().isModified():
            ret = QMessageBox.question(self, 'Item modified', 'The item content has been modified, do you want to save it?')
            if ret == QMessageBox.Yes:
                self.saveCurrentItem()

        self.sigUseCodeSnippet.emit(self.txtCode.toPlainText().replace('\t', '    '))
        dbItem.last_used = datetime.datetime.now()
        dbItem.save()
        self.close()

    #Rename the code snippet
    def btnRename_pressed(self):
        item = self.treSnippets.currentItem()
        if not item:
            return

        id_ = int(item.text(self.COL_ITEM_ID))
        name = item.text(self.COL_ITEM_NAME)
        nameText, ok = QInputDialog.getText(self, 'Name', 'Please input the name for this snippet. recommend provide the name in detail.', text=name)
        if nameText and ok:
            item.setText(self.COL_ITEM_NAME, nameText)
            dbItem = Snippet.getById(id_)
            if dbItem:
                dbItem.name = nameText
                dbItem.modified_date = datetime.datetime.now()
                dbItem.save()

    #confirm to delete one item
    def btnDelete_pressed(self):
        item = self.treSnippets.currentItem()
        if not item:
            return

        index = self.treSnippets.indexOfTopLevelItem(item)
        if index < 0:
            return

        ret = QMessageBox.question(self, 'Confirm to delete', 'The item will be removed, do you want to continue?\n"%s"' % item.text(self.COL_ITEM_NAME))
        if ret == QMessageBox.Yes:
            self.treSnippets.takeTopLevelItem(index)
            Snippet.delete().where(Snippet.id == int(item.text(self.COL_ITEM_ID))).execute()
            self.txtCode.setPlainText('')
            self.txtDesc.setPlainText('')
            self.txtCode.document().setModified(False)
            self.txtDesc.document().setModified(False)

    def btnClose_pressed(self):
        self.close()

    def txtSearch_textChanged(self, txt=None):
        self.populateListWidget(self.txtSearch.text())

        
    #user activated an item, get code text and desc text from database and populate the textbox
    def treSnippets_currentItemChanged(self, current, previous=None):
        id_ = current.text(self.COL_ITEM_ID) if current else ''
        if not id_:
            return

        #Save modified content
        codeDoc = self.txtCode.document()
        descDoc = self.txtDesc.document()
        if codeDoc.isModified() or descDoc.isModified():
            ret = QMessageBox.question(self, 'Item modified', 'The item content has been modified, do you want to save it?')
            if ret == QMessageBox.Yes:
                self.saveCurrentItem()

        dbItem = Snippet.getById(id_)
        if dbItem:
            self.txtCode.setPlainText(dbItem.code)
            self.txtDesc.setPlainText(dbItem.description)
            codeDoc.setModified(False)
            descDoc.setModified(False)

    def saveCurrentItem(self):
        item = self.treSnippets.currentItem()
        if not item:
            return

        id_ = int(item.text(self.COL_ITEM_ID))
        dbItem = Snippet.getById(id_)
        if not dbItem:
            return

        codeDoc = self.txtCode.document()
        descDoc = self.txtDesc.document()
        
        dirty = False
        if codeDoc.isModified():
            dbItem.code = self.txtCode.toPlainText()
            dirty = True

        if descDoc.isModified() and descNode is not None:
            dbItem.description = self.txtDesc.toPlainText()
            dirty = True

        if dirty:
            dbItem.modified_date = datetime.datetime.now()
            dbItem.save()
            codeDoc.setModified(False)
            descDoc.setModified(False)
