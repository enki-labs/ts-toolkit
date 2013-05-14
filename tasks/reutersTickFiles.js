
var fs = require('fs'),
    Zoot = require('zoot'),
    util = require('util'),
    dateFormat = require('dateformat');

var zc = new Zoot('http://omnius01:7474', 'omnius01', 6379, function () {

    console.log("Read files");

    fs.readdir('/media/wayne240/tstoolbox_bak/reuters_original', function (error, files)
    {
        console.log("Process " + files.length + " files.");
        //var fileMatch = new RegExp("TimeAndSales_[A-Z].*[A-Z][0-9]_[0-9].*", "g");
        var fileMatch = new RegExp("TimeAndSales_ES.*[A-Z][0-9]_[0-9].*", "g");
        var fileCount = files.length;

        var processFiles = function (files) {
                                return function (index, processor)
                                {
                                    if (index < 0) return;

                                    var file = files[index];
                                    if (file.match(fileMatch))
                                    {
                                        console.log(file);
                                        var contractIndex = file.lastIndexOf('_');
                                        var name = file.substr(0, contractIndex);
                                        name = name.substr(0, name.lastIndexOf('_'));
                                        var contractDate = file.substr(contractIndex+1, 
                                            file.lastIndexOf('.csv') - contractIndex-1);
                                        var contractDateParts = contractDate.split('-');
                                        contractDate = new Date();
                                        contractDate.setFullYear(
                                            parseInt(contractDateParts[0], 10),
                                            (parseInt(contractDateParts[1], 10)-1),
                                            parseInt(contractDateParts[2], 10));
                                        var tags = ["timeAndSales", "raw", "future", 
                                                    dateFormat(contractDate, "yyyy"), 
                                                    dateFormat(contractDate, "mm"), 
                                                    name.substr(13,(name.length-15))];
                                        this.processor = processor;
                                        var nextStep = function () 
                                            { this.processor(index-1, this.processor); }.bind(this);
                                        zc.addTask({ file: file, type: 'futureTimeAndSales' }, 
                                                   null, tags, null, false, nextStep);
                                    }
                                    else
                                    {
                                        processor(index-1, processor);
                                    }
                                };
                            };

        var processor = processFiles(files);
        processor(files.length -1, processor);
    });
});


