import streamlit as st
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الواجهة ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

if 'recognized_words' not in st.session_state:
    st.session_state.recognized_words = []

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-container {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2E7D32; margin: 20px auto; max-width: 900px; line-height: 2.8;
    }
    .word-visible { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; font-weight: bold; transition: all 0.5s ease-in-out; }
    .word-hidden { font-family: 'Amiri Quran', serif; font-size: 45px; color: #eee; opacity: 0.1; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. البيانات (سورة الكوثر برواية ورش) ---
surah_data = [
    {"text": "إِنَّآ", "clean": "انا"},
    {"text": "أَعْطَيْنَٰكَ", "clean": "اعطيناك"},
    {"text": "اَ۬لْكَوْثَرَ", "clean": "الكوثر"},
    {"text": "فَصَلِّ", "clean": "فصل"},
    {"text": "لِرَبِّكَ", "clean": "لربك"},
    {"text": "وَانْحَرْۖ", "clean": "وانحر"},
    {"text": "إِنَّ", "clean": "ان"},
    {"text": "شَانِئَكَ", "clean": "شانئك"},
    {"text": "هُوَ", "clean": "هو"},
    {"text": "اَ۬لَابْتَرُۖ", "clean": "الابتر"}
]

def clean_text(text):
    t = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return t.strip()

# --- 3. العرض الرئيسي ---
st.title("🕌 مصحح التلاوة: تتبع الكلمات الحي")
st.write("سجل تلاوتك، وستظهر الكلمات على الشاشة بمجرد نطقها بشكل صحيح.")

# حاوية عرض الكلمات
quran_area = st.empty()

def update_display():
    html = "<div class='quran-container'>"
    for item in surah_data:
        if item['clean'] in st.session_state.recognized_words:
            html += f"<span class='word-visible'>{item['text']}</span> "
        else:
            html += f"<span class='word-hidden'>{item['text']}</span> "
    html += "</div>"
    quran_area.markdown(html, unsafe_allow_html=True)

update_display()

st.divider()

# --- 4. معالجة التسجيل والتعرف ---
audio = mic_recorder(start_prompt="🎤 ابدأ التلاوة الآن", stop_prompt="⏹️ توقف لمعالجة الكلمات", key='live_tracker')

if audio:
    with st.spinner("⏳ جاري تمييز الكلمات المنطوقة..."):
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
                
                # تحليل الكلمات المنطوقة وإضافتها للسجل
                new_words = [clean_text(w) for w in text.split()]
                for nw in new_words:
                    if nw not in st.session_state.recognized_words:
                        st.session_state.recognized_words.append(nw)
                
                st.rerun() # تحديث الواجهة لإظهار الكلمات الجديدة

        except Exception as e:
            st.warning("لم يتم التعرف على الكلمات بشكل دقيق، حاول مرة أخرى بوضوح.")

if st.button("🔄 إعادة الاختبار"):
    st.session_state.recognized_words = []
    st.rerun()
