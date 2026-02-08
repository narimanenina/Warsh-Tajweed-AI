import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والذاكرة ---
if 'total_score' not in st.session_state: st.session_state.total_score = 0
if 'stars' not in st.session_state: st.session_state.stars = 0
if 'recognized_words' not in st.session_state: st.session_state.recognized_words = []
if 'is_hidden' not in st.session_state: st.session_state.is_hidden = False

st.set_page_config(page_title="مقرأة ورش - التقييم الذكي", layout="wide")

# --- 2. تحميل ملف الأحكام (CSV) ---
@st.cache_data
def load_tajweed_rules():
    try:
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8')
    except:
        return None

df_rules = load_tajweed_rules()

# --- 3. التصميم (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri:wght@700&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .score-box {
        background: linear-gradient(135deg, #1e5d2f 0%, #2e7d32 100%);
        padding: 20px; border-radius: 20px; color: #FFD700;
        box-shadow: 0 8px 20px rgba(0,0,0,0.2); margin-bottom: 25px;
    }
    .quran-frame {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2e7d32; margin-bottom: 20px;
    }
    .word-correct { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2e7d32; font-weight: bold; }
    .word-faded { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2e7d32; opacity: 0.15; }
    .word-hidden { background-color: #ddd; color: #ddd; border-radius: 10px; font-size: 45px; margin: 0 5px; }
    </style>
    """, unsafe_allow_html=True)

# بيانات السورة مع النقاط لكل حكم
surah_data = [
    {"text": "إِنَّآ", "clean": "ان", "letter": "ن", "points": 30, "rule": "مد مشبع + غنة"},
    {"text": "أَعْطَيْنَٰكَ", "clean": "اعطيناك", "letter": "ع", "points": 20, "rule": "مخرج العين"},
    {"text": "اَ۬لْكَوْثَرَ", "clean": "الكوثر", "letter": "ث", "points": 20, "rule": "مخرج الثاء"},
    {"text": "فَصَلِّ", "clean": "فصل", "letter": "ل", "points": 25, "rule": "تغليظ اللام"},
    {"text": "لِرَبِّكَ", "clean": "لربك", "letter": "ر", "points": 15, "rule": "ترقيق الراء"},
    {"text": "وَانْحَرْۖ", "clean": "وانحر", "letter": "ح", "points": 25, "rule": "إظهار النون"},
    {"text": "إِنَّ", "clean": "ان", "letter": "ن", "points": 20, "rule": "غنة"},
    {"text": "شَانِئَكَ", "clean": "شانئك", "letter": "ش", "points": 15, "rule": "تفشي الشين"},
    {"text": "هُوَ", "clean": "هو", "letter": "ه", "points": 10, "rule": "مخرج الهاء"},
    {"text": "اَ۬لَابْتَرُۖ", "clean": "الابتر", "letter": "ب", "points": 40, "rule": "نقل + قلقلة"}
]

st.title("🕌 مقرأة ورش: نظام التقييم بالنجوم")

# لوحة النجوم
stars_display = "⭐" * st.session_state.stars
st.markdown(f"""
    <div class='score-box'>
        <h2 style='color: white; margin:0;'>إجمالي النقاط: {st.session_state.total_score}</h2>
        <div style='font-size: 35px;'>{stars_display if stars_display else '📩 ابدأ لجمع النجوم'}</div>
    </div>
    """, unsafe_allow_html=True)

col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    if st.button("👁️ إظهار السورة"): st.session_state.is_hidden = False; st.rerun()
with col_ctrl2:
    if st.button("🙈 وضع الاختبار"): st.session_state.is_hidden = True; st.rerun()

# عرض السورة
html = "<div class='quran-frame'>"
for item in surah_data:
    if item['clean'] in st.session_state.recognized_words:
        html += f"<span class='word-correct'>{item['text']}</span> "
    elif st.session_state.is_hidden:
        html += f"<span class='word-hidden'>&nbsp;{item['text']}&nbsp;</span> "
    else:
        html += f"<span class='word-faded'>{item['text']}</span> "
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

st.divider()

# --- 4. محرك التقييم ---
audio = mic_recorder(start_prompt="🎤 سجل تلاوتك للتقييم", stop_prompt="توقف للتحليل", key='final_eval_mic')

if audio:
    with st.spinner("⏳ جاري تقييم تلاوتك بناءً على الأحكام..."):
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
                
                clean_text = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text).replace("أ", "ا").replace("إ", "ا")
                spoken_words = clean_text.split()
                
                new_p = 0
                for item in surah_data:
                    if item['clean'] in spoken_words and item['clean'] not in st.session_state.recognized_words:
                        st.session_state.recognized_words.append(item['clean'])
                        st.session_state.total_score += item['points']
                        new_p += item['points']
                
                if new_p > 0:
                    st.session_state.stars = st.session_state.total_score // 50
                    st.balloons()
                    st.success(f"أحسنت! حصلت على {new_p} نقطة جديدة.")
                st.rerun()
        except:
            st.error("يرجى القراءة بوضوح ليتم تقييمك.")

# --- 5. دليل المخارج (ص 19) ---
if df_rules is not None and st.session_state.recognized_words:
    with st.expander("📍 دليل تصحيح مخارج الحروف (بناءً على أخطائك)"):
        for item in surah_data:
            if item['clean'] not in st.session_state.recognized_words:
                advice = df_rules[df_rules['letter'] == item['letter']]
                if not advice.empty:
                    st.write(f"**كلمة {item['text']}**: تحتاج ضبط {item['rule']}.")
                    st.info(f"نصيحة المخرج: {advice.iloc[0]['description']}")
                    if "الحلق" in advice.iloc[0]['place']:
                        st.write("")
                    elif "اللسان" in advice.iloc[0]['place']:
                        st.write("")
