import numpy as np
import hftools.utils
from vega import Vega
import ROOT

def histo2bar(histo):
    data = np.array([(histo.GetBinCenter(i),histo.GetBinContent(i),histo.GetBinWidth(i)) for i in range(1,histo.GetNbinsX())])
    return data

def histo2scatter(histo):
    data = np.array([(histo.GetBinCenter(i),histo.GetBinContent(i)) for i in range(1,histo.GetNbinsX())])
    return data

def make_mc_marks(name,color):
    marks = {
          "type": "rect",
          "from": {"data": name},
          "properties": {
            "enter": {
              "xc": {"scale": "x", "field": "x"},
              "width": {"scale": "x", "band": True},
              "y": {"scale": "y", "field": "bottom"},
              "y2": {"scale": "y", "field": "y"},
            },
            "update": {
              "fill": {"value": color}
            },
            "hover": {
              "fill": {"value": "orange"}
            }
          }
    }
    return marks

def make_obsdata_data_marks(name,data_source):
    data  = {'name':name,'values': [{'x': d[0], 'y': d[1]} for d in data_source]}
    marks = {
              "type": "symbol",
              "from": {"data": name},
              "properties": {
                "enter": {
                  "x": {"scale": "x", "field": "x"},
                  "y": {"scale": "y", "field": "y"},
                },
                "update": {
                  "fill": {"value": 'black'}
                },
                "hover": {
                  "fill": {"value": "orange"}
                }
              }
        }
    return data,marks


def get_data(ws,channel,obs,samples):
    hdata = hftools.utils.extract_data(ws,'channel1','x')

    mc_histos = [hftools.utils.extract(ws,channel,obs,s) for s in samples]

    def barify(mchistos,data):
        bardatas = []
        for i,mc in enumerate(mchistos):
            bardata = histo2bar(mc)
            if i == 0:
                bottom = np.zeros(bardata.shape[0])
            bardatas += [(bottom,bardata)]
            bottom = bottom + bardata[:,1]

        scatdata = histo2scatter(data)
        return bardatas,scatdata

    data = barify(mc_histos,hdata)
    for h in [hdata] + mc_histos:
        h.Delete()
    
    return data

def mk_vega(ws,**parvalues):
    for k,v in parvalues.iteritems():
        ws.var(k).setVal(v)

    samples = ['background2','background1','signal']
    colors = ['blue','red','green']
    data = get_data(ws,'channel1','x',samples)

    all_data  = []
    all_marks = []
    for name,mc,color in zip(samples,data[0],colors):
        bottom, mcdata = mc
        all_data += [{
            'name': name,
            'values': [{'x': row[0], 'y': b+row[1],'bottom': b, 'w': row[2]} for b,row in zip(bottom,mcdata)]
        }]
        all_marks += [
            make_mc_marks(name,color)
        ]

    obsdata_marks = make_obsdata_data_marks('obsdata',data[1])
    all_data += [obsdata_marks[0]]
    all_marks += [obsdata_marks[1]]
    
    vega_figure = {
      "width": 600,
      "height": 400,
      "padding": {"top": 10, "left": 30, "bottom": 30, "right": 10},
      "data": all_data,
      "scales": [
        {
          "name": "x",
          "type": "ordinal",
          "range": "width",
          "domain": {"data": "obsdata", "field": "x"}
        },
        {
          "name": "y",
          "type": "linear",
          "range": "height",
          "domain": {"data": "obsdata", "field": "y"},
          "nice": True
        }
      ],
      "axes": [
        {"type": "x", "scale": "x"},
        {"type": "y", "scale": "y"}
      ],
      "marks": all_marks
    }
    return vega_figure

import os
def get_workspace(rootdir,prefix,workspace,measurement):
	f = ROOT.TFile.Open(os.path.join(rootdir,'results','{}_{}_{}_model.root'.format(prefix,workspace,measurement)))
	ws = f.Get('combined')
	return ws