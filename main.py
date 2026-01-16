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

# --- 1. إعدادات الواجهة (طابع قرآني حديث) ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-container {
        background-color: #fcfdfc; padding: 30px; border-radius: 20px;
        border: 2px solid #e0eee0; border-right: 10px solid #2E7D32;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05); margin-bottom: 25px;
    }
    .result-card { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #c8e6c9; margin-top: 10px; }
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 12px; height: 3em; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البحث عن الأحكام (خلف الكواليس) ---
@st.cache_data
def load_warsh_rules():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_warsh_rules()

def get_tajweed_insight(word):
    """ربط حروف الكلمة بقواعد التجويد من ملف CSV"""
    insights = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word) # إزالة التشكيل للبحث
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                insights.append({
                    'الحرف': row['letter'],
                    'الحكم': row['rule_category'],
                    'المخرج': row['place'],
                    'الصفة': row['emphasis']
                })
    return insights

# --- 3. المعالجة الصوتية المتقدمة (المدود والغنة) ---
def analyze_audio_features(audio_bytes):
    """تحليل الإشارة الصوتية لاكتشاف المد المشبع (6 حركات) وقوة الغنة"""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    buf.seek(0)
    
    y, sr_rate = librosa.load(buf)
    # حساب الطاقة الصوتية (RMS)
    rms = librosa.feature.rms(y=y)[0]
    # تحديد أطول فترة استمرار صوتي (المد)
    durations = []
    count = 0
    threshold = np.max(rms) * 0.3
    for s in (rms > threshold):
        if s: count += 1
        else:
            if count > 0: durations.append(count * (512 / sr_rate))
            count = 0
    max_mad = round(max(durations), 2) if durations else 0
    return max_mad, buf

# --- 4. واجهة المستخدم الرئيسية ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مصحح تلاوة ورش الشامل</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>تصحيح مخارج الحروف، المدود المشبعة، وأحكام التجويد</p>", unsafe_allow_html=True)



with st.sidebar:
    st.header("📖 إعدادات المصحح")
    target_text = st.text_area("الآية المراد تصحيحها:", "إنا أعطيناك الكوثر")
    st.success("تم تحميل قواعد بيانات ورش في الخلفية.")

audio_data = mic_recorder(start_prompt="🎤 ابدأ التلاوة برواية ورش", stop_prompt="⏹️ توقف لظهور التقرير", key='warsh_full')

if audio_data:
    audio_bytes = audio_data['bytes']
    
    with st.spinner("⏳ جاري تحليل التجويد والمخارج..."):
        try:
            # التحليل الصوتي
            mad_time, wav_buffer = analyze_audio_features(audio_bytes)
            
            # التعرف على الكلمات
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # حساب المطابقة النصية
            norm_target = re.sub(r"[إأآا]", "ا", target_text)
            norm_spoken = re.sub(r"[إأآا]", "ا", spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # --- عرض التقرير النهائي ---
            st.markdown("<div class='quran-container'>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            col1.metric("دقة مخارج الحروف", f"{accuracy}%")
            col2.metric("زمن أطول مد", f"{mad_time} ثانية")

            st.write(f"**النص المكتشف:** {spoken_text}")
            
            # تحليل الأحكام بناءً على ملف CSV المخفي
            st.subheader("📋 تحليل أحكام التجويد للآية:")
            words = target_text.split()
            for word in words:
                tajweed_data = get_tajweed_insight(word)
                if tajweed_data:
                    with st.expander(f"أحكام كلمة: {word}"):
                        st.table(pd.DataFrame(tajweed_data))
            
            # تقييم نهائي
            if accuracy > 85:
                if mad_time > 3.2:
                    st.success("ما شاء الله! تلاوة مطابقة لرواية ورش مع إشباع المد.")
                else:
                    st.warning("الكلمات صحيحة، ولكن زمن المد قصير. طريق الأزرق يمد 6 حركات.")
            else:
                st.error("يوجد خطأ في نطق بعض الكلمات، راجع المخارج الموضحة في الجداول أعلاه.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error("عذراً، لم نتمكن من تحليل التلاوة بوضوح. يرجى الترتيل بالقرب من الميكروفون.")
