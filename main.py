import streamlit as st
import pandas as pd
import librosa
import numpy as np
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

# --- 1. إعدادات الواجهة ---
st.set_page_config(page_title="مدرسة بلال العيناوي", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .main-card { background-color: #f8f9f8; padding: 25px; border-radius: 15px; border-right: 10px solid #1B5E20; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .vs-box { background-color: white; border: 2px solid #e0e0e0; border-radius: 15px; padding: 20px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. دالة تحويل وتحليل الصوت ---
def convert_and_load(audio_bytes):
    """تحويل الصوت إلى WAV PCM وتحميله كمصفوفة رقمية"""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    # توحيد التردد والقنوات لضمان دقة المقارنة
    audio = audio.set_frame_rate(22050).set_channels(1)
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    buf.seek(0)
    y, sr = librosa.load(buf, sr=22050)
    return y, sr

def calculate_mimicry_score(t_bytes, s_bytes):
    """حساب نسبة المحاكاة باستخدام DTW و MFCC"""
    y_t, sr_t = convert_and_load(t_bytes)
    y_s, sr_s = convert_and_load(s_bytes)
    
    # استخراج بصمة الصوت (رنين الحروف)
    mfcc_t = librosa.feature.mfcc(y=y_t, sr=sr_t, n_mfcc=13)
    mfcc_s = librosa.feature.mfcc(y=y_s, sr=sr_s, n_mfcc=13)
    
    # المقارنة الزمنية المرنة
    distance, _ = fastdtw(mfcc_t.T, mfcc_s.T, dist=euclidean)
    
    # معادلة تحويل المسافة إلى نسبة مئوية (تقريبية للأداء التجويدي)
    score = 100 / (1 + (distance / 40000))
    return round(score, 1)

# --- 3. واجهة المستخدم ---
st.title("🕌 محاكي القارئ بلال العيناوي")
st.write("قارن تلاوتك بأداء الشيخ بلال العيناوي في مخارج الحروف والنبرة.")



with st.sidebar:
    st.header("👤 المرجع المعتمد")
    st.info("القارئ: بلال العيناوي")
    uploaded_teacher = st.file_uploader("ارفع مقطع الشيخ بلال (WAV/MP3/OGG):")

st.markdown("<div class='main-card'>", unsafe_allow_html=True)
if uploaded_teacher:
    t_bytes = uploaded_teacher.read()
    st.write("✅ تم تحميل صوت الشيخ المرجع.")
    st.audio(t_bytes)
    
    st.divider()
    
    st.subheader("🎤 دورك الآن (التلميذ):")
    student_rec = mic_recorder(start_prompt="بدء المحاكاة", stop_prompt="توقف للمقارنة", key='bilal_mimic_final')
    
    if student_rec:
        s_bytes = student_rec['bytes']
        
        with st.spinner("⏳ جاري تحليل البصمة الصوتية ومطابقتها..."):
            try:
                final_score = calculate_mimicry_score(t_bytes, s_bytes)
                
                st.markdown("<div class='vs-box'>", unsafe_allow_html=True)
                st.write("### نسبة مطابقة أداء الشيخ بلال")
                color = "#2E7D32" if final_score > 75 else "#E64A19"
                st.markdown(f"<h1 style='color:{color}; font-size: 60px;'>{final_score}%</h1>", unsafe_allow_html=True)
                
                if final_score > 80:
                    st.success("أداء متقن! لقد نجحت في محاكاة رنين مخارج الشيخ.")
                elif final_score > 55:
                    st.warning("محاولة جيدة. ركز أكثر على 'النبرة' وزمن الغنة والمدود.")
                else:
                    st.error("توجد فوارق كبيرة في الأداء. استمع للشيخ بلال مرة أخرى وحاول التقليد.")
                st.markdown("</div>", unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"⚠️ خطأ تقني: {str(e)}")
else:
    st.warning("يرجى رفع ملف صوتي للشيخ بلال العيناوي أولاً لبدء عملية المقارنة.")
st.markdown("</div>", unsafe_allow_html=True)
