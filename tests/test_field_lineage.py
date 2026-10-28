"""Regression coverage: actual QVS and catalog edges, without Qlik credentials."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ci"))
import field_lineage as fl

class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=fl.build()
        cls.nodes={n["id"]:n for n in cls.g["nodes"]}

    def test_etl_qvd_and_presentation_field_chain(self):
        g=self.g
        start="table:etl1:RawOrders.Quantity"
        self.assertIn(start,self.nodes)
        reachable=fl.reachable(g,{start})
        self.assertIn("qvd:lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity",reachable)
        self.assertIn("table:etl2:SalesClean.Revenue",reachable)
        self.assertIn("qvd:lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue",reachable)
        self.assertIn("logical:presentation:Revenue",reachable)
        self.assertIn("logical:presentation2:Revenue",reachable)
        self.assertIn("measure:qlikgpt_shared_revenue",reachable)

    def test_formula_value_lineage_is_not_made_up(self):
        g=self.g
        origin="table:etl1:RawOrders.CostRatio"
        impacted=fl.reachable(g,{origin},exclude_row_filters=True)
        self.assertIn("measure:qlikgpt_shared_margin",impacted)
        self.assertIn("measure:qlikgpt_shared_margin_pct",impacted)
        self.assertNotIn("measure:qlikgpt_shared_orders",impacted)
        self.assertNotIn("measure:qlikgpt_shared_revenue",impacted)

    def test_row_filter_distinguished_from_value(self):
        edge=next(e for e in self.g["edges"] if
                  e["from"]=="table:etl2:RawOrders.Quantity" and
                  e["to"]=="table:etl2:SalesClean.Market")
        self.assertEqual(edge["kind"],"row_filter")
        filtered=fl.reachable(self.g,{"table:etl1:RawOrders.Quantity"})
        value=fl.reachable(self.g,{"table:etl1:RawOrders.Quantity"},
                           exclude_row_filters=True)
        self.assertIn("table:etl2:SalesClean.Market",filtered)
        self.assertNotIn("table:etl2:SalesClean.Market",value)

    def test_measure_impact_exact_objects_across_apps(self):
        item=fl.impact(self.g,"measure:qlikgpt_shared_revenue")
        self.assertEqual(item["impactedApps"],["presentation","presentation2"])
        expected={
            "object:presentation:qlikgpt_kpi_revenue",
            "object:presentation:qlikgpt_chart_month",
            "object:presentation:qlikgpt_chart_market",
            "object:presentation:qlikgpt_table_sales",
            "object:presentation:qlikgpt_chart_channel",
            "object:presentation2:qlikgpt_p2_kpi_revenue",
        }
        self.assertEqual({x["id"] for x in item["impactedObjects"]},expected)

    def test_unsubscribed_average_order_is_not_in_a_visual(self):
        item=fl.impact(self.g,"measure:qlikgpt_shared_average_order")
        self.assertEqual(item["impactedApps"],[])
        self.assertEqual(item["impactedObjects"],[])

    def test_filter_targets_and_calendar_year(self):
        item=fl.impact(self.g,"dimension:qlikgpt_d_year")
        self.assertIn("object:presentation:qlikgpt_list_year",
                      [x["id"] for x in item["impactedObjects"]])
        self.assertNotIn("presentation2",item["impactedApps"])
        sources=fl.reachable(self.g,{"logical:presentation:SalesYear"},
                             backward=True,exclude_row_filters=True)
        self.assertIn("table:presentation:Calendar.SalesYear",sources)
        self.assertIn("table:presentation:FactSales.OrderDate",sources)

    def test_market_sort_uses_master_measure_without_inline_formula(self):
        edges=[x for x in self.g["edges"] if
               x["to"]=="object:presentation:qlikgpt_chart_market" and
               x["kind"]=="inline_sort"]
        self.assertEqual(edges,[])
        self.assertTrue(any(x["from"]=="subscription:presentation:measure:qlikgpt_shared_revenue" and
                            x["to"]=="object:presentation:qlikgpt_chart_market"
                            for x in self.g["edges"]))

    def test_unsupported_qvs_does_not_infer_unknown_source_fields(self):
        script="A:\nLOAD Ghost AS Value FROM [lib://DataFiles/outside.qvd] (qvd);\n"
        blocks,warnings=fl.parse_loads(script,"test.qvs")
        self.assertEqual(len(blocks),1)
        used,missing=fl.fields_used("Ghost",{"Revenue"})
        self.assertEqual(used,set())
        self.assertEqual(missing,{"Ghost"})

    def test_complex_commas_in_pick_are_one_column(self):
        script=("Raw:\nLOAD Pick(1+Floor(Rand()*4), 'Italy', 'France', "
                "'Spain', 'Germany') AS Market, Rand() AS UnitPrice "
                "AUTOGENERATE 5000;\n")
        blocks,_=fl.parse_loads(script,"test.qvs")
        self.assertEqual([x["field"] for x in blocks[0]["columns"]],
                         ["Market","UnitPrice"])

    def test_evidence_and_determinism(self):
        for edge in self.g["edges"]:
            self.assertTrue(edge["source"]["path"])
            self.assertGreater(edge["source"]["line"],0)
        self.assertEqual(fl.render(self.g),fl.render(fl.build()))
        self.assertEqual(self.g,fl.build())

if __name__=="__main__":
    unittest.main()
