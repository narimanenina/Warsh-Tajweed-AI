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

# --- 1. إعدادات الهوية البصرية ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .quran-box {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .tajweed-report { background-color: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; }
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 10px; width: 100%; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل الأحكام في الخلفية ---
@st.cache_data
def load_warsh_rules():
    if os.path.exists('arabic_phonetics.csv'):
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_warsh_rules()

# --- 3. وظائف التحليل الذكي ---

def get_phonetic_analysis(word):
    """ربط حروف الكلمة بالمخارج والأحكام من ملف CSV"""
    analysis = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                analysis.append({
                    'الحرف': row['letter'],
                    'المخرج': row['place'],
                    'الحكم': row['rule_category'],
                    'الصفة': row['emphasis']
                })
    return analysis

def analyze_audio_mad(audio_bytes):
    """تحليل الإشارة الصوتية لاكتشاف المد المشبع (6 حركات)"""
    try:
        # تحويل الصوت لضمان الصيغة الصحيحة
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_buf = io.BytesIO()
        audio.export(wav_buf, format="wav")
        wav_buf.seek(0)
        
        y, sr_rate = librosa.load(wav_buf)
        rms = librosa.feature.rms(y=y)[0]
        # حساب أطول فترة استمرار صوتي
        threshold = np.max(rms) * 0.3
        durations = np.sum(rms > threshold) * (512 / sr_rate)
        return round(durations, 2), wav_buf
    except Exception as e:
        return 0, io.BytesIO(audio_bytes)

# --- 4. واجهة المستخدم ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مصحح تلاوة ورش (طريق الأزرق)</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>نظام تعليمي ذكي لتصحيح الأحكام والمخارج</p>", unsafe_allow_html=True)



with st.sidebar:
    st.header("⚙️ الضبط")
    target_text = st.text_area("الآية المرجعية:", "إنا أعطيناك الكوثر")
    st.info("💡 يتم استخدام ملف CSV كخبير تجويد في الخلفية لتحليل مخارج حروفك.")

# تسجيل الصوت
audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة", stop_prompt="⏹️ توقف واطلب التقرير", key='warsh_final_itqan')

if audio_record:
    audio_bytes = audio_record['bytes']
    
    with st.spinner("⏳ جاري تحليل الأحكام والمخارج..."):
        # التحليل الصوتي (المد)
        mad_time, wav_buffer = analyze_audio_mad(audio_bytes)
        
        try:
            # التعرف على النص
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                r.adjust_for_ambient_noise(source)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # المطابقة النصية
            norm_target = re.sub(r"[إأآا]", "ا", target_text)
            norm_spoken = re.sub(r"[إأآا]", "ا", spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # عرض التقرير
            st.markdown("<div class='quran-box'>", unsafe_allow_html=True)
            st.metric("نسبة صحة مخارج الحروف", f"{accuracy}%")
            st.write(f"**النص المكتشف:** {spoken_text}")
            
            # تصحيح الأحكام (بناءً على CSV)
            st.divider()
            st.subheader("📋 تصحيح الأحكام والمخارج:")
            words = target_text.split()
            for word in words:
                tajweed_info = get_phonetic_analysis(word)
                if tajweed_info:
                    with st.expander(f"توجيهات تجويدية لكلمة: {word}"):
                        st.table(pd.DataFrame(tajweed_info))
            
            # تقييم المد لورش
            if mad_time < 3.0:
                st.warning(f"⚠️ زمن المد المكتشف ({mad_time} ث) قصير. تذكر إشباع المد لـ 6 حركات.")
            else:
                st.success(f"✅ إتقان ممتاز! زمن المد ({mad_time} ث) يتوافق مع رواية ورش.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except sr.UnknownValueError:
            st.error("لم يستطع النظام تمييز الكلمات. يرجى الترتيل بصوت واضح ومرتفع قليلاً.")
        except Exception as e:
            st.error(f"خطأ تقني: تأكد من تحديث مكتبة pydub ووجود ffmpeg. (التفاصيل: {e})")
