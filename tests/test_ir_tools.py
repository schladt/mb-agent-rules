import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script(relative_path: str) -> dict:
    path = REPO_ROOT / relative_path
    namespace = {"__file__": str(path), "__name__": f"test_{path.stem}"}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


def retarget_sync_check(namespace: dict, root: Path) -> None:
    namespace.update({
        "PROJECT_ROOT": root,
        "MEMORY_BANK": root / "memory-bank",
        "ARTIFACTS_DIR": root / "artifacts",
        "INCOMING_DIR": root / "incoming",
        "SENSITIVE_DIR": root / "sensitive",
        "CONFIG_FILE": root / "dashboard.config.json",
        "CUSTODY_MANIFEST": root / "artifacts/.custody-manifest.jsonl",
    })


def retarget_intake(namespace: dict, root: Path) -> None:
    memory_bank = root / "memory-bank"
    artifacts = root / "artifacts"
    namespace.update({
        "PROJECT_ROOT": root,
        "INCOMING_DIR": root / "incoming",
        "ARTIFACTS_DIR": artifacts,
        "MEMORY_BANK": memory_bank,
        "EVIDENCE_INDEX": memory_bank / "evidenceIndex.md",
        "REVIEW_QUEUE": memory_bank / "reviewQueue.md",
        "PROGRESS": memory_bank / "progress.md",
        "CONFIG_FILE": root / "dashboard.config.json",
        "LOCK_FILE": artifacts / ".intake.lock",
        "JOURNAL_FILE": artifacts / ".intake-journal.json",
        "CUSTODY_MANIFEST": artifacts / ".custody-manifest.jsonl",
    })


class SyncCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = load_script("skills/memory-bank-ir-dashboard/scripts/sync_check.py")
        self.temporary = tempfile.TemporaryDirectory(prefix="mb-sync-test-")
        self.root = Path(self.temporary.name)
        for directory in ("memory-bank", "incoming", "artifacts", "sensitive"):
            path = self.root / directory
            path.mkdir(mode=0o700)
            path.chmod(0o700)
        (self.root / "dashboard.config.json").write_text("{}\n", encoding="utf-8")
        retarget_sync_check(self.namespace, self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_sensitive_policy_is_required(self) -> None:
        issues = self.namespace["check_memory_bank_semantics"]()
        messages = [item["message"] for item in issues]
        self.assertIn("Required file missing: sensitiveDataPolicy.md", messages)

    def test_ir_policy_template_is_semantically_valid(self) -> None:
        template = REPO_ROOT / "templates/incident-response-memory-bank/sensitiveDataPolicy.md"
        (self.root / "memory-bank/sensitiveDataPolicy.md").write_text(
            template.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.assertEqual([], self.namespace["check_sensitive_policy"]())

    def test_invalid_policy_values_and_missing_ir_store_are_reported(self) -> None:
        template = REPO_ROOT / "templates/incident-response-memory-bank/sensitiveDataPolicy.md"
        content = template.read_text(encoding="utf-8")
        content = content.replace("Mode: `designated-store`", "Mode: `invalid`")
        content = content.replace("`artifacts/`", "`other/`")
        (self.root / "memory-bank/sensitiveDataPolicy.md").write_text(content, encoding="utf-8")
        messages = [item["message"] for item in self.namespace["check_sensitive_policy"]()]
        self.assertTrue(any("unsupported mode" in message for message in messages))
        self.assertTrue(any("artifacts/ store is not declared" in message for message in messages))

    def test_insecure_sensitive_store_is_reported(self) -> None:
        sensitive = self.root / "sensitive"
        sensitive.chmod(0o777)
        messages = [item["message"] for item in self.namespace["check_permissions"]()]
        self.assertTrue(any("sensitive/ mode 0777" in message for message in messages))

    def test_invalid_dashboard_config_is_reported(self) -> None:
        (self.root / "dashboard.config.json").write_text("{not json", encoding="utf-8")
        issues = self.namespace["check_permissions"]()
        self.assertTrue(any(item["category"] == "configuration" for item in issues))

    def test_missing_sensitive_store_is_warning_not_error(self) -> None:
        (self.root / "artifacts").rmdir()
        issues = self.namespace["check_permissions"]()
        missing = [it for it in issues if it["category"] == "permissions" and "artifacts/" in it["message"]]
        self.assertTrue(missing, "a missing store should still be surfaced")
        self.assertTrue(all(it["severity"] == "warning" for it in missing))
        self.assertFalse(any(it["severity"] == "error" for it in missing))


class IntakeTests(unittest.TestCase):
    def test_queue_exhaustion_leaves_no_pending_artifact(self) -> None:
        namespace = load_script("skills/memory-bank-ir-dashboard/scripts/intake.py")
        with tempfile.TemporaryDirectory(prefix="mb-intake-test-") as temporary:
            root = Path(temporary)
            for directory in ("memory-bank", "incoming", "artifacts"):
                (root / directory).mkdir()
            source = root / "incoming/evidence.txt"
            source.write_text("fictional evidence\n", encoding="utf-8")
            (root / "memory-bank/evidenceIndex.md").write_text("# Evidence Index\n", encoding="utf-8")
            (root / "memory-bank/reviewQueue.md").write_text("### RQ-999 — Previous batch\n", encoding="utf-8")
            (root / "memory-bank/progress.md").write_text("# Progress\n", encoding="utf-8")
            (root / "dashboard.config.json").write_text("{}\n", encoding="utf-8")
            retarget_intake(namespace, root)

            with self.assertRaisesRegex(RuntimeError, "RQ identifier space exhausted"):
                namespace["ingest_files"]([source])

            self.assertTrue(source.exists())
            self.assertEqual([], list((root / "artifacts").glob(".pending-*")))
            self.assertFalse((root / "artifacts/.intake-journal.json").exists())


if __name__ == "__main__":
    unittest.main()
