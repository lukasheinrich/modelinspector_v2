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

def vega_data_name(channel):
    return 'obsdata_{}'.format(channel)

def vega_mc_name(channel):
    return 'all_samples_{}'.format(channel)

def make_scales(channel):
    return [{
        "range": "width",
        "type": "linear",
        "name": "x",
        "domain": {
          "field": "bin_center",
          "data": vega_mc_name(channel)
        }
      }, {
        "range": "height",
        "type": "linear",
        "name": "y",
        "domain":  {
          "field": "y",
          "data": vega_data_name(channel)
        }
      }
    ]

def make_global_scales(ws):
    samples = sum([hftools.utils.samples(ws,c) for c in get_channels(ws)],[])
    colors = zip(*zip(samples,itertools.cycle(["red", "steelblue", "purple"])))[1]
    return [{
        "name": "color",
        "type": "ordinal",
        "domain": samples,
        "range": colors
      },
    ]


def make_group_marks(channel):
  return {
    "type": "group",
    "encode": {
      "enter": {
        "height": {"value": 200}
      }
    },
    "axes": axes,
    "scales": make_scales(channel),
    "marks": make_marks(channel)
  }


def make_marks(channel):
  return [{
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
        "xc": {
          "field": "bin_center",
          "scale": "x"
        },
        "width": {
          "scale": "x",
          "field": "bin_width"
        }
      }
    },
    "type": "rect",
    "from": {
      "data": vega_mc_name(channel)
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
            },
            "fill": {
                "value": "black"
            }
        }
    },

    "type": "symbol",
    "from": {
        "data": vega_data_name(channel)
        }
}
]

def histo2bar(histo):
    data = np.array([(histo.GetBinCenter(i),histo.GetBinContent(i),histo.GetBinWidth(i)) for i in range(1,1+histo.GetNbinsX())])
    return data

def histo2scatter(histo):
    data = np.array([(histo.GetBinCenter(i),histo.GetBinContent(i)) for i in range(1,1+histo.GetNbinsX())])
    return data

def extract_for_vega(ws,channel,parvalues):


    last_data_mc = {}
    last_data_data = []

    for k,v in parvalues.iteritems():
        ws.var(k).setVal(v)


    data = hftools.utils.extract_data(ws,channel,'x')
    mcnames  = hftools.utils.samples(ws,channel)
    mchistos = [hftools.utils.extract(ws,channel,'x',name) for name in mcnames]

    bottom = None
    for i,(mc,name) in enumerate(zip(mchistos,mcnames)):
        bardata = histo2bar(mc)
        last_data_mc[name] = bardata.tolist()
        bottom = bardata[:,1] if i==0 else bottom + bardata[:,1]
    
    scatdata = histo2scatter(data)
    last_data_data = scatdata.tolist()
    
    for h in [data] + mchistos:
      h.Delete()
    return last_data_mc, last_data_data
    

def get_parameters(ws, model_config = 'ModelConfig'):
    import itertools
    config = ws.obj(model_config)
    nuis_pars = config.GetNuisanceParameters()

    if nuis_pars:
      it = nuis_pars.fwdIterator()
      nuis = list(itertools.takewhile(lambda x: x, (it.next() for i in itertools.repeat(True))))
    else:
      nuis = []

    it = config.GetParametersOfInterest().fwdIterator()
    pois = list(itertools.takewhile(lambda x: x, (it.next() for i in itertools.repeat(True))))
    return pois, nuis

def get_channels(ws):
    ws.allVars().getSize()
    it = ws.allVars().fwdIterator()
    return [x.GetName().split('_')[-1] for x in list(it.next() for i in range(ws.allVars().getSize())) if  str(x.GetName()).startswith('obs_')]

def make_new_vega_data_values(ws,channel,pars):
    mc_data, data_data = extract_for_vega(ws,channel,pars)

    chained_data = list(itertools.chain(*[[dict(zip(['sample','bin_center','bin_content','bin_width'],[k]+d)) for d in v]
        for k,v in mc_data.iteritems()
    ]))
    return  chained_data, [dict(zip(['x','y'],d)) for d in data_data]

def make_new_vega_data(ws,channel,pars):
    mcdata, obsdata = make_new_vega_data_values(ws,channel,pars)

    return [{
        'name': vega_mc_name(channel),
        'values': mcdata,
        'transform': [
            {
              "type": "stack",
              "groupby": ["bin_center"],
              "sort": {"field": "sample"},
              "field": "bin_content"
            }
        ]},{
        'name': 'obsdata_{}'.format(channel),
        'values': obsdata
    }]

def make_signals(ws):
    return [{
        'name': v.GetName(),
        'value': v.getVal(),
        'bind': {'input': 'range', 'min': v.getMin(), 'max': v.getMax(), 'step': (v.getMax()-v.getMin())/ 100.}
      }
      for v in sum(get_parameters(ws),[])
    ]

def make_vega_spec(ws,channel):
    channels = get_channels(ws)


    signals = make_signals(ws)
    data    = sum([make_new_vega_data(ws,c,{}) for c in channels],[])
    scales  = make_global_scales(ws)
    vega_spec = {
      "$schema": "https://vega.github.io/schema/vega/v3.0.json",
      "signals": signals,
      "scales": scales,
      "height": 200,
      "layout": {
        "columns": 1
      },
      "padding": 5,
      "width": 500,
      "marks": [make_group_marks(c) for c in channels],
      "data": data
    }

    return vega_spec

def vega_data_by_channel(ws,pars):
    updated_data = {}
    for c in get_channels(ws):
        mcdata, obsdata = make_new_vega_data_values(ws,c,pars)
        updated_data[vega_mc_name(c)]   = mcdata
        updated_data[vega_data_name(c)] = obsdata
    return updated_data


import sys
def main():
    f = ROOT.TFile.Open(sys.argv[1])
    ws = f.Get('combined')


    return make_vega_spec(ws,'channel1')


if __name__ == '__main__':
    data = main()
    json.dump(data,open('what.json','w'))