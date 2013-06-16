#!/usr/bin/env node
'use strict';

var ArgumentParser = require('argparse').ArgumentParser;

var parser = new ArgumentParser({
    version: '2013.06.16',
    addHelp:true,
    description: 'TS Toolkit app'
});

parser.addArgument(
    [ '-g', '--zgraph'],
    { help: 'Zoot graph server eg: http://zoot:7474' }
);

parser.addArgument(
    [ '-r', '--zdata'],
    { help: 'Zoot data host' }
);

parser.addArgument(
    [ '-p', '--zdataport'],
    { help: 'Zoot data host port' }
);

parser.addArgument(
    [ '-m', '--mongo'],
    { help: 'MongoDB host' }
);

parser.addArgument(
    [ '-mp', '--mongoport'],
    { help: 'MongoDB port' }
);

parser.addArgument(
    [ '-d', '--dataserver'],
    { help: 'Data server eg: http://data:3010' }
);

var args = parser.parseArgs();
var express = require('express');
var Zoot = require('zoot');
var mongodb = require('mongodb');
var ObjectID = require('mongodb').ObjectID;
var task = require('./task');
var explorer = require('./explorer');
var redisHost = args.zData;
var redisPort = 6379;
var zootClient = new Zoot(args.zgraph, args.zdata, args.zdataport, function () {});
var server = new mongodb.Server(args.mongo, args.mongoport, {});

// Routes

function verifyAuth (req, res, route)
{
    route();
    /*
    if (!req.headers['user-agent'].match(/Chrome/g))
    {
        res.redirect('/chrome');
    }
    else
    {
        if (!req.session || !req.session.user)
        {
            console.log('USER NOT AUTHD');
            res.redirect('/login');
        }
        else
        {
            route();
        }
    }*/
}

new mongodb.Db('qu', server, {safe:true}).open(function (error, persist) {
    if (error) throw error;

    var app = module.exports = express();

    app.configure(function() {
        app.set('views', __dirname + '/views');
        app.set('view engine', 'ejs');
        app.set('view options', {layout: false});
        app.use(express.bodyParser());
        app.use(express.methodOverride());
        app.use(app.router);
        app.use(express.static(__dirname + '/static'));
        app.use(express.static(__dirname + '/public'));
    });

    var taskDb = new mongodb.Collection(persist, 'task');
    app.get('/task', verifyAuth, task(taskDb, zootClient).index);
    app.get('/explorer', verifyAuth, explorer(taskDb, zootClient).index);
    app.post('/task/find', verifyAuth, task(taskDb, zootClient).find);
    app.post('/task/detail', verifyAuth, task(taskDb, zootClient).detail);
    app.post('/task/save', verifyAuth, task(taskDb, zootClient).save);
    app.post('/task/delete', verifyAuth, task(taskDb, zootClient).delete);
    
    var request = require('request');
    app.get('/getdata', verifyAuth, function (req, res)
    {
        console.log('/getdata');
        var reqQuery = args.dataserver + '/?file=' + encodeURIComponent(req.query["file"]) +
                '&start=' + req.query["start"] + '&end=' + req.query["end"];
        console.log(reqQuery);
        request.get(reqQuery).pipe(res);
        console.log('/getdata done');
    });
 
    // Server
    app.listen(3000, function(){
      console.log("express-bootstrap app running");
    });
});

