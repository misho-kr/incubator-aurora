#!/usr/bin/env python
# ----------------------------------------------------------------------
#  Simple executor for Aurora commands
# ----------------------------------------------------------------------

import logging

from tornado.concurrent import return_future

logger = logging.getLogger("tornado.access")

# coroutine executor --------------------------------------------------

class CoroutineExecutor():
    """Simple executor that can be used with async Tornado Application object

    Implementation of the Decorator design pattern. It makes possible to
    pass executor objects that run in synchronous mode to Tornado Handlers
    that use coroutines and futures to implement asynchronous execution of
    requests.

    The executor will delegate each command to another executor and then
    invoke the callback. This a test class to experiment with Tornado async
    operations. The execution of Aurora commands is still synchronouse.
    """

    def __init__(self, executor):
        logger.info("aurora -- coroutine executor created")

        self.executor = executor

    @return_future
    def list_jobs(self, cluster, role, callback=None):
        logger.info("entered CoroutineExecutor::list_jobs")

        result = self.executor.list_jobs(cluster, role)
        callback(result)

    @return_future
    def create_job(self, cluster, role, environment, jobname, jobspec, callback=None):
        logger.info("entered CoroutineExecutor::create_job")

        result = self.executor.create_job(cluster, role, environment, jobname, jobspec)
        callback(result)

    @return_future
    def delete_job(self, cluster, role, environment, jobname, callback=None):
        logger.info("entered CoroutineExecutor::delete_job")

        result = self.executor.delete_job(cluster, role, environment, jobname)
        callback(result)

# factory --------------------------------------------------------------

def create(executor=None):
    return CoroutineExecutor(executor=executor)
