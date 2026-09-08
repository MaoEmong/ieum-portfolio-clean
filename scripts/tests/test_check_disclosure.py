"""Synthetic fixtures only. Run: python -m unittest discover -s scripts/tests -v."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

MODULE = Path(__file__).resolve().parents[1] / "check_disclosure.py"
SPEC = importlib.util.spec_from_file_location("check_disclosure", MODULE)
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


def synthetic_token():
    return "gh" + "p_" + "Q" * 30


def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def png(extra=b""):
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + extra
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
        + chunk(b"IEND", b"")
    )


def pdf(metadata=None, mutate=None):
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if metadata:
        writer.add_metadata(metadata)
    if mutate:
        mutate(writer)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class TextTests(unittest.TestCase):
    def test_safe_technical_text(self):
        self.assertEqual(checker.text_rules("Flutter, Spring, PostgreSQL; https://example.com/documentation"), set())

    def test_official_dependencies_are_allowed_in_java_and_pom(self):
        fixtures = {
            "Sample.java": "import org.springframework.boot.SpringApplication;\n"
                           "import org.springframework.web.bind.annotation.GetMapping;\n"
                           "import org.junit.jupiter.api.Test;\n"
                           "import static org.assertj.core.api.Assertions.assertThat;\n",
            "pom.xml": "<groupId>org.springframework.boot</groupId>\n"
                       "<groupId>org.apache.maven.plugins</groupId>\n",
        }
        for path, content in fixtures.items():
            with self.subTest(path=path):
                self.assertEqual(checker.scan_content(path, content.encode()), set())

    def test_unknown_reverse_dns_identifiers_remain_blocked(self):
        for prefix in ("com", "kr", "io", "net", "org"):
            value = prefix + "." + "syntheticvendor.privateapp"
            with self.subTest(prefix=prefix):
                self.assertIn("product-app-id", checker.text_rules(value))

    def test_dependency_prefix_lookalikes_remain_blocked(self):
        for suffix in ("springframeworkx.boot", "junitx.api", "assertjx.core",
                       "mockitox.core", "apache.maven.pluginsx"):
            with self.subTest(suffix=suffix):
                self.assertIn("product-app-id", checker.text_rules("org." + suffix))

    def test_allowed_dependency_does_not_hide_another_identifier(self):
        dependency = "import org.springframework.boot.SpringApplication;"
        unknown = "\npackage org." + "syntheticvendor.privateapp;"
        for contents in (dependency + unknown, unknown + dependency):
            self.assertIn("product-app-id", checker.text_rules(contents))

    def test_java_and_xml_dependencies_do_not_exempt_sensitive_rules(self):
        dependency = "org.springframework.boot"
        sensitive_values = {
            "github-token": synthetic_token(),
            "service-endpoint": "https://fixture." + "onrender" + ".com",
            "assigned-credential": "api_" + "key=" + "'synthetic-private-value'",
        }
        for path in ("Sample.java", "pom.xml"):
            for rule, value in sensitive_values.items():
                with self.subTest(path=path, rule=rule):
                    data = (dependency + "\n" + value).encode()
                    self.assertIn(rule, checker.scan_content(path, data))

    def test_portfolio_package_and_dependency_domains_are_allowed(self):
        for value in ("package portfolio.boundaries;",
                      "https://repo.maven.apache.org/maven2/",
                      "http://maven.apache.org/POM/4.0.0"):
            with self.subTest(value=value):
                self.assertEqual(checker.text_rules(value), set())

    def test_high_signal_signatures(self):
        cases = {
            "github-token": synthetic_token(),
            "api-token": "s" + "k-proj-" + "Q" * 30,
            "cloud-access-key": "AK" + "IA" + "Q" * 16,
            "private-key": "-----BEGIN " + "PRIVATE KEY-----",
            "jwt-token": "ey" + "J" + "Q" * 10 + "." + "R" * 15 + "." + "S" * 15,
            "credential-url": "postgresql://" + "tester:" + "madeup-value@db.invalid/sample",
            "service-endpoint": "https://fixture." + "onrender" + ".com",
            "oauth-client-id": "1234567890-" + "fixture.apps." + "googleusercontent.com",
            "local-private-path": "D" + ":/" + "myproject" + "/fixture.txt",
            "product-app-id": "com." + "example." + "portfolio",
            "provider-resource-id": "srv" + "-" + "q" * 18,
            "configured-app-id": "KAKAO_" + "APP_ID=" + "1234567",
            "assigned-credential": "api_" + "key=" + "'" + "synthetic-value" + "'",
        }
        for rule, value in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, checker.text_rules(value))

    def test_provider_domain_variants(self):
        for suffix in ("co", "com"):
            value = "https://fixture." + "supabase." + suffix
            self.assertIn("service-endpoint", checker.text_rules(value))

    def test_windows_user_path(self):
        value = "C" + ":\\" + "Users\\" + "Fixture\\note.txt"
        self.assertIn("local-private-path", checker.text_rules(value))

    def test_sensitive_filename_is_redacted(self):
        self.assertEqual(checker.safe_path(synthetic_token() + ".txt"), "<redacted-path>")

    def test_checker_and_fixture_source_do_not_self_trigger(self):
        for path in (MODULE, Path(__file__)):
            self.assertEqual(checker.text_rules(path.read_text(encoding="utf-8")), set(), path.name)


class MediaTests(unittest.TestCase):
    def test_clean_png(self):
        self.assertEqual(checker.scan_content("image.png", png()), set())

    def test_png_metadata_variants(self):
        for kind in (b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"iCCP", b"tIME"):
            with self.subTest(kind=kind):
                self.assertIn("png-metadata", checker.scan_png(png(chunk(kind, b"synthetic"))))

    def test_png_trailing_bytes(self):
        self.assertIn("png-invalid", checker.scan_png(png() + b"extra"))

    def test_png_bad_crc(self):
        data = bytearray(png())
        data[29] ^= 1
        self.assertIn("png-invalid", checker.scan_png(bytes(data)))

    def test_png_truncated(self):
        self.assertIn("png-invalid", checker.scan_png(png()[:-5]))

    def test_svg_local_reference(self):
        self.assertEqual(checker.scan_svg('<svg xmlns="http://www.w3.org/2000/svg"><use href="#icon"/></svg>'), set())

    def test_svg_rejects_active_and_external_content(self):
        cases = {
            "svg-active-content": "<svg><script>ignored()</script></svg>",
            "svg-event-handler": '<svg onload="ignored()"/>',
            "svg-external-reference": '<svg><image href="https://example.com/picture.png"/></svg>',
            "svg-entity-or-doctype": '<!DOCTYPE svg [<!ENTITY x "fixture">]><svg/>',
        }
        for rule, value in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, checker.scan_svg(value))

    def test_svg_external_css(self):
        self.assertIn("svg-external-reference", checker.scan_svg('<svg><style>g{fill:url("https://example.com/a")}</style></svg>'))

    def test_svg_stylesheet_processing_instruction(self):
        value = '<?xml-stylesheet href="https://example.com/a.css"?><svg/>'
        self.assertIn("svg-processing-instruction", checker.scan_svg(value))

    def test_svg_animation_cannot_change_link(self):
        value = '<svg><set attributeName="href" to="https://example.com/a"/></svg>'
        self.assertIn("svg-active-content", checker.scan_svg(value))

    def test_clean_pdf(self):
        self.assertEqual(checker.scan_pdf(pdf({"/Title": "Synthetic portfolio"})), set())

    def test_pdf_secret_metadata(self):
        self.assertIn("github-token", checker.scan_pdf(pdf({"/Author": synthetic_token()})))

    def test_pdf_oauth_metadata(self):
        value = "1234567890-" + "fixture.apps." + "googleusercontent.com"
        self.assertIn("oauth-client-id", checker.scan_pdf(pdf({"/Subject": value})))

    def test_pdf_xmp_metadata(self):
        from pypdf.generic import DecodedStreamObject, NameObject
        def add(writer):
            stream = DecodedStreamObject()
            stream.set_data(("<meta>" + synthetic_token() + "</meta>").encode())
            stream[NameObject("/Type")] = NameObject("/Metadata")
            stream[NameObject("/Subtype")] = NameObject("/XML")
            writer._root_object[NameObject("/Metadata")] = writer._add_object(stream)
        self.assertIn("github-token", checker.scan_pdf(pdf(mutate=add)))

    def test_pdf_sensitive_link(self):
        from pypdf.annotations import Link
        def add(writer):
            writer.add_annotation(page_number=0, annotation=Link(rect=(0, 0, 50, 50), url="https://fixture." + "supabase." + "co"))
        self.assertIn("service-endpoint", checker.scan_pdf(pdf(mutate=add)))

    def test_pdf_unsafe_link(self):
        from pypdf.annotations import Link
        def add(writer):
            writer.add_annotation(page_number=0, annotation=Link(rect=(0, 0, 50, 50), url="javascript:void(0)"))
        self.assertIn("pdf-unsafe-link", checker.scan_pdf(pdf(mutate=add)))

    def test_pdf_text_content(self):
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        def add(writer):
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
            writer.pages[0][NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(("BT /F1 10 Tf 10 10 Td (" + synthetic_token() + ") Tj ET").encode())
            writer.pages[0][NameObject("/Contents")] = writer._add_object(stream)
        self.assertIn("github-token", checker.scan_pdf(pdf(mutate=add)))

    def test_pdf_javascript(self):
        self.assertIn("pdf-active-content-or-attachment", checker.scan_pdf(pdf(mutate=lambda writer: writer.add_js("void(0);"))))

    def test_pdf_attachment(self):
        self.assertIn("pdf-active-content-or-attachment", checker.scan_pdf(pdf(mutate=lambda writer: writer.add_attachment("fixture.txt", b"sample"))))

    def test_pdf_forms_and_open_action(self):
        from pypdf.generic import DictionaryObject, NameObject
        for key in ("/AcroForm", "/OpenAction"):
            with self.subTest(key=key):
                def add(writer):
                    writer._root_object[NameObject(key)] = DictionaryObject()
                self.assertIn("pdf-active-content-or-attachment", checker.scan_pdf(pdf(mutate=add)))

    def test_pdf_encrypted(self):
        self.assertIn("pdf-encrypted", checker.scan_pdf(pdf(mutate=lambda writer: writer.encrypt("synthetic"))))

    def test_pdf_invalid(self):
        self.assertIn("pdf-unreadable", checker.scan_pdf(b"not a document"))

    def test_unknown_binary(self):
        self.assertEqual(checker.scan_content("fixture.bin", b"\xff\x00"), {"unsupported-binary"})


@unittest.skipUnless(shutil.which("git"), "Git is required for inventory tests")
class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Synthetic Test")
        self.write("README.md", "Curated, synthetic portfolio.\n")
        self.allow("README.md")

    def tearDown(self):
        # Windows may mark Git object files read-only.
        def retry(function, path, _):
            import os
            import stat
            os.chmod(path, stat.S_IWRITE)
            function(path)
        shutil.rmtree(self.root, onerror=retry)
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.run([shutil.which("git"), "-C", str(self.root), *args], capture_output=True, check=True).stdout

    def write(self, name, contents):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")

    def allow(self, *paths):
        self.write(checker.ALLOWLIST, "\n".join([checker.ALLOWLIST, *paths]) + "\n")

    def rules(self, history=False):
        return {issue.rule for issue in checker.check_repository(self.root, history)}

    def test_untracked_allowlisted_files_pass(self):
        self.assertEqual(self.rules(), set())

    def test_tracked_allowlisted_files_pass(self):
        self.git("add", ".")
        self.assertEqual(self.rules(), set())

    def test_extra_untracked_fails(self):
        self.write("extra.md", "sample")
        self.assertIn("not-allowlisted", self.rules())

    def test_extra_tracked_fails(self):
        self.write("extra.md", "sample")
        self.git("add", "extra.md")
        self.assertIn("not-allowlisted", self.rules())

    def test_ignored_untracked_is_outside_scope(self):
        self.write(".gitignore", "ignored.txt\n")
        self.write("ignored.txt", synthetic_token())
        self.allow("README.md", ".gitignore")
        self.assertEqual(self.rules(), set())

    def test_tracked_ignored_file_is_still_checked(self):
        self.write(".gitignore", "ignored.txt\n")
        self.write("ignored.txt", synthetic_token())
        self.allow("README.md", ".gitignore", "ignored.txt")
        self.git("add", "-f", "ignored.txt")
        self.assertIn("github-token", self.rules())

    def test_required_missing_fails(self):
        self.allow("README.md", "absent.md")
        self.assertIn("required-file-missing", self.rules())

    def test_required_ignored_fails_inventory(self):
        self.write(".gitignore", "ignored.txt\n")
        self.write("ignored.txt", "sample")
        self.allow("README.md", ".gitignore", "ignored.txt")
        self.assertIn("required-file-not-in-git-inventory", self.rules())

    def test_invalid_allowlist_paths(self):
        for value in ("../escape", "/absolute", "folder/../../escape", "*.md", "docs/[ab].md", "folder\\file", "./README.md", "folder//file", ".git/config"):
            with self.subTest(value=value):
                self.allow("README.md", value)
                self.assertTrue(any(rule.startswith("invalid-entry-line-") for rule in self.rules()))

    def test_allowlist_duplicate(self):
        self.allow("README.md", "README.md")
        self.assertTrue(any(rule.startswith("duplicate-entry-line-") for rule in self.rules()))

    def test_allowlist_requires_itself(self):
        self.write(checker.ALLOWLIST, "README.md\n")
        self.assertIn("allowlist-must-list-itself", self.rules())

    def test_allowlisting_new_secret_does_not_bypass_content_scan(self):
        self.write("new.txt", synthetic_token())
        self.allow("README.md", "new.txt")
        self.assertIn("github-token", self.rules())

    def test_allowlist_contents_are_also_scanned(self):
        self.write(checker.ALLOWLIST, checker.ALLOWLIST + "\nREADME.md\n# " + synthetic_token())
        self.assertIn("github-token", self.rules())

    def test_symlink_rejected(self):
        link = self.root / "linked.md"
        try:
            link.symlink_to(self.root / "README.md")
        except OSError:
            self.skipTest("Symlink creation is unavailable on this host")
        self.allow("README.md", "linked.md")
        self.assertIn("symlink-or-reparse-point", self.rules())

    def test_git_index_symlink_rejected_even_when_not_materialized(self):
        oid = self.git("hash-object", "-w", "README.md").decode().strip()
        self.git("update-index", "--add", "--cacheinfo", "120000", oid, "virtual-link.md")
        self.allow("README.md", "virtual-link.md")
        self.assertIn("symlink-or-submodule", self.rules())

    def test_size_limit(self):
        self.write("README.md", "x" * 101)
        with patch.object(checker, "MAX_FILE", 100):
            self.assertIn("file-size-limit", self.rules())

    def test_total_limit(self):
        with patch.object(checker, "MAX_TOTAL", 50):
            self.assertIn("total-size-limit", self.rules())

    def test_no_git_repository_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(checker.check_repository(Path(temporary)), [checker.Issue("<repository>", "git-repository-required")])

    def test_nested_directory_cannot_scan_parent_repository(self):
        nested = self.root / "nested"
        nested.mkdir()
        self.assertEqual(checker.check_repository(nested), [checker.Issue("<repository>", "git-repository-required")])

    def test_history_clean(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic first snapshot")
        self.assertEqual(self.rules(history=True), set())

    def test_history_finds_secret_removed_from_current_file(self):
        self.write("README.md", synthetic_token())
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic fixture")
        self.write("README.md", "clean")
        self.git("add", ".")
        self.git("commit", "-qm", "Remove fixture")
        self.assertEqual(self.rules(), set())
        self.assertIn("github-token", self.rules(history=True))

    def test_history_deleted_nonallowlisted_path(self):
        self.write("old.md", "sample")
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic fixture")
        self.git("rm", "-q", "old.md")
        self.git("commit", "-qm", "Remove fixture")
        self.assertEqual(self.rules(), set())
        self.assertIn("not-allowlisted", self.rules(history=True))

    def test_history_commit_limit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic fixture")
        with patch.object(checker, "MAX_COMMITS", 0):
            self.assertIn("commit-count-limit", self.rules(history=True))

    def test_history_empty_fails_clearly(self):
        self.assertIn("no-reachable-commits", self.rules(history=True))

    def test_cli_does_not_print_secret(self):
        self.write("README.md", synthetic_token())
        output = io.StringIO()
        with redirect_stdout(output):
            result = checker.main(["--root", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("README.md: github-token", output.getvalue())
        self.assertNotIn(synthetic_token(), output.getvalue())

    def test_cli_does_not_print_secret_filename(self):
        filename = synthetic_token() + ".txt"
        self.write(filename, "sample")
        self.allow("README.md", filename)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(checker.main(["--root", str(self.root)]), 1)
        self.assertIn("<redacted-path>", output.getvalue())
        self.assertNotIn(synthetic_token(), output.getvalue())


if __name__ == "__main__":
    unittest.main()
