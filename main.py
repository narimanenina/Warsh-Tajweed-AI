import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
import os

# محاولة استيراد المكتبة مع معالجة الخطأ لإرشاد المستخدم
try:
    from streamlit_mic_recorder import mic_recorder
except ModuleNotFoundError:
    st.error("المكتبة 'streamlit-mic-recorder' غير مثبتة. يرجى إضافتها لملف requirements.txt")

try:
    from pydub import AudioSegment
except ModuleNotFoundError:
    st.error("المكتبة 'pydub' غير مثبتة. يرجى إضافتها لملف requirements.txt")

# --- 1. إعدادات الحالة ---
if 'recognized_words' not in st.session_state:
    st.session_state.recognized_words = []
if 'is_hidden' not in st.session_state:
    st.session_state.is_hidden = False

st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

# --- 2. تحميل البيانات بأمان ---
@st.cache_data
def load_tajweed_rules():
    file_path = 'arabic_phonetics.csv'
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except:
            return None
    return None

df_rules = load_tajweed_rules()

# --- 3. تصميم الواجهة ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-container {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2E7D32; margin: 20px auto; max-width: 800px; line-height: 2.8;
    }
    .word-correct { color: #2E7D32; font-weight: bold; font-family: 'Amiri Quran', serif; font-size: 45px; }
    .word-faded { color: #2E7D32; opacity: 0.2; font-family: 'Amiri Quran', serif; font-size: 45px; }
    .word-hidden { background-color: #ddd; color: #ddd; border-radius: 8px; font-size: 45px; margin: 0 5px; }
    </style>
    """, unsafe_allow_html=True)

# بيانات سورة الكوثر
surah_data = [
    {"text": "إِنَّآ", "clean": "ان"}, {"text": "أَعْطَيْنَٰكَ", "clean": "اعطيناك"},
    {"text": "اَ۬لْكَوْثَرَ", "clean": "الكوثر"}, {"text": "فَصَلِّ", "clean": "فصل"},
    {"text": "لِرَبِّكَ", "clean": "لربك"}, {"text": "وَانْحَرْۖ", "clean": "وانحر"},
    {"text": "إِنَّ", "clean": "ان"}, {"text": "شَانِئَكَ", "clean": "شانئك"},
    {"text": "هُوَ", "clean": "هو"}, {"text": "اَ۬لَابْتَرُۖ", "clean": "الابتر"}
]

st.title("🕌 مصحح تلاوة ورش")

col1, col2 = st.columns(2)
with col1:
    if st.button("👁️ إظهار السورة"): st.session_state.is_hidden = False; st.rerun()
with col2:
    if st.button("🙈 وضع الاختبار"): st.session_state.is_hidden = True; st.rerun()

# عرض المصحف
html = "<div class='quran-container'>"
for item in surah_data:
    if item['clean'] in st.session_state.recognized_words:
        html += f"<span class='word-correct'>{item['text']}</span> "
    elif st.session_state.is_hidden:
        html += f"<span class='word-hidden'>&nbsp;{item['text']}&nbsp;</span> "
    else:
        html += f"<span class='word-faded'>{item['text']}</span> "
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

# --- 4. معالجة الصوت ---
st.subheader("🎤 سجل تلاوتك الآن")
# استخدام المكون فقط إذا تم استيراده بنجاح
if 'mic_recorder' in globals():
    audio = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="توقف للتحليل", key='recorder')
    
    if audio:
        with st.spinner("⏳ جاري التحليل..."):
            try:
                raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
                wav_io = io.BytesIO()
                raw_audio.export(wav_io, format="wav")
                wav_io.seek(0)
                
                r = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = r.record(source)
                    text = r.recognize_google(audio_data, language="ar-SA")
                    
                    # تنظيف ومطابقة
                    clean_text = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text).replace("أ", "ا").replace("إ", "ا")
                    spoken_words = clean_text.split()
                    
                    for item in surah_data:
                        if item['clean'] in spoken_words:
                            if item['clean'] not in st.session_state.recognized_words:
                                st.session_state.recognized_words.append(item['clean'])
                    st.rerun()
            except Exception as e:
                st.error("تعذر التعرف على الصوت، يرجى المحاولة مرة أخرى.")
else:
    st.warning("جاري إعداد نظام التسجيل، يرجى تحديث الصفحة بعد قليل.")
