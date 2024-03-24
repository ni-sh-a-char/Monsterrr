import os
import subprocess
import wave
from vosk import Model, KaldiRecognizer
from transformers import GPT2LMHeadModel, GPT2Tokenizer, TextDataset, DataCollatorForLanguageModeling, Trainer, TrainingArguments

# Step 1: Convert MP4 to WAV and Transcribe using Vosk
def convert_mp4_to_wav_and_transcribe(video_path, model_path):
    wav_path = video_path.replace('.mp4', '.wav')
    subprocess.run(['ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_path])
    
    model = Model(model_path)
    wf = wave.open(wav_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Audio file must be WAV format mono PCM.")
        return None

    rec = KaldiRecognizer(model, wf.getframerate())
    transcript = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            transcript += rec.Result()
        else:
            transcript += rec.PartialResult()

    return transcript

# Step 2: Prepare the Dataset
def prepare_dataset(transcripts, tokenizer):
    tokenized_transcripts = tokenizer(transcripts, padding=True, truncation=True, max_length=512, return_tensors="pt")
    return tokenized_transcripts

# Step 3: Train the Model
def train_model(tokenized_transcripts, model_name="gpt2"):
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)

    dataset = TextDataset(tokenizer=tokenizer, file_path=None, block_size=128, texts=tokenized_transcripts['input_ids'])
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

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

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=dataset
    )

    trainer.train()
    trainer.save_model('./video_language_model')

# Step 4: Main Function
def main():
    # Path to the Vosk model
    vosk_model_path = r'/home/kali/Downloads/vosk-model-small-en-us-0.15'
    
    # Directory containing MP4 videos
    root_dir = r'/home/kali/Downloads/drive-download-20240323T161054Z-001'
    
    transcripts = []
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.mp4'):
                file_path = os.path.join(subdir, file)
                transcript = convert_mp4_to_wav_and_transcribe(file_path, vosk_model_path)
                if transcript: # Ensure the transcript is not empty
                    transcripts.append(transcript)

    if not transcripts:
        print("No transcripts generated. Exiting.")
        return

    # Load pretrained GPT-2 tokenizer
    model_name = "gpt2"
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)

    # Prepare the dataset
    tokenized_transcripts = prepare_dataset(transcripts, tokenizer)

    # Train the model
    train_model(tokenized_transcripts, model_name)

if __name__ == "__main__":
    main()
