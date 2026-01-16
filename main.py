import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import numpy as np
import soundfile as sf
import re
from streamlit_mic_recorder import mic_recorder

# --- 1. إعدادات الصفحة والجماليات (مع حل مشكلة التداخل) ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { 
        font-family: 'Amiri', serif; 
        direction: rtl; 
        text-align: right; 
    }
    /* تحسين شكل الحاويات ومنع تداخل النصوص مع الأيقونات */
    .st-emotion-cache-p4m61c { 
        flex-direction: row-reverse !important; 
    }
    .quran-container {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .stButton>button { 
        background-color: #2E7D32; color: white; border-radius: 10px; 
        width: 100%; height: 3.5em; font-size: 18px;
    }
    /* تنسيق الجداول داخل القوائم المنسدلة */
    .stDataFrame { margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل البيانات في الخلفية ---
@st.cache_data
def load_rules():
    if os.path.exists('arabic_phonetics.csv'):
        # تحميل الأعمدة: letter, name, place, rule_category, emphasis, ipa
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_rules()

# --- 3. محرك التحليل والتصحيح ---

def get_tajweed_analysis(word):
    """استخراج بيانات التجويد لكل حرف في الكلمة من ملف CSV"""
    analysis = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                analysis.append({
                    'الحرف': row['letter'],
                    'المخرج': row['place'],
                    'الحكم': row['rule_category'],
                    'الصفة': row['emphasis']
                })
    return analysis

def process_audio_raw(audio_bytes):
    """معالجة الصوت الخام وحساب زمن المد لتجنب أخطاء التنسيق"""
    # قراءة البيانات الصوتية مباشرة
    with io.BytesIO(audio_bytes) as audio_file:
        data, samplerate = sf.read(audio_file)
    
    if len(data.shape) > 1: data = np.mean(data, axis=1) # تحويل لـ Mono
    
    # حساب المد (6 حركات لورش)
    rms = librosa.feature.rms(y=data)[0]
    threshold = np.max(rms) * 0.25
    mad_duration = np.sum(rms > threshold) * (512 / samplerate)
    
    # تصدير لملف WAV متوافق مع محرك البحث في الذاكرة
    buf = io.BytesIO()
    sf.write(buf, data, samplerate, format='WAV', subtype='PCM_16')
    buf.seek(0)
    return round(mad_duration, 2), buf

# --- 4. واجهة المستخدم ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مقرأة ورش الإلكترونية</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>تصحيح الأحكام والمخارج بناءً على قواعد البيانات</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📖 إعدادات المصحح")
    target_text = st.text_area("الآية المستهدفة:", "إنا أعطيناك الكوثر")
    st.info("💡 يتم تحليل كل كلمة تنطقها وربطها بأحكام التجويد في ملفك الخاص.")

# تسجيل الصوت
audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة بالترتيل", stop_prompt="⏹️ توقف واطلب التصحيح", key='warsh_v12')

if audio_record:
    audio_bytes = audio_record['bytes']
    
    with st.spinner("⏳ جاري تحليل الأداء التجويدي..."):
        try:
            # معالجة الصوت وحساب المد
            mad_time, wav_buffer = process_audio_raw(audio_bytes)
            
            # التعرف على النص
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                r.adjust_for_ambient_noise(source)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # حساب الدقة اللفظية
            norm_target = re.sub(r"[إأآا]", "ا", target_text)
            norm_spoken = re.sub(r"[إأآا]", "ا", spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # --- عرض التقرير النهائي ---
            st.markdown("<div class='quran-container'>", unsafe_allow_html=True)
            st.subheader(f"النتيجة: {accuracy}%")
            st.write(f"**المنطوق:** {spoken_text}")
            
            st.divider()
            st.markdown("### 📋 تصحيح الأحكام والمخارج (بناءً على ملفك):")
            
            words = target_text.split()
            for word in words:
                tajweed_info = get_tajweed_analysis(word)
                if tajweed_info:
                    # استخدام expander مع جدول منسق يمنع تداخل الأيقونات
                    with st.expander(f"📖 أحكام كلمة: {word}"):
                        st.dataframe(
                            pd.DataFrame(tajweed_info),
                            use_container_width=True,
                            hide_index=True
                        )
            
            # تقييم زمن المد
            if mad_time < 3.0:
                st.warning(f"⚠️ زمن المد ({mad_time} ث) قصير. تذكر إشباع المد لـ 6 حركات في رواية ورش.")
            else:
                st.success(f"✅ إتقان ممتاز! زمن المد ({mad_time} ث) يتوافق مع طريق الأزرق.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ تعذر التحليل: يرجى الترتيل بوضوح. (السبب: {e})")import streamlit as st
import pandas as pd
import speech_recognition as sr
import io
import difflib
import os
import librosa
import numpy as np
import soundfile as sf
import re
from streamlit_mic_recorder import mic_recorder

# --- 1. إعدادات الصفحة والجماليات (مع حل مشكلة التداخل) ---
st.set_page_config(page_title="مقرأة ورش الذكية", layout="centered", page_icon="🕌")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&display=swap');
    html, body, [class*="st-"] { 
        font-family: 'Amiri', serif; 
        direction: rtl; 
        text-align: right; 
    }
    /* تحسين شكل الحاويات ومنع تداخل النصوص مع الأيقونات */
    .st-emotion-cache-p4m61c { 
        flex-direction: row-reverse !important; 
    }
    .quran-container {
        background-color: #fcfdfc; padding: 25px; border-radius: 15px;
        border-right: 10px solid #2E7D32; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .stButton>button { 
        background-color: #2E7D32; color: white; border-radius: 10px; 
        width: 100%; height: 3.5em; font-size: 18px;
    }
    /* تنسيق الجداول داخل القوائم المنسدلة */
    .stDataFrame { margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل البيانات في الخلفية ---
@st.cache_data
def load_rules():
    if os.path.exists('arabic_phonetics.csv'):
        # تحميل الأعمدة: letter, name, place, rule_category, emphasis, ipa
        return pd.read_csv('arabic_phonetics.csv', encoding='utf-8-sig')
    return None

df_rules = load_rules()

# --- 3. محرك التحليل والتصحيح ---

def get_tajweed_analysis(word):
    """استخراج بيانات التجويد لكل حرف في الكلمة من ملف CSV"""
    analysis = []
    if df_rules is not None:
        clean_word = re.sub(r"[\u064B-\u0652]", "", word)
        for char in clean_word:
            match = df_rules[df_rules['letter'] == char]
            if not match.empty:
                row = match.iloc[0]
                analysis.append({
                    'الحرف': row['letter'],
                    'المخرج': row['place'],
                    'الحكم': row['rule_category'],
                    'الصفة': row['emphasis']
                })
    return analysis

def process_audio_raw(audio_bytes):
    """معالجة الصوت الخام وحساب زمن المد لتجنب أخطاء التنسيق"""
    # قراءة البيانات الصوتية مباشرة
    with io.BytesIO(audio_bytes) as audio_file:
        data, samplerate = sf.read(audio_file)
    
    if len(data.shape) > 1: data = np.mean(data, axis=1) # تحويل لـ Mono
    
    # حساب المد (6 حركات لورش)
    rms = librosa.feature.rms(y=data)[0]
    threshold = np.max(rms) * 0.25
    mad_duration = np.sum(rms > threshold) * (512 / samplerate)
    
    # تصدير لملف WAV متوافق مع محرك البحث في الذاكرة
    buf = io.BytesIO()
    sf.write(buf, data, samplerate, format='WAV', subtype='PCM_16')
    buf.seek(0)
    return round(mad_duration, 2), buf

# --- 4. واجهة المستخدم ---
st.markdown("<h1 style='text-align: center; color: #1B5E20;'>🕌 مقرأة ورش الإلكترونية</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>تصحيح الأحكام والمخارج بناءً على قواعد البيانات</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📖 إعدادات المصحح")
    target_text = st.text_area("الآية المستهدفة:", "إنا أعطيناك الكوثر")
    st.info("💡 يتم تحليل كل كلمة تنطقها وربطها بأحكام التجويد في ملفك الخاص.")

# تسجيل الصوت
audio_record = mic_recorder(start_prompt="🎤 ابدأ التلاوة بالترتيل", stop_prompt="⏹️ توقف واطلب التصحيح", key='warsh_v12')

if audio_record:
    audio_bytes = audio_record['bytes']
    
    with st.spinner("⏳ جاري تحليل الأداء التجويدي..."):
        try:
            # معالجة الصوت وحساب المد
            mad_time, wav_buffer = process_audio_raw(audio_bytes)
            
            # التعرف على النص
            r = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                r.adjust_for_ambient_noise(source)
                audio_recorded = r.record(source)
                spoken_text = r.recognize_google(audio_recorded, language="ar-SA")
            
            # حساب الدقة اللفظية
            norm_target = re.sub(r"[إأآا]", "ا", target_text)
            norm_spoken = re.sub(r"[إأآا]", "ا", spoken_text)
            accuracy = round(difflib.SequenceMatcher(None, norm_target.split(), norm_spoken.split()).ratio() * 100, 1)

            # --- عرض التقرير النهائي ---
            st.markdown("<div class='quran-container'>", unsafe_allow_html=True)
            st.subheader(f"النتيجة: {accuracy}%")
            st.write(f"**المنطوق:** {spoken_text}")
            
            st.divider()
            st.markdown("### 📋 تصحيح الأحكام والمخارج (بناءً على ملفك):")
            
            words = target_text.split()
            for word in words:
                tajweed_info = get_tajweed_analysis(word)
                if tajweed_info:
                    # استخدام expander مع جدول منسق يمنع تداخل الأيقونات
                    with st.expander(f"📖 أحكام كلمة: {word}"):
                        st.dataframe(
                            pd.DataFrame(tajweed_info),
                            use_container_width=True,
                            hide_index=True
                        )
            
            # تقييم زمن المد
            if mad_time < 3.0:
                st.warning(f"⚠️ زمن المد ({mad_time} ث) قصير. تذكر إشباع المد لـ 6 حركات في رواية ورش.")
            else:
                st.success(f"✅ إتقان ممتاز! زمن المد ({mad_time} ث) يتوافق مع طريق الأزرق.")
            
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ تعذر التحليل: يرجى الترتيل بوضوح. (السبب: {e})")
