
var proc = require('child_process'),
    datejs = require('datejs'),
    Zoot = require('zoot');

var exit = false;
var taskRunning = false;
var that = this;

var runNext = function (zc, that)
{
    return function (taskInfo)
    {
        console.log(taskInfo);
        taskRunning = true;
        var argtest = taskInfo.childData;
        argtest.output = taskInfo.child.key;
        argtest.input = taskInfo.parentData.file;
        argtest["validFrom"] = (Date.parse(argtest["validFrom"], 'yyyy-MM-dd') / 1000); 
        argtest["validTo"] = (Date.parse(argtest["validTo"], 'yyyy-MM-dd') / 1000); 
        argtest["allow"] = argtest["allow"].split('\r\n');
        argtest["remove"] = argtest["remove"].split('\r\n');
        argtest["filter"] = argtest["filters"].split('\r\n');    
        argtest["volFollows"] = false;

        var process = proc.spawn('/usr/bin/python', ['/home/wayne/src/prologue/build/import.py', JSON.stringify(argtest)]);
        process.stdout.on('data', function (data) { var buff = new Buffer(data); });
        process.stderr.on('data', function (data) { var buff = new Buffer(data); });
        process.stdout.on('end', function (data) { zc.releaseTask(task, false, function() { getNext(zc, that)(); });
        process.stderr.on('end', function (data) {});
        process.stdout.on('exit', function (code) { if (code != 0) { console.log('FAIL!'); } });        
    };
};

var getNext = function (zc, that)
{
    return function ()
    {
        if (!exit)
        {
            taskRunning = false;
            zc.getTask(['filtered'], runNext(zc, that));
        }
    };
};

var zc = new Zoot('http://omnius01:7474', 'omnius01', 6379);
getNext(z, that)();


