from __future__ import print_function
import os.path
from re import S
import subprocess
from sys import stdout
from webbrowser import get
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os
import time
import playsound
from pyasn1.type.univ import Null
import speech_recognition as sr
from gtts import gTTS
import datetime
import requests, json
import psutil
import gi
gi.require_version("Notify",'0.7')
from gi.repository import Notify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import webbrowser
import random
from timeit import default_timer as timer
from datetime import timedelta
import wikipedia
from googlesearch import search

#all the stats about the user will be stored here.
statsfile= open("stats.json")
stats = json.load(statsfile)

#notification initializer
Notify.init("athena")
#To make the icon showup replace 3rd argument with correct path
#should have used sys and os to fetch paths here
#! FIX : the path to the icon should be dynamically fetched based on the
#!        folder it is placed in.
notification = Notify.Notification.new("athena:","athena started","/home/av/projects/project_athena/athena-logo.png")
notification.set_urgency(0)
notification.show()

#startime of the assitant
start_time = time.time()


"""
? all the keys and static information
"""
# name of the assitant 
ASSITANT = "athena"
SCOPES_CALENDER = ['https://www.googleapis.com/auth/calendar.readonly']
SCOPES_GMAIL = ['https://www.googleapis.com/auth/gmail.readonly']
#weather : api_key_weather + weather_url
api_key_weather = "paste your weather api key here"
weather_url = "http://api.openweathermap.org/data/2.5/weather?"
 
#used by weather API
#this can be inputted using STT via get commands
city_name = "your city name"

#setting up the microphone for listening in background, it listenes for a certain time period
#and determines the threshold
r = sr.Recognizer()
with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source=source)

#authentication for gmail api
def Authenticate_Gmail():

    creds = None
    if os.path.exists('token_gmail.json'):
        creds = Credentials.from_authorized_user_file('token_gmail.json', SCOPES_GMAIL)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_gmail.json', SCOPES_GMAIL)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token_gmail.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    return service

#pre-processing calls to API
gmail_service = Authenticate_Gmail()

"""
? all api calls should be done here
"""
#authenticate the weather api   
def get_api_weather(api_key_weather,weather_url,city_name):
    complete_url = weather_url + "appid=" + api_key_weather + "&q=" + city_name
    response = requests.get(complete_url)
    return response
#pre-processes the weather api
weather_response = get_api_weather(api_key_weather,weather_url,city_name)

#authenticate google calendar API
def authenticate_CALAPI():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES_CALENDER)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES_CALENDER)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    return service

#pre-processing the calender api to be used later
calender_service = authenticate_CALAPI()


#universal speeches 
no_input = ["Didn't catch that, Come again", "I didn't get that",
            "Please try again sir","Something happened,Please try again",
            "Ah! I think I missed something there.","Try again","I missed it, please come again"
            ]
casual_ends = ["Off you go","This all you've got","Tata bye bye","Come quick, off you go","startup go","move on move on","run run"]

#text engine started here.
def speak(text):
    tts = gTTS(text = text,lang="en",tld="co.uk")
    filename = "voice.mp3"
    tts.save(filename)
    playsound.playsound(filename)

# *startup greetings
def startup():
    hr = datetime.datetime.now().hour
    if( hr > 12 and hr < 17):
        afternoon = ["noon there","hot afternoon that its","n"]
        speak(generate_random(afternoon))
    elif(hr >17):
        evening = ["A very good afternoon sir","Evening","hello sir","Evening There"]
        speak(generate_random(evening))
    else:
        morning= ["A very good morning sir","Morning there","Morning Morning","Good morning Sir","Time to start the day"]
        speak(generate_random(morning))
    get_date("today")
    get_weather(weather_response)
    get_calendar_events(10,calender_service)
    get_tasks()
    get_gmail(gmail_service)
    speak(generate_random(casual_ends))

#* invoke to get text from speech
def get_commands():
    playsound.playsound("sounds/start.mp3")
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source, phrase_time_limit=3)
        said = ""
        try:
            said = r.recognize_google(audio).lower()
            print("you said: "+ said)
            playsound.playsound("sounds/mid.mp3")
        except Exception:
            speak(generate_random(no_input))
            playsound.playsound("sounds/end.mp3")
    notification.close()
    return said
# checks the validity of the speech
def valid(said):
    words = get_commands()
    if(len(words.split())<=1):
        speak("Come again master.")
        return False
    return True


#gives next n events details
def get_calendar_events(n,calender_service):

    # Call the Calendar API
    now = datetime.datetime.now().isoformat() + 'Z' # 'Z' indicates UTC time
    events_result = calender_service.events().list(calendarId='primary', timeMin=now,
                                        maxResults=n, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    calender_speech = ["On your calender is","Your schedule is","Stuff on your calendar is"]
    speak(generate_random(calender_speech))
    if not events:
        speak('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        start = start.replace("T"," ")
        i = start.find("+")
        #strip out +timezone
        start = start[:i]
        i = start.find(" ")
        #gets the hr of the event
        hr = int(start[i:].split(":")[0])
        start = start[:i]
        if(hr>12):
            speak(event['summary']+ "on" + start+ "at "+ str(hr)+" PM")
        else:
            speak(event['summary']+ "on" + start+ "at "+ str(hr)+" AM")
        
        print(str(start)+" " + str(event['summary'] + "at " + str(hr)))

#speaks the current date
def get_date(text):
    text = text
    today = datetime.date.today()
    speech = ["Today is the","Date is","It is","day is"]
    if text.count("today") > 0:
        speak(generate_random(speech) +  str(today)) 

#speaks the weather report
def get_weather(weather_response):
    x = weather_response.json()
    
    if x["cod"] != "404":
        y = x["main"]
        current_temperature = y["temp"] -273
        current_pressure = y["pressure"]
        current_humidity = y["humidity"]
        z = x["weather"]
        weather_description = z[0]["description"]
    
        # print following values
        speak("Temperature" +
                        str(current_temperature)[:4] + "degree Celsius"+
            "\n atmospheric pressure" +
                        str(current_pressure) + "pascals"+
            "\n humidity" +
                        str(current_humidity) + "%"+
            "\n ,Overall it seems to be" +
                        str(weather_description))
        if(weather_description.count("rain")):
            rain = ["Sir! If you are planning to go out, please take an umbrella with you.","It is raining sir","dripping clouds","stay away from water"]
            speak(generate_random(rain))
        elif(weather_description.count("overcast")):
            overcast = ["Weather sigh","It maybe shady out there","Weather Nowadays seems so unpredictable!"]
            speak(generate_random(overcast))
    else:
        speak("No information on weather")

#helper for adding tasks
def add_tasks():
    speak("I'm noting down your task sir.")
    task = get_commands()
    flag = False
    while(flag!=True):
        if len(task) > 0:
            with open("todo.txt",'a') as todos:
                todos.write("\n" + task)
            speak("Task added sir.")
            flag = True
        else: 
            speak("Didn't catch that sir. Come again?")
            task = get_commands()

#reads the tasks on the todolist and also asks to add new
def get_tasks():
    task_speeches = ["your todo list for today","your tasks","you have these on list","you have things scheduled"]
    speak(generate_random(task_speeches))
    try:
        with open("todo.txt","r") as todos:
            for each in todos.readlines():
                if(each == "\n"):
                    continue
                speak(each)
    except:
        speak("No tasks in todo list sir!")
    
    ask_to_add = ["Do you want me to add new task?","Want to add something?","Can I can a add task for you?"]
    speak(generate_random(ask_to_add))
    confirm = get_commands()
    if(confirm.count("yes")):
        add_tasks()
    else:
        speeches = ["alright!","Carry on.","I'll be here for you","I am working then"]
        speak(generate_random(speeches))
#remove all tasks
def remove_all():
    #open the file and write nothing to it.
    with open("todo.txt","w") as todo:
        todo.write("")

#used to check a process is already running or not
def check_process(process):
    proc=subprocess.Popen(["ps","ax"],stdout=subprocess.PIPE)
    for each in proc.stdout.readlines():
        if not each:
            break
        if process in str(each):
            return True
    return False

#lauching spotify
def spotify_start():
    if(check_process("spotify")==False):
        subprocess.Popen(["spotify"])
        notification.update("athena","Launching spotify","/home/av/projects/project_athena/athena-logo.png")
        notification.show()
        notification.set_urgency(0)
        launch_confirmation("spotify")
    else:
        subprocess.Popen(["jumpapp","spotify"])
#launching voice commands for the process to be launched
def launch_confirmation(process):
    speeches = ["opening","launching","on your screen","there you go"]
    speak(generate_random(speeches) + str(process))

#gives the information about users gmail
def get_gmail(service):
    # Call the Gmail API
    mail_count = 0
    g = service.users().getProfile(userId="me").execute()
    if(stats["gmail"] < g["messagesTotal"]):
        notification.update("athena says","You have " + str(g["messagesTotal"]-stats["gmail"])+ " new mail in your inbox","/home/av/projects/project_athena/athena-logo.png")
        notification.show()
        speak("You have " + str(g["messagesTotal"]-stats["gmail"])+ " new mail in your inbox") 
        speak("Would you like to check them now?")
        confirm = get_commands()
        if "yes" in confirm:
            webbrowser.open_new("www.gmail.com")
        else:
            speak("okay")

            
    stats["gmail"] = g["messagesTotal"]
    statsfile = open("stats.json",'w')
    json.dump(stats,statsfile)

#generates a random index
def generate_random(array):
    return array[random.randint(0,len(array)-1)]    

#exit
def exit_application():
    exit_speech = ["Bye bye sir","And I see you againnnn","see ya mate","I'll take a sleep"]
    speak(generate_random(exit_speech))
    notification.update("athena says",generate_random(exit_speech),"/home/av/projects/project_athena/athena-logo.png")
    notification.show()
    exit()

#generalized app launcher
def application_launcher(app_name):
    try:
        if(check_process("app_name")==False):
                subprocess.Popen(["jumpapp",str(app_name)])
                launch_confirmation(app_name)
                notification.update("Athena says:","Launching " + str(app_name),"/home/av/projects/project_athena/athena-logo.png" )
                notification.show()
                notification.set_urgency(0)
                notification.close()
        else:
            subprocess.Popen(["jumpapp",str(app_name)])
    except:
        speak("Sorry")
#extracts the name of the application from the text command
def get_app_name(text):
    try:
        text = text.split(" ")[1]
        return str(text)
    except:
        return Null

#provides information from wikipedia
def wiki(text):
    triggers = ["who is","what is","meaning of","what does"]
    for each in triggers:
        if each in text:
            info = wikipedia.summary(text,sentences =1)
            notification.update("Athena says",info,"/home/av/projects/project_athena/athena-logo.png")
            notification.show()
            notification.set_urgency(1)
            return True,info
    return False,""

#browse
def browse(domain):
    speeches = ["opening it","give me a second","on it"]
    speak(generate_random(speeches))
    webbrowser.open_new("www."+str(domain)+".com")


#google search
def google_search(text):
    speeches = ["searching for it","looking for it","searching the web"]
    speak(generate_random(speeches))
    query = text.replace("search","")
    if(len(query)>0):
        site = ""
        for each in search(query, tld='co.in', lang='en', num=1, start=0, stop=None, pause=2.0):
            site = each
        webbrowser.open_new(str(site))
    else:
        speak("try again sir")
            
#listens in background for wake command
def background_listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source=source)
        audio = r.listen(source, phrase_time_limit=7)
        said = ""
        try:
            said = r.recognize_google(audio).lower()
        except Exception:
            pass
    return said    

def summary():
    speeches = ["Here are the updates","Updating your","Getting you updated sir","There you go"]
    speak(generate_random(speeches))
    get_weather(weather_response)
    get_calendar_events(10,calender_service)
    get_tasks()
    get_gmail(gmail_service)
    speak(generate_random(casual_ends))

#casual talks, hello hi
def sup():
    replies = ["hello","hi","hey there!","hola!","Yes sier!","Yes master","hello sir!"]
    speak(generate_random(replies))

#introduce athena
def introduce():
    speeches = ["I am Athena.","Athena. A powerful and intelligent assistant.","A british assistant","I'm a wizard. I can magically do somethings for you."]
    speak(generate_random(speeches)+generate_random(speeches))

def main():
    while True:
        statsfile = open("stats.json",'r')
        stats = json.load(statsfile)

        if(stats["once"]==False):
                startup()
                stats["once"] = True

        wake = background_listen()
        print(wake)
        if wake.count(ASSITANT)>0:

            notification.update("athena says:","athena is listening....","/home/av/projects/project_athena/athena-logo.png")
            notification.show()
            notification.set_urgency(0)
            
            text = get_commands()
        
            notification.close()
            if "who are you" in text or "Who is Athena" in text:
                introduce()
            elif ("hello" in text or "hi" in text or "hey" in text or "hai" in text or "hay" in text):
                sup()
            elif "spotify" in text:
                spotify_start()
            elif "exit" in text or "bye athena" in text:
                exit_application()
            elif "discord" in text:
                application_launcher("discord")
            elif "open" in text:
                application_launcher(get_app_name(text))
            elif wiki(text)[0]:
                speak(wiki(text)[1])
            elif "what's up" in text or "whatsapp" in text:
                summary()
            elif "note down" in text or "remind me" in text or "add tasks" in text:
                add_tasks()
            elif "what's on my list" in text or "what to do" in text:
                get_tasks()
            elif "clear todo" in text or "remove all" in text:
                remove_all()
            elif "browse" in text:
                domain = text.split(" ")[1]
                browse(domain)
            elif "search" in text:
                google_search(text)
            
        
        get_gmail(gmail_service)
        
        #updates the work time of the user
        statsfile = open("stats.json",'w')
        stats["work"] = (time.time() - start_time)/3600.0
        json.dump(stats,statsfile)

if __name__ == "__main__":
    statsfile = open("stats.json",'r')
    stats = json.load(statsfile)
    statsfile = open("stats.json",'w')
    stats["once"] = False
    json.dump(stats,statsfile)
    statsfile.close()
    main()
    