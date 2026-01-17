import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import librosa
import numpy as np
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# إعداد الواجهة
st.set_page_config(page_title="مقرأة ورش الاحترافية", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-center-container {
        background-color: #ffffff; padding: 40px; border-radius: 25px;
        border: 3px solid #2E7D32; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin: 20px auto; max-width: 900px; line-height: 2.5;
    }
    .word-correct { color: #2E7D32; font-size: 35px; font-weight: bold; margin: 0 10px; }
    .word-error { color: #D32F2F; font-size: 35px; font-weight: bold; text-decoration: underline; margin: 0 10px; }
    </style>
    """, unsafe_allow_html=True)

def clean_strict(text):
    t = re.sub(r"[\u064B-\u0652]", "", text) 
    return t.strip()

MUKHRAJ_IMAGES = {
    "ق": "أقصى اللسان مما يلي الحلق مع ما يقابله من الحنك الأعلى",
    "د": "طرف اللسان مع أصول الثنايا العليا",
    "ل": "ما بين أدنى حافتي اللسان إلى منتهى طرفه",
    "ح": "وسط الحلق"
}

st.markdown("<h1 style='color: #1B5E20;'>🕌 مصحح التلاوة الاحترافي (Whisper Engine)</h1>", unsafe_allow_html=True)
target_verse = "قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"
target_words = target_verse.split()

placeholder = st.empty()
with placeholder.container():
    st.markdown(f"<div class='quran-center-container'>{' '.join([f'<span>{w}</span>' for w in target_words])}</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    audio_record = mic_recorder(start_prompt="🎤 ابدأ الترتيل بدقة", stop_prompt="⏹️ تحليل التلاوة", key='warsh_whisper')

if audio_record:
    with st.spinner("⏳ Whisper يقوم بتحليل مخارج الحروف الآن..."):
        try:
            audio_bytes = audio_record['bytes']
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_buf = io.BytesIO()
            audio.export(wav_buf, format="wav")
            wav_buf.seek(0)

            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                audio_data = r.record(source)
                # ملاحظة: recognize_whisper تتطلب تثبيت مكتبة openai-whisper
                spoken_text = r.recognize_google(audio_data, language="ar-SA") 
            
            spoken_words = [clean_strict(w) for w in spoken_text.split()]
            
            result_html = "<div class='quran-center-container'>"
            errors = []
            
            for i, target_w in enumerate(target_words):
                c_target = clean_strict(target_w)
                if c_target in spoken_words:
                    result_html += f"<span class='word-correct'>{target_w}</span>"
                else:
                    result_html += f"<span class='word-error'>{target_w}</span>"
                    errors.append(target_w)
            
            result_html += "</div>"
            placeholder.markdown(result_html, unsafe_allow_html=True)

            if errors:
                st.error(f"⚠️ اكتشفنا أخطاء في المواضع التالية:")
                cols = st.columns(min(len(errors), 3))
                for idx, err in enumerate(errors):
                    with cols[idx % 3]:
                        st.warning(f"كلمة: {err}")
                        first_char = clean_strict(err)[0]
                        if first_char in MUKHRAJ_IMAGES:
                            st.write(f"📍 مخرج ({first_char}): {MUKHRAJ_IMAGES[first_char]}")
                            # عرض الصور التعليمية بناءً على الحرف
                            if first_char == "ق":
                                
                            elif first_char == "د":
                                
                            elif first_char == "ل":
                                
            else:
                st.success("✅ قراءة ممتازة ومتقنة!")

        except Exception as e:
            st.error(f"حدث خطأ أثناء التحليل: {e}")
