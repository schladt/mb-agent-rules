"""Consumer-visible installer preservation and Git failure regressions."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "bin/init-agent-rules"
FRESH = ROOT / "bin/check-memory-freshness"


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mb-install-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = (Path(self.temp.name) / "project").resolve()
        self.root.mkdir()
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), AGENT_RULES_ROOT=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("CLAUDECODE", None)

    def command(self, executable, *args, cwd=None):
        return subprocess.run([sys.executable, "-B", str(executable), *args], cwd=cwd or self.root,
                              env=self.env, capture_output=True, text=True)

    def install(self, *args):
        return self.command(INSTALL, "general-project", *args)

    def put(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        return dest

    def assert_ok(self, result):
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


    def snapshot(self, root=None):
        root = root or self.root
        entries = {}
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                entries[relative] = ("link", os.readlink(path))
            elif path.is_file():
                entries[relative] = ("file", path.read_bytes())
            else:
                entries[relative] = ("directory",)
        return entries

class InstallerTests(WorkspaceCase):
    def test_migration_preserves_custody_bytes_and_cognitive_history(self):
        context = "# Active Context\n\nHistorical artifacts/source.bin\n[Evidence](../artifacts/source.bin)\nPlan: `memory-bank/planning/work.md`\n"
        self.put("memory-bank/activeContext.md", context)
        self.put("memory-bank/planning/work.md", "# Work\n\nSupported plan.\n")
        self.put("README.md", "[Plan](memory-bank/planning/work.md)\nHistorical layout: `memory-bank/`.\n")
        manifest = b'{"stored_path":"artifacts/source.bin","hash":"opaque historical chain"}\n'
        artifact = self.put("artifacts/source.bin", "acquired bytes\n")
        self.put("artifacts/.custody-manifest.jsonl", manifest.decode())
        before = hashlib.sha256(artifact.read_bytes()).hexdigest()
        self.put("loot/nested/other.bin", "other acquired bytes\n")
        self.put("sensitive/operator.conf", "synthetic operational input\n")
        self.assert_ok(self.install("--migrate"))
        bank = self.root / ".memory-bank"
        self.assertFalse((self.root / "memory-bank").exists())
        self.assertFalse((self.root / "artifacts").exists())
        self.assertEqual(before, hashlib.sha256((bank / "artifacts/source.bin").read_bytes()).hexdigest())
        self.assertEqual(manifest, (bank / "artifacts/.custody-manifest.jsonl").read_bytes())
        self.assertEqual("other acquired bytes\n", (bank / "artifacts/nested/other.bin").read_text())
        self.assertEqual("synthetic operational input\n", (bank / "sensitive/operator.conf").read_text())
        self.assertIn("Historical artifacts/source.bin", (bank / "activeContext.md").read_text())
        self.assertIn("[Evidence](artifacts/source.bin)", (bank / "activeContext.md").read_text())
        self.assertIn("`.memory-bank/planning/work.md`", (bank / "activeContext.md").read_text())
        self.assertIn("[Plan](.memory-bank/planning/work.md)", (self.root / "README.md").read_text())
        self.assertIn("Historical layout: `memory-bank/`.", (self.root / "README.md").read_text())
        snapshots = list((bank / "backups").glob("*/activeContext.md"))
        self.assertEqual([context], [p.read_text() for p in snapshots])
        mapping = json.loads((bank / "path-migrations.json").read_text())
        self.assertEqual(".memory-bank/artifacts/", mapping["prefixes"]["loot/"])
        self.assertEqual([str(self.root)], mapping["project_roots"])

    def test_collision_rejects_migration_before_any_source_moves(self):
        self.put("memory-bank/activeContext.md", "owner memory")
        self.put("artifacts/same.bin", "first")
        self.put("loot/same.bin", "second")
        result = self.install("--migrate")
        self.assertEqual(2, result.returncode)
        self.assertEqual("first", (self.root / "artifacts/same.bin").read_text())
        self.assertEqual("second", (self.root / "loot/same.bin").read_text())
        self.assertEqual("owner memory", (self.root / "memory-bank/activeContext.md").read_text())
        self.assertFalse((self.root / ".memory-bank").exists())

    def test_direct_claude_skill_directory_upgrade_retains_owner_edits(self):
        self.assert_ok(self.install("--skills-dir", ".claude/skills"))
        old = self.root / ".claude/skills/memory-bank-context/SKILL.md"
        owner_text = old.read_text() + "\nOwner customization.\n"
        old.write_text(owner_text)
        self.assert_ok(self.install())
        link = self.root / ".claude/skills/memory-bank-context"
        self.assertTrue(link.is_symlink())
        self.assertEqual((self.root / ".agents/skills/memory-bank-context").resolve(), link.resolve())
        backups = list((self.root / ".memory-bank/backups").glob("*/skills/memory-bank-context/SKILL.md"))
        self.assertEqual([owner_text], [p.read_text() for p in backups])
        self.assertNotIn("Owner customization.", (link / "SKILL.md").read_text())

    def test_unrelated_claude_and_ignore_rules_survive_migration(self):
        self.put("memory-bank/activeContext.md", "# Local notes\n")
        self.put("AGENTS.md", "# General Project Memory Bank Instructions\n")
        claude = self.put("CLAUDE.md", "# Owner instructions\nNot installer-owned.\n")
        self.put(".gitignore", "custom-private/\n/deliverables/\n/.agents/\n/memory-bank/\n")
        self.assert_ok(self.install("--migrate"))
        self.assertEqual("# Owner instructions\nNot installer-owned.\n", claude.read_text())
        ignored = (self.root / ".gitignore").read_text()
        self.assertIn("custom-private/\n", ignored)
        self.assertIn("/deliverables/\n", ignored)
        self.assertNotIn("/.agents/\n", ignored)
        self.assertIn("/.memory-bank/\n", ignored)

    def test_dry_run_does_not_move_or_create_files(self):
        self.put("memory-bank/activeContext.md", "existing")
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        self.assert_ok(self.install("--migrate", "--dry-run"))
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))
        self.assertEqual("existing", (self.root / "memory-bank/activeContext.md").read_text())

    def test_outside_skill_destination_is_rejected_without_mutation(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / ".agents").symlink_to(outside, target_is_directory=True)
        result = self.install()
        self.assertEqual(2, result.returncode)
        self.assertEqual([], list(outside.iterdir()))
        self.assertFalse((self.root / ".memory-bank").exists())


    def test_outside_claude_discovery_ancestors_are_rejected_before_mutation(self):
        outside = Path(self.temp.name) / "outside"
        package = outside / "skills/memory-bank-context"
        shutil.copytree(ROOT / "skills/memory-bank-context", package)
        for ancestor in (".claude", ".claude/skills"):
            with self.subTest(ancestor=ancestor):
                link = self.root / ancestor
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside if ancestor == ".claude" else outside / "skills",
                                target_is_directory=True)
                before = self.snapshot(Path(self.temp.name))
                for args in (("--dry-run",), ()):
                    with self.subTest(args=args):
                        result = self.install(*args)
                        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                        self.assertIn("must not traverse a symlink", result.stderr)
                        self.assertEqual(before, self.snapshot(Path(self.temp.name)))
                        self.assertFalse((self.root / ".memory-bank").exists())
                link.unlink()

    def test_unrelated_skill_links_are_preserved_on_fresh_and_same_location_installs(self):
        outside = Path(self.temp.name) / "owner-skill"
        outside.mkdir()
        (outside / "SKILL.md").write_text("# Owner skill\n")
        dest = self.root / ".agents/skills/memory-bank-context"
        for installed in (False, True):
            with self.subTest(installed=installed):
                if installed:
                    self.assert_ok(self.install())
                    shutil.rmtree(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.symlink_to(outside, target_is_directory=True)
                before = self.snapshot(Path(self.temp.name))
                for args in (("--dry-run",), ()):
                    result = self.install(*args)
                    self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                    self.assertIn("unrelated symlink", result.stderr)
                    self.assertEqual(before, self.snapshot(Path(self.temp.name)))
                dest.unlink()

    def test_unrelated_claude_discovery_link_is_preserved(self):
        outside = Path(self.temp.name) / "owner-skill"
        outside.mkdir()
        (outside / "SKILL.md").write_text("# Owner skill\n")
        link = self.root / ".claude/skills/memory-bank-context"
        link.parent.mkdir(parents=True)
        link.symlink_to(outside, target_is_directory=True)
        before = self.snapshot(Path(self.temp.name))
        result = self.install()
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("unrelated symlink", result.stderr)
        self.assertEqual(before, self.snapshot(Path(self.temp.name)))

    def test_source_package_links_are_preserved(self):
        source = ROOT / "skills/memory-bank-context"
        link = self.root / ".agents/skills/memory-bank-context"
        link.parent.mkdir(parents=True)
        link.symlink_to(source, target_is_directory=True)
        (self.root / ".claude").mkdir()
        for _ in range(2):
            self.assert_ok(self.install())
            self.assertTrue(link.is_symlink())
            self.assertEqual(source, link.resolve())
            discovery = self.root / ".claude/skills/memory-bank-context"
            self.assertTrue(discovery.is_symlink())
            self.assertEqual(source, discovery.resolve())

    def test_managed_discovery_links_can_become_direct_skill_packages(self):
        (self.root / ".claude").mkdir()
        self.assert_ok(self.install())
        for skills_dir in (".claude/skills", "project-skills", ".claude/skills", ".agents/skills"):
            with self.subTest(skills_dir=skills_dir):
                self.assert_ok(self.install("--dry-run", "--skills-dir", skills_dir))
                self.assert_ok(self.install("--skills-dir", skills_dir))
                for name in ("memory-bank-context", "memory-bank-maintenance", "memory-bank-workflow"):
                    package = self.root / skills_dir / name
                    self.assertTrue(package.is_dir())
                    self.assertFalse(package.is_symlink())
                    self.assertEqual((ROOT / "skills" / name / "SKILL.md").read_bytes(),
                                     (package / "SKILL.md").read_bytes())
                    discovery = self.root / ".claude/skills" / name
                    self.assertEqual(package.resolve(), discovery.resolve())
                    self.assertEqual(skills_dir != ".claude/skills", discovery.is_symlink())

    def test_in_project_discovery_package_is_backed_up_and_linked(self):
        package = self.root / ".claude/skills/memory-bank-context"
        source = ROOT / "skills/memory-bank-context"
        shutil.copytree(source, package)
        original = self.snapshot(package)
        self.assert_ok(self.install())
        self.assertTrue(package.is_symlink())
        self.assertEqual(self.root / ".agents/skills/memory-bank-context", package.resolve())
        backups = list((self.root / ".memory-bank/backups").glob("*/skills/memory-bank-context"))
        self.assertEqual(1, len(backups))
        self.assertEqual(original, self.snapshot(backups[0]))


class FreshnessTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "synthetic@example.invalid")

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout.strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)

    def test_staged_freshness_is_identical_from_repository_subdirectory(self):
        self.put(".memory-bank/activeContext.md", "tracked memory")
        self.put("src/example.txt", "base")
        self.commit("base")
        self.put("src/example.txt", "changed")
        self.git("add", "src/example.txt")
        root_result = self.command(FRESH, "--staged")
        nested_result = self.command(FRESH, "--staged", cwd=self.root / "src")
        self.assertEqual(1, root_result.returncode, root_result.stdout + root_result.stderr)
        self.assertEqual(root_result.returncode, nested_result.returncode, nested_result.stdout)
        self.assertEqual(root_result.stdout, nested_result.stdout)
        self.assertIn("src/example.txt", nested_result.stdout)
        self.put(".memory-bank/activeContext.md", "updated cognitive memory")
        self.git("add", ".memory-bank/activeContext.md")
        self.assert_ok(self.command(FRESH, "--staged", cwd=self.root / "src"))

    def test_subdirectory_worktree_includes_staged_unstaged_and_all_untracked_paths(self):
        self.put(".memory-bank/activeContext.md", "tracked memory")
        self.put("src/staged.txt", "base")
        self.put("unstaged.txt", "base")
        self.commit("base")
        self.put("src/staged.txt", "staged change")
        self.git("add", "src/staged.txt")
        self.put("unstaged.txt", "unstaged change")
        self.put("outside-src/untracked.txt", "untracked outside invocation directory")
        self.put("src/untracked.txt", "untracked inside invocation directory")
        root_result = self.command(FRESH, "--worktree")
        nested_result = self.command(FRESH, "--worktree", cwd=self.root / "src")
        self.assertEqual(1, nested_result.returncode, nested_result.stdout + nested_result.stderr)
        self.assertEqual(root_result.stdout, nested_result.stdout)
        for path in ("src/staged.txt", "unstaged.txt", "outside-src/untracked.txt", "src/untracked.txt"):
            self.assertIn(repr(path), nested_result.stdout)
        self.put(".memory-bank/activeContext.md", "unstaged cognitive update")
        self.assert_ok(self.command(FRESH, "--worktree", cwd=self.root / "src"))

    def test_subdirectory_revision_modes_use_root_relative_paths(self):
        self.put(".memory-bank/activeContext.md", "tracked memory")
        self.put("src/example.txt", "base")
        self.commit("base")
        self.put("outside-src.txt", "changed without memory")
        self.commit("project change")
        for args in (("--head",), ("--range", "HEAD~1..HEAD")):
            with self.subTest(args=args):
                root_result = self.command(FRESH, *args)
                nested_result = self.command(FRESH, *args, cwd=self.root / "src")
                self.assertEqual(1, nested_result.returncode, nested_result.stdout + nested_result.stderr)
                self.assertEqual(root_result.stdout, nested_result.stdout)
                self.assertIn("outside-src.txt", nested_result.stdout)

    def test_subdirectory_ignored_bank_skips_only_after_valid_git_queries(self):
        self.put(".memory-bank/activeContext.md", "local memory")
        self.put(".gitignore", "/.memory-bank/\n")
        self.put("src/example.txt", "base")
        self.commit("base")
        self.put("src/example.txt", "changed")
        self.git("add", "src/example.txt")
        for args in (("--staged",), ("--worktree",)):
            with self.subTest(args=args):
                result = self.command(FRESH, *args, cwd=self.root / "src")
                self.assert_ok(result)
                self.assertIn("Skipping (not a freshness guarantee)", result.stdout)
                self.assertEqual(self.command(FRESH, *args).stdout, result.stdout)
        result = self.command(FRESH, "--range", "missing..also-missing", cwd=self.root / "src")
        self.assertEqual(2, result.returncode)
        self.assertIn("error:", result.stderr)

    def test_invalid_range_never_becomes_untracked_bank_skip(self):
        self.put(".memory-bank/activeContext.md", "private memory")
        self.put(".gitignore", "/.memory-bank/\n")
        self.put("source.txt", "base")
        self.commit("base")
        result = self.command(FRESH, "--range", "missing..also-missing")
        self.assertEqual(2, result.returncode)
        self.assertIn("error:", result.stderr)

    def test_clean_merge_uses_first_parent_project_changes(self):
        self.put(".memory-bank/activeContext.md", "tracked memory")
        self.put("source.txt", "base")
        self.commit("base")
        branch = self.git("branch", "--show-current")
        self.git("checkout", "-qb", "feature")
        self.put("feature.txt", "feature without memory")
        self.commit("feature")
        self.git("checkout", "-q", branch)
        self.git("merge", "--no-ff", "-qm", "clean merge", "feature")
        result = self.command(FRESH, "--head")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("feature.txt", result.stdout)

    def test_raw_store_update_is_not_cognitive_memory_update(self):
        self.put(".memory-bank/activeContext.md", "tracked memory")
        self.put("source.txt", "base")
        self.commit("base")
        self.put("source.txt", "changed")
        self.put(".memory-bank/artifacts/raw.bin", "raw")
        self.git("add", ".")
        self.assertEqual(1, self.command(FRESH, "--staged").returncode)
        self.put(".memory-bank/activeContext.md", "updated cognitive context")
        self.git("add", ".")
        self.assert_ok(self.command(FRESH, "--staged"))

    def test_unborn_worktree_reports_untracked_project_files(self):
        self.put("filename\nwith-newline.txt", "new source")
        result = self.command(FRESH, "--worktree")
        self.assertEqual(1, result.returncode)
        self.assertIn("filename\\nwith-newline.txt", result.stdout)
        (self.root / "src").mkdir()
        nested_result = self.command(FRESH, "--worktree", cwd=self.root / "src")
        self.assertEqual(result.returncode, nested_result.returncode, nested_result.stdout)
        self.assertEqual(result.stdout, nested_result.stdout)


if __name__ == "__main__":
    unittest.main()
