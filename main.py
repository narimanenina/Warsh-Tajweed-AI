import streamlit as st
import pandas as pd
import numpy as np
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والواجهة ---
if 'user_points' not in st.session_state: st.session_state.user_points = 0
if 'badges' not in st.session_state: st.session_state.badges = []
if 'recognized_words' not in st.session_state: st.session_state.recognized_words = []
if 'is_hidden' not in st.session_state: st.session_state.is_hidden = False

st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri:wght@700&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-frame {
        background-color: #fffcf2; padding: 35px; border-radius: 25px;
        border: 10px double #2E7D32; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 20px auto; max-width: 900px; line-height: 2.8;
    }
    .word-correct { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; font-weight: bold; }
    .word-faded { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; opacity: 0.2; }
    .word-test { background-color: #ddd; color: #ddd; border-radius: 8px; font-size: 45px; margin: 0 5px; }
    
    .points-display { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); padding: 10px 25px; border-radius: 50px; color: white; font-size: 22px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. دالة تحميل الأحكام من CSV ---
def load_tajweed_data():
    try:
        df = pd.read_csv('arabic_phonetics.csv', encoding='utf-8')
        return df
    except:
        return None

df_rules = load_tajweed_data()

# --- 3. بيانات السورة (ورش) ---
surah_data = [
    {"text": "إِنَّآ", "clean": "ان", "audio": "https://server10.mp3quran.net/huys/0108.mp3"},
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

def clean_input(text):
    t = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return t.strip()

# --- 4. واجهة المستخدم والأزرار ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🕌 مصحح تلاوة ورش الاحترافي")
with c2:
    st.markdown(f"<div class='points-display'>🌟 النقاط: {st.session_state.user_points}</div>", unsafe_allow_html=True)

col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    if st.button("👁️ إظهار السورة"):
        st.session_state.is_hidden = False
        st.rerun()
with col_btn2:
    if st.button("🙈 وضع الاختبار"):
        st.session_state.is_hidden = True
        st.rerun()
with col_btn3:
    if st.button("🔄 إعادة التصفير"):
        st.session_state.recognized_words = []
        st.session_state.user_points = 0
        st.rerun()

# عرض السورة التفاعلي
html = "<div class='quran-frame'>"
for item in surah_data:
    if item['clean'] in st.session_state.recognized_words:
        html += f"<span class='word-correct'>{item['text']}</span> "
    elif st.session_state.is_hidden:
        html += f"<span class='word-test'>&nbsp;{item['text']}&nbsp;</span> "
    else:
        html += f"<span class='word-faded'>{item['text']}</span> "
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

st.divider()

# --- 5. محرك التصحيح والتقييم ---
st.subheader("🎤 سجل تلاوتك الآن")
audio = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="توقف للتحليل", key='tarteel_final_v1')

if audio:
    with st.spinner("⏳ جاري تحليل مخارج الحروف والأحكام..."):
        try:
            # معالجة الصوت
            raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes'])).normalize()
            wav_io = io.BytesIO()
            raw_audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language="ar-SA")
                
                spoken_words = [clean_input(w) for w in text.split()]
                
                # تحديث الكلمات والنقاط
                found_new = False
                for item in surah_data:
                    if item['clean'] in spoken_words and item['clean'] not in st.session_state.recognized_words:
                        st.session_state.recognized_words.append(item['clean'])
                        st.session_state.user_points += 10
                        found_new = True
                
                if found_new:
                    st.balloons()
                    st.success("أحسنت! تم التعرف على كلمات جديدة.")
                else:
                    st.error(f"التلاوة غير مطابقة. سمعتُ: {text}")
                
                st.rerun()

        except Exception as e:
            st.error("يرجى القراءة بوضوح. تأكد من مخارج الحروف.")

# --- 6. عرض نصائح المخارج من CSV (ص 19) ---
if st.session_state.recognized_words and df_rules is not None:
    st.subheader("📍 دليل تصحيح المخارج (بناءً على تلاوتك)")
    last_word = st.session_state.recognized_words[-1]
    # محاولة مطابقة الحرف الأول من الكلمة مع جدول المخارج
    first_char = last_word[0]
    advice = df_rules[df_rules['letter'] == first_char]
    
    if not advice.empty:
        info = advice.iloc[0]
        st.info(f"نصيحة لحرف ({first_char}): {info['description']}")
        st.write(f"المخرج: {info['place']}")
