from sqlalchemy import create_engine, Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from collections import Counter
from transformers import AutoTokenizer
import os
from dotenv import load_dotenv
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import matplotlib.pyplot as plt

load_dotenv()

DATABASE_URL = f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}/testowa'

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base = declarative_base()

class Message(Base):
    __tablename__ = 'message'
    message_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    category_id = Column(Integer, ForeignKey('categories.category_id'))
    question = Column(Text)
    date = Column(DateTime)

def load_messages():
    session = Session()
    questions = session.query(Message.question).all()
    session.close()
    return [message.question for message in questions]

def preprocess_text(text, all_excluded_words):
    words = word_tokenize(text)
    filtered_words = [word for word in words if word.lower() not in all_excluded_words and word.isalpha()]
    return ' '.join(filtered_words)

def combine_subtokens(tokens):
    combined_tokens = []
    for token in tokens:
        if token.startswith('##'):
            combined_tokens[-1] += token[2:]
        else:
            combined_tokens.append(token)
    return combined_tokens

def filter_tokens(tokens):
    return [token for token in tokens if len(token) > 1 and not token.isnumeric()]

def analyze_questions(questions, all_excluded_words):
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    all_phrases = []
    for question in questions:
        cleaned_question = preprocess_text(question, all_excluded_words)
        tokens = tokenizer.tokenize(cleaned_question)
        tokens = combine_subtokens(tokens)
        tokens = filter_tokens(tokens)
        all_phrases.extend(tokens)

    phrase_counts = Counter(all_phrases)
    most_common_phrases = phrase_counts.most_common(10)

    return most_common_phrases

def main():
    nltk_stopwords = set(stopwords.words('english'))

    custom_exclude_words = {'fov', 'please', 'suggest', 'mark'}

    all_excluded_words = nltk_stopwords.union(custom_exclude_words)

    questions = load_messages()
    most_common_phrases = analyze_questions(questions, all_excluded_words)
 
    print("Most common phrases:")
    for phrase, count in most_common_phrases:
        print(f"{phrase}: {count}")
     
    
    phrases = [phrase for phrase, count in most_common_phrases]
    counts = [count for phrase, count in most_common_phrases]

    plt.figure(figsize=(10,8))
    plt.barh(phrases, counts, color='skyblue')
    plt.xlabel('Phrase count')
    plt.title('10 most common phrases in slack qa channel')
    plt.gca().invert_yaxis()
    plt.show()

if __name__ == "__main__":
    main()

