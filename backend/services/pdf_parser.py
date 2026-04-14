import re

import fitz


SECTION_PATTERNS = {
    "summary": re.compile(r"^(summary|professional summary|profile)$", re.IGNORECASE),
    "experience": re.compile(r"^(experience|work experience|professional experience)$", re.IGNORECASE),
    "skills": re.compile(r"^(skills|technical skills|core competencies)$", re.IGNORECASE),
    "education": re.compile(r"^(education|academic background)$", re.IGNORECASE),
    "projects": re.compile(r"^(projects|selected projects)$", re.IGNORECASE),
}


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages = [page.get_text("text") for page in document]
    finally:
        document.close()
    return "\n".join(pages).strip()


def chunk_resume_text(raw_text: str) -> list[dict]:
    sections: list[dict] = []
    current_name = "general"
    current_lines: list[str] = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        matched_name = _match_section_name(stripped)
        if matched_name:
            if current_lines:
                sections.append(
                    {
                        "section": current_name,
                        "text": "\n".join(current_lines).strip(),
                    }
                )
            current_name = matched_name
            current_lines = [stripped]
            continue

        current_lines.append(stripped)

    if current_lines:
        sections.append({"section": current_name, "text": "\n".join(current_lines).strip()})

    expanded_chunks: list[dict] = []
    for section in sections:
        expanded_chunks.extend(_split_section_chunk(section["section"], section["text"]))

    return [section for section in expanded_chunks if section["text"]]


def _match_section_name(line: str) -> str | None:
    normalized = re.sub(r"[:\s]+$", "", line).strip()
    for section_name, pattern in SECTION_PATTERNS.items():
        if pattern.match(normalized):
            return section_name
    return None


def _split_section_chunk(section: str, text: str, max_chars: int = 1200) -> list[dict]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(text) <= max_chars:
        return [{"section": section, "text": text}]

    chunks: list[dict] = []
    current_lines: list[str] = []
    current_length = 0

    for line in lines:
        projected_length = current_length + len(line) + 1
        if current_lines and projected_length > max_chars:
            chunks.append({"section": section, "text": "\n".join(current_lines)})
            current_lines = []
            current_length = 0

        current_lines.append(line)
        current_length += len(line) + 1

    if current_lines:
        chunks.append({"section": section, "text": "\n".join(current_lines)})

    return chunks
