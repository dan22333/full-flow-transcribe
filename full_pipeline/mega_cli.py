"""
Module that contains the command line app.
"""
import os
import io
import argparse
import shutil
import glob
from google.cloud import storage
from google.cloud import speech
from google.cloud import texttospeech
import ffmpeg
from tempfile import TemporaryDirectory
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from googletrans import Translator

client = texttospeech.TextToSpeechLongAudioSynthesizeClient()
translator = Translator()

# Generate the inputs arguments parser
parser = argparse.ArgumentParser(description="Command description.")

gcp_project = "hw2-daniel"
bucket_name = "hw2_daniel"
input_audios = "input_audios"
text_prompts = "text_prompts"
text_paragraphs = "text_paragraphs" 
text_audios = "text_audios"
output_audios = "output_audios"
text_translated = "text_translated"
group_name = "hw2_folder" # This needs to be your Group name e.g: group-01, group-02, group-03, group-04, group-05, ...

vertexai.init(project=gcp_project, location="us-central1")
model = GenerativeModel(model_name="gemini-1.5-flash-001",)
generation_config = GenerationConfig(
    temperature=0.01
)

assert group_name!="", "Update group name"
assert group_name!="pavlos-advanced", "Update group name"

def makedirs():
    os.makedirs(input_audios, exist_ok=True)
    os.makedirs(os.path.join(text_prompts,group_name), exist_ok=True)
    os.makedirs(os.path.join(text_paragraphs,group_name), exist_ok=True)
    os.makedirs(os.path.join(text_audios,group_name), exist_ok=True)
    os.makedirs(os.path.join(text_translated,group_name), exist_ok=True)

def transcribe_download():
    print("audio download")

    # Clear
    shutil.rmtree(input_audios, ignore_errors=True, onerror=None)
    makedirs()

    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    blobs = bucket.list_blobs(prefix=input_audios+"/")
    for blob in blobs:
        print(blob.name)
        if not blob.name.endswith("/"):
            blob.download_to_filename(blob.name)

def transcribe():
    print("transcribe")
    makedirs()

    # Speech client
    client = speech.SpeechClient()

    # Get the list of audio file
    audio_files = os.listdir(input_audios)

    for audio_path in audio_files:
        uuid = audio_path.replace(".mp3", "")
        audio_path = os.path.join(input_audios, audio_path)
        text_file = os.path.join(text_prompts, group_name, uuid + ".txt")

        if os.path.exists(text_file):
            continue

        print("Transcribing:", audio_path)
        with TemporaryDirectory() as audio_dir:
            flac_path = os.path.join(audio_dir, "audio.flac")
            stream = ffmpeg.input(audio_path)
            stream = ffmpeg.output(stream, flac_path)
            ffmpeg.run(stream)

            with io.open(flac_path, "rb") as audio_file:
                content = audio_file.read()

            # Transcribe
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(language_code="en-US")
            operation = client.long_running_recognize(config=config, audio=audio)
            response = operation.result(timeout=90)
            print("response:", response)
            text = "None"
            if len(response.results) > 0:
                text = response.results[0].alternatives[0].transcript
                print(text)

            # Save the transcription
            with open(text_file, "w") as f:
                f.write(text)

def transcribe_upload():
    print("transcribe upload")
    print("----------------------------------------")
    makedirs()

    # Upload to bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_prompts, group_name, "*.txt"))

    for text_file in text_files:
        filename = os.path.basename(text_file)
        destination_blob_name = os.path.join(text_prompts, group_name, filename)
        blob = bucket.blob(destination_blob_name)
        print("Uploading:",destination_blob_name, text_file)
        blob.upload_from_filename(text_file)


def generate_download():
    print("transcription download")

    # Clear
    shutil.rmtree(text_prompts, ignore_errors=True, onerror=None)
    makedirs()

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(match_glob=f"{text_prompts}/{group_name}/*.txt")
    for blob in blobs:
        print(blob.name)
        blob.download_to_filename(blob.name)

def generate():
    print("generate")
    makedirs()

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_prompts, group_name, "*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        paragraph_file = os.path.join(text_paragraphs, group_name, uuid + ".txt")

        if os.path.exists(paragraph_file):
            continue

        with open(text_file) as f:
            input_text = f.read()


        # Generate output
        input_prompt = f"""
            Create a transcript for the podcast about cheese with 1000 or more words.
            Use the below text as a starting point for the cheese podcast.
            Output the transcript as paragraphs and not with who is talking or any "Sound" or any other extra information.
            Do not highlight or make words bold.
            The host's name is Pavlos Protopapas.
            {input_text}
        """
        print(input_prompt,"\n\n\n")
        response = model.generate_content(input_prompt,generation_config=generation_config)
        paragraph = response.text


        print("Generated text:")
        print(paragraph)

        # Save the transcription
        with open(paragraph_file, "w") as f:
            f.write(paragraph)


def generate_upload():
    print("genertaed text upload")
    print("----------------------------------------")
    makedirs()

    # Upload to bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_paragraphs, group_name, "*.txt"))

    for text_file in text_files:
        filename = os.path.basename(text_file)
        destination_blob_name = os.path.join(text_paragraphs, group_name, filename)
        blob = bucket.blob(destination_blob_name)
        print("Uploading:",destination_blob_name, text_file)
        blob.upload_from_filename(text_file)

def synthesis_download():
    print("download generated text")

    # Clear
    shutil.rmtree(text_paragraphs, ignore_errors=True, onerror=None)
    makedirs()

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(match_glob=f"{text_paragraphs}/{group_name}/*.txt")
    for blob in blobs:
        print(blob.name)
        blob.download_to_filename(blob.name)


def synthesis():
    print("synthesis")
    print("----------------------------------------")
    makedirs()

    language_code = "en-US" # https://cloud.google.com/text-to-speech/docs/voices
    language_name = "en-US-Standard-B" # https://cloud.google.com/text-to-speech/docs/voices

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_paragraphs, group_name, "*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        audio_file = os.path.join(text_audios, group_name, uuid + ".mp3")

        if os.path.exists(audio_file):
            continue

        with open(text_file) as f:
            input_text = f.read()
        
        # Check if audio file already exists
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        audio_blob_name = f"{text_audios}/{group_name}/{uuid}.mp3"
        blob = bucket.blob(audio_blob_name)

        if not blob.exists():
            # Set the text input to be synthesized
            input = texttospeech.SynthesisInput(text=input_text)
            # Build audio config / Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
            # voice config
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=language_name)

            parent = f"projects/{gcp_project}/locations/us-central1"
            output_gcs_uri = f"gs://{bucket_name}/{audio_blob_name}"

            request = texttospeech.SynthesizeLongAudioRequest(
                parent=parent,
                input=input,
                audio_config=audio_config,
                voice=voice,
                output_gcs_uri=output_gcs_uri,
            )

            operation = client.synthesize_long_audio(request=request)
            # Set a deadline for your LRO to finish. 300 seconds is reasonable, but can be adjusted depending on the length of the input.
            result = operation.result(timeout=300)
            print("Audio file will be saved to GCS bucket automatically.")

def translate_download():
    print("download generated text for translation")

    # Clear
    shutil.rmtree(text_paragraphs, ignore_errors=True, onerror=None)
    makedirs()

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(match_glob=f"{text_paragraphs}/{group_name}/*.txt")
    for blob in blobs:
        print(blob.name)
        blob.download_to_filename(blob.name)


def translate():
    print("translate text")
    makedirs()

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_paragraphs, group_name, "*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        translated_file = os.path.join(text_translated, group_name, uuid + ".txt")

        if os.path.exists(translated_file):
            continue

        with open(text_file) as f:
            input_text = f.read()

        results = translator.translate(input_text, src="en", dest="fr")
        print(results.text)

        # Save the translation
        with open(translated_file, "w") as f:
            f.write(results.text)


def translate_upload():
    print("upload translated text")
    print("----------------------------------------")
    makedirs()

    # Upload to bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_translated, group_name, "*.txt"))

    for text_file in text_files:
        filename = os.path.basename(text_file)
        destination_blob_name = os.path.join(text_translated, group_name, filename)
        blob = bucket.blob(destination_blob_name)
        print("Uploading:",destination_blob_name, text_file)
        blob.upload_from_filename(text_file)

def synthesis_translation_download():
    print("download translated text")

    # Clear
    shutil.rmtree(text_translated, ignore_errors=True, onerror=None)
    makedirs()

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(match_glob=f"{text_translated}/{group_name}/*.txt")
    for blob in blobs:
        print(blob.name)
        blob.download_to_filename(blob.name)

def synthesis_translation():
    print("synthesis translated audio")
    print("----------------------------------------")
    makedirs()

    language_code = "fr-FR" # https://cloud.google.com/text-to-speech/docs/voices
    language_name = "fr-FR-Standard-C" # https://cloud.google.com/text-to-speech/docs/voices

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_translated, group_name, "*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        audio_file = os.path.join(output_audios, group_name, uuid + ".mp3")

        if os.path.exists(audio_file):
            continue

        with open(text_file) as f:
            input_text = f.read()
        
        # Check if audio file already exists
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        audio_blob_name = f"{output_audios}/{group_name}/{uuid}.mp3"
        blob = bucket.blob(audio_blob_name)

        if not blob.exists():
            # Set the text input to be synthesized
            input = texttospeech.SynthesisInput(text=input_text)
            # Build audio config / Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
            # voice config
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=language_name)

            parent = f"projects/{gcp_project}/locations/us-central1"
            output_gcs_uri = f"gs://{bucket_name}/{audio_blob_name}"

            request = texttospeech.SynthesizeLongAudioRequest(
                parent=parent,
                input=input,
                audio_config=audio_config,
                voice=voice,
                output_gcs_uri=output_gcs_uri,
            )

            operation = client.synthesize_long_audio(request=request)
            # Set a deadline for your LRO to finish. 300 seconds is reasonable, but can be adjusted depending on the length of the input.
            result = operation.result(timeout=300)
            print("Audio file will be saved to GCS bucket automatically.")


if __name__ == "__main__":
    transcribe_download()
    transcribe()
    transcribe_upload()
    generate_download()
    generate()
    generate_upload()
    synthesis_download()
    synthesis()
    translate_download()
    translate()
    translate_upload()
    synthesis_translation_download()
    synthesis_translation()
