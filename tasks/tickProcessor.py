import pytz
import datetime


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
            tickType = self._mapper.parseType()
            qualifiers = self._mapper.parseQualifiers()
            
            if tickType == "Trade":

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
                            #std::cout << "__QUALIFIER__" << qualifiers << "__QUALIFIER__\n__FILTER__" << filter << "__FILTER__" << std::endl;
                            stats.qualifierFiltered += 1
                            filterTrade = True
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
                                continue
                            #else:
                            #    LOG_DEBUG1("Not holding for volume after parsing (" << line << ")")
                        elif self._mapper.hasAccVolume():
                            tradeVol = max((thisAccVolume - lastAccVolume), 1.0)
                            
                            if lastTradeTime:
                                filterTick = False
                                for tickFilter in tickFilters:
                                    if tickFilter.filter(lastTradeTime, lastTradePrice, tradeVol):
                                        stats.priceFiltered += 1
                                        filterTick = True
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
                            
                            if self.volumeOk(tradeVol, tradeVolumeLimit):
                                lastAccVolume = thisAccVolume
                            else:
                                volumeJump = True
                            continue
                        else:
                            stats.tradeNoVolCount += 1

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

                        elif newTradeOk:
                            stats.tradeNoVolCount += 1

                    else: #check for volume reset
                        if thisAccVolume == 0:
                            lastAccVolume = thisAccVolume
                
                if self.volumeOk(tradeVol, tradeVolumeLimit):
                    lastAccVolume = thisAccVolume

                else:
                    volumeJump = True

        return stats

    #catch (boost::exception& ex)
    #{
    #    //LOG_WARN("Failed on line (" << lineCount << ") (" << line << ")")
    #    throw;
    #}
    #catch (std::exception& ex)
    #{
    #    //LOG_WARN("Failed on line (" << lineCount << ") (" << line << ") " << ex.what())
    #    throw;
    #}
    #std::cout << "lines(" << lineCount << ") totalTrades(" << totalTrades << ") trades(" << tradeCount << ") qualifierFiltered(" << qualifierFiltered << ") priceFiltered(" << priceFiltered << ") bad(" << badTradeCount << ") skipped zero vol(" << tradeNoVolCount << ")" << std::endl;
    

    def priceOk (self, price):
    
        if price <= 0.0:
            return False
    
        return True

    def volumeOk (self, volume, tradeVolumeLimit):
        if volume >= 0 and volume < tradeVolumeLimit:
            return True
    
        return False





