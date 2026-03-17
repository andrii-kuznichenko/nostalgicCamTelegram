from dataclasses import dataclass

from app.models.analysis import ImageAnalysisResult
from app.models.prompting import PromptPackage

HUMAN_BASE_PROMPT = (
    "Edit the uploaded photo by applying a photorealistic vintage flash camera aesthetic while preserving the exact same "
    "person, exact same facial identity, exact same pose, exact same outfit, exact same hairstyle, exact same framing, and "
    "exact same scene composition. Keep the image realistic and natural. Preserve true facial structure, natural skin texture, "
    "realistic eyes, realistic hands, realistic body proportions, realistic clothing texture, and unchanged background structure. "
    "Do not beautify the subject. Do not make the face more symmetrical. Do not change body shape. Do not change expression. "
    "Do not change age, ethnicity, hairstyle, outfit, accessories, or environment. Only transform the photographic style and "
    "lighting. Apply a realistic direct on-camera flash effect, slightly overexposed highlights, natural flash shadows, a darker "
    "ambient background, subtle film grain, light digital sensor noise, gentle bloom, soft flash falloff, and an authentic "
    "early-2000s compact digital camera / disposable camera aesthetic. The final result must look like the original real photo "
    "with a believable vintage flash treatment applied, not like a regenerated portrait, not like digital art, not like CGI, "
    "and not like an obviously AI-generated image."
)

NO_FACE_BASE_PROMPT = (
    "Edit the uploaded photo by applying a photorealistic vintage flash camera aesthetic while preserving the exact same "
    "main subject, exact same composition, exact same camera angle, exact same framing, and exact same background structure. "
    "Keep the image realistic and natural. Preserve the true shape, proportions, surface texture, and placement of the visible "
    "subject and surrounding scene. Do not redesign the subject. Do not replace objects. Do not invent missing elements. "
    "Do not turn the image into digital art, CGI, or an obviously AI-generated result. Only transform the photographic style "
    "and lighting. Apply a realistic direct on-camera flash effect, slightly overexposed highlights, natural flash shadows, "
    "a darker ambient background, subtle film grain, light digital sensor noise, gentle bloom, soft flash falloff, and an "
    "authentic early-2000s compact digital camera / disposable camera aesthetic. The final result must look like the original "
    "real photo with a believable vintage flash treatment applied."
)

HUMAN_NEGATIVE_PROMPT = (
    "different person, identity loss, face reconstruction, changed facial features, beautified face, plastic skin, smooth skin, "
    "fake skin, stylized portrait, cartoon, painting, illustration, CGI, 3d render, unrealistic eyes, distorted hands, extra fingers, "
    "altered pose, changed outfit, changed hairstyle, changed background, altered camera angle, excessive glow, extreme grain, "
    "oversaturated colors, ai-generated face, opened eyes, reconstructed eyes, invented pupils, altered eyelids, sharpened facial details, "
    "invented eyelashes, invented eyebrows, reconstructed blurred face, artificial skin detail"
)

NO_FACE_NEGATIVE_PROMPT = (
    "redesigned subject, replaced object, invented details, extra animals, duplicate subject, altered proportions, altered shape, "
    "deformed anatomy, surreal textures, cartoon, painting, illustration, CGI, 3d render, fake fur, plastic texture, melted details, "
    "warped edges, altered background structure, changed camera angle, excessive glow, extreme grain, oversaturated colors, "
    "obviously ai-generated image"
)

MODE_PROMPTS = {
    "classic": "Use a soft realistic direct-flash look with mild highlight lift, subtle grain, light sensor noise, soft shadow contrast, and a clean natural candid result. Keep the effect understated and believable.",
    "vintage": "Use a realistic vintage direct-flash look inspired by early-2000s compact digital cameras and disposable cameras. Add slightly overexposed highlights, natural flash shadows, darker ambient tones, subtle film grain, light sensor noise, gentle bloom, and a nostalgic candid snapshot feeling.",
    "paparazzi": "Use a strong harsh direct-flash look with brighter frontal illumination, slightly blown highlights, stronger separation between subject and background, deeper ambient shadows, visible but controlled grain, and a gritty candid nightlife snapshot aesthetic.",
    "night_luxury": "Use a clean premium nighttime flash photography look with crisp direct flash, elegant contrast, slightly lifted highlights, controlled shadows, refined grain, subtle sensor texture, and a fashionable editorial candid aesthetic while staying fully photorealistic.",
    "disposable": "Use an authentic disposable camera aesthetic with direct flash, slightly uneven exposure, nostalgic color rendering, subtle grain, light sensor noise, mild softness, darker background falloff, and a believable casual snapshot feel.",
}

SAFETY_PROMPTS = {
    "face_visible": "Preserve the exact same visible facial identity and facial proportions. Keep facial features unchanged and natural.",
    "face_occluded": "Do not reconstruct hidden parts of the face. Do not invent or alter covered facial features. Preserve only the visible facial structure exactly as shown.",
    "face_unclear": "If facial details are soft, distant, motion-blurred, closed-eyed, or unclear in the source, preserve that ambiguity exactly. Do not sharpen the face, do not open the eyes, do not invent pupils, eyelashes, eyelids, teeth, skin detail, or missing facial features.",
    "mirror_selfie": "Preserve the exact same phone, exact same hand position, exact same reflection geometry, exact same mirror perspective, exact same camera angle, and exact same framing. Do not alter the reflection structure.",
    "phone_covers_face": "Do not modify the phone shape, hand anatomy, finger placement, or the visible part of the face. Do not regenerate hidden facial areas.",
    "multi_face": "Preserve every visible person exactly. Do not merge faces, do not alter identity, and do not shift facial proportions between subjects.",
    "no_face": "Preserve the exact same object and scene composition. Apply only the vintage flash treatment without redesigning the image.",
}

SCENE_PROMPTS = {
    "daylight": "Keep the daylight believable while adding subtle direct-flash character and nostalgic camera rendering.",
    "night": "Preserve the dark ambient mood and emphasize realistic flash separation between subject and background.",
    "indoor": "Keep the indoor lighting believable and natural while applying realistic direct-flash rendering.",
    "outdoor": "Maintain the street atmosphere and realistic depth while adding authentic flash-camera contrast and shadow behavior.",
}


@dataclass(slots=True)
class PromptBuilder:
    def select_mode(self, analysis: ImageAnalysisResult, user_mode: str | None = None) -> str:
        if analysis.subject_type == "scene":
            return "vintage" if user_mode is None else user_mode
        if analysis.subject_type in {"object", "person_no_face"}:
            return "disposable" if user_mode is None else user_mode

        if user_mode:
            if (
                analysis.is_mirror_selfie
                or analysis.face_occluded
                or analysis.phone_covers_face
                or analysis.complex_scene
            ):
                return "classic"
            return user_mode

        if analysis.is_mirror_selfie:
            return "classic"
        if analysis.face_occluded:
            return "classic"
        if analysis.phone_covers_face:
            return "classic"
        if analysis.complex_scene:
            return "classic"
        if analysis.face_count > 1:
            return "classic"
        if analysis.is_night and analysis.close_up_portrait:
            return "paparazzi"
        if analysis.is_night and analysis.strong_existing_flash:
            return "night_luxury"
        if analysis.subject_type in {"object", "person_no_face"}:
            return "disposable"
        if analysis.subject_type == "scene":
            return "vintage"
        if analysis.is_outdoor:
            return "vintage"
        return analysis.recommended_mode or "vintage"

    def build_flux_prompt(self, analysis: ImageAnalysisResult, user_mode: str | None = None) -> PromptPackage:
        selected_mode = self.select_mode(analysis, user_mode=user_mode)
        base_prompt = HUMAN_BASE_PROMPT
        base_prompt_name = "human_base_prompt"
        negative_prompt = HUMAN_NEGATIVE_PROMPT
        if analysis.subject_type in {"object", "scene", "person_no_face"}:
            base_prompt = NO_FACE_BASE_PROMPT
            base_prompt_name = "no_face_base_prompt"
            negative_prompt = NO_FACE_NEGATIVE_PROMPT

        blocks: list[tuple[str, str]] = [(base_prompt_name, base_prompt)]
        blocks.append((f"{selected_mode}_mode", MODE_PROMPTS[selected_mode]))

        if analysis.face_visible:
            blocks.append(("face_visible", SAFETY_PROMPTS["face_visible"]))
        if analysis.face_occluded:
            blocks.append(("face_occluded", SAFETY_PROMPTS["face_occluded"]))
        if analysis.face_unclear:
            blocks.append(("face_unclear", SAFETY_PROMPTS["face_unclear"]))
        if analysis.phone_covers_face:
            blocks.append(("phone_covers_face", SAFETY_PROMPTS["phone_covers_face"]))
        if analysis.requires_mirror_safe_prompt:
            blocks.append(("mirror_selfie", SAFETY_PROMPTS["mirror_selfie"]))
        if analysis.face_count > 1:
            blocks.append(("multi_face", SAFETY_PROMPTS["multi_face"]))
        if analysis.subject_type in {"object", "scene", "person_no_face"}:
            blocks.append(("no_face", SAFETY_PROMPTS["no_face"]))

        if analysis.is_night:
            blocks.append(("night", SCENE_PROMPTS["night"]))
        else:
            blocks.append(("daylight", SCENE_PROMPTS["daylight"]))

        if analysis.is_indoor:
            blocks.append(("indoor", SCENE_PROMPTS["indoor"]))
        if analysis.is_outdoor:
            blocks.append(("outdoor", SCENE_PROMPTS["outdoor"]))

        return PromptPackage(
            prompt=" ".join(text for _, text in blocks),
            negative_prompt=negative_prompt,
            selected_mode=selected_mode,
            applied_blocks=[name for name, _ in blocks],
        )
