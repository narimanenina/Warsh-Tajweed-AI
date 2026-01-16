import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import librosa
import numpy as np
import soundfile as sf
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الواجهة ---
st.set_page_config(page_title="مصحح تلاوة ورش - نسخة مستقرة", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .main-box { background-color: #f4f9f4; padding: 25px; border-radius: 15px; border-right: 10px solid #1B5E20; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #c8e6c9; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. دالة تحويل الصوت ومعالجة الصيغ ---
def process_audio_data(audio_bytes):
    """تحويل البايتات المسجلة من المتصفح إلى صيغة WAV PCM صالحة"""
    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
    # تحويل لـ Mono وتردد 16000Hz لضمان أفضل دقة مع جوجل وليبروسا
    audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
    
    buf = io.BytesIO()
    audio_segment.export(buf, format="wav")
    buf.seek(0)
    return buf

# --- 3. دالة تحليل مد ورش (طريق الأزرق) ---
def analyze_warsh_duration(wav_buf):
    y, sr_rate = librosa.load(wav_buf)
    rms = librosa.feature.rms(y=y)[0]
    smoothed_rms = np.convolve(rms, np.ones(5)/5, mode='same')
    is_speech = smoothed_rms > (np.max(smoothed_rms) * 0.25)
    
    durations = []
    count = 0
    for s in is_speech:
        if s: count += 1
        else:
            if count > 0: durations.append(count * (512 / sr_rate))
            count = 0
    return round(max(durations), 2) if durations else 0

# --- 4. واجهة التطبيق الرئيسية ---
st.title("🕌 مصحح تلاوة ورش الذكي")

with st.sidebar:
    st.header("👤 بيانات القارئ")
    surahs = {"سورة الكوثر": "إنا أعطيناك الكوثر", "سورة الفاتحة": "غير المغضوب عليهم ولا الضالين"}
    choice = st.selectbox("اختر السورة:", list(surahs.keys()))
    target_text = surahs[choice]
    st.info(f"الآية المرجعية: {target_text}")

# تسجيل الصوت
audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة", stop_prompt="⏹️ توقف واطلب النتيجة", key='final_rec')

if audio_record:
    audio_bytes = audio_record['bytes']
    
    with st.spinner("⏳ جاري تحويل الصوت وتحليل التجويد..."):
        try:
            # معالجة الصيغة (حل مشكلة PCM WAV)
            wav_buffer = process_audio_data(audio_bytes)
            
            # التعرف على النص
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                audio_data = r.record(source)
                spoken_text = r.recognize_google(audio_data, language="ar-SA")
            
            # تحليل المد
            wav_buffer.seek(0) # إعادة المؤشر للبداية
            mad_time = analyze_warsh_duration(wav_buffer)
            
            # حساب الدقة
            acc = round(difflib.SequenceMatcher(None, target_text.split(), spoken_text.split()).ratio() * 100, 1)
            
            # عرض النتائج
            st.markdown("<div class='main-box'>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='metric-card'><h4>صحة اللفظ</h4><h2>{acc}%</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><h4>أطول مد</h4><h2>{mad_time} ث</h2></div>", unsafe_allow_html=True)
            
            st.write(f"**المنطوق:** {spoken_text}")
            
            if acc > 85 and mad_time >= 3.5:
                st.success("ما شاء الله! تلاوة صحيحة مع مد مشبع (طريق الأزرق).")
            elif acc > 85:
                st.warning("اللفظ صحيح ولكن المد قصير (ورش يمد 6 حركات).")
            else:
                st.error("يوجد خطأ في نطق الكلمات.")
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ خطأ فني: تأكد من الكلام بوضوح (التفاصيل: {str(e)})")
