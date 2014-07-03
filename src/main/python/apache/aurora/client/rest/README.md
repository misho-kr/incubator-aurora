REST service for Aurora client commands
==========================================

Aurora provides a powerful command line tool to execute
[query and management commands](https://github.com/apache/incubator-aurora/blob/master/docs/client-commands.md).
This server implements RESTful API to allow remote access to the same capabilities.

## Implementation

The REST service is built with the [Tornado framework](http://www.tornadoweb.org/en/stable/index.html). 

## Execution Mode

The REST service can be started in one of several execution modes:

* synchronous -- blocking mode, requests are executed one at a time
* multi-processing -- asynchronous mode, every request is handled by new process
* multi-threading -- asynchronous mode, every request is handled by new thread in the same process that runs Tornado

## Supported commands

* Create job
* List jobs
* Update job
* Cancel update
* Restart job
* Kill job

TBC and expanded ...
