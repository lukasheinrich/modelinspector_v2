from gevent import monkey
monkey.patch_all()

import os
import json
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from tasks import ws_task, red, red_conn_str

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

socketio = SocketIO(app, message_queue = red_conn_str)

@app.route('/')
def home():
    return 'Hello World'


@app.route('/<modelid>')
def modelview(modelid):
    return render_template('home.html', modelid = modelid)


@app.route('/<modelid>/getdata', methods = ['POST'])
def model_getdata(modelid):
    print 'json: ',request.json
    import time
    time.sleep(2.0)
    mu = request.json['mu']
    return jsonify([
        {"u": 1,  "v": mu*1}, {"u": 2,  "v": mu*2}
    ])

def wskey(modelid):
    return 'workspaces:{}'.format(modelid)


@socketio.on('wstart')
def handle_event(jsondata):
    print('received json on wsstart: ' + str(jsondata))
    if not red.exists(wskey(jsondata['data'])):
        result = ws_task.delay(jsondata['data'])
        red.set(wskey(jsondata['data']),result.id)
        print 'started task', result.id, wskey(jsondata['data'])
    else: 
        print 'task already exists',red.get(wskey(jsondata['data']))

    return {'sid': request.sid}

@socketio.on('wsupdate')
def ws_update(jsondata):
    print('received json on wsupdate: ' + str(jsondata))
    red.publish(jsondata['data'],json.dumps(jsondata))


@socketio.on('connect')
def test_connect():
    print('Client connected: ', request.sid)

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    socketio.run(app, host = '0.0.0.0')