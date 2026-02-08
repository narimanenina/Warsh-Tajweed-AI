import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- إعدادات الحالة ---
if 'total_score' not in st.session_state: st.session_state.total_score = 0
if 'recognized_words' not in st.session_state: st.session_state.recognized_words = []
if 'is_hidden' not in st.session_state: st.session_state.is_hidden = False

st.set_page_config(page_title="مقرأة ورش - المصحح الذكي", layout="wide")

# --- تحميل الأحكام من CSV ---
@st.cache_data
def load_rules():
    try:
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8')
    except:
        return None

df_rules = load_rules()

# --- التصميم ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-frame {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2e7d32; margin-bottom: 20px;
    }
    .word-correct { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2e7d32; font-weight: bold; }
    .word-faded { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2e7d32; opacity: 0.25; }
    .word-hidden { background-color: #ddd; color: #ddd; border-radius: 10px; font-size: 45px; margin: 0 5px; }
    </style>
    """, unsafe_allow_html=True)

# بيانات السورة (تم ضبط كلمة فصل لتسهيل التعرف عليها)
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

st.title("🕌 مقرأة ورش: المصحح والمقيّم")

# أزرار التحكم
c1, c2 = st.columns(2)
with c1:
    if st.button("👁️ إظهار السورة (للمساعدة)"): st.session_state.is_hidden = False; st.rerun()
with c2:
    if st.button("🙈 وضع الاختبار (تغطية الكلمات)"): st.session_state.is_hidden = True; st.rerun()

# عرض السورة
html = "<div class='quran-frame'>"
for item in surah_data:
    if item['clean'] in st.session_state.recognized_words:
        html += f"<span class='word-correct'>{item['text']}</span> "
    elif st.session_state.is_hidden:
        html += f"<span class='word-hidden'>&nbsp;{item['text']}&nbsp;</span> "
    else:
        # الكلمة تظهر "باهتة" وليست مغطاة في الوضع العادي
        html += f"<span class='word-faded'>{item['text']}</span> "
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

st.divider()

# تسجيل الصوت والتحليل
audio = mic_recorder(start_prompt="🎤 سجل تلاوتك", stop_prompt="توقف للتحليل", key='fix_eval')

if audio:
    with st.spinner("⏳ جاري تحليل الأحكام..."):
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
                
                for item in surah_data:
                    if item['clean'] in spoken_words:
                        if item['clean'] not in st.session_state.recognized_words:
                            st.session_state.recognized_words.append(item['clean'])
                            st.session_state.total_score += item['points']
                
                st.success(f"تم التعرف على: {text}")
                st.rerun()
        except:
            st.error("يرجى القراءة بوضوح.")

# --- قسم تصحيح الأحكام (هنا تظهر النتيجة) ---
if st.session_state.recognized_words and df_rules is not None:
    st.subheader("📍 دليل تصحيح الأحكام (ص 19)")
    # نأخذ آخر كلمة تم نطقها لتقديم النصيحة عنها
    last_word_clean = st.session_state.recognized_words[-1]
    
    # البحث عن معلومات الحكم للكلمة المنطوقة
    for item in surah_data:
        if item['clean'] == last_word_clean:
            rule_info = df_rules[df_rules['letter'] == item['letter']]
            if not rule_info.empty:
                st.warning(f"💡 في كلمة '{item['text']}': مطلوب {item['rule']}")
                st.info(f"توجيه المخرج: {rule_info.iloc[0]['description']}")
                
                # عرض الصور بناءً على المخرج لتعزيز الفهم
                if "الحلق" in rule_info.iloc[0]['place']:
                    
                elif "اللسان" in rule_info.iloc[0]['place']:
                    
                elif "الشفتان" in rule_info.iloc[0]['place']:
