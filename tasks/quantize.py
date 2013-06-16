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

jsoninput = sys.argv[1]
args = json.loads(jsoninput)

inPath = os.path.join("/media/wayne240/tstoolbox/hdf_new", (args["parent"]["key"] + ".h5"))
outPath = os.path.join("/media/wayne240/tstoolbox/hdf_new", (args["child"]["key"] + ".h5"))
outPathCsv = os.path.join("/media/wayne240/tstoolbox/csv", (args["child"]["key"] + ".csv"))

print str(inPath)
print ",".join(args["child"]["tag"])

with openFile(str(inPath), mode = "r") as h5file:

    if h5file.root.data.nrows <= 0:
        print "No rows", h5file.root.data.nrows, inPath
        with openFile(str(outPath), mode = "w", title = ",".join(args["child"]["tag"])) as h5resamplefile:
            filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
            appender = OHLC(h5resamplefile, filters)
            appender.close()
        exit()

    timeColumn = h5file.root.data.col('time')
    dataFrame = pd.DataFrame.from_records(h5file.root.data[:], index=pd.DatetimeIndex(pd.Series(h5file.root.data.col('time'), dtype='datetime64[us]'), tz='UTC'))

    ohlcSample = { 'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum', 'openInterest':'sum'};

    resampledReady = False

    if args["childData"]["periodType"] == "minute":
        resampleType = "%sMin" % args["childData"]["periodCount"]
        print resampleType
        resampled = dataFrame.resample(resampleType, how=ohlcSample).dropna()
        resampledReady = True

    elif args["childData"]["periodType"] == "day":
        resampled = dataFrame.tz_convert(pytz.timezone(args["childData"]["alignTo"]))
        resampled = resampled.between_time(args["childData"]["open"], args["childData"]["close"]).resample('D', how=ohlcSample).dropna()
        resampledReady = True

    else:
        resampled = dataFrame.resample(args["childData"]["periodType"], how=ohlcSample).dropna()
        resampledReady = True

    if resampledReady:

        with openFile(str(outPath), mode = "w", title = ",".join(args["child"]["tag"])) as h5resamplefile:
            filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
            appender = OHLC(h5resamplefile, filters)

            rowCount = 0
            for record in resampled.to_records():
                appender.add(record[0], record["open"], record["high"], record["low"], record["close"], record["volume"], record["openInterest"])
                rowCount = rowCount + 1            
    
            appender.close()
            print "Wrote", rowCount, "records"

            resampled['timeAsDate'] = resampled.index.to_pydatetime()
            resampled['date'] = resampled['timeAsDate'].apply(lambda x: x.strftime('%Y%m%d'))
            resampled['datetime'] = resampled['timeAsDate'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
            resampled.to_csv(outPathCsv, index=False, cols=['date', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'openInterest'], float_format='%.8f')



