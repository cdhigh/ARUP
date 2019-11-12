#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""ARUP - Another bulk Rename Utility with embedded Python interpreter
Database module
Author: cdhigh <https://github.com/cdhigh>
"""
import os, sys, datetime
from mylib.peewee import *
from mylib.commutils import str_to_int, str_to_float, local_time

dbName = os.path.join(appDir, 'data/snippets.db')

dbInstance = SqliteDatabase(dbName, check_same_thread=False)

#Base class for my models
class MyBaseModel(Model):
    class Meta:
        database = dbInstance
        
    @classmethod
    def getOne(cls, *query, **kwargs):
       try:
          return cls.get(*query,**kwargs)
       except DoesNotExist:
           return None

    @classmethod
    def getById(cls, id_):
        try:
            return cls.get(cls.id == int(id_))
        except DoesNotExist:
            return None

    #Convert current row to a dict without any datatype-convert
    def toRawDict(self):
        return {field: getattr(self, field) for field in self._meta.fields}
    
class Snippet(MyBaseModel):
    name = CharField()
    code = CharField()
    description = CharField(default='')
    last_used = DateTimeField(default=datetime.datetime.now)
    modified_date = DateTimeField(default=datetime.datetime.now)

def connectToDatabase():
    global dbInstance
    dbInstance.connect()

def createDatabaseTable():
    try:
        os.remove(dbName)
    except:
        pass
    Snippet.create_table()
    