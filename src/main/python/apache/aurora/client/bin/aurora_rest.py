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
    external_executor
)

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

def proxy_main():
    tornado.options.parse_command_line()

    client = external_executor.create()
    app = application.create("alpha", executor=client)

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)

    tornado.ioloop.IOLoop.instance().start()
