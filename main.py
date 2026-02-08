import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والمكافآت ---
if 'user_points' not in st.session_state: st.session_state.user_points = 0
if 'stars' not in st.session_state: st.session_state.stars = 0
if 'recognized_words' not in st.session_state: st.session_state.recognized_words = []
if 'is_hidden' not in st.session_state: st.session_state.is_hidden = False

st.set_page_config(page_title="مقرأة ورش - نظام النجوم", layout="wide")

# --- 2. التصميم (CSS) لإضافة النجوم والجمالية ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-frame {
        background-color: #fffcf2; padding: 35px; border-radius: 25px;
        border: 8px double #2E7D32; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 20px auto; max-width: 850px; line-height: 2.8;
    }
    .word-correct { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; font-weight: bold; }
    .word-faded { font-family: 'Amiri Quran', serif; font-size: 45px; color: #2E7D32; opacity: 0.15; }
    .word-test { background-color: #e0e0e0; color: #e0e0e0; border-radius: 8px; font-size: 45px; margin: 0 5px; }
    
    .reward-container {
        background: linear-gradient(135deg, #1e5631 0%, #2e7d32 100%);
        padding: 15px; border-radius: 20px; color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px;
    }
    .star-icon { color: #FFD700; font-size: 30px; text-shadow: 0 0 10px #fff; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. بيانات السورة ---
surah_data = [
    {"text": "إِنَّآ", "clean": "ان"}, {"text": "أَعْطَيْنَٰكَ", "clean": "اعطيناك"},
    {"text": "اَ۬لْكَوْثَرَ", "clean": "الكوثر"}, {"text": "فَصَلِّ", "clean": "فصل"},
    {"text": "لِرَبِّكَ", "clean": "لربك"}, {"text": "وَانْحَرْۖ", "clean": "وانحر"},
    {"text": "إِنَّ", "clean": "ان"}, {"text": "شَانِئَكَ", "clean": "شانئك"},
    {"text": "هُوَ", "clean": "هو"}, {"text": "اَ۬لَابْتَرُۖ", "clean": "الابتر"}
]

# --- 4. واجهة المكافآت (النجوم) ---
st.title("🌟 تلاوة ورش مع نظام المكافآت")

# عرض النجوم والنقاط
stars_html = "".join(["<span class='star-icon'>⭐</span>" for _ in range(st.session_state.stars)])
st.markdown(f"""
    <div class='reward-container'>
        <h3>مستواك الحالي</h3>
        <div style='font-size: 25px;'>{stars_html if stars_html else 'ابدأ لتنال النجوم'}</div>
        <p>النقاط: {st.session_state.user_points} | الكلمات المتقنة: {len(st.session_state.recognized_words)}</p>
    </div>
    """, unsafe_allow_html=True)

# أزرار التحكم
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("👁️ إظهار السورة"): st.session_state.is_hidden = False; st.rerun()
with col2:
    if st.button("🙈 وضع الاختبار"): st.session_state.is_hidden = True; st.rerun()
with col3:
    if st.button("🔄 إعادة"): st.session_state.recognized_words = []; st.session_state.stars = 0; st.session_state.user_points = 0; st.rerun()

# عرض المصحف
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

# --- 5. التسجيل ونظام منح النجوم ---
st.subheader("🎤 سجل تلاوتك لتجمع النجوم")
audio = mic_recorder(start_prompt="ابدأ التسجيل", stop_prompt="توقف للتقييم", key='reward_recorder')

if audio:
    with st.spinner("⏳ جاري تقييم تلاوتك..."):
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
                
                initial_count = len(st.session_state.recognized_words)
                
                for item in surah_data:
                    if item['clean'] in spoken_words and item['clean'] not in st.session_state.recognized_words:
                        st.session_state.recognized_words.append(item['clean'])
                        st.session_state.user_points += 10
                
                # منطق منح النجوم: نجمة لكل 3 كلمات جديدة
                new_total = len(st.session_state.recognized_words)
                if new_total > initial_count:
                    st.session_state.stars = new_total // 2 # نجمة لكل كلمتين صحيحة
                    st.balloons()
                    st.toast(f"رائع! لقد نطقت {new_total} كلمات صحيحة!", icon="⭐")
                
                st.rerun()
        except:
            st.error("حاول القراءة بوضوح أكثر ليتم منحك النجوم.")

