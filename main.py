import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. تحميل بيانات الحروف من ملف CSV ---
@st.cache_data
def load_phonetics_data():
    try:
        # تأكد من وجود ملف arabic_phonetics.csv في نفس المجلد
        return pd.read_csv('arabic_phonetics.csv')
    except:
        return None

df_phonetics = load_phonetics_data()

# --- 2. إعدادات الواجهة ---
st.set_page_config(page_title="مختبر التجويد - ورش", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quiz-card {
        background-color: #f0f7f4; padding: 30px; border-radius: 20px;
        border: 2px dashed #2E7D32; margin: 20px auto; max-width: 600px;
    }
    .char-display { font-size: 80px; color: #1B5E20; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🕌 مختبر مخارج الحروف (رواية ورش)")

# --- 3. اختيار نوع الاختبار ---
tab1, tab2 = st.tabs(["📖 تصحيح سورة", "🎯 اختبار الحروف المنفردة"])

with tab2:
    st.subheader("اختبر دقة نطقك لمخارج الحروف")
    
    if df_phonetics is not None:
        selected_char = st.selectbox("اختر الحرف الذي تريد التدرب عليه:", df_phonetics['letter'].unique())
        
        char_info = df_phonetics[df_phonetics['letter'] == selected_char].iloc[0]
        
        st.markdown(f"""
        <div class='quiz-card'>
            <div class='char-display'>{selected_char}</div>
            <p>المخرج: <b>{char_info['place']}</b></p>
            <p>الصفة: <b>{char_info['emphasis']}</b></p>
            <p>الحكم لورش: <b>{char_info['rule_category']}</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.write(f"انطق حرف (**{selected_char}**) بوضوح مع السكون أو الحركة")
        
        quiz_audio = mic_recorder(start_prompt="🎤 ابدأ تسجيل الحرف", stop_prompt="⏹️ تحليل النطق", key='quiz_mic')

        if quiz_audio:
            with st.spinner("⏳ جاري تحليل مخرج الحرف..."):
                try:
                    audio_bytes = quiz_audio['bytes']
                    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
                    wav_buf = io.BytesIO()
                    audio.export(wav_buf, format="wav")
                    wav_buf.seek(0)

                    r = sr.Recognizer()
                    with sr.AudioFile(wav_buf) as source:
                        audio_data = r.record(source)
                        # محاولة التعرف على الحرف المنطوق
                        spoken_result = r.recognize_google(audio_data, language="ar-SA")
                    
                    # تنظيف النتيجة
                    clean_spoken = re.sub(r"[\u064B-\u0652]", "", spoken_result).strip()

                    if selected_char in clean_spoken:
                        st.success(f"✅ أحسنت! تم التعرف على حرف ({selected_char}) بنجاح.")
                        st.balloons()
                    else:
                        st.error(f"❌ لم يتم التعرف على الحرف بدقة. تأكد من إخراجه من {char_info['place']}.")
                        st.info(f"💡 نصيحة لورش: {char_info['rule_category']}")
                
                except Exception as e:
                    st.warning("حاول نطق الحرف بشكل أوضح أو في بيئة أهدأ.")
    else:
        st.error("لم يتم العثور على ملف arabic_phonetics.csv. يرجى رفعه في مجلد المشروع.")

# الجزء الأول (تصحيح السورة) يبقى كما هو في الكود السابق
with tab1:
    st.info("هذا القسم مخصص لقراءة السور الكاملة كما في النسخة السابقة.")
