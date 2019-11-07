#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""ARUP - Another bulk Rename Utility with embedded Python interpreter
Some utils
Author: cdhigh <https://github.com/cdhigh>
"""
import os, datetime, random, time

#A subclass of dict, a dictionary that can access elements using attributes
class AttributeDict(dict):
    def __getattr__(self, attr):
        return self[attr]
    def __setattr__(self, attr, value):
        self[attr] = value

def local_time(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(fmt)

def is_int(s):
    try:
        int(s)
        return True
    except:
        return False
        
def is_float(s):
    try:
        float(s)
        return True
    except:
        return False
    
def str_to_int(txt, zero_if_except=True):
    try:
        return int(txt.strip())
    except:
        return 0 if zero_if_except else ''

def str_to_float(txt, zero_if_except=True):
    try:
        txt = txt.strip().replace(',', '.')
        return float(txt)
    except:
        return 0.0 if zero_if_except else ''

def random_str(length=5, prefixWithDate=True, prefixWithTime=True):
    s = datetime.datetime.now().strftime('%Y%m%d') if prefixWithDate else ''
    if prefixWithTime:
        s += datetime.datetime.now().strftime('%H%M%S')
    s += new_secret_key(length)
    return s
