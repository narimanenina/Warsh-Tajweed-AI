import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة ---
if 'user_points' not in st.session_state: st.session_state.user_points = 0
if 'stars' not in st.session_state: st.session_state.stars = 0
if 'recognized_words' not in st.session_state: st.session_state.recognized_words = []
if 'feedback_list' not in st.session_state: st.session_state.feedback_list = []

st.set_page_config(page_title="مصحح أحكام ورش", layout="wide")

# --- 2. تحميل ملف الأحكام (المرجع العلمي) ---
@st.cache_data
def load_phonetics():
    try:
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8')
    except:
        return None

df_rules = load_phonetics()

# --- 3. تصميم الواجهة ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-frame {
        background-color: #fffcf2; padding: 35px; border-radius: 25px;
        border: 8px double #2E7D32; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 20px auto; line-height: 2.8;
    }
    .word-correct { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; font-weight: bold; }
    .word-faded { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; opacity: 0.15; }
    .feedback-box { background-color: #fff3e0; padding: 15px; border-right: 5px solid #ff9800; border-radius: 10px; text-align: right; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# بيانات سورة الكوثر
surah_data = [
    {"text": "إِنَّآ", "clean": "ان", "key_letter": "ن"},
    {"text": "أَعْطَيْنَٰكَ", "clean": "اعطيناك", "key_letter": "ع"},
    {"text": "اَ۬لْكَوْثَرَ", "clean": "الكوثر", "key_letter": "ث"},
    {"text": "فَصَلِّ", "clean": "فصل", "key_letter": "ل"},
    {"text": "لِرَبِّكَ", "clean": "لربك", "key_letter": "ر"},
    {"text": "وَانْحَرْۖ", "clean": "وانحر", "key_letter": "ح"},
    {"text": "إِنَّ", "clean": "ان", "key_letter": "ن"},
    {"text": "شَانِئَكَ", "clean": "شانئك", "key_letter": "ش"},
    {"text": "هُوَ", "clean": "هو", "key_letter": "ه"},
    {"text": "اَ۬لَابْتَرُۖ", "clean": "الابتر", "key_letter": "ب"}
]

st.title("🕌 مصحح أحكام التجويد (رواية ورش)")

# عرض السورة
html = "<div class='quran-frame'>"
for item in surah_data:
    if item['clean'] in st.session_state.recognized_words:
        html += f"<span class='word-correct'>{item['text']}</span> "
    else:
        html += f"<span class='word-faded'>{item['text']}</span> "
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

# --- 4. محرك التصحيح والمقارنة مع CSV ---
audio = mic_recorder(start_prompt="🎤 ابدأ التلاوة للتصحيح", stop_prompt="توقف للتحليل", key='tajweed_checker')

if audio:
    with st.spinner("⏳ جاري تحليل الأحكام والمخارج..."):
        try:
            raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_io = io.BytesIO()
            raw_audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                r.adjust_for_ambient_noise(source)
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language="ar-SA")
                
                clean_txt = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text).replace("أ", "ا").replace("إ", "ا")
                spoken_words = clean_txt.split()
                
                new_feedback = []
                for item in surah_data:
                    if item['clean'] in spoken_words:
                        if item['clean'] not in st.session_state.recognized_words:
                            st.session_state.recognized_words.append(item['clean'])
                    else:
                        # إذا لم ينطق الكلمة صحيحة، نبحث عن الحكم في CSV
                        if df_rules is not None:
                            rule = df_rules[df_rules['letter'] == item['key_letter']]
                            if not rule.empty:
                                new_feedback.append(f"⚠️ خطأ في '{item['text']}': تأكد من مخرج {rule.iloc[0]['place']} ({rule.iloc[0]['description']})")
                
                st.session_state.feedback_list = new_feedback
                st.rerun()
        except:
            st.error("يرجى التحدث بوضوح أكبر لنتمكن من تصحيح الأحكام.")

# --- 5. عرض التوجيهات البصرية ---
if st.session_state.feedback_list:
    st.subheader("📍 توجيهات تصحيح الأداء (بناءً على تلاوتك)")
    for fb in st.session_state.feedback_list:
        st.markdown(f"<div class='feedback-box'>{fb}</div>", unsafe_allow_html=True)
        
        # عرض صور المخارج بناءً على نوع الخطأ
        if "الحلق" in fb:
            st.write("استعن بصورة مخرج الحلق لتصحيح النطق:")
            
        elif "اللسان" in fb:
            st.write("لاحظ وضعية اللسان الصحيحة:")
            
        elif "الشفتان" in fb:
            st.write("تأكد من إطباق الشفتين كما في الصورة:")


