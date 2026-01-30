# Tarot deck with Russian names and meanings

MAJOR_ARCANA = [
    "Шут", "Маг", "Верховная Жрица", "Императрица", "Император",
    "Иерофант", "Влюблённые", "Колесница", "Сила", "Отшельник",
    "Колесо Фортуны", "Справедливость", "Повешенный", "Смерть", "Умеренность",
    "Дьявол", "Башня", "Звезда", "Луна", "Солнце",
    "Суд", "Мир"
]

MINOR_ARCANA = {
    "Жезлы": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка", "Шестёрка", 
              "Семёрка", "Восьмёрка", "Девятка", "Десятка", 
              "Паж", "Рыцарь", "Королева", "Король"],
    "Кубки": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка", "Шестёрка",
              "Семёрка", "Восьмёрка", "Девятка", "Десятка",
              "Паж", "Рыцарь", "Королева", "Король"],
    "Мечи": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка", "Шестёрка",
             "Семёрка", "Восьмёрка", "Девятка", "Десятка",
             "Паж", "Рыцарь", "Королева", "Король"],
    "Пентакли": ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка", "Шестёрка",
                 "Семёрка", "Восьмёрка", "Девятка", "Десятка",
                 "Паж", "Рыцарь", "Королева", "Король"]
}

def get_full_deck():
    """Returns all 78 tarot cards"""
    deck = MAJOR_ARCANA.copy()
    for suit, cards in MINOR_ARCANA.items():
        for card in cards:
            deck.append(f"{card} {suit}")
    return deck

def normalize_card_name(name):
    """Normalize card name for matching"""
    return name.lower().strip()

def find_card(user_input):
    """Find card by partial name match"""
    normalized_input = normalize_card_name(user_input)
    all_cards = get_full_deck()
    
    # Exact match
    for card in all_cards:
        if normalize_card_name(card) == normalized_input:
            return card
    
    # Partial match
    matches = []
    for card in all_cards:
        if normalized_input in normalize_card_name(card):
            matches.append(card)
    
    return matches if matches else None
