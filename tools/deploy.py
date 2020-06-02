import os
import subprocess
import pysftp

assert 'DEPLOY_HOST' in os.environ
assert 'DEPLOY_HOST_PATH' in os.environ
assert 'DEPLOY_HOST_SFTP_USER' in os.environ
assert 'DEPLOY_HOST_SFTP_PASSWORD' in os.environ
assert 'TRAVIS_BUILD_DIR' in os.environ

with pysftp.Connection(os.environ['DEPLOY_HOST'], username=os.environ['DEPLOY_HOST_SFTP_USER'], password=os.environ['DEPLOY_HOST_SFTP_PASSWORD']) as sftp:
    src_dir = os.environ['TRAVIS_BUILD_DIR']
    dst_dir = os.environ['DEPLOY_HOST_PATH']
    if not sftp.exists(dst_dir):
        sftp.mkdir(dst_dir)
    with sftp.cd(dst_dir):
        # clean old code
        for item in sftp.listdir():
            if item == 'logs' or item == 'secrets.json':
                continue
            sftp.remove(item)

        # upload new code
        sftp.put(src_dir + '/data_model.py')
        sftp.put(src_dir + '/passenger_wsgi.py')
        sftp.put(src_dir + '/request_handler.py')
        sftp.put(src_dir + '/settings.py')
