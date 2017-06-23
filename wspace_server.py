import json
import copy
import glob
import make_vega
import ROOT
import os

def callback_update_data(state,input_data,socketio):
    ws = state['ws']
    new_data = make_vega.make_new_vega_data(ws, 'channel1', input_data['pars'])
    emit = new_data[0]['values']
    print 'emitting!'
    socketio.emit('wsevent', {"sid": input_data['sid'], 'new_data':  emit} )

def callback_init_vega(state,input_data,socketio):
    ws = state['ws']
    print 'emitting init state based on workspace: ', ws
    socketio.emit('wsinit',{"sid": input_data['sid'], "vega_spec": make_vega.make_vega_spec(ws,'channel1')})
    print 'emitted'


def init_root(state,input_data):
    globexpr = 'data/{modelid}/results/*combined*.root'.format(modelid = input_data['modelid'])

    print 'looking for', globexpr
    filename = glob.glob(globexpr)[0]

    f = ROOT.TFile.Open(filename)

    ws = f.Get('combined')
    state['f'] = f
    state['ws'] = ws
    print 'opened file!'

callbacks = {'update_data': callback_update_data, 'init_vega': callback_init_vega}

def workspace_server(channel,red,socketio):
    state = {'ws': None}
    init_root(state,{'modelid': channel})

    print 'workspace set.. ready to listen...', state
    print 'subscribe to',channel

    pubsub = red.pubsub()
    pubsub.subscribe([channel])
    for item in pubsub.listen():
        if item['type'] == 'message':
            print 'received', item, type(item)
            input_data = json.loads(item['data'])
            cb = callbacks.get(input_data['event'])
            if cb: cb(state,input_data,socketio)

