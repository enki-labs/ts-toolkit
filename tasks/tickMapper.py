import datetime
import pytz


class TickMapper(object):

    def __init__ (self, priceShift=0):
        self._columns = []
        self._priceShift = priceShift
        self._fldDate = 10000
        self._fldTime = 10000
        self._fldType = 10000
        self._fldPrice = 10000
        self._fldVolume = 10000
        self._fldQualifiers = 10000
        self._fldAccVolume = 10000                

    def mapAll (self, cols):
        for index in range(0, len(cols)):
            self.map(cols[index], index)

    def map (self, token, index):
        if token == "Date[G]":
            self._fldDate = index
        elif token == "Time[G]":
            self._fldTime = index
        elif token == "Type":
            self._fldType = index
        elif token == "Price":
            self._fldPrice = index
        elif token == "Volume":
            self._fldVolume = index;
        elif token == "Qualifiers":
            self._fldQualifiers = index
        elif token == "Acc. Volume":
            self._fldAccVolume = index
        else:
            print "Unknown token (%s) of type (%s)" % (token, type(token))

    def mapOk (self):
        return (self._fldDate != 10000 and self._fldTime != 10000 and self._fldType != 10000 and
            self._fldPrice != 10000 and self._fldVolume != 10000 and self._fldQualifiers != 10000 and
            self._fldAccVolume != 10000)
    
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

    def hasPrice (self):
        return not self._columns[self._fldPrice] == ""
    
    def parsePrice (self):
        val = float(self._columns[self._fldPrice])
        if self._priceShift:
            val = val * self._priceShift

        return val
        
    def hasVolume (self):
        return  not self._columns[self._fldVolume] == ""
    
    def parseVolume (self):
        return float(self._columns[self._fldVolume])
    
    def parseQualifiers (self):
        return self._columns[self._fldQualifiers]

    def hasAccVolume (self):
        return  not self._columns[self._fldAccVolume] == ""
    
    def parseAccVolume (self):
        return float(self._columns[self._fldAccVolume])
