"""Export the actual log dashboard as SVG and HTML, without a browser."""
from __future__ import annotations
import argparse
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.dashboard import dashboard_html, dashboard_snapshot


def export_svg(data: dict) -> str:
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="950" viewBox="0 0 1500 950">', '<rect width="1500" height="950" fill="#eef3f7"/>', '<style>text{font-family:DejaVu Sans,sans-serif;fill:#17283a}.label{font-size:13px;fill:#52667a}.value{font-family:monospace;font-size:24px}.threshold{font-size:13px;fill:#ae542c}</style>']
    def text(x,y,value,cls='',size=None):
        out.append(f'<text x="{x}" y="{y}" class="{cls}"'+(f' font-size="{size}"' if size else '')+f'>{escape(str(value))}</text>')
    text(35,48,'LLM operations / Day 13 — Nguyen Ngoc Tuyen · 03010',size=27)
    text(35,80,f"Source: {data['source']} · {data['start'][:19]} → {data['end'][:19]} UTC",'label')
    text(35,103,'Last 60 minutes · Refresh 30s on /dashboard · Exported runtime chart, not a browser screenshot','label')
    labels={'p50':'P50', 'p95':'P95','p99':'P99','ttft_p95':'TTFT P95','count':'Requests','rate_per_minute':'Mean / minute','error_rate_pct':'Error rate','tool_success_rate_pct':'Retrieval success','total':'Total cost','tokens_in':'Input tokens','tokens_out':'Output tokens','mean':'Mean quality'}
    fmt=lambda v: 'N/A' if v is None else f'{v:,.6f}'.rstrip('0').rstrip('.') if isinstance(v,float) else str(v)
    for idx,p in enumerate(data['panels']):
        x,y=35+(idx%3)*485,132+(idx//3)*385
        out.append(f'<rect x="{x}" y="{y}" width="460" height="360" fill="white" stroke="#cfdae3"/>')
        text(x+20,y+32,p['title'],size=18)
        values=[(k,v) for k,v in p['values'].items() if k!='count_by_value']
        for j,(k,v) in enumerate(values):
            xx,yy=x+20+(j%2)*220,y+73+(j//2)*57
            text(xx,yy,fmt(v),'value');text(xx,yy+20,f"{labels[k]} ({'requests' if k=='count' else p['unit']})",'label')
        key={'latency':'latency_p95','traffic':'traffic','errors':'error_rate_pct','cost':'cost'}.get(p['id'])
        chart_vals=[r[key] for r in data['timeline']] if key else [v for _,v in values]
        threshold=p['threshold']['value'] if p['id']!='cost' else None
        ymax=max([v for v in chart_vals if v is not None]+[threshold or 0, .000001])*1.1
        left,right,top,bottom=x+48,x+435,y+205,y+285
        scale=lambda v:bottom-v/ymax*(bottom-top)
        out.append(f'<path d="M {left} {top} V {bottom} H {right}" fill="none" stroke="#cfdae3"/>')
        text(x+10,top+3,fmt(ymax),'label');text(x+20,bottom,'0','label')
        if threshold is not None:out.append(f'<path d="M {left} {scale(threshold)} H {right}" stroke="#ae542c" stroke-dasharray="5 3"/>')
        # Missing observations create gaps, rather than invented measurements.
        segment=[]
        for j,v in enumerate(chart_vals+[None]):
            if v is None:
                if segment:out.append(f'<polyline points="{" ".join(segment)}" stroke="#17679a" stroke-width="2" fill="none"/>');segment=[]
            else:
                px=left+j/max(1,len(chart_vals)-1)*(right-left)
                segment.append(f'{px},{scale(v)}')
                out.append(f'<circle cx="{px}" cy="{scale(v)}" r="3" fill="#17679a"/>')
        if key:
            text(left,bottom+19,data['timeline'][0]['minute'][11:16],'label');text(right-40,bottom+19,data['timeline'][-1]['minute'][11:16],'label')
        else:
            text(left,bottom+19,' / '.join(labels[k] for k,_ in values),'label')
        text(x+20,y+328,f"Threshold: {p['threshold']['aggregation']} {'≤' if p['threshold']['operator']=='lte' else '≥'} {p['threshold']['value']} {p['unit']}",'threshold')
        if p['id']=='errors':text(x+20,y+348,f"Error breakdown: {p['values']['count_by_value'] or 'none'} · retrieval target ≥ 90%",'label')
        elif key:text(x+20,y+348,f"Chart: {key} per minute · UTC time → {p['unit']}",'label')
    text(35,927,'Cost = lab estimates · Quality = heuristic proxy · Match correlation ID with Langfuse for request investigation','label')
    out.append('</svg>')
    return '\n'.join(out)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot',type=Path,help='Use captured runtime JSON instead of current logs')
    args=parser.parse_args()
    data=json.loads(args.snapshot.read_text()) if args.snapshot else dashboard_snapshot()
    output=ROOT/'submission/evidence'
    output.mkdir(parents=True,exist_ok=True)
    (output/'cp2-dashboard-data.json').write_text(json.dumps(data,indent=2)+'\n')
    (output/'11-dashboard-overview.html').write_text(dashboard_html(data))
    (output/'11-dashboard-overview.svg').write_text(export_svg(data))
    print(f'Exported six panels: {data["start"]} → {data["end"]}')


if __name__=='__main__':main()
