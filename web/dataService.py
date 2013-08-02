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
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.internet import reactor
import argparse
from spark import Sparkplot


class DataServiceIndex (Resource):
    """
    Index.

    """

    isLeaf = True

    def __init__ (self, rootpath):
        self._rootpath = rootpath
        #super(DataServiceIndex, self).__init__()
        Resource.__init__(self)

    def render_GET (self, request):

        print request.args

        if not "file" in request.args:
            return "MISSING ARGUMENTS"

        if "output" in request.args:
            output = request.args["output"]
        else:
            output = None

        filename = self._rootpath + request.args["file"][0] + ".h5"
        returnData = ""

        with openFile(filename, mode = "r") as h5file:

            rows = h5file.root.data.nrows

            if output:
                fromIndex = 0
                toIndex = rows
            else:
                fromIndex = max(0, long(request.args["start"][0]))
                toIndex = min(long(request.args["end"][0]), rows)

            data = h5file.root.data[fromIndex:toIndex]

            if output:

                sp = Sparkplot(type='line', data=data["close"], plot_first=False, plot_last=False)
                returnData = ""
                #, input_file="data.txt", output_file="",
                #     plot_first=True, plot_last=True,
                #     label_first_value=False, label_last_value=False,
                #     plot_min=False, plot_max=False,
                #     label_min=False, label_max=False,                 
                #     draw_hspan=False, hspan_min=-1, hspan_max=0,
                #     label_format="", currency='$', verbose=0):
                request.setHeader('Content-Type', 'image/png')
                request.write(sp.plot_sparkline().getvalue())


            else:
                sample = []

                if fromIndex == 0 and rows > 10000:
                    mult = long(round(rows/10000))
                    count = 0                

                    for i in range(0, rows, mult):
                        sample.append(h5file.root.data[i:(i+1)])
                        count += 1

                elif fromIndex == 0:
                    sample = data

                ohlcData = []
                volData = []
                openinterestData = []
                for r in data:
                    t = float(r['time']/1000)
                    outRow = [t, float(r['open']), float(r['high']), float(r['low']), float(r['close']), float(r['volume'])]
                    volData.append([t, float(r['volume'])])
                    openinterestData.append([t, float(r['openInterest'])])
                    ohlcData.append(outRow)
                    
                outSample = []
                for r in sample:
                    outRow = [float(r['time']/1000), float(r['open']), float(r['high']), float(r['low']), float(r['close']), float(r['volume'])]
                    outSample.append(outRow)

                returnData = json.dumps({'from': long(fromIndex), 'to': long(toIndex), 'summary': outSample, 'ohlc': ohlcData, 'volume': volData, 'openinterest': openinterestData, 'max': long((rows - 1))})

        return returnData


parser = argparse.ArgumentParser(description="Data server")
parser.add_argument('--path', type=str)
args = parser.parse_args()

res = DataServiceIndex(args.path)
factory = Site(res)
reactor.listenTCP(3010, factory)
reactor.run()




