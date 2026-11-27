import unittest
import pandas as pd
from src.pipeline import prepare,calculate
class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.raw={
            'orders':pd.DataFrame({'order_id':['a','b'],'customer_id':['x','y'],'order_status':['delivered','delivered'],'order_purchase_timestamp':['2018-01-01','2018-01-01'],'order_delivered_customer_date':['2018-01-05','2018-01-10'],'order_estimated_delivery_date':['2018-01-06','2018-01-06']}),
            'customers':pd.DataFrame({'customer_id':['x','y'],'customer_state':['SP','RJ']}),
            'items':pd.DataFrame({'order_id':['a','a','b'],'order_item_id':[1,2,1],'price':[10.,20.,30.],'freight_value':[3.,4.,5.]}),
            'reviews':pd.DataFrame({'review_id':['r1','r2'],'order_id':['a','b'],'review_score':[5,1],'review_creation_date':['2018-01-06','2018-01-11']})
        }
    def test_unique_order_and_kpi(self):
        df,q=prepare(self.raw);k,_,_,_=calculate(df,q)
        self.assertEqual(len(df),2)
        self.assertEqual(df.loc[df.order_id.eq('a'),'valor_itens'].iloc[0],30.)
        self.assertEqual(k['pedidos_com_datas_validas'],2)
        self.assertAlmostEqual(k['taxa_atraso_pct'],50.)
        self.assertAlmostEqual(k['avaliacao_media'],3.)
        self.assertAlmostEqual(k['taxa_avaliacoes_negativas_pct'],50.)
        self.assertAlmostEqual(k['valor_itens_pedidos_entregues_brl'],60.)
        self.assertEqual(q['inflacao_contagem_sem_agregacao'],1)
if __name__=='__main__':unittest.main()
