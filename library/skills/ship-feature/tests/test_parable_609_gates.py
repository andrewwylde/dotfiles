#!/usr/bin/env python3
"""Unit tests for PARABLE-609 campaign / approval / visual gates (user-scoped)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from campaign_paths import (  # noqa: E402
    harness_kind_for,
    is_campaign_child,
    normalize_ticket,
    resolve_campaign,
    sha256_text,
)
from approval_gate import approval_path, validate_payload  # noqa: E402
from reference_audit_gate import validate as validate_audit, write_stub  # noqa: E402
from visual_qa_gate import (  # noqa: E402
    cleanup_check,
    harness_provenance,
    write_baseline,
    write_after,
    validate_after,
    write_matrix_template,
)


class CampaignDetectionTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_ticket("parable-644"), "PARABLE-644")

    def test_children(self):
        self.assertTrue(is_campaign_child("PARABLE-644"))
        self.assertTrue(is_campaign_child("PARABLE-641"))
        self.assertFalse(is_campaign_child("PARABLE-9999"))

    def test_parable_1045_resolves_to_613(self):
        resolved = resolve_campaign("PARABLE-1045")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["campaign_id"], "PARABLE-613")
        self.assertEqual(harness_kind_for("PARABLE-1045"), "app_route")
        self.assertTrue(is_campaign_child("PARABLE-1045"))


class ApprovalGateTests(unittest.TestCase):
    def test_rejects_short_quote(self):
        payload = {
            "RUN_BY_SKILL": "ship-feature",
            "HUMAN_APPROVAL": "implementation",
            "TICKET": "PARABLE-644",
            "APPROVED_AT": "now",
            "APPROVAL_QUOTE": "short",
            "plan_hash": "a",
            "campaign_hash": "b",
            "reference_fingerprint": "c",
        }
        errors = validate_payload(payload, "implementation", "PARABLE-644")
        self.assertTrue(any("20" in e for e in errors))

    def test_approve_and_validate_roundtrip(self):
        ticket = "PARABLE-644"
        path = approval_path(ticket, "implementation")
        # clean previous
        if path.exists():
            path.unlink()
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "approval_gate.py"),
                "--kind",
                "implementation",
                "--ticket",
                ticket,
                "--approve",
                "--quote",
                "APPROVE IMPLEMENTATION PARABLE-644 as reviewed",
                "--plan-hash",
                "planhash",
                "--campaign-hash",
                "camphash",
                "--ref-fp",
                "reffp",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc2 = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "approval_gate.py"),
                "--kind",
                "implementation",
                "--ticket",
                ticket,
                "--validate",
                "--expect-plan-hash",
                "planhash",
                "--expect-campaign-hash",
                "camphash",
                "--expect-ref-fp",
                "reffp",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)
        # stale hash fails
        proc3 = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "approval_gate.py"),
                "--kind",
                "implementation",
                "--ticket",
                ticket,
                "--validate",
                "--expect-plan-hash",
                "CHANGED",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc3.returncode, 0)


class ReferenceAuditTests(unittest.TestCase):
    def test_write_and_validate(self):
        ticket = "PARABLE-631"
        write_stub(ticket, "abc123deadbeef", [
            "apps/web-app/src/lib/domains/plots/components/ponder-admin-page/PonderAdminPage.component.svelte",
            "apps/web-app/src/lib/domains/plots/components/monaco-sql-editor",
            "apps/web-app/src/lib/domains/plots/components/tree-list",
            "apps/web-app/src/lib/domains/admin/components/bottom-pane",
        ], "dirty")
        # stub still has TODO classifications but mentions preserve|migrate|discard in table header
        result = validate_audit(ticket, "abc123deadbeef")
        self.assertTrue(result["passed"], result)


class VisualGateTests(unittest.TestCase):
    def test_baseline_write(self):
        result = write_baseline("PARABLE-640", "http://127.0.0.1:1/nope", [], force=True)
        self.assertTrue(result["written"])
        self.assertEqual(result["payload"]["status"], "BLOCKED")

    def test_after_validate_requires_mapping(self):
        write_baseline("PARABLE-636", "http://127.0.0.1:1/nope", [], force=True)
        # force BLOCKED baseline to allow after for structure — validate_after still needs mapping
        write_after("PARABLE-636", "deadbeef", [{"id": "s1"}], [], force=True, region="bottomPane")
        result = validate_after("PARABLE-636", "deadbeef")
        self.assertFalse(result["passed"])
        written = write_after(
            "PARABLE-636",
            "deadbeef",
            [{"id": "s1"}],
            [{"ac_id": "AC-1", "assertions": [{"selector": "x", "expected": "visible"}]}],
            force=True,
            region="bottomPane",
        )
        self.assertEqual(written["payload"]["harness"]["kind"], "persistent_external")
        self.assertEqual(written["payload"]["harness"]["region"], "bottomPane")
        self.assertFalse(written["payload"]["harness"]["cleanup_required"])
        # baseline still BLOCKED without ack — validate_after only checks baseline exists
        result2 = validate_after("PARABLE-636", "deadbeef")
        self.assertTrue(result2["passed"], result2)

    def test_matrix_template_writes_region_file(self):
        result = write_matrix_template("PARABLE-641", region="editor", force=True)
        self.assertTrue(result["written"], result)
        self.assertEqual(result["payload"]["region"], "editor")
        self.assertTrue(result["payload"]["rows"])

    def test_matrix_template_app_route_1045(self):
        result = write_matrix_template("PARABLE-1045", force=True)
        self.assertTrue(result["written"], result)
        self.assertEqual(result.get("harness_kind"), "app_route")
        self.assertEqual(result["payload"]["harness_kind"], "app_route")
        self.assertTrue(any(r["id"] == "rows" for r in result["payload"]["rows"]))

    def test_app_route_after_provenance(self):
        write_baseline("PARABLE-1045", "http://127.0.0.1:1/nope", [], force=True)
        written = write_after(
            "PARABLE-1045",
            "abc123",
            [{"id": "rows"}],
            [{"ac_id": "AC-1", "assertions": [{"selector": "bottom-pane", "expected": "visible"}]}],
            force=True,
            workspace=Path("/tmp/fake-pr"),
        )
        self.assertEqual(written["payload"]["harness"]["kind"], "app_route")
        self.assertEqual(written["payload"]["harness"]["path"], "/admin/ponder")
        result = validate_after("PARABLE-1045", "abc123")
        self.assertTrue(result["passed"], result)
        prov = harness_provenance("PARABLE-1045", workspace=Path("/tmp/fake-pr"))
        self.assertEqual(prov["kind"], "app_route")
        self.assertIn("admin-ponder", prov["spec_path"])

    def test_cleanup_check_clean_temp_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
            (root / "README").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "add", "README"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
            # no origin/main — cleanup still scans status
            result = cleanup_check(root)
            self.assertTrue(result["passed"], result)


class CampaignGateScriptTests(unittest.TestCase):
    def test_non_campaign_skip(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "campaign_context_gate.py"),
                "--ticket",
                "PARABLE-1",
                "--check-only",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertFalse(data["triggered"])

    def test_campaign_triggered(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "campaign_context_gate.py"),
                "--ticket",
                "PARABLE-644",
                "--check-only",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["triggered"])
        self.assertIn("reference_sha", data)

    def test_613_campaign_triggered(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "campaign_context_gate.py"),
                "--ticket",
                "PARABLE-1045",
                "--check-only",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["triggered"])
        self.assertEqual(data["campaign"], "PARABLE-613")
        self.assertEqual(data["harness_kind"], "app_route")
        self.assertEqual(data["git_base"], "origin/feature/parable-editor")


class StageComplianceCampaignTests(unittest.TestCase):
    def test_stage5_pr_blocks_without_visual(self):
        # Ensure campaign gate is triggered via env workspace later; call check functions
        from stage_compliance_check import check_stage5_pr

        # Without workspace campaign-gate.json, ticket in task id still triggers via is_campaign_child
        checks = check_stage5_pr("parable-644-property-picker")
        names = {c.name: c.passed for c in checks}
        self.assertIn("campaign-mode", names)
        # visual approval should fail
        self.assertFalse(names.get("visual-approval", True))


if __name__ == "__main__":
    _ = sha256_text
    unittest.main()
