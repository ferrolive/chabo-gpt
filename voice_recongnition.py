import requests
import json
import sqlite3
import speech_recognition as sr
from gtts import gTTS
import os
import webbrowser

DATABASE = 'knowledge.db'

# Create a database connection
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Create table
cursor.execute('''CREATE TABLE IF NOT EXISTS knowledge
                  (question text, answer text)''')

def remember_knowledge(question, answer):
    cursor.execute("INSERT INTO knowledge VALUES (?,?)", (question, answer))
    conn.commit()

def check_knowledge(question):
    cursor.execute("SELECT answer FROM knowledge WHERE question=?", (question,))
    rows = cursor.fetchall()
    return rows[0][0] if rows else None

def get_response(question):
    # Check if the question is in the database
    answer = check_knowledge(question)
    if answer:
        return answer

    # If not in the database, get the response from the ChatGPT API
    response = requests.post(
        "https://api.openai.com/v1/engines/text-davinci-002/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer OPENAI_API_KEY"
        },
        data=json.dumps({
            "prompt": question,
            "max_tokens": 150
        })
    )


    # Check if the request was successful
    if response.status_code != 200:
        print(f"Request failed with status {response.status_code}")
        print(f"Response content: {response.content.decode('utf-8')}")
        return

    response_content = json.loads(response.content.decode('utf-8'))

    # Check if the 'choices' key is in the response
    if 'choices' not in response_content:
        print(f"'choices' key missing in response")
        print(f"Response content: {response_content}")
        return

    # Get the content of the response
    answer = response_content['choices'][0]['text'].strip()

    # Remember the question and answer for next time
    remember_knowledge(question, answer)

    return answer

def speak(text):
    tts = gTTS(text=text, lang='en') 
    tts.save("response.mp3") 
    os.system("mpg123 -q response.mp3 2>/dev/null") 

def recognize_speech_from_mic(recognizer, microphone):
    if not isinstance(recognizer, sr.Recognizer):
        raise TypeError("`recognizer` must be `Recognizer` instance")

    if not isinstance(microphone, sr.Microphone):
        raise TypeError("`microphone` must be `Microphone` instance")

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    response = {
        "success": True,
        "error": None,
        "transcription": None
    }

    try:
        response["transcription"] = recognizer.recognize_google(audio)
    except sr.RequestError:
        response["success"] = False
        response["error"] = "API unavailable"
    except sr.UnknownValueError:
        response["error"] = "Unable to recognize speech"

    return response

def listen_and_respond():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    print('Listening...')
    while True:        
        speech = recognize_speech_from_mic(recognizer, microphone)

        if speech["transcription"]:
            print('You said: {}'.format(speech["transcription"]))

            # Check if the transcription starts with the command "Ask GPT:"
            if speech["transcription"].lower().startswith("ask gpt:"):
                question = speech["transcription"][len("ask gpt:"):].strip()  # Extract the actual question
                reply = get_response(question)
        
                if reply is not None:
                    print('Bot: ', reply)
                    speak(reply)
                else:
                    print('Sorry, I could not generate a response.')
            elif(speech["transcription"].lower() == "open browser"):
                webbrowser.open('http://google.com')
                continue



if __name__ == "__main__":
    while True:
        listen_and_respond()