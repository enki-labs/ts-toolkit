from tables import *
import numpy
import csv
import gzip
import datetime
import pytz
import bunch
import tickMapper
import tickProcessor
import re
import time
import pandas as pd
import numpy as np
import pytz
import sys
import json
import os
import requests

class OHLC (object):

    class OHLC_table (IsDescription):
        time            = Int64Col()
        open            = Float64Col()
        high            = Float64Col()
        low             = Float64Col()
        close           = Float64Col()
        volume          = Float64Col()
        openInterest    = Float64Col()

    def __init__ (self, hdfFile, filters):
        #self._group = hdfFile.createGroup("/", 'data', 'Market Data')
        #self._group
        self._table = hdfFile.createTable(hdfFile.root, 'data', OHLC.OHLC_table, "data", filters=filters)
    
    def add (self, t, open, high, low, close, volume, openInterest):
        row = self._table.row
        row['time'] = (time.mktime(t.timetuple())*1000000) + long("%s" % t.microsecond)
        row['open'] = open
        row['high'] = high
        row['low'] = low
        row['close'] = close
        row['volume'] = volume
        row['openInterest'] = openInterest
        row.append()    

    def close (self):
        self._table.flush()


def ohlcProc (df):
     returnDf = df.ix[0:1]
     #returnDf = df.iloc[0:1]
     returnDf["close"] = df["close"][-1]
     returnDf["high"] = df["high"].max()
     returnDf["low"] = df["low"].min()
     returnDf["volume"] = df["volume"].sum()
     returnDf["openInterest"] = df["openInterest"].sum()
     return returnDf

def step_window (df, window, func):
    rowCount = df["close"].count()
    returnDf = None
    first = True

    for i in xrange(0, rowCount, window):
        if first:
            #returnDf = func(df.iloc[i:min(i+window,rowCount)])
            returnDf = func(df.ix[i:min(i+window,rowCount)])
            first = False
        else:
            #returnDf = pd.concat([returnDf, func(df.iloc[i:min(i+window,rowCount)])], axis=0)
            returnDf = pd.concat([returnDf, func(df.ix[i:min(i+window,rowCount)])], axis=0)
    return returnDf


class Join (object):

    def __init__ (self, joins, baseTags, taskInfo):
        self._joins = joins
        self._baseTags = baseTags
        self._taskInfo = taskInfo

    def run (self, args):

        rowCount = 0
        frames = []

        for join in self._joins:
             print join
             searchTags = []
             for tag in self._baseTags:
                 searchTags.append(tag)
             for tag in join["tag"]:
                 searchTags.append(tag)

             print searchTags
             tagData = json.dumps(dict(content=json.dumps(searchTags)))
             print "SEND REQUEST"
             res = requests.post("http://%s:%s/task/detail" % (args.taskhost, args.taskport), data=tagData, headers={'Content-type': 'application/json', 'Accept': 'text/plain'})
             nodes = json.loads(res.text)
             print nodes
             inPath = os.path.join(args.hdfpath, (nodes[0]["_id"] + ".h5"))
             with openFile(str(inPath), mode = "r") as h5file:
                 timeColumn = h5file.root.data.col('time')
                 dataFrame = pd.DataFrame.from_records(h5file.root.data[:], index=pd.DatetimeIndex(pd.Series(h5file.root.data.col('time'), dtype='datetime64[us]'), tz='UTC'))
                 print dataFrame            
                 if len(join["start"]) > 0 and len(join["end"]) > 0:
                     frames.append(dataFrame[join["start"]:join["end"]])
                 elif len(join["start"]) > 0:
                     frames.append(dataFrame[join["start"]:])
                 elif len(join["end"]) > 0:
                     frames.append(dataFrame[:join["end"]])
                 else:
                     frames.append(dataFrame)

        outFrame = pd.concat(frames)
        outPath = os.path.join(args.hdfpath, (self._taskInfo["node"]["_id"] + ".h5"))
        with openFile(str(outPath), mode = "w", title = ",".join(self._taskInfo["node"]["tags"])) as h5resamplefile:
            filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
            appender = OHLC(h5resamplefile, filters)
            rowCount = 0
            for record in outFrame.to_records():
                appender.add(record[0], record["open"], record["high"], record["low"], record["close"], record["volume"], record["openInterest"])
                rowCount = rowCount + 1            
            
            appender.close()
            print "Wrote", rowCount, "records"

	return "Wrote %s records" % rowCount
