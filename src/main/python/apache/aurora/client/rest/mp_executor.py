#!/usr/bin/env python
# ----------------------------------------------------------------------
#  Asynchronous executor for Aurora commands
# ----------------------------------------------------------------------

import logging
from functools import partial, wraps

from tornado.ioloop import IOLoop
from concurrent.futures import ProcessPoolExecutor

logger = logging.getLogger("tornado.access")

# thread-pool executor ------------------------------------------------

DEFAULT_MAX_PROCESSES = 4

def call_by_name(method_name, obj, *args, **kwargs):
    method = getattr(obj, method_name)
    return method(*args, **kwargs)

class ProcessExecutor():
    """Asynchronous Executor that can be used with async Tornado Application object
    """

    def __init__(self, delegate, thread_pool, io_loop):
        logger.info("ProcessExecutor(procs=%s) created" %
            (str(thread_pool._max_workers) if thread_pool._max_workers else "unlimited"))

        self.delegate = delegate
        self.executor = thread_pool
        self.io_loop  = io_loop

    def run_on_executor(self, method_name, obj, *args, **kwargs):
        logger.info("ProcessExecutor schedule method: %s" % method_name)

        return self.executor.submit(call_by_name, method_name, obj, *args, **kwargs)

    delegated_methods = [
        "list_jobs", "create_job", "delete_job"
    ]

    def __getattr__(self, name):
        if name in self.delegated_methods:
            logger.info("ProcessExecutor lookup method: %s" % name)
            return partial(self.run_on_executor, name, self.delegate)
        else:
            raise AttributeError("Instance does not have attribute: %s" % name)

# factory --------------------------------------------------------------

def create(executor, thread_pool=None, io_loop=None, max_procs=DEFAULT_MAX_PROCESSES):
    io_loop     = io_loop or IOLoop.instance()
    thread_pool = thread_pool or ProcessPoolExecutor(max_procs)

    return ProcessExecutor(executor, thread_pool, io_loop)
