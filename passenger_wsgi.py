import os

import logging
fhandler = logging.FileHandler(filename=os.path.join(os.getcwd(), 'logs', 'bot.log'))
fhandler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
logging.getLogger().addHandler(fhandler)
logging.getLogger().setLevel(logging.INFO)

import urllib.parse
import json

import settings
from request_handler import handle_request

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def application(environ, start_response):

    try:
        with open(os.path.join(os.getcwd(), 'secrets.json'), 'r') as secrets_file:
            secrets = json.load(secrets_file)

        encoded_passord = urllib.parse.quote(secrets['db_password'])
        engine = create_engine('mysql+mysqldb://zaripov_shls_bot:{password}@localhost/zaripov_shls_bot?charset=utf8'.format(password=encoded_passord))
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError):
            content_length = 0
        if content_length != 0:
            body = environ['wsgi.input'].read(content_length)
        else:
            body = b''

        request = json.loads(body)
        response = handle_request(request, settings.TelegramApi(secrets['telegram_token']), session, engine)
        session.commit()

        start_response('200 OK', [('Content-Type','application/json;charset=utf-8')])
        return [bytes(json.dumps(response), 'utf-8')]

    except Exception as e:
        logging.exception('exception while handling request')