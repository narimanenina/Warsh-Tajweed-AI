import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import librosa
import numpy as np
import soundfile as sf
from streamlit_mic_recorder import mic_recorder

# --- 1. الإعدادات البصرية ---
st.set_page_config(page_title="مصحح ورش - طريق الأزرق", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .main-box { background-color: #f4f9f4; padding: 20px; border-radius: 15px; border-right: 10px solid #1B5E20; }
    .metric-card { background-color: white; padding: 10px; border-radius: 10px; border: 1px solid #c8e6c9; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. دالة تحليل المد المشبع (6 حركات) ---
def get_max_mad_duration(audio_bytes):
    try:
        # قراءة الصوت باستخدام soundfile مباشرة من البايتات
        audio_stream = io.BytesIO(audio_bytes)
        data, samplerate = sf.read(audio_stream)
        
        # إذا كان الصوت ستيريو، نحوله لمونو
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # حساب الطاقة الصوتية
        rms = librosa.feature.rms(y=data)[0]
        threshold = np.max(rms) * 0.3
        
        # حساب أطول فترة استمرار صوتي فوق العتبة
        frames = librosa.frames_to_time(np.arange(len(rms)), sr=samplerate)
        is_speech = rms > threshold
        
        max_duration = 0
        current_duration = 0
        frame_time = frames[1] - frames[0] if len(frames) > 1 else 0.02
        
        for speech in is_speech:
            if speech:
                current_duration += frame_time
            else:
                max_duration = max(max_duration, current_duration)
                current_duration = 0
        return round(max(max_duration, current_duration), 2)
    except Exception as e:
        return 0

# --- 3. واجهة التطبيق ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مصحح تلاوة ورش</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📖 خيارات التلاوة")
    surah_dict = {
        "سورة الكوثر": "إنا أعطيناك الكوثر",
        "سورة الإخلاص": "قل هو الله أحد الله الصمد",
        "سورة الفاتحة": "غير المغضوب عليهم ولا الضالين"
    }
    choice = st.selectbox("اختر السورة:", list(surah_dict.keys()))
    target = surah_dict[choice]
    st.info(f"الآية: {target}")

# استخدام الميكروفون
audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة", stop_prompt="⏹️ توقف", key='recorder')

if audio_record:
    audio_bytes = audio_record['bytes']
    st.audio(audio_bytes)
    
    with st.spinner("جاري التحليل..."):
        try:
            # التحليل النصي
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio_data = r.record(source)
                # استخدام لغة الاستهداف (العربية)
                spoken_text = r.recognize_google(audio_data, language="ar-SA")
            
            # تحليل المد
            mad_duration = get_max_mad_duration(audio_bytes)
            
            # حساب المطابقة
            accuracy = round(difflib.SequenceMatcher(None, target.split(), spoken_text.split()).ratio() * 100, 1)
            
            # عرض النتائج
            st.markdown("<div class='main-box'>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='metric-card'><h4>دقة الألفاظ</h4><h2>{accuracy}%</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><h4>زمن أطول مد</h4><h2>{mad_duration} ثانية</h2></div>", unsafe_allow_html=True)
            
            st.write(f"**النص المكتشف:** {spoken_text}")
            
            if accuracy > 80:
                if mad_duration > 3.5:
                    st.success("✅ تلاوة رائعة ومد مشبع صحيح برواية ورش!")
                else:
                    st.warning("⚠️ اللفظ صحيح، ولكن حاول إطالة المد ليكون 6 حركات (إشباع).")
            else:
                st.error("❌ هناك اختلاف في الكلمات، حاول القراءة بهدوء وترتيل.")
            st.markdown("</div>", unsafe_allow_html=True)

        except sr.UnknownValueError:
            st.error("❌ لم يستطع النظام تمييز الكلمات. حاول القراءة بوضوح أكبر وبصوت مرتفع قليلاً.")
        except Exception as e:
            st.error(f"⚠️ خطأ في معالجة الملف الصوتي: {e}")

