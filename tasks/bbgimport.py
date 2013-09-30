from tables import *
import numpy
import datetime
import pytz
import time
import pandas as pd
import numpy as np
from pandas.lib import Timestamp
import requests
import glob
import os
import json
import urllib
import sys

class OHLC (object):

    class OHLC_table (IsDescription):
        time            = Int64Col()
        open            = Float64Col()
        high            = Float64Col()
        low             = Float64Col()
        close           = Float64Col()
        volume          = Float64Col()
        openInterest    = Float64Col()

    def __init__ (self, fileName, title):
        #self._group = hdfFile.createGroup("/", 'data', 'Market Data')
        #self._group
        self._file = openFile(fileName, mode = "w", title = title)
        filters = Filters(complevel = 9, complib = "blosc", fletcher32 = False)
        self._table = self._file.createTable(self._file.root, 'data', OHLC.OHLC_table, "data", filters=filters)
    
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
        self._file.close()


def run (fileName, args):
    print "run()"
    
    def parse (v):
        v = v.strip()
        if len(v) == 0 or v == "N.A.":
            return None
        else:
            return float(v)

    reading = False
    lastTicker = None
    writer = None
    nodeDetail = None
    tags = None
    lineCount = 0
    skipTicker = False

    with open(fileName, 'r') as f:
        for l in f.readlines():
            l = l.strip()
            if not reading and l.strip() == "START-OF-DATA":
                print "reading..."
                reading = True
            elif reading and l == "END-OF-DATA":
                print "end"
                break
            elif reading:
                vals = l.split("|")

                if len(vals[3].strip()) > 0:

                    if vals[0] != lastTicker:
                        if writer:
                            writer.close()
                            r = requests.post('http://%s:%s/task/submit' % (args.taskhost, args.taskport),files={"file": (nodeDetail['_id']+".h5", open(nodeDetail['_id']+".h5", 'rb').read())})
                            writer = None
                            print "wrote", lineCount
                            lineCount = 0
                       
                        print "parse ", vals[0] 
                        tags = ["daily", "bbg", vals[0]]    
                        newNode = "http://%s:%s/task/queue?action=create&searchtags=&addtags=" % (args.taskhost, args.taskport) + urllib.quote(",".join(tags)) + "&removetags=&dirty=false&data={}"
                        n = requests.get(newNode)
                        skipTicker = len(n.text.strip()) == 0

                        if not skipTicker:
                            nodeDetail = json.loads(n.text)
                            #nodeDetail = dict(_id="test123")
                            writer = OHLC(nodeDetail['_id']+".h5", ",".join(tags))
                        else:
                            print "skipping", vals[0]                  

                    lastTicker = vals[0]
                    lineCount = lineCount + 1
                    if writer:
                        tickTime = datetime.datetime.strptime(vals[3], "%Y/%m/%d")
                        tickTime = tickTime.replace(tzinfo=pytz.utc)
                        writer.add(tickTime, parse(vals[4]), parse(vals[5]), parse(vals[6]), parse(vals[7]), parse(vals[8]), parse(vals[9]))
    
    if writer:    
        writer.close()
        r = requests.post('http://%s:%s/task/submit' % (args.taskhost, args.taskport),files={"file": (nodeDetail['_id']+".h5", open(nodeDetail['_id']+".h5", 'rb').read())})
                

if __name__ == "__main__":
    run(sys.argv[1])



