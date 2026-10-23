import json
import re
import zipfile
from io import BytesIO

import pymupdf
import pytesseract
import streamlit as st
from PIL import Image

# Windows Tesseract installation.
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

MAX_ZIP_FILES = 500
MAX_SOURCE_FILE_BYTES = 500_000
MAX_TOTAL_SOURCE_BYTES = 10_000_000

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".sql",
    ".sh",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".md",
    ".txt",
    ".xml",
}

IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}

IGNORED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
}

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "their",
    "have",
    "has",
    "will",
    "can",
    "should",
    "must",
    "are",
    "was",
    "were",
    "been",
    "being",
    "then",
    "than",
    "when",
    "where",
    "what",
    "which",
    "who",
    "how",
    "why",
    "all",
    "any",
    "each",
    "use",
    "using",
    "user",
    "users",
    "system",
    "project",
    "application",
    "app",
    "feature",
    "features",
    "support",
    "based",
}

WORD_NORMALIZATION = {
    "completed": "complete",
    "completes": "complete",
    "creating": "create",
    "created": "create",
    "creates": "create",
    "tasks": "task",
    "stored": "store",
    "stores": "store",
    "storing": "store",
    "marked": "mark",
    "marking": "mark",
    "saved": "save",
    "saves": "save",
    "saving": "save",
}

DATABASE_INDICATORS = (
    "sqlite3.connect",
    "sqlite.connect",
    "psycopg.connect",
    "psycopg2.connect",
    "create_engine(",
    "pymongo",
    "mongodb",
    "mysql.connector",
    "sqlite3.",
    "sqlalchemy",
    "cursor.execute(",
    "session.add(",
    "session.commit(",
    "db.session",
    "database_url",
)


def extract_pdf_text(file_bytes: bytes) -> tuple[str, int]:
    """Extract selectable PDF text or OCR scanned pages."""
    extracted_pages = []

    with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
        page_count = len(document)

        for page_number, page in enumerate(document, start=1):
            text = page.get_text().strip()

            if not text:
                pixmap = page.get_pixmap(dpi=200, alpha=False)
                image_bytes = pixmap.tobytes("png")

                with Image.open(BytesIO(image_bytes)) as image:
                    text = pytesseract.image_to_string(image, lang="eng").strip()

            if not text:
                text = "[No text recognized]"

            extracted_pages.append(f"--- Page {page_number} ---\n{text}")

    return "\n\n".join(extracted_pages), page_count


def extract_image_text(image_bytes: bytes) -> tuple[Image.Image, str]:
    """Open an image and recognize its English text."""
    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGB")

    text = pytesseract.image_to_string(image, lang="eng").strip()
    return image, text


def read_requirements(filename: str, file_bytes: bytes) -> str:
    """Read PDF or plain-text project requirements."""
    if filename.lower().endswith(".pdf"):
        text, _ = extract_pdf_text(file_bytes)
        return text

    return file_bytes.decode("utf-8-sig", errors="replace")


def inspect_project_zip(
    zip_bytes: bytes,
) -> tuple[list[dict[str, str]], list[str]]:
    """Read source files from a ZIP without extracting or executing them."""
    files: list[dict[str, str]] = []
    warnings: list[str] = []
    total_bytes = 0

    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            members = archive.infolist()

            if len(members) > MAX_ZIP_FILES:
                return [], [
                    f"ZIP contains {len(members)} entries. "
                    f"The limit is {MAX_ZIP_FILES}."
                ]

            for member in members:
                if member.is_dir():
                    continue

                path = member.filename.replace("\\", "/")
                parts = path.split("/")
                filename = parts[-1]
                lowered_parts = {part.lower() for part in parts}

                if lowered_parts & IGNORED_PARTS:
                    continue

                if filename.lower() in IGNORED_NAMES or filename.lower().startswith(
                    ".env"
                ):
                    warnings.append(f"Skipped sensitive-looking file: {path}")
                    continue

                suffix = (
                    "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                )

                if suffix not in SOURCE_EXTENSIONS:
                    continue

                if member.file_size > MAX_SOURCE_FILE_BYTES:
                    warnings.append(f"Skipped large file: {path}")
                    continue

                if total_bytes + member.file_size > MAX_TOTAL_SOURCE_BYTES:
                    warnings.append("Reached the total source-size limit.")
                    break

                try:
                    content = archive.read(member)
                    text = content.decode("utf-8-sig")
                except (
                    UnicodeDecodeError,
                    OSError,
                    RuntimeError,
                    zipfile.BadZipFile,
                ):
                    warnings.append(f"Skipped unreadable file: {path}")
                    continue

                files.append({"path": path, "text": text})
                total_bytes += len(content)

    except (zipfile.BadZipFile, OSError, ValueError):
        return [], ["The uploaded file is not a readable ZIP archive."]

    if not files and not warnings:
        warnings.append("No supported source or documentation files found.")

    return files, warnings


def tokenize(text: str) -> set[str]:
    """Convert prose and code identifiers into comparable keywords."""
    text = text.replace("_", " ").lower()
    words = re.findall(r"[a-z][a-z0-9+#.-]*", text)
    normalized = set()

    for word in words:
        word = WORD_NORMALIZATION.get(word, word)

        if len(word) > 2 and word not in STOP_WORDS:
            normalized.add(word)

    return normalized


def extract_requirements(text: str) -> list[str]:
    """Build a preliminary checklist from requirement-document lines."""
    requirements = []

    for line in text.splitlines():
        cleaned = line.strip()
        cleaned = re.sub(r"^#{1,6}\s*", "", cleaned)
        cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", cleaned)
        cleaned = cleaned.strip()

        if len(cleaned) < 12:
            continue

        if cleaned.startswith(("--- Page ", "[No text")):
            continue

        if cleaned.endswith(":") and len(cleaned.split()) <= 6:
            continue

        requirements.append(cleaned)

    if not requirements:
        requirements = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if len(sentence.strip()) >= 12
        ]

    return list(dict.fromkeys(requirements))[:50]


def is_database_requirement(requirement: str) -> bool:
    """Identify requirements explicitly about persistence or databases."""
    text = requirement.lower()

    phrases = (
        "database",
        "persistent storage",
        "stores tasks",
        "store tasks",
        "save tasks",
        "save data",
        "persist data",
        "persist tasks",
        "store data",
    )

    return any(phrase in text for phrase in phrases)


def match_requirements(
    requirements: list[str],
    source_files: list[dict[str, str]],
) -> list[dict[str, object]]:
    """Find potential implementation evidence using conservative heuristics."""
    results = []

    implementation_extensions = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".cs",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".sql",
    }

    for requirement in requirements:
        requirement_terms = tokenize(requirement)
        evidence = []
        needs_database = is_database_requirement(requirement)

        for source in source_files:
            path = source["path"]
            source_text = source["text"]
            source_lower = source_text.lower()

            suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""

            # Documentation is context, not proof of implementation.
            if suffix in {".md", ".txt"}:
                continue

            if suffix not in implementation_extensions:
                continue

            # Database requirements need database-related code evidence.
            if needs_database and not any(
                indicator in source_lower for indicator in DATABASE_INDICATORS
            ):
                continue

            source_terms = tokenize(source_text)
            overlap = requirement_terms & source_terms

            if not overlap:
                continue

            score = len(overlap) / max(len(requirement_terms), 1)

            evidence.append(
                {
                    "path": path,
                    "matched_terms": sorted(overlap),
                    "score": round(score, 2),
                }
            )

        evidence.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        best_score = evidence[0]["score"] if evidence else 0.0

        if best_score >= 0.5:
            status = "Possible evidence"
        elif best_score >= 0.2:
            status = "Weak evidence"
        else:
            status = "No evidence found"

        results.append(
            {
                "requirement": requirement,
                "status": status,
                "best_match_score": best_score,
                "evidence": evidence[:3],
            }
        )

    return results


def main() -> None:
    st.set_page_config(
        page_title="ProofSprint AI | Project Auditor",
        page_icon="🔍",
        layout="wide",
    )

    st.title("ProofSprint AI")
    st.subheader("Project Auditor for Hackathon Teams and Developers")
    st.write(
        "Compare a project brief with your source code, find potential "
        "evidence gaps, and prepare for your submission."
    )

    st.info(
        "Prototype: this version uses keyword matching, not an AI model. "
        "A match does not prove a feature works. Review findings manually."
    )

    with st.sidebar:
        st.header("Audit workflow")
        st.write("1. Upload the project requirements.")
        st.write("2. Upload the source-code ZIP.")
        st.write("3. Review the evidence matches.")
        st.write("4. Download the audit report.")

    left, right = st.columns(2)

    with left:
        st.markdown("### 1. Project requirements")
        brief = st.file_uploader(
            "Upload a problem statement or requirements document",
            type=["pdf", "txt", "md"],
            key="project_brief",
        )

    with right:
        st.markdown("### 2. Project source code")
        project_zip = st.file_uploader(
            "Upload the project as a ZIP file",
            type=["zip"],
            key="project_zip",
        )

    brief_text = ""

    if brief is not None:
        try:
            brief_text = read_requirements(brief.name, brief.getvalue())
            st.success("Requirements document loaded.")

            with st.expander("Preview extracted requirements text"):
                st.text(brief_text[:12000])

        except (
            pymupdf.FileDataError,
            RuntimeError,
            ValueError,
            OSError,
        ):
            st.error(
                "Could not read the requirements document. "
                "Check that the file is valid and try again."
            )

    project_files = []
    warnings = []

    if project_zip is not None:
        project_files, warnings = inspect_project_zip(project_zip.getvalue())

        if project_files:
            st.success(f"Read {len(project_files)} source/documentation files.")

        for warning in warnings:
            st.warning(warning)

    if st.button("Run project audit", type="primary"):
        if not brief_text.strip():
            st.error("Upload a readable project requirements document.")
        elif not project_files:
            st.error("Upload a ZIP containing supported source files.")
        else:
            requirements = extract_requirements(brief_text)

            if not requirements:
                st.error(
                    "No requirements could be extracted. "
                    "Try a text document with one requirement per line."
                )
            else:
                results = match_requirements(requirements, project_files)

                st.session_state["last_audit"] = {
                    "project_brief": brief.name,
                    "source_file_count": len(project_files),
                    "requirements": results,
                    "warnings": warnings,
                }

    report = st.session_state.get("last_audit")

    if report:
        st.divider()
        st.header("Project audit report")

        results = report["requirements"]

        possible = sum(item["status"] == "Possible evidence" for item in results)
        weak = sum(item["status"] == "Weak evidence" for item in results)
        missing = sum(item["status"] == "No evidence found" for item in results)

        first, second, third = st.columns(3)
        first.metric("Possible evidence", possible)
        second.metric("Weak evidence", weak)
        third.metric("No evidence found", missing)

        st.caption(
            "These labels describe keyword matches only, not verified "
            "feature completion or code correctness."
        )

        for index, item in enumerate(results, start=1):
            with st.expander(f"{index}. {item['status']} — {item['requirement']}"):
                evidence = item["evidence"]

                if evidence:
                    for match in evidence:
                        st.write(f"**File:** `{match['path']}`")
                        st.write("Matched terms: " + ", ".join(match["matched_terms"]))
                        st.write(f"Keyword overlap: {match['score']:.0%}")
                else:
                    st.write(
                        "No matching implementation evidence was found "
                        "by the current heuristic."
                    )

        st.download_button(
            "Download audit report (JSON)",
            data=json.dumps(report, indent=2, ensure_ascii=False),
            file_name="proofsprint_audit_report.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
