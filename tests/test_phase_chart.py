"""Verify the shared browser renderer's scale and missing-value behavior."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js is unavailable')
def test_phase_chart_shared_scale_units_and_gaps():
    source = Path(__file__).resolve().parents[1] / 'docs/javascripts/phase-chart.js'
    script = r'''
const fs = require('fs');
class Element {
  constructor(tag) { this.tag = tag; this.attrs = {}; this.children = []; }
  setAttribute(k,v) { this.attrs[k] = v; }
  append(...children) { this.children.push(...children); }
}
global.document = {createElement: t=>new Element(t), createElementNS: (_,t)=>new Element(t)};
global.window = {};
eval(fs.readFileSync(process.argv[1], 'utf8'));
const {makeChart,displayUnit} = window.LocoHubPhaseChart;
const signal = {label:'Knee',unit:'rad'};
const phase = [0,25,50,75,100];
const stats = {mean:[0,Math.PI/2,null,Math.PI/4,0],sd:[.1,.1,null,.1,.1],n:[1,1,0,1,1]};
const chart = makeChart(phase,stats,signal,true,540,[0,180]);
const line = chart.children.find(n=>n.attrs.class==='preview-line aggregate-mean');
const other = makeChart(phase,{...stats,mean:[0,Math.PI/2,null,Math.PI,0]},signal,false,540,[0,180]);
const otherLine = other.children.find(n=>n.attrs.class==='preview-line aggregate-mean');
const boxed = makeChart(phase,stats,signal,false,540,[0,180],[{phase:25,sample_phase:25,min:0,max:Math.PI/2}]);
const box = boxed.children.find(n=>n.attrs.class==='phase-range-box');
console.log(JSON.stringify({box:box.attrs,factor:displayUnit('rad').factor,path:line.attrs.d,
  otherPath:otherLine.attrs.d, bands:chart.children.filter(n=>n.attrs.class==='aggregate-band').length,
  yTicks:chart.children.filter(n=>n.tag==='text' && n.attrs['text-anchor']==='end').map(n=>n.textContent)}));
'''
    result = subprocess.run(['node', '-e', script, str(source)], check=True, capture_output=True, text=True)
    chart = json.loads(result.stdout)
    assert chart['factor'] == pytest.approx(180 / 3.141592653589793)
    assert chart['bands'] == 0  # One contributor cannot define an SD band.
    assert chart['path'].count('M') == 2  # Never join across missing phase values.
    assert 'L170.00,127.00' in chart['path']  # 90 degrees halfway up the shared 0..180 scale.
    assert chart['path'].split('M')[1] == chart['otherPath'].split('M')[1]
    assert '0' in chart['yTicks'] and '150' in chart['yTicks']

    assert chart['box']['x'] == 166  # Box centered at the actual sample.
    assert chart['box']['y'] == 127
    assert chart['box']['height'] == 99  # Exact 0..90-degree bound on a 0..180 scale.
