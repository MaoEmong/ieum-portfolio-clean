#!/usr/bin/env python3
"""Check this curated repository's explicit disclosure boundary, without network I/O.

This is a bounded heuristic check, not a proof that content contains no private data.
Git-ignored working files and image pixels are outside its scope. --history checks
tracked blob paths/content in commits reachable from local refs; commit messages,
unreachable objects and reflogs are excluded.
"""

from __future__ import annotations

import argparse
import io
import logging
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import subprocess
import sys
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import zlib


MAX_FILE = 5 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 4096
MAX_COMMITS = 100
ALLOWLIST = "disclosure-allowlist.txt"

# Patterns deliberately describe signatures rather than containing live examples.
TEXT_RULES = {
    "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    "github-token": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
    "api-token": r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b",
    "cloud-access-key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "jwt-token": r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
    "credential-url": r"(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|https?)://[^\s/:@]+:[^\s/@]+@",
    "service-endpoint": r"\b[a-z0-9][a-z0-9.-]*\.(?:onrender\.com|supabase\.(?:co|com))\b",
    "oauth-client-id": r"\b\d{5,}-[a-z0-9_-]+\.apps\.googleusercontent\.com\b",
    "local-private-path": r"\b[A-Z]:[\\/](?:Users[\\/]|myproject(?:[\\/]|\b))",
    "product-app-id": r"\b(?:com|kr|io|net|org)(?:[.][a-z][a-z0-9_]*){2,}\b",
    "provider-resource-id": r"\b(?:srv|dep)-[a-z0-9]{15,}\b",
    "configured-app-id": r"\b(?:KAKAO_APP_ID|KAKAO_NATIVE_APP_KEY|GOOGLE_SERVER_CLIENT_ID)\b\s*[:=]\s*[\"']?[A-Za-z0-9_-]{4,}",
    "assigned-credential": r"\b(?:password|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']",
}
COMPILED_RULES = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in TEXT_RULES.items()}

# Official dependency namespaces used by the standalone Java example. This
# exception applies only to an individual reverse-DNS match, never an entire
# file or any secret, endpoint, or other disclosure rule.
JAVA_DEPENDENCY_NAMESPACES = (
    "org.springframework",
    "org.junit",
    "org.assertj",
    "org.apache.maven.plugins",
)


@dataclass(frozen=True, order=True)
class Issue:
    path: str
    rule: str


def text_rules(value: str) -> set[str]:
    issues = {
        name for name, pattern in COMPILED_RULES.items()
        if name != "product-app-id" and pattern.search(value)
    }
    for match in COMPILED_RULES["product-app-id"].finditer(value):
        identifier = match.group().lower()
        if not any(identifier == prefix or identifier.startswith(prefix + ".")
                   for prefix in JAVA_DEPENDENCY_NAMESPACES):
            issues.add("product-app-id")
    return issues


def safe_path(value: str) -> str:
    if text_rules(value):
        return "<redacted-path>"
    return "".join(character if character.isprintable() else "?" for character in value)


def valid_relative(value: str) -> bool:
    if not value or value != value.strip() or any(c in value for c in "\\:*?[]\x00\r\n"):
        return False
    if value.startswith("/") or any(part in ("", ".", "..", ".git") for part in value.split("/")):
        return False
    return not PurePosixPath(value).is_absolute()


def is_link(path: Path) -> bool:
    details = path.lstat()
    return stat.S_ISLNK(details.st_mode) or bool(
        getattr(details, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def contained_file(root: Path, relative: str) -> str | None:
    if not valid_relative(relative):
        return "invalid-path"
    path = root
    try:
        for part in relative.split("/"):
            path = path / part
            if is_link(path):
                return "symlink-or-reparse-point"
        path.resolve().relative_to(root)
        if not path.is_file():
            return "not-regular-file"
    except FileNotFoundError:
        return "required-file-missing"
    except (OSError, ValueError):
        return "unsafe-or-unreadable-path"
    return None


def git(root: Path, *arguments: str) -> bytes:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git-unavailable")
    try:
        result = subprocess.run(
            [executable, "-C", str(root), *arguments], capture_output=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("git-command-failed") from None
    if result.returncode:
        raise RuntimeError("git-command-failed")
    if len(result.stdout) > MAX_TOTAL:
        raise RuntimeError("git-output-limit")
    return result.stdout


def read_allowlist(root: Path) -> tuple[set[str], list[Issue]]:
    problem = contained_file(root, ALLOWLIST)
    if problem:
        return set(), [Issue(ALLOWLIST, problem)]
    try:
        if (root / ALLOWLIST).stat().st_size > MAX_FILE:
            return set(), [Issue(ALLOWLIST, "file-size-limit")]
        contents = (root / ALLOWLIST).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return set(), [Issue(ALLOWLIST, "allowlist-unreadable")]
    allowed: set[str] = set()
    issues = []
    for number, line in enumerate(contents.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not valid_relative(line):
            issues.append(Issue(ALLOWLIST, f"invalid-entry-line-{number}"))
        elif line in allowed:
            issues.append(Issue(ALLOWLIST, f"duplicate-entry-line-{number}"))
        else:
            allowed.add(line)
    if ALLOWLIST not in allowed:
        issues.append(Issue(ALLOWLIST, "allowlist-must-list-itself"))
    if len(allowed) > MAX_FILES:
        issues.append(Issue(ALLOWLIST, "file-count-limit"))
    return allowed, issues


def scan_png(data: bytes) -> set[str]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return {"png-invalid"}
    issues: set[str] = set()
    offset = 8
    seen_header = False
    seen_data = False
    approved = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"cHRM", b"gAMA", b"sBIT", b"sRGB", b"pHYs"}
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data):
            return issues | {"png-invalid"}
        body = data[offset + 8 : end - 4]
        crc = struct.unpack(">I", data[end - 4 : end])[0]
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            issues.add("png-invalid")
        if kind in (b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"iCCP", b"tIME"):
            issues.add("png-metadata")
        elif kind not in approved:
            issues.add("png-unapproved-chunk")
        if not seen_header and kind != b"IHDR":
            issues.add("png-invalid")
        if kind == b"IHDR":
            if seen_header or length != 13:
                issues.add("png-invalid")
            seen_header = True
        if kind == b"IDAT":
            seen_data = True
        if kind == b"IEND":
            if length or end != len(data) or not seen_header or not seen_data:
                issues.add("png-invalid")
            return issues
        offset = end
    return issues | {"png-invalid"}


def scan_svg(text: str) -> set[str]:
    issues = text_rules(text)
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.IGNORECASE):
        return issues | {"svg-entity-or-doctype"}
    if re.search(r"<\?(?!xml\s)", text, re.IGNORECASE):
        issues.add("svg-processing-instruction")
    try:
        tree = ET.fromstring(text)
    except ET.ParseError:
        return issues | {"svg-invalid"}
    if tree.tag.rsplit("}", 1)[-1].lower() != "svg":
        issues.add("svg-invalid")
    for node in tree.iter():
        name = node.tag.rsplit("}", 1)[-1].lower()
        if name in ("script", "foreignobject", "iframe", "object", "embed", "animate", "animatemotion", "animatetransform", "set", "discard", "audio", "video"):
            issues.add("svg-active-content")
        for key, value in node.attrib.items():
            attribute = key.rsplit("}", 1)[-1].lower()
            if attribute.startswith("on"):
                issues.add("svg-event-handler")
            if attribute in ("href", "src") and not value.strip().startswith("#"):
                issues.add("svg-external-reference")
    if re.search(r"@import\b", text, re.IGNORECASE):
        issues.add("svg-external-reference")
    for match in re.finditer(r"url\(\s*([^)]+)\)", text, re.IGNORECASE):
        if not match.group(1).strip(" \t\r\n\"'").startswith("#"):
            issues.add("svg-external-reference")
    return issues


def scan_pdf(data: bytes) -> set[str]:
    try:
        from pypdf import PdfReader
        from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, StreamObject, TextStringObject
    except ImportError:
        return {"pdf-dependency-missing"}
    logging.getLogger("pypdf").setLevel(logging.CRITICAL)
    # Also inspect literal bytes, including unused objects from incremental saves.
    # Encoded/compressed content still needs the structured traversal below.
    issues: set[str] = text_rules(data.decode("utf-8", errors="ignore"))
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            return {"pdf-encrypted"}
        if len(reader.pages) > 50:
            return {"pdf-page-limit"}
        forbidden = {"/OpenAction", "/AA", "/JavaScript", "/JS", "/EmbeddedFiles", "/EF", "/AcroForm", "/XFA", "/RichMediaContent"}
        forbidden_actions = {"/JavaScript", "/Launch", "/SubmitForm", "/ImportData", "/GoToR", "/GoToE", "/Rendition"}
        visited: set[tuple[int, int] | int] = set()
        stack = [(reader.trailer, 0)]
        nodes = 0
        text_size = 0
        while stack:
            value, depth = stack.pop()
            nodes += 1
            if nodes > 20000 or depth > 64:
                return issues | {"pdf-object-limit"}
            if isinstance(value, IndirectObject):
                identity = (value.idnum, value.generation)
                if identity in visited:
                    continue
                visited.add(identity)
                stack.append((value.get_object(), depth + 1))
            elif isinstance(value, DictionaryObject):
                identity = id(value)
                if identity in visited:
                    continue
                visited.add(identity)
                if forbidden.intersection(value.keys()) or str(value.get("/S")) in forbidden_actions:
                    issues.add("pdf-active-content-or-attachment")
                if str(value.get("/Type")) in ("/Filespec", "/EmbeddedFile") or str(value.get("/Subtype")) == "/FileAttachment":
                    issues.add("pdf-active-content-or-attachment")
                if "/URI" in value and not re.match(r"^(?:https?://|mailto:)", str(value["/URI"]), re.IGNORECASE):
                    issues.add("pdf-unsafe-link")
                stack.extend((child, depth + 1) for child in value.values())
                if isinstance(value, StreamObject) and (str(value.get("/Type")) == "/Metadata" or str(value.get("/Subtype")) == "/XML"):
                    metadata = value.get_data()
                    text_size += len(metadata)
                    if text_size > MAX_FILE:
                        return issues | {"pdf-text-limit"}
                    issues.update(text_rules(metadata.decode("utf-8", errors="replace")))
            elif isinstance(value, ArrayObject):
                stack.extend((child, depth + 1) for child in value)
            elif isinstance(value, (str, TextStringObject)):
                text_size += len(value.encode("utf-8", errors="replace"))
                if text_size > MAX_FILE:
                    return issues | {"pdf-text-limit"}
                issues.update(text_rules(str(value)))
            elif isinstance(value, bytes):
                # Undecodable document strings should not bypass metadata checks.
                for encoding in ("utf-8", "utf-16-be", "utf-16-le"):
                    issues.update(text_rules(value.decode(encoding, errors="ignore")))
        for page in reader.pages:
            extracted = page.extract_text() or ""
            text_size += len(extracted.encode("utf-8"))
            if text_size > MAX_FILE:
                return issues | {"pdf-text-limit"}
            issues.update(text_rules(extracted))
    except Exception:
        # Parser errors can contain document text; report only a fixed rule.
        issues.add("pdf-unreadable")
    return issues


def scan_content(path: str, data: bytes) -> set[str]:
    if len(data) > MAX_FILE:
        return {"file-size-limit"}
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".pdf":
        return scan_pdf(data)
    if suffix == ".png":
        return scan_png(data)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        return {"unsupported-binary"}
    if "\x00" in text:
        return {"unsupported-binary"}
    return scan_svg(text) if suffix == ".svg" else text_rules(text)


def history_issues(root: Path, allowed: set[str], remaining: int) -> list[Issue]:
    issues: list[Issue] = []
    commits = git(root, "rev-list", "--all", f"--max-count={MAX_COMMITS + 1}").splitlines()
    if not commits:
        return [Issue("<history>", "no-reachable-commits")]
    if len(commits) > MAX_COMMITS:
        return [Issue("<history>", "commit-count-limit")]
    checked: dict[tuple[str, str], set[str]] = {}
    seen_blobs: dict[str, bytes] = {}
    for commit in commits:
        entries = git(root, "ls-tree", "-r", "-z", "--full-tree", commit.decode("ascii")).split(b"\x00")
        if len(entries) > MAX_FILES + 1:
            return issues + [Issue("<history>", "file-count-limit")]
        for entry in filter(None, entries):
            header, raw_path = entry.split(b"\t", 1)
            mode, kind, raw_oid = header.split()
            path = raw_path.decode("utf-8", errors="replace")
            label = "history:" + safe_path(path)
            if not valid_relative(path):
                issues.append(Issue("<history>", "invalid-path"))
                continue
            if path not in allowed:
                issues.append(Issue(label, "not-allowlisted"))
            issues.extend(Issue(label, rule) for rule in text_rules(path))
            if mode == b"120000" or kind != b"blob":
                issues.append(Issue(label, "symlink-or-submodule"))
                continue
            oid = raw_oid.decode("ascii")
            if oid not in seen_blobs:
                size = int(git(root, "cat-file", "-s", oid))
                if size > MAX_FILE:
                    issues.append(Issue(label, "file-size-limit"))
                    continue
                remaining -= size
                if remaining < 0:
                    return issues + [Issue("<history>", "total-size-limit")]
                seen_blobs[oid] = git(root, "cat-file", "blob", oid)
            key = (oid, PurePosixPath(path).suffix.lower())
            if key not in checked:
                checked[key] = scan_content(path, seen_blobs[oid])
            issues.extend(Issue(label, rule) for rule in checked[key])
    return issues


def check_repository(root: Path, history: bool = False) -> list[Issue]:
    try:
        if is_link(root):
            return [Issue("<repository>", "symlink-or-reparse-point")]
        root = root.resolve(strict=True)
        if not (root / ".git").exists():
            return [Issue("<repository>", "git-repository-required")]
        top = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
        if top != root:
            return [Issue("<repository>", "root-must-be-git-toplevel")]
    except (OSError, RuntimeError):
        return [Issue("<repository>", "git-repository-required")]
    allowed, issues = read_allowlist(root)
    if issues:
        return sorted(set(issues))
    try:
        paths = {
            value.decode("utf-8", errors="replace")
            for value in git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\x00")
            if value
        }
        if len(paths) > MAX_FILES:
            return [Issue("<repository>", "file-count-limit")]
        for entry in filter(None, git(root, "ls-files", "--stage", "-z").split(b"\x00")):
            header, raw_path = entry.split(b"\t", 1)
            if header.split()[0] in (b"120000", b"160000"):
                issues.append(Issue(safe_path(raw_path.decode("utf-8", errors="replace")), "symlink-or-submodule"))
        total = 0
        for path in sorted(paths | allowed):
            label = safe_path(path)
            if path not in allowed:
                issues.append(Issue(label, "not-allowlisted"))
            if path not in paths:
                issues.append(Issue(label, "required-file-not-in-git-inventory"))
            issues.extend(Issue(label, rule) for rule in text_rules(path))
            problem = contained_file(root, path)
            if problem:
                issues.append(Issue(label, problem))
                continue
            file = root / path
            size = file.stat().st_size
            if size > MAX_FILE:
                issues.append(Issue(label, "file-size-limit"))
                continue
            total += size
            if total > MAX_TOTAL:
                issues.append(Issue("<repository>", "total-size-limit"))
                break
            with file.open("rb") as stream:
                data = stream.read(MAX_FILE + 1)
            if len(data) != size:
                issues.append(Issue(label, "file-changed-during-check"))
            issues.extend(Issue(label, rule) for rule in scan_content(path, data))
        if history:
            issues.extend(history_issues(root, allowed, MAX_TOTAL - total))
    except (OSError, RuntimeError, ValueError):
        issues.append(Issue("<repository>", "inventory-or-read-failed"))
    return sorted(set(issues))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--history", action="store_true", help="also check all commits reachable from local refs")
    arguments = parser.parse_args(argv)
    issues = check_repository(arguments.root, arguments.history)
    for issue in issues:
        print(f"{issue.path}: {issue.rule}")
    if issues:
        print(f"Disclosure check failed: {len(issues)} finding(s).")
        return 1
    print("Disclosure checks passed for the selected Git files" + (" and reachable history." if arguments.history else "."))
    print("Heuristic scope only; image pixels, ignored files and semantic privacy review are not covered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
