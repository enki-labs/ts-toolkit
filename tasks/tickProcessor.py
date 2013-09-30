import pytz
import datetime

class WeekendFilter (object):

    def __init__ (self, timezone=None, weekEnd=None, weekStart=None):

        self._check = False

        if timezone:
            self._check = True
            self._weekEnd = datetime.datetime.strptime(weekEnd, "%A %H:%M")
            self._weekStart = datetime.datetime.strptime(weekStart, "%A %H:%M")
            self._localZone = pytz.timezone(timezone)

            weekOrdinalMap = dict(Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6)
            self._weekEndDay = weekOrdinalMap[weekEnd.split(" ")[0]]
            self._weekStartDay = weekOrdinalMap[weekStart.split(" ")[0]]
            self._weekEndTime = self._weekEnd.time()
            self._weekStartTime = self._weekStart.time()
            

    def ok (self, checkTime):

        ok = True

        if not self._check:
            ok = False

        else:
            localizedTime = checkTime.astimezone(self._localZone)
            dayOfWeek = localizedTime.weekday()
            if dayOfWeek >= self._weekEndDay and dayOfWeek <= self._weekStartDay:
                if dayOfWeek == self._weekEndDay:
                    ok = not (localizedTime.time() >= self._weekEndTime)                    
                elif dayOfWeek == self._weekStartDay:
                    ok = not (localizedTime.time() < self._weekStartTime)
                else:
                    ok = False
        return ok


class FxProcessor (object):

    def __init__ (self, mapper):
        self._mapper = mapper

    def process (self, stats, reader, appender):
        header = True
        for row in reader:
            stats.lines += 1

            if header:
                self._mapper.mapAll(row)
                if not self._mapper.mapOk():
                    raise Exception("Bad file - cannot map ((%s))" % row)
                header = False
                continue

            self._mapper.load(row)
            if self._mapper.hasOpen():
                if self._mapper.parseOpen() == 0.0 or self._mapper.parseHigh() == 0.0 or self._mapper.parseLow() == 0.0 or self._mapper.parseLast() == 0.0:
                    print "SKIP", row
                else:
                    appender.add(   self._mapper.parseTime()
                            ,   self._mapper.parseOpen()
                            ,   self._mapper.parseHigh()
                            ,   self._mapper.parseLow()
                            ,   self._mapper.parseLast()
                            ,   self._mapper.parseVolume()
                            ,   0.0
                            )
        return stats


class TickProcessor (object):

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
                 validTo,
                 weekTimezone,
                 weekEnd,
                 weekStart):

        timeCheck = WeekendFilter(weekTimezone, weekEnd, weekStart)
        copyLastPriceTimeout = datetime.timedelta(minutes = 5)
        lastTradeTime = 0
        lastTradePrice = 0
        thisAccVolume = 0
        lastAccVolume = 0
        volumeJump = False
        checkFromTime = validFrom != None
        checkToTime = validTo != None
        parsedTime = -1
        filterAllRemaining = False

        header = True
        for row in reader:
            stats.lines += 1

            if filterAllRemaining:
                stats.timeFiltered += 1
                continue

            if header:
                self._mapper.mapAll(row)
                if not self._mapper.mapOk():
                    raise Exception("Bad file - cannot map ((%s))" % row)
                header = False
                continue

            self._mapper.load(row)
            tickType = self._mapper.parseType()
            qualifiers = self._mapper.parseQualifiers()
            
            if tickType == "Trade":

                parsedTime = self._mapper.parseTime()

                if not timeCheck.ok(parsedTime):
                    stats.weekendCount += 1
                    print "FWEEK", row 
                    continue

                if checkFromTime or checkToTime:

                    if checkFromTime:
                        if parsedTime >= validFrom:
                            checkFromTime = False
                        else:
                            stats.timeFiltered += 1
                            #print "FTIME2", row
                            continue                            

                    if checkToTime:
                        if parsedTime >= validTo:
                            filterAllRemaining = True
                            print "FREMAIN", row
                            continue

                stats.totalTrades += 1

                if self._mapper.hasAccVolume():
                    
                    newAccVolume = self._mapper.parseAccVolume()
                    
                    if volumeJump:           
                        if (lastAccVolume < thisAccVolume and 
                           thisAccVolume <= newAccVolume or
                           thisAccVolume < lastAccVolume and
                           thisAccVolume <= newAccVolume): #volume has reset to new level
                            lastAccVolume = thisAccVolume
                        
                        volumeJump = False
                    
                    thisAccVolume = newAccVolume
                
                tradeVol = 0.0
                filterTrade = True
                
                for allow in allows:
                    if allow.match(qualifiers):
                        filterTrade = False
                        break
                
                if filterTrade:
                    filterTrade = False             
                    for filter in filters:
                        if filter.match(qualifiers):
                            stats.qualifierFiltered += 1
                            filterTrade = True
                            print "FFILTER", row
                            break
                
                if not filterTrade:
                    if holdForVolume:  #Handle markets where there is no volume reported on trades.
                                       #Trade volume will be derived from the delta of accumulated volume reported.
                        if self._mapper.hasPrice():
                            holdForVolume =  not self._mapper.hasVolume()
                        
                            if holdForVolume:
                                if parsedTime != -1:
                                    lastTradeTime = parsedTime
                                else:
                                    lastTradeTime = self._mapper.parseTime()
                                lastTradePrice = self._mapper.parsePrice()
                                print "HOLDVOL", row
                                continue
                        elif self._mapper.hasAccVolume():
                            tradeVol = max((thisAccVolume - lastAccVolume), 1.0)
                            
                            if lastTradeTime:
                                filterTick = False
                                for tickFilter in tickFilters:
                                    if tickFilter.filter(lastTradeTime, lastTradePrice, tradeVol):
                                        stats.priceFiltered += 1
                                        filterTick = True
                                        print "FPRICE", row
                                        break
                                if not filterTick and self.priceOk(lastTradePrice) and self.volumeOk(tradeVol, tradeVolumeLimit):
                                    stats.tradeCount += 1
                                    appender.add(   lastTradeTime
                                                ,   lastTradePrice
                                                ,   lastTradePrice
                                                ,   lastTradePrice
                                                ,   lastTradePrice
                                                ,   tradeVol
                                                ,   0.0
                                                )
                                else:
                                    stats.badTradeCount += 1
                                    print "FBAD", row
                            
                            if self.volumeOk(tradeVol, tradeVolumeLimit):
                                lastAccVolume = thisAccVolume
                            else:
                                volumeJump = True
                            continue
                        else:
                            stats.tradeNoVolCount += 1
                            print "FVOL", row

                    elif self._mapper.hasPrice() or copyLastPrice: #Trade record has volume reported on trade.
                        newTradeTime = 0

                        if parsedTime != -1:
                            newTradeTime = parsedTime
                        else:
                            newTradeTime = self._mapper.parseTime()

                        newTradeOk = True                      
                        
                        if self._mapper.hasPrice():
                            lastTradePrice = self._mapper.parsePrice()
                        elif lastTradeTime != 0: #copy last price
                            newTradeOk = (newTradeTime - lastTradeTime) <= copyLastPriceTimeout
                        
                        lastTradeTime = newTradeTime
                        
                        if newTradeOk and self._mapper.hasVolume():

                            tradeVol = max(self._mapper.parseVolume(), 1.0)
                            filterTick = False

                            for tickFilter in tickFilters:
                                if tickFilter.filter(lastTradeTime, lastTradePrice, tradeVol):
                                    stats.priceFiltered += 1
                                    filterTick = True
                                    print "FPRICE2", row
                                    break
                            priceOk = self.priceOk(lastTradePrice)
                            volOk = self.volumeOk(tradeVol, tradeVolumeLimit)                           
 
                            if not filterTick and priceOk and volOk:
                                stats.tradeCount += 1                                
                                appender.add(   lastTradeTime
                                            ,   lastTradePrice
                                            ,   lastTradePrice
                                            ,   lastTradePrice
                                            ,   lastTradePrice
                                            ,   tradeVol
                                            ,   0.0
                                            )
                            else:
                                stats.badTradeCount += 1
                                print "FBAD2", row, "FILTER", filterTick, "PRICE", priceOk, "VOL", volOk

                        elif newTradeOk and thisAccVolume:
                            if lastAccVolume > (thisAccVolume + (lastAccVolume * 0.5)):
                                tradeVol = thisAccVolume #vol reset
                            else:
                                tradeVol = thisAccVolume - lastAccVolume

                            tradeVol = max(tradeVol, 1.0)
                            
                            filterTick = False

                            for tickFilter in tickFilters:
                                if tickFilter.filter(lastTradeTime, lastTradePrice, tradeVol):
                                    stats.priceFiltered += 1
                                    filterTick = True
                                    print "FPRICE3", row
                                    break
                            
                            if not filterTick and self.priceOk(lastTradePrice) and self.volumeOk(tradeVol, tradeVolumeLimit):
                                stats.tradeCount += 1
                                appender.add(   lastTradeTime
                                            ,   lastTradePrice
                                            ,   lastTradePrice
                                            ,   lastTradePrice
                                            ,   lastTradePrice
                                            ,   tradeVol
                                            ,   0.0
                                            )
                            else:
                                stats.badTradeCount += 1
                                print "FBAD3", row

                        elif newTradeOk:
                            stats.tradeNoVolCount += 1
                            print "FVOL3", row

                    else: #check for volume reset
                        if thisAccVolume == 0:
                            lastAccVolume = thisAccVolume
                
                if self.volumeOk(tradeVol, tradeVolumeLimit):
                    lastAccVolume = thisAccVolume

                else:
                    volumeJump = True

        return stats


    def priceOk (self, price):
    
        if price <= 0.0:
            return False
    
        return True

    def volumeOk (self, volume, tradeVolumeLimit):
        if volume >= 0 and volume < tradeVolumeLimit:
            return True
    
        return False

