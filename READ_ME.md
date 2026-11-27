# Projeto em BI e Analytics -> Fase 2 - PUCRS

**Projeto acadêmico ** Fonte: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (2016–2018).

## Objetivo

Produzir indicadores reproduzíveis de pontualidade e avaliações de clientes e estimar o risco de atraso de entregas com regressão logística.

## Execução:
- Execute as células na ordem. O notebook baixa a base original via KaggleHub; se necessário, recorre ao espelho acadêmico comprimido.
- Aguarde o cálculo e baixe `BI_Olist_resultados.zip` contendo KPIs e tabelas de auditoria

## Execução local:

```bash
pip install -r requirements.txt
python -m src.pipeline --data-dir data/raw --output-dir results
```

A pasta `data/raw/` deve conter os CSVs originais ou `.csv.gz`: orders, order_items, customers, order_reviews. O script tenta obtê-los automaticamente quando há acesso à internet.

## Arquitetura

`Kaggle Olist CSV → Python/pandas (inspeção, chaves, limpeza, agregações) → tabela fato de pedidos → KPIs e dashboards Plotly HTML → regressão logística scikit-learn (risco histórico de atraso) → relatório executivo`.

**Auditoria:** `results/qualidade_dados.json`, `results/kpis.json`, `results/mensal.csv`, `results/estados.csv`, `results/fato_pedidos_validada.csv`.

**Modelagem:** `results/modelo_risco_atraso.joblib`, `results/previsoes_teste.csv`, `results/avaliacao_modelo.json` (partição temporal 80%/20%, ROC AUC, average precision, precisão, recall e F1).

**Dashboards:** `results/dashboards/01_desempenho_logistico.html`, `02_qualidade_e_predicao.html` e `03_explorador_uf_mes.html` (filtro UF/mês). Os gráficos carregam Plotly via CDN na abertura; é preciso internet para a interação.

## Obs.:

- A análise é retrospectiva (2016–2018) e não informa desempenho atual.
- Estudo de caso **hipotético** apoiado em dados públicos.
