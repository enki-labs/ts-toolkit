
var proc = require('child_process'),
    datejs = require('datejs'),
    Zoot = require('zoot');

var exit = false;
var taskRunning = false;
var that = this;

var ArgumentParser = require('argparse').ArgumentParser;
var parser = new ArgumentParser({version: '0.0.1', addHelp:true, description: 'Task agent.'});
parser.addArgument(['--tags'], {help:'Task tags'});
parser.addArgument(['--proc'], {help:'Agent process'});
parser.addArgument(['--type'], {help:'Agent process type'});
parser.addArgument(['--debug'], {help:'Debug mode'});
var args = parser.parseArgs();
var taskTags = args.tags.split(',');

function handleOutput (output, data)
{
    var buff = new Buffer(data);
    var line = buff.toString('utf8');
    output += line;
    console.log(line);
}

var runNext = function (zc, that)
{
    return function (taskInfo)
    {
        if (taskInfo == null)
        {
            getNext(zc, that)();
            return;
        }

        taskRunning = true;
        console.log(taskInfo);

        if (args.type == "python")
        {
            var agentProcess = require('path').resolve(__dirname, args.proc)
            var process = proc.spawn('/usr/bin/python', [agentProcess, JSON.stringify(taskInfo)]);
            var output = '';
            process.stdout.on('data', function (data) { handleOutput(output, data); });
            process.stderr.on('data', function (data) { handleOutput(output, data); });
            process.stdout.on('end', function (data) { 
                console.log("--RELEASE--");
                if (args.debug == "1") { zc.releaseTask(taskInfo, false, function() {}); }
                else { zc.releaseTask(taskInfo, true, function() { getNext(zc, that)(); });
                }
            });
            process.stderr.on('end', function (data) {});
            process.stdout.on('exit', function (code) { if (code != 0) { console.log('FAIL!'); } else { console.log("!!!!!SUCCESS!!!!!!"); } });
        }
        else if (args.type == "node")
        {
            console.log("import");
            var process = require(args.proc);
            process().execute(taskInfo, zc, function (err, output) {
                if (err) { console.log(err); }
                else { zc.releaseTask(taskInfo, true, function() { getNext(zc, that)(); }); }
            });
        }
    };
};

var getNext = function (zc, that)
{
    return function ()
    {
        if (!exit)
        {
            taskRunning = false;
            zc.getTask(taskTags, runNext(zc, that));
        }
    };
};

var zc = new Zoot('http://omnius01:7474', 'omnius01', 6379, function () { getNext(zc, that)(); });



