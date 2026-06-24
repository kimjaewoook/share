import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('/Users/kimjaewoook/ai/.env')
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

file_path = '/Users/kimjaewoook/.gemini/antigravity/brain/5cb09760-0efa-43d9-9ae7-cab3b0d78168/uploaded_media_1778071994634.img'

print("Uploading file...")
uploaded_file = genai.upload_file(file_path, mime_type='audio/mp3') 
print("File uploaded:", uploaded_file.name)

model = genai.GenerativeModel('models/gemini-2.5-pro')
print("Generating transcription...")
response = model.generate_content([
    "This is an audio file containing the user's response to Q1, Q2, Q3. Please provide a full, accurate transcription of what the user says in Korean.",
    uploaded_file
])
print("Transcription:")
print(response.text)

genai.delete_file(uploaded_file.name)
