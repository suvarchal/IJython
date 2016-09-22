from distutils.command.install import install
from distutils import log
import sys
import os
import json


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


kernel_json = {
    "argv": [sys.executable,
	     "-m", "jython_kernel",
	     "-f", "{connection_file}"],
    "display_name": "Jython",
    "language": "python",
    "name": "jython_kernel",
}


class install_with_kernelspec(install):

    def run(self):
        install.run(self)
        user = '--user' in sys.argv
        try:
            from jupyter_client.kernelspec import install_kernel_spec
        except ImportError:
            from IPython.kernel.kernelspec import install_kernel_spec
        from IPython.utils.tempdir import TemporaryDirectory
        with TemporaryDirectory() as td:
            os.chmod(td, 0o755)  # Starts off as 700, not user readable
            with open(os.path.join(td, 'kernel.json'), 'w') as f:
                json.dump(kernel_json, f, sort_keys=True)
            log.info('Installing kernel spec')
            kernel_name = kernel_json['name']
            try:
                install_kernel_spec(td, kernel_name, user=user,
                                    replace=True)
            except:
                install_kernel_spec(td, kernel_name, user=not user,
                                    replace=True)


svem_flag = '--single-version-externally-managed'
if svem_flag in sys.argv:
    # Die, setuptools, die.
    sys.argv.remove(svem_flag)


with open('jython_kernel.py') as fid:
    for line in fid:
        if line.startswith('__version__'):
            version = line.strip().split()[-1][1:-1]
            break
setup(name='jython_kernel',
      description='A Jython kernel for Jupyter/IPython',
      version=version,
      url="https://github.com/suvarchal/IJython",
      author='Suvarchal Kumar Cheedela',
      author_email='suvarchal.kumar@gmail.com',
      py_modules=['jython_kernel'],
      license="MIT",
      cmdclass={'install': install_with_kernelspec},
      install_requires=["IPython >= 3.0","jupyter_client"],
      classifiers=[
          'Framework :: IPython',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Jython :: 2',
          'Programming Language :: Python :: 2',
          'Topic :: System :: Shells',
      ]
)
