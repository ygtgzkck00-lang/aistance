import streamlit as st
from google import genai
from google.genai import types

# --- ÖZELLEŞTİRME ALANI ---
BOT_ADI = "Benim Özel Asistanım"
BOT_ACIKLAMA = "Arkadaşlarım için özel olarak hazırlanmış yapay zeka asistanı."
BOT_KARAKTERI = """
Sen samimi, esprili ve yardımsever bir asistansın.
Cevaplarını kısa, akıcı ve doğal tut.
"""
YARATICILIK = 0.3  # 0.0 (daha ciddi/net) ile 1.0 (daha yaratıcı/esnek) arası
# ---------------------------

st.set_page_config(page_title=BOT_ADI, page_icon="🤖")
st.title(f"🤖 {BOT_ADI}")
st.caption(BOT_ACIKLAMA)

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Mesajını buraya yaz..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in st.session_state.messages
    ]

    with st.chat_message("assistant"):
        with st.spinner("Düşünüyor..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=BOT_KARAKTERI,
                    temperature=YARATICILIK,
                ),
            )
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
