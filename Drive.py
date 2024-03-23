import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from transformers import GPT2LMHeadModel, GPT2Tokenizer, TextDataset, DataCollatorForLanguageModeling, Trainer, TrainingArguments

def search_google(topic, site="drive.google.com"):
    # Perform a Google search with the provided topic and filter by the specified site
    query = f"{topic} site:{site}"
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to perform Google search. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error performing Google search: {e}")
        return None

def extract_video_titles(html_content):
    # Extract video titles from the HTML content of the search results
    soup = BeautifulSoup(html_content, "html.parser")
    video_titles = []
    for link in soup.find_all("h3", {"class": "LC20lb DKV0Md"}):
        video_titles.append(link.get_text())
    return video_titles

def preprocess_data(video_titles):
    # Preprocess the video titles as needed
    # For example, tokenize the titles and remove special characters
    # Return a list of preprocessed text data
    preprocessed_data = []
    for title in video_titles:
        # Example preprocessing steps
        cleaned_title = title.strip().replace('\n', ' ')
        preprocessed_data.append(cleaned_title)
    return preprocessed_data

def train_language_model(data):
    # Load pretrained GPT-2 model and tokenizer
    model_name = "gpt2"
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    model = GPT2LMHeadModel.from_pretrained(model_name)

    # Define dataset and data collator for language modeling
    dataset = TextDataset(tokenizer=tokenizer, file_path=None, block_size=128, texts=data)
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # Define training arguments
    training_args = TrainingArguments(
        output_dir="./google_drive_lm",
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
    trainer.save_model('./google_drive_language_model')

def main():
    topic = input("Enter the topic you want to search on Google Drive: ")
    html_content = search_google(topic)
    if not html_content:
        print("No search results found. Exiting.")
        return
    video_titles = extract_video_titles(html_content)
    if not video_titles:
        print("No video titles found in the search results. Exiting.")
        return
    preprocessed_data = preprocess_data(video_titles)
    train_language_model(preprocessed_data)

if __name__ == "__main__":
    main()
