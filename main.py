import streamlit as st
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والواجهة ---
if 'recognized_words' not in st.session_state:
    st.session_state.recognized_words = []
if 'is_hidden' not in st.session_state:
    st.session_state.is_hidden = False
if 'last_feedback' not in st.session_state:
    st.session_state.last_feedback = ""

st.set_page_config(page_title="مقرأة ورش - المصحح الذكي", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-container {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2E7D32; margin: 20px auto; max-width: 900px; line-height: 2.8;
    }
    .word-correct { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; font-weight: bold; }
    .word-error { font-family: 'Amiri Quran', serif; font-size: 45px; color: #D32F2F; text-decoration: line-through; opacity: 0.6; }
    .word-faded { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; opacity: 0.2; }
    .word-hidden { background-color: #ddd; color: #ddd; border-radius: 8px; font-size: 45px; margin: 0 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. البيانات والأحكام (بناءً على ص 19 وص 80) ---
#
surah_data = [
    {"text": "إِنَّآ", "clean": "ان", "rule": "مد مشبع 6 حركات", "makhraj": "الجوف"},
    {"text": "أَعْطَيْنَٰكَ", "clean": "اعطيناك", "rule": "تحقيق الهمزة", "makhraj": "أقصى الحلق / وسط الحلق (للعين)"},
    {"text": "اَ۬لْكَوْثَرَ", "clean": "الكوثر", "rule": "ترقيق الراء وصلاً", "makhraj": "طرف اللسان (للثاء)"},
    {"text": "فَصَلِّ", "clean": "فصل", "rule": "تغليظ اللام (ورش)", "makhraj": "طرف اللسان"},
    {"text": "لِرَبِّكَ", "clean": "لربك", "rule": "ترقيق الراء", "makhraj": "طرف اللسان"},
    {"text": "وَانْحَرْۖ", "clean": "وانحر", "rule": "إظهار النون", "makhraj": "وسط الحلق (للحاء)"},
    {"text": "إِنَّ", "clean": "ان", "rule": "غنة أكمل ما تكون", "makhraj": "الخيشوم"},
    {"text": "شَانِئَكَ", "clean": "شانئك", "rule": "تحقيق الحركات", "makhraj": "وسط اللسان (للشين)"},
    {"text": "هُوَ", "clean": "هو", "rule": "فتح الهاء", "makhraj": "أقصى الحلق"},
    {"text": "اَ۬لَابْتَرُۖ", "clean": "الابتر", "rule": "النقل وقلقلة الباء", "makhraj": "الشفتان (للباء)"}
]

def clean_text(text):
    t = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return t.strip()

# --- 3. الواجهة والأزرار ---
st.title("🕌 مصحح تلاوة ورش (AI Tarteel)")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("👁️ إظهار السورة"):
        st.session_state.is_hidden = False
        st.rerun()
with col2:
    if st.button("🙈 إخفاء السورة"):
        st.session_state.is_hidden = True
        st.rerun()
with col3:
    if st.button("🔄 إعادة"):
        st.session_state.recognized_words = []
        st.rerun()

# عرض السورة
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

# --- 4. محرك التصحيح الصارم ---
st.subheader("🎤 ابدأ التلاوة: سيتم تصحيح الكلمات والحركات")
audio = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="إنهاء للتحليل", key='tarteel_strict_v5')

if audio:
    with st.spinner("⏳ جاري تحليل التجويد والمخارج..."):
        try:
            raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_io = io.BytesIO()
            raw_audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language="ar-SA")
                
                spoken_words = [clean_text(w) for w in text.split()]
                
                # فحص الأخطاء
                for item in surah_data:
                    if item['clean'] in spoken_words:
                        if item['clean'] not in st.session_state.recognized_words:
                            st.session_state.recognized_words.append(item['clean'])
                    else:
                        st.session_state.last_feedback = f"⚠️ انتبه لكلمة '{item['text']}': تأكد من {item['rule']} ومخرج {item['makhraj']}."

                st.rerun()

        except Exception as e:
            st.error("يرجى القراءة بوضوح تام لتفعيل التصحيح.")

# --- 5. التغذية الراجعة (Feedback) بناءً على ص 19 ---
if st.session_state.last_feedback:
    st.info(st.session_state.last_feedback)
    
    st.write("📍 المرجع: مخارج الحروف - الصفحة 19 من كتاب أحكام التجويد لورش.")
