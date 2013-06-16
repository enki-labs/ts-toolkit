from tables import *
import numpy
import csv
import gzip
import datetime
import pytz
import bunch
import tickMapper
import tickProcessor
import ohlcMapper
import ohlcProcessor
import re
import time
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

class FloorFilter (object):

    def __init__ (self, minPrice):
        self._minPrice = minPrice

    def filter (self, time, price, volume):
        return price < self._minPrice

class CapFilter (object):

    def __init__ (self, maxPrice):
        self._maxPrice = maxPrice

    def filter (self, time, price, volume):
        return price > self._maxPrice

class StepFilter (object):

    def __init__ (self, timeoutSeconds, maxPriceStep, maxFilterCount):
        self._filterCount = 0
        self._timeout = datetime.timedelta(seconds = timeoutSeconds)
        self._maxPriceStep = maxPriceStep
        self._maxFilterCount = maxFilterCount
        self._lastTime = None
        self._lastPrice = None

    def filter (self, time, price, volume):
    
        if (( self._lastTime and self._lastPrice )
           and   ( abs(price - self._lastPrice) >= self._maxPriceStep )
           and   ( (time - self._lastTime) <= self._timeout )
           and   ( self._filterCount < self._maxFilterCount ) ):
            self._filterCount += 1
            return True

        else:
            self._lastTime = time
            self._lastPrice = price
            self._filterCount = 0
            return False


#jsoninput = '{ "filter": [ "floor,50", "cap,200", "step,3600,0.328125,3", "step,900,0.234375,1", "step,180,0.21875,5" ], "remove": [ "([A-RT-Za-z]\\\[MKT_ST_IND\\\])|([^A]S\\\[MKT_ST_IND\\\])|([^F]AS\\\[MKT_ST_IND\\\])", "(.*[A-S,U-Z,a-u,w-z]{1,2}\\\[ACT_TP_1\\\].*)|(.*O(?!T)\\\[ACT_TP_1\\\].*)|([^O]T\\\[ACT_TP_1\\\])", ".*IRGCOND.*" ], "allow": [ "Open\\\|High\\\|" ], "name": "TY", "input": "TimeAndSales_TYU7_1997-10-01_2007-09-30.csv.gz", "volFollows": false, "copyLast": true, "priceShift": "0", "volumeLimit": "25000", "output": "TY__TimeAndSales_TYU7-200612", "validFrom": "1181930000", "validTo": "1186930000" }'
jsoninput = sys.argv[1]
args = json.loads(jsoninput)

inPath = os.path.join("/media/wayne240/tstoolbox/reuters_original/", args["parentData"]["file"])
outPath = os.path.join("/media/wayne240/tstoolbox/hdf_new/", (args["child"]["key"] + ".h5"))

with openFile(str(outPath), mode = "w", title = ",".join(args["child"]["tag"])) as h5file:

    mapper = None
    processor = None

    if args["parentData"]["type"] == "futureTimeAndSales":
        mapper = tickMapper.TickMapper()
        processor = tickProcessor.TickProcessor(mapper)
    elif args["parentData"]["type"] == "ohlc":
        mapper = ohlcMapper.OhlcMapper()
        processor = ohlcProcessor.OhlcProcessor(mapper)
    
    stats = bunch.Bunch(lines=0, qualifierFiltered=0, priceFiltered=0, badTradeCount=0, tradeNoVolCount=0, tradeCount=0, totalTrades=0, timeFiltered=0)
    filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
    appender = OHLC(h5file, filters)

    remove = []
    for f in args["childData"]["remove"]:
        remove.append(re.compile(f))

    allow = []
    for a in args["childData"]["allow"]:
        allow.append(re.compile(a))

    filter = []
    for f in args["childData"]["filter"]:
        filterParts = f.split(",")
        if filterParts[0] == "step":
            filter.append(StepFilter(int(filterParts[1]), float(filterParts[2]), int(filterParts[3])))
        elif filterParts[0] == "floor":
            filter.append(FloorFilter(float(filterParts[1])))
        elif filterParts[0] == "cap":
            filter.append(CapFilter(float(filterParts[1])))

    holdForVolume = bool(args["childData"]["volFollows"])
    copyLastPrice = bool(args["childData"]["copyLast"])
    priceShift = float(args["childData"]["priceShift"])
    tradeVolumeLimit = float(args["childData"]["maxTrade"])

    validFrom = None
    if len(args["childData"]["validFrom"]) > 0:
        validFrom = datetime.datetime.strptime(args["childData"]["validFrom"], "%Y-%m-%d")
    validTo = None
    if len(args["childData"]["validTo"]) > 0:
        validTo = datetime.datetime.strptime(args["childData"]["validTo"], "%Y-%m-%d")
    
    #validFrom = datetime.datetime.fromtimestamp(long(args["validFrom"]), pytz.utc) if args["validFrom"] else None
    #validTo = datetime.datetime.fromtimestamp(long(args["validTo"]), pytz.utc) if args["validTo"] else None

    with gzip.open(str(inPath), 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')

        stats = processor.process(stats, reader, appender, remove, allow, filter, holdForVolume,
                     copyLastPrice, priceShift, tradeVolumeLimit, validFrom, validTo)  

    appender.close()
    print stats




