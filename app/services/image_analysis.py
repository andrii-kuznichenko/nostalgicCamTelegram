import logging
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image, ImageStat

from app.models.analysis import ImageAnalysisResult

logger = logging.getLogger(__name__)

try:
    import cv2  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    cv2 = None
    np = None


class ImageAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, image_path: str | Path) -> ImageAnalysisResult:
        raise NotImplementedError


class HeuristicImageAnalyzer(ImageAnalyzer):
    def __init__(self) -> None:
        self._frontal_face = None
        self._profile_face = None
        self._eye_cascade = None
        self._hog = None

        if cv2 is not None:
            cascades_dir = Path(cv2.data.haarcascades)
            self._frontal_face = cv2.CascadeClassifier(str(cascades_dir / "haarcascade_frontalface_default.xml"))
            self._profile_face = cv2.CascadeClassifier(str(cascades_dir / "haarcascade_profileface.xml"))
            self._eye_cascade = cv2.CascadeClassifier(str(cascades_dir / "haarcascade_eye.xml"))
            self._hog = cv2.HOGDescriptor()
            self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    async def analyze(self, image_path: str | Path) -> ImageAnalysisResult:
        path = Path(image_path)
        with Image.open(path) as image:
            rgb_image = image.convert("RGB")
            grayscale = rgb_image.convert("L")
            hsv_image = rgb_image.convert("HSV")

            width, height = rgb_image.size
            aspect_ratio = width / max(height, 1)
            overall_brightness = ImageStat.Stat(grayscale).mean[0]
            overall_contrast = ImageStat.Stat(grayscale).stddev[0]
            saturation = ImageStat.Stat(hsv_image).mean[1]

            top_half = grayscale.crop((0, 0, width, max(1, int(height * 0.5))))
            lower_half = grayscale.crop((0, int(height * 0.45), width, height))
            center_crop = rgb_image.crop(
                (
                    int(width * 0.2),
                    int(height * 0.18),
                    int(width * 0.8),
                    int(height * 0.82),
                )
            )
            face_zone = rgb_image.crop(
                (
                    int(width * 0.18),
                    0,
                    int(width * 0.82),
                    int(height * 0.56),
                )
            )

            top_half_brightness = ImageStat.Stat(top_half).mean[0]
            lower_half_brightness = ImageStat.Stat(lower_half).mean[0]
            overall_skin_ratio = self._skin_ratio(rgb_image)
            center_skin_ratio = self._skin_ratio(center_crop)
            face_zone_skin_ratio = self._skin_ratio(face_zone)

        face_boxes, face_trace = self._detect_faces(path)
        face_count = len(face_boxes)
        has_face = face_count > 0

        largest_face_ratio = 0.0
        top_face_centered = False
        eye_hits = 0
        if face_boxes:
            largest_face_ratio = max((w * h) / max(width * height, 1) for (_, _, w, h) in face_boxes)
            top_face_centered = any(
                (x + w / 2) > width * 0.25
                and (x + w / 2) < width * 0.75
                and (y + h / 2) < height * 0.48
                for (x, y, w, h) in face_boxes
            )
            eye_hits = self._count_eyes(path, face_boxes)

        person_boxes, person_trace = self._detect_people(path)
        person_count = len(person_boxes)
        has_person = person_count > 0 or center_skin_ratio > 0.12 or face_zone_skin_ratio > 0.10

        is_portrait_frame = height >= width
        is_squareish = 0.82 <= aspect_ratio <= 1.18
        close_up_portrait = has_face and largest_face_ratio >= 0.10

        if not has_face and self._frontal_face is None:
            has_face = (
                is_portrait_frame
                and center_skin_ratio > 0.22
                and face_zone_skin_ratio > 0.18
                and top_half_brightness > 95
                and overall_contrast > 22
            )
            face_count = 1 if has_face else 0
            close_up_portrait = has_face and is_squareish

        phone_like_region_score = self._estimate_phone_presence(path)
        is_selfie = has_face and face_count == 1 and (close_up_portrait or (is_squareish and top_face_centered))
        is_indoor = top_half_brightness < 155 or saturation < 92
        is_outdoor = not is_indoor and top_half_brightness >= 155

        face_occluded = (
            has_person
            and not close_up_portrait
            and phone_like_region_score >= 0.50
            and face_zone_skin_ratio > 0.10
        )
        phone_covers_face = face_occluded and (has_face or has_person)

        is_mirror_selfie = (
            is_portrait_frame
            and is_indoor
            and aspect_ratio <= 0.80
            and phone_like_region_score >= 0.50
            and (has_face or has_person)
            and (face_occluded or eye_hits <= 1)
        )
        if is_mirror_selfie:
            is_selfie = True

        face_visible = has_face and not face_occluded
        if is_mirror_selfie and has_face:
            face_visible = True

        is_night = overall_brightness < 80 and top_half_brightness < 95
        strong_existing_flash = (
            has_face
            and top_half_brightness > 145
            and overall_contrast > 55
            and lower_half_brightness + 20 < top_half_brightness
        )

        subject_type, subject_confidence, subject_trace = self._detect_subject_type(
            has_face=has_face,
            face_count=face_count,
            has_person=has_person,
            person_count=person_count,
            is_portrait_frame=is_portrait_frame,
            aspect_ratio=aspect_ratio,
            overall_contrast=overall_contrast,
            center_skin_ratio=center_skin_ratio,
            face_zone_skin_ratio=face_zone_skin_ratio,
            phone_like_region_score=phone_like_region_score,
            is_mirror_selfie=is_mirror_selfie,
        )

        complex_scene = (
            subject_type == "scene"
            or face_count > 1
            or person_count > 1
            or overall_contrast > 78
            or aspect_ratio > 1.35
        )

        photo_type = self._detect_photo_type(
            subject_type=subject_type,
            has_face=has_face,
            face_count=face_count,
            is_mirror_selfie=is_mirror_selfie,
            is_selfie=is_selfie,
            is_night=is_night,
            is_outdoor=is_outdoor,
            close_up_portrait=close_up_portrait,
            strong_existing_flash=strong_existing_flash,
            phone_covers_face=phone_covers_face,
        )

        recommended_mode, mode_trace = self._recommend_mode(
            subject_type=subject_type,
            photo_type=photo_type,
            is_mirror_selfie=is_mirror_selfie,
            face_occluded=face_occluded,
            phone_covers_face=phone_covers_face,
            complex_scene=complex_scene,
            is_night=is_night,
            close_up_portrait=close_up_portrait,
            strong_existing_flash=strong_existing_flash,
            is_outdoor=is_outdoor,
            face_count=face_count,
        )

        requires_safe_prompt = (
            face_occluded
            or phone_covers_face
            or face_count > 1
            or complex_scene
            or (subject_type == "face" and not face_visible)
        )
        requires_mirror_safe_prompt = is_mirror_selfie

        decision_trace = [
            *face_trace,
            *person_trace,
            *subject_trace,
            *mode_trace,
        ]
        debug_notes = [
            f"detector={'opencv-multistage' if self._frontal_face is not None else 'heuristic'}",
            f"subject_type={subject_type}",
            f"subject_confidence={subject_confidence:.2f}",
            f"face_count={face_count}",
            f"person_count={person_count}",
            f"eye_hits={eye_hits}",
            f"largest_face_ratio={largest_face_ratio:.3f}",
            f"phone_like_region_score={phone_like_region_score:.2f}",
            f"overall_brightness={overall_brightness:.1f}",
            f"top_half_brightness={top_half_brightness:.1f}",
            f"lower_half_brightness={lower_half_brightness:.1f}",
            f"overall_contrast={overall_contrast:.1f}",
            f"overall_skin_ratio={overall_skin_ratio:.3f}",
            f"center_skin_ratio={center_skin_ratio:.3f}",
            f"face_zone_skin_ratio={face_zone_skin_ratio:.3f}",
            f"aspect_ratio={aspect_ratio:.2f}",
        ]

        logger.info(
            "Image analyzed: path=%s subject_type=%s photo_type=%s mode=%s trace=%s",
            path,
            subject_type,
            photo_type,
            recommended_mode,
            " | ".join(decision_trace),
        )

        return ImageAnalysisResult(
            subject_type=subject_type,
            subject_confidence=subject_confidence,
            has_face=has_face,
            face_count=face_count,
            face_visible=face_visible,
            face_occluded=face_occluded,
            phone_covers_face=phone_covers_face,
            is_mirror_selfie=is_mirror_selfie,
            is_selfie=is_selfie,
            is_night=is_night,
            is_indoor=is_indoor,
            is_outdoor=is_outdoor,
            close_up_portrait=close_up_portrait,
            complex_scene=complex_scene,
            strong_existing_flash=strong_existing_flash,
            recommended_mode=recommended_mode,
            requires_safe_prompt=requires_safe_prompt,
            requires_mirror_safe_prompt=requires_mirror_safe_prompt,
            photo_type=photo_type,
            decision_trace=decision_trace,
            debug_notes=debug_notes,
        )

    def _detect_faces(self, path: Path) -> tuple[list[tuple[int, int, int, int]], list[str]]:
        if self._frontal_face is None or cv2 is None:
            return [], ["face detector unavailable"]

        image = cv2.imread(str(path))
        if image is None:
            return [], ["image load failed for face detector"]

        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = grayscale.shape
        faces: list[tuple[int, int, int, int]] = []
        trace: list[str] = []

        frontal = self._frontal_face.detectMultiScale(grayscale, scaleFactor=1.1, minNeighbors=5, minSize=(42, 42))
        if len(frontal) > 0:
            trace.append(f"frontal face detector found {len(frontal)} face(s)")
            faces.extend((int(x), int(y), int(w), int(h)) for (x, y, w, h) in frontal)

        flipped = cv2.flip(grayscale, 1)
        frontal_flipped = self._frontal_face.detectMultiScale(flipped, scaleFactor=1.1, minNeighbors=5, minSize=(42, 42))
        if len(frontal_flipped) > 0:
            trace.append(f"flipped frontal detector found {len(frontal_flipped)} face(s)")
            for (x, y, w, h) in frontal_flipped:
                faces.append((int(width - x - w), int(y), int(w), int(h)))

        if self._profile_face is not None:
            profile = self._profile_face.detectMultiScale(grayscale, scaleFactor=1.1, minNeighbors=4, minSize=(42, 42))
            if len(profile) > 0:
                trace.append(f"profile detector found {len(profile)} face(s)")
                faces.extend((int(x), int(y), int(w), int(h)) for (x, y, w, h) in profile)

            profile_flipped = self._profile_face.detectMultiScale(flipped, scaleFactor=1.1, minNeighbors=4, minSize=(42, 42))
            if len(profile_flipped) > 0:
                trace.append(f"flipped profile detector found {len(profile_flipped)} face(s)")
                for (x, y, w, h) in profile_flipped:
                    faces.append((int(width - x - w), int(y), int(w), int(h)))

        deduped = self._dedupe_boxes(faces)
        if not trace:
            trace.append("no face found by frontal/profile cascades")
        return deduped, trace

    def _count_eyes(self, path: Path, face_boxes: list[tuple[int, int, int, int]]) -> int:
        if self._eye_cascade is None or cv2 is None:
            return 0

        image = cv2.imread(str(path))
        if image is None:
            return 0
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        eye_hits = 0
        for (x, y, w, h) in face_boxes:
            roi = grayscale[y:y + h, x:x + w]
            eyes = self._eye_cascade.detectMultiScale(roi, scaleFactor=1.05, minNeighbors=3, minSize=(12, 12))
            eye_hits += len(eyes)
        return eye_hits

    def _detect_people(self, path: Path) -> tuple[list[tuple[int, int, int, int]], list[str]]:
        if self._hog is None or cv2 is None:
            return [], ["people detector unavailable"]

        image = cv2.imread(str(path))
        if image is None:
            return [], ["image load failed for people detector"]

        max_width = 512
        scale = 1.0
        if image.shape[1] > max_width:
            scale = max_width / image.shape[1]
            image = cv2.resize(image, None, fx=scale, fy=scale)

        rects, _weights = self._hog.detectMultiScale(image, winStride=(8, 8), padding=(8, 8), scale=1.05)
        people = []
        for (x, y, w, h) in rects:
            people.append((int(x / scale), int(y / scale), int(w / scale), int(h / scale)))
        if people:
            return self._dedupe_boxes(people), [f"people detector found {len(people)} person-like region(s)"]
        return [], ["people detector found no confident person regions"]

    def _estimate_phone_presence(self, path: Path) -> float:
        if cv2 is None or np is None:
            return 0.0

        image = cv2.imread(str(path))
        if image is None:
            return 0.0
        height, width = image.shape[:2]
        roi = image[int(height * 0.18):int(height * 0.82), int(width * 0.35):int(width * 0.95)]
        if roi.size == 0:
            return 0.0

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 180)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_score = 0.0
        roi_area = roi.shape[0] * roi.shape[1]
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < roi_area * 0.02 or area > roi_area * 0.40:
                continue
            ratio = w / max(h, 1)
            rect_like = 0.0
            if 0.45 <= ratio <= 0.85:
                rect_like = 1.0
            elif 0.35 <= ratio <= 1.0:
                rect_like = 0.6
            if rect_like == 0.0:
                continue

            crop = roi[y:y + h, x:x + w]
            mean_color = crop.mean(axis=(0, 1))
            darkness = max(0.0, 1.0 - (float(mean_color.mean()) / 255.0))
            edge_density = float((edges[y:y + h, x:x + w] > 0).mean())

            score = min(1.0, rect_like * 0.45 + darkness * 0.30 + min(1.0, edge_density * 4.0) * 0.25)
            best_score = max(best_score, score)

        return best_score

    def _skin_ratio(self, image: Image.Image) -> float:
        sample = image.resize((64, 64)).convert("RGB")
        skin_pixels = 0
        total = 64 * 64
        for red, green, blue in sample.getdata():
            max_channel = max(red, green, blue)
            min_channel = min(red, green, blue)
            is_skin = (
                red > 95
                and green > 40
                and blue > 20
                and (max_channel - min_channel) > 15
                and abs(red - green) > 15
                and red > green
                and red > blue
            )
            if is_skin:
                skin_pixels += 1
        return skin_pixels / total

    def _detect_subject_type(
        self,
        *,
        has_face: bool,
        face_count: int,
        has_person: bool,
        person_count: int,
        is_portrait_frame: bool,
        aspect_ratio: float,
        overall_contrast: float,
        center_skin_ratio: float,
        face_zone_skin_ratio: float,
        phone_like_region_score: float,
        is_mirror_selfie: bool,
    ) -> tuple[str, float, list[str]]:
        trace: list[str] = []

        if has_face:
            trace.append("subject_type=face because a face detector found at least one face")
            confidence = min(0.98, 0.72 + 0.08 * face_count)
            if is_mirror_selfie:
                trace.append("mirror selfie heuristic is active but face remains primary subject")
            return "face", confidence, trace

        if has_person:
            confidence = 0.60
            if phone_like_region_score >= 0.50 and is_portrait_frame:
                trace.append("subject_type=person_no_face because person-like frame and phone-like region suggest occluded selfie/mirror shot")
                confidence = 0.82
            elif person_count > 0:
                trace.append("subject_type=person_no_face because people detector found a person-like region but no face detector fired")
                confidence = 0.76
            elif face_zone_skin_ratio > 0.10 or center_skin_ratio > 0.12:
                trace.append("subject_type=person_no_face because body/skin cues are present without a confirmed face")
                confidence = 0.68
            return "person_no_face", confidence, trace

        if aspect_ratio > 1.35 or overall_contrast > 76:
            trace.append("subject_type=scene because frame geometry/contrast suggests a wider scene")
            return "scene", 0.74, trace

        trace.append("subject_type=object because no face or person signals were strong enough")
        return "object", 0.72, trace

    def _detect_photo_type(
        self,
        *,
        subject_type: str,
        has_face: bool,
        face_count: int,
        is_mirror_selfie: bool,
        is_selfie: bool,
        is_night: bool,
        is_outdoor: bool,
        close_up_portrait: bool,
        strong_existing_flash: bool,
        phone_covers_face: bool,
    ) -> str:
        if subject_type == "object":
            return "object_photo"
        if subject_type == "scene":
            return "no_face_scene"
        if subject_type == "person_no_face":
            if is_mirror_selfie or phone_covers_face:
                return "mirror_selfie"
            return "person_no_face"
        if is_mirror_selfie:
            return "mirror_selfie"
        if face_count > 1:
            return "group_photo"
        if is_night and close_up_portrait:
            return "night_portrait"
        if close_up_portrait and has_face:
            return "close_up_portrait"
        if is_selfie:
            return "selfie"
        if strong_existing_flash:
            return "indoor_flash_like"
        if is_outdoor:
            return "casual_outdoor"
        return "portrait"

    def _recommend_mode(
        self,
        *,
        subject_type: str,
        photo_type: str,
        is_mirror_selfie: bool,
        face_occluded: bool,
        phone_covers_face: bool,
        complex_scene: bool,
        is_night: bool,
        close_up_portrait: bool,
        strong_existing_flash: bool,
        is_outdoor: bool,
        face_count: int,
    ) -> tuple[str, list[str]]:
        trace: list[str] = []
        if subject_type == "scene":
            trace.append("selected vintage because subject_type=scene")
            return "vintage", trace
        if subject_type == "object":
            trace.append("selected disposable because subject_type=object")
            return "disposable", trace
        if subject_type == "person_no_face":
            if is_mirror_selfie or face_occluded or phone_covers_face:
                trace.append("selected classic because subject_type=person_no_face with occlusion/mirror risk")
                return "classic", trace
            trace.append("selected disposable because subject_type=person_no_face without a safe visible face")
            return "disposable", trace
        if is_mirror_selfie or face_occluded or phone_covers_face or complex_scene:
            trace.append("selected classic because mirror/occlusion/complex-scene safety rule fired")
            return "classic", trace
        if face_count > 1:
            trace.append("selected classic because multiple faces were detected")
            return "classic", trace
        if is_night and close_up_portrait:
            trace.append("selected paparazzi because this is a close-up night portrait")
            return "paparazzi", trace
        if is_night and strong_existing_flash:
            trace.append("selected night_luxury because this looks like a clean nighttime flash image")
            return "night_luxury", trace
        if photo_type == "indoor_flash_like":
            trace.append("selected classic because the source already has flash-like characteristics")
            return "classic", trace
        if is_outdoor:
            trace.append("selected vintage because this is an outdoor casual shot")
            return "vintage", trace
        trace.append("selected vintage as the default safe mode for a single-face non-risky image")
        return "vintage", trace

    def _dedupe_boxes(self, boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
        deduped: list[tuple[int, int, int, int]] = []
        for box in sorted(boxes, key=lambda item: item[2] * item[3], reverse=True):
            if all(self._iou(box, existing) < 0.35 for existing in deduped):
                deduped.append(box)
        return deduped

    def _iou(self, a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        x1 = max(ax, bx)
        y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw)
        y2 = min(ay + ah, by + bh)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        intersection = (x2 - x1) * (y2 - y1)
        union = aw * ah + bw * bh - intersection
        return intersection / max(union, 1)
