import os
import subprocess

assert 'DEPLOY_HOST' in os.environ
assert 'DEPLOY_HOST_PATH' in os.environ
assert 'DEPLOY_HOST_SSH_USER' in os.environ
assert 'DEPLOY_HOST_SSH_PASSWORD' in os.environ
assert 'TRAVIS_BUILD_DIR' in os.environ

src_file = os.path.join(os.environ['TRAVIS_BUILD_DIR'], 'data_model.py')
dst_file =         os.environ['DEPLOY_HOST_SSH_USER'] \
           + ':' + os.environ['DEPLOY_HOST_SSH_PASSWORD'] \
           + '@' + os.environ['DEPLOY_HOST'] \
           + ':' + os.path.join(os.environ['TRAVIS_BUILD_DIR'], 'data_model.py')
proc = subprocess.Popen(["scp", src_file, dst_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = proc.communicate(timeout=15)

print('scp retcode %s' % proc.returncode)
print('scp stdout "%s"' % stdout)
print('scp stderr "%s"' % stderr)

