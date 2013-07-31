
var ObjectID = require('mongodb').ObjectID;
var async = require('async');
var util = require('util');

/**
 * Init Z.
 */
var Z = function (db)
{
    console.log("ZZZZZZZZ");
    this.db = db;
};

Z.prototype._combineTags = function (existingTags, addTags, removeTags)
{
    var tags = [];

    for (tagIndex in existingTags)
    {
        var tag = existingTags[tagIndex];
        if (removeTags.indexOf(tag) < 0)
        {
            tags.push(tag);
        }
    }
    
    for (tagIndex in addTags)
    {
        tags.push(addTags[tagIndex]);
    }

    return tags.sort();
};

Z.prototype.updateTask = function (id, dirty, status, callback)
{
    var self = this;
    console.log("111");
    self.db.update({_id: new ObjectID(id)}, {$set: { status: status, dirty: dirty }}, {safe:true}, function(err) {
        console.log("222");
        callback(err);
        console.log("333");
    });
    console.log("444");
};

Z.prototype.findTasks = function (searchTags, callback)
{
    var self = this;
    self.db.find({ 'tags' : { $all : searchTags } }, {}).toArray ( function (err, nodes) {
        callback(err, nodes);
    });
};

Z.prototype.getTask = function (searchTags, callback)
{
    console.log("GET TASK");
    var self = this;

    self.db.find({ 'tags' : { $all : searchTags } }, {}).toArray( function (err, nodes) {

        if (err || nodes.length == 0)
        {
            console.log("RETURN NOTHING");
            callback(err); 
            return; 
        }

        console.log("CHECK NODES");
        async.eachSeries(nodes, function (node, next) {

                console.log(node.dirty); console.log(node.status);
                if (node.dirty && node.status == "")
                {
                    console.log(node.parent);
                    if (node.parent.length == 0)
                    {
                        console.log("FIND AND MODIFY");
                        self.db.findAndModify({_id: node._id, status: ""}, {}, {$set: { status: "working" }}, { safe:true }, function (err, result) {
                            if (err) { callback(err); return; }
                            if (result) { console.log("CALLBACK"); callback({parent: [], node: node}); return; }
                            else { next(); console.log("ATOM FAILED"); } //atomic update failed
                        });
                    }
                    else
                    {
                        console.log("CHECK PARENT");
                        self.db.find( {'_id': { $in : node.parent }}, {}).toArray( function(err, parents) {
                        
                            if (err) { callback(err); return; }

                            console.log(parents);
                            async.eachSeries(parents, function (parent, nextParent) {
                                    console.log(parent.dirty);
                                    if (parent.dirty) nextParent("break");
                                    else nextParent();

                                },
                                function (err) {
                                    console.log(err);
                                    if (err == "break") next();
                                    else if (err) callback(err);
                                    else
                                    {
                                        console.log("FIND AND MODIFY 2");
                                        self.db.findAndModify({_id: node._id, status: ""}, {}, {$set: { status: "working" }}, { safe:true }, function (err, result) {
                                            console.log(result);
                                            if (err) { callback(err); return; }
                                            if (result) { callback({parent: parents, node: node}); return; }
                                            else { console.log("ATOM FAILED 2"); next(); } //atomic update failed
                                        });
                                    }
                                }
                            );                            
                        });
                    }
                }
                else
                {
                    console.log("next()");
                    next();
                }
            },
            function (err) {
                console.log("CALLBACK NONE ERROR");
                callback(null);
            }
        );
    });
};

/**
 * Add a task.
 */
Z.prototype.addTask = function (taskData, searchTags, addTags, removeTags, markDirty, replaceExisting, done)
{
    console.log("ADDTASK___________________ADDTASK_______________");
    var self = this;

    if (searchTags == null || searchTags.length == 0)
    {
        console.log("NO SEARCH TAGS!!!!");
        self.db.find({ 'tags' : { $all : addTags } }, {}).toArray( function (err, nodes) {

            if (err) { callback(err); return; }

            if (nodes.length > 0)
            {
                async.eachSeries(nodes, function (node, next) {
                        //console.log(node);
                        node.data = taskData;
                        node.dirty = markDirty;
                        self.db.update({_id: node._id}, node, {upsert:true, safe:true}, function(err) {
                            next(err);
                        });
                    },
                    function (err) {
                        done(err);
                    }
                );
            }
            else
            {
                var node = {_id: new ObjectID(), 
                            searchTags: searchTags, 
                            tags: self._combineTags([], addTags, removeTags), 
                            dirty: markDirty,
                            status: "",
                            parent: [],
                            child: [],
                            data: taskData };

                self.db.update({_id: node._id}, node, {upsert:true, safe:true}, function(err) {
                    done(err);
                });
            }
        });

    }
    else
    {
        console.log("WITH SEARCH TAGS");
        self.db.find({ 'tags' : { $all : searchTags } }, {}).toArray( function (err, nodes) {
            
            console.log("COUNT____COUNT__( " + nodes.length);
            if (nodes.length > 0)
            {
                var childTags = {};
                async.eachSeries(nodes, function (node, next) {
                        console.log("CHECKING NODE");
                        if (node.child.length > 0)
                        {
                            async.eachSeries(node.child, function (childId, nextChild) {
                                    self.db.find({ '_id' : childId }, {limit: 1}).toArray( function (err, childNodes) {
                                        if (err) { done(err); return; }
                                        if (childNodes.length == 0) { done(util.format("Cannot find child %s", childId)); return; }
                                        console.log("CHECK THIS");
                                        var newTags = self._combineTags(node.tags, addTags, removeTags);
                                        var newTagsString = newTags.join(",");
                                        console.log(JSON.stringify(childTags));
                                        console.log("CK " + newTagsString);
                                        if (childTags.hasOwnProperty(newTagsString)) { nextChild(); }
                                        else
                                        {                                            
                                            console.log(newTagsString);
                                            var childNode = childNodes[0];
                                            if (newTagsString === childNode.tags.join(","))
                                            {
                                                childTags[newTagsString] = 0;
                                                childNode.data = taskData;
                                                childNode.dirty = markDirty;
                                                console.log("DUDOIUDIOUIODUIJDKJD");
                                                self.db.update({_id: childNode._id}, childNode, {upsert:true, safe:true}, function(err) {
                                                    console.log(err); console.log("si929929292");
                                                    nextChild();
                                                    //done();
                                                    //return;
                                                });
                                            }
                                            else
                                            { console.log("NOT THIS");
                                                nextChild();
                                            }
                                        }
                                    });
                                },
                                function (err) {

                                    if (err)
                                    {
                                        next(err);
                                    }
                                    else
                                    {
                                        console.log("ADDING NEW - CHILD VERSION");
                                        var newTags = self._combineTags(node.tags, addTags, removeTags);
                                        var newTagsString = newTags.join(",");
                                        console.log(JSON.stringify(childTags));
                                        console.log("CK " + newTagsString);
                                        console.log(childTags.hasOwnProperty(newTagsString));
                                        if (childTags.hasOwnProperty(newTagsString)) { next(); }
                                        else
                                        {
                                            childTags[newTagsString] = 0;
                                            console.log(newTagsString);
                                            var childNode = {_id: new ObjectID(), 
                                                searchTags: searchTags, 
                                                tags: newTags, 
                                                dirty: markDirty,
                                                status: "",
                                                parent: [ node._id ],
                                                child: [],
                                                data: taskData };
                                            console.log("UPDATE111");
                                            self.db.update({_id: childNode._id}, childNode, {upsert:true, safe:true}, function(err) {
                                                console.log("UPDATING1111");
                                                if (err) { done(err); return; }
                                                console.log(childNode._id);
                                                node.child.push(childNode._id);
                                                self.db.update({_id: node._id}, node, {upsert:true, safe:true}, function (err) {
                                                    next();
                                                });
                                            });
                                        }                                      
                                    }
                                }
                            );
                        }
                        else
                        {
                            console.log("ADDING NEW");
                            var newTags = self._combineTags(node.tags, addTags, removeTags);
                            console.log(newTags.join(","));
                            var childNode = {_id: new ObjectID(), 
                                searchTags: searchTags, 
                                tags: newTags, 
                                dirty: markDirty,
                                status: "",
                                parent: [ node._id ],
                                child: [],
                                data: taskData };
                            console.log("UPDATE");
                            self.db.update({_id: childNode._id}, childNode, {upsert:true, safe:true}, function(err) {
                                console.log("UPDATING");
                                if (err) { done(err); return; }
                                console.log(childNode._id);
                                node.child.push(childNode._id);
                                self.db.update({_id: node._id}, node, {upsert:true, safe:true}, function (err) {
                                    next();
                                });
                            });
                        }
                    },
                    function (err) {
                        console.log("DONE HERE DONE HERE DONE HERE");
                        done(err);
                    }
                );
            }
            else
            {
                console.log("DONE NOTHING NOTHING NOTHING");
                done();
            }
        });
    }
};

/*
persist.find(this.request.find, this.request.limit).toArray(function(err, docs) {



    console.log(JSON.stringify(taskData));
    var self = this;
    var refCounter = new RefCounter(callback);

    if (searchTags == null || searchTags.length == 0) //no parent
    {
        var tags = [];        
        for (var tagIndex in addTags.sort())
        {
            tags.push('tag:*' + addTags[tagIndex] + '* ');
        }

        var query = "start nodes=node:node_auto_index('" + tags.join(" AND ") + "') return nodes;";
        self.neoClient.cypherQuery(query, function(err, existingNodes) {
            if (existingNodes != null && existingNodes.data.length > 0)
            {
                var existingNode = existingNodes.data[0];
                existingNode.data.dirty = String(markDirty);
                console.log("EXISTING: " + JSON.stringify(existingNode.data));
                self.neoClient.updateNode(existingNode.id, existingNode.data, function(err, node) {
                    if(err) throw err;
                    if (markDirty) { self._markDirty(existingNode, refCounter); }
                    else { callback(); }
                });
            }
            else
            {
                var key = uuid.v1();

                var createNode = function (key, markDirty, addTags, callback) { return function (err, data) {

                    //NB!! Query must be space rather than empty string or Neo4j errors silently.
                    var nodeInfo = {'dirty':markDirty, 'tag':addTags.sort(), 'key':key, 'query':' '};

                    var callbackFromNode = function (callback) { return function(err, node) {
                        if (err) throw err;
                        callback();
                    };};

                    self.neoClient.insertNode(nodeInfo, callbackFromNode(callback));
                };};

                this.redisClient.set("task:" + key, JSON.stringify(taskData), createNode(key, markDirty, addTags, callback));
            }
        }.bind(this));
    }
    else //search for matching nodes
    {
        var tags = [];
        
        for (var tagIndex in searchTags.sort())
        {
            tags.push('tag:*' + searchTags[tagIndex] + '* ');
        }

        var query = "start nodes=node:node_auto_index('" + tags.join(" AND ") + "') return nodes;";
        
        var findNodes = function (query, addTags, removeTags, refCounter) { return function (err, result) {

            if(err) throw err;

            for (index in result.data)
            {
                refCounter.start();
                var task = result.data[index];
                var newTags = self._combineTags(task.data.tag, addTags, removeTags);
                var findExistingChildren = "start a=node(" + task.id + ") match a<-[DEPENDS_ON]-b return b;";

                var findChildren = function (task, newTags, findExistingChildren, refCounter) { return function (err, parentData) {
                    if (err) throw err;

                    var processChildren = function (task, newTags, refCounter) { return function (err, existingChildren) {
                        if(err) throw err;

                        //DEAL WITH THE DAMN CYPHER QUERY WEIRDNESS --------------------------------
                        var taskTags = (typeof task.data.tag == "string") ? JSON.parse(task.data.tag) : task.data.tag;
                        for (searchIndex in searchTags)
                        {
                            var found = false;
                            for (tagIndex in taskTags)
                            {
                                if (taskTags[tagIndex] == searchTags[searchIndex])
                                {
                                    found = true;
                                    break;
                                }
                            }

                            if (!found)
                            {
                                //console.log("--------BAD TASK------");
                                //console.log(task.data);
                                refCounter.end();
                                return;
                            }
                        }
                        //--------------------------------------------------------------------------

                        var nodeExists = false;
                        console.log("!!!!!-------!!!!!!!--------!!!!!!!!");
                        console.log(existingChildren.data.length);
                        //console.log(task.data);
                        for (existingIndex in existingChildren.data) 
                        {
                            var existingChild = existingChildren.data[existingIndex];
                            var existingTags = (typeof existingChild.data.tag == "string") ? JSON.parse(existingChild.data.tag) : existingChild.data.tag;
                            //console.log(existingChild.data.query);
                            //console.log(query);
                            //console.log(existingTags.join(","));
                            //console.log(newTags.join(","));
                            //console.log((existingChild.data.query == query));
                            //console.log((existingTags.join(",") == newTags.join(",")));
                            if (existingChild.data.query == query && existingTags.join(",") == newTags.join(","))
                            {
                                console.log("UUUUUUUUUPPPPPPPPDDDDDDDDDAAAAAAAAAAATEEEEEEEEEEEEEEE");
                                existingChild.data.dirty = String(markDirty);
                                if (markDirty) { self._markDirty(existingChild, refCounter); }

                                var doneUpdate = function (refCounter) { return function (err, node) {
                                    if (err) throw err;
                                    refCounter.end();
                                };};

                                self.neoClient.updateNode(existingChild.id, existingChild.data, doneUpdate(refCounter));
                                nodeExists = true;
                                break;
                            }
                        }

                        if (!nodeExists)
                        {
                            console.log("NNNNNNNNNNEEEEEEEEEEEEEEEEEEWWWWWWWWWWWWWWWWWW");
                            var key = uuid.v1();

                            var createNode = function (key, markDirty, newTags, query, refCounter, task) { return function (err, data) {
                                if (err) throw err;

                                var insertRelationship = function (markDirty, refCounter, task) { return function (err, newNode) {
                                    if (err) throw err;

                                    var markChildren = function (markDirty, newNode, refCounter) { return function (err, relation) {
                                        if (err) throw err;
                                        if (markDirty) { self._markDirty(newNode, refCounter); }
                                        refCounter.end();
                                    };};

                                    self.neoClient.insertRelationship(newNode.id, task.id, 'DEPENDS_ON', {}, markChildren(markDirty, newNode, refCounter));
                                };};

                                self.neoClient.insertNode({dirty: markDirty, tag: newTags, key: key, query: query }, insertRelationship(markDirty, refCounter, task));
                            };};

                            self.redisClient.set("task:" + key, JSON.stringify(taskData), createNode(key, markDirty, newTags, query, refCounter, task));
                        }
                    };};

                    self.neoClient.cypherQuery(findExistingChildren, processChildren(task, newTags, refCounter));
                };};

                self.redisClient.get("task:" + task.data.key, findChildren(task, newTags, findExistingChildren, refCounter));
            }

        };};

        self.neoClient.cypherQuery(query, findNodes(query, addTags, removeTags, refCounter));
    }
};



Zoot.prototype.findTasks = function (searchTags, callback)
{
    var self = this;
    var tags = [];
    for (var tagIndex in searchTags.sort())
    {
        tags.push('tag:*' + searchTags[tagIndex] + '* ');
    }
    
    var findTags = "start n=node:node_auto_index('" + tags.join(" AND ") + "') return n;";
    
    var processResult = function (searchTags, callback) { return function(err, result) {
    
        if (err) throw err;
        
        var foundNodes = [];
        
        for (resultIndex in result.data)
        {
            var node = result.data[resultIndex].data;
            var nodeTags = (typeof node.tag == "string") ? JSON.parse(node.tag) : node.tag;
            
            var add = true;
            for (searchIndex in searchTags)
            {
                var found = false;
                for (tagIndex in nodeTags)
                {
                    if (nodeTags[tagIndex] == searchTags[searchIndex])
                    {
                        found = true;
                        break;
                    }                   
                }
                
                if (!found)
                {
                    add = false;
                    break;
                }
            }
            node.tag = nodeTags;
            foundNodes.push(node);
        }
        
        callback(foundNodes);
    
    };};
    
    self.neoClient.cypherQuery(findTags, processResult(searchTags, callback));
};



Zoot.prototype.getTask = function (searchTags, callback)
{
    console.log("getTask");
    var self = this;
    var tags = [];

    for (var tagIndex in searchTags.sort())
    {
        tags.push('tag:*' + searchTags[tagIndex] + '* ');
    }

    var findDirtyRoot = "start a=node:node_auto_index('dirty: true AND " + tags.join(" AND ") + "') match a-[r?:DEPENDS_ON]->b WHERE r is null return a as child;";
    
    console.log(findDirtyRoot);
    self.neoClient.cypherQuery(findDirtyRoot, function(err, result) {

        if (err) throw err;

        var tryLock = function (index, nodes, callback, exitOnNone, childParent) {

            console.log("tryLock");

            if (index < nodes.length)
            {
                var thisNode = {};
                if (childParent)
                {
                    thisNode.parent = nodes[index]["parent"]._data.data;
                    thisNode.child = nodes[index]["child"]._data.data;
                    thisNode.childId = nodes[index]["childId"];
                }
                else
                {
                    thisNode.parent = null;
                    thisNode.child = nodes[index].data;
                    thisNode.childId = nodes[index].id;
                }

                self.redisClient.setnx("queue:" + thisNode.child.key , thisNode, function(err, reply) {
                    if (reply == 1)
                    {
                        self.redisClient.get("task:" + thisNode.child.key, function (err, data) {
                            if (err) throw err;

                            thisNode.childData = JSON.parse(data);

                            if (thisNode.parent == null)
                            {
                                callback(thisNode);
                            }
                            else
                            {
                                self.redisClient.get("task:" + thisNode.parent.key, function (err, data) {
                                    if (err) throw err;
                                    console.log(data);
                                    thisNode.parentData = JSON.parse(data);
                                    console.log("CALLBACK");
                                    callback(thisNode);
                                });
                            }
                        });
                    }
                    else
                    {
                        tryLock(index+1, nodes, callback, false, childParent);
                    }
                });
            }
            else
            {
                console.log("nothing found");
                if (exitOnNone)
                {
                    callback(null);
                }
                else
                {
                    console.log("keep looking");
                    var findDirtyOneLevel = "start a=node:node_auto_index('dirty: true AND " + tags.join(" AND ") +
                        "'), b=node:node_auto_index('dirty: false') match a-[DEPENDS_ON*1..1]->b return a as child, ID(a) as childId, b as parent;";
                    
                    console.log(findDirtyOneLevel);
                    self.neoClient2.query(findDirtyOneLevel, {}, function(err, result) {   
                        if (result)
                        {           
                            console.log(result);
                            console.log("try this");
                            tryLock(0, result, callback, true, true);
                        }
                        else
                        {
                            console.log("nothing");
                            callback(null);
                        }
                    });
                }
            }            
        };

        tryLock(0, result.data, callback, false, false);
    });
};



Zoot.prototype.releaseTask = function (task, complete, callback)
{
    console.log("releaseTask");
    console.log(complete);
    var self = this;
    if (task == null) {
        console.log("ERROR: releasing null task");
         throw { name: "Argument Exception", message: "Attempted to release null task" };
    }
    
    if (complete)
    {
        console.log("task complete");
        task.child.dirty = 'false';
        console.log(task.childId);
        console.log(JSON.stringify(task.child));
        var that = this;
        that.ctx = { task: task, callback: callback };

        this.neoClient2.query('start n=node({id}) set n.dirty="false"', { id: task.childId }, function (err, results)
        { 
                console.log("SAVED");
                console.log(err);
                if (err) throw err;
                console.log(results);
                console.log(task.child.key);
                self.redisClient.del("queue:" + task.child.key, function(err, val) {
                    console.log("DELETED");
                    console.log(err);
                    if(err) throw err;
                    console.log("calling back..");
                    that.ctx.callback();
                });
        });

    }
    else
    {
        console.log("not complete");
        console.log(task.child.key);
        self.redisClient.del("queue:" + task.child.key, function(err, val) {
            console.log("deleted");
            console.log(err);
            if (err) throw err;
            console.log("calling back");
            callback();
        });
    }
};


Zoot.prototype._combineTags = function (existingTags, addTags, removeTags)
{
    var tags = [];
    if (typeof existingTags === 'string') existingTags = JSON.parse(existingTags);
    if (typeof addTags === 'string') addTags = JSON.parse(addTags);
    if (typeof removeTags === 'string') removeTags = JSON.parse(removeTags);

    for (tagIndex in existingTags)
    {
        var tag = existingTags[tagIndex];
        if (removeTags.indexOf(tag) < 0)
        {
            tags.push(tag);
        }
    }
    
    for (tagIndex in addTags)
    {
        tags.push(addTags[tagIndex]);
    }

    return tags.sort();
};



Zoot.prototype._markDirty = function (parentNode, refCounter)
{
    var self = this;
    var query = "start a=node(" + parentNode.id + ") match a<-[DEPENDS_ON*1..1000]-b return b;";
    refCounter.start();

    self.neoClient.cypherQuery(query, function(err, children) {
        for (childIndex in children.data)
        {
            var child = children.data[childIndex];
            refCounter.start();
            child.data.dirty = 'true';
            self.neoClient.updateNode(child.id, child.data, function(err, result) {
                if(err) throw err;
                refCounter.end();
            });
        }
        refCounter.end();
    });
};
*/

/**
* Export classes and modules.
*/
module.exports = Z;


