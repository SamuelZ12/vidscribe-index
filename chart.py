"""Standalone SVG charts with marginal item-bootstrap intervals."""
from html import escape

COLORS = ('#007081','#a14717','#6347a6','#296a37','#922c62')


def plot(sets, chance, axis, label):
    points = sorted([(s[axis],s['accuracy'],name) for name,s in sets.items() if s[axis]],
                    key=lambda p:(p[0][0],-p[1][0]))
    if not points:
        return '<p>Usage unavailable.</p>'
    xmax = max(p[0][2] for p in points)*1.12 or 1
    ymax = min(1,max([chance]+[p[1][2] for p in points])+.08)
    x = lambda value: 60+600*value/xmax
    y = lambda value: 288-248*value/ymax
    svg = [f'<svg viewBox="0 0 820 360" role="img" aria-label="Accuracy versus {label}"><title>Accuracy versus {label}</title>']
    for i in range(6):
        tx,ty=x(i*xmax/5),y(i*ymax/5)
        svg += [f'<path d="M60 {ty} H660" stroke="#dee4e7"/>',
                f'<text x="51" y="{ty+4}" text-anchor="end">{i*ymax/5:.0%}</text>',
                f'<text x="{tx}" y="309" text-anchor="middle">{i*xmax/5:.3g}</text>']
    svg += [f'<text x="60" y="21">Accuracy</text><text x="360" y="343" text-anchor="middle">{label}</text>',
            f'<path d="M60 {y(chance)} H660" stroke="#636363" stroke-dasharray="4 4"/>',
            f'<text x="669" y="{y(chance)+4}">Guessing {chance:.1%}</text>']
    frontier = []
    best = -1
    for cost,acc,_ in points:
        if acc[0] > best:
            frontier.append(f'{x(cost[0])},{y(acc[0])}')
            best = acc[0]
    svg.append('<polyline points="'+' '.join(frontier)+'" fill="none" stroke="#263c47" stroke-width="2"/>')
    legend=[]
    for index,(cost,acc,name) in enumerate(points,1):
        cx,cy=x(cost[0]),y(acc[0])
        color=COLORS[(index-1)%len(COLORS)]
        svg.append(f'<g><title>{escape(name)}: {acc[0]:.2%}, {cost[0]:.4g}</title>'
                   f'<path d="M{x(cost[1])} {cy} H{x(cost[2])} M{cx} {y(acc[1])} V{y(acc[2])}" stroke="{color}" stroke-width="2"/>'
                   f'<circle cx="{cx}" cy="{cy}" r="9" fill="{color}"/><text x="{cx}" y="{cy+4}" text-anchor="middle" '
                   f'style="fill:white">{index}</text></g>')
        legend.append(f'<span style="color:{color}">{index}. {escape(name)} ({cost[0]:.4g}, {acc[0]:.1%})</span>')
    return ''.join(svg)+'</svg><footer>'+' &nbsp; '.join(legend)+'</footer>'


def charts(sets,chance):
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Video-Index development frontier</title><style>body{font:16px system-ui;color:#172c36;max-width:900px;'
            'margin:3rem auto;padding:0 1rem}section{margin:2.5rem 0}svg{width:100%;background:#fafcfc}svg text{font:13px system-ui;'
            'fill:#263c47}footer{padding:.6rem}h2{font-size:1.25rem}</style><h1>Video-Index development frontier</h1>'
            '<p>Higher accuracy and lower cost are better. The line connects undominated means. Bars show 95% item-bootstrap intervals.</p>'
            + ''.join('<section><h2>'+label+'</h2>'+plot(sets,chance,axis,label)+'</section>'
                      for axis,label in [('dollars','API dollars per question'),('seconds','Seconds per question')])+'</html>')
