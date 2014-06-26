#!/usr/bin/env python
# ----------------------------------------------------------------------
#  Tornado handlers implementing REST interface to Aurora client commands
# ----------------------------------------------------------------------

import logging
import httplib
import tornado.web

logger = logging.getLogger("tornado.access")

# basic handlers -------------------------------------------------------

class VersionHandler(tornado.web.RequestHandler):
    def get(self):
        self.write({
            "status":       "success",
            "version":      "0.1"
        })

# aurora interface handlers --------------------------------------------

class ListJobsHandler(tornado.web.RequestHandler):
    def get(self, cluster, role):
        logger.info("entered ListJobsHandler::GET")

        (jobkey, jobs, errors) = self.application.get_executor().list_jobs(
                                                            cluster, role)
        if errors is None:
            logger.info("no errors")
            # no jobs were found to termminate, not an error
            if len(jobs) == 0:
                logger.info("nothing found")
                self.set_status(httplib.NOT_FOUND)
            self.write({
                "status":       "success",
                "key":          jobkey,
                "count":        len(jobs),
                "jobs":         dict(enumerate(jobs, start=1))
            })

        else:
            logger.info("internal error")
            self.set_status(httplib.INTERNAL_SERVER_ERROR)
            self.write({
                "status":       "failure",
                "key":          jobkey,
                "errors":       errors,
                "count":        0,
                "jobs":         {}
            })

class JobHandler(tornado.web.RequestHandler):
    def put(self, cluster, role, environment, jobname):
        logger.info("entered JobHandler::PUT")

        (jobkey, errors) = self.application.get_executor().create_job(
                                    cluster, role, environment, jobname,
                                    self.request.body)
        if errors is None:
            self.set_status(httplib.CREATED)
            self.write({
                "status":       "success",
                "key":          jobkey,
                "count":        1,
                "job":          jobkey
            })

        else:
            self.set_status(httplib.INTERNAL_SERVER_ERROR)
            self.write({
                "status":       "failure",
                "key":          jobkey,
                "count":        0,
                "job":          [],
                "errors":       errors
            })

    def delete(self, cluster, role, environment, jobname):
        logger.info("entered JobHandler::DELETE")

        jobspec = None
        if self.request.body is not None and len(self.request.body) > 0:
            jobspec = self.request.body

        (jobkey, jobs, errors) = self.application.get_executor().delete_job(
                                    cluster, role, environment, jobname, jobspec)
        if errors is None:
            # no jobs were found to termminate, not an error
            if len(jobs) == 0:
                self.set_status(httplib.NOT_FOUND)
            self.write({
                "status":       "success",
                "key":          jobkey,
                "count":        len(jobs),
                "job":          jobs[0] if len(jobs) > 0 else ""
            })

        else:
            self.set_status(httplib.INTERNAL_SERVER_ERROR)
            self.write({
                "status":       "failure",
                "key":          jobkey,
                "count":        0,
                "job":          [],
                "errors":       errors
            })

class UpdateJobHandler(tornado.web.RequestHandler):
    def put(self, cluster, role, environment, jobname):
        logger.info("entered UpdateJobHandler::PUT")

        (jobkey, errors) = self.application.get_executor().update_job(
                                    cluster, role, environment, jobname,
                                    self.request.body)
        if errors is None:
            self.set_status(httplib.ACCEPTED)
            self.write({
                "status":       "success",
                "key":          jobkey,
                "count":        1,
                "job":          jobkey
            })

        else:
            self.set_status(httplib.INTERNAL_SERVER_ERROR)
            self.write({
                "status":       "failure",
                "key":          jobkey,
                "count":        0,
                "job":          [],
                "errors":       errors
            })

    def delete(self, cluster, role, environment, jobname):
        logger.info("entered UpdateJobHandler::DELETE")

        jobspec = None
        if self.request.body is not None and len(self.request.body) > 0:
            jobspec = self.request.body

        (jobkey, errors) = self.application.get_executor().cancel_update_job(
                                    cluster, role, environment, jobname, jobspec)
        if errors is None:
            self.set_status(httplib.ACCEPTED)
            self.write({
                "status":       "success",
                "key":          jobkey,
                "count":        1,
                "job":          jobkey
            })

        else:
            self.set_status(httplib.INTERNAL_SERVER_ERROR)
            self.write({
                "status":       "failure",
                "key":          jobkey,
                "count":        0,
                "job":          [],
                "errors":       errors
            })

class RestartJobHandler(tornado.web.RequestHandler):
    def put(self, cluster, role, environment, jobname):
        logger.info("entered RestartJobHandler::PUT")
#        logger.info("cluster = %s" % cluster)
#        logger.info("role = %s" % role)
#        logger.info("environment = %s" % environment)
#        logger.info("jobname = %s" % jobname)

        jobspec = None
        if self.request.body is not None and len(self.request.body) > 0:
            jobspec = self.request.body

        (jobkey, errors) = self.application.get_executor().restart_job(
                                    cluster, role, environment, jobname, jobspec)
        if errors is None:
            self.set_status(httplib.ACCEPTED)
            self.write({
                "status":       "success",
                "key":          jobkey,
                "count":        1,
                "job":          jobkey
            })

        else:
            self.set_status(httplib.INTERNAL_SERVER_ERROR)
            self.write({
                "status":       "failure",
                "key":          jobkey,
                "count":        0,
                "job":          [],
                "errors":       errors
            })

# application ----------------------------------------------------------

class AuroraApplicaiton(tornado.web.Application):
    def __init__(self, prefix, executor=None, **settings):
        """Tornado application implementing REST service points"""

        logging.info("aurora -- application created")

        self.url_prefix = prefix.lstrip('/').rstrip('/')
        self.executor   = executor

        settings["debug"] = True
        handlers = self.make_app_handlers(self.url_prefix, [
            (r"/version",                           VersionHandler),
            (r"/jobs/(.+)/(.+)/(.+)/(.+)/restart",  RestartJobHandler),
            (r"/jobs/(.+)/(.+)/(.+)/(.+)/update",   UpdateJobHandler),
            (r"/jobs/(.+)/(.+)/(.+)/(.+)",          JobHandler),
            (r"/jobs/(.+)/(.+)",                    ListJobsHandler)
        ])

        super(AuroraApplicaiton, self).__init__(handlers, **settings)

    def get_executor(self): return self.executor

    def make_app_handlers(self, url_prefix, handlers):
        return [ ("/" + url_prefix + "/" + url.lstrip('/'), handler)
                    for url, handler in handlers ]

# factory --------------------------------------------------------------

def create(url_prefix, executor=None, **settings):
    return AuroraApplicaiton(url_prefix, executor=executor, **settings)
