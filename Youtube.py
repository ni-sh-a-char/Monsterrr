import requests
from bs4 import BeautifulSoup
import os
import torch
from transformers import (
    GPT2LMHeadModel,
    GPT2Tokenizer,
    TextDataset,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

# Function to collect YouTube video titles through web scraping
def collect_youtube_data(topic, max_results=50):
    try:
        base_url = f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}"
        response = requests.get(base_url)
        if response.status_code != 200:
            print(f"Failed to retrieve page, status code: {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        titles = []

        for link in soup.find_all("a", {"class": "yt-simple-endpoint style-scope ytd-video-renderer"}):
            title = link.get("title")
            if title:
                titles.append(title)

        with open("youtube_data.txt", "w", encoding="utf-8") as f:
            for title in titles[:max_results]:
                f.write(title.strip() + "\n")

        print(f"Collected {len(titles)} video titles related to '{topic}'.")
        return titles
    except Exception as e:
        print(f"Error collecting data: {e}")
        return []

# Function to collect general text data through web scraping
def collect_general_text_data(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to retrieve page, status code: {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        text_data = []

        # Example: Collect all paragraph text
        for paragraph in soup.find_all("p"):
            text_data.append(paragraph.get_text())

        # Save text data to a file
        with open("general_text_data.txt", "w", encoding="utf-8") as f:
            for text in text_data:
                f.write(text.strip() + "\n")

        print(f"Collected {len(text_data)} paragraphs of text from {url}.")
        return text_data
    except Exception as e:
        print(f"Error collecting data: {e}")
        return []

def main():
    # Prompt user for the topic
    topic = input("Enter the topic you want to train the model on: ")

    # Collect YouTube data related to the topic through web scraping
    youtube_titles = collect_youtube_data(topic)

    # Collect general text data from a specific URL
    # Example URL: 'https://example.com'
    collect_general_text_data('https://example.com')

    # Check if the YouTube dataset is empty
    if len(youtube_titles) == 0:
        print("No YouTube video titles were collected for the topic '{}'. This could be due to changes in YouTube's website structure, restrictions on scraping, or the specific topic not yielding results.".format(topic))
        print("Please try a different topic or check your internet connection.")
        return

    # Load pretrained GPT-2 model and tokenizer
    model_name = "gpt2"
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    model = GPT2LMHeadModel.from_pretrained(model_name)

    # Define dataset and data collator for language modeling
    dataset = TextDataset(
        tokenizer=tokenizer,
        file_path="youtube_data.txt",
        block_size=128
    )

    # Check if the dataset is empty
    if len(dataset) == 0:
        print("The dataset is empty. Please try a different topic or check your internet connection.")
        return

    # Validate dataset content (example: check if the dataset is too small)
    if len(dataset) < 10: # Adjust this threshold based on your needs
        print("The dataset is too small to proceed with training. Please try a different topic or check your internet connection.")
        return

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )

    # Define training arguments
    training_args = TrainingArguments(
        output_dir="./youtube_lm",
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
    trainer.save_model('./youtube_language_model')

if __name__ == "__main__":
    main()
