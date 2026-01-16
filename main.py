import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import numpy as np
import soundfile as sf
from streamlit_mic_recorder import mic_recorder
from datetime import datetime

# --- 1. إعدادات الصفحة والهوية البصرية ---
st.set_page_config(page_title="مصحح تلاوة ورش - طريق الأزرق", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: right; }
    .main-box { background-color: #f4f9f4; padding: 25px; border-radius: 15px; border-right: 10px solid #1B5E20; margin-top: 20px; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #c8e6c9; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .stButton>button { background-color: #2E7D32; color: white; width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. خوارزمية تحليل المد المشبع (طريق الأزرق) ---
def analyze_mad_duration(audio_bytes):
    """تحليل الإشارة الصوتية لاكتشاف أطول مد مستمر (6 حركات)"""
    try:
        with io.BytesIO(audio_bytes) as audio_file:
            y, sr_rate = librosa.load(audio_file)
        
        # حساب الطاقة الصوتية (RMS) لتحديد فترات الكلام
        rms = librosa.feature.rms(y=y)[0]
        # تنعيم الإشارة
        smoothed_rms = np.convolve(rms, np.ones(5)/5, mode='same')
        threshold = np.mean(smoothed_rms) * 0.5 # عتبة حساسة للترتيل
        
        is_speech = smoothed_rms > threshold
        durations = []
        count = 0
        for s in is_speech:
            if s: count += 1
            else:
                if count > 0: durations.append(count * (512 / sr_rate))
                count = 0
        
        return round(max(durations), 2) if durations else 0
    except:
        return 0

# --- 3. محرك التصحيح والمقارنة ---
def compare_recitation(target, spoken):
    target_words = target.split()
    spoken_words = spoken.split()
    matcher = difflib.SequenceMatcher(None, target_words, spoken_words)
    accuracy = round(matcher.ratio() * 100, 1)
    return accuracy

# --- 4. واجهة المستخدم ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مصحح تلاوة ورش الإلكتروني</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>تحليل دقة الألفاظ ومدود طريق الأزرق (6 حركات)</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("👤 بيانات القارئ")
    user_name = st.text_input("اسم القارئ:", "طالب العلم")
    surah_options = {
        "سورة الكوثر": "إنا أعطيناك الكوثر",
        "سورة الإخلاص": "قل هو الله أحد الله الصمد",
        "سورة الفاتحة": "غير المغضوب عليهم ولا الضالين",
        "تدريب (مد مشبع)": "آمنوا وعملوا الصالحات"
    }
    selected_surah = st.selectbox("اختر السورة:", list(surah_options.keys()))
    target_text = surah_options[selected_surah]
    st.divider()
    st.write("⚙️ **إرشادات:**")
    st.caption("1. اضغط على الميكروفون.")
    st.caption("2. رتل الآية مع إشباع المد.")
    st.caption("3. انتظر ثانية بعد الانتهاء ثم اضغط توقف.")

st.info(f"الآية المرجعية: **{target_text}**")

# تسجيل الصوت
audio_data = mic_recorder(start_prompt="🎤 ابدأ التلاوة", stop_prompt="⏹️ توقف واطلب التصحيح", key='warsh_v2')

if audio_data:
    audio_bytes = audio_data['bytes']
    st.audio(audio_bytes)
    
    with st.spinner("⏳ جاري تحليل التلاوة والمدود..."):
        try:
            # أولاً: تحويل الصوت لنص مع معالجة الأخطاء
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio_recorded = r.record(source)
                # استخدام لغة الاستهداف العربية
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # ثانياً: تحليل الزمن
            mad_time = analyze_mad_duration(audio_bytes)
            
            # ثالثاً: حساب الدقة
            acc = compare_texts = compare_recitation(target_text, spoken_text)
            
            # --- عرض التقرير النهائي ---
            st.markdown("<div class='main-box'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"<div class='metric-card'><h4>دقة الألفاظ</h4><h2 style='color:#2E7D32;'>{acc}%</h2></div>", unsafe_allow_html=True)
            with col2:
                # القاعدة: المد المشبع في طريق الأزرق >= 3.5 ثانية تقريباً
                is_long_enough = mad_time >= 3.5
                color = "#2E7D32" if is_long_enough else "#E64A19"
                st.markdown(f"<div class='metric-card'><h4>أطول مد</h4><h2 style='color:{color};'>{mad_time} ث</h2></div>", unsafe_allow_html=True)
            
            st.write(f"**ما التقطه النظام:** {spoken_text}")
            
            if acc > 85:
                if is_long_enough:
                    st.success("✅ تلاوة ممتازة! التزمت باللفظ الصحيح وبمد الـ 6 حركات.")
                    st.balloons()
                else:
                    st.warning("⚠️ اللفظ صحيح، ولكن زمن المد قصير. ورش من طريق الأزرق يمد المشبع 6 حركات.")
            else:
                st.error("❌ يوجد اختلاف في الكلمات. تأكد من مخارج الحروف وقواعد النقل عند ورش.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except sr.UnknownValueError:
            st.error("❌ لم يفهم النظام الكلمات. حاول الترتيل بوضوح أكبر وبوتيرة هادئة.")
        except Exception as e:
            st.error("⚠️ لم نتمكن من تحليل الصوت. تأكد من جودة الميكروفون والقرب منه.")
