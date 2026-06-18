# NLP-предобработка тестов, импутация данных и базовая визуализация результатов
import subprocess
import sys

# Автоматическая проверка и загрузка библиотек для визуализации данных
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    from wordcloud import WordCloud
except ModuleNotFoundError:
    print("Инициализация графического окружения. Загружаем библиотеки визуализации...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "matplotlib", "seaborn", "wordcloud"]
    )
    print("Все библиотеки визуализации установлены! Перезапустите скрипт.")
    sys.exit()

def create_charts():
    # Читаем наш файл
    INPUT_FILE = "yandex_reviews_analyzed_3.xlsx"

    try:
        df = pd.read_excel(INPUT_FILE)
        print(f"Датасет успешно загружен. Начинаю построение графиков для {len(df)} отзывов...")
    except FileNotFoundError:
        print(f"Ошибка: Файл {INPUT_FILE} не найден. Сначала завершите работу ИИ-модели!")
        return

    # Автоматически восстанавливаем нулевой рейтинг на основе ИИ-анализа тональности
    print("Модуль Data Imputation: восстановление пропущенных рейтингов на основе тональности...")

    def mapping_sentiment_to_stars(sentiment):
        if sentiment == 'Позитивный':
            return 5
        elif sentiment == 'Негативный':
            return 1
        else:
            return 3

    # Перезаписываем нулевой рейтинг реальными оценками от RuBERT
    df['Рейтинг'] = df['Тональность'].apply(mapping_sentiment_to_stars)

    # Настройка стиля графиков
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.size': 12, 'figure.titlesize': 16})

    # ГРАФИК 1: Распределение тональности отзывов (Barplot)
    plt.figure(figsize=(8, 6))
    colors = {'Позитивный': '#2ecc71', 'Нейтральный': '#95a5a6', 'Негативный': '#e74c3c'}

    ax = sns.countplot(
        data=df,
        x='Тональность',
        order=['Позитивный', 'Нейтральный', 'Негативный'],
        palette=colors,
        hue='Тональность',
        legend=False
    )

    # Добавляем точные числовые значения над каждым столбцом
    for p in ax.patches:
        ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 8), textcoords='offset points', fontweight='bold')

    plt.title('Распределение тональности отзывов бренда «Вкусно — и точка»', pad=15)
    plt.xlabel('Класс тональности')
    plt.ylabel('Количество отзывов')
    plt.tight_layout()
    plt.savefig('sentiment_distribution.png', dpi=300)
    plt.close()
    print("График 1 (Распределение тональности) сохранен как 'sentiment_distribution.png'")

    # ГРАФИК 2: Соотношение оценок (Рейтинг 1-5 звезд) (Pie Chart)
    plt.figure(figsize=(7, 7))
    rating_counts = df['Рейтинг'].value_counts().sort_index()

    # Палитра для восстановленных ИИ оценок (1, 3, 5 звезд)
    star_colors = ['#e74c3c', '#95a5a6', '#2ecc71']

    plt.pie(
        rating_counts,
        labels=[f'{x} ★' for x in rating_counts.index],
        autopct='%1.1f%%',
        startangle=140,
        colors=star_colors,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )
    plt.title('Восстановленная структура клиентских оценок (Рейтинг от ИИ)', pad=15)
    plt.tight_layout()
    plt.savefig('rating_pie_chart.png', dpi=300)
    plt.close()
    print("График 2 (Структура оценок) сохранен как 'rating_pie_chart.png'")

    # ГРАФИК 3: Облако тегов (Word Cloud) для Негативных отзывов
    negative_reviews = " ".join(df[df['Тональность'] == 'Негативный']['Текст'].dropna().astype(str)).lower()

    if negative_reviews.strip():
        plt.figure(figsize=(10, 6))

        stop_words = {
            'и', 'в', 'во', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так',
            'его', 'но', 'да', 'ты', 'к', 'у', 'было', 'за', 'вы', 'это', 'был', 'были', 'очень', 'мне',
            'меня', 'только', 'еще', 'ещё', 'когда', 'из', 'заказ', 'точка', 'вкусно', 'вкуснойточка', 'ресторан'
        }

        wordcloud = WordCloud(
            width=1600,
            height=800,
            background_color='white',
            colormap='Reds',
            max_words=50,
            stopwords=stop_words,
            collocations=True,
            collocation_threshold=10
        ).generate(negative_reviews)

        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Облако ключевых маркеров в негативных отзывах (Проблемные зоны)', pad=15)
        plt.tight_layout()
        plt.savefig('negative_wordcloud.png', dpi=300)
        plt.close()
        print("График 3 (Облако негативных тегов) сохранен как 'negative_wordcloud.png'")
    else:
        print("Негативные отзывы отсутствуют, облако тегов пропущено.")

    # Дополнительно сохраняем обновленный Excel, где колонка 'Рейтинг' теперь восстановлена!
    df.to_excel("yandex_reviews_fully_recovered.xlsx", index=False)
    print("Восстановленный датасет с адресами сохранен как 'yandex_reviews_fully_recovered.xlsx'")
    print("\nВсе аналитические графики успешно сформированы и сохранены в папку проекта!")


if __name__ == "__main__":
    create_charts()
