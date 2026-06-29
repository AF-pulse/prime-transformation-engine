import json
import unittest
from pathlib import Path

from backend.app.extensions.transformation.continuity.transformation_object import (
    validate_transformation_object,
)


OBJECT_PATH = Path("runtime/objects/PTE-101.transformation-object.json")


class Pte101TransformationObjectTest(unittest.TestCase):
    def test_transformation_object_artifact_is_valid(self):
        obj = json.loads(OBJECT_PATH.read_text(encoding="utf-8"))

        validate_transformation_object(obj)

        self.assertEqual(obj["id"], "PTE-101")
        self.assertEqual(obj["created_by"], "prime-transformation-engine")
        self.assertEqual(obj["ctl_layer"], "CTL-E")
        self.assertEqual(obj["substrate"], "ET")
        self.assertEqual(obj["state"], "grounded")
        self.assertGreaterEqual(len(obj["grounding"]["references"]), 1)
        self.assertIn("DBA-09", obj["provenance"]["reference_ids"])

    def test_missing_grounding_fails_closed(self):
        obj = json.loads(OBJECT_PATH.read_text(encoding="utf-8"))
        obj["grounding"] = {"references": []}

        with self.assertRaises(ValueError):
            validate_transformation_object(obj)


if __name__ == "__main__":
    unittest.main()
