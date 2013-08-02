
var json2csv = require('json2csv');
var ObjectID = require('mongodb').ObjectID;
var url = require('url');
var fs = require('fs');
var microtime = require('microtime');
var request = require('request');


module.exports = function (persist, logDb, nodeDb, zootClient) {

    return {

        /**
         * Display default task page.
         */
        index: function (req, res) {
            console.log("/task/index");
            res.render('task.ejs', { locals : { title: 'working' } });            
        },
        
        /**
         * Detail.
         */
        detail: function (req, res) {
            console.log("/task/detail  --------------?????");
            console.log(req.body);
            var searchTags = JSON.parse(req.body.content);
            console.log(searchTags);
            zootClient.findTasks(searchTags, function (err, tasks) {
                console.log(err);
                res.send(JSON.stringify(tasks));
            });
        },

        submit: function (req, res) {
            console.log("/task/submit");

            fs.readFile(req.files.file.path, function (err, data) {
                var newPath = "/root/data/" + req.files.file.name;
                fs.writeFile(newPath, data, function (err) {
                    if (err) { console.log(err); }
                    res.send("failed here");
                });
            });
        },

        define: function (req, res) {
            console.log("/task/define");
            var options = url.parse(req.url, true).query;

            if (options.action == "get")
            {
                var filePath = "/root/define/" + options.file;
                res.download(filePath, options.file);
                console.log("DONE");
            }
            else if (options.action == "save")
            {
                fs.readFile(req.files.file.path, function (err, data) {
                    var newPath = "/root/define/" + req.files.file.name;
                    fs.writeFile(newPath, data, function (err) {
                        res.redirect("/task");
                        console.log("DONE");
                    });
                });
            }
            else if (options.action == "list")
            {
                var files = fs.readdirSync('/root/define/');
                res.send(JSON.stringify(files));
                console.log("DONE");
            }
            else
            {
                res.send("UNKNOWN ACTION");
                console.log("DONE");
            }
        },

        /**
         * Retrieve a list of tasks.
         */
        find: function (req, res) {
            console.log("/task/find");
            this.request = JSON.parse(req.body.content);
            this.res = res;            
            persist.find(this.request.find, this.request.limit).toArray(function(err, docs) {
                //console.log(docs);
                this.res.send(JSON.stringify(docs));
            }.bind(this));
        },

        /**
         * Add/modify a task.
         */
        save: function (req, res) {
            console.log("/task/save");
            this.res = res;
            this.request = JSON.parse(req.body.content);
            this.currentId = this.request._id == '' ? new ObjectID() : new ObjectID(this.request._id);
            this.request._id = currentId;
            //console.log(this.request);
            persist.update({_id: this.currentId}, this.request, {upsert:true, safe:true}, function(err) {
                if (err)
                {
                    console.warn(err.message);
                    this.res.send(JSON.stringify(err));
                }
                else
                {
                    console.log("add zoot"); //this.request.detail
                    zootClient.addTask({ id: this.request._id }, this.request.searchTags, this.request.addTags, this.request.removeTags, true, true, function () {
                        console.log("zooted");
                        this.res.send(JSON.stringify(this.request));
                    }.bind(this));
                }
            }.bind(this));
        },

        /**
         * Delete an existing filter task.
         */
        delete: function (req, res) {
            console.log("/task/delete");
            //persist.FilterTask.remove(  {'_id' : mongoose.Types.ObjectId(req.body._id)}, 
            //                            function (err, count) { res.send({}); }  
            //);
        },

        /**
         * Interface to get queued tasks.
         */
        queue: function (req, res) {
            console.log("/task/queue");

            var get = function (res)
            {
                return function (taskInfo) {

                    console.log("GOT QUEUE - PARSING");
                    //if (taskInfo != null && typeof(taskInfo.child.tag) === "string") { taskInfo.child.tag = JSON.parse(taskInfo.child.tag); }
                    //console.log("11111111");

                    if (taskInfo != null && taskInfo.node.data.hasOwnProperty("id"))
                    {
                        console.log(taskInfo.node.data.id);
                        persist.find( { _id: taskInfo.node.data.id } ).toArray(function(err, docs) {
                            if (err)
                            {
                                console.warn(err.message);
                                this.res.send(JSON.stringify(err));
                            }
                            else
                            {   
                                taskInfo.childData = docs[0];
                                res.send(JSON.stringify(taskInfo));
                            }
                        }.bind(this));
                    }
                    else
                    {
                        res.send(JSON.stringify(taskInfo));
                    }
                };
            };

            var options = url.parse(req.url, true).query;
            
            if (options.action == "get")
            {
                var tags = options.tags.split(",");
                console.log(tags);
                zootClient.getTask(tags, get(res));
            }
            else if (options.action == "release")
            {
                function _ret (r) { return function () { r.send(""); } };
                console.log(options.status);
                logDb.insert({_id: new ObjectID(), task: options.tags, status: options.status, output: options.output, index: microtime.now()}, {safe:true}, function(err) {
                    if (err) { console.log("ERR: " + err); }

                    console.log("...releasing");
                    //zootClient.releaseTask(JSON.parse(options.task), (options.status == "complete"), _ret(res));
                    var status = (options.status == "complete") ? "" : options.status;
                    zootClient.updateTask(options.id, "", status, _ret(res));
                });
            }
            else if (options.action == "create")
            {
                console.log("CREATE______");
                var searchTags = options.searchtags.length > 0 ? options.searchtags.split(",") : [];
                var addTags = options.addtags.length > 0 ? options.addtags.split(",") : [];
                var removeTags = options.removetags.length > 0 ? options.removetags.split(",") : [];
                var dirty = options.dirty == "true";
                this.res = res;

                zootClient.addTask(JSON.parse(options.data), searchTags, addTags, removeTags, dirty, true, function () {
                    console.log("zooted");
                    this.res.send(JSON.stringify(this.request));
                }.bind(this));
            }
        }
    }
};

