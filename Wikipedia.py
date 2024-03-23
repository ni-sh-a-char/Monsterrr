import requests
from bs4 import BeautifulSoup
import re
import torch
from transformers import (
    GPT2LMHeadModel,
    GPT2Tokenizer,
    TextDataset,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

def scrape_wikipedia_data(topic):
    try:
        base_url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
        response = requests.get(base_url)
        if response.status_code != 200:
            print(f"Failed to retrieve page, status code: {response.status_code}")
            return ""
        soup = BeautifulSoup(response.text, "html.parser")
        text_data = []

        # Collect all paragraph text
        paragraphs = soup.find_all("p")
        for paragraph in paragraphs:
            text_data.append(paragraph.get_text())

        # Remove citations, references, and special characters
        cleaned_text_data = [re.sub(r"\[.*?\]+", "", paragraph) for paragraph in text_data]
        cleaned_text_data = [re.sub(r"[^a-zA-Z0-9\s]", "", paragraph) for paragraph in cleaned_text_data]

        # Combine paragraphs into a single text
        combined_text = " ".join(cleaned_text_data)

        # Save text data to a file
        with open("wikipedia_data.txt", "w", encoding="utf-8") as f:
            f.write(combined_text)

        print(f"Collected Wikipedia data on '{topic}'.")
        return combined_text
    except Exception as e:
        print(f"Error collecting data: {e}")
        return ""

def train_model():
    # Load pretrained GPT-2 model and tokenizer
    model_name = "gpt2"
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    model = GPT2LMHeadModel.from_pretrained(model_name)

    # Load Wikipedia data
    with open("wikipedia_data.txt", "r", encoding="utf-8") as f:
        wikipedia_text = f.read()

    # Check if the text data is empty
    if not wikipedia_text.strip():
        print("The Wikipedia data is empty. Please ensure the Wikipedia page URL is correct and accessible.")
        return

    # Define dataset and data collator for language modeling
    dataset = TextDataset(
        tokenizer=tokenizer,
        file_path="wikipedia_data.txt",
        block_size=128
    )

    # Check if the dataset is empty
    if len(dataset) == 0:
        print("The dataset is empty. Please ensure the Wikipedia page URL is correct and accessible.")
        return

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )

    # Define training arguments
    training_args = TrainingArguments(
        output_dir="./wikipedia_lm",
        overwrite_output_dir=True,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        save_steps=10_000,
        save_total_limit=2,
        logging_steps=100,
        evaluation_strategy="epoch",
        logging_dir="./logs",
        report_to="none"
    )

    # Create Trainer instance and start training
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=dataset
    )

    trainer.train()

    # Save the trained model
    trainer.save_model('./wikipedia_language_model')

# Main function
def main():
    topic = input("Enter the topic you want to fetch data from Wikipedia: ")
    wikipedia_text = scrape_wikipedia_data(topic)
    if not wikipedia_text:
        print("Failed to collect Wikipedia data. Please try a different topic or check your internet connection.")
        return
    train_model()

if __name__ == "__main__":
    main()
