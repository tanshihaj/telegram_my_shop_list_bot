
class TelegramApi:
    def __init__(self, token, host_port=None):
        self.host_port = host_port if host_port else 'https://api.telegram.org'
        self.token = token

        self.url_tmpl = self.host_port + '/bot{token}/{method}'

