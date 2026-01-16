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

# --- 1. إعدادات الواجهة الاحترافية ---
st.set_page_config(page_title="مقرأة ورش الشاملة", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { 
        font-family: 'Amiri', serif; direction: rtl; text-align: right; 
    }
    .st-emotion-cache-p4m61c { flex-direction: row-reverse !important; }
    .quran-container {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .stButton>button { 
        background-color: #2E7D32; color: white; border-radius: 10px; 
        width: 100%; height: 3.5em; font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البحث عن الأحكام (خلف الكواليس) ---
@st.cache_data
def load_warsh_data():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_warsh_data()

def get_tajweed_feedback(word):
    """تحليل الكلمة وربطها بالأحكام والمخارج بناءً على ملف CSV"""
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

# --- 3. وظيفة معالجة وتحويل الصوت ---
def process_audio_v14(audio_bytes):
    # استخدام pydub لضمان تحويل أي تنسيق إلى WAV PCM صالح للتحليل
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    wav_buf = io.BytesIO()
    audio.export(wav_buf, format="wav")
    wav_buf.seek(0)
    
    # تحليل زمن الصوت (للمد المشبع 6 حركات)
    y, sr_rate = librosa.load(wav_buf)
    rms = librosa.feature.rms(y=y)[0]
    threshold = np.max(rms) * 0.25
    mad_duration = np.sum(rms > threshold) * (512 / sr_rate)
    
    wav_buf.seek(0)
    return round(mad_duration, 2), wav_buf

# --- 4. واجهة المستخدم ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مصحح تلاوة ورش الشامل</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>تصحيح المخارج، القلقلة، الغنة، وأحكام المد</p>", unsafe_allow_html=True)



with st.sidebar:
    st.header("⚙️ الضبط")
    target_text = st.text_area("الآية المستهدفة:", "إنا أعطيناك الكوثر")
    st.info("💡 يتم استخدام ملف CSV كمرجع للأحكام في الخلفية.")

audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة بالترتيل", stop_prompt="⏹️ توقف واطلب التصحيح", key='warsh_v14')

if audio_record:
    audio_bytes = audio_record['bytes']
    
    with st.spinner("⏳ جاري تحليل الأحكام والمخارج..."):
        try:
            # 1. المعالجة والتحويل
            mad_time, wav_buffer = process_audio_v14(audio_bytes)
            
            # 2. التعرف على النص عبر جوجل
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                r.adjust_for_ambient_noise(source)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # 3. المقارنة اللفظية الذكية
            norm_target = re.sub(r"[إأآا]", "ا", target_text)
            norm_spoken = re.sub(r"[إأآا]", "ا", spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # --- عرض التقرير النهائي ---
            st.markdown("<div class='quran-container'>", unsafe_allow_html=True)
            st.subheader(f"نسبة الإتقان: {accuracy}%")
            st.write(f"**المنطوق:** {spoken_text}")
            
            st.divider()
            st.markdown("### 📋 التحليل التفصيلي لجميع الأحكام:")
            
            words = target_text.split()
            for word in words:
                tajweed_data = get_tajweed_feedback(word)
                if tajweed_data:
                    # expander مع منع تداخل الكتابة مع الأيقونة
                    with st.expander(f"📖 أحكام ومخارج كلمة: {word}"):
                        st.dataframe(pd.DataFrame(tajweed_data), use_container_width=True, hide_index=True)
            
            # تقييم زمن المد لورش
            if mad_time < 3.0:
                st.warning(f"⚠️ تنبيه تجويدي: زمن المد ({mad_time} ث) قصير. تذكر إشباع المد لـ 6 حركات.")
            else:
                st.success(f"✅ إتقان ممتاز! زمن المد ({mad_time} ث) يتوافق مع رواية ورش.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ تعذر التحليل: يرجى القراءة بوضوح أو التأكد من إعدادات الميكروفون. (السبب: {e})")
