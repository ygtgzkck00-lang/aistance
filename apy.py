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
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error(
        "GEMINI_API_KEY bulunamadı. "
        "Streamlit Cloud > Settings > Secrets "
        "bölümüne API anahtarını ekle."
    )
    st.stop()

client = genai.Client(api_key=api_key)

# GÜNLÜK SORU SAYACI VE SOHBET GEÇMİŞİ

bugun = date.today().isoformat()

if "kullanim_tarihi" not in st.session_state or st.session_state.kullanim_tarihi != bugun:
    st.session_state.kullanim_tarihi = bugun
    st.session_state.soru_sayisi = 0

if "messages" not in st.session_state:
    st.session_state.messages = []

kalan_hak = max(0, GUNLUK_SORU_LIMITI - st.session_state.soru_sayisi)
st.info(f"📊 Bugünkü kalan soru hakkın: **{kalan_hak} / {GUNLUK_SORU_LIMITI}**")

# ÖNCEKİ MESAJLARI GÖSTER

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            kaynak_metni = "\n\n### 🔎 Yararlanılan Kaynaklar\n"
            for kaynak in message["sources"]:
                kaynak_metni += f"- [{kaynak['title']}]({kaynak['url']})\n"
            st.markdown(kaynak_metni)

# GOOGLE SEARCH KAYNAKLARINI AL

def kaynaklari_al(response):
    kaynaklar = []
    try:
        for candidate in response.candidates or []:
            metadata = candidate.grounding_metadata
            if not metadata:
                continue
            for chunk in metadata.grounding_chunks or []:
                web = getattr(chunk, "web", None)
                if web:
                    url = getattr(web, "uri", None)
                    title = getattr(web, "title", None)
                    if url and url not in [k["url"] for k in kaynaklar]:
                        kaynaklar.append({
                            "title": title or "Web kaynağı",
                            "url": url
                        })
    except Exception:
        pass
    return kaynaklar

# YENİ MESAJI İŞLE

if kalan_hak <= 0:
    st.warning("Günlük 3 soru kullanım hakkın doldu. Yarın tekrar deneyebilirsin.")
    prompt = st.chat_input(
        "Günlük soru limitin doldu (3/3)...",
        disabled=True
    )
else:
    prompt = st.chat_input("BAUN hakkında merak ettiğini sor...")

if prompt:
    if st.session_state.soru_sayisi >= GUNLUK_SORU_LIMITI:
        st.warning("Günlük 3 soru kullanım hakkın doldu. Yarın tekrar deneyebilirsin.")
        st.stop()

    st.session_state.soru_sayisi += 1

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    contents = [
        types.Content(
            role="user" if message["role"] == "user" else "model",
            parts=[types.Part.from_text(text=message["content"])],
        )
        for message in st.session_state.messages
    ]

    with st.chat_message("assistant"):
        with st.spinner("BAUN Asistan interneti araştırıyor..."):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=BOT_KARAKTERI,
                        tools=[
                            types.Tool(
                                google_search=types.GoogleSearch()
                            )
                        ],
                    ),
                )

                answer = response.text or (
                    "Şu an yanıt oluşturamadım. Lütfen tekrar dene."
                )
                kaynaklar = kaynaklari_al(response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": kaynaklar
                })

                st.rerun()

            except Exception as error:
                st.session_state.soru_sayisi = max(0, st.session_state.soru_sayisi - 1)
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                    st.session_state.messages.pop()
                st.error(
                    "Gemini API isteği başarısız oldu.\n\n"
                    "Model adını, API anahtarını ve "
                    "Google Search desteğini kontrol et.\n\n"
                    f"Teknik hata: {error}"
                )
