import av
import cv2
import threading
import time
from streamlit_webrtc import VideoProcessorBase
from face_engine import (
    detect_faces,
    get_embedding,
    find_registered_person,
    prepare_people
)

from database import (
    get_people,
    mark_attendance
)

from utils import draw_face_box


# =====================================================
# GLOBAL FRAME FOR REGISTRATION
# =====================================================

latest_frame = None
frame_lock = threading.Lock()


# =====================================================
# REGISTRATION CAMERA
# =====================================================

class RegistrationProcessor(VideoProcessorBase):

    def recv(self, frame):

        global latest_frame

        img = frame.to_ndarray(
            format="bgr24"
        )

        with frame_lock:
            latest_frame = img.copy()

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )


# =====================================================
# ATTENDANCE CAMERA
# =====================================================

class AttendanceProcessor(VideoProcessorBase):

    def __init__(self, detector, recognizer):

        self.detector = detector
        self.recognizer = recognizer

        # =============================================
        # FRAME CONTROL
        # =============================================

        self.frame_count = 0

        # Process recognition every N frames
        self.process_every_n_frames = 5

        # =============================================
        # REGISTERED PEOPLE
        # =============================================

        self.people = []
        self.people_loaded = False

        # =============================================
        # CURRENT PERSON STATE
        # =============================================

        self.current_person_id = None

        self.person_left_camera = True

        self.current_label = None

        self.current_face = None

        # =============================================
        # LAST RECOGNITION
        # =============================================

        self.last_person = None

        # =============================================
        # DATABASE REFRESH
        # =============================================

        self.last_people_refresh = 0

        # Refresh registered people every 60 seconds
        self.people_refresh_interval = 60

        # =============================================
        # ATTENDANCE CONTROL
        # =============================================

        self.last_attendance_time = 0

        # Minimum time between attendance DB operations
        self.attendance_cooldown = 3

    # =================================================
    # LOAD PEOPLE
    # =================================================

    def load_registered_people(self):

        try:

            people = get_people()

            if not people:

                self.people = []
                self.people_loaded = True
                return

            # Convert BYTEA embeddings to numpy
            # ONLY ONCE
            self.people = prepare_people(
                people
            )

            self.people_loaded = True

            self.last_people_refresh = time.time()

        except Exception as e:

            print(
                "Failed to load registered people:",
                e
            )

            self.people = []

    # =================================================
    # REFRESH PEOPLE OCCASIONALLY
    # =================================================

    def refresh_people_if_needed(self):

        current_time = time.time()

        # First load
        if not self.people_loaded:

            self.load_registered_people()

            return

        # Refresh only after 60 seconds
        if (
            current_time - self.last_people_refresh
            >= self.people_refresh_interval
        ):

            self.load_registered_people()

    # =================================================
    # DRAW CURRENT STATUS
    # =================================================

    def draw_status(self, img):

        if self.current_label:

            cv2.putText(
                img,
                self.current_label,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        return img

    # =================================================
    # LIVE VIDEO PROCESSING
    # =================================================

    def recv(self, frame):

        img = frame.to_ndarray(
            format="bgr24"
        )

        self.frame_count += 1

        # =============================================
        # LOAD REGISTERED PEOPLE
        # =============================================

        # This does NOT hit Supabase every frame.
        self.refresh_people_if_needed()

        # =============================================
        # NO REGISTERED PEOPLE
        # =============================================

        if not self.people:

            self.current_label = (
                "NO REGISTERED PERSON"
            )

            img = self.draw_status(img)

            return av.VideoFrame.from_ndarray(
                img,
                format="bgr24"
            )

        # =============================================
        # FRAME SKIPPING
        # =============================================

        if (
            self.frame_count
            % self.process_every_n_frames != 0
        ):

            # Keep last known face box/label
            if (
                self.current_face is not None
                and self.current_label is not None
            ):

                img = draw_face_box(
                    img,
                    self.current_face,
                    self.current_label,
                    self.last_person is not None
                )

            else:

                img = self.draw_status(img)

            return av.VideoFrame.from_ndarray(
                img,
                format="bgr24"
            )

        # =============================================
        # FACE DETECTION
        # =============================================

        faces = detect_faces(
            self.detector,
            img
        )

        # =============================================
        # NO FACE
        # =============================================

        if len(faces) == 0:

            self.current_person_id = None

            self.person_left_camera = True

            self.current_label = None

            self.current_face = None

            self.last_person = None

            return av.VideoFrame.from_ndarray(
                img,
                format="bgr24"
            )

        # =============================================
        # FACE FOUND
        # =============================================

        for face in faces:

            # -----------------------------------------
            # CREATE FACE EMBEDDING
            # -----------------------------------------

            embedding = get_embedding(
                self.recognizer,
                img,
                face
            )

            # -----------------------------------------
            # FIND REGISTERED PERSON
            # -----------------------------------------

            person = find_registered_person(
                self.recognizer,
                embedding,
                self.people
            )

            # =========================================
            # UNKNOWN PERSON
            # =========================================

            if person is None:

                self.current_label = "UNKNOWN"

                self.current_face = face

                self.last_person = None

                img = draw_face_box(
                    img,
                    face,
                    "UNKNOWN",
                    False
                )

                continue

            # =========================================
            # REGISTERED PERSON
            # =========================================

            person_id = person["person_id"]

            name = person["name"]

            # Save latest recognition
            self.last_person = person

            self.current_face = face

            # =========================================
            # PERSON FIRST TIME / RETURNING
            # =========================================

            if (
                self.current_person_id != person_id
                or self.person_left_camera
            ):

                current_time = time.time()

                # -------------------------------------
                # DATABASE COOLDOWN
                # -------------------------------------

                if (
                    current_time
                    - self.last_attendance_time
                    >= self.attendance_cooldown
                ):

                    try:

                        result = mark_attendance(
                            person_id,
                            name
                        )

                        self.last_attendance_time = (
                            current_time
                        )

                        # ---------------------------------
                        # FIRST ATTENDANCE TODAY
                        # ---------------------------------

                        if result == "NEW":

                            self.current_label = (
                                f"{name} - "
                                f"SUCCESSFULLY PRESENT"
                            )

                        # ---------------------------------
                        # ALREADY PRESENT
                        # ---------------------------------

                        else:

                            self.current_label = (
                                f"{name} - "
                                f"ALREADY PRESENT TODAY"
                            )

                    except Exception as e:

                        print(
                            "Attendance error:",
                            e
                        )

                        self.current_label = (
                            f"{name} - DATABASE ERROR"
                        )

                else:

                    self.current_label = (
                        f"{name} - "
                        f"PROCESSING..."
                    )

                # -------------------------------------
                # UPDATE STATE
                # -------------------------------------

                self.current_person_id = (
                    person_id
                )

                self.person_left_camera = False

            # =========================================
            # SAME PERSON STILL IN CAMERA
            # =========================================

            else:

                # Don't touch database
                # Don't mark attendance again

                if not self.current_label:

                    self.current_label = name

            # =========================================
            # DRAW FACE BOX
            # =========================================

            img = draw_face_box(
                img,
                face,
                self.current_label,
                True
            )

        # =============================================
        # RETURN FRAME
        # =============================================

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )