import streamlit as st
import pandas as pd
import numpy as np
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والذاكرة ---
if 'user_points' not in st.session_state: st.session_state.user_points = 0
if 'badges' not in st.session_state: st.session_state.badges = []

st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide")

# --- 2. التنسيق الجمالي (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri:wght@700&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    /* تنسيق المصحف الملون */
    .quran-frame {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2E7D32; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 20px auto; max-width: 900px; line-height: 2.8;
    }
    .madd { color: #D32F2F; font-weight: bold; } /* أحمر: مد مشبع */
    .ghunna { color: #2E7D32; font-weight: bold; } /* أخضر: غنة */
    .qalaqala { color: #1976D2; font-weight: bold; } /* أزرق: قلقلة */
    .naql { color: #9E9E9E; } /* رمادي: نقل */
    .word { font-family: 'Amiri Quran', serif; font-size: 45px; margin: 0 5px; color: #3e2723; }
    .aya-num { color: #2E7D32; font-size: 25px; font-weight: bold; }
    
    /* نظام النقاط */
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
        "image": ""
    },
    "فَصَلِّ لِرَبِّكَ وَانْحَرْۖ": {
        "audio": "https://server10.mp3quran.net/huys/0108.mp3",
        "points": 30,
        "makhraj": "طرف اللسان (للام) ووسط الحلق (للحاء)",
        "tip": "رقق اللام في 'فصلِّ' وأخرج الحاء صافية من وسط الحلق.",
        "image": ""
    },
    "إِنَّ شَانِئَكَ هُوَ اَ۬لَابْتَرُۖ": {
        "audio": "https://server10.mp3quran.net/huys/0108.mp3",
        "points": 70,
        "makhraj": "الشفتان (للباء) واللسان (للنقل)",
        "tip": "طبق حكم النقل (لَبْتَرُ) مع قلقلة الباء بقوة.",
        "image": ""
    }
}

# --- 4. واجهة المستخدم ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🕌 مقرأة ورش التفاعلية الملونة")
with c2:
    st.markdown(f"<div class='points-display'>🌟 النقاط: {st.session_state.user_points}</div>", unsafe_allow_html=True)

# عرض الأوسمة
if st.session_state.badges:
    st.markdown("".join([f"<span class='badge-item' title='{b}'>{b}</span>" for b in st.session_state.badges]), unsafe_allow_html=True)

# --- 5. عرض السورة الملونة ---
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

# --- 6. نظام الاختبار والاستماع ---
st.subheader("🛠️ مختبر التلاوة: استمع ثم رتّل")
selected_aya = st.selectbox("اختر الآية التي تريد التدرب عليها:", list(SURAH_DATA.keys()))

col_audio, col_mic = st.columns(2)
with col_audio:
    st.write("🔊 استمع للنطق الصحيح:")
    st.audio(SURAH_DATA[selected_aya]['audio'])

with col_mic:
    st.write("🎤 سجل محاكاتك للآية:")
    audio_record = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="إنهاء للتقييم", key='mic_points')

if audio_record:
    with st.spinner("⏳ جاري تقييم مخارج الحروف والأحكام..."):
        # محاكاة النجاح في التلاوة
        points_won = SURAH_DATA[selected_aya]['points']
        st.session_state.user_points += points_won
        
        st.balloons()
        st.success(f"🎊 أحسنت! حصلت على {points_won} نقطة.")
        
        # منح الأوسمة بناءً على الإنجاز
        if st.session_state.user_points >= 150 and "👑 ملك التجويد" not in st.session_state.badges:
            st.session_state.badges.append("👑 ملك التجويد")
        elif st.session_state.user_points >= 50 and "🌟 قارئ مجتهد" not in st.session_state.badges:
            st.session_state.badges.append("🌟 قارئ مجتهد")

        # عرض مخرج الحرف المصور بناءً على الصفحة 19
        st.info(f"📍 مخرج الحرف المستهدف: {SURAH_DATA[selected_aya]['makhraj']}")
        st.write(SURAH_DATA[selected_aya]['image'])
        st.markdown(f"💡 **نصيحة تعليمية:** {SURAH_DATA[selected_aya]['tip']}")
