import streamlit as st
import requests
import json
import pypdf
import docx
import pandas as pd
import os
import base64
import time

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="ШІ-асистент рекрутера",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS СТИЛІЗАЦІЯ ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* ТЕКСТИ */
    .title-text {
        text-align: center;
        color: #2c3e50;
        font-family: 'Helvetica', sans-serif;
        font-weight: bold;
        font-size: 2.5rem;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    
    .subtitle-text {
        text-align: center;
        color: #666;
        font-family: 'Helvetica', sans-serif;
        font-weight: normal;
        font-size: 1.2rem;
        margin-bottom: 30px;
    }
    
    /* ЗАВАНТАЖУВАЧ */
    [data-testid='stFileUploaderDropzone'] div div span { display: none; }
    [data-testid='stFileUploaderDropzone'] div div::after {
        content: "Перетягніть файли сюди • PDF, DOCX";
        visibility: visible;
        display: block;
        font-size: 1rem;
        color: #555;
        margin-bottom: 10px;
    }
    [data-testid='stFileUploaderDropzone'] button { position: relative; color: transparent !important; }
    [data-testid='stFileUploaderDropzone'] button::after {
        content: "Обрати файли";
        position: absolute;
        color: #31333F;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        white-space: nowrap;
    }

    /* АНІМАЦІЯ */
    .loading-text {
        font-size: 24px;
        font-weight: bold;
        color: #FF4500;
        text-align: center;
        padding: 20px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ФУНКЦІЇ ---

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def read_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = pypdf.PdfReader(uploaded_file)
            return "".join([page.extract_text() or "" for page in reader.pages])
        elif uploaded_file.name.endswith('.docx'):
            doc = docx.Document(uploaded_file)
            return "\n".join([p.text for p in doc.paragraphs])
        return ""
    except:
        return ""

def call_gemini_json(api_key, prompt):
    base_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    model_name = "gemini-1.5-flash"
    try:
        r = requests.get(base_url)
        if r.status_code == 200:
            data = r.json()
            for m in data.get('models', []):
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    if 'flash' in m['name']: 
                        model_name = m['name'].replace('models/', '')
                        break
    except: pass

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    final_prompt = prompt + "\n\nReturn the result strictly as a JSON Array of objects."
    data = {
        "contents": [{"parts": [{"text": final_prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code != 200: return f"Error: {response.text}"
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"Error: {str(e)}"

# --- 4. ІНТЕРФЕЙС ---

if 'results_df' not in st.session_state:
    st.session_state.results_df = None

with st.sidebar:
    st.header("🔐 Налаштування")
    api_key = st.text_input("Google API Key", type="password")
    
    # --- РЕАЛЬНА ПЕРЕВІРКА КЛЮЧА ---
    if api_key:
        with st.spinner("Перевіряю ключ..."):
            try:
                # Робимо легкий запит до Google, щоб перевірити доступ
                test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                response = requests.get(test_url)
                
                if response.status_code == 200:
                    st.success("✅ З'єднання встановлено! Ключ активний.")
                else:
                    st.error(f"❌ Ключ не працює. Помилка: {response.status_code}")
            except:
                st.error("❌ Помилка мережі. Перевірте інтернет.")

# --- ШАПКА ---

if os.path.exists("logo.png"):
    img_base64 = get_base64_image("logo.png")
    st.markdown(
        f'<div style="text-align: center; margin-bottom: 20px;">'
        f'<img src="data:image/png;base64,{img_base64}" width="200">'
        f'</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown("<div style='text-align: center;'><h2>👔</h2></div>", unsafe_allow_html=True)

st.markdown('<h1 class="title-text">ШІ-асистент рекрутера</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Ваш персональний помічник у пошуку талантів</p>', unsafe_allow_html=True)

st.markdown("---")

# --- ОСНОВНА ЧАСТИНА ---
c1, c2 = st.columns(2)

# ВАКАНСІЯ
with c1:
    st.subheader("📝 Вакансія") 
    st.caption("Завантажте файл з описом вакансії або вставте текст вручну.")
    
    tab1, tab2 = st.tabs(["📤 Завантажити файл", "✍️ Вставити текст"])
    job_text_final = ""
    with tab1:
        job_file = st.file_uploader("Файл вакансії", type=["pdf", "docx"], key="j_up", label_visibility="collapsed")
        if job_file:
            extracted = read_file(job_file)
            if extracted: job_text_final = extracted; st.success("Файл прочитано")
    with tab2:
        text_input = st.text_area("Вставте текст вакансії:", height=300, key="j_txt")
        if not job_text_final and text_input: job_text_final = text_input

# КАНДИДАТИ
with c2:
    st.subheader("🗂️ Кандидати") 
    st.caption("Додайте резюме кандидатів файлами або текстом для аналізу.")
    
    tab_c1, tab_c2 = st.tabs(["📤 Завантажити файли", "✍️ Вставити текст"])
    
    uploaded_files = []
    candidates_text_input = ""

    with tab_c1:
        uploaded_files = st.file_uploader("Резюме", type=["pdf", "docx"], accept_multiple_files=True, label_visibility="collapsed", key="c_up")
        if uploaded_files: st.info(f"✅ Завантажено файлів: {len(uploaded_files)}")
    
    with tab_c2:
        candidates_text_input = st.text_area("Вставте текст резюме (можна декілька):", height=300, key="c_txt")

st.markdown("###")

# --- КНОПКА ПО ЦЕНТРУ ---
col_space1, col_btn, col_space2 = st.columns([1, 1, 1])

with col_btn:
    # use_container_width=True - це те, що ми зафіксували минулого разу
    start_btn = st.button("Знайти ідеального кандидата", type="primary", use_container_width=True)

if start_btn:
    st.session_state.results_df = None
    
    full_candidates_text = ""
    if uploaded_files:
        for f in uploaded_files:
            content = read_file(f)
            clean_content = content.replace("\n", " ")[:6000]
            full_candidates_text += f"\n--- File: {f.name} ---\n{clean_content}"
    if candidates_text_input:
        full_candidates_text += f"\n--- Pasted Text ---\n{candidates_text_input}"

    if not api_key: st.error("Введіть API Key зліва.")
    elif not job_text_final: st.warning("Відсутній опис вакансії.")
    elif not full_candidates_text: st.warning("Відсутні дані кандидатів.")
    else:
        loading_phrases = ["🧠 Аналізую вимоги...", "⚖️ Вмикаю режим суворого відбору...", "🔍 Шукаю приховані ризики...", "💎 Відсіюю невідповідних кандидатів...", "🚀 Формую фінальний рейтинг..."]
        status_container = st.empty()
        for phrase in loading_phrases:
            status_container.markdown(f'<div class="loading-text">{phrase}</div>', unsafe_allow_html=True)
            time.sleep(0.7)
        
        prompt = f"""
        ##Роль
        Ти — ШІ-асистент рекрутера.
        ##Задачі
        Допомогти в попередній оцінці кандидатів.
        !!ВАЖЛИВО: Оцінюй максимально строго. Відсів важливіше приємних коментарів.
        ##Дані
        Вакансія: {job_text_final}
        Резюме: {full_candidates_text}
        ##Результат (JSON)
        Поверни масив об'єктів:
        1. "Name"
        2. "Age_Exp" (Вік/Досвід)
        3. "Strengths" (Теги плюсів)
        4. "Weaknesses" (Теги мінусів)
        5. "Highlights" (Важливе/Незвичне)
        6. "Score" (1-10)
        7. "Verdict" ("Не варто спілкуватися" [1-3], "Резерв" [4-6], "Запросити" [7-10])
        8. "Risks"
        Мова: Українська.
        """
        raw_response = call_gemini_json(api_key, prompt)
        status_container.empty()
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            df = pd.DataFrame(data)
            if 'Score' in df.columns: df = df.sort_values(by='Score', ascending=False)
            display_df = df.rename(columns={"Name": "Кандидат", "Age_Exp": "Досвід", "Strengths": "Плюси", "Weaknesses": "Мінуси", "Highlights": "Важливе", "Score": "Бал", "Verdict": "Вердикт", "Risks": "Ризики"})
            st.session_state.results_df = display_df
        except Exception as e: st.error("Помилка обробки."); st.code(raw_response)

if st.session_state.results_df is not None:
    df = st.session_state.results_df
    st.success("✅ Аналіз завершено!")
    def color_rows(val):
        s = str(val).lower()
        if 'запросити' in s: return 'background-color: #dcfce7; color: #166534; font-weight: bold'
        if 'не варто' in s: return 'background-color: #fee2e2; color: #991b1b'
        return 'background-color: #fef9c3; color: #854d0e'
    st.dataframe(df.style.map(color_rows, subset=['Вердикт']), use_container_width=True, hide_index=True)
    st.markdown("###")
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Скачати Excel таблицю", data=csv_data, file_name="recruiter_assistant_report.csv", mime="text/csv", use_container_width=True)