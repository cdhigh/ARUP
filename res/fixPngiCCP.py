#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""小店销售管理系统
修正QT5.5读取PNG文件报错的问题，仅需要双击执行一次，修改一次PNG即可
双击执行后会扫描和此文件相同目录(不包括子目录)下的所有png文件并做相应处理。
PNG报错：libpng warning: iCCP: known incorrect sRGB profile
Last modified: 2017-04-07
Author: suqiyuan <chsqyuan@gmail.com>
"""

import os
from PyQt5.QtGui import QImage

fileNumProcessed = 0
pathname = os.path.dirname(os.path.abspath(__file__))
print('\n')
try:
    for filename in os.listdir(pathname):
        if filename.lower().endswith('.png'):
            fullFileName = os.path.join(pathname, filename)
            img = QImage(fullFileName)
            img.save(fullFileName, 'PNG')
            print('processed: %s' % fullFileName)
            fileNumProcessed += 1
    if fileNumProcessed == 0:
        print('Cannot found any png file in [%s]!' % pathname)
    else:
        print('Total %d files have been processed!' % fileNumProcessed)

except Exception as e:
    print(str(e))

os.system('pause')
