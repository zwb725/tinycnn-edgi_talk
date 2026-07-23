from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_e84_fvp_output.py"

FVP_PASS_LOG = """\
PTE Model data loaded. Size: 31696 bytes.
NPU delegations: 1 (1.00 per inference)
Output[0][0]: (float) -0.020373
Output[0][1]: (float) 0.067080
Output[0][2]: (float) -0.059627
Output[0][3]: (float) 0.062111
Program complete, exiting.
"""

E84_PASS_LOG = """\
[executorch] output0 float top1=1
[executorch] output0[0] float_bits=0xbca6e43b
[executorch] output0[1] float_bits=0x3d896156
[executorch] output0[2] float_bits=0xbd743b44
[executorch] output0[3] float_bits=0x3d7e6867
"""


class ValidateE84FvpOutputTest(unittest.TestCase):
    def run_validator(
        self,
        fvp_log: str,
        e84_log: str,
        tolerance: str = "1e-6",
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fvp_path = tmp_path / "fvp.log"
            e84_path = tmp_path / "e84.log"
            fvp_path.write_text(fvp_log, encoding="utf-8")
            e84_path.write_text(e84_log, encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--fvp-log",
                    str(fvp_path),
                    "--e84-log",
                    str(e84_path),
                    "--tolerance",
                    tolerance,
                ],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_pass_logs(self) -> None:
        result = self.run_validator(FVP_PASS_LOG, E84_PASS_LOG)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pte_loaded=PASS", result.stdout)
        self.assertIn("npu_delegate=PASS", result.stdout)
        self.assertIn("program_complete=PASS", result.stdout)
        self.assertIn("top1_match=PASS", result.stdout)
        self.assertIn("output_match=PASS", result.stdout)
        self.assertIn("TINYCNN_E84_FVP_FINAL_COMPARE=PASS", result.stdout)

    def test_output_error_above_tolerance_fails(self) -> None:
        fvp_log = FVP_PASS_LOG.replace("-0.020373", "-0.100000", 1)
        result = self.run_validator(fvp_log, E84_PASS_LOG)
        self.assertEqual(result.returncode, 1)
        self.assertIn("output_match=FAIL", result.stdout)
        self.assertIn("TINYCNN_E84_FVP_FINAL_COMPARE=FAIL", result.stdout)

    def test_top1_mismatch_fails(self) -> None:
        fvp_log = FVP_PASS_LOG.replace("-0.020373", "0.200000", 1)
        result = self.run_validator(fvp_log, E84_PASS_LOG)
        self.assertEqual(result.returncode, 1)
        self.assertIn("top1_match=FAIL", result.stdout)

    def test_missing_one_e84_output_fails(self) -> None:
        e84_log = E84_PASS_LOG.replace("[executorch] output0[3] float_bits=0x3d7e6867\n", "")
        result = self.run_validator(FVP_PASS_LOG, e84_log)
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing output index", result.stderr)

    def test_missing_program_complete_fails(self) -> None:
        fvp_log = FVP_PASS_LOG.replace("Program complete, exiting.\n", "")
        result = self.run_validator(fvp_log, E84_PASS_LOG)
        self.assertEqual(result.returncode, 1)
        self.assertIn("program_complete=FAIL", result.stdout)

    def test_invalid_float_bits_fails(self) -> None:
        e84_log = E84_PASS_LOG.replace("0xbca6e43b", "0xnot-a-float")
        result = self.run_validator(FVP_PASS_LOG, e84_log)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid float_bits", result.stderr)

    def test_invalid_tolerance_fails(self) -> None:
        result = self.run_validator(FVP_PASS_LOG, E84_PASS_LOG, tolerance="0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tolerance", result.stderr)


if __name__ == "__main__":
    unittest.main()