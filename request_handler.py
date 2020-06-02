import data_model

import urllib.request
import urllib.error
import logging
import json

# common

def updated(dct, upd):
    dct.update(upd)
    return dct

def has_command(message):
    if not 'text' in message or not 'entities' in message:
        return False
    for entry in message['entities']:
        if 'type' in entry and entry['type'] == 'bot_command':
            return True
    return False

def extract_commands(message):
    commands = []
    for entry in message['entities']:
        if 'type' in entry and entry['type'] == 'bot_command':
            command = message['text'][entry['offset'] : entry['offset']+entry['length']]
            commands += [command.split('@')[0]]
    return commands

def extract_text(message):
    text = message['text']
    cutted = 0
    for entry in message['entities']:
        if 'type' in entry and entry['type'] in ['bot_command', 'mention']:
            begin = entry['offset'] - cutted
            end = entry['offset'] + entry['length'] - cutted
            text = text[:begin] + text[end + 1:]
            cutted += entry['length'] + 1
    return text

def tg_request(tg_settings, body, method):
    url = tg_settings.url_tmpl.format(token=tg_settings.token, method=method)
    headers = {'Content-Type': 'application/json'}
    request = urllib.request.Request(url, data=bytearray(json.dumps(body), 'ascii'), headers=headers)
    try:
        httpResponse = urllib.request.urlopen(request)
        responseText = httpResponse.read()
        response = json.loads(responseText)
        assert response['ok']
        return response
    except urllib.error.HTTPError as e:
        logging.error('can\'t make request \'%s\': \'%s\'' % (url, str(e)))
    return {}
    
# list

def get_lists_inline_keyboard(session, chat_id):
    inline_keyboard = []
    for ilist in session.query(data_model.List).filter_by(tg_chat_id=chat_id):
        inline_keyboard += [
            [
                {
                    'text': ('- ' if ilist.is_current else '') + ilist.name,
                    'callback_data': 'select_list ' + str(ilist.id)
                },
                {
                    'text': '✗',
                    'callback_data': 'remove_list ' + str(ilist.id)
                },
            ]
        ]

    inline_keyboard += [
        [
            {
                'text': 'new',
                'switch_inline_query_current_chat': '/new '
            },
        ]
    ]
    return inline_keyboard

def send_all_lists(session, chat_id):
    return {
        'method': 'sendMessage',
        'chat_id': chat_id,
        'text': 'Lists',
        'reply_markup': {
            'inline_keyboard': get_lists_inline_keyboard(session, chat_id),
        }
    }

def edit_lists(session, chat_id, message_id):
    return {
        'method': 'editMessageReplyMarkup',
        'chat_id': chat_id,
        'message_id': message_id,
        'reply_markup': {
            'inline_keyboard': get_lists_inline_keyboard(session, chat_id),
        }
    }


# items

def get_items_inline_keyboard(session, list_id):
    inline_keyboard = []
    clist = session.query(data_model.List).get(list_id)
    for item in clist.items:
        inline_keyboard += [
            [
                {
                    'text': ('✓ ' if item.checked else '') + item.name,
                    'callback_data': 'check ' + str(item.id)
                },
                {
                    'text': '✗',
                    'callback_data': 'remove ' + str(item.id)
                },
            ]
        ]

    inline_keyboard += [
        [
            {
                'text': 'add',
                'switch_inline_query_current_chat': '/add '
            },
        ]
    ]
    return inline_keyboard

def get_items(session, list_id, chat_id):
    clist = session.query(data_model.List).get(list_id)

    return {
        'chat_id': chat_id,
        'text': clist.name,
        'reply_markup': {
            'inline_keyboard': get_items_inline_keyboard(session, list_id)
        }
    }

def edit_items(session, list_id, chat_id, message_id):
    return {
        'method': 'editMessageReplyMarkup',
        'chat_id': chat_id,
        'message_id': message_id,
        'reply_markup': {
            'inline_keyboard': get_items_inline_keyboard(session, list_id),
        }
    }


def handle_request(request, tg_settings, session, engine):
    data_model.Base.metadata.create_all(engine)

    if 'message' in request:
        message = request['message']
        chat_id = message['chat']['id']
        
        if has_command(message):
            commands = extract_commands(message)
            if commands[0] == '/start':
                username = message['from']['username']
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'Oh hi %s!\nCreate first list using /new' % username
                } 
            elif commands[0] == '/new':
                name = extract_text(message)
                logging.info('adding new list "%s" to the "%s" chat' % (name, chat_id))

                if not name:
                    return {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': 'send new list name, e.g: /new myTodoList'
                    }                
                # first make all other messages non-current
                for old_list in session.query(data_model.List).filter_by(tg_chat_id=chat_id):
                    old_list.is_current = False
                clist = data_model.List(name=name, tg_chat_id=chat_id, is_current=True)
                session.add(clist)
                session.commit()
                return updated(get_items(session, clist.id, chat_id), {'method': 'sendMessage'})
            elif commands[0] == '/list':
                logging.info('listing lists for the "%s" chat' % (chat_id))
                return send_all_lists(session, chat_id)
            elif commands[0] == '/add':
                name = extract_text(message)
                clist = session.query(data_model.List).filter_by(tg_chat_id=chat_id, is_current=True).one_or_none()
                if not clist:
                    return {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': 'no list to add, create list using /new listName first'
                    }
                item = data_model.Item(name=name, list_id=clist.id, checked=False)
                session.add(item)
                session.commit()

                if clist.last_tg_msg_id:
                    tg_request(tg_settings, {'chat_id': chat_id, 'message_id': clist.last_tg_msg_id}, 'deleteMessage')
                resp = tg_request(tg_settings, get_items(session, clist.id, chat_id), 'sendMessage')
                clist.last_tg_msg_id = resp['result']['message_id']
                return {}
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': 'I don\'t know ' + commands[0] + ' command('
                }
            
        else:
            return {
                'method': 'sendMessage',
                'chat_id': message['chat']['id'],
                'text': 'Oh hi %s!' % message['from']['username']
            }

    elif 'callback_query' in request:
        callback_query = request['callback_query']
        command_list = callback_query['data'].split(' ')
        action = command_list[0]
        list_or_item_id = int(command_list[1])
        chat_id = callback_query['message']['chat']['id']
        message_id = callback_query['message']['message_id']
        
        if action == 'select_list':
            for clist in session.query(data_model.List).filter_by(tg_chat_id=chat_id):
                clist.is_current = False
            clist = session.query(data_model.List).get(list_or_item_id)
            logging.info('selecting list "%s" lists for the "%s" chat' % (clist.name, chat_id))
            clist.is_current = True
            tg_request(tg_settings, get_items(session, clist.id, chat_id), 'sendMessage')
            
            return edit_lists(session, chat_id, message_id)
        elif action == 'remove_list':
            clist = session.query(data_model.List).get(list_or_item_id)
            logging.info('removing list "%s" lists for the "%s" chat' % (clist.name, chat_id))
            session.query(data_model.List).filter_by(id=list_or_item_id).delete()
            clist = session.query(data_model.List).filter_by(tg_chat_id=chat_id).first()
            if clist:
                clist.is_current = True

            return edit_lists(session, chat_id, message_id)
        elif action == 'check':
            item = session.query(data_model.Item).get(list_or_item_id)
            logging.info('cheking item "%s" lists for the "%s" chat' % (item.name, chat_id))
            item.checked = not item.checked

            return edit_items(session, item.list_id, chat_id, message_id)
        elif action == 'remove':
            list_id = session.query(data_model.Item).get(list_or_item_id).list_id
            session.query(data_model.Item).filter_by(id = list_or_item_id).delete()
            session.commit()

            return edit_items(session, list_id, chat_id, message_id)

        