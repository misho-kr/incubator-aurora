from __future__ import print_function

from collections import namedtuple
import getpass
import os
import pwd
import sys
import time
import pprint

from pystachio import Ref

from twitter.common import app, log
from twitter.common.log.options import LogOptions
from twitter.common.dirutil import du
from twitter.common.quantity import Amount, Time, Data
from twitter.common.quantity.parse_simple import parse_time, parse_data
from twitter.common.recordio import ThriftRecordReader
from twitter.thermos.base.path import TaskPath
from twitter.thermos.base.ckpt import CheckpointDispatcher
from twitter.thermos.base.options import add_port_to, add_binding_to
from twitter.thermos.config.loader import ThermosConfigLoader, ThermosTaskWrapper
from twitter.thermos.config.schema import (
  Process,
  Resources,
  Task)
from twitter.thermos.runner import TaskRunner
from twitter.thermos.monitoring.detector import TaskDetector
from twitter.thermos.monitoring.garbage import TaskGarbageCollector, DefaultCollector

from gen.twitter.thermos.ttypes import (
  ProcessState,
  RunnerCkpt,
  RunnerState,
  TaskState)

app.add_option("--root", dest="root", metavar="PATH",
               default=os.path.join(os.environ['HOME'], '.thermos'),
               help="the thermos config root")


def set_keep(option, opt_str, value, parser):
  setattr(parser.values, option.dest, opt_str.startswith('--keep'))


def get_task_from_options(args, opts, **kw):
  loader = ThermosConfigLoader.load_json if opts.json else ThermosConfigLoader.load

  if len(args) != 1:
    app.error('Should specify precisely one config, instead got: %s' % args)

  tasks = loader(args[0], bindings=opts.bindings, **kw)

  if len(tasks.tasks()) == 0:
    app.error("No tasks specified!")

  if opts.task is None and len(tasks.tasks()) > 1:
    app.error("Multiple tasks in config but no task name specified!")

  task = None
  if opts.task is not None:
    for t in tasks.tasks():
      if t.task().name().get() == opts.task:
        task = t
        break
    if task is None:
      app.error("Could not find task %s!" % opts.task)
  else:
    task = tasks.tasks()[0]

  if kw.get('strict', False):
    if not task.task.check().ok():
      app.error(task.task.check().message())

  return task


def daemonize():
  def daemon_fork():
    try:
      if os.fork() > 0:
        os._exit(0)
    except OSError as e:
      sys.stderr.write('[pid:%s] Failed to fork: %s\n' % (os.getpid(), e))
      sys.exit(1)
  daemon_fork()
  os.setsid()
  daemon_fork()
  sys.stdin, sys.stdout, sys.stderr = (open('/dev/null', 'r'),
                                       open('/dev/null', 'a+'),
                                       open('/dev/null', 'a+', 0))

@app.command
@app.command_option("--user", metavar="USER", default=getpass.getuser(), dest='user',
                    help="run as this user.  if not $USER, must have setuid privilege.")
@app.command_option("--enable_chroot", dest="chroot", default=False, action='store_true',
                    help="chroot tasks to the sandbox before executing them, requires "
                    "root privileges.")
@app.command_option("--task", metavar="TASKNAME", default=None, dest='task',
                    help="The thermos task within the config that should be run. Only required if "
                    "there are multiple tasks exported from the thermos configuration.")
@app.command_option("--task_id", metavar="STRING", default=None, dest='task_id',
                    help="The id to which this task should be bound, synthesized from the task "
                    "name if none provided.")
@app.command_option("--json", default=False, action='store_true', dest='json',
                    help="Read the source file in json format.")
@app.command_option("--sandbox", metavar="PATH", default="/var/lib/thermos/sandbox", dest='sandbox',
                    help="The sandbox in which to run the task.")
@app.command_option("-P", "--port", type="string", nargs=1, action="callback",
                    callback=add_port_to('prebound_ports'), dest="prebound_ports", default=[],
                    metavar="NAME:PORT", help="bind named PORT to NAME.")
@app.command_option("-E", "--environment", type="string", nargs=1, action="callback",
                    callback=add_binding_to('bindings'), default=[], dest="bindings",
                    metavar="NAME=VALUE",
                    help="bind the configuration environment variable NAME to VALUE.")
@app.command_option("--daemon", default=False, action='store_true', dest='daemon',
                    help="fork and daemonize the thermos runner.")
def run(args, options):
  # TODO(wickman)  This should really be integrated into an AppCmd class.
  """Run a thermos task.

    Usage: thermos run [options] config [task_name]
    Options:
      --user=USER		   run as this user.  if not $USER, must have setuid privilege.
      --enable_chroot		   chroot into the sandbox for this task, requires superuser
                                   privilege
      --task=TASKNAME		   the thermos task within the config that should be run.  only
                                   required if there are multiple tasks exported from the thermos
                                   configuration.
      --task_id=STRING		   the id to which this task should be bound, synthesized from the
                                   task name if none provided.
      --json			   specify that the config is in json format instead of pystachio
      --sandbox=PATH		   the sandbox in which to run the task
                                   [default: /var/lib/thermos/sandbox]
      -P/--port=NAME:PORT	   bind the named port NAME to port number PORT (may be specified
                                   multiple times to bind multiple names.)
      -E/--environment=NAME=VALUE  bind the configuration environment variable NAME to
                                   VALUE.
      --daemon			   Fork and daemonize the task.
  """
  thermos_task = get_task_from_options(args, options)
  prebound_ports = options.prebound_ports or {}
  missing_ports = set(thermos_task.ports()) - set(prebound_ports.keys())
  if missing_ports:
    app.error('ERROR!  Unbound ports: %s' % ' '.join(port for port in missing_ports))
  task_runner = TaskRunner(thermos_task.task, options.root, options.sandbox,
    task_id=options.task_id, user=options.user, portmap=prebound_ports, chroot=options.chroot)
  if options.daemon:
    print('Daemonizing and starting runner.')
    try:
      log.teardown_stderr_logging()
      daemonize()
    except Exception as e:
      print("Failed to daemonize: %s" % e)
      sys.exit(1)
  task_runner.run()


@app.command
@app.command_option("--user", metavar="USER", default=getpass.getuser(), dest='user',
                    help="run as this user.  if not $USER, must have setuid privilege.")
@app.command_option("--name", metavar="STRING", default='simple', dest='name',
                    help="The name to give this task.")
@app.command_option("--task_id", metavar="STRING", default=None, dest='task_id',
                    help="The id to which this task should be bound, synthesized from the task "
                    "name if none provided.")
@app.command_option("-P", "--port", type="string", nargs=1, action="callback",
                    callback=add_port_to('prebound_ports'), dest="prebound_ports", default=[],
                    metavar="NAME:PORT", help="bind named PORT to NAME.")
@app.command_option("-E", "--environment", type="string", nargs=1, action="callback",
                    callback=add_binding_to('bindings'), default=[], dest="bindings",
                    metavar="NAME=VALUE",
                    help="bind the configuration environment variable NAME to VALUE.")
@app.command_option("--daemon", default=False, action='store_true', dest='daemon',
                    help="fork and daemonize the thermos runner.")
def simplerun(args, options):
  """Run a simple command line as a thermos task.

    Usage: thermos simplerun [options] [--] commandline
    Options:
      --user=USER		   run as this user.  if not $USER, must have setuid privilege.
      --name=STRING		   the name to give this task. ('simple' by default)
      --task_id=STRING		   the id to which this task should be bound, synthesized from the
                                   task name if none provided.
      -P/--port=NAME:PORT	   bind the named port NAME to port number PORT (may be specified
                                   multiple times to bind multiple names.)
      -E/--environment=NAME=VALUE  bind the configuration environment variable NAME to
                                   VALUE.
      --daemon			   Fork and daemonize the task.
  """
  try:
    cutoff = args.index('--')
    cmdline = ' '.join(args[cutoff+1:])
  except ValueError:
    cmdline = ' '.join(args)

  print("Running command: '%s'" % cmdline)

  thermos_task = ThermosTaskWrapper(Task(
    name = options.name,
    resources = Resources(cpu = 1.0, ram = 256 * 1024 * 1024, disk = 0),
    processes = [Process(name = options.name, cmdline = cmdline)]))

  prebound_ports = options.prebound_ports or {}
  missing_ports = set(thermos_task.ports()) - set(prebound_ports.keys())
  if missing_ports:
    app.error('ERROR!  Unbound ports: %s' % ' '.join(port for port in missing_ports))
  task_runner = TaskRunner(thermos_task.task, options.root, None,
    task_id=options.task_id, user=options.user, portmap=prebound_ports)
  if options.daemon:
    print('Daemonizing and starting runner.')
    try:
      log.teardown_stderr_logging()
      daemonize()
    except Exception as e:
      print("Failed to daemonize: %s" % e)
      sys.exit(1)
  task_runner.run()


@app.command
@app.command_option("--simple", default=False, dest='simple', action='store_true',
                    help="Only print the checkpoint records, do not replay them.")
def read(args, options):
  """Replay a thermos checkpoint.

  Usage: thermos read [options] checkpoint_filename
  Options:
    --simple	Do not replay the full task state machine.  Only print out the contents of
                each checkpoint log message.
  """
  if len(args) != 1:
    app.error('Expected one checkpoint file, got %s' % len(args))
  if not os.path.exists(args[0]):
    app.error('Could not find %s' % args[0])

  dispatcher = CheckpointDispatcher()
  state = RunnerState(processes={})
  with open(args[0], 'r') as fp:
    for record in ThriftRecordReader(fp, RunnerCkpt):
      if not options.simple:
        dispatcher.dispatch(state, record)
      else:
        print('CKPT: %s' % record)

  if not options.simple:
    print('Recovered Task Header:')
    print('  id:      %s' % state.header.task_id)
    print('  user:    %s' % state.header.user)
    print('  host:    %s' % state.header.hostname)
    print('  sandbox: %s' % state.header.sandbox)
    if state.header.ports:
      print('  ports:   %s' % ' '.join(
        '%s->%s' % (name, port) for (name, port) in state.header.ports.items()))
    print('Recovered Task States:')
    for task_status in state.statuses:
      print('  %s [pid: %d] => %s' % (
        time.asctime(time.localtime(task_status.timestamp_ms/1000.0)),
        task_status.runner_pid,
        TaskState._VALUES_TO_NAMES[task_status.state]))
    print('Recovered Processes:')
    for process, process_history in state.processes.items():
      print('  %s   runs: %s' % (process, len(process_history)))
      for k in reversed(range(len(process_history))):
        run = process_history[k]
        print('    %2d: pid=%d, rc=%s, finish:%s, state:%s' % (
          k,
          run.pid,
          run.return_code if run.return_code is not None else '',
          time.asctime(time.localtime(run.stop_time)) if run.stop_time else 'None',
          ProcessState._VALUES_TO_NAMES.get(run.state, 'Unknown')))


@app.command
def kill(args, options):
  """Kill task(s)

  Usage: thermos kill task_id1 [task_id2 ...]
  """
  if not args:
    print('Must specify tasks!', file=sys.stderr)
    return
  for task_id in args:
    runner = TaskRunner.get(task_id, options.root)
    if runner is None:
      print('Could not bind to %s!' % task_id, file=sys.stderr)
    else:
      print('Killing %s...' % task_id, end='')
      runner.kill(force=True)
      print('done.')


@app.command
@app.command_option("--max_age", metavar="AGE", default=None, dest='max_age',
                    help="Max age in human readable form, e.g. 2d5h or 7200s")
@app.command_option("--max_tasks", metavar="NUM", default=None, dest='max_tasks',
                    help="Max number of tasks to keep.")
@app.command_option("--max_space", metavar="SPACE", default=None, dest='max_space',
                    help="Max space to allow for tasks, e.g. 20G.")
@app.command_option("--keep-data", "--delete-data",
                    metavar="PATH", default=True,
                    action='callback', callback=set_keep, dest='keep_data',
                    help="Keep data.")
@app.command_option("--keep-logs", "--delete-logs",
                    metavar="PATH", default=True,
                    action='callback', callback=set_keep, dest='keep_logs',
                    help="Keep logs.")
@app.command_option("--keep-metadata", "--delete-metadata",
                    metavar="PATH", default=True,
                    action='callback', callback=set_keep, dest='keep_metadata',
                    help="Keep metadata.")
@app.command_option("--force", default=False, action='store_true', dest='force',
                    help="Perform garbage collection without confirmation")
@app.command_option("--dryrun", default=False, action='store_true', dest='dryrun',
                    help="Don't actually run garbage collection.")
def gc(args, options):
  """Garbage collect task(s) and task metadata.

    Usage: thermos gc [options] [task_id1 task_id2 ...]

    If tasks specified, restrict garbage collection to only those tasks,
    otherwise all tasks are considered.  The optional constraints are still
    honored.

    Options:
      --max_age=AGE		Max age in quasi-human readable form, e.g. --max_age=2d5h,
                                format *d*h*m*s [default: skip]
      --max_tasks=NUM		Max number of tasks to keep [default: skip]
      --max_space=SPACE		Max space to allow for tasks [default: skip]
      --[keep/delete-]metadata	Garbage collect metadata [default: keep]
      --[keep/delete-]logs	Garbage collect logs [default: keep]
      --[keep/delete-]data	Garbage collect data [default: keep]
                                WARNING: Do NOT do this if your sandbox is $HOME.
      --force			Perform garbage collection without confirmation [default: false]
      --dryrun			Don't actually run garbage collection [default: false]
  """
  print('Analyzing root at %s' % options.root)
  gc_options = {}
  if options.max_age is not None:
    gc_options['max_age'] = parse_time(options.max_age)
  if options.max_space is not None:
    gc_options['max_space'] = parse_data(options.max_space)
  if options.max_tasks is not None:
    gc_options['max_tasks'] = int(options.max_tasks)
  gc_options.update(include_data = not options.keep_data,
                    include_metadata = not options.keep_metadata,
                    include_logs = not options.keep_logs,
                    verbose = True, logger = print)
  tgc = TaskGarbageCollector(root=options.root)
  gc_tasks = DefaultCollector(tgc, **gc_options).run()

  if not gc_tasks:
    print('No tasks to garbage collect.  Exiting')
    return

  if options.dryrun:
    print('Specified dry-run, skipping.')
  else:
    value = 'y'
    if not options.force:
      value = raw_input("Continue [y/N]? ") or 'N'
    if value.lower() == 'y':
      print('Running gc...')
      tgc = TaskGarbageCollector(root=options.root)
      for task in gc_tasks:
        print('  Task %s ' % task.task_id, end='')
        print('data %s ' % ('keeping' if options.keep_data else 'deleting'), end='')
        if not options.keep_data:
          tgc.erase_data(task.task_id)
        print('logs %s ' % ('keeping' if options.keep_logs else 'deleting'), end='')
        if not options.keep_logs:
          tgc.erase_logs(task.task_id)
        print('metadata %s ' % ('keeping' if options.keep_metadata else 'deleting'), end='')
        if not options.keep_metadata:
          tgc.erase_metadata(task.task_id)
        print('done.')
    else:
      print('Cancelling gc.')


# TODO(wickman)  Implement.
@app.command
def monitor(args, options):
  """Monitor task(s)

    Usage: thermos monitor task_id [task_id_2 ...]
  """
  pass


@app.command
@app.command_option("--verbosity", default=0, dest='verbose', type='int',
                    help="Display more verbosity")
def status(args, options):
  """Get the status of task(s).

    Usage: thermos [options] status [task_name]
    Options:
      --verbosity=LEVEL		Verbosity level for logging. [default: 0]
  """
  detector = TaskDetector(root = options.root)

  def format_task(task_id):
    checkpoint_filename = detector.get_checkpoint(task_id)
    checkpoint_stat = os.stat(checkpoint_filename)
    try:
      checkpoint_owner = pwd.getpwuid(checkpoint_stat.st_uid).pw_name
    except:
      checkpoint_owner = 'uid:%s' % checkpoint_stat.st_uid
    print('  %-20s [owner: %8s]' % (task_id, checkpoint_owner), end='')
    if options.verbose == 0:
      print()
    if options.verbose > 0:
      state = CheckpointDispatcher.from_file(checkpoint_filename)
      if state is None:
        print(' - CORRUPT or outdated format')
        return
      print('  state: %8s' % TaskState._VALUES_TO_NAMES.get(state.statuses[-1].state, 'Unknown'),
        end='')
      print(' start: %25s' % time.asctime(time.localtime(state.header.launch_time_ms/1000.0)))
    if options.verbose > 1:
      print('    user: %s' % state.header.user, end='')
      if state.header.ports:
        print(' ports: %s' % ' '.join('%s -> %s' % (key, val)
                                         for key, val in state.header.ports.items()))
      else:
        print(' ports: None')
      print('    sandbox: %s' % state.header.sandbox)
    if options.verbose > 2:
      print('    process table:')
      for process, process_history in state.processes.items():
        print('      - %s runs: %s' % (process, len(process_history)), end='')
        last_run = process_history[-1]
        print(' last: pid=%d, rc=%s, finish:%s, state:%s' % (
          last_run.pid,
          last_run.return_code if last_run.return_code is not None else '',
          time.asctime(time.localtime(last_run.stop_time)) if last_run.stop_time else 'None',
          ProcessState._VALUES_TO_NAMES.get(last_run.state, 'Unknown')))
      print()

  if args:
    for task_id in args:
      if os.path.exists(detector.get_checkpoint(task_id)):
        print('Found task %s' % task_id)
        format_task(task_id)
      else:
        print('ERROR: Could not find task %s' % task_id, file=sys.stderr)
  else:
    active_task_ids = [t_id for _, t_id in detector.get_task_ids(state='active')]
    finished_task_ids = [t_id for _, t_id in detector.get_task_ids(state='finished')]

    if not active_task_ids and not finished_task_ids:
      print('No tasks found in root [%s]' % options.root)
      sys.exit(1)

    if active_task_ids:
      print('Active tasks:')
      for task_id in active_task_ids:
        format_task(task_id)
      print()

    if finished_task_ids:
      print('Finished tasks:')
      for task_id in finished_task_ids:
        format_task(task_id)
      print()


@app.command
def help(args, options):
  """Get help about a specific command.
  """
  if len(args) == 0:
    app.help()
  for (command, doc) in app.get_commands_and_docstrings():
    if args[0] == command:
      print('command %s:' % command)
      print(doc)
      app.quit(0)
  print('unknown command: %s' % args[0], file=sys.stderr)


def generate_usage():
  usage = """
thermos

commands:
"""

  for (command, doc) in app.get_commands_and_docstrings():
    usage += '    ' + '%-10s' % command + '\t' + doc.split('\n')[0].strip() + '\n'
  app.set_usage(usage)


LogOptions.set_disk_log_level('DEBUG')
LogOptions.set_stdout_log_level('INFO')
generate_usage()
app.main()