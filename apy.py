from datetime import date
import os
import streamlit as st
from google import genai
from google.genai import types

# --- BAUN ASİSTAN AYARLARI ---

BOT_ADI = "BAUN Asistan"

BOT_ACIKLAMA = (
    "Balıkesir Üniversitesi öğrencileri için "
    "yapay zekâ destekli asistan. (Günlük kullanım hakkı: 3 soru)"
)

GUNLUK_SORU_LIMITI = 3

BOT_KARAKTERI = """
Sen BAUN Asistan'sın. Balıkesir Üniversitesi (BAUN)
öğrencilerine yardımcı olan, Türkçe konuşan,
samimi, açık ve güvenilir bir üniversite asistanısın.

Üniversite, fakülteler, meslek yüksekokulları, bölümler,
akademik takvim, kayıt, dersler, sınavlar, not sistemi,
öğrenci işleri, kampüs, yemekhane, yurtlar ve üniversite
hizmetleri hakkında soruları yanıtla.

ÖNEMLİ DOĞRULUK KURALLARI:

- Kesin olmayan bilgileri uydurma.
- Güncel bilgiler için Google Search aracını kullan.
- Özellikle BAUN'un resmî internet sitesini ve resmî
  duyurularını öncelikli kaynak olarak değerlendir.
- Başvuru tarihleri, ücretler, kontenjanlar ve yönetmelikler
  gibi değişebilen bilgileri mümkün olduğunca doğrula.
- Bilgiyi doğrulayamazsan bunu açıkça belirt.
- Tahminlerini kesin bilgi gibi sunma.
- Üniversite dışındaki genel sorulara da yardımcı ol.
- Kısa, anlaşılır ve doğal cevaplar ver.
- Kullanıcıya Türkçe cevap ver.
"""

GEMINI_MODEL = "gemini-2.5-flash"

# ----------------------------

st.set_page_config(
    page_title=BOT_ADI,
    page_icon="🎓"
)

st.title(f"🎓 {BOT_ADI}")
st.caption(BOT_ACIKLAMA)

# API ANAHTARI

api_key = None

try:
    api_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    api_key = None

if not api_key:
    api_key = os.getenv("GEMINI_
