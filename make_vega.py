import hftools
import ROOT
import numpy as np
import hftools.utils

import json
import itertools

axes = [{
    "scale": "x",
    "orient": "bottom"
  }, {
    "scale": "y",
    "orient": "left"
}]


marks = [{
    "encode": {
        "update": {
          "fillOpacity": {"value": 1}
        },
        "hover": {
          "fillOpacity": {"value": 0.5}
        },
      "enter": {
        "fill": {
            "scale": "color",
            "field": "sample"
        },
        "y2": {
          "scale": "y",
          "field": "y1"
        },
        "y": {
          "field": "y0",
          "scale": "y"
        },
        "x": {
          "field": "bin_center",
          "scale": "x"
        },
        "width": {
          "band": True,
          "scale": "x"
        }
      }
    },
    "type": "rect",
    "from": {
      "data": "all_samples"
    }
},{
    "encode": {
        "enter": {
            "y": {
                "field": "y",
                "scale": "y"
            },




            "x": {
                "field": "x",
                "scale": "x",
                "mult": 0.5,
                "band": True
            },
            "fill": {
                "value": "black"
            }
        }
    },

    "type": "symbol",
    "from": {
        "data": "obsdata"
    }
}
]

def histo2bar(histo):
    data = np.array([(histo.GetBinCenter(i),histo.GetBinContent(i),histo.GetBinWidth(i)) for i in range(1,histo.GetNbinsX())])
    return data

def histo2scatter(histo):
    data = np.array([(histo.GetBinCenter(i),histo.GetBinContent(i)) for i in range(1,histo.GetNbinsX())])
    return data

def extract_for_vega(ws,parvalues):


    last_data_mc = {}
    last_data_data = []

    for k,v in parvalues.iteritems():
        ws.var(k).setVal(v)
    hdata = hftools.utils.extract_data(ws,'channel1','x')
    hsignal = hftools.utils.extract(ws,'channel1','x','signal')
    hbackground1 = hftools.utils.extract(ws,'channel1','x','background1')
    hbackground2 = hftools.utils.extract(ws,'channel1','x','background2')
    
    mcnames = ['background2','background1','signal']
    mchistos, data = [hbackground2,hbackground1,hsignal],hdata

    
    bottom = None
    for i,(mc,name) in enumerate(zip(mchistos,mcnames)):
        bardata = histo2bar(mc)
        last_data_mc[name] = bardata.tolist()
        bottom = bardata[:,1] if i==0 else bottom + bardata[:,1]
    
    scatdata = histo2scatter(data)
    last_data_data = scatdata.tolist()
    
    hdata.Delete()
    hsignal.Delete()
    hbackground1.Delete()
    hbackground2.Delete()
    return last_data_mc, last_data_data
    

def get_parameters(ws, model_config = 'ModelConfig'):
    import itertools
    config = ws.obj(model_config)
    it = config.GetNuisanceParameters().fwdIterator()
    nuis = list(itertools.takewhile(lambda x: x, (it.next() for i in itertools.repeat(True))))

    it = config.GetParametersOfInterest().fwdIterator()
    pois = list(itertools.takewhile(lambda x: x, (it.next() for i in itertools.repeat(True))))
    return pois, nuis


def make_new_vega_data(ws,pars):
    mc_data, data_data = extract_for_vega(ws,pars)

    chained_data = list(itertools.chain(*[[dict(zip(['sample','bin_center','bin_content','bin_width'],[k]+d)) for d in v]
        for k,v in mc_data.iteritems()
    ]))

    newvega_data = [{
        'name': 'all_samples',
        'values': chained_data,
        'transform': [
            {
              "type": "stack",
              "groupby": ["bin_center"],
              "sort": {"field": "sample"},
              "field": "bin_content"
            }
        ]},{
        'name': 'obsdata',
        'values': [dict(zip(['x','y'],d)) for d in data_data]
    }]
    return newvega_data


def make_signals(ws):
    return [{
        'name': v.GetName(),
        'value': v.getVal(),
        'bind': {'input': 'range', 'min': v.getMin(), 'max': v.getMax(), 'step': (v.getMax()-v.getMin())/ 100.}
      }
      for v in sum(get_parameters(ws),[])
    ]


def make_scales(ws,channel):
    samples = hftools.utils.samples(ws,'channel1')
    colors = zip(*zip(samples,itertools.cycle(["steelblue", "red", "purple"])))[1]
    return [{
        "range": "width",
        "type": "band",
        "name": "x",
        "domain": {
          "field": "bin_center",
          "data": "all_samples"
        }
      }, {
        "range": "height",
        "type": "linear",
        "name": "y",
        "domain":  {
          "field": "y",
          "data": "obsdata"
        }
      }, {
        "name": "color",
        "type": "ordinal",
        "domain": samples,
        "range": colors
      },
    ]


def make_vega_spec(ws):
    signals = make_signals(ws)
    data    = make_new_vega_data(ws,{'mu': 1.0})
    scales  = make_scales(ws,'channel1')
    vega_spec = {
      "$schema": "https://vega.github.io/schema/vega/v3.0.json",
      "signals": signals,
      "scales": scales,
      "axes": axes,
      "height": 400,
      "padding": 5,
      "width": 500,
      "marks": marks,
      "data": data
    }

    return vega_spec



def main():
    f = ROOT.TFile.Open('data/testws/results/example_combined_Meas1_model.root')
    ws = f.Get('combined')


    return make_vega_spec(ws)


if __name__ == '__main__':
    data = main()
    json.dump(data,open('what.json','w'))