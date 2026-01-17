import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
import speech_recognition as sr
import io
import re
import time
import random
import datetime
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment
from fpdf import FPDF

# --- 1. إعدادات الواجهة والذاكرة ---
st.set_page_config(page_title="مقرأة ورش الاحترافية", layout="wide", page_icon="🕌")

if 'history' not in st.session_state: st.session_state.history = []
if 'high_scores' not in st.session_state: st.session_state.high_scores = {}
if 'daily_seed' not in st.session_state: st.session_state.daily_seed = datetime.date.today().strftime("%Y%m%d")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    .quran-container {
        background-color: #ffffff; padding: 35px; border-radius: 25px;
        border: 2px solid #2E7D32; margin: 20px auto; max-width: 950px;
        display: flex; flex-wrap: wrap; justify-content: center; gap: 15px;
    }
    .word-correct { color: #2E7D32; font-size: 38px; font-weight: bold; }
    .word-error { color: #D32F2F; font-size: 38px; font-weight: bold; text-decoration: underline; }
    .word-pending { color: #444444; font-size: 38px; }
    .challenge-box { background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); padding: 20px; border-radius: 15px; border-right: 8px solid #2E7D32; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. البيانات والوظائف المساعدة ---
surahs = {
    "سورة الكوثر": "إِنَّا أَعْطَيْنَاكَ الْكَوْثَرَ فَصَلِّ لِرَبِّكَ وَانْحَرْ إِنَّ شَانِئَكَ هُوَ الْأَبْتَرُ",
    "سورة الإخلاص": "قُلْ هُوَ اللَّهُ أَحَدٌ اللَّهُ الصَّمَدُ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ",
    "سورة الفاتحة": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ الرَّحْمَنِ الرَّحِيمِ مَالِكِ يَوْمِ الدِّينِ إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ"
}

def clean_text(text): 
    return re.sub(r"[\u064B-\u0652]", "", text).strip()

def generate_cert(user_name, surah, acc):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.rect(10, 10, 277, 190)
    pdf.set_font("Arial", 'B', 30)
    pdf.cell(0, 50, "Certificate of Recitation Mastery", ln=True, align='C')
    pdf.set_font("Arial", '', 20)
    pdf.cell(0, 20, f"This certifies that {user_name}", ln=True, align='C')
    pdf.cell(0, 20, f"Mastered {surah} with {acc}% Accuracy", ln=True, align='C')
    pdf.cell(0, 30, f"Date: {datetime.date.today()}", ln=True, align='C')
    return pdf.output(dest='S')

# --- 3. تصميم واجهة التبويبات ---
st.title("🕌 منصة ورش التعليمية الذكية")
tab1, tab2, tab3 = st.tabs(["🎯 الاختبار والتحدي", "🔬 المختبر الترددي", "📈 الإحصائيات"])

with tab1:
    random.seed(st.session_state.daily_seed)
    daily_s = random.choice(list(surahs.keys()))
    st.markdown(f"<div class='challenge-box'><h3>🎯 تحدي اليوم: {daily_s}</h3></div>", unsafe_allow_html=True)
    
    selected_s = st.selectbox("اختر سورة للاختبار:", list(surahs.keys()))
    target_v = surahs[selected_s]
    target_w = target_v.split()
    
    placeholder = st.empty()
    placeholder.markdown(f"<div class='quran-container'>{' '.join([f'<span class=word-pending>{w}</span>' for w in target_w])}</div>", unsafe_allow_html=True)
    
    audio = mic_recorder(start_prompt="🎤 ابدأ الترتيل", stop_prompt="⏹️ توقف للتحليل", key='main_recorder')

    if audio:
        with st.spinner("⏳ جاري تحسين جودة الصوت وتحليل تلاوتك..."):
            try:
                # تحويل الصوت وتطبيعه (Normalization) لزيادة الوضوح
                raw_audio = AudioSegment.from_file(io.BytesIO(audio['bytes']))
                raw_audio = raw_audio.normalize() 
                
                duration = len(raw_audio) / 1000.0
                
                # تصدير بصيغة WAV قياسية متوافقة تماماً مع SpeechRecognition
                wav_io = io.BytesIO()
                raw_audio.export(wav_io, format="wav", parameters=["-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000"])
                wav_io.seek(0)
                
                r = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    r.adjust_for_ambient_noise(source, duration=0.3)
                    audio_data = r.record(source)
                    spoken = r.recognize_google(audio_data, language="ar-SA")
                
                spoken_w = [clean_text(w) for w in spoken.split()]
                
                res_html = "<div class='quran-container'>"
                correct = 0
                for w in target_w:
                    if clean_text(w) in spoken_w:
                        res_html += f"<span class='word-correct'>{w}</span> "
                        correct += 1
                    else:
                        res_html += f"<span class='word-error'>{w}</span> "
                res_html += "</div>"
                placeholder.markdown(res_html, unsafe_allow_html=True)
                
                acc = (correct / len(target_w)) * 100
                wpm = (correct / duration) * 60 if duration > 0 else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("🎯 الدقة", f"{round(acc)}%")
                c2.metric("⏱️ الزمن", f"{round(duration, 1)} ث")
                c3.metric("🚀 الطلاقة", f"{round(wpm)} كلمة/د")
                
                st.session_state.history.append({"سورة": selected_s, "دقة": acc, "سرعة": wpm})
                
                if acc >= 90:
                    st.success("🏆 إتقان مذهل!")
                    u_name = st.text_input("اسمك للشهادة:", "هاني معمري")
                    if st.button("📄 إصدار الشهادة"):
                        pdf_data = generate_cert(u_name, selected_s, round(acc))
                        st.download_button("تحميل الشهادة", pdf_data, f"Cert_{selected_s}.pdf", "application/pdf")
            except sr.UnknownValueError:
                st.error("⚠️ لم يتمكن المحرك من تمييز الكلمات. حاول القراءة ببطء ووضوح أكثر.")
            except Exception as e:
                st.error(f"⚠️ حدث خطأ أثناء التحليل: {e}")

with tab2:
    st.subheader("🔬 تحليل مخارج الحروف (بصمة الصوت)")
    test_char = st.selectbox("اختر حرفاً للتحليل:", ["ق", "د", "س", "ر"])
    q_audio = mic_recorder(start_prompt=f"انطق حرف ({test_char})", stop_prompt="تحليل", key='q_mic')
    if q_audio:
        y, sr_rate = librosa.load(io.BytesIO(q_audio['bytes']), sr=22050)
        fig, ax = plt.subplots()
        S = librosa.feature.melspectrogram(y=y, sr=sr_rate)
        librosa.display.specshow(librosa.power_to_db(S, ref=np.max), ax=ax, y_axis='mel', x_axis='time')
        st.pyplot(fig)

with tab3:
    st.subheader("📈 سجل الأداء")
    if st.session_state.history:
        df_hist = pd.DataFrame(st.session_state.history)
        st.line_chart(df_hist['دقة'])
        st.table(df_hist)
    else: st.write("لا توجد بيانات مسجلة حالياً.")
