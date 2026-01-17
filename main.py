import streamlit as st
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import io
from streamlit_mic_recorder import mic_recorder

# --- 1. دالة مقارنة الموجات الصوتية (البصمة الصوتية) ---
def compare_audio_waves(recorded_y, sr_rate):
    """
    مقارنة ترددات المستخدم مع موجة مرجعية (أو تحليل خصائصها)
    """
    # استخراج الـ Mel-spectrogram
    S = librosa.feature.melspectrogram(y=recorded_y, sr=sr_rate, n_mels=128)
    S_db = librosa.power_to_db(S, ref=np.max)
    
    return S_db

# --- 2. واجهة المختبر الصوتي ---
st.markdown("### 🔬 مختبر التحليل الترددي للمخارج")
st.write("هذا الجزء يحلل 'بصمة صوتك' ويقارنها بخصائص الحرف الصوتية.")

# اختيار الحرف للاختبار الترددي
char_to_test = st.selectbox("اختر حرفاً للتحليل الترددي:", ["ق", "ط", "د", "س"])

# تسجيل الصوت للتحليل
audio_data = mic_recorder(start_prompt=f"انطق حرف ({char_to_test}) بوضوح للتحليل", 
                          stop_prompt="تحليل البصمة الصوتية", 
                          key='spectro_mic')

if audio_data:
    try:
        # قراءة البيانات الصوتية
        audio_bytes = audio_data['bytes']
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=22050)
        
        # استخراج البصمة
        spectrogram = compare_audio_waves(y, sr)
        
        # إنشاء الرسم البياني
        fig, ax = plt.subplots(figsize=(10, 4))
        img = librosa.display.specshow(spectrogram, x_axis='time', y_axis='mel', sr=sr, ax=ax)
        plt.colorbar(img, ax=ax, format='%+2.0f dB')
        plt.title(f"البصمة الصوتية لنطق حرف ({char_to_test})")
        
        # عرض الرسم في Streamlit
        st.pyplot(fig)
        
        # تحليل قوة النطق (نبرة الحرف)
        power = np.mean(librosa.feature.rms(y=y))
        st.write(f"📊 قوة دفع الهواء في الحرف: {round(power * 100, 2)} وحدة")
        
        if char_to_test in ["ق", "ط"] and power < 0.05:
            st.warning("⚠️ تنبيه: نطقك للحرف ضعيف (يحتاج قوة استعلاء). حاول ضغط الهواء أكثر في المخرج.")
        elif char_to_test == "س" and power > 0.1:
            st.info("✅ نطق حاد وواضح (صفير سليم).")

    except Exception as e:
        st.error(f"خطأ في تحليل الموجة: {e}")
