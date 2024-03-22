import requests
from bs4 import BeautifulSoup
import re
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

# Function to collect YouTube data through web scraping
def collect_youtube_data(topic, max_results=50):
    try:
        base_url = f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}"
        response = requests.get(base_url)
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
    except Exception as e:
        print(f"Error collecting data: {e}")

# Main function to train the language model
def main():
    # Prompt user for the topic
    topic = input("Enter the topic you want to train the model on: ")

    # Set maximum number of results
    max_results = 50

    # Collect YouTube data related to the topic through web scraping
    collect_youtube_data(topic, max_results)

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

if __name__ == "__main__":
    main()
