from ipykernel.kernelbase import Kernel
from IPython.utils.path import locate_profile
from pexpect import replwrap,EOF,spawn
import signal
import re
import os
from distutils.spawn import find_executable
import sys


__version__ = '0.9.1'

class JythonKernel(Kernel):
    implementation = 'Jython Kernel'
    implementation_version = __version__
    language = 'jython'
    language_version = '2.5.2'
    language_info = {'mimetype': 'text/x-python','name':'jython','file_extension':'.py','codemirror_mode':{'version':2,'name':'text/x-python'},'pygments_lexer':'python','help_links':[{'text':'Jython', 'url': 'www.jython.org'},{'text':'Jython Kernel Help','url':'https://github.com/suvarchal/IJython'}]}
    banner = "Jython Kernel"

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._start_jython()

        try:
            self.hist_file = os.path.join(locate_profile(),'jython_kernel.hist')
        except:
            self.hist_file = None
            self.log.warn('No default profile found, history unavailable')

        self.max_hist_cache = 1000
        self.hist_cache = []
    def _start_jython(self):
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        #for some reason kernel needs two excepts with jython executable so using only jython.jar
        try:
            if "JAVA_HOME" in os.environ:
               self._executable=os.environ['JAVA_HOME']+"/bin/java"
            elif not find_executable("java")=="":
               self._executable=find_executable("java")
            else:
               raise Exception("JAVA_HOME not set or java not found") 
            
            if "JYTHON_HOME" in os.environ:
               self._executable=self._executable+" -jar "+os.environ['JYTHON_HOME']+"/jython.jar"
            elif not find_executable("jython")=="":
               self._executable=self._executable+" -jar "+str('/'.join(find_executable("jython").split('/')[:-2]))+"/jython.jar"
            else:
               raise Exception("JYTHON_HOME not set or jython not found") 
                     
            self._child  = spawn(self._executable,timeout = None)
            self.jywrapper = replwrap.REPLWrapper(self._child,u">>> ",prompt_change=None,new_prompt=u">>> ",continuation_prompt=u'... ')
        finally:
            signal.signal(signal.SIGINT, sig)
       

    def do_execute(self, code, silent, store_history=False, user_expressions=None,
                   allow_stdin=False):
        code   =  code.strip()
	abort_msg = {'status': 'abort',
                     'execution_count': self.execution_count}
        interrupt = False
        try:
  	    output = self.jywrapper.run_command(code+"\n", timeout=None)
            output = '\n'.join([line for line in output.splitlines()[1::]])+'\n'
        except KeyboardInterrupt:
            self.jywrapper.child.sendintr()
            output = self.jywrapper.child.before+output+'\n Got interrupt restarting Jython'
            interrupt = True
            self._start_jython()
	except EOF:
            output = self.jywrapper.child.before + 'Reached EOF Restarting Jython'
            self._start_jython()
 	if not silent:
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        if interrupt:
            return {'status': 'abort', 'execution_count': self.execution_count}

        return {'status': 'ok','execution_count': self.execution_count,'payload': [],'user_expressions': {}}
    def do_complete(self, code, cursor_pos):
        code = code[:cursor_pos]
        default = {'matches': [], 'cursor_start': 0,
                   'cursor_end': cursor_pos, 'metadata': dict(),
                   'status': 'ok'}

        if not code or code[-1] == ' ':
            return default
        
 	tokens = code.split()
        if not tokens:
            return default

        matches = []
        token = tokens[-1]
        start = cursor_pos - len(token)
        
        if len(re.split(r"[^\w]",token)) > 1:
            cmd="dir("+re.split(r"[^\w]",token)[-2]+")"
            output=self.jywrapper.run_command(cmd,timeout=None)
            matches.extend([e for e in re.split(r"[^\w]",output)[2:] if not e.strip()=="" and not e.strip().startswith("__")])
            token=re.split(r"[^\w]",token)[-1]
            start = cursor_pos - len(token)
        else:
            cmd=("import sys;sys.builtins.keys()")
            output=self.jywrapper.run_command(cmd,timeout=None)
            matches.extend([e for e in re.split(r"[^\w]",output)[2:] if not e.strip()=="" and not e.strip().startswith("__")])
        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': sorted(matches), 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}
        
        if code.strip() and store_history:
            self.hist_cache.append(code.strip())

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JythonKernel)
