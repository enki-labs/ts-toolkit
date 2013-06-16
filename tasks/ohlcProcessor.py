import pytz
import datetime


class OhlcProcessor (object):

    def __init__ (self, mapper):
        self._mapper = mapper

    def process (self,
                 stats,
                 reader,
                 appender,
                 filters,
                 allows,
                 tickFilters,
                 holdForVolume,
                 copyLastPrice,
                 priceShift,
                 tradeVolumeLimit,
                 validFrom,
                 validTo):

        copyLastPriceTimeout = datetime.timedelta(minutes = 5)
        lastTradeTime = 0
        lastTradePrice = 0
        thisAccVolume = 0
        lastAccVolume = 0
        tradeCount = 0
        qualifierFiltered = 0
        priceFiltered = 0
        totalTrades = 0
        tradeNoVolCount = 0
        badTradeCount = 0
        lastBad = 0
        volumeJump = False
        checkFromTime = validFrom != None
        checkToTime = validTo != None
        parsedTime = -1
        filterAllRemaining = False

        header = True
        for row in reader:
            stats.lines += 1
            #if stats.lines % 50000 == 0:
            #    print stats.lines

            if filterAllRemaining:
                stats.timeFiltered += 1
                continue

            if header:
                self._mapper.mapAll(row)
                header = False
                continue

            self._mapper.load(row)
            rowType = self._mapper.parseType()
            
            if rowType.startswith("Intraday"):

                if checkFromTime or checkToTime:

                    parsedTime = self._mapper.parseTime()

                    if checkFromTime:
                        if parsedTime >= validFrom:
                            checkFromTime = False
                        else:
                            stats.timeFiltered += 1
                            continue                            

                    if checkToTime:
                        if parsedTime >= validTo:
                            filterAllRemaining = True
                            continue

                stats.totalTrades += 1

                filterTick = False
                if not lastTradeTime == 0:
                    filterTick = False
                    for tickFilter in tickFilters:
                        if tickFilter.filter(self._mapper.parseTime(), self._mapper.parseOpen(), self._mapper.parseVolume()):
                            stats.priceFiltered += 1
                            filterTick = True
                            break
                else:
                    lastTradeTime = self._mapper.parseTime()
                    lastTradePrice = self._mapper.parseOpen()

                if not filterTick and self.priceOk(self._mapper.parseOpen()) and self.volumeOk(self._mapper.parseVolume(), tradeVolumeLimit):
                    stats.tradeCount += 1
                    appender.add(   self._mapper.parseTime()
                                ,   self._mapper.parseOpen()
                                ,   self._mapper.parseHigh()
                                ,   self._mapper.parseLow()
                                ,   self._mapper.parseClose()
                                ,   self._mapper.parseVolume()
                                ,   0.0
                                )
                else:
                    stats.badTradeCount += 1

        return stats


    def priceOk (self, price):
    
        if price <= 0.0:
            return False
    
        return True

    def volumeOk (self, volume, tradeVolumeLimit):
        if volume >= 0 and volume < tradeVolumeLimit:
            return True
    
        return False





