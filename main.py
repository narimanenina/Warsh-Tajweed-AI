import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import librosa
import numpy as np
import re
import os
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="مدرسة بلال العيناوي الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-container { background-color: #fcfdfc; padding: 25px; border-radius: 15px; border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .score-display { background-color: #e8f5e9; border-radius: 15px; padding: 20px; text-align: center; border: 2px solid #2E7D32; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. وظائف المعالجة الصوتية ---
def get_audio_fingerprint(audio_bytes):
    """تحويل الصوت إلى WAV PCM واستخراج الخصائص (MFCC)"""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_frame_rate(22050).set_channels(1)
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    buf.seek(0)
    y, sr_rate = librosa.load(buf, sr=22050)
    # استخراج بصمة الصوت التي تميز مخارج حروف القارئ
    mfcc = librosa.feature.mfcc(y=y, sr=sr_rate, n_mfcc=13)
    return mfcc, buf

# --- 3. واجهة المستخدم ---
st.title("🕌 مدرسة القارئ بلال العيناوي")
st.write("نظام المحاكاة الذكي: قارن أداءك الملحني والتجويدي بصوت الشيخ بلال.")



with st.sidebar:
    st.header("⚙️ المرجع الصوتي")
    teacher_file = st.file_uploader("ارفع مقطع الشيخ بلال العيناوي:", type=['wav', 'mp3', 'ogg'])
    if teacher_file:
        st.audio(teacher_file)
        t_bytes = teacher_file.read()

st.markdown("<div class='quran-container'>", unsafe_allow_html=True)
st.subheader("🎤 سجل محاكاتك الآن:")
student_rec = mic_recorder(start_prompt="🎤 ابدأ التسجيل", stop_prompt="⏹️ توقف واطلب النتيجة", key='bilal_v3')

if student_rec and teacher_file:
    s_bytes = student_rec['bytes']
    
    with st.spinner("⏳ جاري تحليل البصمة الصوتية والمطابقة مع أداء الشيخ بلال..."):
        try:
            # معالجة صوت الشيخ والتلميذ
            mfcc_t, _ = get_audio_fingerprint(t_bytes)
            mfcc_s, _ = get_audio_fingerprint(s_bytes)
            
            # المقارنة باستخدام Dynamic Time Warping (DTW)
            distance, _ = fastdtw(mfcc_t.T, mfcc_s.T, dist=euclidean)
            # معادلة تحسين النسبة لتناسب الأداء القرآني
            score = round(100 / (1 + (distance / 45000)), 1)
            
            st.markdown(f"""
                <div class='score-display'>
                    <h3>نسبة محاكاة الشيخ بلال</h3>
                    <h1 style='color:#2E7D32; font-size:60px;'>{score}%</h1>
                </div>
            """, unsafe_allow_html=True)
            
            if score > 80:
                st.success("أداء ممتاز! لقد وفقت في محاكاة رنين مخارج حروف الشيخ بلال.")
            elif score > 60:
                st.warning("أداء جيد، حاول التركيز أكثر على 'النبر' وزمن المدود كما يفعل الشيخ.")
            else:
                st.error("توجد فوارق في الأداء. استمع للشيخ بلال مرة أخرى وحاول التقليد بدقة أكبر.")

        except Exception as e:
            st.error(f"⚠️ خطأ تقني: {e}")
elif student_rec and not teacher_file:
    st.warning("يرجى رفع ملف صوتي للشيخ بلال أولاً لتتم المقارنة.")

st.markdown("</div>", unsafe_allow_html=True)
