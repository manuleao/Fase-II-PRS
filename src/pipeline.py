"""Cloud-independent educational BI pipeline for the 2016-2018 Olist dataset.

Downloads raw data in Google Colab when network is available; alternatively
place the original CSV or CSV.GZ files in data/raw before running.
Metrics must only be reported after actual execution on the authentic files.
"""
from pathlib import Path
import argparse
import json
import warnings
import urllib.request
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib

FILES = {
    'orders': 'olist_orders_dataset.csv',
    'items': 'olist_order_items_dataset.csv',
    'customers': 'olist_customers_dataset.csv',
    'reviews': 'olist_order_reviews_dataset.csv'
}
SOURCE = 'https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce'
MIRROR = 'https://raw.githubusercontent.com/infobarbosa/dataset-olist/main/data/'


def ensure_data(folder: Path, allow_download=True):
    folder.mkdir(parents=True,exist_ok=True)
    def present(fname):
        return (folder/fname).exists() or (folder/(fname+'.gz')).exists()
    missing = [fname for fname in FILES.values() if not present(fname)]
    if not missing: return
    if not allow_download:
        raise FileNotFoundError('Ausentes em '+str(folder)+': '+', '.join(missing))
    print('Baixando a base Olist original (licença CC BY-NC-SA 4.0)...')
    try:
        import kagglehub
        kpath = Path(kagglehub.dataset_download('olistbr/brazilian-ecommerce'))
        for filename in missing:
            matches=list(kpath.rglob(filename))
            if matches:
                import shutil
                shutil.copyfile(matches[0],folder/filename)
    except Exception as exc:
        print('Kaggle indisponível:',exc)
    missing=[fname for fname in FILES.values() if not present(fname)]
    for fname in missing:
        print('Obtendo espelho educacional:',fname)
        urllib.request.urlretrieve(MIRROR+fname+'.gz',str(folder/(fname+'.gz')))
    missing=[fname for fname in FILES.values() if not present(fname)]
    if missing: raise FileNotFoundError('Não foi possível obter: '+', '.join(missing))


def load_raw(folder: Path):
    frames={}
    for key,filename in FILES.items():
        path=folder/filename
        if not path.exists():path=folder/(filename+'.gz')
        frames[key]=pd.read_csv(path)
    return frames


def prepare(raw):
    orders=raw['orders'].copy()
    customers=raw['customers'].copy()
    items=raw['items'].copy()
    reviews=raw['reviews'].copy()
    log={}
    log['pedidos_brutos']=int(len(orders))
    log['pedidos_duplicados_id']=int(orders['order_id'].duplicated().sum())
    orders=orders.drop_duplicates('order_id',keep='first')
    log['clientes_duplicados_id']=int(customers['customer_id'].duplicated().sum())
    customers=customers.drop_duplicates('customer_id')
    for col in ['order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date']:
        orders[col]=pd.to_datetime(orders[col],errors='coerce')
    log['itens_brutos']=int(len(items))
    log['itens_duplicados_chave']=int(items.duplicated(['order_id','order_item_id']).sum())
    items=items.drop_duplicates(['order_id','order_item_id'],keep='first')
    for col in ['price','freight_value']:
        items[col]=pd.to_numeric(items[col],errors='coerce')
        log[f'itens_{col}_invalidos']=int((items[col].isna() | (items[col]<0)).sum())
        items.loc[items[col]<0,col]=np.nan
    item_ag=items.groupby('order_id',as_index=False).agg(
        valor_itens=('price','sum'),frete=('freight_value','sum'),quantidade_itens=('order_item_id','count'))
    # Multiple reviews per order: keep the latest review event (documented rule).
    reviews['review_creation_date']=pd.to_datetime(reviews['review_creation_date'],errors='coerce')
    reviews['review_score']=pd.to_numeric(reviews['review_score'],errors='coerce')
    log['avaliacoes_multiplas_pedido']=int(reviews['order_id'].duplicated().sum())
    reviews=reviews.sort_values(['review_creation_date','review_id'],kind='mergesort').drop_duplicates('order_id',keep='last')
    reviews.loc[~reviews['review_score'].between(1,5),'review_score']=np.nan
    df=orders.merge(customers[['customer_id','customer_state']],on='customer_id',how='left',validate='many_to_one')
    df=df.merge(item_ag,on='order_id',how='left',validate='one_to_one')
    df=df.merge(reviews[['order_id','review_score']],on='order_id',how='left',validate='one_to_one')
    df['dias_entrega']=(df['order_delivered_customer_date']-df['order_purchase_timestamp']).dt.total_seconds()/86400
    df['dias_prometidos']=(df['order_estimated_delivery_date']-df['order_purchase_timestamp']).dt.total_seconds()/86400
    df['dias_atraso']=(df['order_delivered_customer_date'].dt.normalize()-df['order_estimated_delivery_date'].dt.normalize()).dt.days
    complete = (df['order_status'].eq('delivered') & df['order_purchase_timestamp'].notna() & df['order_delivered_customer_date'].notna() & df['order_estimated_delivery_date'].notna())
    coherent = (df['dias_entrega']>=0) & (df['dias_prometidos']>=0) & df['dias_entrega'].le(730)
    df['valido_prazo']=complete & coherent
    df['atrasou']=df['dias_atraso'].gt(0)
    df['mes_compra']=df['order_purchase_timestamp'].dt.to_period('M').astype('string')
    df['dia_semana']=df['order_purchase_timestamp'].dt.dayofweek
    df['mes_numero']=df['order_purchase_timestamp'].dt.month
    log['pedidos_unicos']=int(len(df))
    log['linhas_se_join_direto_itens']=int(len(orders.merge(items[['order_id','order_item_id']],on='order_id',how='left')))
    log['inflacao_contagem_sem_agregacao']=log['linhas_se_join_direto_itens']-log['pedidos_unicos']
    log['registros_avaliacao_fora_1_5']=int(raw['reviews']['review_score'].isna().sum()) + int((pd.to_numeric(raw['reviews']['review_score'],errors='coerce').notna() & ~pd.to_numeric(raw['reviews']['review_score'],errors='coerce').between(1,5)).sum())
    log['pedidos_entregues_status']=int(df['order_status'].eq('delivered').sum())
    log['entregas_validas_para_prazo']=int(df['valido_prazo'].sum())
    log['entregas_descartadas_da_analise_prazo']=int((df['order_status'].eq('delivered') & ~df['valido_prazo']).sum())
    log['entregas_validas_sem_nota']=int((df['valido_prazo'] & df['review_score'].isna()).sum())
    log['pedidos_sem_uf']=int(df['customer_state'].isna().sum())
    return df,log


def calculate(df,quality):
    sub=df.loc[df['valido_prazo']].copy()
    evaluated=sub.loc[sub['review_score'].notna()].copy()
    kpis={
        'pedidos_entregues_total_status':int((df['order_status']=='delivered').sum()),
        'pedidos_com_datas_validas':int(len(sub)),
        'entregas_atrasadas':int(sub['atrasou'].sum()),
        'taxa_atraso_pct':round(float(sub['atrasou'].mean()*100),2),
        'tempo_medio_entrega_dias':round(float(sub['dias_entrega'].mean()),2),
        'pedidos_avaliados_validos':int(len(evaluated)),
        'avaliacao_media':round(float(evaluated['review_score'].mean()),3),
        'taxa_avaliacoes_negativas_pct':round(float(evaluated['review_score'].le(2).mean()*100),2),
        'valor_itens_pedidos_entregues_brl':round(float(df.loc[df.order_status.eq('delivered'),'valor_itens'].sum()),2),
        'ticket_medio_itens_entregues_brl':round(float(df.loc[df.order_status.eq('delivered'),'valor_itens'].mean()),2)
    }
    groups=evaluated.groupby('atrasou')['review_score'].agg(['mean','count']).reset_index()
    kpis['nota_media_atrasados']=float(groups.loc[groups['atrasou'],'mean'].iloc[0]) if groups['atrasou'].any() else None
    kpis['nota_media_no_prazo']=float(groups.loc[~groups['atrasou'],'mean'].iloc[0]) if (~groups['atrasou']).any() else None
    kpis['diferenca_nota_atrasados_menos_prazo']=(round(kpis['nota_media_atrasados']-kpis['nota_media_no_prazo'],3) if kpis['nota_media_atrasados'] is not None and kpis['nota_media_no_prazo'] is not None else None)
    monthly=sub.groupby('mes_compra',dropna=False).agg(pedidos=('order_id','nunique'),taxa_atraso=('atrasou','mean'),tempo_medio=('dias_entrega','mean')).reset_index()
    monthly['taxa_atraso']=100*monthly['taxa_atraso']
    states=sub.groupby('customer_state',dropna=False).agg(pedidos=('order_id','nunique'),taxa_atraso=('atrasou','mean'),tempo_medio=('dias_entrega','mean')).reset_index()
    states['taxa_atraso']=100*states['taxa_atraso']
    # Comparação inferencial para a hipótese H2: diferença das notas entre grupos,
    # sem inferir causalidade, usando intervalo t de Welch de 95% e p-valor bilateral.
    from scipy.stats import ttest_ind, t
    late=evaluated.loc[evaluated['atrasou'],'review_score'].astype(float).to_numpy()
    ontime=evaluated.loc[~evaluated['atrasou'],'review_score'].astype(float).to_numpy()
    if len(late)>1 and len(ontime)>1:
        import math
        diff=float(late.mean()-ontime.mean())
        v1=float(late.var(ddof=1))/len(late);v2=float(ontime.var(ddof=1))/len(ontime)
        se=math.sqrt(v1+v2)
        dfree=(v1+v2)**2/((v1*v1)/(len(late)-1)+(v2*v2)/(len(ontime)-1)) if v1+v2 else float('inf')
        tcritical=float(t.ppf(.975,dfree)) if se else 0.
        kpis['h2_diferenca_nota_ic95']=[round(diff-tcritical*se,3),round(diff+tcritical*se,3)]
        kpis['h2_teste_welch_p_valor']=float(ttest_ind(late,ontime,equal_var=False).pvalue)
    review_by_late=evaluated.groupby('atrasou').agg(nota_media=('review_score','mean'),avaliacoes=('order_id','nunique'),negativas=('review_score',lambda x:int((x<=2).sum()))).reset_index()
    review_by_late['faixa']=review_by_late['atrasou'].map({False:'No prazo',True:'Atrasada'})
    return kpis,monthly,states.sort_values('pedidos',ascending=False),review_by_late


def predictive_model(df, output:Path):
    sub=df[df['valido_prazo']].copy().sort_values('order_purchase_timestamp')
    features=['valor_itens','frete','quantidade_itens','dias_prometidos','mes_numero','dia_semana','customer_state']
    # Features exclusively known when order is placed; prohibit actual delivery in X.
    numeric=features[:-1]
    categorical=['customer_state']
    sub=sub.dropna(subset=['atrasou','order_purchase_timestamp'])
    if len(sub)<150 or sub['atrasou'].nunique()<2:
        raise ValueError('Base insuficiente para avaliação preditiva real.')
    pivot=int(len(sub)*.8)
    train,test=sub.iloc[:pivot],sub.iloc[pivot:]
    if train['atrasou'].nunique()<2 or test['atrasou'].nunique()<2:
        raise ValueError('Classes insuficientes no treino ou teste temporal.')
    transform=ColumnTransformer([
        ('numericos',Pipeline([('imputer',SimpleImputer(strategy='median')),('scale',StandardScaler())]),numeric),
        ('categorias',Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]),categorical)
    ])
    pipeline=Pipeline([('preparation',transform),('classifier',LogisticRegression(max_iter=1500,class_weight='balanced',random_state=42))])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        pipeline.fit(train[features],train['atrasou'].astype(int))
    p=pipeline.predict_proba(test[features])[:,1]
    y=test['atrasou'].astype(int).to_numpy()
    pred=(p>=.5).astype(int)
    stats={
        'tipo':'classificacao_de_risco_de_atraso',
        'estimador':'regressao_logistica_com_pesos_de_classe',
        'particao':'80% treino, 20% teste por data de compra (sem embaralhar)',
        'treino_n':int(len(train)), 'teste_n':int(len(test)),
        'taxa_atraso_teste_pct':round(100*float(y.mean()),2),
        'roc_auc':round(float(roc_auc_score(y,p)),4),
        'average_precision':round(float(average_precision_score(y,p)),4),
        'precision_threshold_05':round(float(precision_score(y,pred,zero_division=0)),4),
        'recall_threshold_05':round(float(recall_score(y,pred,zero_division=0)),4),
        'f1_threshold_05':round(float(f1_score(y,pred,zero_division=0)),4),
        'matriz_confusao':confusion_matrix(y,pred,labels=[0,1]).tolist(),
        'observacao':'Predição histórica avaliada fora da amostra. Não demonstra causalidade nem previsão de 2026.'
    }
    joblib.dump(pipeline,output/'modelo_risco_atraso.joblib')
    test[['order_id','order_purchase_timestamp','atrasou']].assign(probabilidade_atraso=p).to_csv(output/'previsoes_teste.csv',index=False)
    return stats


def figures(monthly,states,reviews,output):
    from matplotlib.ticker import PercentFormatter
    output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    fig,ax=plt.subplots(figsize=(10,4)); ax.plot(monthly.mes_compra.astype(str),monthly.taxa_atraso,marker='o',color='#2867a5');ax.set(title='Taxa de entregas atrasadas por mês',ylabel='Atrasos (%)',xlabel='Mês de compra');ax.tick_params(axis='x',rotation=65);fig.tight_layout();fig.savefig(output/'01_atrasos_mes.png',dpi=180);plt.close(fig)
    top=states.head(12).iloc[::-1]
    fig,ax=plt.subplots(figsize=(8,5));ax.barh(top.customer_state.fillna('ND'),top.taxa_atraso,color='#2867a5');ax.set(title='Taxa de atraso nos 12 estados com mais pedidos',xlabel='Entregas atrasadas (%)');fig.tight_layout();fig.savefig(output/'02_atrasos_uf.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4));ax.bar(reviews.faixa,reviews.nota_media,color=['#43a68c','#df885a'][:len(reviews)]);ax.set_ylim(0,5);ax.set(title='Avaliação média por pontualidade',ylabel='Notas de 1 a 5');fig.tight_layout();fig.savefig(output/'03_avaliacao_prazo.png',dpi=180);plt.close(fig)


def main(data_dir:Path,output:Path,allow_download=True):
    output.mkdir(parents=True,exist_ok=True)
    ensure_data(data_dir,allow_download)
    raw=load_raw(data_dir)
    orders,quality=prepare(raw)
    kpis,monthly,states,reviews=calculate(orders,quality)
    quality['origem']=SOURCE
    (output/'qualidade_dados.json').write_text(json.dumps(quality,indent=2,ensure_ascii=False),encoding='utf-8')
    (output/'kpis.json').write_text(json.dumps(kpis,indent=2,ensure_ascii=False),encoding='utf-8')
    monthly.to_csv(output/'mensal.csv',index=False)
    states.to_csv(output/'estados.csv',index=False)
    reviews.to_csv(output/'avaliacoes_pontualidade.csv',index=False)
    x=orders.loc[orders['valido_prazo']].copy()
    x['nota_valida']=x['review_score'].where(x['review_score'].between(1,5))
    cross=x.groupby(['customer_state','mes_compra'],dropna=False).agg(
        pedidos=('order_id','nunique'),atrasadas=('atrasou','sum'),
        dias_entrega_total=('dias_entrega','sum'),
        notas_soma=('nota_valida','sum'), notas_qtd=('nota_valida','count'),
        notas_negativas=('nota_valida',lambda v:int(v.le(2).sum()))).reset_index()
    cross.to_csv(output/'uf_mes_agregado.csv',index=False)
    orders[['order_id','customer_state','mes_compra','order_status','valido_prazo','atrasou','dias_entrega','dias_atraso','review_score','valor_itens','frete']].to_csv(output/'fato_pedidos_validada.csv',index=False)
    results=predictive_model(orders,output)
    (output/'avaliacao_modelo.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    figures(monthly,states,reviews,output/'charts')
    try:
        from src.dashboard import make_dashboards
        make_dashboards(kpis,quality,results,monthly,states,reviews,output/'dashboards', cross)
    except ImportError:
        from dashboard import make_dashboards
        make_dashboards(kpis,quality,results,monthly,states,reviews,output/'dashboards', cross)
    # GitHub Pages: publish these generated documents from the /docs folder on main.
    import shutil
    page_dir=output.parent/'docs'
    page_dir.mkdir(parents=True,exist_ok=True)
    for html_file in (output/'dashboards').glob('*.html'):
        shutil.copyfile(html_file,page_dir/html_file.name)
    (page_dir/'index.html').write_text('''<!doctype html><html lang="pt-br"><meta charset="utf-8"><title>Painéis BI Olist</title><style>body{font:18px Arial;margin:4rem;background:#f2f7fb;color:#173c65}a{display:block;margin:1rem 0;color:#1262a0}</style><h1>Olist | BI e Analytics</h1><p>Estudo histórico, 2016–2018.</p><a href="01_desempenho_logistico.html">Painel de entregas e avaliações</a><a href="02_qualidade_e_predicao.html">Painel preditivo</a><a href="03_explorador_uf_mes.html">Explorador por UF e mês</a></html>''',encoding='utf-8')
    print('Processamento real finalizado. Resultados em:',output.resolve())
    print(json.dumps(kpis,indent=2,ensure_ascii=False))
    return kpis,results

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',default='data/raw',type=Path)
    parser.add_argument('--output-dir',default='results',type=Path)
    parser.add_argument('--no-download',action='store_true')
    a=parser.parse_args()
    main(a.data_dir,a.output_dir,not a.no_download)
