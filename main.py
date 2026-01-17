import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
import librosa
import numpy as np
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الواجهة المتطورة ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    
    html, body, [class*="st-"] { 
        font-family: 'Amiri', serif; direction: rtl; text-align: center; 
    }

    /* حاوية السورة المركزية المحسنة لمنع التصاق الكلمات */
    .quran-center-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        align-items: center;
        background-color: #ffffff;
        padding: 40px;
        border-radius: 25px;
        border: 2px solid #2E7D32;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        margin: 20px auto;
        max-width: 950px;
        line-height: 2.8;
        gap: 15px; /* يضمن وجود مسافة ثابتة بين الكلمات */
    }

    /* تنسيق الكلمات */
    .word-correct { color: #2E7D32; font-size: 38px; font-weight: bold; padding: 0 5px; }
    .word-error { color: #D32F2F; font-size: 38px; font-weight: bold; text-decoration: underline; padding: 0 5px; }
    .word-pending { color: #444444; font-size: 38px; padding: 0 5px; }

    .stButton>button { width: 280px; border-radius: 50px; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. منطق المعالجة ---
def clean_strict(text):
    """تنظيف النص من التشكيل لضمان دقة المقارنة اللفظية"""
    t = re.sub(r"[\u064B-\u0652]", "", text) 
    return t.strip()

MUKHRAJ_DATA = {
    "ق": {"info": "أقصى اللسان مع ما يقابله من الحنك الأعلى", "tip": "ارفع أقصى لسانك بقوة لتجنب تحويلها لكاف."},
    "د": {"info": "طرف اللسان مع أصول الثنايا العليا", "tip": "احرص على القلقلة إذا كانت ساكنة (أحدْ)."},
    "ل": {"info": "أدنى حافتي اللسان إلى منتهى طرفه", "tip": "تغلظ اللام في 'الله' لورش إذا سبقت بفتح أو ضم."},
}

# --- 3. عرض التطبيق ---
st.markdown("<h1 style='color: #1B5E20;'>🕌 مصحح التلاوة التفاعلي (رواية ورش)</h1>", unsafe_allow_html=True)

target_verse = "قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"
target_words = target_verse.split()

# عرض السورة بشكل مبدئي
placeholder = st.empty()
with placeholder.container():
    html_init = "<div class='quran-center-container'>"
    for w in target_words:
        html_init += f"<span class='word-pending'>{w}</span>"
    html_init += "</div>"
    st.markdown(html_init, unsafe_allow_html=True)

# ميكروفون التسجيل في المركز
c1, c2, c3 = st.columns([1, 1, 1])
with c2:
    audio_record = mic_recorder(start_prompt="🎤 ابدأ الترتيل", stop_prompt="⏹️ توقف للتحليل", key='warsh_v20')

# --- 4. التحليل بعد التسجيل ---
if audio_record:
    with st.spinner("⏳ جاري تحليل مخارج الحروف..."):
        try:
            audio_bytes = audio_record['bytes']
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_buf = io.BytesIO()
            audio.export(wav_buf, format="wav")
            wav_buf.seek(0)

            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                audio_data = r.record(source)
                spoken_text = r.recognize_google(audio_data, language="ar-SA")
            
            spoken_words = [clean_strict(w) for w in spoken_text.split()]
            
            # إعادة بناء العرض مع التلوين والمسافات
            result_html = "<div class='quran-center-container'>"
            errors = []
            
            for word in target_words:
                c_word = clean_strict(word)
                if c_word in spoken_words:
                    result_html += f"<span class='word-correct'>{word}</span>"
                else:
                    result_html += f"<span class='word-error'>{word}</span>"
                    errors.append(word)
            
            result_html += "</div>"
            placeholder.markdown(result_html, unsafe_allow_html=True)

            # --- التقرير والنتائج ---
            st.divider()
            if not errors:
                st.success("✅ هنيئاً لك! تلاوة متقنة لفظاً.")
            else:
                st.subheader("📋 تقرير الأداء التجويدي")
                cols = st.columns(min(len(errors), 3))
                for idx, err in enumerate(errors):
                    with cols[idx % 3]:
                        st.error(f"تحتاج مراجعة: {err}")
                        char = clean_strict(err)[0]
                        if char in MUKHRAJ_DATA:
                            st.info(f"📍 مخرج الحرف ({char}): {MUKHRAJ_DATA[char]['info']}")
                            st.write(f"💡 نصيحة: {MUKHRAJ_DATA[char]['tip']}")
                            # عرض صورة المخرج المناسبة
                            if char == "ق":
                                
                            elif char == "د":
                                
                            elif char == "ل":
                                

        except Exception as e:
            st.warning("لم نتمكن من تحليل الصوت بدقة، يرجى المحاولة في مكان هادئ.")
