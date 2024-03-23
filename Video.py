import os
from google.cloud import speech_v1p1beta1 as speech
from transformers import GPT2LMHeadModel, GPT2Tokenizer, TextDataset, DataCollatorForLanguageModeling, Trainer, TrainingArguments

# Step 1: Generate Transcripts from Local Video Files
def generate_transcripts_from_videos(video_paths):
    transcripts = []
    for path in video_paths:
        client = speech.SpeechClient()

        with open(path, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )

        response = client.recognize(config=config, audio=audio)

        for result in response.results:
            transcripts.append(result.alternatives[0].transcript)

    return transcripts

# Step 2: Preprocess Data
def preprocess_data(transcripts, tokenizer):
    # Tokenize the transcripts
    tokenized_transcripts = tokenizer(transcripts, padding=True, truncation=True, max_length=512, return_tensors="pt")
    return tokenized_transcripts

# Step 3: Train the Language Model
def train_language_model(preprocessed_data, tokenizer):
    # Load pretrained GPT-2 model
    model_name = "gpt2"
    model = GPT2LMHeadModel.from_pretrained(model_name)

    # Define dataset and data collator for language modeling
    dataset = TextDataset(tokenizer=tokenizer, file_path=None, block_size=128, texts=preprocessed_data['input_ids'])
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # Define training arguments
    training_args = TrainingArguments(
        output_dir="./video_language_model",
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
    trainer.save_model('./video_language_model')

def main():
    # Step 1: Generate Transcripts from Local Video Files
    video_paths = ["path/to/video1.wav", "path/to/video2.wav"] # Adjust paths to your local video files
    transcripts = generate_transcripts_from_videos(video_paths)
    
    if not transcripts:
        print("No transcripts generated. Exiting.")
        return

    # Load pretrained GPT-2 tokenizer
    model_name = "gpt2"
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)

    # Step 2: Preprocess Data
    preprocessed_data = preprocess_data(transcripts, tokenizer)

    # Step 3: Train the Language Model
    train_language_model(preprocessed_data, tokenizer)

if __name__ == "__main__":
    main()
