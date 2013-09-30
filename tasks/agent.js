var vm = require('vm'),
    http = require('http'),
    argParse = require('argparse');


var parser = new argParse.ArgumentParser({
    version: '0.0.1',
    addHelp: true,
    description: 'Agent arguments'});

parser.addArgument(['--taskhost'], { help: 'Task management host name' });
parser.addArgument(['--taskport'], { help: 'Task management port' });
var args = parser.parseArgs();

var task_path = "/task/queue?action=get&tags=file,tick,future";

http.get( {hostname: args.taskhost, port:args.taskport, path: task_path, agent:false}, 
    function (res)
    {
	var taskData = ""; 
        res.on("data", function (d) {
		taskData += d.toString();
	});

	res.on("end", function () {
		console.log("TASKDATA: " + taskData);
		var taskInfo = JSON.parse(taskData);

                if (taskInfo == null) return;

                var varContext = { output: "", console: console, require: require, taskInfo: taskInfo };
		var context = vm.createContext(varContext);
                console.log(JSON.stringify(taskInfo));
		console.log(taskInfo.childData.detail.code);
		vm.runInNewContext(taskInfo.childData.detail.code, context);
                console.log(varContext.output);
                var updateCall = "/task/queue?action=release&id=" + 
				 encodeURIComponent(taskInfo.node._id) + 
				 "&tags=" + encodeURIComponent(taskInfo.node.tags.join(",")) +
				 "&status=complete" +
				 "&output=" + encodeURIComponent(varContext.output);
                console.log(updateCall);
                http.get( {host: args.taskhost, port:args.taskport, path: updateCall}, function (r) 
                {
                    return;
                }).on("error", function(e) { console.log(e); return; });

	 });
    })
    .on("error", function (e) { console.log(e); });

