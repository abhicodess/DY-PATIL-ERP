workers = 2
worker_class = 'gevent'
bind = '0.0.0.0:8000'
timeout = 120
keepalive = 5
accesslog = '-'
errorlog = '-'
loglevel = 'info'

import os
reload = os.environ.get("DEBUG", "false").lower() == "true"
