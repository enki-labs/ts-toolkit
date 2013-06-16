import datetime
import pytz


class OhlcMapper(object):

    def __init__ (self, priceShift=0):
        self._columns = []
        self._priceShift = priceShift
        self._fldDate = 10000
        self._fldTime = 10000
        self._fldType = 10000
        self._fldOpen = 10000
        self._fldHigh = 10000
        self._fldLow = 10000
        self._fldClose = 10000
        self._fldVolume = 10000            

    def mapAll (self, cols):
        for index in range(0, len(cols)-1):
            self.map(cols[index], index)

    def map (self, token, index):
        if token == "Date[G]":
            self._fldDate = index
        elif token == "Time[G]":
            self._fldTime = index
        #else if (token == "GMT Offset")
        elif token == "Type":
            self._fldType = index
        elif token == "Open":
            self._fldOpen = index
        elif token == "High":
            self._fldHigh = index
        elif token == "Low":
            self._fldLow = index
        elif token == "Last":
            self._fldClose = index
        elif token == "Volume":
            self._fldVolume = index;

    def mapOk (self):
        return (self._fldDate != 10000 and self._fldTime != 10000 and self._fldType != 10000 and
            self._fldOpen != 10000 and self._fldHigh != 10000 and self._fldLow != 10000 and
            self._fldClose != 10000 and self._fldVolume != 10000 and self._fldQualifiers != 10000 and
            _fldAccVolume != 10000)
    
    def load (self, cols):
        self._columns = cols        
    
    def parseTime (self):
        return datetime.datetime( int(self._columns[self._fldDate][0:4]),
                                int(self._columns[self._fldDate][4:6]),
                                int(self._columns[self._fldDate][6:8]),
                                int(self._columns[self._fldTime][0:2]),
                                int(self._columns[self._fldTime][3:5]),
                                int(self._columns[self._fldTime][6:8]),
                                int(self._columns[self._fldTime][9:15]),
                                pytz.utc)
    
    def parseType (self):
        return self._columns[self._fldType]
    
    def parseOpen (self):
        val = float(self._columns[self._fldOpen])
        if self._priceShift:
            val = val * self._priceShift
        return val

    def parseHigh (self):
        val = float(self._columns[self._fldHigh])
        if self._priceShift:
            val = val * self._priceShift
        return val

    def parseLow (self):
        val = float(self._columns[self._fldLow])
        if self._priceShift:
            val = val * self._priceShift
        return val
        
    def parseClose (self):
        val = float(self._columns[self._fldClose])
        if self._priceShift:
            val = val * self._priceShift
        return val

    def hasVolume (self):
        return  not self._columns[self._fldVolume] == ""
    
    def parseVolume (self):
        return float(self._columns[self._fldVolume])


