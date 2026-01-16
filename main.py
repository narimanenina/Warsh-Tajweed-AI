import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import librosa
import numpy as np
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="مدرسة بلال العيناوي الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-box { background-color: #f0f4f0; padding: 25px; border-radius: 15px; border-right: 10px solid #2E7D32; }
    .highlight { color: #2E7D32; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. دالة المقارنة السمعية (المحاكاة) ---
def compare_to_teacher(teacher_bytes, student_bytes):
    # تحويل البصمة الصوتية للشيخ والتلميذ
    y_t, sr_t = librosa.load(io.BytesIO(teacher_bytes), sr=22050)
    y_s, sr_s = librosa.load(io.BytesIO(student_bytes), sr=22050)
    
    # استخراج رنين الحروف
    mfcc_t = librosa.feature.mfcc(y=y_t, sr=sr_t)
    mfcc_s = librosa.feature.mfcc(y=y_s, sr=sr_s)
    
    # حساب المسافة بين الأداءين
    distance, _ = fastdtw(mfcc_t.T, mfcc_s.T, dist=euclidean)
    similarity = 100 / (1 + (distance / 45000)) # نسبة تقريبية للمحاكاة
    return round(similarity, 1)

# --- 3. واجهة المستخدم ---
st.title("🕌 مدرسة القارئ بلال العيناوي")
st.write("تدرّب على محاكاة أداء القارئ بلال العيناوي والحصول على تقييم فوري.")

with st.sidebar:
    st.header("🎵 اختيار الآية المرجعية")
    # هنا يمكنك وضع روابط لملفات صوتية حقيقية لبلال العيناوي أو رفعها يدوياً
    sample_options = {
        "سورة الفاتحة - بلال العيناوي": "fatiah_bilal.wav",
        "سورة الكوثر - بلال العيناوي": "kawthar_bilal.wav"
    }
    choice = st.selectbox("اختر التسجيل المرجعي:", list(sample_options.keys()))
    
    # خيار رفع ملف الشيخ يدوياً
    uploaded_teacher = st.file_uploader("أو ارفع ملف القارئ بلال العيناوي (WAV/MP3):")

# التحقق من وجود ملف الشيخ
teacher_data = None
if uploaded_teacher:
    teacher_data = uploaded_teacher.read()
    st.audio(teacher_data)
else:
    st.info("قم برفع ملف القارئ بلال العيناوي لتبدأ المقارنة السمعية.")

# تسجيل التلميذ
st.subheader("🎤 سجل تلاوتك الآن محاكياً الشيخ:")
student_rec = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="إيقاف وطلب النتيجة", key='bilal_mimic')

if student_rec and teacher_data:
    student_bytes = student_rec['bytes']
    
    with st.spinner("⏳ جاري تحليل مخارج الحروف ومطابقتها بصوت بلال العيناوي..."):
        try:
            # المقارنة السمعية
            sim_score = compare_to_teacher(teacher_data, student_bytes)
            
            st.markdown("<div class='quran-box'>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align:center;'>نسبة محاكاة الشيخ بلال: <span class='highlight'>{sim_score}%</span></h2>", unsafe_allow_html=True)
            
            # نصائح بناءً على الأداء
            if sim_score > 85:
                st.success("أحسنت! أداءك قريب جداً من نبرة ومخارج الشيخ بلال العيناوي.")
            elif sim_score > 60:
                st.warning("أداء جيد، حاول التركيز على أزمنة المدود وتفخيم اللامات كما يفعل الشيخ.")
            else:
                st.error("هناك اختلاف في رنين الحروف، استمع للشيخ جيداً وحاول التقليد مرة أخرى.")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"حدث خطأ أثناء المقارنة: {e}")
