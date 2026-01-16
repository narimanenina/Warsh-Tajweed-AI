import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import soundfile as sf
from streamlit_mic_recorder import mic_recorder
from datetime import datetime

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="مصحح التلاوة الإلكتروني", layout="centered")

st.markdown("""
    <style>
    .quran-card {
        background-color: #f0f4f0; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-right: 5px solid #2E7D32;
        margin-bottom: 20px; color: #1B5E20; text-align: right; font-family: 'Amiri', serif;
    }
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 10px; }
    h1 { color: #1B5E20; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_phonetics():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv')
    return None

df_phonetics = load_phonetics()

# --- 2. دالة حفظ سجلات التلاوة ---
def save_recitation(user_name, surah, target, spoken, accuracy):
    db_file = 'recitation_history.csv'
    new_data = pd.DataFrame([{
        'الاسم': user_name,
        'السورة': surah,
        'النص المستهدف': target,
        'ما تمت قراءته': spoken,
        'الدقة': f"{accuracy}%",
        'التاريخ': datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    if os.path.exists(db_file):
        new_data.to_csv(db_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        new_data.to_csv(db_file, index=False, encoding='utf-8-sig')

# --- 3. محرك تحليل التلاوة ---
def analyze_recitation(target, spoken):
    target_words = target.split()
    spoken_words = spoken.split()
    
    matcher = difflib.SequenceMatcher(None, target_words, spoken_words)
    accuracy = round(matcher.ratio() * 100, 1)
    
    report = []
    diff = list(difflib.ndiff(target_words, spoken_words))
    
    for word in diff:
        if word.startswith('- '):
            report.append(f"❌ **خطأ في اللفظ أو نقص:** {word[2:]}")
        elif word.startswith('+ '):
            report.append(f"⚠️ **زيادة في القراءة:** {word[2:]}")
            
    return report, accuracy

# --- 4. واجهة المستخدم ---
st.title("🕌 مصحح التلاوة التفاعلي")
st.subheader("تحسين التلاوة باستخدام الذكاء الاصطناعي")

with st.sidebar:
    st.header("⚙️ إعدادات الجلسة")
    user_name = st.text_input("اسم القارئ:")
    surah_name = st.selectbox("اختر السورة:", ["الفاتحة", "الإخلاص", "الفلق", "الناس", "نص حر"])
    target_text = st.text_area("الآية المستهدفة:", placeholder="اكتب الآية هنا أو اختر سورة...")

# تعبئة تلقائية لبعض السور كمثال
if surah_name == "الإخلاص" and not target_text:
    target_text = "قل هو الله أحد الله الصمد لم يلد ولم يولد ولم يكن له كفوا أحد"

st.info("💡 نصيحة: حاول الترتيل بوضوح لتحسين دقة التعرف على الحروف.")

# تسجيل الصوت
audio_data = mic_recorder(start_prompt="🔴 ابدأ التلاوة", stop_prompt="⏹️ توقف", key='recorder')

if audio_data:
    audio_bytes = audio_data['bytes']
    st.audio(audio_bytes, format='audio/wav')
    
    with st.spinner("⏳ جاري تحليل التلاوة..."):
        # تحويل الصوت لنص
        buf = io.BytesIO(audio_bytes)
        r = sr.Recognizer()
        spoken_text = ""
        try:
            with sr.AudioFile(buf) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            st.success(f"الكلمات المكتشفة: **{spoken_text}**")
            
            if target_text:
                report, acc = analyze_recitation(target_text, spoken_text)
                
                # عرض النتيجة
                st.markdown(f"""
                <div class='quran-card'>
                    <h3>📊 نتيجة التلاوة</h3>
                    <p>نسبة المطابقة اللفظية: <b>{acc}%</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                if report:
                    st.warning("⚠️ ملاحظات على التلاوة:")
                    for item in report:
                        st.write(item)
                else:
                    st.balloons()
                    st.success("ما شاء الله! تلاوة مطابقة للنص.")

                if st.button("💾 حفظ في سجل المتابعة"):
                    save_recitation(user_name, surah_name, target_text, spoken_text, acc)
                    st.info("تم حفظ التقرير في سجل الانجازات.")
                    
        except Exception as e:
            st.error("⚠️ عذراً، تعذر معالجة الصوت. يرجى التأكد من جودة الميكروفون.")
