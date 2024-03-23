from googlesearch import search
from transformers import GPT2LMHeadModel, GPT2Tokenizer, TextDataset, DataCollatorForLanguageModeling, Trainer, TrainingArguments

def search_web(topic):
    # Search the web for content related to the given topic
    query = f"{topic}"
    search_results = search(query, num_results=5)
    return search_results

def preprocess_data(search_results):
    # Preprocess the search results as needed
    # For this example, we'll just use the titles of the search results
    preprocessed_data = []
    for result in search_results:
        # Example preprocessing step: Extract the title from the URL
        title = result.split('/')[-1].replace('_', ' ')
        preprocessed_data.append(title)
    return preprocessed_data

def train_language_model(data):
    # Load pretrained GPT-2 model and tokenizer
    model_name = "gpt2"
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    model = GPT2LMHeadModel.from_pretrained(model_name)

    # Write preprocessed data to a file
    with open("preprocessed_data.txt", "w", encoding="utf-8") as f:
        for text in data:
            f.write(text + "\n")

    # Define dataset and data collator for language modeling
    dataset = TextDataset(tokenizer=tokenizer, file_path="preprocessed_data.txt", block_size=128)
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # Check if the dataset is empty
    if len(dataset) == 0:
        print("The dataset is empty. Please ensure the preprocessed data file is not empty and correctly formatted.")
        return

    # Define training arguments
    training_args = TrainingArguments(
        output_dir="./web_lm",
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
    trainer.save_model('./web_language_model')

def main():
    topic = input("Enter the topic you want to search on the web: ")
    # Search the web for content related to the topic
    search_results = search_web(topic)
    if not search_results:
        print("No search results found. Exiting.")
        return
    preprocessed_data = preprocess_data(search_results)
    train_language_model(preprocessed_data)

if __name__ == "__main__":
    main()
