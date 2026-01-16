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

# --- 1. إعدادات الصفحة والهوية البصرية ---
st.set_page_config(page_title="مصحح تلاوة ورش - طريق الأزرق", layout="centered")

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
    h1 { color: #1B5E20; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل البيانات (بالأعمدة المحددة) ---
@st.cache_data
def load_phonetics():
    if os.path.exists('arabic_phonetics.csv'):
        # قراءة الملف الذي يحتوي على (letter, name, place, rule_category, emphasis, ipa)
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_phonetics()

# --- 3. وظائف التحليل والذكاء الاصطناعي ---

def normalize_text(text):
    """تنظيف النص للمقارنة العادلة (تجاهل الهمزات والتشكيل)"""
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"[\u064B-\u0652]", "", text) 
    return text.strip()

def get_phonetic_info(word):
    """استخراج بيانات الأحكام والمخارج لكل حرف في الكلمة من ملف CSV"""
    info_list = []
    if df_rules is not None:
        for char in word:
            # البحث عن الحرف في عمود letter
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                info_list.append({
                    'الحرف': row['letter'],
                    'الاسم': row['name'],
                    'المخرج': row['place'],
                    'الحكم': row['rule_category'],
                    'الصفة': row['emphasis']
                })
    return info_list

# --- 4. واجهة المستخدم ---
st.title("🕌 مصحح تلاوة ورش")
st.subheader("تحليل الأحكام والمخارج بناءً على قواعد البيانات")

# عرض صور الأحكام والمخارج إذا كان هناك مرجع (اختياري)


with st.sidebar:
    st.header("⚙️ الإعدادات")
    target_text = st.text_area("الآية المستهدفة:", "إنا أعطيناك الكوثر")
    
    if df_rules is not None:
        with st.expander("📄 عرض بيانات الأحكام (CSV)"):
            st.dataframe(df_rules)

# تسجيل الصوت ومعالجته
audio_data = mic_recorder(start_prompt="🔴 ابدأ التلاوة", stop_prompt="⏹️ توقف واطلب التحليل", key='warsh_v6')

if audio_data:
    audio_bytes = audio_data['bytes']
    
    with st.spinner("⏳ جاري تحليل التلاوة وربطها بالأحكام..."):
        try:
            # تحويل الصوت لضمان الجودة
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            buf = io.BytesIO()
            audio.export(buf, format="wav")
            buf.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(buf) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # المقارنة النصية
            norm_target = normalize_text(target_text)
            norm_spoken = normalize_text(spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)
            
            # عرض النتائج
            st.markdown("<div class='quran-card'>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align:center;'>نسبة الإتقان: {accuracy}%</h2>", unsafe_allow_html=True)
            st.write(f"**النص المكتشف:** {spoken_text}")
            
            # تحليل الأحكام والمخارج للكلمات
            st.divider()
            st.subheader("📝 التحليل الصوتي (بناءً على ملف CSV):")
            
            words = target_text.split()
            for word in words:
                clean_word = re.sub(r"[\u064B-\u0652]", "", word)
                phonetics = get_phonetic_info(clean_word)
                
                with st.expander(f"تحليل كلمة: {word}"):
                    if phonetics:
                        # عرض البيانات في جدول لكل كلمة
                        temp_df = pd.DataFrame(phonetics)
                        st.table(temp_df)
                    else:
                        st.write("بيانات الحروف غير متوفرة في الملف.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ حدث خطأ: يرجى التأكد من وضوح الصوت. (التفاصيل: {e})")
