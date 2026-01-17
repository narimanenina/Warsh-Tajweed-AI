import streamlit as st
import pandas as pd
import numpy as np
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة (Session State) ---
if 'user_points' not in st.session_state: st.session_state.user_points = 0
if 'badges' not in st.session_state: st.session_state.badges = []

st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

# --- 2. التنسيق الجمالي (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri:wght@700&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .quran-frame {
        background-color: #fffcf2; padding: 35px; border-radius: 25px;
        border: 10px double #2E7D32; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 20px auto; max-width: 900px; line-height: 2.8;
    }
    .madd { color: #D32F2F; font-weight: bold; } 
    .ghunna { color: #2E7D32; font-weight: bold; } 
    .qalaqala { color: #1976D2; font-weight: bold; } 
    .naql { color: #9E9E9E; } 
    .word { font-family: 'Amiri Quran', serif; font-size: 45px; margin: 0 5px; color: #3e2723; }
    .aya-num { color: #2E7D32; font-size: 25px; font-weight: bold; }
    
    .points-display { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); padding: 10px 25px; border-radius: 50px; color: white; font-size: 22px; font-weight: bold; }
    .badge-item { font-size: 45px; margin: 0 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. بيانات السورة والمخارج (ص 19) ---
SURAH_DATA = {
    "إِنَّآ أَعْطَيْنَٰكَ اَ۬لْكَوْثَرَ": {
        "audio": "https://server10.mp3quran.net/huys/0108.mp3",
        "points": 50,
        "makhraj": "الجوف (للمد) ووسط الحلق (للعين)",
        "tip": "مد 'إنا' 6 حركات كاملة، واضغط على وسط الحلق لنطق العين.",
        "image": "[صورة توضيحية لمخرج العين من وسط الحلق]",
        "compare_text": "انا اعطيناك الكوثر"
    },
    "فَصَلِّ لِرَبِّكَ وَانْحَرْۖ": {
        "audio": "https://server10.mp3quran.net/huys/0108.mp3",
        "points": 30,
        "makhraj": "طرف اللسان (للام) ووسط الحلق (للحاء)",
        "tip": "رقق اللام في 'فصلِّ' وأخرج الحاء صافية من وسط الحلق.",
        "image": "[صورة توضيحية لمخرج الحاء من وسط الحلق]",
        "compare_text": "فصل لربك وانحر"
    },
    "إِنَّ شَانِئَكَ هُوَ اَ۬لَابْتَرُۖ": {
        "audio": "https://server10.mp3quran.net/huys/0108.mp3",
        "points": 70,
        "makhraj": "الشفتان (للباء) واللسان (للنقل)",
        "tip": "طبق حكم النقل (لَبْتَرُ) مع قلقلة الباء بقوة.",
        "image": "[صورة توضيحية لمخرج الباء من الشفتين]",
        "compare_text": "ان شانئك هو الابتر"
    }
}

def clean_text(text):
    t = re.sub(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]", "", text)
    t = t.replace("آ", "ا").replace("اَ۬", "ا").replace("ۖ", "").replace("أ", "ا").replace("إ", "ا")
    return t.strip()

# --- 4. واجهة المستخدم ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🕌 مقرأة ورش التفاعلية")
with c2:
    st.markdown(f"<div class='points-display'>🌟 النقاط: {st.session_state.user_points}</div>", unsafe_allow_html=True)

# عرض السورة الملونة
st.markdown(f"""
<div class="quran-frame">
    <span class="word"><span class="ghunna">إِنَّ</span><span class="madd">آ</span></span>
    <span class="word">أَعْطَيْنَٰكَ</span> <span class="word">اَ۬لْكَوْثَرَ</span> <span class="aya-num">(1)</span>
    <span class="word">فَصَلِّ</span> <span class="word">لِرَبِّكَ</span> <span class="word">وَانْحَرْۖ</span> <span class="aya-num">(2)</span>
    <span class="word"><span class="ghunna">إِنَّ</span></span> <span class="word">شَانِئَكَ</span> <span class="word">هُوَ</span>
    <span class="word"><span class="naql">اَ۬لَ</span><span class="qalaqala">بْ</span>تَرُۖ</span> <span class="aya-num">(3)</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# --- 5. نظام الاختبار والتقييم الصارم ---
st.subheader("🛠️ مختبر التلاوة الذكي")
selected_aya = st.selectbox("اختر الآية التي تريد التدرب عليها:", list(SURAH_DATA.keys()))

col_audio, col_mic = st.columns(2)
with col_audio:
    st.write("🔊 استمع للنطق الصحيح:")
    st.audio(SURAH_DATA[selected_aya]['audio'])

with col_mic:
    st.write("🎤 سجل تلاوتك للمطابقة:")
    audio_record = mic_recorder(start_prompt="ابدأ التسجيل", stop_prompt="إنهاء للتقييم", key='mic_points_strict')

if audio_record:
    with st.spinner("⏳ جاري تقييم أدائك الفعلي ومطابقته..."):
        try:
            # معالجة الصوت
            raw_audio = AudioSegment.from_file(io.BytesIO(audio_record['bytes'])).normalize()
            wav_io = io.BytesIO()
            raw_audio.export(wav_io, format="wav")
            wav_io.seek(0)
            
            r = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = r.record(source)
                spoken_text = r.recognize_google(audio_data, language="ar-SA")
            
            # المقارنة
            spoken_cleaned = clean_text(spoken_text)
            target_cleaned = clean_text(SURAH_DATA[selected_aya]['compare_text'])
            
            # التحقق من المطابقة (مطابقة جزئية أو كاملة)
            if spoken_cleaned in target_cleaned or target_cleaned in spoken_cleaned or len(set(spoken_cleaned.split()) & set(target_cleaned.split())) > 0:
                points_won = SURAH_DATA[selected_aya]['points']
                st.session_state.user_points += points_won
                st.balloons()
                st.success(f"🎊 أحسنت! تلاوتك صحيحة. حصلت على {points_won} نقطة.")
                
                # إظهار المخرج التعليمي فقط عند النجاح
                st.info(f"📍 المخرج المتقن: {SURAH_DATA[selected_aya]['makhraj']}")
                st.write(SURAH_DATA[selected_aya]['image'])
                st.markdown(f"💡 **توجيه من الكتاب (ص 19):** {SURAH_DATA[selected_aya]['tip']}")
            else:
                st.error("❌ التلاوة غير مطابقة. حاول القراءة بوضوح أكبر.")
                st.warning(f"لقد سمعتُك تقول: '{spoken_text}'")
                
        except sr.UnknownValueError:
            st.error("⚠️ عذراً، لم أستطع تمييز كلماتك. يرجى رفع صوتك والقراءة ببطء.")
        except Exception as e:
            st.error(f"⚠️ خطأ تقني: {e}")
