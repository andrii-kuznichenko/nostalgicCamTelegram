from html import escape

from app.models.analysis import ImageAnalysisResult
from app.models.prompting import PromptPackage


def _bool_en(value: bool) -> str:
    return "yes" if value else "no"


def build_preview_messages(analysis: ImageAnalysisResult, package: PromptPackage) -> list[str]:
    summary = "\n".join(
        [
            f"<b>Detected subject type:</b> <code>{escape(analysis.subject_type)}</code>",
            f"<b>Subject confidence:</b> <code>{analysis.subject_confidence:.2f}</code>",
            "",
            f"<b>Detected photo type:</b> <code>{escape(analysis.photo_type)}</code>",
            "",
            "<b>Analysis:</b>",
            f"- Face detected: {_bool_en(analysis.has_face)}",
            f"- Face count: {analysis.face_count}",
            f"- Face visible: {_bool_en(analysis.face_visible)}",
            f"- Face partially occluded: {_bool_en(analysis.face_occluded)}",
            f"- Face unclear: {_bool_en(analysis.face_unclear)}",
            f"- Eyes closed or hidden: {_bool_en(analysis.eyes_closed_or_hidden)}",
            f"- Intimate close pose: {_bool_en(analysis.intimate_close_pose)}",
            f"- Phone covers face: {_bool_en(analysis.phone_covers_face)}",
            f"- Mirror selfie: {_bool_en(analysis.is_mirror_selfie)}",
            f"- Selfie: {_bool_en(analysis.is_selfie)}",
            f"- Night photo: {_bool_en(analysis.is_night)}",
            f"- Indoor: {_bool_en(analysis.is_indoor)}",
            f"- Outdoor: {_bool_en(analysis.is_outdoor)}",
            f"- Close-up portrait: {_bool_en(analysis.close_up_portrait)}",
            f"- Complex scene: {_bool_en(analysis.complex_scene)}",
            f"- Strong existing flash: {_bool_en(analysis.strong_existing_flash)}",
            "",
            "<b>Selected mode:</b>",
            f"<code>{escape(package.selected_mode)}</code>",
            "",
            "<b>Added prompt blocks:</b>",
            *[f"- <code>{escape(block)}</code>" for block in package.applied_blocks],
            "",
            "<b>Debug notes:</b>",
            *[f"- <code>{escape(note)}</code>" for note in analysis.debug_notes],
            "",
            "<b>Decision trace:</b>",
            *[f"- {escape(step)}" for step in analysis.decision_trace],
        ]
    )

    negative = "\n".join(
        [
            "<b>Negative prompt:</b>",
            f"<code>{escape(package.negative_prompt)}</code>",
        ]
    )

    prompt = "\n".join(
        [
            "<b>Final prompt:</b>",
            f"<code>{escape(package.prompt)}</code>",
        ]
    )

    return [summary, negative, prompt]
