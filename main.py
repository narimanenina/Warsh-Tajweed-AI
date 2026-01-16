import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import numpy as np
import re
import soundfile as sf
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الواجهة (هوية بصرية إسلامية) ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-box {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 8px solid #2E7D32; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .metric-card { background-color: white; padding: 15px; border-radius: 12px; border: 1px solid #e0e0e0; text-align: center; }
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 10px; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل البيانات في الخلفية ---
@st.cache_data
def load_rules():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_rules()

# --- 3. وظائف التحليل الذكي ---

def normalize_arabic(text):
    """توحيد الحروف لتجنب أخطاء الهمزات والتشكيل"""
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"[\u064B-\u0652]", "", text) # إزالة التشكيل
    return text.strip()

def analyze_mad_duration(audio_bytes):
    """تحليل طول المد المشبع (6 حركات عند ورش)"""
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        buf.seek(0)
        y, sr_rate = librosa.load(buf)
        rms = librosa.feature.rms(y=y)[0]
        # حساب أطول فترة استمرار صوتي
        threshold = np.max(rms) * 0.25
        durations = []
        count = 0
        for s in (rms > threshold):
            if s: count += 1
            else:
                if count > 0: durations.append(count * (512 / sr_rate))
                count = 0
        return round(max(durations), 2) if durations else 0, buf
    except:
        return 0, io.BytesIO(audio_bytes)

def get_word_tajweed(word):
    """استخراج الأحكام لكل حرف من ملف CSV المخفي"""
    insights = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                insights.append({
                    'الحرف': row['letter'],
                    'المخرج': row['place'],
                    'الحكم': row['rule_category'],
                    'الصفة': row['emphasis']
                })
    return insights

# --- 4. واجهة المستخدم الرئيسية ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مقرأة ورش الإلكترونية</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>تصحيح التلاوة، المخارج، والمدود المشبعة (طريق الأزرق)</p>", unsafe_allow_html=True)



with st.sidebar:
    st.header("📖 إعدادات الجلسة")
    target_text = st.text_area("الآية المراد تصحيحها:", "إنا أعطيناك الكوثر")
    st.info("💡 يتم استخدام قاعدة بيانات الأحكام في الخلفية لتحليل مخارج حروفك.")

# تسجيل الصوت
audio_data = mic_recorder(start_prompt="🎤 ابدأ التلاوة بالترتيل", stop_prompt="⏹️ توقف واطلب التقرير", key='warsh_v8')

if audio_data:
    audio_bytes = audio_data['bytes']
    
    with st.spinner("⏳ جاري تحليل الأحكام والمخارج..."):
        try:
            # التحليل الصوتي (المد)
            mad_time, wav_buffer = analyze_mad_duration(audio_bytes)
            
            # التعرف على النص
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # حساب الدقة اللفظية
            norm_target = normalize_arabic(target_text)
            norm_spoken = normalize_arabic(spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # --- عرض التقرير ---
            st.markdown("<div class='quran-box'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            col1.markdown(f"<div class='metric-card'><h4>دقة مخارج الحروف</h4><h2 style='color:#2E7D32;'>{accuracy}%</h2></div>", unsafe_allow_html=True)
            col2.markdown(f"<div class='metric-card'><h4>زمن أطول مد</h4><h2 style='color:#2E7D32;'>{mad_time} ث</h2></div>", unsafe_allow_html=True)
            
            st.write(f"**النص المكتشف:** {spoken_text}")
            
            # تحليل الأحكام لكل كلمة بناءً على CSV
            st.subheader("📋 التحليل التجويدي للمقاطع:")
            words = target_text.split()
            for word in words:
                tajweed_info = get_word_tajweed(word)
                if tajweed_info:
                    with st.expander(f"أحكام كلمة: {word}"):
                        st.table(pd.DataFrame(tajweed_info))
            
            if accuracy > 85:
                if mad_time >= 3.0:
                    st.success("ما شاء الله! تلاوة مطابقة لرواية ورش مع إشباع للمد.")
                    st.balloons()
                else:
                    st.warning("اللفظ صحيح، لكن زمن المد قصير (ورش يمد المشبع 6 حركات).")
            else:
                st.error("يوجد خطأ في نطق الكلمات، راجع المخارج والأحكام الموضحة أعلاه.")
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error("عذراً، لم نتمكن من تحليل التلاوة بوضوح. يرجى الترتيل بالقرب من الميكروفون والتأكد من وضوح الصوت.")
