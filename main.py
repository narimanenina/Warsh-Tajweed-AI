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

# --- 1. الإعدادات البصرية ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-box {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .metric-card { background-color: white; padding: 15px; border-radius: 12px; border: 1px solid #e0e0e0; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. وظائف التحميل والمعالجة (الخلفية) ---
@st.cache_data
def load_rules():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_rules()

def normalize_arabic(text):
    """توحيد الحروف لزيادة دقة المطابقة"""
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"[\u064B-\u0652]", "", text) # حذف التشكيل
    return text.strip()

def get_word_analysis(word):
    """ربط الكلمة بالأحكام والمخارج من ملف CSV"""
    analysis = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                analysis.append({
                    'الحرف': row['letter'],
                    'المخرج': row['place'],
                    'الحكم': row['rule_category'],
                    'الصفة': row['emphasis']
                })
    return analysis

# --- 3. واجهة المستخدم ---
st.title("🕌 مقرأة ورش الإلكترونية الشاملة")
st.write("نظام تصحيح التلاوة والمخارج والأحكام")



with st.sidebar:
    st.header("📖 خيارات التصحيح")
    target_text = st.text_area("الآية المراد تصحيحها:", "إنا أعطيناك الكوثر")
    st.info("💡 يتم استخدام ملف الأحكام (CSV) لتحليل مخارج حروفك في الخلفية.")

# تسجيل الصوت
audio_data = mic_recorder(start_prompt="🎤 ابدأ التلاوة", stop_prompt="⏹️ توقف واطلب التقرير", key='warsh_v9')

if audio_data:
    audio_bytes = audio_data['bytes']
    
    with st.spinner("⏳ جاري تحليل الأحكام والمخارج..."):
        try:
            # تحويل الصوت لصيغة WAV PCM لضمان فهم المحرك له
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_buf = io.BytesIO()
            audio.export(wav_buf, format="wav")
            wav_buf.seek(0)
            
            # التعرف على الكلام
            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                # تقليل أثر الضجيج لضمان التحليل
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # حساب الدقة اللفظية
            norm_target = normalize_arabic(target_text)
            norm_spoken = normalize_arabic(spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # عرض النتائج
            st.markdown("<div class='quran-box'>", unsafe_allow_html=True)
            st.metric("نسبة إتقان المخارج", f"{accuracy}%")
            st.write(f"**النص المكتشف:** {spoken_text}")
            
            # التحليل التفصيلي للأحكام
            st.subheader("📋 تحليل الحروف والأحكام (بناءً على ملفك المرجعي):")
            words = target_text.split()
            for word in words:
                tajweed_info = get_word_analysis(word)
                if tajweed_info:
                    with st.expander(f"تفاصيل كلمة: {word}"):
                        st.table(pd.DataFrame(tajweed_info))
            
            if accuracy > 85:
                st.success("ما شاء الله! تلاوة صحيحة.")
                st.balloons()
            else:
                st.error("يوجد اختلاف في نطق الكلمات، يرجى مراجعة مخارج الحروف أعلاه.")
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error("لم يتمكن النظام من معالجة الصوت. حاول القراءة بوضوح أكبر أو تأكد من إعدادات الميكروفون.")
