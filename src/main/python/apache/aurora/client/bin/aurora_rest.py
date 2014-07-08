#!/usr/bin/env python
# ----------------------------------------------------------------------
#  REST service exposing API to call Aurora client commands
# ----------------------------------------------------------------------

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from apache.aurora.client.rest import (
    application,
    application_async,
    external_executor,
    internal_executor,
    coroutine_executor,
    mt_executor,
    mp_executor
)

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("executor", default="internal", help="Type of Aurora command executor", type=str)
define("application", default="thread", help="Type of Tornado application object", type=str)
define("parallel", default=4, help="Max number of simultaneous requests", type=int)

def proxy_main():
    """Main function to prepare the Tornado web server to process Aurora REST API calls

    Tornado web server can process requests in one of several ways:

      1. Asynchronously by spawning new process or thread for each requests (that are
         managed by ProcessPool or ThreadPool respectively)
      2. Synchronously by executing requests one at a time and blocking new
         requests until the current one is completed

    Aurora client commands can be executed either by:

      1. Spawning external process to invoke the Aurora command-line client
      2. Calling directly the Aurora client code

    """

    tornado.options.parse_command_line()

    if options.executor == "external":
        client = external_executor.create()
    elif options.executor == "internal":
        client = internal_executor.create()

    if options.application == "coroutine":
        app = application_async.create("alpha", executor=coroutine_executor.create(client))
    elif options.application == "thread":
        executor = mt_executor.create(client, max_workers=options.parallel)
        app = application_async.create("alpha", executor=executor)
    elif options.application == "process":
        executor = mp_executor.create(client, max_procs=options.parallel)
        app = application_async.create("alpha", executor=executor)
    else:
        app = application.create("alpha", executor=client)

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)

    tornado.ioloop.IOLoop.instance().start()
