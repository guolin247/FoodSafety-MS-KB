from pathlib import Path
import unittest

from data_layer import (
    build_knowledge_base,
    classify_platform,
    data_signature,
    normalize_region,
    plain_formula,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


class DataLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.knowledge_base = build_knowledge_base(
            DATA_DIR,
            data_signature(DATA_DIR),
        )

    def test_schema_v2_counts(self) -> None:
        kb = self.knowledge_base
        self.assertEqual(len(kb["documents"]), 451)
        self.assertEqual(len(kb["methods"]), 1_130)
        self.assertEqual(len(kb["detections_df"]), 17_771)
        self.assertEqual(len(kb["compounds"]), 1_298)

    def test_every_detection_has_identity_and_context(self) -> None:
        frame = self.knowledge_base["detections_df"]
        self.assertTrue(frame["CAS"].ne("").all())
        self.assertTrue(frame["化合物"].ne("").all())
        self.assertTrue(frame["标准编号"].ne("").all())
        self.assertTrue(frame["方法"].ne("").all())
        self.assertEqual(len(self.knowledge_base["detection_lookup"]), len(frame))

    def test_method_and_document_links_resolve(self) -> None:
        kb = self.knowledge_base
        self.assertTrue(
            all(
                document_id in kb["documents_by_id"]
                for document_id, _ in kb["methods_by_key"]
            )
        )
        self.assertTrue(
            all(
                (context["row"]["document_id"], context["row"]["方法"])
                in kb["methods_by_key"]
                for context in kb["detection_lookup"].values()
            )
        )

    def test_reviewed_document_correction(self) -> None:
        kb = self.knowledge_base
        document = kb["documents_by_id"]["193F.00"]
        self.assertEqual(document["issuing_country"]["value"], "日本")
        self.assertIsNone(document["issuing_agency"]["value"])
        self.assertIsNone(document["publication_date"]["value"])
        self.assertIn("参考文献", document["_correction"]["reason"])
        self.assertNotIn("澳大利亚", set(kb["documents_df"]["地区"]))
        corrected_row = kb["documents_df"].loc[
            kb["documents_df"]["document_id"] == "193F.00"
        ].iloc[0]
        self.assertEqual(corrected_row["地区"], "日本")
        self.assertEqual(corrected_row["标准编号"], "JP 000473283（内部记录）")

    def test_display_normalization(self) -> None:
        self.assertEqual(normalize_region("中华人民共和国", "GB_1"), "中国")
        self.assertEqual(normalize_region(None, "JP_0001"), "日本")
        self.assertEqual(classify_platform("UHPLC-MS/MS"), "UHPLC-MS/MS")
        self.assertEqual(classify_platform("气相色谱—质谱法"), "GC-MS")
        self.assertEqual(
            plain_formula("C<sub>21</sub>H<sub>28</sub>O<sub>5</sub>"),
            "C21H28O5",
        )


if __name__ == "__main__":
    unittest.main()
