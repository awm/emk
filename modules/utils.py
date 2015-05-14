import os
import errno
import subprocess
import traceback
import shutil
import logging
import glob
import filecmp
import sys
import itertools
import platform

log = logging.getLogger("emk.utils")

class Module(object):
    """
    emk utility module - when you call emk.module("utils") you will get an instance of this class.
    """
    def __init__(self, scope):
        self._clean_rules = 0
    
    def new_scope(self, scope):
        return Module(scope)
        
    def flatten(self, args):
        """
        Convert a string, a list of strings, or a list of lists of ... of strings into a single list of strings.
        Any iterable counts as a list (but a real list is returned).
        
        Arguments:
          args -- The string or list to flatten.
        
        Returns a flattened version of the input, which is always a list containing only strings.
        """
        return list(emk._flatten_gen(args))

    def unique_list(self, orig):
        """
        Create a new list from the input list, with duplicate items removed. Order is preserved.
        
        The list items must be hashable.
        
        Arguments:
          orig -- The original list. This list is not modified.
        
        Returns a copy of the original list, with duplicate items removed.
        """
        result = []
        seen = set()
        for item in orig:
            if not item in seen:
                seen.add(item)
                result.append(item)
        return result
    
    def rm_list(self, thelist, item):
        """
        Remove an item from a list, if it is present. It is not an error if the item is not in the list.
        
        Arguments:
          thelist -- The list to remove the item from. This list is modified.
          item    -- The item to remove if it is present in the list.
        """
        try:
            thelist.remove(item)
        except ValueError:
            pass

    def mkdirs(self, path):
        """
        Create all nonexistent directories in a path. It is not an error if the path already exists and is a directory.
        
        If the path already exists and is not a directory, an OSError will be raised.
        
        Arguments:
          path -- The absolute or relative path to create directories for.
        """
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def rm(self, path, print_msg=False):
        """
        Delete a file or directory tree.
        
        It is not an error if the file or directory does not exist.
        
        Arguments:
          path      -- The file or directory tree to remove.
          print_msg -- If True, a log message is printed about the removal. The default value is False.
        """
        if print_msg:
            if os.path.isabs(path):
                log.info("Removing %s", path)
            else:
                log.info("Removing %s", os.path.realpath(os.path.join(os.getcwd(), path)))
        try:
            os.remove(path)
        except OSError:
            shutil.rmtree(path, ignore_errors=True)
    
    def symlink(self, source, link_name):
        """
        Create a symbolic link pointing to source named link_name.  If symbolic links are not supported, then the source will be copied to link_name.
        
        Arguments:
          source    -- The file or directory that the link is to point to.
          link_name -- The name of the link to create.
        """
        try:
            os.symlink(source, link_name)
        except AttributeError:
            shutil.copy(source, link_name)

    class cd(object):
        """
        Simple context manager for changing to a directory, and always returning to the original directory.
        
        Usage:
          with utils.cd("some/path"):
              # do stuff
          # the working directory will always be returned to its original state.
        """
        def __init__(self, path):
            self.dest = path

        def __enter__(self):
            self.orig = os.getcwd()
            os.chdir(self.dest)

        def __exit__(self, *args):
            os.chdir(self.orig)

    def call(self, *args, **kwargs):
        """
        Call a subprocess.
        
        The subprocess will run until it exits (normally or otherwise). The stdout, stderr, and exit code of the
        subprocess are returned if the process exits normally. Otherwise, the default behaviour is to raise a build error,
        but this can be suppressed using the "noexit" keyword argument.
        
        Arguments:
          -- All non-keyword arguments are used to create the subprocess (they are passed to subprocess.Popen()).
        
        Keyword arguments:
          cwd          -- Set the working directory that the subprocess will run in. By default, the subprocess will run
                          in the working directory of the current process.
          env          -- Set the environment for the calling process. Passed directly to subprocess.Popen().
                          The default value is None (ie, the current process environment will be used).
          noexit       -- If True, a non-zero exit code will not raise an error; instead, the normal (stdout, stderr, code) will
                          be returned. The default value is False.
          print_call   -- If True, the subprocess call will be logged. The default value is True.
          print_stdout -- If True, the stdout of the subprocess will be logged (after the subprocess exits). Otherwise,
                          the subprocess stdout will not be logged. The default value is False.
          print_stderr -- If True, the stderr of the subprocess will be logged (after the subprocess exits). If "nonzero",
                          the subprocess stderr will be logged only if the subprocess exits abnormally (with a nonzero exit code).
                          If False, the subprocess stderr will not be logged. The default value is "nonzero".
          error_stream -- Controls which output stream is logged as an error. Can be set to "none", "stdout", "stderr", or "both".
                          The default value is "stderr".
                          
        Returns a tuple (stdout, stderr, exit code).
        """
        args = list(emk._flatten_gen(args))
        print_call = True
        print_stdout = False
        print_stderr = "nonzero"
        error_stream = "stderr"
        exit_on_nonzero_return = True
        cwd = None
        env = None

        if "print_call" in kwargs and not kwargs["print_call"]:
            print_call = False
        if "print_stdout" in kwargs and kwargs["print_stdout"]:
            print_stdout = True
        if "print_stderr" in kwargs:
            print_stderr = kwargs["print_stderr"]
        if "error_stream" in kwargs:
            error_stream = kwargs["error_stream"]
        if "noexit" in kwargs and kwargs["noexit"]:
            exit_on_nonzero_return = False
        if "cwd" in kwargs:
            cwd = kwargs["cwd"]
        if "env" in kwargs:
            env = kwargs["env"]
        
        stdout_tag = emk.style_tag('stdout')
        if error_stream == "stdout" or error_stream == "both":
            stdout_tag = emk.style_tag('stderr')
        
        stderr_tag = emk.style_tag('stdout')
        if error_stream == "stderr" or error_stream == "both":
            stderr_tag = emk.style_tag('stderr')
        
        shell = False
        if platform.system() == "Windows":
            shell = True

        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env, shell=shell)
            proc_stdout, proc_stderr = proc.communicate()
        except OSError as e:
            stack = []
            if emk.options["log"] == "debug":
                stack.append("Call stack:")
                stack += emk.fix_stack(traceback.extract_stack()[:-1])
                if emk.current_rule:
                    stack.append("Rule definition:")
                    stack.extend([emk.style_tag('rule_stack') + line + emk.end_style() for line in emk.current_rule.stack])
            raise emk.BuildError("Could not call '%s' as a subprocess: %s" % (' '.join(args), str(e)), stack)
        strings = []
        if print_call:
            strings.append(' '.join(args))
        if exit_on_nonzero_return and proc.returncode != 0:
            strings.append(emk.style_tag('stderr') + "Nonzero return code: %d" % (proc.returncode) + emk.end_style())
        if print_stdout and proc_stdout:
            strings.append(emk.style_tag('u') + "Subprocess stdout:" + emk.end_style())
            strings.append(stdout_tag + proc_stdout + emk.end_style())
        if (print_stderr == True or (print_stderr == "nonzero" and proc.returncode != 0)) and proc_stderr:
            strings.append(emk.style_tag('u') + "Subprocess stderr:" + emk.end_style())
            strings.append(stderr_tag + proc_stderr + emk.end_style())
        if strings:
            log.info('\n'.join(strings), extra={'adorn':False})
        if exit_on_nonzero_return and proc.returncode != 0:
            stack = []
            if error_stream == "stdout" or error_stream == "both":
                stack.append(stdout_tag + proc_stdout + emk.end_style())
            if error_stream == "stderr" or error_stream == "both":
                stack.append(stderr_tag + proc_stderr + emk.end_style())
            if emk.options["log"] == "debug":
                stack.append("Call stack:")
                stack += emk.fix_stack(traceback.extract_stack()[:-1])
            if emk.options["log"] == "debug" and emk.current_rule:
                stack.append("Rule definition:")
                stack.extend([emk.style_tag('rule_stack') + line + emk.end_style() for line in emk.current_rule.stack])
            raise emk.BuildError("In directory %s:\nSubprocess '%s' returned %s" % (emk.scope_dir, ' '.join(args), proc.returncode), stack)
        return (proc_stdout, proc_stderr, proc.returncode)

    def mark_virtual_rule(self, produces, requires):
        """
        Define an emk rule to mark the productions as virtual.
        
        Arguments:
          produces -- The paths to mark as virtual when the rule is executed.
          requires -- The dependencies of the rule.
        """
        emk.rule(self.mark_virtual, produces, requires, cwd_safe=True, ex_safe=True)
        
    def mark_virtual(self, produces, requires):
        """
        emk rule function to mark the productions as virtual.
        """
        emk.mark_virtual(produces)
    
    def copy_rule(self, source, dest):
        """
        Define an emk rule to copy a file.
        
        The file will only be copied if the source differs from the destination (or the destination does not yet exist).
        Directories containing the destination that do not exist will be created.
        
        Arguments:
          source -- The source file to copy; it treated as an emk dependency (so if there is a rule that produces the source,
                    that rule will be executed before the copy rule is).
          dest   -- The path to copy the file to; must include the destination file name (ie not just the directory).
        """
        emk.rule(self.copy_file, dest, source, cwd_safe=True, ex_safe=True)
    
    def copy_file(self, produces, requires):
        """
        emk rule function to copy a single file.
        """
        dest = produces[0]
        src = requires[0]
        
        try:
            if(os.path.isfile(dest) and filecmp.cmp(dest, src, shallow=False)):
                emk.mark_untouched(produces)
                return
                
            emk.log.info("Copying %s to %s" % (src, dest))
            destdir = os.path.dirname(dest)
            self.mkdirs(destdir)
            shutil.copy2(src, dest)
        except:
            self.rm(dest)
            raise

    def clean_rule(self, *patterns):
        """
        Add patterns for files to remove when "emk clean" is called.
        
        This attaches a rule to the "clean" target that will remove files matching the given patterns.
        
        Arguments:
          patterns -- The patterns for files to remove when cleaning, in glob format.
        
        Returns:
          The product path generated by the new rule (in case you want to depend on it or whatever).
        """
        patterns = list(emk._flatten_gen(patterns))
        target = "__clean_rule_%d__" % (self._clean_rules)
        self._clean_rules += 1
        emk.rule(self.do_cleanup, target, emk.ALWAYS_BUILD, patterns)
        emk.attach("clean", target)
        return target
    
    def do_cleanup(self, produces, requires, patterns):
        """
        emk rule function to clean up (remove) files based on glob patterns.
        """
        for pattern in patterns:
            for f in glob.glob(pattern):
                self.rm(f, print_msg=True)
        emk.mark_virtual(produces)

    def get_environment_from_batch_command(self, env_cmd, initial=None):
        """
        Take a command (either a single command or list of arguments)
        and return the environment created after running that command.
        Note that the command must be a batch file or .cmd file, or the
        changes to the environment will not be captured.

        If initial is supplied, it is used as the initial environment passed
        to the child process.

        Based on response at http://stackoverflow.com/questions/1214496/how-to-get-environment-from-a-subprocess-in-python.

        Arguments:
          env_cmd -- The command to get the post-run environment of.
          initial -- An initial environment dictionary.

        Returns:
          A dictionary representing the environment after running the command.
        """
        if sys.platform != "win32":
            raise OSError("Only supported on Windows")

        def _validate_pair(ob):
            try:
                if not (len(ob) == 2):
                    raise ValueError("Unexpected result: %s" % ob)
            except:
                return False
            return True

        def _consume(iter):
            try:
                while True: next(iter)
            except StopIteration:
                pass

        if not isinstance(env_cmd, (list, tuple)):
            env_cmd = [env_cmd]
        tag = '___COMPLETE___'
        
        out, err, code = self.call(env_cmd, '&&', 'echo', tag, '&&', 'set', env=initial, shell=True, print_call=False)

        lines = out.splitlines()
        _consume(itertools.takewhile(lambda l: tag not in l, lines))
        handle_line = lambda l: l.rstrip().split('=',1)

        pairs = map(handle_line, lines)
        valid_pairs = filter(_validate_pair, pairs)
        result = dict(valid_pairs)
        return result
