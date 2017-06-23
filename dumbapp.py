from gevent import monkey
monkey.patch_all()

import json
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from tasks import ws_task, red
import os
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data'
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, message_queue ='redis://')




@app.route('/')
def home():
    return 'Hello World'


@app.route('/<modelid>')
def modelview(modelid):
    plotdata = json.load(open('what.json'))
    return render_template('home.html', modelid = modelid, plotdata = plotdata)


def upload_key(sid):
    return 'upload:{}'.format(sid)

@socketio.on('uploadstart')
def upload_start(jsondata):
    print 'session id',request.sid
    directory = 'here'
    if os.path.exists(directory):
        shutil.rmtree(directory)
    red.set(upload_key(request.sid), directory)
    return {'next': directory}

@socketio.on('connect')
def test_connect():
    print('Client connected: ', request.sid)
    emit('sid',{'data': request.sid})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected: ',request.sid)
    if red.exists(upload_key(request.sid)):
        red.delete(upload_key(request.sid))

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/upload_file', methods = ['POST'])
def upload_file():
    target_filename = os.path.join(app.config['UPLOAD_FOLDER'],red.get(upload_key(request.args['sid'])),request.args['fullpath'])
    print target_filename
    if not os.path.exists(os.path.dirname(target_filename)):
        os.makedirs(os.path.dirname(target_filename))
    request.files['file'].save(target_filename)

    print request.args['fullpath'],request.files['file']
    return 'ok'

if __name__ == '__main__':
    socketio.run(app)