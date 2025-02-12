import pymongo
import time
from scrapy.exceptions import DropItem
from pymongo.errors import ConnectionFailure
import spacy
from transformers import pipeline, BertTokenizer, BertForSequenceClassification
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class ESGProcessingPipeline:
    def __init__(self):
        """Initialize MongoDB connection with retry logic."""
        try:
            # MongoDB connection with a timeout to avoid hanging the program
            self.client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
            self.db = self.client["esg_database"]
            self.collection = self.db["esg_data"]
            
            # Create indexes to optimize queries
            self.collection.create_index([("company", pymongo.ASCENDING)])  # Index for company
            self.collection.create_index([("cleaned_text", pymongo.ASCENDING)])  # Index for cleaned_text
            self.collection.create_index([("esg_terms", pymongo.ASCENDING)])  # Index for esg_terms

            # Check if MongoDB connection is successful
            self.client.admin.command('ping')
            print("✅ Successfully connected to MongoDB.")
        except ConnectionFailure as e:
            print(f"❌ MongoDB connection failed: {e}")
            raise DropItem(f"Failed to connect to MongoDB: {e}")
        
        # Load SpaCy model for NLP-based processing
        self.nlp = spacy.load("en_core_web_sm")  # Load SpaCy model for English processing

        # Define ESG term weights
        self.esg_weights = {
            'carbon': 3, 'energy': 3, 'sustainability': 2, 'emissions': 3, 
            'partnerships': 2, 'projects': 2, 'eco-friendly': 3, 'climate': 3, 
            'initiative': 2, 'education': 1, 'social': 1, 'community': 1, 
            'transparency': 1, 'business': 1
        }

        # Define lexicon of ESG-related terms
        self.lexicon = {
            'carbon': ['carbon', 'carbon footprint', 'co2', 'greenhouse gases'],
            'energy': ['energy', 'renewable energy', 'solar power', 'wind energy'],
            'sustainability': ['sustainability', 'sustainable', 'green tech', 'eco-friendly'],
            'climate': ['climate change', 'global warming', 'climate action', 'environmental protection','Greenfield'],
            'social': ['social impact', 'community', 'education', 'healthcare', 'diversity'],
            'transparency': ['transparency', 'accountability', 'ethics', 'governance']
        }
        
        # Load the RoBERTa zero-shot classification model for ESG classification
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        
        # Load the BERT model for sentiment analysis
        self.sentiment_analyzer = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")

        # Load BERT model for fine-tuning
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.model = BertForSequenceClassification.from_pretrained('bert-base-uncased')

        # Initialize the TF-IDF Vectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english")

    def insert_with_retry(self, data, retries=3, initial_delay=2):
        """Attempt to insert data into MongoDB with retries and backoff strategy."""
        attempt = 0
        delay = initial_delay
        while attempt < retries:
            try:
                self.collection.insert_one(data)
                print(f"✅ Data inserted successfully.")
                return True
            except Exception as e:
                attempt += 1
                print(f"❌ Attempt {attempt} failed: {e}")
                if attempt < retries:
                    print(f"⏳ Retrying in {delay} seconds... (Attempt {attempt}/{retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print("❌ Max retries reached. Could not insert data.")
                    return False

    def update_company_data(self, company_name, data):
        """Update data for a single company by combining terms and updating the ESG score."""
        existing_entry = self.collection.find_one({"company": company_name})

        if existing_entry:
            # Combine ESG terms
            existing_terms = set(existing_entry.get("esg_terms", []))
            new_terms = set(data["esg_terms"])
            combined_terms = list(existing_terms.union(new_terms))

            # Update the URLs for the company
            existing_urls = set(existing_entry.get("url", []))
            new_urls = set(data.get("url", []))
            combined_urls = list(existing_urls.union(new_urls))

            # Update ESG score by adding the new terms' scores
            updated_esg_score = self.calculate_esg_score(combined_terms, data.get("classification"), data.get("sentiment"))

            # Update the company data with new terms, URLs, and updated score
            self.collection.update_one(
                {"company": company_name},
                {"$set": {
                    "esg_terms": combined_terms,
                    "url": combined_urls,
                    "esg_score": updated_esg_score,
                    "classification": data.get("classification"),  # Store classification result
                    "sentiment": data.get("sentiment")  # Store sentiment result
                }} 
            )
            print(f"✅ Updated data for {company_name}.")
        else:
            # Insert new data for the company
            self.collection.insert_one(data)
            print(f"✅ Inserted new data for {company_name}.")

    def process_item(self, item, spider):
        """Process each scraped item from Scrapy."""
        # Fallback if 'text' field is missing
        if not item.get("text"):
            item["text"] = "No text available"  # Fallback value if missing
            print(f"❌ Missing 'text' field in item, using fallback.")

        # Extract company name from the spider's metadata (passed to item)
        company_name = spider.name  # Use spider name to identify company or project
        if not company_name:
            company_name = "Unknown Company"  # Default value if no company name is found

        urls = item.get("urls", [])  # Ensure that URLs are retrieved as a list
        if not urls:
            urls = [item.get("url", "Unknown")]  # Default to a single URL if none provided

        # Process the text and extract ESG-related terms
        processed_data = self.process_text(item["text"])
        processed_data.update({"company": company_name, "url": urls})

        # Classify the scraped text using RoBERTa
        labels = ["eco-friendly", "sustainability", "renewable energy", "carbon neutral", "green tech"]
        classification_result = self.classifier(item["text"], candidate_labels=labels)
        
        # Add classification result to the processed data
        processed_data["classification"] = classification_result

        # Perform sentiment analysis
        sentiment_result = self.sentiment_analyzer(item["text"], truncation=True, max_length=512)

        # Add sentiment result to the processed data
        processed_data["sentiment"] = sentiment_result

        # Calculate the ESG score for the company based on extracted terms and their weights
        esg_score = self.calculate_esg_score(processed_data["esg_terms"], classification_result, sentiment_result)

        # Add the ESG score to the processed data
        processed_data["esg_score"] = esg_score

        # Combine data for the company into one document
        self.update_company_data(company_name, processed_data)

        return item  # Continue passing item through Scrapy pipeline

    def process_text(self, text):
        """Process the ESG-related text, clean it, and extract relevant terms using NLP and lexicon."""
        # Clean the text (you can add more cleaning logic as needed)
        cleaned_text = text.lower()

        # Use NLP to extract potential ESG-related terms dynamically
        doc = self.nlp(cleaned_text)
        esg_terms = set()  # Using a set to avoid duplicates
        
        # Example: Extracting nouns and proper nouns as potential ESG-related terms
        for token in doc:
            if token.pos_ in ['NOUN', 'PROPN'] and token.text not in esg_terms:
                esg_terms.add(token.text)

        # Use BERT to refine terms contextually
        refined_terms = self.bert_refinement(cleaned_text)

        # Combine predefined ESG terms with dynamically extracted terms
        esg_terms.update(self.extract_from_lexicon(cleaned_text))
        esg_terms.update(refined_terms)

        return {
            "cleaned_text": cleaned_text,
            "esg_terms": list(esg_terms)  # Convert set back to list
        }

    def bert_refinement(self, text):
        """Refine ESG-related terms using BERT to understand context and relationships between words."""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        logits = outputs.logits
        predicted_class = torch.argmax(logits, dim=1).item()
        # Here, you can extract meaningful ESG terms based on predictions and context
        return ["example_bert_term"]  # Replace with actual term extraction logic using BERT

    def extract_from_lexicon(self, text):
        """Extract terms from lexicon based on predefined categories.""" 
        esg_terms = set()
        
        for category, keywords in self.lexicon.items():
            for keyword in keywords:
                if keyword in text:
                    esg_terms.add(keyword)
        
        return esg_terms

    def calculate_esg_score(self, esg_terms, classification_result, sentiment_result=None):
        """Calculate the ESG score based on the extracted terms, classification, and sentiment."""
        score = 0
        term_frequencies = {}  # Store frequency of each term in the text
        
        # Count term frequencies
        for term in esg_terms:
            term_frequencies[term] = term_frequencies.get(term, 0) + 1

        # Apply weight based on term frequency and importance of terms
        for term, frequency in term_frequencies.items():
            term_weight = self.esg_weights.get(term, 0)

            # Calculate score with frequency adjustment (term frequency multiplied by weight)
            score += term_weight * frequency

        # Normalize the score (optional: adjust depending on the scale you want)
        max_score = sum(self.esg_weights.values()) * len(esg_terms)  # Maximum score possible
        normalized_score = (score / max_score) * 100  # Normalize to a percentage

        # Ensure score does not go below zero
        normalized_score = max(normalized_score, 0)

        return round(normalized_score, 2)  # Return the score rounded to 2 decimal places

    def close_spider(self, spider):
        """Ensure MongoDB connection is closed properly after the spider finishes.""" 
        if hasattr(self, "client"):
            self.client.close()
            print("✅ MongoDB connection closed.")
