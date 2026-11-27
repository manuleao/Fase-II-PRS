# Creates interactive HTML dashboards from real pipeline outputs.
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import html

def fmt(x,suffix=''):
    if x is None:return 'N/D'
    return f'{x:,.1f}'.replace(',','X').replace('.',',').replace('X','.')+suffix if isinstance(x,float) else f'{x:,}'.replace(',','.')+suffix

def page(title,kpi,body,notes):
    return '''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'''+html.escape(title)+'''</title><style>
    body{background:#f5f7fb;color:#172435;font-family:Arial,sans-serif;margin:0}header{padding:32px 5%;background:#122c4c;color:white}header h1{margin:0 0 9px}header p{color:#cadbed}.container{max-width:1250px;margin:24px auto;padding:0 20px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}.card{background:white;border:1px solid #dfe5ee;border-radius:13px;padding:18px;box-shadow:0 3px 7px #ccd7e020}.card b{display:block;color:#4a596c;font-size:12px;letter-spacing:.05em;text-transform:uppercase}.card span{font-size:30px;font-weight:700;color:#124976}section{background:white;border:1px solid #dfe5ee;border-radius:15px;margin:18px 0;padding:15px}.note{color:#576879;line-height:1.55;margin:16px 0 38px}.note p{margin:6px 0}footer{color:#687889;text-align:center;padding:22px}</style></head><body><header><h1>'''+html.escape(title)+'''</h1><p>Olist · base histórica brasileira 2016–2018 · fins acadêmicos</p></header><main class="container"><div class="cards">'''+kpi+'''</div>'''+body+'''<div class="note">'''+notes+'''</div></main><footer>Projeto acadêmico de BI & Analytics • Indicadores reproduzíveis no código-fonte</footer></body></html>'''

def card(title,num):return f'<div class="card"><b>{html.escape(title)}</b><span>{html.escape(str(num))}</span></div>'
def plot(fig):
    fig.update_layout(template='plotly_white',font={'family':'Arial'},height=440,margin=dict(l=60,r=35,t=55,b=75))
    return '<section>'+pio.to_html(fig,include_plotlyjs='cdn',full_html=False)+'</section>'

def make_dashboards(k,q,ml,monthly,states,reviews,dest:Path,cross=None):
    dest.mkdir(parents=True,exist_ok=True)
    stat=''.join([
       card('Entregas analisáveis',fmt(k['pedidos_com_datas_validas'])),
       card('Taxa de atraso',fmt(k['taxa_atraso_pct'],'%')),
       card('Tempo médio de entrega',fmt(k['tempo_medio_entrega_dias'],' dias')),
       card('Avaliação média',fmt(k['avaliacao_media'])),
       card('Notas 1 ou 2',fmt(k['taxa_avaliacoes_negativas_pct'],'%')) + card('Valor itens entregues (R$)',fmt(k.get('valor_itens_pedidos_entregues_brl')))])
    a=go.Figure();a.add_trace(go.Scatter(x=monthly['mes_compra'].astype(str),y=monthly['taxa_atraso'],mode='lines+markers',name='Atraso'))
    a.update_layout(title='Taxa de atrasos por mês',xaxis_title='Mês da compra',yaxis_title='Taxa (%)')
    b=go.Figure(); st=states[states.pedidos>=100].sort_values('taxa_atraso',ascending=False).head(18)
    b.add_trace(go.Bar(x=st.customer_state,y=st.taxa_atraso,name='Atraso (%)'));b.update_layout(title='Atrasos por UF (pelo menos 100 pedidos)',yaxis_title='Taxa (%)')
    c=go.Figure();c.add_trace(go.Bar(x=reviews.faixa,y=reviews.nota_media,text=reviews.nota_media.round(2),textposition='outside'));c.update_layout(title='Nota média: pedidos no prazo versus atrasados',yaxis=dict(range=[0,5.3]),yaxis_title='Nota média')
    notes=f'<p><b>Definição:</b> atraso = dia da entrega real posterior ao dia estimado. Somente pedidos entregues com datas válidas entram no denominador. Avaliações referem-se a pedidos entregues com nota válida.</p><p><b>Amostra:</b> {fmt(k["pedidos_com_datas_validas"])} entregas com datas válidas; {fmt(k["pedidos_avaliados_validos"])} delas com nota.</p><p><b>Limitação:</b> correlação entre atraso e nota não demonstra causalidade. Dados históricos, não representam o mercado atual.</p>'
    (dest/'01_desempenho_logistico.html').write_text(page('Painel executivo · Entregas e avaliações',stat,plot(a)+plot(b)+plot(c),notes),encoding='utf8')
    if ml:
        m=''.join([card('ROC AUC',fmt(ml['roc_auc'])),card('Precisão',fmt(ml['precision_threshold_05'])),card('Recall',fmt(ml['recall_threshold_05'])),card('Amostra teste',fmt(ml['teste_n']))])
        d=go.Figure(data=go.Heatmap(z=ml['matriz_confusao'],x=['Previsto no prazo','Previsto atraso'],y=['Real no prazo','Real atraso'],text=ml['matriz_confusao'],texttemplate='%{text}',colorscale='Blues'))
        d.update_layout(title='Classificação de risco de atraso · Matriz de confusão')
        note='<p>Separação temporal 80/20, sem embaralhamento. Modelo usa apenas características disponíveis na compra: valor, frete, itens, prazo prometido, mês, dia e UF. O desempenho é estimado no teste histórico, não em pedidos de 2026.</p>'
        (dest/'02_qualidade_e_predicao.html').write_text(page('Painel analítico · Qualidade e previsão',m,plot(d),note),encoding='utf8')

    if cross is not None:
        # Filtros combináveis de UF e mês para todos os indicadores, via agregações
        # pré-calculadas. Nenhum dado sintético ou API é necessário.
        import json
        rows=cross.fillna({'customer_state':'ND','mes_compra':'ND'}).to_dict('records')
        payload=json.dumps(rows,ensure_ascii=False)
        html_page="""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Olist | Indicadores por UF e mês</title>
        <style>body{margin:0;background:#f5f7fb;color:#172435;font:16px Arial,sans-serif}header{background:#122c4c;color:white;padding:28px 5%}main{max-width:1150px;margin:auto;padding:22px}select{font-size:15px;padding:9px;border:1px solid #b9c6d5;border-radius:8px;margin-right:20px}.panel{background:white;padding:22px;border-radius:14px;margin-top:16px;border:1px solid #dce5ee}.row{display:flex;gap:15px;flex-wrap:wrap}.metric{min-width:175px;flex:1;background:#f1f6fa;border-radius:10px;padding:15px}.metric small{color:#52677c}.metric strong{display:block;font-size:26px;color:#14507c;margin-top:8px}.muted{color:#586b7b}</style></head>
        <body><header><h1>Painel de entregas | filtro geográfico e temporal</h1><p>Olist, pedidos históricos de 2016–2018</p></header><main><div class="panel"><label>Estado <select id="uf"></select></label><label>Mês de compra <select id="mes"></select></label></div><div class="panel row" id="metrics"></div><div class="panel"><h2>Atrasos por mês (filtro de UF aplicado)</h2><div id="chart"></div></div><p class="muted">Indicadores calculados sobre entregas válidas; valor de item não está incluído neste painel, pois tem denominador próprio. As notas consideram apenas avaliações válidas. As proporções usam contagens, sem médias de médias.</p></main>
        <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><script>
        const ROWS=__DATA__;
        const states=[...new Set(ROWS.map(x=>x.customer_state))].sort();
        const months=[...new Set(ROWS.map(x=>x.mes_compra))].sort();
        const uf=document.getElementById('uf'),mes=document.getElementById('mes');
        const opts=(a)=>['Todos',...a].map(v=>`<option value="${v}">${v}</option>`).join('');
        uf.innerHTML=opts(states);mes.innerHTML=opts(months);
        const integer=x=>new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(x);
        const dec=x=>new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(x);
        function render(){const subset=ROWS.filter(r=>(uf.value==='Todos'||r.customer_state===uf.value)&&(mes.value==='Todos'||r.mes_compra===mes.value));
        const sum=(key)=>subset.reduce((a,r)=>a+Number(r[key]||0),0);
        const n=sum('pedidos'),a=sum('atrasadas'),d=sum('dias_entrega_total'),nc=sum('notas_qtd'),nt=sum('notas_soma'),neg=sum('notas_negativas');
        const val=[['Entregas válidas',integer(n)],['Taxa de atraso',n?dec(a/n*100)+'%':'N/D'],['Tempo médio',n?dec(d/n)+' dias':'N/D'],['Nota média',nc?dec(nt/nc):'N/D'],['Avaliações negativas',nc?dec(neg/nc*100)+'%':'N/D']];
        document.getElementById('metrics').innerHTML=val.map(x=>`<div class="metric"><small>${x[0]}</small><strong>${x[1]}</strong></div>`).join('');
        const filtered=ROWS.filter(r=>uf.value==='Todos'||r.customer_state===uf.value);const g=new Map();for(const r of filtered){const k=r.mes_compra;if(!g.has(k))g.set(k,[0,0]);const v=g.get(k);v[0]+=Number(r.pedidos);v[1]+=Number(r.atrasadas)}
        let series=[...g.entries()].sort((a,b)=>a[0].localeCompare(b[0])); if(mes.value!=='Todos')series=series.filter(x=>x[0]===mes.value);
        if(typeof Plotly!=='undefined')Plotly.react('chart',[{type:'scatter',mode:'lines+markers',x:series.map(x=>x[0]),y:series.map(x=>x[1][0]?x[1][1]/x[1][0]*100:null),line:{color:'#14669c',width:3}}],{margin:{t:20},height:360,xaxis:{title:'Mês de compra'},yaxis:{title:'Entregas atrasadas (%)'},paper_bgcolor:'white'});else document.getElementById('chart').innerText='Internet necessária para carregar o gráfico Plotly; indicadores acima funcionam localmente.';
        }
        uf.addEventListener('change',render);mes.addEventListener('change',render);render();</script></body></html>"""
        (dest/'03_explorador_uf_mes.html').write_text(html_page.replace('__DATA__',payload),encoding='utf-8')
