import cv2
import numpy as np

from config import (
    YUNET_MODEL,
    SFACE_MODEL,
    FACE_CONFIDENCE,
    FACE_MATCH_THRESHOLD
)


# =====================================================
# LOAD MODELS
# =====================================================

def load_models():
    detector = cv2.FaceDetectorYN.create(
        str(YUNET_MODEL),
        "",
        (320, 320),
        FACE_CONFIDENCE,
        0.3,
        5000
    )

    recognizer = cv2.FaceRecognizerSF.create(
        str(SFACE_MODEL),
        ""
    )

    return detector, recognizer


# =====================================================
# DETECT FACE
# =====================================================

def detect_faces(detector, image):
    h, w = image.shape[:2]

    detector.setInputSize((w, h))

    _, faces = detector.detect(image)

    if faces is None:
        return []

    return faces


# =====================================================
# GET EMBEDDING
# =====================================================

def get_embedding(recognizer, image, face):
    aligned = recognizer.alignCrop(
        image,
        face
    )

    feature = recognizer.feature(
        aligned
    )

    return feature


# =====================================================
# COMPARE EMBEDDINGS
# =====================================================

def compare_embeddings(
    recognizer,
    embedding1,
    embedding2
):
    score = recognizer.match(
        embedding1,
        embedding2,
        cv2.FaceRecognizerSF_FR_COSINE
    )

    return float(score)


# =====================================================
# PREPARE REGISTERED PEOPLE
# =====================================================

def prepare_people(people):
    """
    Convert database BYTEA embeddings into numpy arrays
    only once.

    This prevents np.frombuffer() from running on every
    webcam frame.
    """

    prepared = []

    for person in people:

        person_id = person[1]
        name = person[2]
        department = person[3]
        stored_bytes = person[4]

        if stored_bytes is None:
            continue

        try:

            stored_embedding = np.frombuffer(
                stored_bytes,
                dtype=np.float32
            ).reshape(1, -1)

            prepared.append({
                "person_id": person_id,
                "name": name,
                "department": department,
                "embedding": stored_embedding
            })

        except Exception:
            continue

    return prepared


# =====================================================
# FIND BEST MATCH
# =====================================================

def find_best_match(
    recognizer,
    query_embedding,
    people
):

    best_person = None
    best_score = -1.0

    for person in people:

        # =================================================
        # PREPARED FORMAT
        # Used by optimized webcam.py
        # =================================================

        if isinstance(person, dict):

            person_id = person["person_id"]
            name = person["name"]
            department = person["department"]
            stored_embedding = person["embedding"]

        # =================================================
        # ORIGINAL DATABASE TUPLE FORMAT
        # Used by existing app.py
        # =================================================

        else:

            person_id = person[1]
            name = person[2]
            department = person[3]
            stored_bytes = person[4]

            if stored_bytes is None:
                continue

            try:

                stored_embedding = np.frombuffer(
                    stored_bytes,
                    dtype=np.float32
                ).reshape(1, -1)

            except Exception:

                continue

        # =================================================
        # COMPARE
        # =================================================

        score = compare_embeddings(
            recognizer,
            query_embedding,
            stored_embedding
        )

        # =================================================
        # BEST SCORE
        # =================================================

        if score > best_score:

            best_score = score

            best_person = {
                "person_id": person_id,
                "name": name,
                "department": department,
                "score": score
            }

    # =====================================================
    # THRESHOLD
    # =====================================================

    if (
        best_person is not None
        and best_score >= FACE_MATCH_THRESHOLD
    ):

        return best_person

    return None


# =====================================================
# FIND REGISTERED PERSON
# =====================================================

def find_registered_person(
    recognizer,
    query_embedding,
    people
):

    return find_best_match(
        recognizer,
        query_embedding,
        people
    )