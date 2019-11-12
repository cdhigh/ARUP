#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""Auto comiple ui files
Author: Author: cdhigh <https://github.com/cdhigh>
"""
import os,sys
print('\n\t\tComiple ui files if nesssory!\n')
currDir = os.path.dirname(os.path.abspath(__file__))
uiDir = currDir

uis = []
uisToCompiled = []
for ui in os.listdir(uiDir):
    if not ui.lower().endswith('.ui'):
        continue
    ui = os.path.normpath(os.path.join(uiDir, ui))
    uis.append(ui)
    uiMtime = int(os.stat(ui).st_mtime)
    pyui = os.path.join(uiDir, 'ui_%s.py' % os.path.splitext(os.path.basename(ui))[0])
    if not os.path.exists(pyui):
        uisToCompiled.append((pyui, ui))
    else:
        pyuiMtime = int(os.stat(pyui).st_mtime)
        if pyuiMtime < uiMtime:
            uisToCompiled.append((pyui, ui))

if uis:
    print('Found following ui files (%d):' % len(uis))
    for ui in uis:
        print('\t%s' % ui)

if not uisToCompiled:
    print('\nAll UI files is up-to-date, do not need to compile.')
else:
    print('\nThe following ui files will be compiled (%d)!' % len(uisToCompiled))
    for ui in uisToCompiled:
        print('\t%s' % ui[1])
    
    try:
        response = raw_input('\n\tContinue?(y/n)')
    except:
        response = input('\n\tContinue?(y/n)')
    if response.lower() == 'n' :
        sys.exit(0)
        
    for ui in uisToCompiled:
        os.system(r'pyuic5 "%s" -o "%s"' % (ui[1], ui[0]))
    
os.system('pause')
