import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import re
from streamlit_mic_recorder import mic_recorder
from pydub import AudioSegment

# --- 1. إعدادات الحالة والذاكرة ---
if 'total_score' not in st.session_state: st.session_state.total_score = 0
if 'stars' not in st.session_state: st.session_state.stars = 0
if 'recognized_words' not in st.session_state: st.session_state.recognized_words = []
if 'is_hidden' not in st.session_state: st.session_state.is_hidden = False

st.set_page_config(page_title="مقرأة ورش - التقييم الذكي", layout="wide")

# --- 2. تحميل البيانات والمخارج ---
@st.cache_data
def load_tajweed_rules():
    try:
        # تأكد من وجود الملف arabic_phonetics.csv بجانب الكود
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8')
    except:
        return None

df_rules = load_tajweed_rules()

# --- 3. التصميم الجمالي (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri:wght@700&display=swap');
    html, body, [class*="st-"] { font-family: 'Amiri', serif; direction: rtl; text-align: center; }
    
    .score-board {
        background: linear-gradient(135deg, #1e5d2f 0%, #2e7d32 100%);
        padding: 20px; border-radius: 20px; color: gold;
        box-shadow: 0 8px 20px rgba(0,0,0,0.2); margin-bottom: 25px;
    }
    .quran-frame {
        background-color: #fffcf2; padding: 40px; border-radius: 25px;
        border: 10px double #2e7d32; margin-bottom: 20px;
    }
    .word-correct { font-family: 'Amiri Quran', serif; font-size: 48px; color: #2e7d32; font-weight: bold; }
    .word-pending { font-family: 'Amiri Quran', serif; font-size: 48px; color: #2e7d32; opacity: 0.15; }
    .word-hidden { background-color: #d1d1d1; color: #d1d1d1; border-radius: 10px; font-size: 48px; margin: 0 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. بيانات السورة مع توزيع النقاط حسب الحكم ---
# تم توزيع النقاط (Points) بناءً على صعوبة الحكم في رواية ورش
surah_data = [
    {"text": "إِنَّآ", "clean": "ان", "letter": "ن", "points": 30, "rule": "مد مشبع 6 حركات + غنة"},
    {"text": "أَعْطَيْنَٰكَ", "clean": "اعطيناك", "letter": "ع", "points": 20, "rule": "تحقيق مخرج العين"},
    {"text": "اَ۬لْكَوْثَرَ", "clean": "الكوثر", "letter": "ث", "points": 20, "rule": "مخرج الثاء وترقيق الراء"},
    {"text": "فَصَلِّ", "clean": "فصل", "letter": "ل", "points": 25, "rule": "تغليظ اللام عند ورش"},
    {"text": "لِرَبِّكَ", "clean": "لربك", "letter": "ر", "points": 15, "rule": "ترقيق الراء"},
    {"text": "وَانْحَرْۖ", "clean": "وانحر", "letter": "ح", "points": 25, "rule": "إظهار النون عند الحاء"},
    {"text": "إِنَّ", "clean": "ان", "letter": "ن", "points": 20, "rule": "غنة أكمل ما تكون"},
    {"text": "شَانِئَكَ", "clean": "شانئك", "letter": "ش", "points": 15, "rule": "تفشي الشين"},
    {"text": "هُوَ", "clean": "هو", "letter": "ه", "points": 10, "rule": "مخرج الهاء"},
    {"text": "اَ۬لَابْتَرُۖ", "clean": "الابتر", "letter": "ب", "points": 40, "rule": "حكم النقل + قلقلة الباء"}
]

st.title("🕌 مقرأة ورش: التقييم والمكافآت")

# لوحة النتائج
stars_display = "⭐" * st.session_state.stars
st.markdown(f"""
    <div class='score-board'>
        <h2 style='color: white; margin:0;'>النتيجة الإجمالية: {st.session_state.total_score}</h2>
        <div style='font-size: 30px;'>{stars_display}</div>
        <p style='color: #e0e0e0; margin:0;'>أتقنت {len(st.session_state.recognized_words)} من أصل {len(surah_data)} كلمات</p>
    </div>
    """, unsafe_allow_html=True)

# أزرار التحكم
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("👁️ إظهار السورة"): st.session_state.is_hidden = False; st.rerun()
with c2:
    if st.button("🙈 وضع الاختبار"): st.session_state.is_hidden = True; st.rerun()
with c3:
    if st.button("🔄 إعادة التحدي"): 
        st.session_state.recognized_words = []; st.session_state.total_score = 0; st.session_state.stars = 0; st.rerun()

# عرض المصحف
html = "<div class='quran-frame'>"
for item in surah_data:
    if item['clean'] in st.session_state.recognized_words:
        html += f"<span class='word-correct'>{item['text']}</span> "
    elif st.session_state.is_hidden:
        html += f"<span class='word-hidden'>&nbsp;{item['text']}&nbsp;</span> "
    else:
        html += f"<span class='word-pending'>{item['text']}</span> "
html += "</div>"
st.markdown(html, unsafe_allow_html=True)

st.divider()

# --- 5. محرك التقييم الصارم ---
st.subheader("🎤 رتّل الآن للحصول على التقييم")
audio = mic_recorder(start_prompt="ابدأ التلاوة", stop_prompt="إنهاء للتقييم", key='eval_mic')

if audio:
    with st.spinner("⏳ جاري تحليل الأحكام والمخارج..."):
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
                
                new_points = 0
                for item in surah_data:
                    if item['clean'] in spoken_words and item['clean'] not in st.session_state.recognized_words:
                        # منح نقاط بناءً على الحكم التجويدي للكلمة
                        st.session_state.recognized_words.append(item['clean'])
                        st.session_state.total_score += item['points']
                        new_points += item['points']
                
                if new_points > 0:
                    # تحديث النجوم: نجمة لكل 50 نقطة
                    st.session_state.stars = st.session_state.total_score // 50
                    st.balloons()
                    st.success(f"ممتاز! حصلت على {new_points} نقطة إضافية لتطبيقك أحكام ورش.")
                else:
                    st.error(f"لم يتم مطابقة كلمات جديدة. تأكد من مخارج الحروف. سمعتُ: {text}")
                
                st.rerun()
        except:
            st.warning("يرجى القراءة بوضوح أكبر وبصوت مسموع.")

# --- 6. عرض نصيحة المخرج عند الخطأ (من CSV) ---
if df_rules is not None:
    with st.expander("📍 دليل تصحيح الأحكام (بناءً على تلاوتك)"):
        for item in surah_data:
            if item['clean'] not in st.session_state.recognized_words:
                rule_info = df_rules[df_rules['letter'] == item['letter']]
                if not rule_info.empty:
                    st.write(f"**كلمة {item['text']}:** مطلوب {item['rule']}.")
                    st.
