import time
from celery import Celery
from flask_socketio import SocketIO
import redis
import os
import sys
sys.path.append(os.getcwd())

red_conn_str = os.environ.get('MODELINSPECTOR_REDIS','redis://localhost')

red = redis.Redis.from_url(red_conn_str)
celery_app = Celery(broker = red_conn_str)
socketio   = SocketIO(message_queue = red_conn_str)


@celery_app.task
def ws_task(channel):
    import wspace_server
    wspace_server.workspace_server(channel,red,socketio)