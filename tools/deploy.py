import os
import subprocess
import pysftp

assert 'DEPLOY_HOST' in os.environ
assert 'DEPLOY_HOST_PATH' in os.environ
assert 'DEPLOY_HOST_SFTP_USER' in os.environ
assert 'DEPLOY_HOST_SFTP_PASSWORD' in os.environ
assert 'TRAVIS_BUILD_DIR' in os.environ

host = os.environ['DEPLOY_HOST']
username = os.environ['DEPLOY_HOST_SFTP_USER']
password = os.environ['DEPLOY_HOST_SFTP_PASSWORD']
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None


def rmdir_recurse(client, path):
    for item in client.listdir(remotepath=path):
        subpath = path + '/' + item
        if client.isdir(subpath):
            rmdir_recurse(client, subpath)
        else:
            client.remove(subpath)
    client.rmdir(path)

with pysftp.Connection(host, username=username, password=password, cnopts=cnopts) as sftp:
    src_dir = os.environ['TRAVIS_BUILD_DIR']
    dst_dir = os.environ['DEPLOY_HOST_PATH']
    if not sftp.exists(dst_dir):
        sftp.mkdir(dst_dir)
    with sftp.cd(dst_dir):
        # clean old code
        for item in sftp.listdir():
            if item == 'logs' or item == 'secrets.json':
                continue
            if sftp.isdir(item):
                rmdir_recurse(sftp, item)
            else:
                sftp.remove(item)

        # upload new code
        sftp.put(src_dir + '/data_model.py')
        sftp.put(src_dir + '/passenger_wsgi.py')
        sftp.put(src_dir + '/request_handler.py')
        sftp.put(src_dir + '/settings.py')

        # create 'logs' folder if it not exists
        if not sftp.exists('logs'):
            sftp.mkdir('logs')

        # tell the passanger to restart app by creating tmp/restart
        sftp.mkdir('tmp')
        with sftp.cd('tmp'):
            sftp.open('restart.txt', 'w')

print('Deploy finished successfully')
