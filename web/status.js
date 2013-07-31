
var json2csv = require('json2csv');
var ObjectID = require('mongodb').ObjectID;
var url = require('url');
var fs = require('fs');
var microtime = require('microtime');


module.exports = function (persist, zootClient) {

    return {

        /**
         * Display default task page.
         */
        index: function (req, res) {
            console.log("/status/index");
            res.render('status.ejs', { locals : { title: 'working' } });            
        },
        
        /**
         * Retrieve status info.
         */
        find: function (req, res) {
            console.log("/status/find");
            this.request = JSON.parse(req.body.content);
            this.res = res;            
            persist.find(this.request.find, this.request.fields, this.request.options).toArray(function(err, docs) {
                console.log(docs);
                this.res.send(JSON.stringify(docs));
            }.bind(this));
        }
    }
};

