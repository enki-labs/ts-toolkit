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
from pandas.lib import Timestamp

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
            returnDf = func(df.ix[i:min(i+window,rowCount)])
            first = False
        else:
            returnDf = pd.concat([returnDf, func(df.ix[i:min(i+window,rowCount)])], axis=0)
    return returnDf


class Quantize (object):

    def __init__ (self, params, taskInfo):
        self._params = params
        self._taskInfo = taskInfo

    def run (self, args):
        print self._params
        print self._taskInfo
	rowCount = 0

        inPath = os.path.join(args.hdfpath, (self._taskInfo["parent"][0]["_id"] + ".h5"))
        outPath = os.path.join(args.hdfpath, (self._taskInfo["node"]["_id"] + ".h5"))

        print str(inPath)
        print ",".join(self._taskInfo["node"]["tags"])

        with openFile(str(inPath), mode = "r") as h5file:

            if h5file.root.data.nrows <= 0:
                print "No rows", h5file.root.data.nrows, inPath
                with openFile(str(outPath), mode = "w", title = ",".join(self._taskInfo["node"]["tags"])) as h5resamplefile:
                    filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
                    appender = OHLC(h5resamplefile, filters)
                    appender.close()
	        return "Wrote %s records" % rowCount

            timeColumn = h5file.root.data.col('time')
            dataFrame = pd.DataFrame.from_records(h5file.root.data[:], index=pd.DatetimeIndex(pd.Series(h5file.root.data.col('time'), dtype='datetime64[us]'), tz='UTC'))

            ohlcSample = { 'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum', 'openInterest':'sum'};

            resampledReady = False

            if self._params["periodType"] == "minute":
                resampleType = "%sMin" % self._params["periodCount"]
                print resampleType
                resampled = dataFrame.resample(resampleType, how=ohlcSample).dropna()
                resampledReady = True

            elif self._params["periodType"] == "day":
                resampled = dataFrame.tz_convert(pytz.timezone(self._params["alignTo"]))
                resampled = resampled.between_time(self._params["open"], self._params["close"], include_start = True, include_end = False).resample('D', how=ohlcSample, convention=self._params["timeAlign"]).dropna()
                resampled.index = pd.DatetimeIndex([i.replace(tzinfo=pytz.timezone('UTC')) for i in resampled.index])
                criteria = resampled.index.map(lambda x: x.weekday() != 6)
                resampled = resampled[criteria]
                resampledReady = True
            
            elif self._params["periodType"] == "rolling":
                resampled = step_window(dataFrame, self._params["periodCount"], ohlcProc)
                resampledReady = True

            else:
                resampled = dataFrame.resample(self._params["periodType"], how=ohlcSample).dropna()
                resampledReady = True

            if resampledReady:

                with openFile(str(outPath), mode = "w", title = ",".join(self._taskInfo["node"]["tags"])) as h5resamplefile:
                    filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
                    appender = OHLC(h5resamplefile, filters)

                    rowCount = 0
                    for record in resampled.to_records():
                        appender.add(record[0], record["open"], record["high"], record["low"], record["close"], record["volume"], record["openInterest"])
                        rowCount = rowCount + 1            
            
                    appender.close()
                    print "Wrote", rowCount, "records"

	return "Wrote %s records" % rowCount
