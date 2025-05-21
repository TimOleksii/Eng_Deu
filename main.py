# Для запуска приложения установите streamlit командой:
# pip install streamlit

try:
    import streamlit as st
    import pandas as pd
    import random
    import datetime
    import pyperclip
except ModuleNotFoundError as e:
    print("Необходимый модуль не найден:", e)
    print("Установите его командой: pip install streamlit")
    exit(1)

# === Настройки ===
LANGUAGES = ["Немецкие слова", "Немецкие фразы", "Английские слова", "Английские фразы"]
FILES = {
    "Немецкие слова": "german_words.xlsx",
    "Немецкие фразы": "german_phrases.xlsx",
    "Английские слова": "english_words.xlsx",
    "Английские фразы": "english_phrases.xlsx"
}

# === Загрузка или создание файлов ===
def load_data(category):
    file_path = FILES[category]
    try:
        return pd.read_excel(file_path)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["Word", "Translation", "Level", "Last_Review"])
        df.to_excel(file_path, index=False)
        return df

def save_data(category, df):
    df.to_excel(FILES[category], index=False)

# === Логика выбора слов ===
def is_due(last_review, level):
    if pd.isna(last_review) or level == 0:
        return True
    days_passed = (datetime.datetime.now() - pd.to_datetime(last_review)).days
    if level == 5:
        return days_passed >= 60
    return days_passed >= 2 ** level

def get_due_words(df):
    df_due = df[df.apply(lambda row: is_due(row["Last_Review"], row["Level"]), axis=1)]
    if df_due.empty:
        return None
    max_level = df_due["Level"].max()
    return df_due[df_due["Level"] == max_level]

# === Интерфейс Streamlit ===
st.set_page_config(page_title="Языковой Тренажер", layout="centered")
st.title("🧠 Тренажёр немецких и английских слов/фраз")

category = st.radio("Режим тренировки / редактирования", LANGUAGES, index=2, horizontal=True)
df = load_data(category)

menu = st.sidebar.radio("Меню", ["Добавить слово", "Тренировка", "Просмотр словаря"])

if menu == "Добавить слово":
    st.subheader("Добавление нового слова или фразы")
    word = st.text_input("Слово / фраза")
    translation = st.text_input("Перевод (на русский)")
    if st.button("Добавить") and word and translation:
        new_row = {
            "Word": word.strip(),
            "Translation": translation.strip(),
            "Level": 0,
            "Last_Review": pd.NaT
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(category, df)
        st.success("Слово или фраза добавлены!")

elif menu == "Тренировка":
    st.subheader("🔁 Тренировка")
    due_words = get_due_words(df)

    if due_words is None or due_words.empty:
        st.info("Нет слов или фраз для тренировки. Попробуйте позже или добавьте новые записи.")
    else:
        word_row = due_words.sample(1).iloc[0]
        st.markdown(f"**{word_row['Word']}**")

        if st.button("📋 Копировать для тренировки"):
            pyperclip.copy(f"{word_row['Word']} тренировка")
            st.success("Скопировано!")

        if st.checkbox("Показать перевод"):
            st.markdown(f"_Перевод: {word_row['Translation']}_")

        col1, col2, col3 = st.columns(3)
        if col1.button("⬆️ Повысить уровень"):
            df.loc[(df["Word"] == word_row["Word"]) & (df["Translation"] == word_row["Translation"]), "Level"] += 1
            df.loc[(df["Word"] == word_row["Word"]) & (df["Translation"] == word_row["Translation"]), "Last_Review"] = datetime.datetime.now()
            save_data(category, df)
            st.rerun()

        if col2.button("➡️ Оставить как есть"):
            df.loc[(df["Word"] == word_row["Word"]) & (df["Translation"] == word_row["Translation"]), "Last_Review"] = datetime.datetime.now()
            save_data(category, df)
            st.rerun()

        if col3.button("⬇️ Понизить уровень"):
            idx = (df["Word"] == word_row["Word"]) & (df["Translation"] == word_row["Translation"])
            df.loc[idx, "Level"] = df.loc[idx, "Level"].apply(lambda x: max(x - 1, 0))
            df.loc[idx, "Last_Review"] = datetime.datetime.now()
            save_data(category, df)
            st.rerun()

elif menu == "Просмотр словаря":
    st.subheader("📖 Словарь")

    search_term = st.text_input("Поиск по слову или переводу")
    sort_option = st.selectbox("Сортировка по", ["Word", "Translation", "Level", "Last_Review"])
    filtered_df = df[df.apply(lambda row: search_term.lower() in str(row["Word"]).lower() or search_term.lower() in str(row["Translation"]).lower(), axis=1)] if search_term else df
    df_sorted = filtered_df.sort_values(by=sort_option).reset_index(drop=True)

    page_size = 30
    total_pages = (len(df_sorted) - 1) // page_size + 1
    page = st.number_input("Страница", min_value=1, max_value=total_pages, value=1, step=1)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = df_sorted.iloc[start_idx:end_idx]

    selected_rows = []
    for i, row in page_df.iterrows():
        col1, col2 = st.columns([0.05, 0.95])
        with col1:
            selected = st.checkbox("", key=f"sel_{start_idx + i}")
        with col2:
            st.markdown(f"**{row['Word']}** — _{row['Translation']}_")
        if selected:
            selected_rows.append(start_idx + i)

    if len(selected_rows) == 1:
        i = selected_rows[0]
        st.markdown("---")
        st.markdown("**Редактировать выбранное слово**")
        new_word = st.text_input("Новое слово", value=df.loc[i, "Word"], key="edit_word")
        new_translation = st.text_input("Новый перевод", value=df.loc[i, "Translation"], key="edit_translation")
        if st.button("💾 Сохранить изменения"):
            df.at[i, "Word"] = new_word
            df.at[i, "Translation"] = new_translation
            save_data(category, df)
            st.success("Изменения сохранены")

    if selected_rows:
        if st.button("🗑 Удалить выбранные"):
            if st.checkbox("Подтверждаю удаление выбранных записей"):
                df = df.drop(index=selected_rows).reset_index(drop=True)
                save_data(category, df)
                st.success("Записи удалены")

    st.markdown("---")
    st.dataframe(page_df.reset_index(drop=True))
