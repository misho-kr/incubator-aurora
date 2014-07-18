Aurora REST service
===================

Aurora includes a powerful command-line tool to submit to the scheduler
[all sorts of query and management commands](https://github.com/apache/incubator-aurora/blob/master/docs/client-commands.md).
Users can start, stop and monitor jobs that are handled by the Aurora
Scheduler. This command-line tool requires to build and install the Aurora
client libraries and binaries on the local machine, or to have access
to server that has everything ready set up.

The REST service allows remote access to the Aurora Scheduler without these
prerequisites. Any REST client, or the __curl__ command, can be used to call
the REST API and the results are standard JSON documents.

## Implementation

The REST service is built with the [Tornado framework](http://www.tornadoweb.org/en/stable/index.html). 
The advantages of using Tornado are:

* It is written in Python like the Aurora command-line client
* It offers non-blocking execution of requests that can help the service to
scale up

The Tornado web server accepts requests for the REST API and delegates the
execution to the Aurora client code or command-line tool. The simultaneous
execution of multiple requests is implemented with either threads or external
processes managed with [concurrent.futures](http://pythonhosted.org//futures).

#### Build and Installation

The instructions for building, testing and deploying the Aurora command-line
client apply for the REST service:

* Execute the following command which will produce executable file __dist/aurora_rest.pex__

```
$ ./pants src/main/python/apache/aurora/client/bin:aurora_rest

```

* Run all client tests

```
$ ./pasts src/test/python/apache/aurora/rest/:all
```

* Copy the executable to some apropriate location

```
$ sudo cp dist/aurora_rest.pex /usr/local/bin/aurora_rest
```

#### Start the REST server

The command below will start the Aurora REST service. The paramters that are passed to
the executable will have the following effect:

- The server will listen for requests on port __8888__
- All requests will be executed by __direct calls to the Aurora client code__
- Every request will be handled by __separate thread running in the same process__
- At most __4 threads__ will be spawned to process API calls

```
$ aurora_rest --port=8888 --executor=internal --application=thread --parallel=4
```

## Execution Modes

The REST service can run in one of several execution modes. Some of them 
allow the service to scale up and handle multiple requests simultaneously,
and therefore are expected to be used most of the time. Others are useful
only for troubleshooting problems in the code of the REST service so they
will be used rarely, most likely by developers only.

The recommended mode is __asynchronous execution with multiple threads__
as the example above demonstrated.

All execution modes are categorized into two groups as described below.
This picture illustrates all available execution modes and how they can be
combined to provide the desired service operation.

TBC __add picture here__ TBC

### A. Command execution modes

The defining feature of this group is how requests are handled by the
application code __after__ they were accepted and dispatched by the Tornado
web-handling code.

#### A.1 Aurora API calls

The preferred execution mode to handle requests for the Aurora scheduler
is by directly calling the Aurora client code. In order to enable this
the REST service imports the same Python modules that the Aurora client uses
and simply calls the right methods.

Potential problem with this execution mode is the chance that the Aurora
client code may not be multithread-safe (MT-safe). As the Tornado server
acceptes simultaneous requests and handles them asynchronously, if there
are such issues they may lead to incorrect results or disruption of service.

#### A.2 External command

The alternative, and probably safer but slower, execution mode is when
requests are handled by delegating to an external command to run the
command line tool that the implements
[all sorts of query and management commands](https://github.com/apache/incubator-aurora/blob/master/docs/client-commands.md).
In this mode the Aurora client code is executed by a new process in
single-threaded mode just as the Aurora client command line tool does. 

### B. Request handling modes

The execution modes in this group are different from each other
by how the web requests are handled inside the server -- after the requests
are accepted and before they are delegated to the Aurora client code.

Regardless of the choice of how Aurora commands are actually executed,
the REST service can handle requests synchronously or asynchronousely,
one at a time or in parallel.

#### B.1 Multithreaded mode

Multiple threads managed with [ThreadPool](http://pythonhosted.org//futures/#threadpoolexecutor-objects)
are used to provide simultaneous execution of RESTful calls. 

#### B.2 Multiprocess mode

Similar to the previous mode but, instead of threads, external processes that are
managed with [ProcessPool](http://pythonhosted.org//futures/#processpoolexecutor-objects)
are used to execute the RESTful calls simultaneously.

#### B.3 Function calls

This is the simplest execution mode from code perspective. There is nothing
complicated here -- the Tornado request handler calls directly the code
that handles the execution of Aurora commands. The result is a __synchronous__
processing of RESTful calls that are handled one at a time. The execution
will block for every request and will wait until it is completed, during which
time the service is unavailable to accept and process new requests.

#### B.4 Coroutines

This is an internal execution mode that enables, together with a thread or
process pool, to process RESTful calls *asynchornously*. When this mode is
combined with either multiple threads or processes that makes possible to
process requests in parallel.

## Commands

* [GET /alpha/jobs/{cluster}/{role}](#get-alphajobsclusterrole): List all jobs
* [PUT /alpha/job/{cluster}/{role}/{environment}/{jobname}](#put-alphajobclusterroleenvironmentjobname): Create job
* [PUT /alpha/job/{cluster}/{role}/{environment}/{jobname}/update?shards={X}](#put-alphajobclusterroleenvironmentjobnameupdateshardsx): Update job
* [DELETE /alpha/job/{cluster}/{role}/{environment}/{jobname}/update](#delete-alphajobclusterroleenvironmentjobnameupdate): Cancel update
* [PUT /alpha/job/{cluster}/{role}/{environment}/{jobname}/restart?shards={X}](#put-alphajobclusterroleenvironmentjobnamerestartshardsx): Restart job
* [DELETE /alpha/job/{cluster}/{role}/{environment}/{jobname}?shards={X}](#delete-alphajobclusterroleenvironmentjobnameshardsx): Kill Aurora job
* [GET /alpha/version](#get-alphaversion): Query service version

## Examples

#### `GET` /alpha/jobs/{cluster}/{role}

```
HTTP/1.1 200 OK
Content-Type: application/json
Server: TornadoServer/3.2.1
```
```json
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

#### `PUT` /alpha/job/{cluster}/{role}/{environment}/{jobname}

```bash
$ curl -s -X PUT --data-binary @rhel59_world2.aurora \
  "http://localhost:8888/alpha/jobs/paas-aurora/mkrastev/devel/rhel59_world2" | \
  python -m json.tool
```

**Response:**
```
HTTP/1.1 201 Created
Content-Type: application/json
Server: TornadoServer/3.2.1
```
```json
{
    "count": 1,
    "job": "paas-aurora/mkrastev/devel/rhel59_world2",
    "key": "paas-aurora/mkrastev/devel/rhel59_world2",
    "status": "success"
}
```

#### `PUT` /alpha/job/{cluster}/{role}/{environment}/{jobname}/update?shards={X}

```bash
$ curl -s -X PUT --data-binary @rhel59_world2.aurora \
  "http://localhost:8888/alpha/jobs/paas-aurora/mkrastev/devel/rhel59_world2?shards=1" | \
  python -m json.tool
```

**Response:**
```
HTTP/1.1 202 Accepted
Content-Type: application/json
Server: TornadoServer/3.2.1
```
```json
{
    "count": 1,
    "job": "paas-aurora/mkrastev/devel/rhel59_world2",
    "key": "paas-aurora/mkrastev/devel/rhel59_world2",
    "status": "success"
}
```

#### `DELETE` /alpha/job/{cluster}/{role}/{environment}/{jobname}/update

```
HTTP/1.1 202 Accepted
Content-Type: application/json
Server: TornadoServer/3.2.1
```
```json
{
    "count": 1,
    "job": "paas-aurora/mkrastev/devel/rhel59_world2",
    "key": "paas-aurora/mkrastev/devel/rhel59_world2",
    "status": "success"
}
```

#### `PUT` /alpha/job/{cluster}/{role}/{environment}/{jobname}/restart?shards={X}

```
HTTP/1.1 202 Accepted
Content-Type: application/json
Server: TornadoServer/3.2.1
```
```json
{
    "count": 1,
    "job": "paas-aurora/mkrastev/devel/rhel59_world2",
    "key": "paas-aurora/mkrastev/devel/rhel59_world2",
    "status": "success"
}
```

#### `DELETE` /alpha/job/{cluster}/{role}/{environment}/{jobname}?shards={X}

```bash
$ curl -s -X \
  DELETE "http://localhost:8888/alpha/jobs/paas-aurora/mkrastev/devel/rhel59_world2?shards=2" | \
  python -m json.tool
```

**Response:**
```
HTTP/1.1 200 OK
Content-Type: application/json
Server: TornadoServer/3.2.1
```
````json
{
    "count": 1,
    "job": "paas-aurora/mkrastev/devel/rhel59_world2",
    "key": "paas-aurora/mkrastev/devel/rhel59_world2",
    "status": "success"
}
```

#### `GET` /alpha/version

```
HTTP/1.1 200 OK
Content-Type: application/json
Server: TornadoServer/3.2.1
```
```json
{
    "status": "success",
    "version": "0.1"
}
```