import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/memory-bank-findings/scripts/findings.py"
NAMESPACE = {"__file__": str(SCRIPT), "__name__": "findings_test_module"}
exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), NAMESPACE)


def report(title="Observed access boundary", state="Validated", informational=False, incident=False):
    scoring = "" if incident else (
        "## CVSSv3.1 Score and Severity\n\n"
        + ("**CVSSv3.1 score: 0.0 (Informational)**\nVector: N/A\n" if informational else
           "**CVSSv3.1 score: 9.8 (Critical)**\n"
           "Vector: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`\n\n"
           "| Metric | Value | Metric | Value |\n|---|---|---|---|\n"
           "| Attack Vector | Network | Scope | Unchanged |\n"
           "| Attack Complexity | Low | Confidentiality | High |\n"
           "| Required Privileges | None | Integrity | High |\n"
           "| User Interaction | None | Availability | High |\n") + "\n")
    analysis = ("### Statement of fact\n\nA reviewed ART-0001 recorded the event.\n\n"
                "### Inference\n\nThe observed event supports the scoped conclusion.\n\n"
                "### Alternative explanations considered\n\nTest traffic was excluded.\n\n") if incident else ""
    incident_headers = "**Finding type:** Incident conclusion\n**Confidence:** High — reviewed corroboration.\n" if incident else ""
    return (f"# {title}\n\n**Status:** `{state}`\n**Workstream:** Application\n"
            "**Date:** 2026-10-04\n" + incident_headers + "\n" + scoring
            + "## Affected Assets\n\n**Origin:** Application\n\nThe isolated service was affected.\n\n"
            "## Description\n\nObserved behavior was reproduced within the authorized test scope.\n\n"
            + analysis + "### Affected assets\n\nThe test service.\n\n"
            "### Steps to reproduce / observed behavior\n\n1. Review the scoped test observation.\n\n"
            "## Impact\n\n**Technical.** The observed access boundary was crossed.\n\n"
            "**Business.** The scoped test demonstrates a supported business risk.\n\n"
            "## Remediation\n\n1. Enforce the documented boundary.\n\n"
            "## References\n\n- [Guidance](https://example.org/guidance)\n\n"
            "*Evidence source: Reviewed scoped test observation; no broader scope was tested.*\n")


class FindingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="findings-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / ".memory-bank").mkdir()
        (self.root / "findings").mkdir()
        self.profile("pentest")
        self.log = self.root / ".memory-bank/findings.md"
        self.log.write_text("# Findings\n\n## Entries\n", encoding="utf-8")
        self.index = self.root / "findings/README.md"
        self.index.write_text((ROOT / "templates/findings/pentest/README.md").read_text(encoding="utf-8"), encoding="utf-8")

    def profile(self, value, enabled=True):
        (self.root / ".memory-bank/layout.json").write_text(json.dumps({"schema": 1, "profile": value, "findings": enabled}), encoding="utf-8")

    def entry(self, title="Observed access boundary", state="Validated", path="", legacy=False):
        heading = "F-001: " + title if legacy else title
        with self.log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n### {heading}\n- Status: `{state}`\n- Evidence references: reviewed ART-0001\n- Report path: {path}\n- Status history: 2026-10-01 Hypothesis; 2026-10-04 {state}\n")

    def file(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def canonical(self, text=None, title="Observed access boundary", state="Validated", slug="observed-access"):
        relative = f"findings/application/{slug}/finding.md"
        self.entry(title, state, relative)
        return self.file(relative, text if text is not None else report(title, state))

    def cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = NAMESPACE["main"](["--root", str(self.root), *args])
        return code, output.getvalue(), errors.getvalue()

    def promote(self, title="Observed access boundary", workstream="application", slug="observed-access", source="draft/finding.md", extra=()):
        return self.cli("promote", "--title", title, "--workstream", workstream,
                        "--slug", slug, "--source", source, *extra)

    def test_explicit_profile_cannot_override_installed_domain(self):
        self.canonical()
        code, selected, _ = self.cli("--profile", "incident-response", "list")
        self.assertEqual(1, code)
        self.assertEqual("", selected)

    def test_suspected_ir_promotion_and_selection_remain_provisional(self):
        self.profile("incident-response")
        self.entry(state="Suspected")
        draft = self.file("draft/finding.md", report(state="Suspected", incident=True))
        self.assertEqual(1, self.promote()[0])
        self.assertTrue(draft.exists())
        self.assertEqual(0, self.promote(extra=("--include-suspected",))[0])
        target = self.root / "findings/application/observed-access/finding.md"
        self.assertIn("**Status:** `Suspected`", target.read_text())
        self.assertIn("**Provisional:** Yes", target.read_text())
        self.assertNotIn("CVSS", target.read_text())
        self.assertEqual("", self.cli("list")[1])
        self.assertIn("Suspected\tObserved access boundary\t", self.cli("list", "--include-suspected")[1])

    def test_complete_scored_report_has_no_warnings(self):
        self.canonical()
        self.assertEqual((0, "", ""), self.cli("lint"))

    def test_complete_informational_report_omits_grid(self):
        self.canonical(report(state="Informational", informational=True), state="Informational")
        self.assertEqual((0, "", ""), self.cli("lint"))
        code, selected, errors = self.cli("list")
        self.assertEqual(0, code)
        self.assertIn("Informational\tObserved access boundary\t", selected)
        self.assertEqual("", errors)

    def test_complete_incident_report_preserves_domain_without_cvss(self):
        self.profile("incident-response")
        self.canonical(report(state="Confirmed", incident=True), state="Confirmed")
        self.assertEqual((0, "", ""), self.cli("lint"))
        self.assertIn("Confirmed\t", self.cli("list")[1])

    def test_ir_cvss_requires_explicit_vulnerability_type(self):
        self.profile("incident-response")
        prose = report(state="Confirmed", incident=True).replace("## Affected Assets", "## CVSSv3.1 Score and Severity\n\n**CVSSv3.1 score: 0.0 (Informational)**\nVector: N/A\n\n## Affected Assets")
        target = self.canonical(prose, state="Confirmed")
        self.assertIn("without explicit", self.cli("lint")[2])
        target.write_text(prose.replace("**Finding type:** Incident conclusion", "**Finding type:** Vulnerability"), encoding="utf-8")
        self.assertEqual((0, "", ""), self.cli("lint"))

    def test_cvss_vectors_roundup_and_zero_impact(self):
        calculate = NAMESPACE["cvss_base"]
        cases = [
            ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
            ("AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", 10.0),
            ("AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N", 4.3),
            ("AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", 5.3),
            ("AV:N/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:N", 0.0),
        ]
        for vector, expected in cases:
            with self.subTest(vector=vector):
                self.assertEqual(expected, calculate("CVSS:3.1/" + vector)[0])
        for vector in ("CVSS:3.0/AV:N", "CVSS:3.1/AV:N/AV:L", "CVSS:3.1/AV:?"):
            with self.assertRaises(ValueError):
                calculate(vector)

    def test_cvss_severity_boundaries(self):
        for score, expected in [(0, "Informational"), (.1, "Low"), (3.9, "Low"), (4, "Medium"), (6.9, "Medium"), (7, "High"), (8.9, "High"), (9, "Critical"), (10, "Critical")]:
            with self.subTest(score=score):
                self.assertEqual(expected, NAMESPACE["severity"](score))

    def test_cvss_score_vector_and_grid_disagreements_warn_only(self):
        self.canonical(report().replace("9.8 (Critical)", "8.0 (Medium)").replace("| Network |", "| Local |"))
        code, _, warnings = self.cli("lint")
        self.assertEqual(0, code)
        self.assertIn("severity does not match", warnings)
        self.assertIn("calculated vector", warnings)
        self.assertIn("metric grid missing or inconsistent: Attack Vector", warnings)

    def test_informational_rejects_fabricated_grid_and_vector_as_warnings(self):
        self.canonical(report(state="Informational").replace("9.8 (Critical)", "0.0 (Informational)"), state="Informational")
        code, _, warnings = self.cli("lint")
        self.assertEqual(0, code)
        self.assertIn("N/A vector and no metric grid", warnings)

    def test_sections_and_header_log_mismatch_are_warnings(self):
        self.canonical(report(state="Hypothesis").replace("## Remediation", "## Fix"))
        code, _, warnings = self.cli("lint")
        self.assertEqual(0, code)
        self.assertIn("working-log truth", warnings)
        self.assertIn("Remediation", warnings)
        self.assertIn("provisional label", warnings)
        self.assertEqual("", self.cli("list")[1])

    def test_missing_and_quoted_nested_assets(self):
        prose = report() + '\n![Quoted](<assets/nested/évidence one(2).png> "caption")\n![Missing](assets/missing.png)\n'
        target = self.canonical(prose)
        self.file(str(target.parent.relative_to(self.root) / "assets/nested/évidence one(2).png"), "synthetic image")
        code, _, warnings = self.cli("lint")
        self.assertEqual(0, code)
        self.assertEqual(1, warnings.count("does not resolve"))
        self.assertNotIn("évidence", warnings)

    def test_reference_html_and_parenthesized_asset_links(self):
        target = self.canonical(report() + '\n![One](assets/capture(1).png "caption")\n![Two][shot]\n[shot]: <assets/nested image.png> "caption"\n<img src="assets/nested image.png">\n')
        for name in ("capture(1).png", "nested image.png"):
            self.file(str(target.parent.relative_to(self.root) / "assets" / name), "synthetic image")
        self.assertEqual((0, "", ""), self.cli("lint"))

    def test_assets_cannot_escape_by_traversal_encoding_or_symlink(self):
        target = self.canonical(report() + '\n![Traversal](../../../.memory-bank/sensitive.txt)\n![Encoded](%2Ftmp%2Fprivate.txt)\n![Symlink](assets/link.txt)\n')
        private = self.file(".memory-bank/sensitive.txt", "password=do-not-read-or-echo")
        assets = target.parent / "assets"
        assets.mkdir()
        (assets / "link.txt").symlink_to(private)
        code, _, warnings = self.cli("lint")
        self.assertEqual(0, code)
        self.assertEqual(3, warnings.count("containment"))
        self.assertNotIn("do-not-read-or-echo", warnings)
        self.assertNotIn("credential assignment", warnings)

    def test_suspect_values_are_never_echoed_from_report_or_text_asset(self):
        token = "SYNTHETIC-DO-NOT-ECHO-12345"
        email = "synthetic.person@example.invalid"
        target = self.canonical(report() + f'\npassword={token}\nContact: {email}\n[Evidence](assets/review.txt)\n')
        self.file(str(target.parent.relative_to(self.root) / "assets/review.txt"), f"api_key={token}\n")
        code, output, warnings = self.cli("lint")
        self.assertEqual(0, code)
        self.assertIn("credential assignment", warnings)
        self.assertIn("email-like", warnings)
        self.assertIn("assets/review.txt:1", warnings)
        self.assertNotIn(token, output + warnings)
        self.assertNotIn(email, output + warnings)

    def test_promote_consumes_prose_sets_log_status_and_backlinks(self):
        self.entry()
        draft = self.file("draft/finding.md", report(state="Hypothesis"))
        original = self.log.read_text(encoding="utf-8")
        code, output, warnings = self.promote()
        self.assertEqual(0, code, warnings)
        self.assertFalse(draft.exists())
        self.assertEqual("", warnings)
        self.assertIn("findings/application/observed-access/finding.md", output)
        self.assertIn("**Status:** `Validated`", (self.root / output.strip()).read_text(encoding="utf-8"))
        updated = self.log.read_text(encoding="utf-8")
        self.assertTrue(updated.startswith(original.replace("- Report path: ", "- Report path: findings/application/observed-access/finding.md")))
        self.assertIn("- Promotion: ", updated)
        self.assertIn("[Observed access boundary](application/observed-access/finding.md)", self.index.read_text(encoding="utf-8"))

    def test_promotion_rejects_source_symlink_components_without_changes(self):
        self.entry()
        draft = self.file(".memory-bank/sensitive/case/finding.md",
                          report() + "\n[Evidence](assets/proof.txt)\n")
        asset = self.file(".memory-bank/sensitive/case/assets/proof.txt", "synthetic private proof")
        alias = self.root / "draft-alias"
        alias.symlink_to(draft.parent, target_is_directory=True)
        leaf = self.root / "draft-link.md"
        leaf.symlink_to(draft)
        original = {path: path.read_bytes() for path in (draft, asset, self.log, self.index)}
        for source in ("draft-alias/finding.md", "draft-link.md",
                       "draft-alias/../case/finding.md"):
            with self.subTest(source=source):
                code, output, errors = self.promote(source=source)
                self.assertEqual(1, code, errors)
                self.assertEqual("", output)
                self.assertIn("symlink component", errors)
                for path, content in original.items():
                    self.assertEqual(content, path.read_bytes())
                self.assertTrue(alias.is_symlink())
                self.assertTrue(leaf.is_symlink())
                self.assertFalse((self.root / "findings/application").exists())

    def test_direct_authored_source_is_not_rejected_by_directory_name(self):
        self.entry()
        draft = self.file(".memory-bank/sensitive/case/finding.md",
                          report() + "\n[Evidence](assets/nested/proof.txt)\n")
        asset = self.file(".memory-bank/sensitive/case/assets/nested/proof.txt", "synthetic proof")
        code, output, warnings = self.promote(source=draft.relative_to(self.root).as_posix())
        self.assertEqual(0, code, warnings)
        self.assertEqual("", warnings)
        self.assertFalse(draft.exists())
        target = self.root / output.strip()
        self.assertEqual(asset.read_bytes(), (target.parent / "assets/nested/proof.txt").read_bytes())
        self.assertIn("assets/nested/proof.txt", target.read_text(encoding="utf-8"))
        self.assertIn("- Promotion: ", self.log.read_text(encoding="utf-8"))
        self.assertIn("[Observed access boundary]", self.index.read_text(encoding="utf-8"))

    def test_promotion_rejects_nested_and_leaf_asset_symlinks_without_changes(self):
        self.entry()
        proof = self.file("draft/assets/original/proof.txt", "synthetic proof")
        private = self.file(".memory-bank/sensitive/proof.txt", "synthetic private proof")
        (self.root / "draft/assets/nested").symlink_to(proof.parent, target_is_directory=True)
        (self.root / "draft/assets/private").symlink_to(private.parent, target_is_directory=True)
        (self.root / "draft/assets/proof-link.txt").symlink_to(proof)
        draft = self.file("draft/finding.md", report())
        original = {path: path.read_bytes() for path in (proof, private, self.log, self.index)}
        for link in ("assets/nested/proof.txt", "assets/private/proof.txt",
                     "assets/proof-link.txt", "assets/nested/../original/proof.txt"):
            with self.subTest(link=link):
                prose = report() + "\n[Normal](assets/original/proof.txt)\n[Alias](" + link + ")\n"
                draft.write_text(prose, encoding="utf-8")
                code, output, errors = self.promote()
                self.assertEqual(1, code, errors)
                self.assertEqual("", output)
                self.assertIn("symlink component", errors)
                self.assertEqual(prose, draft.read_text(encoding="utf-8"))
                for path, content in original.items():
                    self.assertEqual(content, path.read_bytes())
                self.assertFalse((self.root / "findings/application").exists())

    def test_existing_report_promotion_rejects_symlinked_assets_before_updates(self):
        target = self.canonical(report(state="Hypothesis") + "\n[Evidence](assets/alias/proof.txt)\n")
        proof = self.file("findings/application/observed-access/assets/original/proof.txt", "synthetic proof")
        (target.parent / "assets/alias").symlink_to(proof.parent, target_is_directory=True)
        original = {path: path.read_bytes() for path in (target, proof, self.log, self.index)}
        code, output, errors = self.promote(source=target.relative_to(self.root).as_posix())
        self.assertEqual(1, code, errors)
        self.assertEqual("", output)
        self.assertIn("symlink component", errors)
        for path, content in original.items():
            self.assertEqual(content, path.read_bytes())

    def test_unicode_title_slug_and_assets_are_report_safe(self):
        title = 'Évidence [boundary] | "quoted"'
        self.entry(title)
        self.file("draft/finding.md", report(title) + '\n![Proof](<assets/nested/évidence one(2).png> "caption")\n')
        self.file("draft/assets/nested/évidence one(2).png", "synthetic image")
        code, output, warnings = self.promote(title, "sécurité", "évidence-boundary")
        self.assertEqual(0, code, warnings)
        self.assertEqual("", warnings)
        target = self.root / output.strip()
        self.assertTrue((target.parent / "assets/nested/évidence one(2).png").is_file())
        self.assertIn("assets/nested/%C3%A9vidence%20one%282%29.png", target.read_text(encoding="utf-8"))
        self.assertIn("&#124;", self.index.read_text(encoding="utf-8"))
        self.assertIn("s%C3%A9curit%C3%A9", self.index.read_text(encoding="utf-8"))

    def test_hypothesis_requires_explicit_promotion_and_selection(self):
        self.entry(state="Hypothesis")
        draft = self.file("draft/finding.md", report(state="Hypothesis"))
        self.assertEqual(1, self.promote()[0])
        self.assertTrue(draft.exists())
        code, output, warnings = self.promote(extra=("--include-hypothesis",))
        self.assertEqual(0, code, warnings)
        self.assertIn("**Provisional:** Yes", (self.root / output.strip()).read_text(encoding="utf-8"))
        self.assertEqual("", self.cli("list")[1])
        self.assertIn("Hypothesis\t", self.cli("list", "--include-hypothesis")[1])

    def test_ineligible_states_cannot_be_promoted_even_with_hypothesis_flag(self):
        for profile, state in [("pentest", "False Positive"), ("incident-response", "Suspected"), ("incident-response", "Ruled Out")]:
            with self.subTest(profile=profile, state=state):
                self.profile(profile)
                self.log.write_text("# Findings\n\n## Entries\n", encoding="utf-8")
                self.entry(state=state)
                draft = self.file("draft/finding.md", report(state=state, incident=profile == "incident-response"))
                self.assertEqual(1, self.promote(extra=("--include-hypothesis",))[0])
                self.assertTrue(draft.exists())

    def test_sync_existing_false_positive_retains_history_and_report(self):
        target = self.canonical(report(state="Hypothesis"), state="False Positive")
        original = self.log.read_bytes()
        code, _, errors = self.cli("sync")
        self.assertEqual(0, code, errors)
        self.assertEqual(original, self.log.read_bytes())
        self.assertIn("**Status:** `False Positive`", target.read_text(encoding="utf-8"))
        self.assertNotIn("**Provisional:**", target.read_text(encoding="utf-8"))
        self.assertEqual("", self.cli("list", "--include-hypothesis")[1])
        self.assertIn("False Positive", self.index.read_text(encoding="utf-8"))

    def test_sync_legacy_ir_backlink_preserves_history(self):
        self.profile("incident-response")
        self.entry(state="Ruled Out", legacy=True)
        target = self.file("findings/application/observed-access/finding.md", report(state="Confirmed", incident=True))
        old = self.log.read_text(encoding="utf-8")
        code, _, errors = self.cli("sync")
        self.assertEqual(0, code, errors)
        updated = self.log.read_text(encoding="utf-8")
        self.assertEqual(old.replace("- Report path: ", "- Report path: findings/application/observed-access/finding.md"), updated)
        self.assertIn("### F-001: Observed access boundary", updated)
        self.assertIn("**Status:** `Ruled Out`", target.read_text(encoding="utf-8"))
        self.assertEqual("", self.cli("list")[1])

    def test_sync_duplicate_titles_fails_before_writing_headers(self):
        first = self.canonical(report(state="Hypothesis"))
        self.file("findings/other/duplicate/finding.md", report(state="Hypothesis"))
        original = first.read_bytes()
        self.assertEqual(1, self.cli("sync")[0])
        self.assertEqual(original, first.read_bytes())

    def test_sync_missing_index_preserves_headers_and_log(self):
        target = self.canonical(report(state="Hypothesis"))
        original, log = target.read_bytes(), self.log.read_bytes()
        self.index.unlink()
        self.assertEqual(1, self.cli("sync")[0])
        self.assertEqual(original, target.read_bytes())
        self.assertEqual(log, self.log.read_bytes())

    def test_existing_report_registration_does_not_duplicate_or_remove_source(self):
        target = self.canonical()
        code, _, errors = self.promote(source=str(target.relative_to(self.root)))
        self.assertEqual(0, code, errors)
        self.assertTrue(target.exists())
        self.assertEqual(1, len(list((self.root / "findings").rglob("finding.md"))))

    def test_existing_report_is_never_overwritten_by_draft(self):
        target = self.canonical()
        draft = self.file("draft/finding.md", report() + "\nDifferent narrative.\n")
        original = target.read_bytes()
        self.assertEqual(1, self.promote()[0])
        self.assertEqual(original, target.read_bytes())
        self.assertTrue(draft.exists())

    def test_templates_are_never_discovered_or_promoted(self):
        self.file("findings/_TEMPLATE/finding.md", "# Unfinished template\n")
        self.assertEqual((0, "", ""), self.cli("lint"))
        self.assertEqual((0, "", ""), self.cli("list"))
        self.assertEqual(1, self.cli("lint", "findings/_TEMPLATE/finding.md")[0])
        self.entry("Unfinished template")
        self.assertEqual(1, self.promote("Unfinished template", source="findings/_TEMPLATE/finding.md")[0])

    def test_real_input_failures_nonzero_and_do_not_echo_os_details(self):
        self.assertEqual(1, self.cli("lint", "findings/missing/finding.md")[0])
        self.canonical()
        with patch.object(Path, "read_text", side_effect=PermissionError("SYNTHETIC SECRET DETAIL")):
            code, output, errors = self.cli("lint")
        self.assertEqual(1, code)
        self.assertNotIn("SYNTHETIC SECRET DETAIL", output + errors)

    def test_explicit_profile_fallback_and_general_opt_in(self):
        (self.root / ".memory-bank/layout.json").unlink()
        self.assertEqual(1, self.cli("lint")[0])
        self.assertEqual(0, self.cli("--profile", "pentest", "lint")[0])
        self.assertEqual(1, self.cli("--profile", "general-project", "lint")[0])
        self.profile("general-project")
        self.assertEqual(0, self.cli("lint")[0])
        self.profile("general-project", enabled=False)
        self.assertEqual(1, self.cli("lint")[0])

    def test_standalone_executable_list(self):
        self.canonical()
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "list"], capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Validated\tObserved access boundary\tfindings/application/observed-access/finding.md", result.stdout)

    def test_discovered_symlink_report_is_not_read(self):
        private = self.file(".memory-bank/private-source.txt", "password=SYNTHETIC-NEVER-ECHO")
        target = self.root / "findings/application/escape/finding.md"
        target.parent.mkdir(parents=True)
        target.symlink_to(private)
        code, output, errors = self.cli("lint")
        self.assertEqual(1, code)
        self.assertIn("containment", errors)
        self.assertNotIn("SYNTHETIC-NEVER-ECHO", output + errors)

    def test_promotion_never_copies_symlinked_private_asset_directory(self):
        self.entry()
        draft = self.file("draft/finding.md", report() + "\n[Evidence](assets/private.txt)\n")
        private = self.file(".memory-bank/opaque/private.txt", "password=SYNTHETIC-NEVER-COPY")
        (self.root / "draft/assets").symlink_to(private.parent, target_is_directory=True)
        original = {path: path.read_bytes() for path in (draft, private, self.log, self.index)}
        code, output, errors = self.promote()
        self.assertEqual(1, code, errors)
        self.assertEqual("", output)
        self.assertIn("symlink component", errors)
        self.assertFalse((self.root / "findings/application").exists())
        for path, content in original.items():
            self.assertEqual(content, path.read_bytes())
        self.assertTrue((self.root / "draft/assets").is_symlink())
        self.assertNotIn("SYNTHETIC-NEVER-COPY", errors)

    def test_blank_backlink_does_not_consume_following_history(self):
        self.entry()
        entry = NAMESPACE["log_entries"](self.log.read_text(encoding="utf-8"))["Observed access boundary"]
        self.assertEqual("", entry["path"])
        self.assertEqual("Validated", entry["status"])

    def test_markdown_backlink_with_unicode_is_read(self):
        relative = "findings/sécurité/évidence/finding.md"
        self.entry(path="[Observed access boundary](findings/s%C3%A9curit%C3%A9/%C3%A9vidence/finding.md)")
        self.file(relative, report())
        self.assertIn(relative, self.cli("list")[1])

    def test_backlink_is_added_without_changing_historical_subsections(self):
        self.log.write_text("# Findings\n\n## Entries\n\n### Observed access boundary\n- Status: Validated\n\n#### Status history\n- 2026-10-01: Hypothesis recorded.\n\n## Gaps\nUnchanged.\n", encoding="utf-8")
        self.file("findings/application/observed-access/finding.md", report())
        self.assertEqual(0, self.cli("sync")[0])
        text = self.log.read_text(encoding="utf-8")
        self.assertIn("#### Status history\n- 2026-10-01: Hypothesis recorded.\n\n## Gaps\nUnchanged.\n", text)
        self.assertIn("- Report path: findings/application/observed-access/finding.md", text)


if __name__ == "__main__":
    unittest.main()
