import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import numpy as np
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
from datetime import datetime

# --- 1. إعدادات الصفحة والجماليات ---
st.set_page_config(page_title="مصحح تلاوة ورش - طريق الأزرق", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-card {
        background-color: #f0f4f0; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-right: 5px solid #2E7D32;
        margin-bottom: 20px; color: #1B5E20;
    }
    .metric-box {
        background-color: white; padding: 15px; border-radius: 10px;
        border: 1px solid #c8e6c9; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 10px; width: 100%; }
    h1 { color: #1B5E20; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. وظائف معالجة النص والصوت ---
def normalize_arabic(text):
    """إزالة التشكيل وتوحيد الهمزات لزيادة دقة المطابقة اللفظية"""
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"[\u064B-\u0652]", "", text) # إزالة التشكيل
    return text.strip()

def process_audio_to_wav(audio_bytes):
    """تحويل بايتات الصوت من المتصفح إلى صيغة WAV PCM المتوافقة"""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_channels(1).set_frame_rate(16000)
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    buf.seek(0)
    return buf

def analyze_mad_duration(wav_buf):
    """تحليل أطول فترة مد صوتي مستمرة باستخدام librosa"""
    y, sr_rate = librosa.load(wav_buf)
    rms = librosa.feature.rms(y=y)[0]
    # تنعيم الإشارة
    smoothed_rms = np.convolve(rms, np.ones(5)/5, mode='same')
    # حساب الاستمرارية فوق عتبة معينة
    threshold = np.max(smoothed_rms) * 0.25
    durations = []
    count = 0
    for s in (smoothed_rms > threshold):
        if s: count += 1
        else:
            if count > 0: durations.append(count * (512 / sr_rate))
            count = 0
    return round(max(durations), 2) if durations else 0

# --- 3. واجهة المستخدم ---
st.title("🕌 مصحح تلاوة ورش الذكي")
st.subheader("تحليل اللفظ ومدود طريق الأزرق")

with st.sidebar:
    st.header("⚙️ إعدادات الجلسة")
    user_name = st.text_input("اسم القارئ:", "طالب العلم")
    surah_name = st.selectbox("اختر السورة:", ["إنا أعطيناك الكوثر", "الإخلاص", "الفاتحة", "نص حر"])
    
    target_map = {
        "إنا أعطيناك الكوثر": "إنا أعطيناك الكوثر",
        "الإخلاص": "قل هو الله أحد الله الصمد لم يلد ولم يولد",
        "الفاتحة": "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين"
    }
    target_text = st.text_area("الآية المستهدفة:", value=target_map.get(surah_name, ""))

# تسجيل الصوت
audio_data = mic_recorder(start_prompt="🔴 ابدأ التلاوة", stop_prompt="⏹️ توقف واطلب النتيجة", key='warsh_v3')

if audio_data:
    audio_bytes = audio_data['bytes']
    st.audio(audio_bytes)
    
    with st.spinner("⏳ جاري تحليل التلاوة..."):
        try:
            # 1. تحويل الصوت
            wav_buf = process_audio_to_wav(audio_bytes)
            
            # 2. التعرف على النص (Google STT)
            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # 3. تحليل زمن المد (Librosa)
            wav_buf.seek(0)
            mad_time = analyze_mad_duration(wav_buf)
            
            # 4. المقارنة الذكية
            norm_target = normalize_arabic(target_text)
            norm_spoken = normalize_arabic(spoken_text)
            
            matcher = difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split())
            accuracy = round(matcher.ratio() * 100, 1)

            # --- عرض النتائج ---
            st.markdown("<div class='quran-card'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<div class='metric-box'><h4>دقة اللفظ</h4><h2 style='color:#2E7D32;'>{accuracy}%</h2></div>", unsafe_allow_html=True)
            with col2:
                # معيار مد ورش (تقريباً > 3 ثواني للمد المشبع)
                color = "#2E7D32" if mad_time > 3.0 else "#E64A19"
                st.markdown(f"<div class='metric-box'><h4>أطول مد</h4><h2 style='color:{color};'>{mad_time} ث</h2></div>", unsafe_allow_html=True)
            
            st.write(f"**الكلمات المكتشفة:** {spoken_text}")
            
            if accuracy > 85:
                if mad_time > 3.0:
                    st.success("✅ ما شاء الله! تلاوة صحيحة مع مد مشبع متقن.")
                else:
                    st.warning("⚠️ اللفظ صحيح، لكن زمن المد قصير (ورش يمد المشبع 6 حركات).")
            else:
                st.error("❌ يوجد اختلاف في نطق الكلمات، حاول الترتيل بوضوح أكبر.")
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ عذراً، لم نتمكن من فهم الصوت بشكل واضح. (الخطأ: {e})")
