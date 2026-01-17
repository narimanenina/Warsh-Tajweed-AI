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
st.set_page_config(page_title="مقرأة ورش المدعمة بالصور", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-container {
        background-color: #fffcf2; padding: 30px; border-radius: 20px;
        border: 10px double #2E7D32; margin: 20px auto; display: flex; 
        flex-wrap: wrap; justify-content: center; gap: 15px;
    }
    .word-correct { color: #2E7D32; font-size: 35px; font-weight: bold; }
    .word-error { color: #D32F2F; font-size: 35px; font-weight: bold; text-decoration: underline; }
    .word-pending { color: #444444; font-size: 35px; }
    .makhraj-card { background-color: #ffffff; padding: 15px; border-radius: 15px; border: 1px solid #ddd; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. بيانات المخارج المصورة (ص 19) ---
MAKHRAJ_GUIDE = {
    "إِنَّآ": {
        "makhraj": "الجوف واللسان",
        "image": "",
        "tip": "مد الألف من الجوف (تجويف الحلق والفم) لـ 6 حركات."
    },
    "أَعْطَيْنَاكَ": {
        "makhraj": "وسط الحلق (للعين)",
        "image": "",
        "tip": "اضغط على وسط الحلق لإخراج العين واضحة."
    },
    "اَ۬لْكَوْثَرَ": {
        "makhraj": "طرف اللسان (للثاء)",
        "image": "",
        "tip": "أخرج طرف لسانك مع أطراف الثنايا العليا لنطق الثاء."
    },
    "اَ۬لَابْتَرُۖ": {
        "makhraj": "الشفتان (للباء)",
        "image": "",
        "tip": "أطبق الشفتين بقوة ثم أطلقهما لتحقيق القلقلة في الباء."
    }
}

def clean_text(text):
    t = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text)
    t = t.replace("آ", "ا").replace("اَ۬", "ا").replace("ۖ", "")
    return t.strip()

# --- 3. المنطق والعرض ---
st.title("🕌 مصحح ورش مع الدليل البصري")

target_words = ["إِنَّآ", "أَعْطَيْنَاكَ", "اَ۬لْكَوْثَرَ", "فَصَلِّ", "لِرَبِّكَ", "وَانْحَرْۖ", "إِنَّ", "شَانِئَكَ", "هُوَ", "اَ۬لَابْتَرُۖ"]

words_area = st.empty()
words_area.markdown(f"<div class='quran-container'>{' '.join([f'<span class=word-pending>{w}</span>' for w in target_words])}</div>", unsafe_allow_html=True)

audio = mic_recorder(start_prompt="🎤 ابدأ الترتيل لترى المخارج", stop_prompt="⏹️ تحليل الأداء", key='visual_makhraj')

if audio:
    try:
        with st.spinner("⏳ جاري تحليل مخارج الحروف..."):
            raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_buf = io.BytesIO()
            raw_audio.export(wav_buf, format="wav")
            wav_buf.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                recorded = r.record(source)
                spoken = r.recognize_google(recorded, language="ar-SA")
                spoken_words = [clean_text(w) for w in spoken.split()]

            # عرض النتائج الملونة
            res_html = "<div class='quran-container'>"
            errors = []
            for w in target_words:
                if clean_text(w) in spoken_words:
                    res_html += f"<span class='word-correct'>{w}</span> "
                else:
                    res_html += f"<span class='word-error'>{w}</span> "
                    errors.append(w)
            res_html += "</div>"
            words_area.markdown(res_html, unsafe_allow_html=True)

            # عرض الدليل البصري للأخطاء
            if errors:
                st.subheader("📍 دليل تصحيح المخارج البصري")
                for err_w in set(errors):
                    if err_w in MAKHRAJ_GUIDE:
                        guide = MAKHRAJ_GUIDE[err_w]
                        with st.expander(f"كيف تصحح نطق: {err_w}"):
                            col1, col2 = st.columns([1, 2])
                            with col1:
                                st.write(guide['image'])
                            with col2:
                                st.markdown(f"**المخرج:** {guide['makhraj']}")
                                st.info(f"💡 {guide['tip']}")

    except Exception as e:
        st.error("يرجى المحاولة مرة أخرى بوضوح.")
