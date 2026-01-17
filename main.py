import streamlit as st
import time
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والواجهة ---
if 'is_testing' not in st.session_state: st.session_state.is_testing = False
if 'spoken_text' not in st.session_state: st.session_state.spoken_text = ""

st.set_page_config(page_title="مقرأة ورش الذكية - Tarteel Clone", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-container {
        background-color: #ffffff; padding: 40px; border-radius: 20px;
        border: 2px solid #2E7D32; box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin: 20px auto; max-width: 800px; line-height: 3;
    }
    .word-highlight { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; font-weight: bold; border-bottom: 3px solid #2E7D32; }
    .word-hidden { background-color: #eee; color: #eee; border-radius: 5px; font-size: 45px; margin: 0 5px; cursor: pointer; }
    .word-normal { font-family: 'Amiri Quran', serif; font-size: 45px; color: #3e2723; margin: 0 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. البيانات (سورة الكوثر برواية ورش) ---
surah_words = ["إِنَّآ", "أَعْطَيْنَٰكَ", "اَ۬لْكَوْثَرَ", "فَصَلِّ", "لِرَبِّكَ", "وَانْحَرْۖ", "إِنَّ", "شَانِئَكَ", "هُوَ", "اَ۬لَابْتَرُۖ"]

def clean_text(text):
    return re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text).strip()

# --- 3. تصميم واجهة "ترتيل" ---
st.title("🕌 تطبيق ترتيل - رواية ورش")
st.write("استخدم الميكروفون للبدء في التلاوة وسيقوم التطبيق بتتبع كلماتك.")

# تبديل وضع "الاختبار" (إخفاء الآيات)
c1, c2 = st.columns(2)
with c1:
    if st.button("👁️ عرض الآيات"): st.session_state.is_testing = False
with c2:
    if st.button("🙈 وضع الاختبار (إخفاء)"): st.session_state.is_testing = True

# عرض المصحف
display_html = "<div class='quran-container'>"
spoken_words = st.session_state.spoken_text.split()

for w in surah_words:
    clean_w = clean_text(w)
    if st.session_state.is_testing:
        # في وضع الاختبار، الكلمة تظهر فقط إذا نطقها المستخدم صح
        if clean_w in spoken_words:
            display_html += f"<span class='word-normal'>{w}</span> "
        else:
            display_html += f"<span class='word-hidden'>&nbsp;&nbsp;{w}&nbsp;&nbsp;</span> "
    else:
        # في الوضع العادي، يتم تلوين الكلمة المنطوقة حالياً
        if clean_w in spoken_words:
            display_html += f"<span class='word-highlight'>{w}</span> "
        else:
            display_html += f"<span class='word-normal'>{w}</span> "
display_html += "</div>"

st.markdown(display_html, unsafe_allow_html=True)

st.divider()

# --- 4. محرك التعرف الصوتي (Tarteel Engine) ---
st.subheader("🎤 ابدأ التلاوة")
audio = mic_recorder(start_prompt="اضغط للتلاوة", stop_prompt="توقف للتحليل", key='tarteel_mic')

if audio:
    with st.spinner("⏳ جاري التعرف على تلاوتك..."):
        try:
            raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_io = io.BytesIO()
            raw_audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                r.adjust_for_ambient_noise(source)
                audio_data = r.record(source)
                # استخدام محرك جوجل للتعرف على الكلام (يدعم العربية بوضوح)
                text = r.recognize_google(audio_data, language="ar-SA")
                st.session_state.spoken_text = clean_text(text)
                st.rerun() # تحديث الواجهة فوراً لتلوين الكلمات
                
        except Exception as e:
            st.warning("يرجى القراءة بوضوح. تأكد من اتصال الإنترنت.")

# --- 5. ميزات إضافية (من الفيديو) ---
with st.sidebar:
    st.header("⚙️ الإعدادات")
    st.selectbox("اختر القارئ للمحاكاة:", ["بلال عيناوي (ورش)", "الحصري (ورش)"])
    st.slider("سرعة التتبع:", 0.5, 2.0, 1.0)
    st.checkbox("تنبيه عند الخطأ في الحكم")
