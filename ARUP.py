#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""ARUP - Another bulk Rename Utility with embedded Python interpreter
Main dialog
Author: cdhigh <https://github.com/cdhigh>
"""

__Version__ = '0.2'

import os, sys, builtins, re, fnmatch, pickle, types, traceback, copy, datetime, hashlib, uuid, shutil, locale, zipfile
from functools import partial
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QDialog, QFileDialog, QTreeWidgetItem, QMessageBox, QInputDialog, QMenu
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QBrush, QColor, QFontMetrics, QFont, QSyntaxHighlighter, QTextCursor, QCursor
from ui.ui_main import Ui_dlgMain
from mylib.commutils import str_to_int, str_to_float, local_time, AttributeDict
from mylib.chineseNumToArab import changeChineseNumToArab
from mylib.highlighter import PythonHighlighter, CODE_FONT_FAMILY, CODE_FONT_SIZE
from mylib.treegriddelegate import TreeGridDelegate
from mylib.xpinyin import Pinyin
from mylib.tinytag import TinyTag
    
appDir = os.path.dirname(os.path.realpath(__file__))
builtins.__dict__['appDir'] = appDir #for dbmodule

from dbmodule import *
import snippetsMgr

pyQtPath = os.path.dirname(os.path.abspath(QtWidgets.__file__))
QtWidgets.QApplication.addLibraryPath(os.path.join(pyQtPath, 'plugins'))
try: QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
except: pass

app = QtWidgets.QApplication(sys.argv)
app.setWindowIcon(QtGui.QIcon(":/res/app_icon.ico"))
app.lastWindowClosed.connect(app.quit)

APP_DATA_DIR = os.path.join(appDir, 'data')
LAST_RENAME_FILE = os.path.join(APP_DATA_DIR, 'last_rename.pkl')
LAST_DIR_FILE = os.path.join(APP_DATA_DIR, 'last_directory.tmp')

#Main Dialog
class MainDialog(QDialog, Ui_dlgMain):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.Dialog | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle('ARUP - Another bulk Rename Utility with embedded Python interpreter [%s@cdhigh]' % __Version__)

        self.dirName = '' #current directory name
        self.allFileList = [] #All files in current directory (unfiltered, unsorted)
        self.pinyin = None #instance of xpinyin.Pinyin()
        self.recentSnippetsMenuInited = False

        self.initPreviewWidget()
        self.initComboBoxWidget()
        self.initCodeWidget()
        self.initDataDirectory()
        self.createMenu()
        
        self.connectSignals()

    def connectSignals(self):
        self.txtDirectory.returnPressed.connect(self.txtDirectory_returnPressed)
        self.btnDirectory.pressed.connect(self.btnDirectory_pressed)
        self.btnPreview.pressed.connect(self.btnPreview_pressed)
        self.btnStart.pressed.connect(self.btnStart_pressed)
        self.btnUndo.pressed.connect(self.btnUndo_pressed)
        self.btnSnippet.pressed.connect(self.btnSnippet_pressed)
        self.trePreview.itemDoubleClicked.connect(self.trePreview_itemDoubleClicked)
        self.btnMoveUp.pressed.connect(self.btnMoveUp_pressed)
        self.btnMoveDown.pressed.connect(self.btnMoveDown_pressed)
        self.cmbFilter.currentTextChanged.connect(self.populateFileListbox)
        self.cmbSort.currentTextChanged.connect(self.populateFileListbox)
        self.txtCode.installEventFilter(self)

    #Init trePreview widget
    def initPreviewWidget(self):
        self.spltFileAndCode.setStretchFactor(0, 6)
        self.spltFileAndCode.setStretchFactor(1, 4)
        self.trePreview.setColumnCount(3)
        self.trePreview.setHeaderLabels(['No', 'File name', 'New name'])
        self.trePreview.setColumnWidth(0, 70)
        self.trePreview.setColumnWidth(1, 250)
        self.treeGridDelegateforPreview = TreeGridDelegate(self)
        self.trePreview.setItemDelegate(self.treeGridDelegateforPreview)

    #populate comboboxs
    def initComboBoxWidget(self):
        self.sortFuncMap = {
            'Auto': self.sortFileList,
            'Auto [down]': partial(self.sortFileList, reverse=True),
            'by Chinese num': partial(self.sortFileList, mode='cn'),
            'by Chinese num [down]': partial(self.sortFileList, mode='cn', reverse=True),
            'by Arab num': partial(self.sortFileList, mode='arab'),
            'by Arab num [down]': partial(self.sortFileList, mode='arab', reverse=True),
            'by Pinyin': partial(self.sortFileList, mode='py'),
            'by Pinyin [down]': partial(self.sortFileList, mode='py', reverse=True),
            'by Modified time': partial(self.sortFileList, mode='mtime'),
            'by Modified time [down]': partial(self.sortFileList, mode='mtime', reverse=True),
            'by Extension': partial(self.sortFileList, mode='ext'),
            'by Extension [down]': partial(self.sortFileList, mode='ext', reverse=True),
        }
        self.cmbSort.addItems(self.sortFuncMap.keys())
        self.cmbFilter.addItems(['*.*', '*.mp3', '*.m4a', '*.jpg;*.jpeg;*.png;*.bmp','*.txt'])

    #Init QTextEdit widget for code editing
    def initCodeWidget(self):
        initText = '#Return the new filename! return an empty string to skip.\n#arg(dict) has elements: totalNum,index,fileName,dirName,tag()\n'
        initText += '#Available modules: os,sys,re,fnmatch,datetime,hashlib,uuid,locale...\n'
        initText += 'def rename(arg):\n    return arg.fileName'
        self.txtCode.insertPlainText(initText)
        font = QFont(CODE_FONT_FAMILY, CODE_FONT_SIZE)
        metrics = QFontMetrics(font)
        self.txtCode.setFont(font)
        self.txtCode.setTabStopWidth(4 * metrics.width(' ')) #set tab stop with 4 spaces
        self.spltCodeAndOutput.setStretchFactor(0, 7)
        self.spltCodeAndOutput.setStretchFactor(1, 3)
        self.highlighter = PythonHighlighter(self.txtCode.document())

    #Init something in data directory
    def initDataDirectory(self):
        if not os.path.exists(APP_DATA_DIR):
            try:
                os.makedirs(APP_DATA_DIR)
            except:
                pass

        self.btnUndo.setEnabled(os.path.exists(LAST_RENAME_FILE))

        if os.path.exists(LAST_DIR_FILE):
            lastDir = ''
            try:
                with open(LAST_DIR_FILE, 'r', encoding='utf-8') as f:
                    lastDir = f.readline().strip()
            except:
                pass
            if lastDir and os.path.isdir(lastDir):
                self.txtDirectory.setText(lastDir)
                self.txtDirectory_returnPressed(isInInitial=True)

    def createMenu(self):
        self.mnuSnippets = QMenu(self)
        
        self.actAddSnippet = self.mnuSnippets.addAction('Add current snippet to library')
        self.actAddSnippet.triggered.connect(self.actAddSnippet_triggered)
        self.mnuRecentSnippets = self.mnuSnippets.addMenu('Recent snippets')
        self.actSnippetsMgr = self.mnuSnippets.addAction('Snippets manager')
        self.actSnippetsMgr.triggered.connect(self.actSnippetsMgr_triggered)

    #Override this function of the parent class, intercepting shortcut events
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_F2:
            self.btnMoveUp_pressed()
        elif key == Qt.Key_F3:
            self.btnMoveDown_pressed()
        elif key == Qt.Key_F5:
            self.btnPreview_pressed()
        else:
            return super().keyPressEvent(event)

    #Intercept child widget events
    def eventFilter(self, target, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_F5:
            self.btnPreview_pressed()
            return True

        return super().eventFilter(target, event)

    #Drag and Drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    #Drag and Drop
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            print('hasUrls')
            path = event.mimeData().urls()[0].toLocalFile()
            if os.path.isfile(path):
                self.txtDirectory.setText(os.path.dirname(path))
            else:
                self.txtDirectory.setText(path)
            self.txtDirectory.setFocus()
        elif event.mimeData().hasText() and event.mimeData().text():
            self.txtCode.insertPlainText(event.mimeData().text())
            self.txtCode.setFocus()

    #Choose directory to process
    def btnDirectory_pressed(self):
        dirName = QFileDialog.getExistingDirectory(self, 'Directory', self.txtDirectory.text())
        if dirName:
            self.txtDirectory.setText(dirName)
            self.txtDirectory_returnPressed()

    #Start to rename files
    def btnStart_pressed(self):
        ret = QMessageBox.question(self, 'Confirm to continue', 'Please confirm again to rename files in list.')
        if ret == QMessageBox.No:
            return

        self.txtOutput.clear()
        dictToRename = {}
        maxRow = self.trePreview.topLevelItemCount()
        for row in range(maxRow):
            item = self.trePreview.topLevelItem(row)
            if item.checkState(0) and item.text(2):
                srcFile = os.path.join(self.dirName, item.text(1))
                dstFile = os.path.join(self.dirName, item.text(2))
                if srcFile != dstFile:
                    try:
                        os.rename(srcFile, dstFile)
                        dictToRename[srcFile] = dstFile
                    except Exception as e:
                        item.setForeground(2, QBrush(QColor('red')))
                        self.txtOutput.insertPlainText('Failed to rename "%s": %s\n' % (srcFile, str(e)))

        try:
            with open(LAST_RENAME_FILE, 'wb') as f:
                pickle.dump(dictToRename, f)
        except Exception as e:
            QMessageBox.warning(self, 'Failed to save undo file', 'Failed to save undo file, you cannot undo this operation.\n%s' % str(e))

        if len(dictToRename):
            QMessageBox.information(self, 'Successful', 'Successful renamed %d files.' % len(dictToRename))
        else:
            QMessageBox.information(self, 'Nothing happened', 'No files were renamed.')

        self.btnUndo.setEnabled(os.path.exists(LAST_RENAME_FILE))

    #Undo operation
    def btnUndo_pressed(self):
        dictToRename = {}
        try:
            with open(LAST_RENAME_FILE, 'rb') as f:
                dictToRename = pickle.load(f)
        except Exception as e:
            QMessageBox.warning(self, 'Failed to restore undo file', 'Failed to restore undo file, you cannot undo this operation.\n%s' % str(e))
            return

        if len(dictToRename) > 0:
            ret = QMessageBox.question(self, 'Confirm to undo', 'There have [%d] files in undo list, Would you undo them?' % len(dictToRename))
            if ret == QMessageBox.No:
                return
        else:
            QMessageBox.information(self, 'Nothing to do', 'Have no files in undo list.')
            return

        renameCount = 0
        for name in dictToRename:
            try:
                os.rename(dictToRename[name], name)
                renameCount += 1
            except Exception as e:
                pass

        if renameCount == len(dictToRename):
            QMessageBox.information(self, 'Undo finished', 'Successful undo %d files.' % renameCount)
        elif renameCount > 0:
            QMessageBox.information(self, 'Undo finished', 'Total %s files, but undo %d files only.' % (len(dictToRename), renameCount))
        else:
            QMessageBox.warning(self, 'Undo failed', 'Failed to undo! (total %s files).' % len(dictToRename))
    
    #button snippets
    def btnSnippet_pressed(self):
        if not self.recentSnippetsMenuInited:
            self.recentSnippetsMenuInited = True
            self.initRecentSnippetsMenu()
            
        self.actAddSnippet.setEnabled(self.txtCode.toPlainText().strip() != '')
        self.mnuRecentSnippets.setEnabled(not self.mnuRecentSnippets.isEmpty())
        
        self.mnuSnippets.popup(QCursor.pos())

    #Get recent snippets and set the title of sub menus
    def initRecentSnippetsMenu(self):
        RECENT_ITEMS = 20
        
        metrics = self.mnuRecentSnippets.fontMetrics() #for measure the length of the string

        self.mnuRecentSnippets.clear()
        self.actRecentSnippetsList = [None for i in range(RECENT_ITEMS)]

        itemList = list(Snippet.select().order_by(Snippet.last_used.desc()).limit(RECENT_ITEMS))
        for idx, item in enumerate(itemList):
            actText = item.name
            addEllipsis = False
            while metrics.width(actText) > 400:
                actText = actText[:-1]
                addEllipsis = True

            if addEllipsis:
                actText += '...'

            self.actRecentSnippetsList[idx] = self.mnuRecentSnippets.addAction(actText)
            self.actRecentSnippetsList[idx].triggered.connect(partial(self.actRecentSnippets_triggered, id_=item.id))
            if addEllipsis:
                self.actRecentSnippetsList[idx].setToolTip(item.name)
                self.mnuRecentSnippets.setToolTipsVisible(True)

    #Compile a function object from text in Textbox
    def compileUserFunction(self):
        txt = self.txtCode.toPlainText().replace('\t', '    ')
        
        #simple syntax check
        if not re.search(r'def rename\(\w+\):', txt):
            self.txtOutput.setPlainText('No "rename(arg)" function found.\n')
            return None
        elif not re.search(r'return .+', txt):
            self.txtOutput.setPlainText('Function "rename(arg)" has no return statement.\n')
            return None

        try:
            codeObj = compile(txt, '<user code>', 'exec')
        except Exception as e:
            execInfo = traceback.format_exc()
            self.highlightCodeLine(execInfo)
            self.txtOutput.setPlainText(execInfo)
            return None

        funcCode = [c for c in codeObj.co_consts if isinstance(c, types.CodeType)][0]
        gDict = copy.copy(globals())
        gDict['print'] = printInUserCode
        return types.FunctionType(funcCode, gDict)

    #Return pressed to update preview
    def txtDirectory_returnPressed(self, isInInitial=False):
        self.dirName = self.txtDirectory.text().strip()
        try:
            self.allFileList = [f for f in os.listdir(self.dirName) if not os.path.isdir(os.path.join(self.dirName, f))]
        except Exception as e:
            self.txtOutput.setPlainText(str(e))
            return

        self.populateFileListbox()
        if not isInInitial: #Save the last directory for next time
            try:
                with open(LAST_DIR_FILE, 'w', encoding='utf-8') as f:
                    f.write(self.dirName)
            except:
                pass

    #populate the file list box with filtered and sorted list
    def populateFileListbox(self):
        self.txtOutput.clear()
        self.trePreview.clear()
        fileList = self.filterFileList(self.allFileList)
        funcSort = self.sortFuncMap.get(self.cmbSort.currentText(), self.sortFileList)
        fileList = funcSort(fileList)
        funcRename = self.compileUserFunction()
        if not funcRename:
            for idx, srcName in enumerate(fileList):
                item = QTreeWidgetItem([str(idx + 1), srcName, srcName])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                item.setCheckState(0, Qt.Checked)
                self.trePreview.addTopLevelItem(item)
            return

        argDict = AttributeDict({'totalNum': len(fileList), 'dirName': self.dirName})
        for idx, srcName in enumerate(fileList):
            fullPathName = os.path.join(self.dirName, srcName)
            argDict['index'] = idx
            argDict['fileName'] = srcName
            argDict['fullPathName'] = fullPathName
            argDict['tag'] = lambda: TinyTag.get(fullPathName)
            try:
                dstName = funcRename(argDict)
            except Exception as e:
                execInfo = fullPathName + '\n'
                execInfo += traceback.format_exc()
                self.highlightCodeLine(execInfo)
                self.txtOutput.insertPlainText(execInfo + '\n')
                dstName = None
            
            if dstName in ('', None, srcName):
                dstName = ''

            item = QTreeWidgetItem([str(idx + 1), srcName, str(dstName)])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            item.setCheckState(0, Qt.Checked)
            self.trePreview.addTopLevelItem(item)

    #Double-click source file name to toggle the check state
    #Double-click dest file name to edit manually
    def trePreview_itemDoubleClicked(self, item, col):
        if not item:
            return

        if col == 0 or col == 1:
            item.setCheckState(0, Qt.Unchecked if item.checkState(0) else Qt.Checked)
        else:
            self.trePreview.editItem(item, col)

    #Compile the user code and apply to file list for preview
    def btnPreview_pressed(self):
        self.txtOutput.clear()
        codeText = self.txtCode.toPlainText()
        if 'about()' in codeText:
            aboutTxt = 'ARUP - Another bulk Rename Utility with Python\nAuthor: cdhigh <https://github.com/cdhigh>\nVersion: %s' % __Version__
            QMessageBox.information(self, 'about', aboutTxt)
            return
        elif 'usage()' in codeText:
            usageTxt = 'Write a function [rename(index, fileName, dirName)]:\nindex: sn(start from 0)\nreturn a new fileName.\nYou can use print() for debug.'
            QMessageBox.information(self, 'usage', usageTxt)
            return

        funcRename = self.compileUserFunction()
        if not funcRename:
            return
            
        count = self.trePreview.topLevelItemCount()
        argDict = AttributeDict({'totalNum': count, 'dirName': self.dirName})
        for row in range(count):
            item = self.trePreview.topLevelItem(row)
            if not item.checkState(0):
                continue

            srcName = item.text(1)
            fullPathName = os.path.join(self.dirName, srcName)
            argDict['index'] = row
            argDict['fileName'] = srcName
            argDict['fullPathName'] = fullPathName
            argDict['tag'] = lambda: TinyTag.get(fullPathName)
            try:
                dstName = funcRename(argDict)
            except Exception as e:
                execInfo = fullPathName + '\n'
                execInfo += traceback.format_exc()
                self.highlightCodeLine(execInfo)
                self.txtOutput.insertPlainText(execInfo + '\n')
                continue

            if dstName in ('', None, srcName):
                item.setText(2, '')
            else:
                item.setText(2, str(dstName))

    #Move the selected rows up
    def btnMoveUp_pressed(self):
        itemCount = self.trePreview.topLevelItemCount()
        if itemCount <= 1:
            return

        selModel = self.trePreview.selectionModel()
        indexes = selModel.selectedIndexes()
        if len(indexes) == 0:
            QMessageBox.information(self, 'No selection', 'Have no selection')
            return

        rowsSelected = [index.row() for index in indexes]
        firstSelectedRow = min(rowsSelected)
        lastSelectedRow = max(rowsSelected)

        #Remove a row above the selection area and insert it below the selection area
        if firstSelectedRow > 0:
            item = self.trePreview.takeTopLevelItem(firstSelectedRow - 1)
            self.trePreview.insertTopLevelItem(lastSelectedRow, item)

        self.rectifyTrePreviewNo()

    #Move the selected rows down
    def btnMoveDown_pressed(self):
        itemCount = self.trePreview.topLevelItemCount()
        if itemCount <= 1:
            return

        selModel = self.trePreview.selectionModel()
        indexes = selModel.selectedIndexes()
        if len(indexes) == 0:
            QMessageBox.information(self, 'No selection', 'Have no selection')
            return

        rowsSelected = [index.row() for index in indexes]
        firstSelectedRow = min(rowsSelected)
        lastSelectedRow = max(rowsSelected)

        #Remove a row below the selection area and insert it above the selection area
        if lastSelectedRow < itemCount - 1:
            item = self.trePreview.takeTopLevelItem(lastSelectedRow + 1)
            self.trePreview.insertTopLevelItem(firstSelectedRow, item)

        self.rectifyTrePreviewNo()

    #After manually moving some lines, correct the serial number
    def rectifyTrePreviewNo(self):
        itemCount = self.trePreview.topLevelItemCount()
        for row in range(itemCount):
            item = self.trePreview.topLevelItem(row)
            item.setText(0, str(row + 1))

    #Apply name filtering, accept Unix filename pattern like *.jpg a?.*
    #return a new list
    def filterFileList(self, fileList):
        txt = self.cmbFilter.currentText().strip().replace(',', ';').lower()
        if not txt or txt == '*.*':
            return fileList
        elif ';' in txt: #multiple filters
            flts = [flt.strip() for flt in txt.split(';')]
            funcFlt = lambda elem: len([flt for flt in flts if fnmatch.fnmatch(elem, flt)]) > 0
            return list(filter(funcFlt, fileList))
        else: #single filter
            return fnmatch.filter(fileList, txt)

    #Sort the file list and return a new list
    def sortFileList(self, fileList, mode=None, reverse=False):
        key = None
        if not mode: #Auto mode
            PAT_CHINESE = r'[一二三四五六七八九十百千]'
            PAT_NUM = r'[0123456789]'
            byChinese = 0
            byNum = 0
            firstIsChinese = 0
            maxNum = len(fileList)
            for f in fileList:
                firstChar = f[0]
                if re.search(PAT_CHINESE, f):
                    byChinese += 1
                if re.search(PAT_NUM, f):
                    byNum += 1
                if '\u4e00' <= firstChar <= '\u9fa5': #中文
                    firstIsChinese += 1
            if byChinese >= maxNum:
                key = partial(self.ordinal, mode='cn')
            elif byNum >= maxNum:
                key = partial(self.ordinal, mode='arab')
            elif firstIsChinese >= maxNum:
                key = partial(self.ordinal, mode='py')
        elif mode == 'cn':
            key = partial(self.ordinal, mode='cn')
        elif mode == 'arab':
            key = partial(self.ordinal, mode='arab')
        elif mode == 'py':
            key = partial(self.ordinal, mode='py')
        elif mode == 'mtime':
            key = partial(self.ordinal, mode='mtime')
        elif mode == 'ext':
            key = partial(self.ordinal, mode='ext')

        if key:
            return sorted(fileList, key=key, reverse=reverse)
        else:
            return sorted(fileList, reverse=reverse)

    #Get the sort key for the fileName
    #mode: 
    #   cn: Chinese num, arab: Arab num, py: Chinese pinyin, mtime: modified time, ext: extension
    def ordinal(self, fileName, mode=None):
        if mode == 'cn':
            PAT_CHINESE = r'[一二三四五六七八九十百千]+'
            mat = re.search(PAT_CHINESE, fileName)
            if mat:
                num = changeChineseNumToArab(mat.group())
                if num.isdigit():
                    return int(num)
                else:
                    return 0
            else:
                return 0
        elif mode == 'arab':
            PAT_NUM = r'[0123456789]+'
            mat = re.search(PAT_NUM, fileName)
            if mat:
                num = mat.group()
                if num.isdigit():
                    return int(num)
                else:
                    return 0
            else:
                return 0
        elif mode == 'py':
            if not self.pinyin:
                self.pinyin = Pinyin()
            return self.pinyin.get_pinyin(fileName, splitter='')
        elif mode == 'mtime':
            return os.path.getmtime(os.path.join(self.dirName, fileName))
        elif mode == 'ext':
            return os.path.splitext(fileName)[1].replace('.', '')
        else:
            return fileName

    #Set cursor of txtCode widget to line where execption ocurred
    def highlightCodeLine(self, execInfo):
        if not execInfo:
            return

        lineNo = 0
        mat = re.search(r'File "<user code>", line (\d+)', execInfo)
        if mat:
            lineNo = mat.group(1)
            if lineNo.isdigit():
                lineNo = int(lineNo)
            else:
                return
        else:
            return

        doc = self.txtCode.document()
        block = doc.findBlockByLineNumber(lineNo - 1)
        blockPos = block.position()
        cursor = QTextCursor(block)
        cursor.setPosition(blockPos, QTextCursor.MoveAnchor)
        cursor.select(QTextCursor.LineUnderCursor)
        self.txtCode.setTextCursor(cursor)
        
        self.txtCode.setFocus()

    #Click on menu item 'add snippet'
    def actAddSnippet_triggered(self):
        nameText, ok = QInputDialog.getText(self, 'Name', 'Please input the name for this snippet. recommend provide the name in detail.')
        if not nameText or not ok:
            return

        codeText = self.txtCode.toPlainText().replace('\t', '    ')
        Snippet.create(name=nameText, code=codeText)
        self.initRecentSnippetsMenu()

    #Shortcut for recent used snippets
    #id_: id of database item
    def actRecentSnippets_triggered(self, id_=None):
        if id_ is None:
            return

        item = Snippet.getById(id_)
        if item:
            self.txtCode.setPlainText(item.code)
            item.last_used = datetime.datetime.now()
            item.save()
            
    #open snippets manager dialog
    def actSnippetsMgr_triggered(self):
        dlg = snippetsMgr.SnippetsMgrDialog(self)
        dlg.sigUseCodeSnippet.connect(self.useCodeSnippet)
        dlg.exec_()
        self.initRecentSnippetsMenu()

    #signal received from snippet manager
    def useCodeSnippet(self, codeText):
        if codeText:
            self.txtCode.setPlainText(codeText)
            self.txtCode.setFocus()

#Overwrite print function in user code
def printInUserCode(value, *args):
    mainWindow.txtOutput.insertPlainText(str(value))
    for arg in args:
        mainWindow.txtOutput.insertPlainText(' ' + str(arg))
    mainWindow.txtOutput.insertPlainText('\n')


#reset database if database is broken
if len(sys.argv) == 2 and sys.argv[1] == '--resetdatabase':
    ret = QMessageBox.question(None, 'Reset snippets database? --resetdatabase', 'Dangerous operation!!!\n\nYou want to reset the snippets database?\nIf yes, you will lost all your data!!!')
    if ret == QMessageBox.Yes:
        createDatabaseTable()

connectToDatabase()

try:
    Snippet.getById(0)
except:
    QMessageBox.warning(None, 'snippets database error', 'Snippets database invalid.\n\nYou have to reset the snippets database by using argument : \n--resetdatabase')
    
mainWindow = MainDialog()
mainWindow.show()
result = app.exec_()
app.closeAllWindows()
app.quit()
sys.exit(result)
