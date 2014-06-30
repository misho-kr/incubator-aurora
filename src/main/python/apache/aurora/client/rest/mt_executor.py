#!/usr/bin/env python
# ----------------------------------------------------------------------
#  Asynchronous executor for Aurora commands
# ----------------------------------------------------------------------

import logging

from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("tornado.access")

# thread-pool executor ------------------------------------------------

DEFAULT_MAX_THREADS = 4

class ThreadExecutor():
    """Asynchronous Executor that can be used with async Tornado Application object
    """

    def __init__(self, delegate, thread_pool, io_loop):
        logger.info("ThreadExecutor(threads=%s) created" %
            (str(thread_pool._max_workers) if thread_pool._max_workers else "unlimited"))

        self.delegate = delegate
        self.executor = thread_pool
        self.io_loop  = io_loop

    @run_on_executor
    def list_jobs(self, cluster, role):
        logger.info("entered ThreadExecutor::list_jobs")

        return self.delegate.list_jobs(cluster, role)

    @run_on_executor
    def create_job(self, cluster, role, environment, jobname, jobspec):
        logger.info("entered ThreadExecutor::create_job")

        return self.delegate.create_job(cluster, role, environment, jobname, jobspec)

    @run_on_executor
    def update_job(self, cluster, role, environment, jobname, jobspec):
        logger.info("entered ThreadExecutor::update_job")

        return self.delegate.update_job(cluster, role, environment, jobname, jobspec)

    @run_on_executor
    def cancel_update_job(self, cluster, role, environment, jobname, jobspec=None):
        logger.info("entered ThreadExecutor::cancel_update_job")

        return self.delegate.cancel_update_job(cluster, role, environment, jobname, jobspec)

    @run_on_executor
    def restart_job(self, cluster, role, environment, jobname, jobspec=None):
        logger.info("entered ThreadExecutor::restart_job")

        return self.delegate.restart_job(cluster, role, environment, jobname, jobspec)

    @run_on_executor
    def delete_job(self, cluster, role, environment, jobname):
        logger.info("entered ThreadExecutor::delete_job")

        return self.delegate.delete_job(cluster, role, environment, jobname)

# factory --------------------------------------------------------------

def create(executor, thread_pool=None, io_loop=None, max_workers=DEFAULT_MAX_THREADS):
    io_loop     = io_loop or IOLoop.instance()
    thread_pool = thread_pool or ThreadPoolExecutor(max_workers)

    return ThreadExecutor(executor, thread_pool, io_loop)
