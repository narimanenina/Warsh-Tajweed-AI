import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import numpy as np
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الواجهة ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { 
        font-family: 'Amiri', serif; direction: rtl; text-align: right; 
    }
    .word-correct { color: #2E7D32; font-size: 24px; font-weight: bold; margin: 5px; }
    .word-error { color: #D32F2F; font-size: 24px; font-weight: bold; text-decoration: underline; margin: 5px; }
    .quran-container {
        background-color: #f9f9f9; padding: 30px; border-radius: 20px;
        border: 2px solid #e0e0e0; text-align: center; line-height: 2.5;
    }
    .feedback-box {
        background-color: #e8f5e9; padding: 15px; border-radius: 10px; border-right: 5px solid #2E7D32;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. بيانات أحكام ورش (افتراضية للمثال) ---
def get_warsh_rules(word):
    rules = {
        "أحد": "قلقلة كبرى في الدال عند الوقف.",
        "الصمد": "تغليظ اللام (عند البعض) وقلقلة الدال.",
        "يولد": "قلقلة الدال ساكنة.",
        "كفوا": "لورش فيها إبدال الهمزة واواً (كُفُواً) ونقل الحركة.",
    }
    return rules.get(word, "تأكد من مخارج الحروف وصفاتها.")

# --- 3. معالجة الصوت ---
def process_audio(audio_bytes):
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    wav_buf = io.BytesIO()
    audio.export(wav_buf, format="wav")
    wav_buf.seek(0)
    
    y, sr_rate = librosa.load(wav_buf)
    rms = librosa.feature.rms(y=y)[0]
    duration = np.sum(rms > (np.max(rms)*0.2)) * (512/sr_rate)
    
    wav_buf.seek(0)
    return duration, wav_buf

# --- 4. واجهة المستخدم ---
st.title("🕌 مصحح التلاوة التفاعلي (رواية ورش)")
st.write("اقرأ الآية بتمهل ليقوم النظام بتحليل نطقك وأحكامك.")

# آية التجربة
target_verse = "قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"

with st.sidebar:
    st.header("📖 آية التجربة")
    st.info(target_verse)

audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة الآن", stop_prompt="⏹️ توقف للحصول على النتيجة", key='warsh_final')

if audio_record:
    audio_bytes = audio_record['bytes']
    
    with st.spinner("⏳ جاري تحليل تلاوتك..."):
        try:
            # معالجة الصوت والتعرف على النص
            duration, wav_buffer = process_audio(audio_bytes)
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")

            # تنظيف النصوص للمقارنة
            def clean(text):
                t = re.sub(r"[\u064B-\u0652]", "", text) # حذف التشكيل
                return t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")

            target_words = target_verse.split()
            spoken_words = spoken_text.split()
            
            # --- عرض النتيجة بالتلوين ---
            st.subheader("📊 تحليل النطق المباشر:")
            result_html = "<div class='quran-container'>"
            
            errors_found = []
            for i, word in enumerate(target_words):
                clean_target = clean(word)
                # بحث بسيط عن الكلمة في النص المنطوق
                if any(clean_target in clean(sw) for sw in spoken_words):
                    result_html += f"<span class='word-correct'>{word}</span> "
                else:
                    result_html += f"<span class='word-error'>{word}</span> "
                    errors_found.append(word)
            
            result_html += "</div>"
            st.markdown(result_html, unsafe_allow_html=True)

            # --- ملاحظات أحكام التلاوة ---
            st.divider()
            st.subheader("📝 ملاحظات التجويد (رواية ورش):")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("زمن التلاوة", f"{round(duration, 1)} ثانية")
                if duration < 5:
                    st.warning("⚠️ القراءة سريعة نوعاً ما، حاول الترتيل ببطء لتحقيق أحكام المد.")
            
            with col2:
                accuracy = round(difflib.SequenceMatcher(None, clean(target_verse), clean(spoken_text)).ratio() * 100)
                st.metric("نسبة الإتقان اللفظي", f"{accuracy}%")

            if errors_found:
                st.error("⚠️ توجد كلمات لم يتم التعرف عليها بشكل صحيح. قد يكون السبب مخارج الحروف أو سرعة القراءة.")
                for err in errors_found:
                    with st.expander(f"كيفية تصحيح: {err}"):
                        st.write(f"**الحكم:** {get_warsh_rules(err)}")
                        st.write("**نصيحة:** تأكد من تحقيق مخرج الحرف بوضوح، وإذا كان هناك نقل أو إبدال كما في 'كفواً'، فالتزم بمرتبة الأداء لورش.")
            else:
                st.success("✅ أحسنت! النطق اللفظي سليم جداً وفقاً للتحليل الأولي.")

            st.info("💡 **نصيحة للقراءة:** رواية ورش تمتاز بمد البدل (4-6 حركات) وتغليظ اللامات، حاول إظهار هذه الصفات في تسجيلك القادم.")

        except Exception as e:
            st.error("لم نتمكن من تحليل الصوت بدقة. يرجى محاولة القراءة بصوت أعلى وأوضح.")
