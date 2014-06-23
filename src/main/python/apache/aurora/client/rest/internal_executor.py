#!/usr/bin/env python
# ----------------------------------------------------------------------
#  Simple interface to execute Aurora client commands
# ----------------------------------------------------------------------

import tempfile
import logging

from apache.aurora.common.aurora_job_key import AuroraJobKey
from apache.aurora.client.commands.core import get_job_config

from apache.aurora.client.factory import make_client
from gen.apache.aurora.api.ttypes import ResponseCode

logger = logging.getLogger("tornado.application")

# basic handlers -------------------------------------------------------

def caller_list_jobs(obj, cluster, role):
    return obj.list_jobs(cluster, role)

class AuroraClient():
    def __init__(self):
        logger.info("aurora -- internal executor created")

    def make_job_key(self, cluster, role, environment=None, jobname=None):
        if environment is None:
            return cluster + "/" + role
        else:
            return cluster + "/" + role + "/" + environment + "/" + jobname

    def response_string(self, resp):
        return('Response from scheduler: %s (message: %s)'
            % (ResponseCode._VALUES_TO_NAMES[resp.responseCode], resp.messageDEPRECATED))
                                                    # yes, this is the actual attribute name

    def list_jobs(self, cluster, role):
        """Method to execute [ aurora list_jobs cluster/role command ]"""

        def job_string(cluster, job):
            return '{0}/{1.key.role}/{1.key.environment}/{1.key.name}'.format(cluster, job)

        jobkey = self.make_job_key(cluster, role)
        logger.info("request to list jobs = %s" % jobkey)

        api = make_client(cluster)
        resp = api.get_jobs(role)
        if resp.responseCode != ResponseCode.OK:
            logger.warning("Failed to list Aurora jobs")
            responseStr = self.response_string(resp)
            logger.warning(responseStr)
            return(jobkey, [], ["Failed to list Aurora jobs", responseStr])

        jobs = [ job_string(cluster, job) for job in resp.result.getJobsResult.configs ]
        if len(jobs) == 0:
            logger.info("no jobs found for key = %s" % jobkey)
        for s in jobs:
            logger.info("> %s" % s )

        return(jobkey, jobs, None)

    def create_job(self, cluster, role, environment, jobname, jobspec):
        """Method to create aurora job from job file and job id"""

        job_key = AuroraJobKey.from_path(
                    self.make_job_key(cluster, role, environment, jobname))
        logger.info("request to create job = %s", job_key.to_path())

        logger.info("  job spec:")
        lineno = 1
        for l in jobspec.splitlines():
            logger.info("  %3d: %s" % (lineno, l))
            lineno += 1

        config = None
        with tempfile.NamedTemporaryFile(suffix=".aurora") as config_file:
            config_file.write(jobspec)
            config_file.flush()
            try:
                options = { 'json': False, 'bindings': () }
                config = get_job_config(job_key.to_path(), config_file.name, options)
            except ValueError as e:
                logger.exception("Failed to create Aurora job")
                logger.warning("----------------------------------------")
                return(job_key.to_path(), ["Failed to create Aurora job", str(e)])

        api = make_client(job_key.cluster)
        resp = api.create_job(config)
        if resp.responseCode != ResponseCode.OK:
            logger.warning("aurora -- create job failed")
            responseStr = self.response_string(resp)
            logger.warning(responseStr)
            return(job_key.to_path(), ["Error reported by aurora client:", responseStr])

        logger.info("aurora -- create job successful")
        return(job_key.to_path(), None)

    def update_job(self, cluster, role, environment, jobname, jobspec):
        """Method to update aurora job from job file and job id"""

        job_key = AuroraJobKey.from_path(
                    self.make_job_key(cluster, role, environment, jobname))
        logger.info("request to update job = %s", job_key.to_path())

        logger.info("  job spec:")
        lineno = 1
        for l in jobspec.splitlines():
            logger.info("  %3d: %s" % (lineno, l))
            lineno += 1

        config = None
        with tempfile.NamedTemporaryFile(suffix=".aurora") as config_file:
            config_file.write(jobspec)
            config_file.flush()
            try:
                options = { 'json': False, 'bindings': () }
                config = get_job_config(job_key.to_path(), config_file.name, options)
            except ValueError as e:
                logger.exception("Failed to update Aurora job")
                logger.warning("----------------------------------------")
                return(job_key.to_path(), ["Failed to update Aurora job", str(e)])

        api = make_client(cluster)
        resp = api.update_job(config)
        if resp.responseCode != ResponseCode.OK:
            logger.warning("aurora -- update job failed")
            responseStr = self.response_string(resp)
            logger.warning(responseStr)
            return(job_key.to_path(), ["Error reported by aurora client:", responseStr])

        logger.info("aurora -- update job successful")
        return(job_key.to_path(), None)

    def cancel_update_job(self, cluster, role, environment, jobname):
        """Method to cancel an update of aurora job by job id"""

        job_key = AuroraJobKey.from_path(
                    self.make_job_key(cluster, role, environment, jobname))
        logger.info("request to cancel update of job = %s", job_key.to_path())

        api = make_client(cluster)
        resp = api.cancel_job(job_key, options=None)
        if resp.responseCode != ResponseCode.OK:
            logger.warning("aurora -- cancel the update of job failed")
            responseStr = self.response_string(resp)
            logger.warning(responseStr)
            return(job_key.to_path(), ["Error reported by aurora client:", responseStr])

        logger.info("aurora -- cancel of update job successful")
        return(job_key.to_path(), None)

    def delete_job(self, cluster, role, environment, jobname):
        """Method to delete aurora job by job id"""

        logger.info("aurora -- delete job invoked")

        job_key = AuroraJobKey.from_path(
                    self.make_job_key(cluster, role, environment, jobname))
        logger.info("request to delete job = %s", job_key.to_path())

        api = make_client(job_key.cluster)
        resp = api.kill_job(job_key, None)
        if resp.responseCode != ResponseCode.OK:
            logger.warning("aurora -- kill job failed")
            responseStr = self.response_string(resp)
            logger.warning(responseStr)
            return(job_key.to_path(), [], ["Error reported by aurora client:", responseStr])

        logger.info("aurora -- kill job successful")
        return(job_key.to_path(), [job_key.to_path()], None)

# factory --------------------------------------------------------------

def create():
    return AuroraClient()
