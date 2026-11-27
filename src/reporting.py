"""Populate the official PUCRS Word and PowerPoint templates from actual outputs.
No synthetic/fabricated numeric results are ever inserted into the final artifacts.
"""
from pathlib import Path
import json, os, subprocess
from docx import Document
from docx.shared import Inches as DI, Pt as DPt, RGBColor as DRGB
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.text import MSO_AUTO_SIZE
from PIL import Image

STUDENT='Manoela Teixeira Leão Matos'
NAVY=RGBColor(25,57,91);BLUE=RGBColor(40,107,163);GRAY=RGBColor(84,100,116);LIGHT=RGBColor(237,244,250)

def text_at(p,s):
    p.clear(); p.add_run(s);return p

def remove_paragraph(p):p._element.getparent().remove(p._element)

def kpis_definitions():
    return [
    ('Pedidos entregues', 'Contagem distinta de order_id em status delivered', 'orders.order_id, order_status', 'Volume de entregas realizadas'),
    ('Taxa de atraso', '(Entregas após a data prevista / entregas válidas) × 100', 'orders: datas real e estimada', 'Monitorar pontualidade logística'),
    ('Tempo médio de entrega', 'Média dos dias entre compra e entrega', 'orders: datas de compra e entrega', 'Acompanhar tempo do serviço'),
    ('Nota média', 'Média de review_score nas entregas válidas avaliadas', 'reviews.review_score', 'Medir a experiência do cliente'),
    ('Avaliações negativas', '(Notas 1–2 / entregas válidas avaliadas) × 100', 'reviews.review_score', 'Detectar insatisfação'),
    ('Valor dos itens entregues (R$)', 'Soma de price de todos os itens dos pedidos com status delivered', 'items.price e orders.order_status', 'Dimensionar valor vendido em itens'),
    ]

def build_report(template,out,architecture,metrics=None,model=None,repo_url=None):
    doc=Document(template)
    ps=doc.paragraphs
    text_at(ps[3],f'Nome do estudante: {STUDENT}')
    remove_paragraph(ps[4])
    text_at(ps[6], 'Os indicadores foram definidos com denominadores explícitos, tratamento de duplicidades por pedido e análise exclusiva das entregas com datas válidas. O recorte da base é histórico (2016–2018) e as fontes são os CSVs oficiais da Olist.')
    table=doc.add_table(rows=1,cols=4)
    table.style='Table Grid'
    for j,label in enumerate(['KPI','Cálculo','Fonte','Aplicação']):table.rows[0].cells[j].text=label
    for row in kpis_definitions():
        cells=table.add_row().cells
        for j,val in enumerate(row):cells[j].text=val
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:r.font.size=DPt(8)
    for c in table.rows[0].cells:
        for p in c.paragraphs:
            for r in p.runs:r.bold=True
    # Move table immediately after section-1 description, preserving official headings.
    ps[6]._p.addnext(table._tbl)
    text_at(ps[8], 'Ferramentas: Python e pandas (coleta, limpeza, integração e validação); scikit-learn (previsão de risco de atraso); Plotly (dashboards interativos em HTML); Google Colab (execução); GitHub (publicação e documentação). As tabelas orders, customers, items e reviews são vinculadas por customer_id e order_id, após consolidar itens e avaliações em uma linha por pedido. Dados processados e indicadores são exportados em CSV e JSON para auditoria.')
    ps[9].clear();ps[9].add_run().add_picture(str(architecture),width=DI(6.1))
    intro=('A solução foi desenvolvida em código reproduzível e testada com dados sintéticos para validar o funcionamento, sem confundir testes com resultados reais. '
           'A geração dos KPIs definitivos, dos dashboards e da avaliação preditiva requer executar o notebook com a base original. '
           'A classificação de risco de atraso usa regressão logística, características disponíveis na compra e separação temporal 80%/20%.')
    if metrics:
        intro='A execução com os arquivos históricos da Olist gerou os indicadores e dashboards, com validação das chaves e dos registros. '
        intro+=f"Foram avaliadas {metrics['pedidos_com_datas_validas']:,} entregas com datas válidas, com taxa de atraso de {metrics['taxa_atraso_pct']:.2f}%, tempo médio de {metrics['tempo_medio_entrega_dias']:.2f} dias, nota média de {metrics['avaliacao_media']:.2f} e {metrics['taxa_avaliacoes_negativas_pct']:.2f}% de avaliações negativas. "
        if model: intro+=f"No teste temporal da regressão logística, o ROC AUC foi {model['roc_auc']:.3f} e o recall {model['recall_threshold_05']:.3f}."
    text_at(ps[11],intro)
    text_at(ps[12],'• Script de obtenção, tratamento e integração: src/pipeline.py; auditoria: results/qualidade_dados.json.')
    text_at(ps[13],'• Dashboards interativos: results/dashboards/01_desempenho_logistico.html, 02_qualidade_e_predicao.html e 03_explorador_uf_mes.html (filtros por UF e mês).')
    text_at(ps[14],'• Documentação e dicionário de dados: README.md e docs/dicionario_dados.md; validação: tests/test_pipeline.py.')
    text_at(ps[15],f'Link do GitHub: {repo_url}' if repo_url else 'LINK DO GITHUB: [INSERIR DEPOIS DE PUBLICAR O REPOSITÓRIO]')
    doc.add_paragraph('3.1 Relação com o planejamento da Fase 1',style=None).runs[0].bold=True
    doc.add_paragraph('O problema da Fase 1 foi verificar se entregas atrasadas tendem a receber notas menores e como garantir indicadores confiáveis. A hipótese H1 é analisada por auditoria das chaves, quantidade de registros descartados e contagem distinta por pedido após agregação dos itens; a hipótese H2 é avaliada pela comparação das notas médias de entregas atrasadas versus no prazo, acompanhada de intervalo de confiança e teste de Welch. Os objetivos originais de filtro geográfico e temporal e mensuração do valor dos itens são contemplados pelos painéis e indicadores. Esta análise não demonstra causalidade.')
    doc.add_paragraph('3.2 Fundamentação aplicada das aulas 6 a 10',style=None).runs[0].bold=True
    doc.add_paragraph('A solução utiliza a distinção entre dimensões e medidas e a construção de painéis (aula 6), a metodologia de mineração CRISP-DM — entendimento do negócio, compreensão dos dados, preparação, modelagem, avaliação e apresentação (aula 7), a possibilidade de publicação de painéis estáticos no GitHub Pages (aula 8), a lógica de indicadores e relatórios interativos (aula 9) e a aprendizagem supervisionada para classificar o risco de atraso (aula 10). A implementação adotou Python/Google Colab e Plotly, ferramentas permitidas pelo enunciado; Power BI permanece alternativa de consumo dos CSVs exportados.')
    doc.add_paragraph('4. Resultados e análise',style=None).runs[0].bold=True
    if metrics:
        doc.add_paragraph(f"Dos {metrics['pedidos_com_datas_validas']:,} pedidos com entregas analisáveis, {metrics['entregas_atrasadas']:,} chegaram após o dia prometido ({metrics['taxa_atraso_pct']:.2f}%). A avaliação média é de {metrics['avaliacao_media']:.2f} e {metrics['taxa_avaliacoes_negativas_pct']:.2f}% das notas são 1 ou 2, considerando somente entregas com notas disponíveis.")
        doc.add_paragraph(f"Valor total dos itens em pedidos entregues: R$ {metrics['valor_itens_pedidos_entregues_brl']:,.2f}. O valor é soma de preços de itens, sem frete, não faturamento líquido.")
        diff=metrics.get('diferenca_nota_atrasados_menos_prazo')
        if diff is not None:
            doc.add_paragraph(f'A diferença de nota média entre atrasados e entregues no prazo é de {diff:+.3f} ponto(s). O resultado descreve associação, sem estabelecer causalidade.')
            if metrics.get('h2_diferenca_nota_ic95'):
                ci=metrics['h2_diferenca_nota_ic95']
                doc.add_paragraph(f'H2 — diferença de notas (atrasadas − no prazo): IC95% [{ci[0]:+.3f}; {ci[1]:+.3f}], p do teste t de Welch={metrics["h2_teste_welch_p_valor"]:.5g}. As notas de 1 a 5 foram tratadas como escala numérica; a comparação é exploratória.')
        if model:doc.add_paragraph(f"Na análise preditiva, treinou-se um classificador de regressão logística com dados ordenados pela compra e teste nos últimos 20% dos registros válidos. ROC AUC={model['roc_auc']:.3f}; precisão={model['precision_threshold_05']:.3f}; recall={model['recall_threshold_05']:.3f}; F1={model['f1_threshold_05']:.3f}. A avaliação é histórica; qualquer aplicação real exige revisão e monitoramento.")
    else:
        doc.add_paragraph('PENDENTE DE EXECUÇÃO NA BASE REAL: registrar número de pedidos válidos, taxa de atraso, nota média, notas negativas, comparação por UF/período e métricas do modelo após rodar o notebook no Google Colab. Não utilizar os números dos testes sintéticos.')
    doc.add_paragraph('5. Limitações',style=None).runs[0].bold=True
    doc.add_paragraph('Dados Olist de 2016–2018: estudo retrospectivo, sem representar operações atuais. Ausência de avaliações e exclusões por qualidade podem gerar vieses; associação não significa causalidade. O modelo requer revalidação para uso real. Os dados têm licença CC BY-NC-SA 4.0 e a publicação dos painéis exige verificação dessa licença.')
    out.parent.mkdir(parents=True,exist_ok=True)
    doc.save(out)
    return out

def remove_slide(prs,idx):
    slideid=prs.slides._sldIdLst[idx]; prs.part.drop_rel(slideid.rId);prs.slides._sldIdLst.remove(slideid)

def tb(slide,x,y,w,h,text,size=22,bold=False,color=NAVY,align=None):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=shape.text_frame; tf.word_wrap=True;tf.margin_left=Inches(.04);tf.margin_right=Inches(.04);tf.margin_top=Inches(.04)
    for i,line in enumerate(text.split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=color
        if align:p.alignment=align
    return shape

def bgbox(slide,x,y,w,h,fill=LIGHT):
    sh=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=fill;sh.line.fill.background();return sh

def slide_title(s,heading,description=''):
    tb(s,1.20,1.25,15.7,.68,heading,29,True)
    if description:tb(s,1.20,2.00,15.7,.47,description,15,False,GRAY)

def bullets(s,items,y0=2.65,x=1.4,w=14.6,step=.90,size=19):
    for i,line in enumerate(items):
        bgbox(s,x,y0+i*step,w,.74)
        tb(s,x+.3,y0+i*step+.12,w-.5,.53,'• '+line,size,False)

def pagefooter(s):tb(s,1.2,9.63,14.5,.3,'Base: Olist, 2016–2018  |  Projeto acadêmico • Dados não representam 2026',10,False,GRAY)

def build_slides(template,out,architecture,metrics=None,model=None,charts_dir=None):
    prs=Presentation(template)
    # Retain slides until newly generated slides are allocated: avoids duplicate slide part names.
    cover=prs.slides[0]
    tf=cover.shapes[0].text_frame;tf.clear();p=tf.paragraphs[0];p.text=STUDENT;p.font.size=Pt(18);p.font.color.rgb=RGBColor(255,255,255);p.alignment=PP_ALIGN.CENTER
    content_layout=prs.slides[2].slide_layout
    # Repurpose existing official content slide as page 2.
    def blank(s):
        for sh in list(s.shapes):sh._element.getparent().remove(sh._element)
    s=prs.slides[2];blank(s);slide_title(s,'O desafio de negócio','Confiar nos indicadores antes de tomar decisões logísticas')
    bullets(s,['Dados de pedidos, itens, clientes e avaliações estão em tabelas diferentes.','A falta de tratamento das chaves pode multiplicar registros e distorcer KPIs.','Pergunta: atrasos nas entregas se associam a notas menores dos clientes?','Solução: integrar, validar, medir, visualizar e estimar risco de atraso.'],2.75,1.5,15.0,.91,18);pagefooter(s)
    def new():return prs.slides.add_slide(content_layout)
    s=new();slide_title(s,'Indicadores executivos','KPIs com critérios reproduzíveis e denominadores documentados')
    defs=kpis_definitions()
    vals=[('Pedidos entregues',metrics['pedidos_entregues_total_status'] if metrics else None),('Taxa de atraso',f"{metrics['taxa_atraso_pct']:.2f}%" if metrics else None),('Tempo de entrega',f"{metrics['tempo_medio_entrega_dias']:.2f} dias" if metrics else None),('Avaliação média',f"{metrics['avaliacao_media']:.2f}" if metrics else None),('Notas 1 ou 2',f"{metrics['taxa_avaliacoes_negativas_pct']:.2f}%" if metrics else None),('Valor dos itens entregues',f"R$ {metrics['valor_itens_pedidos_entregues_brl']:,.0f}" if metrics else None)]
    for j,(label,value) in enumerate(vals):
        c=j%3;r=j//3;x=1.3+c*5.12;y=2.78+r*2.52
        bgbox(s,x,y,4.74,2.16)
        tb(s,x+.20,y+.24,4.3,.4,label,19,True)
        tb(s,x+.2,y+.92,4.3,.72,str(value) if value is not None else 'A calcular após execução',26 if value is not None else 15,False,BLUE)
    pagefooter(s)
    s=new();slide_title(s,'Arquitetura da solução','Pipeline com coleta, controle de qualidade, BI, Analytics e publicação')
    from PIL import Image
    im=Image.open(architecture);w,h=im.size
    # image aspect ratio, centered within content slide
    maxw,maxh=15.4,6.5; width=min(maxw,maxh*w/h);height=width*h/w
    s.shapes.add_picture(str(architecture),Inches((17.93-width)/2),Inches(2.65+(6.55-height)/2),width=Inches(width))
    pagefooter(s)
    s=new();slide_title(s,'Pontualidade das entregas','Visão por mês de compra e unidade da federação')
    if charts_dir and (Path(charts_dir)/'01_atrasos_mes.png').exists():
        s.shapes.add_picture(str(Path(charts_dir)/'01_atrasos_mes.png'),Inches(1.1),Inches(2.7),width=Inches(8.3))
        s.shapes.add_picture(str(Path(charts_dir)/'02_atrasos_uf.png'),Inches(9.6),Inches(2.65),width=Inches(7.1))
    else:
        bgbox(s,1.4,2.7,15.0,4.7);tb(s,2.2,4.7,13.4,1.0,'Gráficos gerados ao executar o notebook com os CSVs originais',21,True,BLUE,PP_ALIGN.CENTER)
    pagefooter(s)
    s=new();slide_title(s,'Experiência do cliente','Comparação de avaliações em entregas no prazo e atrasadas')
    if charts_dir and (Path(charts_dir)/'03_avaliacao_prazo.png').exists():
        s.shapes.add_picture(str(Path(charts_dir)/'03_avaliacao_prazo.png'),Inches(1.5),Inches(2.65),width=Inches(9.2))
        if metrics and metrics.get('diferenca_nota_atrasados_menos_prazo') is not None:
            bgbox(s,11.05,3.0,5.5,3.5)
            tb(s,11.45,3.5,4.7,.6,'Diferença entre médias',18,True)
            tb(s,11.45,4.6,4.7,1.0,f"{metrics['diferenca_nota_atrasados_menos_prazo']:+.3f} pontos",25,True,BLUE)
    else:
        bgbox(s,1.5,2.7,14.9,4.4);tb(s,2,4.50,14.0,1.0,'Comparação a preencher após análise de avaliações válidas',21,True,BLUE,PP_ALIGN.CENTER)
    tb(s,1.5,8.23,14.6,.45,'Associação não significa causalidade; outros fatores podem influenciar a avaliação.',15,False,GRAY)
    pagefooter(s)
    s=new();slide_title(s,'Analytics preditivo','Classificação de risco de atraso com informações disponíveis na compra')
    bullets(s,['Modelo: regressão logística com tratamento de variáveis numéricas e categóricas.','Variáveis: valor, frete, quantidade de itens, prazo prometido, mês, dia e UF.','Treino/teste: divisão temporal 80% / 20%, sem vazamento de informações futuras.',f"Métricas de validação: ROC AUC {model['roc_auc']:.3f} | recall {model['recall_threshold_05']:.3f}" if model else 'Métricas: ROC AUC, precisão, recall e F1 — calcular no teste real.'],2.65,1.4,15.0,1.0,17)
    pagefooter(s)
    s=new();slide_title(s,'Fase 1 → Fase 2','Hipóteses, método e entregáveis preservados')
    bullets(s,['H1: auditar duplicidades, chaves e contagens; comparar valores brutos e consolidados.','H2: comparar avaliação média de entregas no prazo versus atrasadas.','Quatro tabelas da Olist: pedidos, itens, clientes e avaliações.','CRISP-DM (aula 7) e aprendizado supervisionado (aula 10).','Acompanhar os filtros por UF e mês e o valor dos itens entregues.'],2.52,1.4,15.0,1.07,17)
    pagefooter(s)
    s=new();slide_title(s,'Recomendações executivas','Próximas decisões apoiadas em indicadores auditáveis')
    bullets(s,['Acompanhar taxa de atraso por período e estado, com análise do volume de pedidos.','Investigar áreas com pior experiência e verificar gargalos operacionais.','Priorizar pedidos com maior risco predito para acompanhamento preventivo.','Monitorar qualidade dos dados, desempenho do modelo e possíveis vieses.'],2.65,1.45,15.0,1.05,18)
    tb(s,1.45,8.05,15.4,.55,'Limitação: dados históricos de 2016–2018 não permitem inferir o desempenho atual.',16,True,BLUE);pagefooter(s)
    s=new();slide_title(s,'Entrega e reprodutibilidade','Código, auditoria, dashboards interativos e material para apresentação')
    bullets(s,['Código documentado e testes: src/pipeline.py e tests/test_pipeline.py.','Qualidade e indicadores: outputs CSV e JSON gerados pelo notebook.','Dashboards: desempenho, predição e explorador por UF/mês em HTML (Plotly).' ,'Publicação em GitHub / GitHub Pages requer autenticação na conta.'],2.75,1.5,15.0,1.0,18);pagefooter(s)
    # Remove the instruction slide and unused blank slide only after adding new pages.
    remove_slide(prs,3);remove_slide(prs,1)
    out.parent.mkdir(parents=True,exist_ok=True)
    prs.save(out)
    return out

def generate(template_doc,template_ppt,architecture,result_dir,out_dir,repo_url=None):
    result_dir=Path(result_dir);out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    k=json.loads((result_dir/'kpis.json').read_text()) if (result_dir/'kpis.json').exists() else None
    m=json.loads((result_dir/'avaliacao_modelo.json').read_text()) if (result_dir/'avaliacao_modelo.json').exists() else None
    w=build_report(template_doc,out_dir/'Relatorio_BI_PUCRS.docx',architecture,k,m,repo_url)
    p=build_slides(template_ppt,out_dir/'Apresentacao_Executiva_PUCRS.pptx',architecture,k,m,result_dir/'charts')
    # Optional PDF conversion for headless LibreOffice environments.
    import shutil
    if shutil.which('libreoffice'):
        try:subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/lo_bi_reporting','--headless','--convert-to','pdf','--outdir',str(out_dir),str(w)],check=True,timeout=80,capture_output=True)
        except Exception as exc:print('Conversão DOCX falhou:',exc)
    if not (out_dir/'Relatorio_BI_PUCRS.pdf').exists():
        _pdf_fallback(out_dir/'Relatorio_BI_PUCRS.pdf',architecture,k,m)
    return w,p

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('--doc',required=True);a.add_argument('--ppt',required=True);a.add_argument('--architecture',default='docs/arquitetura.png');a.add_argument('--results',default='results');a.add_argument('--out',default='entrega');args=a.parse_args()
    generate(args.doc,args.ppt,args.architecture,args.results,args.out)

def _pdf_fallback(output_pdf,arch,metrics,model):
    """Generate readable A4 PDF when LibreOffice is not available in Colab."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    output_pdf=Path(output_pdf)
    doc=SimpleDocTemplate(str(output_pdf),pagesize=A4,rightMargin=1.65*cm,leftMargin=1.65*cm,topMargin=2.7*cm,bottomMargin=2.4*cm)
    st=getSampleStyleSheet()
    st.add(ParagraphStyle(name='BItitle',parent=st['Heading1'],fontName='Helvetica-Bold',fontSize=15,textColor=HexColor('#1f4f88'),spaceBefore=11,spaceAfter=8))
    st.add(ParagraphStyle(name='BIbody',parent=st['BodyText'],fontName='Helvetica',fontSize=9.1,leading=13,spaceAfter=8))
    st.add(ParagraphStyle(name='BItable',parent=st['BodyText'],fontName='Helvetica',fontSize=7.1,leading=10))
    data=[['KPI','Fórmula / critério','Fonte']]
    for name,calc,source,_ in kpis_definitions():data.append([name,calc,source])
    elements=[]
    elements.append(Paragraph('Projeto em Business Intelligence e Analytics | Fase 2',st['BItitle']))
    elements.append(Paragraph('Nome do estudante: '+STUDENT,st['BIbody']))
    elements.append(Paragraph('1. Métricas para o negócio proposto (KPIs)',st['BItitle']))
    elements.append(Paragraph('Indicadores extraídos de pedidos entregues, com consolidação de chaves por order_id e exclusão de registros inválidos apenas dos cálculos afetados. Fonte: Olist, pedidos históricos de 2016 a 2018.',st['BIbody']))
    t=Table([[Paragraph(str(v).replace('&','&amp;'),st['BItable']) for v in r] for r in data],colWidths=[3.8*cm,7.4*cm,5.3*cm],repeatRows=1,hAlign='CENTER')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e8f2fc')),('TEXTCOLOR',(0,0),(-1,0),HexColor('#173d66')),('GRID',(0,0),(-1,-1),.35,HexColor('#b2c4d3')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7)]))
    elements.append(t)
    elements.append(Paragraph('2. Arquitetura da solução',st['BItitle']))
    elements.append(Paragraph('Coleta dos arquivos CSV da Olist, preparação e integração com pandas, criação de uma tabela fato por pedido, geração de KPIs e dashboards interativos em Plotly, e classificação preditiva de risco de atraso em scikit-learn. Execução no Google Colab, documentação e publicação previstas no GitHub.',st['BIbody']))
    if Path(arch).exists():
        from PIL import Image as PIL_Image
        w,h=PIL_Image.open(arch).size
        pw=16.5*cm;elements.append(RLImage(str(arch),width=pw,height=pw*h/w))
    elements.append(Paragraph('3. Solução de BI e Analytics',st['BItitle']))
    elements.append(Paragraph('Código reproduzível: src/pipeline.py; dicionário: docs/dicionario_dados.md; dashboards: results/dashboards; auditoria: results/qualidade_dados.json. O modelo de classificação utiliza separação temporal 80/20 para evitar vazamento das informações futuras.',st['BIbody']))
    if metrics:
        elements.append(Paragraph('4. Resultados executados',st['BItitle']))
        elements.append(Paragraph(f"Foram analisadas {metrics['pedidos_com_datas_validas']:,} entregas com datas válidas. Taxa de atraso: {metrics['taxa_atraso_pct']:.2f}%; tempo médio: {metrics['tempo_medio_entrega_dias']:.2f} dias; nota média: {metrics['avaliacao_media']:.2f}; avaliações negativas: {metrics['taxa_avaliacoes_negativas_pct']:.2f}%.",st['BIbody']))
        elements.append(Paragraph(f"Valor total dos itens em pedidos entregues: R$ {metrics['valor_itens_pedidos_entregues_brl']:,.2f}. O valor é soma de preços de itens, sem frete, não faturamento líquido.",st['BIbody']))
        diff=metrics.get('diferenca_nota_atrasados_menos_prazo')
        if diff is not None:elements.append(Paragraph(f'Diferença média entre notas em atrasos versus no prazo: {diff:+.3f} ponto(s). O resultado não prova causalidade.',st['BIbody']))
        if model:elements.append(Paragraph(f"Regressão logística: ROC AUC {model['roc_auc']:.3f}, precisão {model['precision_threshold_05']:.3f}, recall {model['recall_threshold_05']:.3f}, F1 {model['f1_threshold_05']:.3f} no teste temporal de {model['teste_n']:,} pedidos.",st['BIbody']))
    else:
        elements.append(Paragraph('4. Resultados — pendentes de execução com a base real',st['BItitle']))
        elements.append(Paragraph('Este arquivo preliminar não declara indicadores empíricos. Execute o notebook BI_Olist_Colab.ipynb com os CSVs originais antes da submissão para obter os resultados verificáveis.',st['BIbody']))
    elements.append(Paragraph('Link do GitHub: inserir somente após a publicação real.',st['BIbody']))
    elements.append(Paragraph('Limitações: dados históricos (2016–2018), sem validação do desempenho operacional atual; associação não implica causalidade. A licença de dados é CC BY-NC-SA 4.0.',st['BIbody']))
    def draw(c,doc):
        c.setStrokeColor(HexColor('#2769aa'));c.line(1.65*cm,A4[1]-2.30*cm,A4[0]-1.65*cm,A4[1]-2.30*cm)
        c.setFillColor(HexColor('#1e4b77'));c.setFont('Helvetica-Bold',9);c.drawString(1.65*cm,A4[1]-1.35*cm,'PUCRS online  |  Projeto de BI & Analytics')
        c.setStrokeColor(HexColor('#7699bb'));c.line(1.65*cm,1.55*cm,A4[0]-1.65*cm,1.55*cm)
        c.setFillColor(HexColor('#65778d'));c.setFont('Helvetica',7);c.drawString(1.65*cm,1.23*cm,'Projeto acadêmico - Olist, 2016–2018')
        c.drawRightString(A4[0]-1.65*cm,1.23*cm,str(doc.page))
    doc.build(elements,onFirstPage=draw,onLaterPages=draw)
    return output_pdf
