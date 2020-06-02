import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from request_handler import handle_request
import data_model
import settings
import telegram_api_mock

import unittest
import threading
from http.server import ThreadingHTTPServer
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

class TestRequestHandler(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        telegram_port = telegram_api_mock.get_free_port()
        cls.server = ThreadingHTTPServer(('localhost', telegram_port), telegram_api_mock.ApiHandler)

        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.setDaemon(True)
        cls.server_thread.start()

        cls.tg_settings = settings.TelegramApi(host_port='http://localhost:%s' % telegram_port, token='iamtoken')
        

    @classmethod
    def get_new_command(cls, name='Room'):
        return {
            'message': {
                'chat': {'id': 1},
                'from': {'username': 'Mark'},
                'text': '/new ' + name,
                'entities': [{
                    'type': 'bot_command',
                    'offset': 0,
                    'length': 4
                }]
            }
        }


    # common test

    def test_hello(self):
        request = {
            'message': {
                'chat': {'id': 1},
                'from': {'username': 'Mark'},
                'text': 'Hi'
            }
        }
        expected = {
            'method': 'sendMessage',
            'chat_id': 1,
            'text': 'Oh hi Mark!'
        }
        engine = create_engine('sqlite:///:memory:')
        Session = sessionmaker(bind=engine)
        session = Session()
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)

    def test_start_list_command(self):
        ''' Check that '/start' command send correct intro message '''

        engine = create_engine('sqlite:///:memory:')
        Session = sessionmaker(bind=engine)
        session = Session()

        request = {
            'message': {
                'chat': {'id': 1},
                'from': {'username': 'Mark'},
                'text': '/start@a',
                'entities': [{
                    'type': 'bot_command',
                    'offset': 0,
                    'length': 8
                }]
            }
        }
        expected = {
            'method': 'sendMessage',
            'chat_id': 1,
            'text': 'Oh hi Mark!\nCreate first list using /new'
        }
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)


    # list tests

    def test_new_list_command(self):
        ''' Check that '/new' command create list and sends it as a message '''

        engine = create_engine('sqlite:///:memory:')
        Session = sessionmaker(bind=engine)
        session = Session()

        # add first one
        request = self.get_new_command('Room')
        expected = {
            'method': 'sendMessage',
            'chat_id': 1,
            'text': 'Room',
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': 'add',
                            'switch_inline_query_current_chat': '/add '
                        },
                    ]
                ]
            }
        }
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)

        first_list = session.query(data_model.List).first()
        self.assertEqual(first_list.name, 'Room')
        self.assertEqual(first_list.tg_chat_id, 1)
        self.assertEqual(first_list.is_current, True)
        self.assertEqual(first_list.last_tg_msg_id, None)

        # second
        request = self.get_new_command('Комната')
        expected = {
            'method': 'sendMessage',
            'chat_id': 1,
            'text': 'Комната',
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': 'add',
                            'switch_inline_query_current_chat': '/add '
                        },
                    ]
                ]
            }
        }
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)

        second_list = session.query(data_model.List).filter_by(name='Комната').one()
        self.assertEqual(second_list.name, 'Комната')
        self.assertEqual(second_list.tg_chat_id, 1)
        self.assertEqual(second_list.is_current, True)
        self.assertEqual(second_list.last_tg_msg_id, None)
        
        # ensure that first list become is_current == False
        self.assertFalse(first_list.is_current)

    # todo: add check for empty '/new' request

    def test_list_command(self):
        ''' Check that '/list' command send list of lists) '''

        engine = create_engine('sqlite:///:memory:')
        Session = sessionmaker(bind=engine)
        session = Session()

        data_model.Base.metadata.create_all(engine)

        list1 = data_model.List(name='Room 1', tg_chat_id=1, is_current=True)
        list2 = data_model.List(name='Room 2', tg_chat_id=1, is_current=False)
        session.add_all([list1, list2])
        session.commit()

        request = {
            'message': {
                'chat': {'id': 1},
                'from': {'username': 'Mark'},
                'text': '/list',
                'entities': [{
                    'type': 'bot_command',
                    'offset': 0,
                    'length': 5
                }]
            }
        }
        expected = {
            'method': 'sendMessage',
            'chat_id': 1,
            'text': 'Lists',
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': '- Room 1',
                            'callback_data': 'select_list ' + str(list1.id)
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove_list ' + str(list1.id)
                        },
                    ],
                    [
                        {
                            'text': 'Room 2',
                            'callback_data': 'select_list ' + str(list2.id)
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove_list ' + str(list2.id)
                        },
                    ],
                    [
                        {
                            'text': 'new',
                            'switch_inline_query_current_chat': '/new '
                        },
                    ]
                ]
            }
        }
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)

    def test_list_callbacks(self):
        ''' Check that 'select_list' and 'remove_list' callbacks works as expected '''

        engine = create_engine('sqlite:///:memory:')
        Session = sessionmaker(bind=engine)
        session = Session()

        data_model.Base.metadata.create_all(engine)

        list1 = data_model.List(name='Room 1', tg_chat_id=1, is_current=True)
        list2 = data_model.List(name='Room 2', tg_chat_id=1, is_current=False)
        session.add_all([list1, list2])
        session.commit()

        lisa = data_model.Item(name='Lisa', list_id=list2.id, checked=False)
        session.add(lisa)
        session.commit()

        # select
        request = {
            'callback_query': {
                'message': {
                    'message_id': 1,
                    'chat': {'id': 1},
                    'from': {'username': 'Mark'},
                },
                'data': 'select_list ' + str(list2.id),
            }
        }
        expected = {
            'method': 'editMessageReplyMarkup',
            'chat_id': 1,
            'message_id': 1,
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': 'Room 1',
                            'callback_data': 'select_list ' + str(list1.id)
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove_list ' + str(list1.id)
                        },
                    ],
                    [
                        {
                            'text': '- Room 2',
                            'callback_data': 'select_list ' + str(list2.id)
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove_list ' + str(list2.id)
                        },
                    ],
                    [
                        {
                            'text': 'new',
                            'switch_inline_query_current_chat': '/new '
                        },
                    ]
                ]
            }
        }
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)

        self.assertEqual(list1.is_current, False)
        self.assertEqual(list2.is_current, True)


        # remove
        request = {
            'callback_query': {
                'message': {
                    'message_id': 1,
                    'chat': {'id': 1},
                    'from': {'username': 'Mark'},
                },
                'data': 'remove_list ' + str(list2.id),
            }
        }
        expected = {
            'method': 'editMessageReplyMarkup',
            'chat_id': 1,
            'message_id': 1,
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': '- Room 1',
                            'callback_data': 'select_list ' + str(list1.id)
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove_list ' + str(list1.id)
                        },
                    ],
                    [
                        {
                            'text': 'new',
                            'switch_inline_query_current_chat': '/new '
                        },
                    ]
                ]
            }
        }
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)
        self.assertFalse(inspect(list1).deleted)
        self.assertTrue(list1.is_current)
        self.assertTrue(inspect(list2).deleted)

        #delete 2
        request = {
            'callback_query': {
                'message': {
                    'message_id': 1,
                    'chat': {'id': 1},
                    'from': {'username': 'Mark'},
                },
                'data': 'remove_list ' + str(list1.id),
            }
        }
        expected = {
            'method': 'editMessageReplyMarkup',
            'chat_id': 1,
            'message_id': 1,
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': 'new',
                            'switch_inline_query_current_chat': '/new '
                        },
                    ]
                ]
            }
        }
        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)
        self.assertTrue(inspect(list1).deleted)
        self.assertTrue(inspect(list2).deleted)


    # item tests

    def test_add_item_command(self):
        ''' Check that '/add' command add items to the current list '''
        engine = create_engine('sqlite:///:memory:')
        Session = sessionmaker(bind=engine)
        session = Session()
        data_model.Base.metadata.create_all(engine)

        clist = data_model.List(name='Room 1', tg_chat_id=1, is_current=True)
        session.add(clist)
        session.commit()

        request = {
            'message': {
                'chat': {'id': 1},
                'from': {'username': 'Mark'},
                'text': '/add Lisa',
                'entities': [{
                    'type': 'bot_command',
                    'offset': 0,
                    'length': 4
                }]
            }
        }
        # expected = {
        #     'method': 'sendMessage',
        #     'chat_id': 1,
        #     'text': 'Room 1',
        #     'reply_markup': {
        #         'inline_keyboard': [
        #             [
        #                 {
        #                     'text': 'Lisa',
        #                     'callback_data': 'check 1'
        #                 },
        #                 {
        #                     'text': '✗',
        #                     'callback_data': 'remove 1'
        #                 },
        #             ],
        #             [
        #                 {
        #                     'text': 'add',
        #                     'switch_inline_query_current_chat': '/add '
        #                 },
        #             ]
        #         ]
        #     }
        # }
        # self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)
        handle_request(request, self.tg_settings, session, engine)

        item = session.query(data_model.Item).filter_by(list_id=clist.id, name='Lisa').one()
        self.assertEqual(item.checked, False)

    def test_item_callbacks(self):
        ''' Check that 'check' and 'remove' callbacks works as expected '''
        engine = create_engine('sqlite:///:memory:')
        Session = sessionmaker(bind=engine)
        session = Session()
        data_model.Base.metadata.create_all(engine)

        clist = data_model.List(name='Room 1', tg_chat_id=1, is_current=True)
        session.add(clist)
        session.commit()
        lisa = data_model.Item(name='Lisa', list_id=clist.id, checked=False)
        johnny = data_model.Item(name='Johnny', list_id=clist.id, checked=False)
        session.add_all([lisa, johnny])
        session.commit()

        # check
        request = {
            'callback_query': {
                'data': 'check ' + str(lisa.id),
                'message': {
                    'message_id': 1,
                    'chat': {'id': 1},
                    'from': {'username': 'Mark'},
                },
            }
        }
        expected = {
            'method': 'editMessageReplyMarkup',
            'chat_id': 1,
            'message_id': 1,
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': '✓ Lisa',
                            'callback_data': 'check ' + str(lisa.id),
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove ' + str(lisa.id),
                        },
                    ],
                    [
                        {
                            'text': 'Johnny',
                            'callback_data': 'check ' + str(johnny.id),
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove ' + str(johnny.id),
                        },
                    ],
                    [
                        {
                            'text': 'add',
                            'switch_inline_query_current_chat': '/add '
                        },
                    ]
                ]
            }
        }

        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)
        self.assertEqual(lisa.checked, True)
        self.assertEqual(johnny.checked, False)

        # remove
        request = {
            'callback_query': {
                'data': 'remove ' + str(johnny.id),
                'message': {
                    'message_id': 1,
                    'chat': {'id': 1},
                    'from': {'username': 'Mark'},
                },
            }
        }
        expected = {
            'method': 'editMessageReplyMarkup',
            'chat_id': 1,
            'message_id': 1,
            'reply_markup': {
                'inline_keyboard': [
                    [
                        {
                            'text': '✓ Lisa',
                            'callback_data': 'check ' + str(lisa.id),
                        },
                        {
                            'text': '✗',
                            'callback_data': 'remove ' + str(lisa.id),
                        },
                    ],
                    [
                        {
                            'text': 'add',
                            'switch_inline_query_current_chat': '/add '
                        },
                    ]
                ]
            }
        }

        self.assertEqual(handle_request(request, self.tg_settings, session, engine), expected)
        self.assertEqual(session.query(data_model.Item).count(), 1)


        # todo: check unknown commands & callbacks


if __name__ == '__main__':
    unittest.main()