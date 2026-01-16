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

# --- 1. إعدادات الصفحة والجماليات ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-container {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 10px; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل البيانات في الخلفية ---
@st.cache_data
def load_warsh_data():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_warsh_data()

# --- 3. وظائف التحليل والتصحيح ---

def get_tajweed_feedback(word):
    """يربط الكلمة ببيانات الحروف من ملف CSV المخفي"""
    feedback = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                feedback.append({
                    'الحرف': row['letter'], 'المخرج': row['place'],
                    'الحكم': row['rule_category'], 'الصفة': row['emphasis']
                })
    return feedback

def process_audio(audio_bytes):
    """تحويل الصوت من أي صيغة إلى WAV PCM وتحليله"""
    # تحويل البايتات إلى ملف صوتي باستخدام pydub (يحل مشكلة التنسيق)
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    wav_buf = io.BytesIO()
    audio.export(wav_buf, format="wav")
    wav_buf.seek(0)
    
    # تحميل البيانات لتحليل المد عبر librosa
    y, sr_rate = librosa.load(wav_buf)
    rms = librosa.feature.rms(y=y)[0]
    threshold = np.max(rms) * 0.25
    mad_duration = np.sum(rms > threshold) * (512 / sr_rate)
    
    wav_buf.seek(0)
    return round(mad_duration, 2), wav_buf

# --- 4. واجهة المستخدم ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مقرأة ورش الإلكترونية</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ الضبط")
    target_text = st.text_area("الآية المراد تصحيحها:", "إنا أعطيناك الكوثر")
    st.info("💡 يتم استخدام ملف CSV كخبير تجويد في الخلفية.")

audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة بالترتيل", stop_prompt="⏹️ توقف واطلب التصحيح", key='warsh_v11')

if audio_record:
    audio_bytes = audio_record['bytes']
    
    with st.spinner("⏳ جاري معالجة الصوت وتحليل الأحكام..."):
        try:
            # معالجة التنسيق وحساب المد
            mad_time, wav_buffer = process_audio(audio_bytes)
            
            # التعرف على النص
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # عرض النتائج
            st.markdown("<div class='quran-container'>", unsafe_allow_html=True)
            st.subheader(f"المنطوق: {spoken_text}")
            
            # تصحيح الأحكام والمخارج بناءً على ملف CSV
            st.divider()
            st.markdown("### 📋 تحليل أحكام التجويد (بناءً على ملفك):")
            words = target_text.split()
            for word in words:
                tajweed_info = get_tajweed_feedback(word)
                if tajweed_info:
                    with st.expander(f"أحكام ومخارج كلمة: {word}"):
                        st.table(pd.DataFrame(tajweed_info))
            
            # تقييم المد لورش
            if mad_time < 3.0:
                st.warning(f"⚠️ زمن المد المكتشف ({mad_time} ث) قصير. تذكر إشباع المد لـ 6 حركات عند ورش.")
            else:
                st.success(f"✅ إتقان ممتاز! زمن المد ({mad_time} ث) يتوافق مع طريق الأزرق.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ تعذر التحليل: يرجى التأكد من تثبيت ffmpeg والترتيل بوضوح. (السبب: {e})")
