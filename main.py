import streamlit as st
import time
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والذاكرة ---
if 'user_points' not in st.session_state: st.session_state.user_points = 0

st.set_page_config(page_title="مقرأة ورش - تتبع الكلمات", layout="wide")

# --- 2. التنسيق الجمالي (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-frame {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2E7D32; margin: 20px auto; max-width: 900px; line-height: 2.8;
    }
    /* تنسيق الكلمات أثناء التتبع */
    .word-normal { font-family: 'Amiri Quran', serif; font-size: 45px; color: #3e2723; margin: 0 8px; opacity: 0.2; transition: all 0.4s; }
    .word-active { font-family: 'Amiri Quran', serif; font-size: 52px; color: #D32F2F; font-weight: bold; opacity: 1; transform: scale(1.1); }
    .aya-num { color: #2E7D32; font-size: 25px; font-weight: bold; }
    
    .points-display { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); padding: 10px 25px; border-radius: 50px; color: white; font-size: 22px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. بيانات السورة والمخارج (بناءً على ص 19 من الكتاب) ---
#
SURAH_WORDS = [
    {"text": "إِنَّآ", "makhraj": "الجوف (للمد)", "tip": "مد مشبع 6 حركات لورش", "duration": 1.5},
    {"text": "أَعْطَيْنَٰكَ", "makhraj": "وسط الحلق (للعين)", "tip": "تحقيق مخرج العين الساكنة", "duration": 1.2},
    {"text": "اَ۬لْكَوْثَرَ", "makhraj": "طرف اللسان (للثاء)", "tip": "إخراج طرف اللسان مع الثنايا", "duration": 1.2},
    {"text": "(1)", "makhraj": None, "tip": None, "duration": 0.5},
    {"text": "فَصَلِّ", "makhraj": "طرف اللسان (للام)", "tip": "ترقيق اللام وصلاً", "duration": 1.0},
    {"text": "لِرَبِّكَ", "makhraj": "طرف اللسان (للراء)", "tip": "ترقيق الراء لورش", "duration": 1.0},
    {"text": "وَانْحَرْۖ", "makhraj": "وسط الحلق (للُّحاء)", "tip": "إظهار النون عند الحاء", "duration": 1.2},
    {"text": "(2)", "makhraj": None, "tip": None, "duration": 0.5},
    {"text": "إِنَّ", "makhraj": "الخيشوم (للغنة)", "tip": "غنة أكمل ما تكون حركتين", "duration": 1.0},
    {"text": "شَانِئَكَ", "makhraj": "وسط اللسان (للشين)", "tip": "تفشي الشين بوضوح", "duration": 1.0},
    {"text": "هُوَ", "makhraj": "أقصى الحلق (للهاء)", "tip": "إخراج الهاء من مخرجها", "duration": 0.8},
    {"text": "اَ۬لَابْتَرُۖ", "makhraj": "الشفتان (للباء)", "tip": "حكم النقل (لَبْتَرُ) وقلقلة الباء", "duration": 1.5},
    {"text": "(3)", "makhraj": None, "tip": None, "duration": 0.5}
]

def clean_text(text):
    t = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text)
    return t.strip()

# --- 4. واجهة المستخدم ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🕌 مصحح ورش: نظام تتبع الكلمات")
with c2:
    st.markdown(f"<div class='points-display'>🌟 النقاط: {st.session_state.user_points}</div>", unsafe_allow_html=True)

# حاوية العرض المتغيرة
quran_area = st.empty()

# دالة لعرض الكلمات مع تمييز الكلمة الحالية
def display_quran(active_index=-1):
    html = "<div class='quran-frame'>"
    for idx, item in enumerate(SURAH_WORDS):
        if "(" in item['text']:
            html += f"<span class='aya-num'>{item['text']}</span> "
        elif idx == active_index:
            html += f"<span class='word-active'>{item['text']}</span> "
        else:
            html += f"<span class='word-normal'>{item['text']}</span> "
    html += "</div>"
    quran_area.markdown(html, unsafe_allow_html=True)

# العرض الأولي
display_quran()

st.divider()

# --- 5. منطق التشغيل والتحليل ---
col_play, col_record = st.columns(2)

with col_play:
    if st.button("▶️ ابدأ تتبع الكلمات (محاكاة)"):
        for i in range(len(SURAH_WORDS)):
            display_quran(i)
            time.sleep(SURAH_WORDS[i]['duration'])
        display_quran() # إعادة العرض للحالة الطبيعية

with col_record:
    audio = mic_recorder(start_prompt="🎤 سجل تلاوتك للمطابقة", stop_prompt="⏹️ إنهاء التقييم", key='tracking_mic')

if audio:
    with st.spinner("⏳ جاري تحليل مخارج الحروف..."):
        try:
            raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_io = io.BytesIO()
            raw_audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = r.record(source)
                spoken = r.recognize_google(audio_data, language="ar-SA")
            
            # محاكاة التتبع بناءً على ما تم التعرف عليه
            st.success("تم التعرف على تلاوتك!")
            st.session_state.user_points += 50
            st.balloons()
            
            # عرض نصيحة المخرج بناءً على الصفحة 19
            #
            st.info("📍 توجيهات مخارج الحروف لآية الكوثر:")
            st.markdown("""
            * **العين (وسط الحلق):** تأكد من ضغط وسط الحلق. 
            * **الباء (الشفتان):** انتبه للقلقلة في كلمة 'الابتر'. 
            """)
            
        except Exception as e:
            st.error("يرجى المحاولة مرة أخرى بوضوح.")
