import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import numpy as np
from streamlit_mic_recorder import mic_recorder
from datetime import datetime

# --- 1. إعدادات الهوية البصرية ---
st.set_page_config(page_title="مصحح ورش - طريق الأزرق", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; }
    .main-box { background-color: #f0f7f0; padding: 25px; border-radius: 15px; border-right: 10px solid #1B5E20; box-shadow: 2px 2px 15px rgba(0,0,0,0.1); }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #c8e6c9; text-align: center; }
    .stButton>button { background-color: #2E7D32; color: white; width: 100%; height: 3em; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك تحليل المدود (Librosa) ---
def analyze_warsh_mad(audio_bytes):
    """تحليل الإشارة الصوتية لاكتشاف أطول فترة زمنية مستمرة (المد المشبع)"""
    with io.BytesIO(audio_bytes) as audio_file:
        y, sr_rate = librosa.load(audio_file)
    
    # حساب الطاقة الصوتية (RMS) لتحديد فترات الكلام
    rms = librosa.feature.rms(y=y)[0]
    # تنعيم الإشارة لتقليل التقطع
    smoothed_rms = np.convolve(rms, np.ones(5)/5, mode='same')
    threshold = np.max(smoothed_rms) * 0.2  # عتبة ذكية للضجيج
    
    # حساب أطول استمرار صوتي
    is_speech = smoothed_rms > threshold
    durations = []
    count = 0
    for s in is_speech:
        if s:
            count += 1
        else:
            if count > 0:
                durations.append(count * (512 / sr_rate)) # حساب الزمن بالثواني
            count = 0
    
    max_duration = max(durations) if durations else 0
    return round(max_duration, 2)

# --- 3. واجهة المستخدم ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مقرأة ورش الإلكترونية</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>تحليل التلاوة برواية ورش عن نافع - طريق الأزرق</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📖 إعدادات التلاوة")
    user_name = st.text_input("اسم القارئ:", "طالب العلم")
    
    # سور مختارة تبرز أحكام ورش (المد المشبع، النقل، التقليل)
    surah_options = {
        "سورة الكوثر": "إنا أعطيناك الكوثر",
        "سورة الإخلاص": "قل هو الله أحد الله الصمد",
        "سورة الفاتحة": "غير المغضوب عليهم ولا الضالين",
        "تدريب على المد": "آمنوا وعملوا الصالحات"
    }
    selected_surah = st.selectbox("اختر السورة/الآية:", list(surah_options.keys()))
    target_text = surah_options[selected_surah]
    
    st.divider()
    st.write("**قواعد طريق الأزرق:**")
    st.caption("- المد المتصل والمنفصل: 6 حركات")
    st.caption("- مد البدل: 2 أو 4 أو 6 حركات")

st.info(f"الآية المستهدفة: **{target_text}**")

# تسجيل الصوت
audio_data = mic_recorder(start_prompt="🎤 ابدأ التلاوة بالترتيل", stop_prompt="⏹️ توقف لطلب النتيجة", key='warsh_v1')

if audio_data:
    audio_bytes = audio_data['bytes']
    st.audio(audio_bytes)
    
    with st.spinner("⏳ جاري فحص التجويد والمدود..."):
        try:
            # أولاً: التعرف على النص عبر SpeechRecognition
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # ثانياً: تحليل زمن المد عبر Librosa
            mad_time = analyze_warsh_mad(audio_bytes)
            
            # ثالثاً: حساب دقة الكلمات
            matcher = difflib.SequenceMatcher(None, target_text.split(), spoken_text.split())
            accuracy = round(matcher.ratio() * 100, 1)
            
            # --- عرض النتائج ---
            st.markdown("<div class='main-box'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"<div class='metric-card'><h4>صحة اللفظ</h4><h2 style='color:#2E7D32;'>{accuracy}%</h2></div>", unsafe_allow_html=True)
            with col2:
                # في الترتيل الهادئ، 6 حركات تعادل تقريباً 3.5 إلى 5 ثوانٍ
                status_color = "#2E7D32" if mad_time > 3.5 else "#E64A19"
                st.markdown(f"<div class='metric-card'><h4>أطول مد</h4><h2 style='color:{status_color};'>{mad_time} ث</h2></div>", unsafe_allow_html=True)
            
            st.write(f"**النص المنطوق:** {spoken_text}")
            
            # التقييم الفني
            if accuracy > 85:
                if mad_time >= 3.5:
                    st.success("✅ أحسنت! تلاوة متقنة مع إشباع للمد وفق طريق الأزرق.")
                else:
                    st.warning("⚠️ اللفظ صحيح، ولكن زمن المد قصير. تذكر أن ورشاً يمد 6 حركات (إشباع).")
            else:
                st.error("❌ يوجد اختلاف بين النص المنطوق والآية، يرجى مراجعة مخارج الحروف.")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
        except Exception as e:
            st.error("عذراً، لم نتمكن من تحليل الصوت. حاول القراءة بوضوح أكبر.")