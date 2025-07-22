# utils.py
import re
from collections import Counter
from typing import Dict, Tuple

def calculate_keyword_weight(keyword: str, position: str = 'content') -> float:
    """Calculate weight based on keyword characteristics"""
    base_weight = 1.0
    
    # Multi-word phrases get higher weight
    if ' ' in keyword:
        word_count = len(keyword.split())
        base_weight *= (1.5 ** (word_count - 1))
    
    # Position-based weights
    if position == 'title':
        base_weight *= 2.0
    elif position == 'summary':
        base_weight *= 1.2
    
    # High-value keywords
    high_value_keywords = {
        'artificial intelligence', 'machine learning', 'prime minister', 'chief minister',
        'world cup', 'champions league', 'supreme court', 'coronavirus', 'covid-19',
        'stock market', 'sensex', 'nifty', 'bollywood', 'ipl', 'parliament'
    }
    
    if keyword in high_value_keywords:
        base_weight *= 1.8
    
    return base_weight

def preprocess_text(text: str) -> Dict[str, any]:
    """Advanced text preprocessing"""
    text_lower = text.lower()
    clean_text = re.sub(r'[^\w\s]', ' ', text_lower)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    words = clean_text.split()
    word_set = set(words)
    word_freq = Counter(words)
    
    # Create phrases
    phrases = []
    for i in range(len(words)):
        for j in range(2, 5):
            if i + j <= len(words):
                phrase = ' '.join(words[i:i+j])
                phrases.append(phrase)
    
    return {
        'original': text,
        'clean_text': clean_text,
        'words': words,
        'word_set': word_set,
        'word_freq': word_freq,
        'phrases': phrases,
        'text_length': len(words)
    }

def generate_smart_label(title: str) -> str:
    """Generate intelligent labels"""
    stop_words = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
        'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were',
        'will', 'with', 'says', 'said', 'after', 'this', 'these', 'those', 'they',
        'them', 'their', 'than', 'then', 'there', 'where', 'when', 'what', 'who',
        'why', 'how', 'but', 'or', 'so', 'can', 'could', 'would', 'should'
    }
    
    important_words = {
        'covid', 'corona', 'vaccine', 'election', 'government', 'minister', 'court',
        'cricket', 'ipl', 'bollywood', 'market', 'stock', 'rupee', 'dollar',
        'police', 'arrest', 'hospital', 'doctor', 'school', 'university',
        'technology', 'ai', 'digital', 'cyber'
    }
    
    title_clean = re.sub(r'[^\w\s]', '', title.lower())
    words = title_clean.split()
    
    word_scores = {}
    for i, word in enumerate(words):
        score = 0.0
        
        if len(word) > 3:
            score += len(word) * 0.1
        
        position_bonus = max(0, 5 - i) * 0.1
        score += position_bonus
        
        if word in important_words:
            score += 2.0
        
        if word in stop_words:
            score -= 1.0
        
        if len(word) <= 2:
            score -= 0.5
        
        word_scores[word] = score
    
    sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
    selected_words = []
    
    for word, score in sorted_words:
        if score > 0 and len(selected_words) < 5:
            selected_words.append(word)
    
    if len(selected_words) < 3:
        for word in words:
            if word not in selected_words and len(word) > 2:
                selected_words.append(word)
                if len(selected_words) >= 4:
                    break
    
    if selected_words:
        label = ' '.join(selected_words[:5]).title()
    else:
        label = ' '.join(words[:4]).title()
    
    return label if label.strip() else "News Update"
