from tables import *
import numpy
import csv
import gzip
import datetime
import pytz
import bunch
import tickMapper
import fxMapper
import tickProcessor
import ohlcMapper
import ohlcProcessor
import re
import time
import sys
import json
import os
import glob
from multiprocessing import Pool

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
        if "data" in hdfFile.root:
            self._table = hdfFile.root.data
        else:
            self._table = hdfFile.createTable(hdfFile.root, 'data', OHLC.OHLC_table, "data", filters=filters)
    
    def add (self, t, open, high, low, close, volume, openInterest, raw=False):
        row = self._table.row
        if raw:
            row['time'] = t
        else:
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
        if price < self._minPrice:
            print "TRIGGERED FLOOR", price, self._minPrice
            return True
        else:
            return False

class CapFilter (object):

    def __init__ (self, maxPrice):
        self._maxPrice = maxPrice

    def filter (self, time, price, volume):
        if price > self._maxPrice:
            print "TRIGGERED CAP", price, self._maxPrice
            return True
        else:
            return False

class StepFilter (object):

    def __init__ (self, timeoutSeconds, maxPriceStep, maxFilterCount):
        self._filterCount = 0
        self._timeout = datetime.timedelta(seconds = timeoutSeconds)
        self._maxPriceStep = maxPriceStep
        self._maxFilterCount = maxFilterCount
        self._lastTime = None
        self._lastPrice = None

    def filter (self, time, price, volume):
    
        filtered = False

        if (( self._lastTime and self._lastPrice )
           and   ( abs(price - self._lastPrice) >= self._maxPriceStep )
           and   ( (time - self._lastTime) <= self._timeout )
           and   ( self._filterCount < self._maxFilterCount ) ):
            self._filterCount += 1
            filtered = True

        else:
            self._lastTime = time
            self._lastPrice = price
            self._filterCount = 0
            filtered = False
 
        if filtered:
            print "TRIGGERED STEP", abs(price-self._lastPrice), self._maxPriceStep
        return filtered

def processFile (fileName, args):
    stats = bunch.Bunch(lines=0)
    mapper = fxMapper.FxMapper()
    processor = tickProcessor.FxProcessor(mapper)
    fileName = str(fileName)
    with openFile(args.temppath + fileName + ".h5", mode = "w", title = "") as h5file:
        filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
        appender = OHLC(h5file, filters)
        with gzip.open(hdfrawpath + fileName, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='|')
            stats = processor.process(stats, reader, appender)
        appender.close()

class FxTick (object):

    def __init__ (self):
        pass

    def run (self, infiles, outfile, args):
        threadPool = Pool(1)
        stats = bunch.Bunch(lines=0)
        os.chdir(args.rawpath)
        files = glob.glob(infiles)
        files.sort()
        threadPool.map(processFile, files)

        print "Merge files..."
        with openFile(args.hdfpath + outfile, mode = "w", title = ",".join([""])) as h5file:
            filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
            appender = OHLC(h5file, filters)
            os.chdir(args.temppath)
            for f in files:
                with openFile(str(f)+".h5", mode = "r") as h5file:
                    for r in h5file.root.data[:]:
                        appender.add(r["time"], r["open"], r["high"], r["low"], r["close"], r["volume"], r["openInterest"], raw=True)
            appender.close()
        return stats


class Tick (object):
    def __init__ (self, params, taskInfo):
        self._params = params
        self._taskInfo = taskInfo

    def run (self):
        print self._params
        print self._taskInfo
        #return

        inPath = os.path.join(args.rawpath, self._taskInfo["parent"][0]["data"]["file"])
        outPath = os.path.join(args.temppath, (self._taskInfo["node"]["_id"] + ".h5"))

        filterParams = []
        if "filters" in self._params:
            filterParams = self._params["filters"]
        else:
            filterParams.append(self._params)

        with openFile(str(outPath), mode = "w", title = ",".join(self._taskInfo["node"]["tags"])) as h5file:

            stats = bunch.Bunch(lines=0, qualifierFiltered=0, priceFiltered=0, badTradeCount=0, tradeNoVolCount=0, tradeCount=0, totalTrades=0, timeFiltered=0, weekendCount=0)
            for filterParam in filterParams:
                print "---Filter----------------------------"
                print filterParam
                print "-------------------------------------"
                mapper = None
                processor = None

                if self._taskInfo["parent"][0]["data"]["type"] == "futureTimeAndSales":
                    mapper = tickMapper.TickMapper()
                    processor = tickProcessor.TickProcessor(mapper)
                elif self._taskInfo["parent"][0]["data"]["type"] == "ohlc":
                    mapper = ohlcMapper.OhlcMapper()
                    processor = ohlcProcessor.OhlcProcessor(mapper)
            
                filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
                appender = OHLC(h5file, filters)

                remove = []
                for f in filterParam["remove"]:
                    remove.append(re.compile(f))

                allow = []
                for a in filterParam["allow"]:
                    allow.append(re.compile(a))

                filter = []
                for f in filterParam["filter"]:
                    filterParts = f.split(",")
                    if filterParts[0] == "step":
                        #print "STEP:", filterParts[1], "][", filterParts[2], "][", filterParts[3], "]"
                        filter.append(StepFilter(int(filterParts[1]), float(filterParts[2]), int(filterParts[3])))
                    elif filterParts[0] == "floor":
                        #print "FLOOR:", filterParts[1], "]"
                        filter.append(FloorFilter(float(filterParts[1])))
                    elif filterParts[0] == "cap":
                        #print "CAP:", filterParts[1], "]"
                        filter.append(CapFilter(float(filterParts[1])))

                holdForVolume = bool(filterParam["volFollows"])
                copyLastPrice = bool(filterParam["copyLast"])
                priceShift = float(filterParam["priceShift"])
                tradeVolumeLimit = float(filterParam["maxTrade"])
                #print holdForVolume, copyLastPrice, priceShift, tradeVolumeLimit

                print filterParam["validFrom"], type(filterParam["validFrom"]), filterParam["validTo"], type(filterParam["validTo"])
                validFrom = None
                if filterParam["validFrom"]: #and len(filterParam["validFrom"]) > 0:
                    validFrom = filterParam["validFrom"] #datetime.datetime.strptime(filterParam["validFrom"], "%Y-%m-%d")
                    validFrom = validFrom.replace(tzinfo=pytz.utc)
                validTo = None
                if filterParam["validTo"]: # and len(filterParam["validTo"]) > 0:
                    validTo = filterParam["validTo"] #datetime.datetime.strptime(filterParam["validTo"], "%Y-%m-%d")
                    validTo = validTo.replace(tzinfo=pytz.utc)
            
                timezone = None
                weekEnd = None
                weekStart = None
                if len(filterParam["weekTimezone"]) > 0:
                    timezone = filterParam["weekTimezone"]
                    weekEnd = filterParam["weekEnd"]
                    weekStart = filterParam["weekStart"]
                #validFrom = datetime.datetime.fromtimestamp(long(args["validFrom"]), pytz.utc) if args["validFrom"] else None
                #validTo = datetime.datetime.fromtimestamp(long(args["validTo"]), pytz.utc) if args["validTo"] else None

                with gzip.open(str(inPath), 'rb') as csvfile:
                    reader = csv.reader(csvfile, delimiter=',', quotechar='|')

                    stats = processor.process(stats, reader, appender, remove, allow, filter, holdForVolume,
                             copyLastPrice, priceShift, tradeVolumeLimit, validFrom, validTo, timezone, weekEnd, weekStart)  

                appender.close()
            return stats



