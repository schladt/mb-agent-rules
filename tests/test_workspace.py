import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills/memory-bank-workflow/scripts/workspace.py"
PUBLIC_SECTIONS = ("Progress", "Milestones", "Blockers", "Next Steps", "Client Actions")
STATUS = "# Project Status\n\n## Publishable\n\n" + "\n\n".join(
    "### " + section + "\n- Not yet reported." for section in PUBLIC_SECTIONS
) + "\n\n## Internal\nPrivate analytical notes stay here.\n"


def load_workspace():
    namespace = {"__file__": str(SCRIPT), "__name__": "workspace_test_module"}
    exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), namespace)
    return namespace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mb-workspace-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.bank = self.root / ".memory-bank"
        for relative in ("planning/archive", "incoming", "references/raw", "sensitive", "artifacts", "runtime", "backups"):
            (self.bank / relative).mkdir(parents=True, mode=0o700, exist_ok=True)
        self.configure()
        for name, content in {
            "project-status.md": STATUS,
            "activeContext.md": "# Active Context\n\nPrior working history.\n",
            "progress.md": "# Progress\n\nPrior completion history.\n",
            "sensitiveDataPolicy.md": "# Sensitive Data Policy\n\nNo plaintext credentials in memory.\n",
            "references/reference.md": "# References\n",
        }.items():
            (self.bank / name).write_text(content, encoding="utf-8")

    def configure(self, profile="pentest", external_status=True, findings=None):
        (self.bank / "layout.json").write_text(json.dumps({
            "schema": 1, "profile": profile, "skills_dir": ".agents/skills",
            "findings": profile in ("pentest", "incident-response") if findings is None else findings,
            "external_status": external_status,
        }), encoding="utf-8")

    def cli(self, *arguments, expected=0):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *arguments],
            cwd=self.root, capture_output=True, text=True, check=False,
        )
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        return result

    def receipt(self, name):
        return json.loads((self.bank / "runtime" / name).read_text(encoding="utf-8"))

    def drop(self, name="source.txt", contents=b"synthetic source bytes\n"):
        path = self.bank / "incoming" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        return path

    def intake(self, source, *flags, kind="reference", expected=0):
        return self.cli("intake", str(source.relative_to(self.root)), "--kind", kind,
                        "--origin", "Owner-provided synthetic source", *flags, expected=expected)

    def direct(self, namespace, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = namespace["main"](["--root", str(self.root), *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def legacy_status(self):
        content = ("# Project Status\n\n" + "\n\n".join(
            "## " + section + "\n\n- Previously reported work." for section in PUBLIC_SECTIONS
        ) + "\n").encode()
        (self.root / "project-status.md").write_bytes(content)
        receipt = {
            "schema": 1, "state": "generated",
            "source_sha256": hashlib.sha256((self.bank / "project-status.md").read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(content).hexdigest(),
        }
        (self.bank / "runtime/status-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        return content

    def test_legacy_status_cutover_preserves_backup_and_uses_current_source(self):
        legacy = self.legacy_status()
        source = STATUS.replace("- Not yet reported.", "- Access review is complete; export review is next.", 1)
        (self.bank / "project-status.md").write_text(source, encoding="utf-8")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.cli("status", "--check", expected=1)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes()
                                  for p in self.root.rglob("*") if p.is_file()})
        self.cli("status")
        self.assertFalse((self.root / "project-status.md").exists())
        self.assertIn("Access review is complete", (self.root / "team-status.md").read_text())
        self.assertEqual(source, (self.bank / "project-status.md").read_text())
        preserved = []
        for path in (self.bank / "backups").glob("workflow-*/manifest.json"):
            for record in json.loads(path.read_text())["files"]:
                if record["path"] == "project-status.md" and record["existed"]:
                    preserved.append((path.parent / record["backup"]).read_bytes())
        self.assertEqual([legacy], preserved)
        self.cli("status", "--check")

    def test_unowned_or_edited_legacy_status_is_not_removed(self):
        legacy = self.legacy_status()
        edited = legacy + b"\nOwner's manual addition.\n"
        (self.root / "project-status.md").write_bytes(edited)
        result = self.cli("status")
        self.assertEqual(edited, (self.root / "project-status.md").read_bytes())
        self.assertIn("warning:", result.stderr)
        (self.root / "team-status.md").unlink()
        (self.bank / "runtime/status-receipt.json").unlink()
        result = self.cli("status")
        self.assertEqual(edited, (self.root / "project-status.md").read_bytes())
        self.assertIn("warning:", result.stderr)

    def test_status_cutover_rejects_existing_team_document(self):
        legacy = self.legacy_status()
        owner = b"# Team notes\n\nOwner-managed coordination.\n"
        (self.root / "team-status.md").write_bytes(owner)
        self.cli("status", expected=2)
        self.assertEqual(legacy, (self.root / "project-status.md").read_bytes())
        self.assertEqual(owner, (self.root / "team-status.md").read_bytes())

    def test_malformed_legacy_status_cutover_preserves_output_and_can_retry(self):
        legacy = self.legacy_status()
        (self.bank / "project-status.md").write_text("# Invalid source\n")
        self.cli("status", expected=2)
        self.assertEqual(legacy, (self.root / "project-status.md").read_bytes())
        self.assertFalse((self.root / "team-status.md").exists())
        (self.bank / "project-status.md").write_text(STATUS)
        self.cli("status")
        self.assertFalse((self.root / "project-status.md").exists())
        self.cli("status", "--check")

    def test_failed_legacy_status_cutover_restores_previous_document(self):
        legacy = self.legacy_status()
        namespace = load_workspace()
        replace = namespace["os"].replace
        receipt_path = self.bank / "runtime/status-receipt.json"
        failed = False
        def fail_receipt_once(source, destination):
            nonlocal failed
            if Path(destination) == receipt_path and not failed:
                failed = True
                raise OSError("synthetic receipt failure")
            return replace(source, destination)
        with mock.patch.object(namespace["os"], "replace", side_effect=fail_receipt_once):
            code, _, _ = self.direct(namespace, "status")
        self.assertEqual(2, code)
        self.assertEqual(legacy, (self.root / "project-status.md").read_bytes())
        self.assertFalse((self.root / "team-status.md").exists())
        self.cli("status")
        self.assertFalse((self.root / "project-status.md").exists())
        self.cli("status", "--check")

    def test_failed_legacy_removal_rolls_back_new_team_document(self):
        legacy = self.legacy_status()
        namespace = load_workspace()
        unlink = Path.unlink
        def fail_legacy_unlink(path, *args, **kwargs):
            if path == self.root / "project-status.md":
                raise OSError("synthetic legacy removal failure")
            return unlink(path, *args, **kwargs)
        with mock.patch.object(Path, "unlink", fail_legacy_unlink):
            code, _, _ = self.direct(namespace, "status")
        self.assertEqual(2, code)
        self.assertEqual(legacy, (self.root / "project-status.md").read_bytes())
        self.assertFalse((self.root / "team-status.md").exists())
        self.cli("status")
        self.assertFalse((self.root / "project-status.md").exists())
        self.cli("status", "--check")

    def test_status_is_positive_selected_deterministic_and_check_is_read_only(self):
        progress = "- **Access review:** Completed the agreed role checks; export permissions remain blocked."
        source = STATUS.replace("- Not yet reported.", progress, 1)
        (self.bank / "project-status.md").write_text(source, encoding="utf-8")
        self.cli("status")
        output = (self.root / "team-status.md").read_bytes()
        self.assertIn(progress.encode(), output)
        self.assertNotIn(b"Private analytical notes", output)
        self.assertNotIn(b"## Internal", output)
        self.assertNotIn(b"## Publishable", output)
        self.assertFalse((self.root / "project-status.md").exists())
        receipt_path = self.bank / "runtime/status-receipt.json"
        receipt_bytes = receipt_path.read_bytes()
        self.cli("status", "--check")
        self.assertEqual(receipt_bytes, receipt_path.read_bytes())
        self.cli("status")
        self.assertEqual(output, (self.root / "team-status.md").read_bytes())
        receipt = self.receipt("status-receipt.json")
        self.assertEqual(hashlib.sha256((self.bank / "project-status.md").read_bytes()).hexdigest(), receipt["source_sha256"])
        self.assertIn("generated_at", receipt)
        self.assertIn("source_modified_at", receipt)

    def test_all_installer_status_scaffolds_use_supported_exact_grammar(self):
        for profile in ("pentest", "incident-response", "academic-research", "general-project"):
            with self.subTest(profile=profile):
                template = REPO_ROOT / "templates" / (profile + "-memory-bank") / "project-status.md"
                (self.bank / "project-status.md").write_bytes(template.read_bytes())
                self.configure(profile, external_status=True)
                self.cli("status")
                self.cli("status", "--check")

    def test_status_warns_without_reproducing_suspected_values(self):
        token = "never-print-this-synthetic-password"
        source = STATUS.replace("- Not yet reported.", "- password=" + token + " person@example.test 192.0.2.1", 1)
        (self.bank / "project-status.md").write_text(source, encoding="utf-8")
        result = self.cli("status")
        self.assertIn("warning:", result.stderr)
        self.assertIn("credential indicator", result.stderr)
        self.assertNotIn(token, result.stdout + result.stderr)
        self.assertNotIn("person@example.test", result.stdout + result.stderr)
        self.assertNotIn("192.0.2.1", result.stdout + result.stderr)
        # Warnings are not a blocking redaction claim; the explicitly selected prose is unchanged.
        self.assertIn(token, (self.root / "team-status.md").read_text(encoding="utf-8"))

    def test_internal_change_and_output_tampering_are_stale(self):
        self.cli("status")
        old_output = (self.root / "team-status.md").read_bytes()
        with (self.bank / "project-status.md").open("a", encoding="utf-8") as stream:
            stream.write("Another private note.\n")
        self.cli("status", "--check", expected=1)
        self.cli("status")
        self.assertEqual(old_output, (self.root / "team-status.md").read_bytes())
        (self.root / "team-status.md").write_text("tampered\n", encoding="utf-8")
        self.cli("status", "--check", expected=1)

    def test_malformed_status_preserves_previous_output_and_failure_receipt(self):
        self.cli("status")
        old_output = (self.root / "team-status.md").read_bytes()
        old_hash = self.receipt("status-receipt.json")["output_sha256"]
        for malformed in (
            STATUS.replace("### Blockers", "### Unapproved secret heading"),
            STATUS.replace("## Internal", "### Progress\n- Duplicate\n\n## Internal"),
            STATUS.replace("### Milestones\n- Not yet reported.", "### Milestones"),
        ):
            with self.subTest(source=malformed[:20]):
                (self.bank / "project-status.md").write_text(malformed, encoding="utf-8")
                self.cli("status", expected=2)
                self.assertEqual(old_output, (self.root / "team-status.md").read_bytes())
                receipt = self.receipt("status-receipt.json")
                self.assertEqual("failed", receipt["state"])
                self.assertEqual(old_hash, receipt["output_sha256"])
                self.cli("status", "--check", expected=2)

    def test_failed_status_commit_restores_prior_output(self):
        self.cli("status")
        previous = (self.root / "team-status.md").read_bytes()
        (self.bank / "project-status.md").write_text(STATUS.replace("Not yet reported.", "Real new progress.", 1), encoding="utf-8")
        namespace = load_workspace()
        replace = namespace["os"].replace
        receipt_path = self.bank / "runtime/status-receipt.json"
        failed = False
        def fail_receipt_once(source, destination):
            nonlocal failed
            if Path(destination) == receipt_path and not failed:
                failed = True
                raise OSError("synthetic-write-failure-content-must-not-echo")
            return replace(source, destination)
        with mock.patch.object(namespace["os"], "replace", side_effect=fail_receipt_once):
            code, stdout, stderr = self.direct(namespace, "status")
        self.assertEqual(2, code)
        self.assertNotIn("synthetic-write-failure-content-must-not-echo", stdout + stderr)
        self.assertEqual(previous, (self.root / "team-status.md").read_bytes())
        self.assertEqual("failed", self.receipt("status-receipt.json")["state"])
        self.assertFalse((self.bank / "runtime/workspace.lock").exists())

    def test_missing_projection_is_stale_and_optional_output_is_not_enabled_implicitly(self):
        self.cli("status", "--check", expected=1)
        self.configure("general-project", external_status=False)
        self.cli("status", expected=2)
        self.assertFalse((self.root / "team-status.md").exists())
        self.configure("general-project", external_status=True)
        self.cli("status")

    def test_profile_must_be_explicit_without_metadata_and_old_bank_is_not_used(self):
        (self.bank / "layout.json").unlink()
        self.cli("status", expected=2)
        self.cli("--profile", "pentest", "status")
        self.bank.rename(self.root / "memory-bank")
        self.cli("--profile", "pentest", "status", expected=2)
        self.assertFalse(self.bank.exists())

    def test_plan_archive_preserves_bytes_history_links_and_collisions(self):
        source = self.bank / "planning/feature.md"
        original = b"# Feature plan\n\nAn old decision and completion history.\n"
        source.write_bytes(original)
        active = self.bank / "activeContext.md"
        active.write_text("# Context\n\n[Plan](planning/feature.md#decision)\n` .memory-bank/planning/feature.md `\n", encoding="utf-8")
        reference = self.bank / "references/reference.md"
        reference.write_text("# References\n\n[Plan](../planning/feature.md)\n", encoding="utf-8")
        other = self.bank / "planning/other.md"
        other.write_text("# Other\n\n[Plan](feature.md)\n", encoding="utf-8")
        historical = self.bank / "planning/archive/older.md"
        historical.write_text("Historical reference stays [here](../feature.md).\n", encoding="utf-8")
        self.cli("archive-plan", ".memory-bank/planning/feature.md", "--date", "2026-10-04")
        archived = self.bank / "planning/archive/2026-10-04-feature.md"
        self.assertEqual(original, archived.read_bytes())
        self.assertFalse(source.exists())
        self.assertIn("planning/archive/2026-10-04-feature.md#decision", active.read_text(encoding="utf-8"))
        self.assertIn("../planning/archive/2026-10-04-feature.md", reference.read_text(encoding="utf-8"))
        self.assertIn("archive/2026-10-04-feature.md", other.read_text(encoding="utf-8"))
        self.assertIn("../feature.md", historical.read_text(encoding="utf-8"))
        progress = (self.bank / "progress.md").read_text(encoding="utf-8")
        self.assertIn("Prior completion history", progress)
        self.assertIn("Previous path: `.memory-bank/planning/feature.md`", progress)
        source.write_bytes(b"# A later plan with the same name\n")
        self.cli("archive-plan", ".memory-bank/planning/feature.md", "--date", "2026-10-04")
        self.assertEqual(original, archived.read_bytes())
        self.assertTrue((self.bank / "planning/archive/2026-10-04-feature-2.md").exists())

    def test_plan_archive_repairs_optional_findings_only_when_enabled(self):
        findings = self.bank / "findings.md"
        original = "# Findings\n\nPrior finding history.\n\n[Plan](planning/release.md)\n"
        unlisted = self.bank / "unlisted.md"
        unlisted.write_text(original, encoding="utf-8")
        for enabled in (False, True):
            with self.subTest(findings_enabled=enabled):
                self.configure("general-project", external_status=False, findings=enabled)
                findings.write_text(original, encoding="utf-8")
                source = self.bank / "planning/release.md"
                source.write_text("# Release plan\n", encoding="utf-8")
                stamp = "2026-10-05" if enabled else "2026-10-04"
                self.cli("archive-plan", str(source), "--date", stamp)
                self.assertFalse(source.exists())
                expected = original.replace("planning/release.md", f"planning/archive/{stamp}-release.md") if enabled else original
                self.assertEqual(expected, findings.read_text(encoding="utf-8"))
                self.assertEqual(original, unlisted.read_text(encoding="utf-8"))
                self.assertEqual("# Release plan\n", (self.bank / f"planning/archive/{stamp}-release.md").read_text(encoding="utf-8"))

    def test_plan_archive_prerequisite_failure_preserves_source(self):
        source = self.bank / "planning/feature.md"
        source.write_text("# Preserve me\n", encoding="utf-8")
        (self.bank / "progress.md").unlink()
        self.cli("archive-plan", ".memory-bank/planning/feature.md", expected=2)
        self.assertTrue(source.exists())
        self.assertEqual([], list((self.bank / "planning/archive").iterdir()))

    def test_reference_retention_and_archival_require_explicit_disposition(self):
        source = self.drop(contents=b"opaque source content must not echo\x00\xff")
        result = self.intake(source)
        self.assertTrue(source.exists())
        self.assertEqual([], list((self.bank / "references/raw").iterdir()))
        item = next(iter(self.receipt("intake.json")["items"].values()))
        self.assertEqual("retained-pending-disposition", item["state"])
        self.assertEqual("reference", item["kind"])
        self.assertEqual("Owner-provided synthetic source", item["origin"])
        self.assertNotIn("opaque source content", result.stdout + result.stderr)
        self.intake(source, "--archive", "--topic", "architecture")
        self.assertFalse(source.exists())
        item = next(iter(self.receipt("intake.json")["items"].values()))
        stored = self.root / item["stored_path"]
        self.assertEqual(item["sha256"], hashlib.sha256(stored.read_bytes()).hexdigest())
        self.assertEqual(0o600, stored.stat().st_mode & 0o777)
        self.assertEqual(0o700, stored.parent.stat().st_mode & 0o777)
        self.assertEqual(2, len(item["events"]))

    def test_reference_deletion_without_archive_requires_owner_attestation(self):
        source = self.drop()
        self.intake(source, "--delete", expected=2)
        self.assertTrue(source.exists())
        self.intake(source, "--delete", "--confirm")
        self.assertFalse(source.exists())
        self.assertEqual([], list((self.bank / "references/raw").iterdir()))
        item = next(iter(self.receipt("intake.json")["items"].values()))
        self.assertEqual("delete", item["disposition"])
        self.assertNotIn("stored_path", item)

    def test_operational_and_generic_artifact_sources_are_preserved_before_removal(self):
        for kind, store in (("operational", "sensitive"), ("artifact", "artifacts")):
            with self.subTest(kind=kind):
                source = self.drop(name=kind + ".txt")
                original = source.read_bytes()
                self.intake(source, "--retain", kind=kind)
                self.assertTrue(source.exists())
                items = self.receipt("intake.json")["items"]
                item = next(value for value in items.values() if value["kind"] == kind)
                self.assertTrue(item["stored_path"].startswith(".memory-bank/" + store + "/"))
                stored = self.root / item["stored_path"]
                self.assertEqual(original, stored.read_bytes())
                self.intake(source, "--delete", "--confirm", kind=kind)
                self.assertFalse(source.exists())
                self.assertEqual(original, stored.read_bytes())

    def test_failed_copy_preserves_source_hash_receipt_and_suppresses_exception_data(self):
        source = self.drop()
        original = source.read_bytes()
        namespace = load_workspace()
        with mock.patch.dict(namespace, {"copy_verified": mock.Mock(side_effect=OSError("never-echo-raw-source"))}):
            code, stdout, stderr = self.direct(namespace, "intake", str(source), "--kind", "operational", "--origin", "Fixture", "--archive")
        self.assertEqual(2, code)
        self.assertEqual(original, source.read_bytes())
        self.assertNotIn("never-echo-raw-source", stdout + stderr)
        item = next(iter(self.receipt("intake.json")["items"].values()))
        self.assertEqual("failed-source-retained", item["state"])
        self.assertEqual(hashlib.sha256(original).hexdigest(), item["sha256"])

    def test_hidden_nested_and_symlink_drops_remain_visible_without_content_output(self):
        self.drop(".hidden", b"do-not-echo-hidden")
        self.drop("nested/entry", b"do-not-echo-nested")
        self.drop(".gitkeep", b"")
        (self.bank / "incoming/link").symlink_to(self.bank / "incoming/.hidden")
        result = self.cli("intake-pending")
        self.assertIn("files=2", result.stdout)
        self.assertIn("directories=1", result.stdout)
        self.assertIn("symlinks=1", result.stdout)
        self.assertIn("hidden=1", result.stdout)
        self.assertNotIn("do-not-echo", result.stdout + result.stderr)
        self.intake(self.bank / "incoming/link", "--delete", "--confirm", expected=2)
        self.assertTrue((self.bank / "incoming/.hidden").exists())

    def test_symlink_store_and_nonincoming_source_are_rejected(self):
        source = self.drop()
        (self.bank / "sensitive").rmdir()
        (self.bank / "sensitive").symlink_to(self.bank / "artifacts", target_is_directory=True)
        self.intake(source, "--archive", kind="operational", expected=2)
        self.assertTrue(source.exists())
        outside = self.root / "valuable.txt"
        outside.write_text("preserve", encoding="utf-8")
        self.intake(outside, "--delete", "--confirm", expected=2)
        self.assertTrue(outside.exists())

    def test_declared_root_alias_accepts_absolute_source_without_resolving_child_symlinks(self):
        namespace = load_workspace()
        source = self.drop()
        original = source.read_bytes()
        with tempfile.TemporaryDirectory(prefix="mb-root-alias-") as temporary:
            parent = Path(temporary).resolve()
            alias = parent / "project"
            alias.symlink_to(self.root, target_is_directory=True)
            aliased_source = alias / source.relative_to(self.root)
            self.cli("--root", str(alias), "intake", str(aliased_source),
                     "--kind", "reference", "--origin", "Alias fixture", "--retain")
            self.assertEqual(source, namespace["safe_path"](alias, aliased_source))
            self.assertEqual(source, namespace["safe_path"](self.root, aliased_source, root_alias=alias))
            self.assertEqual(source, namespace["safe_path"](alias, source.relative_to(self.root)))
            outside = parent / "external.txt"
            outside.write_bytes(b"external source retained\n")
            (self.bank / "incoming/file-link").symlink_to(source)
            (self.bank / "incoming/directory-link").symlink_to(source.parent, target_is_directory=True)
            (self.bank / "incoming/external-link").symlink_to(outside)
            rejected = (
                alias / ".memory-bank/incoming/file-link",
                alias / ".memory-bank/incoming/directory-link/source.txt",
                alias / ".memory-bank/incoming/external-link",
                outside,
                alias / "../external.txt",
                alias / ".memory-bank/incoming/../incoming/source.txt",
            )
            for path in rejected:
                with self.subTest(path=path):
                    self.cli("--root", str(alias), "intake", str(path), "--kind", "reference",
                             "--origin", "Alias fixture", "--delete", "--confirm", expected=2)
                    with self.assertRaises(namespace["WorkflowError"]):
                        namespace["safe_path"](alias, path)
                    self.assertEqual(original, source.read_bytes())
                    self.assertEqual(b"external source retained\n", outside.read_bytes())

    def test_intake_infers_root_without_explicit_alias(self):
        source = self.drop()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "intake", str(source), "--kind", "reference",
             "--origin", "Inferred root fixture", "--retain"],
            cwd=self.root, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue(source.exists())
        item = next(iter(self.receipt("intake.json")["items"].values()))
        self.assertEqual(".memory-bank/incoming/source.txt", item["source"])

    def test_missing_ir_intake_is_a_prerequisite_not_generic_copy_fallback(self):
        self.configure("incident-response")
        source = self.drop()
        result = self.intake(source, "--archive", kind="artifact", expected=2)
        self.assertIn("IR custody intake is not installed", result.stderr)
        self.assertTrue(source.exists())
        self.assertEqual([], list((self.bank / "artifacts").iterdir()))
        self.assertEqual("failed-source-retained", next(iter(self.receipt("intake.json")["items"].values()))["state"])

    def test_real_installed_ir_intake_keeps_custody_and_reuses_retained_acquisition(self):
        self.configure("incident-response")
        scripts = REPO_ROOT / "skills/memory-bank-ir-dashboard/scripts"
        shutil.copytree(scripts, self.root / "scripts")
        for filename, contents in (("evidenceIndex.md", "# Evidence Index\n"), ("reviewQueue.md", "# Review Queue\n"), ("dashboard.config.json", "{}\n")):
            (self.bank / filename).write_text(contents, encoding="utf-8")
        source = self.drop(contents=b"synthetic-evidence-content-not-for-diagnostics\n")
        result = self.intake(source, "--retain", kind="artifact")
        self.assertNotIn("synthetic-evidence-content-not-for-diagnostics", result.stdout + result.stderr)
        self.assertTrue(source.exists())
        item = next(iter(self.receipt("intake.json")["items"].values()))
        self.assertRegex(item["artifact_id"], r"^ART-\d{4}$")
        stored = self.root / item["stored_path"]
        self.assertEqual(source.read_bytes(), stored.read_bytes())
        manifest = self.bank / "artifacts/.custody-manifest.jsonl"
        original_manifest = manifest.read_bytes()
        self.assertIn(item["artifact_id"], (self.bank / "evidenceIndex.md").read_text(encoding="utf-8"))
        self.assertIn(item["artifact_id"], (self.bank / "reviewQueue.md").read_text(encoding="utf-8"))
        self.intake(source, "--delete", "--confirm", kind="artifact")
        self.assertFalse(source.exists())
        self.assertEqual(original_manifest, manifest.read_bytes())
        self.assertEqual(item["sha256"], hashlib.sha256(stored.read_bytes()).hexdigest())

    def test_corrupted_ir_acquisition_repeatedly_rejects_archive_preserving_identity_and_history(self):
        self.configure("incident-response")
        shutil.copytree(REPO_ROOT / "skills/memory-bank-ir-dashboard/scripts", self.root / "scripts")
        for filename, contents in (("evidenceIndex.md", "# Evidence Index\n"), ("reviewQueue.md", "# Review Queue\n"), ("dashboard.config.json", "{}\n")):
            (self.bank / filename).write_text(contents, encoding="utf-8")
        source = self.drop(contents=b"synthetic evidence retained until reconciliation\n")
        original = source.read_bytes()
        self.intake(source, "--retain", kind="artifact")
        receipt = self.receipt("intake.json")
        key, acquired = next(iter(receipt["items"].items()))
        self.assertEqual("ART-0001", acquired["artifact_id"])
        custody_paths = [self.bank / path for path in (
            "artifacts/.custody-manifest.jsonl", "evidenceIndex.md", "reviewQueue.md",
        )]
        custody = {path: path.read_bytes() for path in custody_paths}
        stored = self.root / acquired["stored_path"]
        stored.write_bytes(b"corrupted acquisition\n")
        events = acquired["events"]
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                result = self.intake(source, "--archive", kind="artifact", expected=2)
                self.assertIn("previous acquisition receipt does not match stored bytes", result.stderr)
                self.assertEqual(original, source.read_bytes())
                receipt = self.receipt("intake.json")
                self.assertEqual([key], list(receipt["items"]))
                failed = receipt["items"][key]
                for field in ("artifact_id", "stored_path", "verified_sha256", "sha256", "source", "kind", "origin"):
                    self.assertEqual(acquired[field], failed[field], field)
                self.assertEqual("failed-source-retained", failed["state"])
                self.assertEqual(events, failed["events"][:-1])
                self.assertEqual("intake-failed", failed["events"][-1]["error"])
                events = failed["events"]
                for path, contents in custody.items():
                    self.assertEqual(contents, path.read_bytes())
                self.assertEqual(b"corrupted acquisition\n", stored.read_bytes())

    def override_flags(self):
        return ["override", "record", "--id", "fixture-scope", "--policy", ".memory-bank/sensitiveDataPolicy.md",
                "--default", "Keep secrets out of memory", "--risk", "Synthetic text resembles a secret",
                "--action", "Retain one approved synthetic fixture", "--scope", "One named test fixture; no live secrets",
                "--confirmed-by", "Project owner", "--date", "2026-10-04", "--confirm"]

    def test_override_requires_confirmation_persists_exact_scope_and_revokes_with_history(self):
        flags = self.override_flags()
        self.cli(*flags[:-1], expected=2)
        self.assertNotIn("Project override", (self.bank / "activeContext.md").read_text(encoding="utf-8"))
        self.cli(*flags)
        for path in (self.bank / "activeContext.md", self.bank / "sensitiveDataPolicy.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Exact scope: One named test fixture; no live secrets", text)
            self.assertIn("Project-wide until explicitly revoked", text)
        original = (self.bank / "activeContext.md").read_bytes()
        self.cli(*flags)
        self.assertEqual(original, (self.bank / "activeContext.md").read_bytes())
        broadened = list(flags)
        broadened[broadened.index("--scope") + 1] = "All fixtures and live secrets"
        self.cli(*broadened, expected=2)
        self.assertEqual(original, (self.bank / "activeContext.md").read_bytes())
        self.cli("override", "revoke", "--id", "fixture-scope", "--reason", "No longer needed", "--confirmed-by", "Project owner", "--date", "2026-10-05", "--confirm")
        for path in (self.bank / "activeContext.md", self.bank / "sensitiveDataPolicy.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("confirmed 2026-10-04", text)
            self.assertIn("revoked 2026-10-05", text)
        self.assertEqual("revoked", self.receipt("overrides.json")["overrides"]["fixture-scope"]["state"])

    def test_manual_revocation_in_either_authority_file_is_not_certified_active(self):
        flags = self.override_flags()
        self.cli(*flags)
        registry_path = self.bank / "runtime/overrides.json"
        original_registry = registry_path.read_bytes()
        for filename in ("activeContext.md", "sensitiveDataPolicy.md"):
            with self.subTest(filename=filename):
                path = self.bank / filename
                original = path.read_text(encoding="utf-8")
                edited = original + "\n### Project override `fixture-scope` — revoked 2026-10-05\n\n- Confirmed by: Project owner\n- Reason: Explicit manual revocation\n- State: Revoked; the safe default applies again.\n"
                path.write_text(edited, encoding="utf-8")
                result = self.cli(*flags, expected=2)
                self.assertIn("conflicts with authority/context history", result.stderr)
                self.assertNotIn("already active", result.stdout)
                self.assertEqual(edited, path.read_text(encoding="utf-8"))
                self.assertEqual(original_registry, registry_path.read_bytes())
                path.write_text(original, encoding="utf-8")

    def test_stale_revoked_registry_cannot_reconfirm_over_manual_history(self):
        flags = self.override_flags()
        self.cli(*flags)
        confirmation = self.receipt("overrides.json")["overrides"]["fixture-scope"]["block"]
        self.cli("override", "revoke", "--id", "fixture-scope", "--reason", "Ended",
                 "--confirmed-by", "Project owner", "--date", "2026-10-05", "--confirm")
        policy = self.bank / "sensitiveDataPolicy.md"
        with policy.open("a", encoding="utf-8") as stream:
            stream.write(confirmation)
        original = policy.read_bytes()
        self.cli(*flags, expected=2)
        self.assertEqual(original, policy.read_bytes())
        self.assertEqual("revoked", self.receipt("overrides.json")["overrides"]["fixture-scope"]["state"])

    def test_reconfirmation_after_recorded_revocation_preserves_all_events(self):
        flags = self.override_flags()
        self.cli(*flags)
        self.cli("override", "revoke", "--id", "fixture-scope", "--reason", "Ended",
                 "--confirmed-by", "Project owner", "--date", "2026-10-05", "--confirm")
        flags[flags.index("--date") + 1] = "2026-10-06"
        self.cli(*flags)
        self.cli(*flags)
        entry = self.receipt("overrides.json")["overrides"]["fixture-scope"]
        self.assertEqual("active", entry["state"])
        self.assertEqual(3, len(entry["history"]))
        self.assertIn("confirmed 2026-10-04", (self.bank / "sensitiveDataPolicy.md").read_text(encoding="utf-8"))

    def test_override_document_failure_does_not_leave_context_only_authorization(self):
        namespace = load_workspace()
        original = (self.bank / "activeContext.md").read_bytes()
        stage = namespace["stage"]
        def fail_policy(root, path, content, mode=0o600):
            if Path(path) == self.bank / "sensitiveDataPolicy.md":
                raise OSError("secret-looking failure detail")
            return stage(root, path, content, mode)
        with mock.patch.dict(namespace, {"stage": fail_policy}):
            code, stdout, stderr = self.direct(namespace, *self.override_flags())
        self.assertEqual(2, code)
        self.assertEqual(original, (self.bank / "activeContext.md").read_bytes())
        self.assertFalse((self.bank / "runtime/overrides.json").exists())
        self.assertNotIn("secret-looking failure detail", stdout + stderr)


if __name__ == "__main__":
    unittest.main()
