var fs = require('fs');
var util = require('util');
var dateFormat = require('dateformat');

module.exports = function () {
    return {
        execute: function (taskInfo, zc, callback) {
            console.log("exec");
            fs.readdir('/media/wayne240/tstoolbox/reuters_original', function (error, files)
            {
                var fileMatch = new RegExp(taskInfo.childData.fileMatch, "g");
                var fileCount = files.length;
                var processCounter = function (fileCount, callback)
                                    {
                                        var files = [];   
                                        return function (filename) 
                                        {
                                            fileCount--;

                                            if (filename != null)
                                            {
                                                console.log(filename);
                                                files.push(filename);
                                            }

                                            if (fileCount == 0)
                                            {
                                                callback(null, files);
                                            }
                                        };
                                    };

                var pc = processCounter(fileCount, callback);

	            files.forEach( function (file)
                {
                    if (file.match(fileMatch))
                    {
                        console.log(file);
                        if (taskInfo.childData.fileType == "fx")
                        {
                            var tags = ["intra5min", "raw", "fx", "AUD"];
                            zc.addTask({file:file, type:'ohlc'}, null, tags, null, false, function () { pc(file); });
                        }
                        else
                        {
                            var contractIndex = file.lastIndexOf('_');
                            var name = file.substr(0, contractIndex);
                            name = name.substr(0, name.lastIndexOf('_'));
                            var contractDate = file.substr(contractIndex+1, file.lastIndexOf('.csv') - contractIndex-1);
                            var contractDateParts = contractDate.split('-');
                            contractDate = new Date();
                            contractDate.setFullYear(parseInt(contractDateParts[0], 10), 
                                                    (parseInt(contractDateParts[1], 10)-1), 
                                                    parseInt(contractDateParts[2], 10));

                            var tags = ["timeAndSales", "raw", "future", //TODO:change to concat
                                        dateFormat(contractDate, "yyyy"), 
                                        dateFormat(contractDate, "mm"), 
                                        name.substr(13,(name.length-15))];

                            zc.addTask({file:file, type:'futureTimeAndSales'}, null, tags, null, false, function () { pc(file); });
                        }
                    }
                    else
                    {
                        pc(null);
                    }
                });
            });
        }
    };
};



