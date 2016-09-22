from ipykernel.kernelbase import Kernel
from IPython.utils.path import locate_profile
from pexpect import replwrap,EOF,spawn
import signal
import re
import os
from distutils.spawn import find_executable
import sys


__version__ = '1.0.1'

class JythonKernel(Kernel):
    implementation = 'Jython Kernel'
    implementation_version = __version__
    language = 'jython'
    language_version = '2.7.0'
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
            if not find_executable("jython")==None:
               self._executable=find_executable("jython")
            elif "JYTHON_HOME" in os.environ and "JAVA_HOME" in os.environ :
               self._executable=os.environ['JAVA_HOME']+"/bin/java -jar "+os.environ['JYTHON_HOME']+"/jython.jar"
            else:
               raise Exception("JYTHON_HOME not set or jython not found") 
            self._child  = spawn(self._executable,timeout = None)
            self._child.waitnoecho(True)
            self._child.expect(u">>> ")
            self._child.expect(u">>> ")
            self._child.setwinsize(600,400)
        finally:
            signal.signal(signal.SIGINT, sig)
       

    def do_execute(self, code, silent, store_history=False, user_expressions=None,
                   allow_stdin=False):
        code   =  code.strip()
	abort_msg = {'status': 'abort',
                     'execution_count': self.execution_count}
        interrupt = False
        try:
  	    output = self.jyrepl(code, timeout=None)
            output = '\n'.join([line for line in output.splitlines()])+'\n'
        except KeyboardInterrupt:
            self._child.sendintr()
            output = self._child.before+output+'\n Current Jython cannot interrupt so restarting Jython'
            interrupt = True
            self._start_jython()
	except EOF:
            output = self._child.before + 'Reached EOF Restarting Jython'
            self._start_jython()

 	if not silent:
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)
        if code.strip() and store_history:
            self.hist_cache.append(code.strip())
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

        token = tokens[-1]
        start = cursor_pos - len(token)
        matches = []
        
        if len(re.split(r"[^\w]",token)) > 1:
            cmd="dir("+re.split(r"[^\w]",token)[-2]+")"
            output=self.jyrepl(cmd,timeout=None)
            matches.extend([e for e in re.split(r"[^\w]",output)[2:] if not e.strip()=="" and not e.strip().startswith("__")])
            token=re.split(r"[^\w]",token)[-1]
            start = cursor_pos - len(token)
        else:
            cmd=("import sys;sys.builtins.keys()")
            output=self.jyrepl(cmd,timeout=None)
            matches.extend([e for e in re.split(r"[^\w]",output)[2:] if not e.strip()=="" and not e.strip().startswith("__")])
        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': sorted(matches), 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}
        
    def do_history(self,hist_access_type,output,raw,session=None,start=None,stoop=None,n=None,pattern=None,unique=None):
        if not self.hist_file:
            return {'history':[]}
        if not os.path.exists(self.hist_file):
            with open(self.hist_file, 'wb') as f:
                f.write('')

        with open(self.hist_file, 'rb') as f:
            history = f.readlines()

        history = history[:self.max_hist_cache]
        self.hist_cache = history
        self.log.debug('**HISTORY:')
        self.log.debug(history)
        history = [(None, None, h) for h in history]

        return {'history': history}

    def do_shutdown(self,restart):
        try:
            self.send("exit()")
        except:
            self._child.kill(signal.SIGKILL)
        return {'status':'ok', 'restart':restart}
    def jyrepl(self,code,timeout=None):
        out=""
        #this if is needed for printing output if command entered is "variable" or fucntions like abc(var) and for code completion
#        if (len(re.split(r"\=",code.strip()))==1) and (len(re.split(r"[\ ]",code.strip()))==1):
#            code='eval('+repr(code.strip())+')'
#            self._child.sendline(code)
#            now_prompt=self._child.expect_exact([u">>> ",u"... "])
#            if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'
#	    now_prompt=self._child.expect_exact([u">>> ",u"... "])
#        else:
#            code='exec('+repr(code)+')'
#            for line in code.splitlines():
#                self._child.sendline(line)
#                now_prompt=self._child.expect_exact([u">>> ",u"... "])
#                if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'
#                now_prompt=self._child.expect_exact([u">>> ",u"... "])
        code='exec('+repr(code)+')'
        for line in code.splitlines():
            self._child.sendline(line)
            now_prompt=self._child.expect_exact([u">>> ",u"... "])
            if len(self._child.before.splitlines())>1:    out+='\n'.join(self._child.before.splitlines()[1:])+'\n'
            now_prompt=self._child.expect_exact([u">>> ",u"... "])
        return out

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JythonKernel)
