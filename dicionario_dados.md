# Dicionário de dados e regras de qualidade

Fonte: **Brazilian E-Commerce Public Dataset by Olist (2016–2018)**, Kaggle, licença CC BY-NC-SA 4.0.

| Campo | Tabela original | Significado | Tratamento |
|---|---|---|---|
| `order_id` | orders, items, reviews | identificador do pedido | chave única na tabela fato; `nunique` nos KPIs |
| `customer_id` | orders, customers | identifica registro do cliente para o pedido | vínculo muitos-para-um |
| `customer_state` | customers | UF de destino | categoria; ausentes reportados |
| `order_status` | orders | situação do pedido | somente `delivered` para entregas |
| `order_purchase_timestamp` | orders | data de compra | data válida e anterior à entrega |
| `order_delivered_customer_date` | orders | data de entrega real | obrigatória para pontualidade |
| `order_estimated_delivery_date` | orders | data prometida | obrigatória para pontualidade |
| `price`, `freight_value` | order_items | valor e frete por item | soma por `order_id`, evitando multiplicação |
| `review_score` | order_reviews | nota de 1 a 5 | mantém evento de avaliação mais recente por pedido |

## Fórmulas

- **Entregas analisáveis:** contagem de pedidos `delivered` distintos com datas de compra, entrega e estimativa coerentes.
- **Taxa de atraso:** entregas analisáveis com `entrega_real > entrega_estimada` / entregas analisáveis ×100.
- **Tempo médio de entrega:** média de `(entrega_real - compra)` em dias corridos, apenas entregas analisáveis.
- **Avaliação média:** média `review_score` de 1 a 5 entre entregas analisáveis com avaliação válida.
- **Avaliações negativas:** notas 1 ou 2 / total de entregas analisáveis com avaliação válida ×100.
- **Dados faltantes:** excluídos *apenas* do KPI que deles depende; a tabela bruta não é alterada.
- **Pedidos duplicados:** uma linha por `order_id` em pedidos, agregação de itens antes do vínculo e uma avaliação por pedido.

A base contém registros históricos; qualquer decisão operacional atual exigiria dados atualizados.

### Fonte metodológica das aulas
- Aula 7: CRISP-DM / KDD; 
- Aula 8: GitHub Pages; 
- Aula 9: dashboards e indicadores; 
- Aula 10: aprendizado supervisionado.
