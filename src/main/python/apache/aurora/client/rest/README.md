Aurora REST service
===================

Aurora includes a powerful command line tool to execute
[all sorts of query and management commands](https://github.com/apache/incubator-aurora/blob/master/docs/client-commands.md).
Users can start, stop and monitor jobs that are submitted to the Aurora Scheduler.
It requires to build and install the Aurora client binaries, or to have access
to server that has everything ready set up.

The REST service allows remote access to the Aurora Scheduler without the
prerequisites. Any REST client can be used, or the __curl__ command, and the 
results are standard JSON documents.

## Implementation

The REST service is built with the [Tornado framework](http://www.tornadoweb.org/en/stable/index.html). 
The advantages of using Tornado are that it is written in Python like the
Aurora client codebase and enables non-blocking execution that can allow the
service to scale up.

The Tornado web server accepts requests for the REST API and delegates the
execution to the Aurora client. The asynchronous execution is carried out with
a thread or external process handled by [concurrent.futures](http://pythonhosted.org//futures).

## Execution Modes

The REST service can run in one of several execution modes. Some of them 
allow the service to scale up and handle multiple requests simultaneously,
and therefore are expected to be used most of the time. Others are useful
only for troubleshooting problems in the code of the REST service so they
will be used rarely and exclusively by developers.

The recommended mode is __asynchronous execution with multiple threads__.

All execution modes are categorized into two groups as described below.
This picture illustrates all available execution modes and how they can be
combined to provide the desired service operation.

TBC __add picture here__ TBC

### A. Command execution modes

The defining feature of this group is how requests are handled by the
application code __after__ being accepted and dispathed by the Tornado
web-handling code.

### A.1 Aurora API calls

The preferred execution mode to handle requests for the Aurora scheduler
is by directly calling the Aurora client code. In order to enable this
the REST service imports the same Python modules that the Aurora client uses
and just calls the right methods.

Potential problem with this execution mode is the chance that the Aurora
client code may not be multithread-safe (MT-safe). As the Tornado server
acceptes simultaneous requests and handles them asynchronously, if there
are such issues they may lead to incorrect results or disruption of service.

### A.2 External command

The alternative, and probably safer but slower, execution mode is when
requests are handled by delegating to an external command, that is the
command line tool that the implements
[all sorts of query and management commands](https://github.com/apache/incubator-aurora/blob/master/docs/client-commands.md).
In this mode the Aurora client code is executed by new processe in
single-threaded mode just as the Aurora client command line tool does. 

### B. Request handling modes

The execution modes in this group are different from each other
by how the web requests are handled inside the server, after the requests
are accepted and before they are delegated to the Aurora client code.

Regardless of the choice of how Aurora commands are actually executed,
the REST service can handle requests synchronously or asynchronousely,
one at a time or in parallel.

### B.1 Multithreaded mode

Multiple threads managed with [ThreadPool](http://pythonhosted.org//futures/#threadpoolexecutor-objects)
are used to implement the simultaneous execution of RESTful calls. 

### B.2 Multiprocess mode

Similar to the previous mode but, instead of threads, external processes
managed with [ProcessPool](http://pythonhosted.org//futures/#processpoolexecutor-objects)
are used to execute the RESTful calls simultaneously.

### B.3 Function calls

This is the simplest from code perspective exeuction mode. There is nothing
complicated here -- the Tornado request handler calls directly the code
that handles the exection of Aurora commands. The result is __synchronous__
processing of RESTful calls one at a time. It will block for every request
and will wait until it is completed, during which time it is unavailable
to accept and process new requests.

### B.4 Coroutines

Internal execution mode that enables, together with a thread or process pool,
to process RESTful calls asynchornously. When this mode is combined with
either multiple threads or processes that makes possible to process
requests in parallel.

## Commands

* Create job
* GET /alpha/jobs/<cluster>/<role>

List all jobs.

```
{
    "count": 3,
    "jobs": {
        "1": "paas-aurora/mkrastev/devel/rhel59_world2",
        "2": "paas-aurora/mkrastev/devel/kraken_app",
        "3": "paas-aurora/mkrastev/devel/rhel59_world"
    },
    "key": "paas-aurora/mkrastev",
    "status": "success"
}
```

* Update job
* Cancel update
* Restart job
* DELETE /alpha/

Kill Aurora job.

* GET /alpha/version

Query REST service version.

```
$ curl -s http://localhost:8888/alpha/version | python -m json.tool

{
    "status": "success",
    "version": "0.1"
}
```
