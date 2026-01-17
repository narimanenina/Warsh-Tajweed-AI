import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
import speech_recognition as sr
import io
import re
import time
import random
import datetime
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
from fpdf import FPDF

# --- 1. إعدادات الواجهة ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

# منع اختفاء الواجهة باستخدام حاويات ثابتة
if 'history' not in st.session_state: st.session_state.history = []

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-container {
        background-color: #ffffff; padding: 30px; border-radius: 20px;
        border: 2px solid #2E7D32; margin: 20px auto; display: flex; 
        flex-wrap: wrap; justify-content: center; gap: 15px;
    }
    .word-correct { color: #2E7D32; font-size: 35px; font-weight: bold; }
    .word-error { color: #D32F2F; font-size: 35px; font-weight: bold; text-decoration: underline; }
    .word-pending { color: #444444; font-size: 35px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. البيانات ---
surahs = {
    "سورة الكوثر": "إِنَّا أَعْطَيْنَاكَ الْكَوْثَرَ فَصَلِّ لِرَبِّكَ وَانْحَرْ إِنَّ شَانِئَكَ هُوَ الْأَبْتَرُ",
    "سورة الإخلاص": "قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"
}

def clean_text(text):
    return re.sub(r"[\u064B-\u0652]", "", text).strip()

# --- 3. العرض الرئيسي ---
st.title("🕌 مصحح التلاوة التفاعلي")

tab1, tab2 = st.tabs(["🎯 الاختبار", "📊 السجل"])

with tab1:
    selected_s = st.selectbox("اختر السورة:", list(surahs.keys()))
    target_v = surahs[selected_s]
    target_w = target_v.split()
    
    # حاوية عرض الكلمات
    words_area = st.empty()
    words_area.markdown(f"<div class='quran-container'>{' '.join([f'<span class=word-pending>{w}</span>' for w in target_w])}</div>", unsafe_allow_html=True)
    
    # زر التسجيل
    audio = mic_recorder(start_prompt="🎤 ابدأ التسجيل", stop_prompt="⏹️ توقف للتحليل", key='recorder_v1')

    if audio:
        try:
            with st.spinner("⏳ جاري المعالجة..."):
                # تحويل الصوت بصيغة WAV مبسطة جداً
                audio_data = AudioSegment.from_file(io.BytesIO(audio['bytes']))
                audio_data = audio_data.normalize()
                
                wav_buffer = io.BytesIO()
                audio_data.export(wav_buffer, format="wav")
                wav_buffer.seek(0)
                
                r = sr.Recognizer()
                with sr.AudioFile(wav_buffer) as source:
                    r.adjust_for_ambient_noise(source)
                    audio_recorded = r.record(source)
                    # استخدام التعرف على الكلام من جوجل
                    spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
                
                spoken_words = [clean_text(w) for w in spoken_text.split()]
                
                # تحديث الواجهة بالنتائج
                res_html = "<div class='quran-container'>"
                correct_count = 0
                for w in target_w:
                    if clean_text(w) in spoken_words:
                        res_html += f"<span class='word-correct'>{w}</span> "
                        correct_count += 1
                    else:
                        res_html += f"<span class='word-error'>{w}</span> "
                res_html += "</div>"
                words_area.markdown(res_html, unsafe_allow_html=True)
                
                st.success(f"تم تحليل التلاوة بنجاح! نسبة الإتقان: {round((correct_count/len(target_w))*100)}%")

        except Exception as e:
            st.error(f"حدث خطأ في التحليل: يرجى التأكد من نطق الكلمات بوضوح.")
            st.info("نصيحة: سجل في مكان هادئ واستخدم متصفح كروم.")

with tab2:
    st.write("سيظهر سجل تلاواتك هنا قريباً.")
