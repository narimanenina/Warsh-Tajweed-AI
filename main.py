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

st.set_page_config(page_title="مقرأة ورش - تتبع وإخفاء", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-container {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2E7D32; margin: 20px auto; max-width: 900px; line-height: 2.8;
    }
    .word-visible { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; font-weight: bold; }
    .word-faded { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; opacity: 0.2; }
    .word-test { background-color: #ddd; color: #ddd; border-radius: 8px; font-size: 45px; margin: 0 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. البيانات (رواية ورش) ---
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

# --- 3. أزرار التحكم ---
st.title("🕌 تطبيق ترتيل ورش: تتبع وإخفاء")

col1, col2 = st.columns(2)
with col1:
    if st.button("👁️ إظهار السورة كاملة"):
        st.session_state.is_hidden = False
        st.rerun()
with col2:
    if st.button("🙈 وضع الاختبار (إخفاء)"):
        st.session_state.is_hidden = True
        st.rerun()

# --- 4. عرض السورة التفاعلي ---
html = "<div class='quran-container'>"
for item in surah_data:
    # الكلمة تظهر بلون أخضر غامق إذا نطقها المستخدم صح
    if item['clean'] in st.session_state.recognized_words:
        html += f"<span class='word-visible'>{item['text']}</span> "
    # إذا كان وضع الإخفاء مفعلاً والكلمة لم تُنطق بعد
    elif st.session_state.is_hidden:
        html += f"<span class='word-test'>&nbsp;{item['text']}&nbsp;</span> "
    # إذا كان وضع الإظهار مفعلاً تظهر الكلمة باهتة بانتظار نطقها
    else:
        html += f"<span class='word-faded'>{item['text']}</span> "
html += "</div>"

st.markdown(html, unsafe_allow_html=True)

st.divider()

# --- 5. التسجيل والمعالجة بناءً على صفحة 19 من الكتاب ---
st.subheader("🎤 ابدأ التلاوة ليظهر النص")
audio = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="توقف لإظهار الكلمات", key='tarteel_fix')

if audio:
    with st.spinner("⏳ جاري تحليل تلاوتك..."):
        try:
            # معالجة الصوت باستخدام pydub
            raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_io = io.BytesIO()
            raw_audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language="ar-SA")
                
                # تحليل الكلمات المنطوقة
                new_words = [clean_text(w) for w in text.split()]
                for nw in new_words:
                    if nw not in st.session_state.recognized_words:
                        st.session_state.recognized_words.append(nw)
                
                st.rerun()
        except sr.UnknownValueError:
            st.error("لم يتم التعرف على الصوت، يرجى القراءة بوضوح.")
        except Exception as e:
            st.error(f"حدث خطأ فني: {e}")

if st.button("🔄 إعادة الاختبار"):
    st.session_state.recognized_words = []
    st.session_state.is_hidden = False
    st.rerun()

# توجيه تعليمي بناءً على مخارج الحروف
with st.expander("📍 تنبيهات مخارج الحروف (ص 19)"):
    st.info("تأكد من إخراج العين من وسط الحلق في 'أعطيناك' والباء من الشفتين مع القلقلة في 'الأبتر'.")
