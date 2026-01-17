import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import librosa
import numpy as np
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الواجهة المتمركزة ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="wide", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    
    /* تنسيق الخط والاتجاه */
    html, body, [class*="st-"] { 
        font-family: 'Amiri', serif; direction: rtl; text-align: center; 
    }

    /* حاوية السورة المركزية */
    .quran-center-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        align-items: center;
        background-color: #ffffff;
        padding: 40px;
        border-radius: 25px;
        border: 3px solid #f0f2f6;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin: 20px auto;
        max-width: 800px;
        line-height: 2.2;
    }

    .word-correct { color: #2E7D32; font-size: 32px; font-weight: bold; margin: 0 8px; }
    .word-error { color: #D32F2F; font-size: 32px; font-weight: bold; text-decoration: underline; margin: 0 8px; }
    .word-pending { color: #333333; font-size: 32px; margin: 0 8px; }

    /* تحسين شكل الأزرار */
    .stButton>button { width: 250px; border-radius: 50px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. وظائف المساعدة ---
def clean_text(text):
    t = re.sub(r"[\u064B-\u0652]", "", text)  # حذف التشكيل
    return t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").strip()

def get_warsh_feedback(word):
    rules = {
        "أحد": "قلقلة كبرى عند الوقف - انتبه لجهر الدال.",
        "الصمد": "تغليظ اللام لأنها مفتوحة بعد صاد ساكنة - قلقلة الدال.",
        "كفوا": "لورش: إبدال الهمزة واواً (كُفُواً) مع تحقيق ضمة الفاء.",
        "يولد": "قلقلة صغرى في الدال وسط الكلام."
    }
    return rules.get(clean_text(word), "تأكد من مخرج الحرف وصفته.")

# --- 3. الواجهة الرئيسية ---
st.markdown("<h1 style='color: #1B5E20;'>🕌 مصحح التلاوة التفاعلي</h1>", unsafe_allow_html=True)
st.write("رواية ورش عن نافع")

target_verse = "قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"
target_words = target_verse.split()

# عرض السورة في حالة الانتظار (قبل التسجيل)
placeholder = st.empty()
with placeholder.container():
    html_verse = "<div class='quran-center-container'>"
    for w in target_words:
        html_verse += f"<span class='word-pending'>{w}</span>"
    html_verse += "</div>"
    st.markdown(html_verse, unsafe_allow_html=True)

# تجميع الميكروفون في المنتصف
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    audio_record = mic_recorder(start_prompt="🎤 ابدأ الترتيل", stop_prompt="⏹️ توقف للتحليل", key='warsh_v15')

# --- 4. معالجة النتيجة ---
if audio_record:
    with st.spinner("جاري التحليل..."):
        try:
            # تحويل الصوت والتعرف عليه
            audio_bytes = audio_record['bytes']
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_buf = io.BytesIO()
            audio.export(wav_buf, format="wav")
            wav_buf.seek(0)

            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                audio_data = r.record(source)
                spoken_text = r.recognize_google(audio_data, language="ar-SA")
                spoken_words = [clean_text(w) for w in spoken_text.split()]

            # تحديث الشاشة بالكلمات الملونة
            result_html = "<div class='quran-center-container'>"
            errors = []
            
            for word in target_words:
                c_word = clean_text(word)
                if any(c_word in sw for sw in spoken_words):
                    result_html += f"<span class='word-correct'>{word}</span>"
                else:
                    result_html += f"<span class='word-error'>{word}</span>"
                    errors.append(word)
            
            result_html += "</div>"
            placeholder.markdown(result_html, unsafe_allow_html=True)

            # قسم الملاحظات
            st.markdown("---")
            st.subheader("📋 تقرير الأداء التجويدي")
            
            if not errors:
                st.success("ما شاء الله! قراءة متقنة لفظاً.")
            else:
                for err in set(errors):
                    with st.expander(f"تحليل كلمة: {err}"):
                        st.write(f"**القاعدة:** {get_warsh_feedback(err)}")
                        st.info("نصيحة: استمع للمقرئ الحصري (ورش) لضبط هذا الموضع.")
            
            # عرض صورة توضيحية للمخارج لزيادة الفائدة
            st.markdown("#### توضيح مخارج الحروف العربية")
            

        except Exception as e:
            st.warning("تعذر التعرف على الصوت بوضوح، حاول القراءة ببطء وترتيل.")
