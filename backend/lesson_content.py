from __future__ import annotations

import json
from typing import Iterable
from urllib.parse import quote

from backend.models import Lesson
from backend.schemas import LessonContentBlock, LessonDetailRead, LessonRead


def build_legacy_blocks(content: str | None) -> list[LessonContentBlock]:
    text = (content or "").strip()
    if not text:
        return []

    paragraphs = [paragraph.strip() for paragraph in text.splitlines() if paragraph.strip()]
    return [LessonContentBlock(type="rich_text", paragraphs=paragraphs or [text])]


def parse_lesson_blocks(raw_blocks: str | None, fallback_content: str | None = None) -> list[LessonContentBlock]:
    if raw_blocks:
        try:
            payload = json.loads(raw_blocks)
            if isinstance(payload, list):
                return [LessonContentBlock.model_validate(item) for item in payload]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return build_legacy_blocks(fallback_content)


def serialize_lesson_blocks(blocks: Iterable[LessonContentBlock]) -> str | None:
    prepared = [block.model_dump(exclude_none=True) for block in blocks]
    if not prepared:
        return None
    return json.dumps(prepared, ensure_ascii=False)


def summarize_lesson_content(content: str | None, blocks: Iterable[LessonContentBlock]) -> str:
    normalized_content = (content or "").strip()
    if normalized_content:
        return normalized_content

    fragments: list[str] = []
    for block in blocks:
        if block.paragraphs:
            fragments.extend(block.paragraphs)
        if block.text:
            fragments.append(block.text)
        if block.items:
            fragments.extend(block.items)
        if block.caption:
            fragments.append(block.caption)
        if len(" ".join(fragments)) >= 280:
            break

    summary = " ".join(fragment.strip() for fragment in fragments if fragment and fragment.strip()).strip()
    if len(summary) > 280:
        return summary[:277].rstrip() + "..."
    return summary


def build_lesson_read(lesson: Lesson) -> LessonRead:
    blocks = parse_lesson_blocks(lesson.content_blocks)
    return LessonRead(
        id=lesson.id,
        module_id=lesson.module_id,
        title=lesson.title,
        content=summarize_lesson_content(None, blocks),
        content_blocks=blocks,
        video_url=lesson.video_url,
        external_url=lesson.external_url,
        order=lesson.order,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )


def build_lesson_detail(
    lesson: Lesson,
    *,
    is_completed: bool,
    next_lesson_id: int | None,
    next_lesson_title: str | None,
) -> LessonDetailRead:
    base = build_lesson_read(lesson)
    return LessonDetailRead(
        **base.model_dump(),
        is_completed=is_completed,
        next_lesson_id=next_lesson_id,
        next_lesson_title=next_lesson_title,
    )


def build_intro_svg_data_url(title: str, subtitle: str, accent: str, secondary: str) -> str:
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" fill="none">
      <rect width="1200" height="720" rx="40" fill="#F8F5EF"/>
      <circle cx="1010" cy="154" r="124" fill="{accent}" fill-opacity="0.14"/>
      <circle cx="190" cy="570" r="168" fill="{secondary}" fill-opacity="0.14"/>
      <rect x="120" y="108" width="960" height="504" rx="34" fill="white"/>
      <rect x="170" y="176" width="360" height="24" rx="12" fill="{accent}" fill-opacity="0.24"/>
      <rect x="170" y="222" width="690" height="18" rx="9" fill="#D6D3D1"/>
      <rect x="170" y="258" width="620" height="18" rx="9" fill="#E7E5E4"/>
      <rect x="170" y="340" width="230" height="180" rx="26" fill="#FFF7ED"/>
      <rect x="430" y="340" width="230" height="180" rx="26" fill="#F0FDFA"/>
      <rect x="690" y="340" width="220" height="180" rx="26" fill="#F5F3FF"/>
      <rect x="940" y="340" width="90" height="180" rx="26" fill="{accent}" fill-opacity="0.18"/>
      <text x="170" y="158" fill="#1C1917" font-family="Segoe UI, Arial, sans-serif" font-size="46" font-weight="700">{title}</text>
      <text x="170" y="310" fill="#57534E" font-family="Segoe UI, Arial, sans-serif" font-size="24">{subtitle}</text>
    </svg>
    """.strip()
    return f"data:image/svg+xml;utf8,{quote(svg)}"
