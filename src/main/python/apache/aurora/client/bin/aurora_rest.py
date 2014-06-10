#!/usr/bin/env python
# ----------------------------------------------------------------------
#  Simple server exposing REST interface to Aurora client commands
# ----------------------------------------------------------------------

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from apache.aurora.client.rest import (
    application,
    application_coroutine,
    external_executor,
    internal_executor
)

from tornado.options import define, options

define("port", default=8000, help="run on the given port", type=int)
define("executor", default="external", help="Type of Aurora command executor", type=str)
define("application", default="plain", help="Type of Tornado application object", type=str)

def proxy_main():
    tornado.options.parse_command_line()

    if options.executor == "external":
        client = external_executor.create()
    elif options.executor == "internal":
        client = internal_executor.create()

    if options.application == "coroutine":
        app = application_coroutine.create("alpha", executor=client)
    else:
        app = application.create("alpha", executor=client)

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)

    tornado.ioloop.IOLoop.instance().start()
