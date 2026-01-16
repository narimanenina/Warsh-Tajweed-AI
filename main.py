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
st.set_page_config(page_title="مصحح ورش - طريق الأزرق", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-card {
        background-color: #f9fbf9; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-right: 8px solid #2E7D32;
        margin-bottom: 20px; color: #1B5E20;
    }
    .metric-box {
        background-color: white; padding: 15px; border-radius: 10px;
        border: 1px solid #c8e6c9; text-align: center;
    }
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 10px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل البيانات (بالأعمدة الجديدة) ---
@st.cache_data
def load_phonetics():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv')
    return None

df_phonetics = load_phonetics()

# --- 3. وظائف معالجة النصوص والتحليل ---

def normalize_text(text):
    """تنظيف النص للمقارنة العادلة"""
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"[\u064B-\u0652]", "", text) # حذف التشكيل
    return text.strip()

def get_rule_feedback(word):
    """البحث عن أحكام التجويد للحروف الموجودة في الكلمة المتعثرة"""
    feedback = []
    if df_phonetics is not None:
        for char in word:
            match = df_phonetics[df_phonetics['letter'] == char]
            if not match.empty:
                rule = match.iloc[0]['rule_category']
                place = match.iloc[0]['place']
                feedback.append(f"الحرف '{char}': حكمه ({rule}) ومخرجه ({place})")
    return list(set(feedback)) # حذف التكرار

# --- 4. واجهة المستخدم ---
st.title("🕌 مصحح التلاوة (ورش)")
st.subheader("تحليل الأداء بناءً على قواعد التجويد")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    user_name = st.text_input("اسم القارئ:", "طالب العلم")
    target_text = st.text_area("الآية المستهدفة:", "إنا أعطيناك الكوثر")
    if df_phonetics is not None:
        with st.expander("📊 قواعد البيانات المحملة"):
            st.write(df_phonetics)

# تسجيل الصوت
audio_data = mic_recorder(start_prompt="🔴 ابدأ التلاوة", stop_prompt="⏹️ توقف واطلب التحليل", key='recorder_v5')

if audio_data:
    audio_bytes = audio_data['bytes']
    
    with st.spinner("⏳ جاري تحليل التلاوة والأحكام..."):
        try:
            # تحويل الصوت ومعالجته
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            buf = io.BytesIO()
            audio.export(buf, format="wav")
            buf.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(buf) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # المقارنة
            norm_target = normalize_text(target_text)
            norm_spoken = normalize_text(spoken_text)
            
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)
            
            # عرض التقرير
            st.markdown("<div class='quran-card'>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align:center;'>دقة التلاوة: {accuracy}%</h2>", unsafe_allow_html=True)
            st.write(f"**النص المكتشف:** {spoken_text}")
            
            # استخراج الأخطاء وربطها بملف الـ CSV
            diff = list(difflib.ndiff(norm_target.split(), norm_spoken.split()))
            errors = [d[2:] for d in diff if d.startswith('- ')]
            
            if errors:
                st.warning("⚠️ تنبيهات تجويدية للكلمات المتعثرة:")
                for err_word in errors:
                    rules = get_rule_feedback(err_word)
                    if rules:
                        st.write(f"• الكلمة **'{err_word}'**: ")
                        for r in rules: st.write(f"   - {r}")
            else:
                st.balloons()
                st.success("أحسنت! تلاوة مطابقة للأحكام.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"حدث خطأ في التعرف على الصوت: {e}")
