
import streamlit as st
import cv2
import numpy as np
import pandas as pd
import tempfile
import os
import math

st.set_page_config(page_title="Instant Speed Tracker", layout="wide")

st.title("محاسبه تندی لحظه‌ای از روی ویدئو")
st.write("ویدئو را آپلود کن، فاصله‌ی واقعی را بده، سپس نقاط مرجع و کادر جسم را مشخص کن.")

with st.expander("راهنمای استفاده", expanded=True):
    st.markdown("""
1. ویدئو را آپلود کن.
2. فاصله‌ی واقعی بین دو نقطه‌ی مرجع را به متر وارد کن.
3. مختصات دو نقطه‌ی مرجع را از روی فریم اول وارد کن.
4. مختصات کادر اولیه‌ی جسم را وارد کن.
5. روی «تحلیل ویدئو» بزن.
""")

uploaded = st.file_uploader("ویدئو را انتخاب کن", type=["mp4", "mov", "avi", "mkv"])

if uploaded is not None:
    suffix = os.path.splitext(uploaded.name)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        video_path = tmp.name

    cap = cv2.VideoCapture(video_path)
    ok, first = cap.read()
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if not ok:
        st.error("خواندن ویدئو ممکن نشد.")
        st.stop()

    h, w = first.shape[:2]
    st.image(cv2.cvtColor(first, cv2.COLOR_BGR2RGB),
             caption=f"{w} × {h} px | FPS: {fps:.2f}",
             use_container_width=True)

    st.subheader("۱) کالیبراسیون")
    real_distance = st.number_input(
        "فاصله‌ی واقعی بین دو نقطه‌ی مرجع (متر)",
        min_value=0.001, value=1.0, step=0.1
    )

    c1, c2 = st.columns(2)
    with c1:
        x1 = st.number_input("x نقطه ۱", min_value=0, max_value=w-1, value=0)
        y1 = st.number_input("y نقطه ۱", min_value=0, max_value=h-1, value=0)
    with c2:
        x2 = st.number_input("x نقطه ۲", min_value=0, max_value=w-1, value=max(1, w//4))
        y2 = st.number_input("y نقطه ۲", min_value=0, max_value=h-1, value=0)

    st.subheader("۲) کادر اولیه‌ی جسم")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        bx = st.number_input("x کادر", min_value=0, max_value=w-1, value=max(0, w//3))
    with b2:
        by = st.number_input("y کادر", min_value=0, max_value=h-1, value=max(0, h//3))
    with b3:
        bw = st.number_input("عرض کادر", min_value=1, max_value=w, value=max(10, w//6))
    with b4:
        bh = st.number_input("ارتفاع کادر", min_value=1, max_value=h, value=max(10, h//6))

    smooth = st.slider("هموارسازی سرعت (تعداد فریم)", 1, 15, 5)

    def create_tracker():
        makers = []
        if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
            makers.append(lambda: cv2.legacy.TrackerCSRT_create())
        if hasattr(cv2, "TrackerCSRT_create"):
            makers.append(lambda: cv2.TrackerCSRT_create())
        if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerMIL_create"):
            makers.append(lambda: cv2.legacy.TrackerMIL_create())
        if hasattr(cv2, "TrackerMIL_create"):
            makers.append(lambda: cv2.TrackerMIL_create())

        for maker in makers:
            try:
                return maker()
            except Exception:
                pass
        return None

    if st.button("تحلیل ویدئو", type="primary"):
        pixel_ref = math.dist((x1, y1), (x2, y2))
        if pixel_ref <= 0:
            st.error("دو نقطه‌ی مرجع باید متفاوت باشند.")
            st.stop()

        if bx + bw > w or by + bh > h:
            st.error("کادر جسم از محدوده‌ی تصویر خارج شده است.")
            st.stop()

        meters_per_pixel = real_distance / pixel_ref
        tracker = create_tracker()
        if tracker is None:
            st.error("Tracker مناسب در OpenCV پیدا نشد.")
            st.stop()

        cap = cv2.VideoCapture(video_path)
        ok, frame = cap.read()
        if not ok:
            st.error("خواندن ویدئو ممکن نشد.")
            st.stop()

        tracker.init(frame, (float(bx), float(by), float(bw), float(bh)))

        rows = []
        prev_center = None
        recent = []
        frame_idx = 0

        progress = st.progress(0)
        status = st.empty()

        while True:
            if frame_idx == 0:
                success = True
                box = (float(bx), float(by), float(bw), float(bh))
            else:
                ok, frame = cap.read()
                if not ok:
                    break
                success, box = tracker.update(frame)

            time_s = frame_idx / fps if fps > 0 else 0

            if success:
                x, y, ww, hh = [float(v) for v in box]
                center = (x + ww / 2.0, y + hh / 2.0)

                if prev_center is None:
                    raw_speed = 0.0
                else:
                    px_dist = math.dist(center, prev_center)
                    raw_speed = px_dist * meters_per_pixel * fps

                recent.append(raw_speed)
                if len(recent) > smooth:
                    recent.pop(0)
                speed = sum(recent) / len(recent)

                rows.append({
                    "frame": frame_idx,
                    "time_s": time_s,
                    "center_x_px": center[0],
                    "center_y_px": center[1],
                    "raw_speed_m_s": raw_speed,
                    "smoothed_speed_m_s": speed,
                })
                prev_center = center
            else:
                rows.append({
                    "frame": frame_idx,
                    "time_s": time_s,
                    "center_x_px": np.nan,
                    "center_y_px": np.nan,
                    "raw_speed_m_s": np.nan,
                    "smoothed_speed_m_s": np.nan,
                })

            frame_idx += 1
            if frame_count > 0:
                progress.progress(min(frame_idx / frame_count, 1.0))
            if frame_idx % 20 == 0:
                status.write(f"در حال تحلیل فریم {frame_idx} از {frame_count if frame_count > 0 else '?'}")

        cap.release()
        progress.progress(1.0)
        status.write("تحلیل تمام شد.")

        df = pd.DataFrame(rows)
        valid = df["smoothed_speed_m_s"].dropna()

        st.subheader("نتیجه")
        if len(valid):
            m1, m2, m3 = st.columns(3)
            m1.metric("بیشینه تندی", f"{valid.max():.3f} m/s")
            m2.metric("میانگین تندی", f"{valid.mean():.3f} m/s")
            m3.metric("مدت ویدئو", f"{df['time_s'].max():.2f} s")

        st.line_chart(df.set_index("time_s")[["smoothed_speed_m_s"]])
        st.dataframe(df, use_container_width=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "دانلود CSV",
            data=csv_data,
            file_name="instant_speed.csv",
            mime="text/csv"
        )

        st.caption("تندی لحظه‌ای با جابه‌جایی مرکز جسم بین فریم‌های متوالی تقریب زده می‌شود.")
