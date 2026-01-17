import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
import speech_recognition as sr
import io
import re
import random
import datetime
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الواجهة ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

if 'history' not in st.session_state: st.session_state.history = []

# تحسين التنسيق ليكون قريباً من شكل المصحف
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri:wght@700&display=swap');
    
    html, body, [class*="st-"] { 
        font-family: 'Amiri', serif; 
        direction: rtl; 
        text-align: center; 
    }
    
    .quran-frame {
        background-color: #fffcf2; 
        padding: 40px; 
        border-radius: 30px;
        border: 15px double #2E7D32; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 20px auto; 
        max-width: 900px;
        line-height: 2.5;
    }

    .word-correct { color: #2E7D32; font-size: 45px; font-weight: bold; font-family: 'Amiri Quran', serif; }
    .word-error { color: #D32F2F; font-size: 45px; font-weight: bold; text-decoration: underline; font-family: 'Amiri Quran', serif; }
    .word-pending { color: #3e2723; font-size: 45px; font-family: 'Amiri Quran', serif; }
    
    .aya-num { color: #2E7D32; font-size: 25px; font-weight: bold; margin: 0 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. البيانات ---
# نص السورة برواية ورش كما طلبته
kawthar_warsh = [
    "إِنَّآ", "أَعْطَيْنَٰكَ", "اَ۬لْكَوْثَرَ", "(1)", 
    "فَصَلِّ", "لِرَبِّكَ", "وَانْحَرْۖ", "(2)", 
    "إِنَّ", "شَانِئَكَ", "هُوَ", "اَ۬لَابْتَرُۖ", "(3)"
]

def clean_for_comparison(text):
    # إزالة علامات الضبط الخاصة بورش للمقارنة البرمجية فقط
    t = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655\u0610-\u0614]", "", text)
    t = t.replace("آ", "ا").replace("اَ۬", "ا").replace("ۖ", "")
    return t.strip()

# --- 3. العرض والتحليل ---
st.title("🕌 مصحح التلاوة - رواية ورش")

selected_surah = "سورة الكوثر"
target_words = kawthar_warsh

words_area = st.empty()

# عرض السورة في البداية
init_html = "<div class='quran-frame'>"
for w in target_words:
    if "(" in w: init_html += f"<span class='aya-num'>{w}</span> "
    else: init_html += f"<span class='word-pending'>{w}</span> "
init_html += "</div>"
words_area.markdown(init_html, unsafe_allow_html=True)

audio = mic_recorder(start_prompt="🎤 ابدأ الترتيل الآن", stop_prompt="⏹️ توقف للتحليل", key='warsh_v3')

if audio:
    try:
        with st.spinner("⏳ جاري تحليل مخارج الحروف..."):
            audio_data = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_buf = io.BytesIO()
            audio_data.export(wav_buf, format="wav")
            wav_buf.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            spoken_words = [clean_for_comparison(w) for w in spoken_text.split()]
            
            # تحديث العرض بالنتائج
            res_html = "<div class='quran-frame'>"
            correct_count = 0
            word_total = 0
            
            for w in target_words:
                if "(" in w: 
                    res_html += f"<span class='aya-num'>{w}</span> "
                    continue
                
                word_total += 1
                clean_w = clean_for_comparison(w)
                if clean_w in spoken_words:
                    res_html += f"<span class='word-correct'>{w}</span> "
                    correct_count += 1
                else:
                    res_html += f"<span class='word-error'>{w}</span> "
            
            res_html += "</div>"
            words_area.markdown(res_html, unsafe_allow_html=True)
            
            acc = round((correct_count/word_total)*100)
            st.metric("نسبة الإتقان برواية ورش", f"{acc}%")
            if acc == 100: st.balloons()

    except Exception as e:
        st.error("يرجى نطق الآيات بوضوح ليتمكن النظام من تمييزها.")
