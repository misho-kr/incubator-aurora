#!/usr/bin/env python
# ----------------------------------------------------------------------
#  Simple interface to execute Aurora client commands
# ----------------------------------------------------------------------

import logging
import tempfile
import subprocess

logger = logging.getLogger("tornado.application")

DEFAULT_AURORA_CMD      = "/home/mkrastev/projects/Mesos/incubator-aurora.git/dist/aurora_client.pex"
AURORA_SUCCESS_RESPONSE = r"Response from scheduler: OK"

# basic handlers -------------------------------------------------------

class AuroraClient():
    def __init__(self, aurora_cmd):
        logging.info("aurora -- client created")

        self.aurora_cmd = aurora_cmd

    def make_job_key(self, cluster, username, environment=None, jobname=None):
        if environment is None:
            return cluster + "/" + username
        else:
            return cluster + "/" + username + "/" + environment + "/" + jobname

    def list_jobs(self, cluster, username):
        """Method to execute [ aurora list_jobs cluster/username comman ]"""

        jobkey = self.make_job_key(cluster, username)
        logging.info("request to list jobs = %s" % jobkey)

        try:
            with open("/dev/null") as dev_null:
                cmd_output = subprocess.check_output(
                                [ self.aurora_cmd, "list_jobs", jobkey ],
                                stderr=dev_null)

                jobs = cmd_output.splitlines()
                if len(jobs) == 0:
                    logging.info("no jobs found for key = %s" % jobkey)
                for s in jobs:
                    logging.info("> %s" % s )

                return(jobkey, jobs, None)

        except subprocess.CalledProcessError as e:
            logging.exception("Failed to list Aurora jobs")
            return(jobkey, [], ["Exception when listing aurora jobs", e.msg])

    def create_job(self, cluster, username, environment, jobname, jobspec):
        """Method to create aurora job from job file and job id"""

        jobkey = self.make_job_key(cluster, username, environment, jobname)
        logging.info("request to create job = %s", jobkey)

        logger.info("  job spec:")
        lineno = 1
        for l in jobspec.splitlines():
            logger.info("  %3d: %s" % (lineno, l))
            lineno += 1

        # aurora client requires jobspec be passed as file, no reading from STDIN
        cmd_output = ""
        with tempfile.NamedTemporaryFile(suffix=".aurora") as t:
            t.write(jobspec)
            t.flush()

            try:
                cmd_output = subprocess.check_output(
                    [self.aurora_cmd, "create", jobkey, t.name],
                    stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                logger.warning("aurora client exit status: %d, details follow" % e.returncode)
                for s in e.output.splitlines():
                    logger.warning("> %s" % s)
                logger.warning("----------------------------------------")

                return(jobkey, ["Error reported by aurora client:"] + e.output.splitlines())

        cmd_success_status = False
        cmd_output_lines = cmd_output.splitlines()
        for s in cmd_output_lines:
            logger.info("  > %s" % s)
            if AURORA_SUCCESS_RESPONSE in s:
                cmd_success_status = True

        if cmd_success_status:
            logger.info("aurora -- create job successful")
            return(jobkey, None)
        else:
            logger.warning("aurora -- create job failed")
            return(jobkey, ["Error reported by aurora client:"] + cmd_output_lines)

    def delete_job(self, cluster, username, environment, jobname):
        """Method to delete aurora job by job id"""

        logging.info("aurora -- delete job invoked")

        jobkey = cluster + "/" + username + "/" + environment + "/" + jobname

        logger.info("  job-id: %s" % jobkey)
        logger.info("  job spec:")

        # aurora client requires jobspec be passed as file, no reading from STDIN
        cmd_output = ""
        try:
            cmd_output = subprocess.check_output(
                [self.aurora_cmd, "killall", jobkey],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.warning("aurora client exit status: %d, details follow" % e.returncode)
            for s in e.output.splitlines():
                logger.warning("> %s" % s)
            logger.warning("----------------------------------------")

            return(jobkey, [], ["Error reported by aurora client" + e.output.splitlines()])

        cmd_success_status = False
        cmd_output_lines = cmd_output.splitlines()
        for s in cmd_output_lines:
            logger.info("  > %s" % s)
            if AURORA_SUCCESS_RESPONSE in s:
                cmd_success_status = True

        if cmd_success_status:
            logger.info("aurora -- create job successful")
            return(jobkey, [jobkey], None)
        else:
            logger.warning("aurora -- create job failed")
            return(jobkey, [], ["Error reported by aurora client" + cmd_output_lines])

# factory --------------------------------------------------------------

def create(aurora_cmd=DEFAULT_AURORA_CMD):
	return AuroraClient(aurora_cmd)
