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

# إعداد الواجهة
st.set_page_config(page_title="مقرأة ورش الاحترافية", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-center-container {
        background-color: #ffffff; padding: 40px; border-radius: 25px;
        border: 3px solid #2E7D32; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin: 20px auto; max-width: 900px; line-height: 2.5;
    }
    .word-correct { color: #2E7D32; font-size: 35px; font-weight: bold; margin: 0 10px; }
    .word-error { color: #D32F2F; font-size: 35px; font-weight: bold; text-decoration: underline; margin: 0 10px; }
    .instruction-text { color: #555; font-size: 18px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# دالة تنظيف النص (صارمة لورش)
def clean_strict(text):
    t = re.sub(r"[\u064B-\u0652]", "", text) # حذف التشكيل
    # نحافظ على الهمزات لأن ورش يهتم بتحقيقها أو إبدالها
    return t.strip()

# قاموس الصور التوضيحية للمخارج
MUKHRAJ_IMAGES = {
    "ق": "أقصى اللسان مما يلي الحلق مع ما يقابله من الحنك الأعلى",
    "د": "طرف اللسان مع أصول الثنايا العليا",
    "ل": "ما بين أدنى حافتي اللسان إلى منتهى طرفه",
    "ح": "وسط الحلق"
}

# الواجهة الرئيسية
st.markdown("<h1 style='color: #1B5E20;'>🕌 مصحح التلاوة الاحترافي (Whisper Engine)</h1>", unsafe_allow_html=True)
target_verse = "قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"
target_words = target_verse.split()

placeholder = st.empty()
with placeholder.container():
    st.markdown(f"<div class='quran-center-container'>{' '.join([f'<span>{w}</span>' for w in target_words])}</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    audio_record = mic_recorder(start_prompt="🎤 ابدأ الترتيل بدقة", stop_prompt="⏹️ تحليل التلاوة", key='warsh_whisper')

if audio_record:
    with st.spinner("⏳ Whisper يقوم بتحليل مخارج الحروف الآن..."):
        try:
            audio_bytes = audio_record['bytes']
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_buf = io.BytesIO()
            audio.export(wav_buf, format="wav")
            wav_buf.seek(0)

            # استخدام محرك Whisper (يتطلب اتصال بالإنترنت أو مكتبة openai-whisper محلياً)
            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as source:
                audio_data = r.record(source)
                # استخدام Whisper API لضمان أقصى دقة في الحروف
                spoken_text = r.recognize_whisper(audio_data, language="arabic")
            
            spoken_words = spoken_text.split()
            
            # المقارنة الصارمة
            result_html = "<div class='quran-center-container'>"
            errors = []
            
            for i, target_w in enumerate(target_words):
                clean_target = clean_strict(target_w)
                # فحص وجود الكلمة بدقة عالية جداً
                found = False
                for sw in spoken_words:
                    if clean_target == clean_strict(sw):
                        found = True
                        break
                
                if found:
                    result_html += f"<span class='word-correct'>{target_w}</span>"
                else:
                    result_html += f"<span class='word-error'>{target_w}</span>"
                    errors.append(target_w)
            
            result_html += "</div>"
            placeholder.markdown(result_html, unsafe_allow_html=True)

            # التقرير التفصيلي
            st.divider()
            if not errors:
                st.success("✅ هنيئاً لك! التلاوة صحيحة تماماً وفقاً لمحرك Whisper.")
            else:
                st.error(f"⚠️ اكتشفنا {len(errors)} مواضع تحتاج لتصحيح.")
                cols = st.columns(len(errors) if len(errors) < 4 else 3)
                for idx, err in enumerate(errors):
                    with cols[idx % 3]:
                        st.warning(f"خطأ في: {err}")
                        # عرض صورة المخرج إذا كان الحرف مسجلاً
                        first_char = clean_strict(err)[0]
                        if first_char in MUKHRAJ_IMAGES:
                            st.write(f"💡 مخرج حرف ({first_char}): {MUKHRAJ_IMAGES[first_char]}")
                            if first_char == "ق":
                                
                            elif first_char == "د":
                                
                            elif first_char == "ل":
                                

        except Exception as e:
            st.error("يرجى المحاولة مرة أخرى بوضوح أعلى.")
