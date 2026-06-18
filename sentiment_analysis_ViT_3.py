import subprocess
import sys

# Автоматическая проверка и загрузка ИТ-инструментов машинного обучения
try:
    import pandas as pd
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from tqdm import tqdm  # Прогресс-бар
except ModuleNotFoundError:
    print("Инициализация ИИ-окружения. Загружаю библиотеки NLP...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "torch", "transformers", "tqdm"])
    print("Библиотеки машинного обучения установлены! Перезапустите скрипт.")
    sys.exit()

import re

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def run_sentiment_analysis():
    INPUT_FILE = "yandex_reviews_final_3.csv"
    OUTPUT_FILE = "yandex_reviews_analyzed_3.xlsx"

    try:
        df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
        print(f"Датасет успешно загружен. Строк для NLP-анализа: {len(df)}")
    except FileNotFoundError:
        print(f"Ошибка: Файл {INPUT_FILE} не найден.")
        return

    df['Очищенный_Текст'] = df['Текст'].apply(clean_text)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Используемое устройство для ИИ: {device.type.upper()}")

    print("Загрузка стабильной ИИ-модели 'Russian Sentiment BERT'...")

    # ИСПОЛЬЗУЕМ ОТКРЫТУЮ СТАБИЛЬНУЮ МОДЕЛЬ
    model_name = "seara/rubert-base-cased-russian-sentiment"

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device)
        model.eval()
    except Exception as e:
        print(f"Ошибка загрузки новой модели: {e}")
        return

    # У модели seara маппинг классов следующий:
    # 0 - neutral (нейтральный), 1 - positive (позитивный), 2 - negative (негативный)
    label_mapping = {0: 'Нейтральный', 1: 'Позитивный', 2: 'Негативный'}
    sentiments = []

    BATCH_SIZE = 16
    texts = df['Очищенный_Текст'].tolist()

    print("Нейросеть обрабатывает массив отзывов пакетами...")

    for i in tqdm(range(0, len(texts), BATCH_SIZE)):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_texts = [t if t.strip() else "нормально" for t in batch_texts]

        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        predictions = torch.argmax(outputs.logits, dim=1).cpu().numpy()

        for pred in predictions:
            sentiments.append(label_mapping.get(pred, 'Нейтральный'))

    df['Тональность'] = sentiments
    df = df.drop(columns=['Очищенный_Текст'])

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\nАнализ завершен! Создан размеченный датасет: '{OUTPUT_FILE}'")
    print("\nСтатистика распределения тональности:")
    print(df['Тональность'].value_counts())

if __name__ == "__main__":
    run_sentiment_analysis()