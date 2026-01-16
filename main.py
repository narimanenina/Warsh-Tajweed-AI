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
st.set_page_config(page_title="مصحح تلاوة ورش الشامل", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-container {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .tajweed-tile { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل الأحكام من CSV (في الخلفية) ---
@st.cache_data
def load_rules():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_rules()

# --- 3. وظائف التحليل التقني ---

def get_tajweed_feedback(word):
    """ربط الكلمة ببيانات الحروف من ملف CSV (الحكم، المخرج، الصفة)"""
    feedback = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                feedback.append({
                    'الحرف': row['letter'],
                    'الحكم': row['rule_category'],
                    'المخرج': row['place'],
                    'الصفة': row['emphasis']
                })
    return feedback

def analyze_audio_mad(audio_bytes):
    """تحليل الإشارة الصوتية لاكتشاف زمن المد (6 حركات لورش)"""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    buf.seek(0)
    y, sr_rate = librosa.load(buf)
    rms = librosa.feature.rms(y=y)[0]
    # حساب أطول استمرار صوتي فوق عتبة معينة
    threshold = np.max(rms) * 0.3
    durations = np.sum(rms > threshold) * (512 / sr_rate)
    return round(durations, 2), buf

# --- 4. واجهة المستخدم ---
st.title("🕌 مصحح التلاوة التفاعلي (رواية ورش)")
st.write("يتم الآن تحليل المخارج والأحكام بناءً على قاعدة بياناتك المرجعية.")



with st.sidebar:
    st.header("⚙️ الضبط")
    target_text = st.text_area("الآية المستهدفة:", "إنا أعطيناك الكوثر")

audio_data = mic_recorder(start_prompt="🎤 ابدأ التلاوة بالترتيل", stop_prompt="⏹️ توقف لمعرفة الأحكام", key='tajweed_checker')

if audio_data:
    audio_bytes = audio_data['bytes']
    with st.spinner("⏳ جاري تحليل الأحكام والمخارج..."):
        try:
            # التحليل الصوتي واللفظي
            mad_time, wav_buf = analyze_audio_mad(audio_bytes)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                r.adjust_for_ambient_noise(source)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # عرض التقرير
            st.markdown("<div class='quran-container'>", unsafe_allow_html=True)
            st.subheader(f"النتيجة: {spoken_text}")
            
            # تصحيح الأحكام والمخارج
            st.divider()
            st.markdown("### 📋 تحليل أحكام التجويد لكل كلمة:")
            words = target_text.split()
            for word in words:
                tajweed_info = get_tajweed_feedback(word)
                with st.expander(f"توجيهات كلمة: {word}"):
                    if tajweed_info:
                        st.table(pd.DataFrame(tajweed_info))
            
            # تقييم المد لورش
            if mad_time < 3.0:
                st.warning(f"⚠️ زمن المد المكتشف ({mad_time} ث) قصير. تذكر إشباع المد لـ 6 حركات عند ورش.")
            else:
                st.success(f"✅ زمن المد ({mad_time} ث) ممتاز ويتوافق مع طريق الأزرق.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error("تعذر التحليل. يرجى الترتيل بوضوح وثبات أمام الميكروفون.")
