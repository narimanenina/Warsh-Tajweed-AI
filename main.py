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
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

# --- 1. إعدادات الصفحة والجماليات ---
st.set_page_config(page_title="مقرأة ورش الذكية - نظام المحاكاة", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .st-emotion-cache-p4m61c { flex-direction: row-reverse !important; }
    .main-card {
        background-color: #fcfdfc; padding: 20px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .score-box { text-align:center; padding:15px; background-color:#e8f5e9; border-radius:12px; margin:10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل قاعدة بيانات الأحكام (CSV) ---
@st.cache_data
def load_warsh_data():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_warsh_data()

# --- 3. وظائف التحليل التقني ---

def get_tajweed_feedback(word):
    """استخراج أحكام التجويد من ملف CSV لكل حرف"""
    feedback = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                feedback.append({'الحرف': row['letter'], 'المخرج': row['place'], 'الحكم': row['rule_category'], 'الصفة': row['emphasis']})
    return feedback

def calculate_voice_similarity(teacher_bytes, student_bytes):
    """مقارنة البصمة الصوتية بين الشيخ والتلميذ باستخدام DTW"""
    # تحويل الملفات لصيغة متوافقة عبر pydub
    t_audio = AudioSegment.from_file(io.BytesIO(teacher_bytes)).set_frame_rate(22050).set_channels(1)
    s_audio = AudioSegment.from_file(io.BytesIO(student_bytes)).set_frame_rate(22050).set_channels(1)
    
    y_t = np.array(t_audio.get_array_of_samples(), dtype=np.float32)
    y_s = np.array(s_audio.get_array_of_samples(), dtype=np.float32)

    # استخراج مميزات رنين الحروف (MFCCs)
    mfcc_t = librosa.feature.mfcc(y=y_t, sr=22050)
    mfcc_s = librosa.feature.mfcc(y=y_s, sr=22050)
    
    # خوارزمية المقارنة الزمنية
    distance, _ = fastdtw(mfcc_t.T, mfcc_s.T, dist=euclidean)
    similarity = 100 / (1 + (distance / 50000)) 
    return round(similarity, 1)

def process_audio_for_stt(audio_bytes):
    """تحويل الصوت لمعالج التعرف على الكلام"""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    wav_buf = io.BytesIO()
    audio.export(wav_buf, format="wav")
    wav_buf.seek(0)
    return wav_buf

# --- 4. واجهة المستخدم الرئيسية ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 نظام المحاكاة وتصحيح التلاوة</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📖 ضبط الجلسة")
    target_text = st.text_area("الآية المراد التدرب عليها:", "إنا أعطيناك الكوثر")
    st.divider()
    st.subheader("👨‍🏫 المعلم المرجع")
    teacher_file = st.file_uploader("ارفع صوت الشيخ (اختياري):", type=['wav', 'mp3', 'ogg'])
    if teacher_file:
        st.audio(teacher_file)
        t_bytes = teacher_file.read()

# مساحة التسجيل
st.markdown("<div class='main-card'>", unsafe_allow_html=True)
st.subheader("🎤 تسجيل التلميذ")
student_rec = mic_recorder(start_prompt="ابدأ التلاوة / المحاكاة", stop_prompt="توقف واظهر النتيجة", key='final_warsh_v15')
st.markdown("</div>", unsafe_allow_html=True)

if student_rec:
    s_bytes = student_rec['bytes']
    
    with st.spinner("⏳ جاري تحليل مخارج الحروف ومطابقة الأداء..."):
        try:
            # 1. التعرف على النص والأحكام (المصحح الآلي)
            wav_buffer = process_audio_for_stt(s_bytes)
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # 2. حساب نسبة مطابقة النص
            norm_target = re.sub(r"[إأآا]", "ا", target_text)
            norm_spoken = re.sub(r"[إأآا]", "ا", spoken_text)
            text_acc = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # 3. عرض التقرير
            st.markdown("<div class='main-card'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"<div class='score-box'><h4>دقة الألفاظ</h4><h2>{text_acc}%</h2></div>", unsafe_allow_html=True)
            
            # إذا رفع المستخدم صوت الشيخ، نقوم بالمقارنة السمعية
            if teacher_file:
                voice_sim = calculate_voice_similarity(t_bytes, s_bytes)
                with col2:
                    st.markdown(f"<div class='score-box'><h4>محاكاة الشيخ</h4><h2>{voice_sim}%</h2></div>", unsafe_allow_html=True)
            
            st.write(f"**المنطوق:** {spoken_text}")
            
            # 4. تحليل الأحكام من الـ CSV
            st.divider()
            st.markdown("### 📋 التحليل التجويدي والمخارج (بناءً على ملفك):")
            words = target_text.split()
            for word in words:
                tajweed_data = get_tajweed_feedback(word)
                if tajweed_data:
                    with st.expander(f"📖 أحكام كلمة: {word}"):
                        st.dataframe(pd.DataFrame(tajweed_data), use_container_width=True, hide_index=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ تعذر التحليل: يرجى الترتيل بوضوح. (السبب: {e})")
