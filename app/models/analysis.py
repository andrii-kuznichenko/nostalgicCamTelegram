from dataclasses import dataclass, field


@dataclass(slots=True)
class ImageAnalysisResult:
    subject_type: str
    subject_confidence: float
    has_face: bool
    face_count: int
    face_visible: bool
    face_occluded: bool
    phone_covers_face: bool
    is_mirror_selfie: bool
    is_selfie: bool
    is_night: bool
    is_indoor: bool
    is_outdoor: bool
    close_up_portrait: bool
    complex_scene: bool
    strong_existing_flash: bool
    recommended_mode: str
    requires_safe_prompt: bool
    requires_mirror_safe_prompt: bool
    photo_type: str
    decision_trace: list[str] = field(default_factory=list)
    debug_notes: list[str] = field(default_factory=list)
