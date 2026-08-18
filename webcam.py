import av
import cv2
import threading
from streamlit_webrtc import VideoProcessorBase
from face_engine import (
    detect_faces,
    get_embedding,
    find_registered_person
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
        return av.VideoFrame.from_ndarray(img,format="bgr24")


# =====================================================
# ATTENDANCE CAMERA
# =====================================================

class AttendanceProcessor(VideoProcessorBase):
    def __init__(self,detector,recognizer):
        self.detector = detector
        self.recognizer = recognizer

        # Frame counter
        self.frame_count = 0

        # =============================================
        # IMPORTANT STATE VARIABLES
        # =============================================

        # Currently detected person
        self.current_person_id = None

        # True means person camera se hat chuka hai
        self.person_left_camera = True

        # Last status shown on face
        self.current_label = None

    # =================================================
    # LIVE VIDEO PROCESSING
    # =================================================

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        self.frame_count += 1

        # =============================================
        # PROCESS EVERY 10TH FRAME
        # =============================================

        if self.frame_count % 10 != 0:
            # Same status ko screen par maintain karo
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
            return av.VideoFrame.from_ndarray(img,format="bgr24")

        # =============================================
        # GET REGISTERED PEOPLE
        # =============================================

        people = get_people()
        if not people:
            self.current_label = ("NO REGISTERED PERSON")
            cv2.putText(
                img,
                self.current_label,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )
            return av.VideoFrame.from_ndarray(img,format="bgr24")

        # =============================================
        # FACE DETECTION
        # =============================================

        faces = detect_faces(self.detector,img)

        # =============================================
        # NO FACE
        # =============================================

        if len(faces) == 0:
            # Person camera se hat gaya
            self.current_person_id = None
            self.person_left_camera = True
            self.current_label = None
            return av.VideoFrame.from_ndarray(img,format="bgr24")
        
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
                people
            )

            # =========================================
            # UNKNOWN PERSON
            # =========================================

            if person is None:
                self.current_label = "UNKNOWN"
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

            # =========================================
            # PERSON FIRST TIME / RETURNING
            # =========================================

            if (
                self.current_person_id != person_id
                or self.person_left_camera
            ):

                # -------------------------------------
                # MARK ATTENDANCE
                # -------------------------------------

                result = mark_attendance(person_id,name)

                # -------------------------------------
                # FIRST ATTENDANCE TODAY
                # -------------------------------------

                if result == "NEW":
                    self.current_label = (
                        f"{name} - "
                        f"SUCCESSFULLY PRESENT"
                    )

                # -------------------------------------
                # ALREADY PRESENT TODAY
                # -------------------------------------

                else:
                    self.current_label = (
                        f"{name} - "
                        f"ALREADY PRESENT TODAY"
                    )

                # -------------------------------------
                # UPDATE STATE
                # -------------------------------------

                self.current_person_id = person_id
                self.person_left_camera = False

            # =========================================
            # SAME PERSON STILL IN CAMERA
            # =========================================

            else:
                pass

            # =========================================
            # DRAW LABEL ON FACE
            # =========================================

            img = draw_face_box(
                img,
                face,
                self.current_label,
                True
            )
        return av.VideoFrame.from_ndarray(img,format="bgr24")