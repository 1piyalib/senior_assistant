"""
imports
"""

#python imports
import logging
import platform
import sys
import subprocess
import re
import datetime
import csv
import smtplib
import json
import calendar

#assistant Imports
import aiy.assistant.auth_helpers
import aiy.assistant.grpc
from aiy.assistant.library import Assistant
from google.assistant.library.event import EventType

#voice HAT imports
import aiy.voicehat


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)

#global variables
_config_file = 'aiy_config.json'
_config_item_list = ["name", "email"]
_blood_pressure_file = "blood_pressure.csv"
_weight_file = "weight.csv"
_blood_sugar_file = "blood_sugar.csv"

_data_file = ""
_current_category = ''
_user_name = ''
_email_address = ''


#######################################
# Find Category
######################################

"""
From the text of the user speech, finds keywords and return one of the five categories
Statements, Questions, E-mail, Configure and Google Assistant
"""

def find_category(text):
    
    global _data_file
    global _user_name
    
    _data_file = "all"
    text = text.lower()
    
    # Find category
    if "configure" in text and has_cfg_iem(text):
        category = "configure"
        
    elif "pressure" in text:
        if "email" in text or "send" in text:
            category = "email"
        elif "how" in text or "what" in text:
            category = "question"
        else:
            category = "statement"
            
        _data_file = _blood_pressure_file
    
    elif "weigh" in text or "weight" in text:
        if "email" in text or "send" in text:
            category = "email"
        elif "how" in text or "what" in text:
            category = "question"
        else:
            category = "statement"
        _data_file = _weight_file
    
    elif "sugar" in text or "glucose" in text:
        if "email" in text or "send" in text:
            category = "email"
        elif "how" in text or "what" in text:
            category = "question"
        else:
            category = "statement"
        _data_file = _blood_sugar_file
        
    elif "email" in text or "send" in text:
        category = "email"
    else:
        category = "assistant"
    
    global _current_category
    _current_category = category

    #print information
    print("data file = " + _data_file)
    print("category is ",category) 
    if category == "assistant":
        print("Google assistant will respond")
    
    return(category)


#
# finds if a text has one of the config items (email,name) from _config_item_list
#
def has_cfg_iem(text):
    for cfg in _config_item_list:
        if cfg in text:
            return True
    return False

#######################################
# process statement category
######################################

"""
processes statement "my blood pressure was 130 over 70"
"""
def process_statement(speech_text):
    
    answer = "statement stored sucessfully"
    
    global _data_file
    csv_file = _data_file
    
    # from "my blood pressure was 130 over 70" extract [130,70] as list
    number_list = extract_number(speech_text)
    
    #if pressure has one value throw error
    if "pressure" in csv_file and len(number_list) !=2:
        answer = "There was an error. Pressure requires two values"
        return(answer)
    
    # geta a date time list. 
    date_time_list = get_date_time_list() #gets ['03-03-2019', '09:45']
    
    #add date time to number, It'll look like ['03-03-2019', '09:45', '130','70']
    number_list = date_time_list + number_list
    
    print("Adding " + str(number_list) + " to file " +csv_file)
    
    #append the list to csv file
    append_csv(csv_file,number_list)
    
    #process if the numbers are too high or low. Then send an email immediately
    print("Processing for alarm")
    answer = process_alarm(number_list)  

    return(answer)

"""
Uses regular expression to returns the list of numbers from a text that contains multiple numbers
for example "my pressure is 170, 70 will return [170,70]
"""

def extract_number(input): 
  
     # get a list of all numbers in a string  
     # \d+ is a regular expression which means decimal
     #https://stackoverflow.com/questions/43514715/python-how-to-extract-float-values-from-text-file
     numbers = re.findall(r"[-+]?\d*\.\d+|\d+", input)
     numbers = list(map(float,numbers)) 
     print("numbers in speech:", numbers)
     
     return numbers
"""
gets a date and time list
"""
def get_date_time_list():
        
    datetimelist = []
    datetimelist.append(datetime.datetime.now().date().strftime('%m-%d-%Y'))
    datetimelist.append(datetime.datetime.now().time().strftime('%H:%M'))

    return(datetimelist)
"""
#appends a list to csv file
"""
def append_csv(file_name,data_list):

    csvfile = open(file_name, 'a', newline='')
    csvwriter = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow(data_list)
    
    return

"""
If readings are too high or low, send email to caregiver
"""
def process_alarm(data_list):

    #low and high alarms were from:
    #https://www.heart.org/en/health-topics/high-blood-pressure/the-facts-about-high-blood-pressure
    #HYPERTENSIVE CRISIS (consult your doctor immediately)	HIGHER THAN 180	and/or	HIGHER THAN 120
    #https://www.mayoclinic.org/diseases-conditions/low-blood-pressure/symptoms-causes/syc-20355465
    
    global _data_file
    csv_file = _data_file
    answer = ""
    if "pressure" in _data_file:
        # data_list[2] is high pressure, data_list[3] low_pressure
        high_pressure = data_list[2]
        low_pressure = data_list[3]
        if(int(high_pressure) >180 or int(low_pressure) > 120 ):
            answer = "Your blood pressure level is high. emailing for immediate attention. "
            email_subject = "Alarm, blood pressure level is too High. Needs attention!!"
            answer += send_email(csv_file,email_subject)
        elif (int(high_pressure) <90 or int(low_pressure) <60):
            answer = "Your blood pressure level is low. emailing for immediate attention. "
            email_subject = "Alarm, blood pressure level is too Low. Needs attention!!"
            answer += send_email(csv_file,email_subject)
        else:
            answer = "your blood pressure level is stored successfully"
    if "sugar" in _data_file:
        #https: // www.webmd.com / diabetes / guide / diabetes - hyperglycemia  # 1
        #https://www.medicalnewstoday.com/articles/322744.php
        suger_level = data_list[2]
        if (suger_level > 240):
            answer = "Your sugar level is too high. emailing for immediate attention. "
            email_subject = "Alarm, blood sugar level is too High. Needs attention!!"
            answer += send_email(csv_file, email_subject)
        elif (suger_level < 80):
            answer = "Your sugar level is too low. emailing for immediate attention. "
            email_subject = "Alarm, blood sugar level is too Low. Needs attention!!"
            answer += send_email(csv_file, email_subject)
        else:
            answer = "your sugar level is stored successfully"
    elif "weight" in _data_file:
        answer = "your weight is stored successfully"
            
    print(answer)      
    return(answer)

#######################################
# process email category
######################################

"""
process email
"""
def process_email(speech):
    #find csv file
    global _data_file
    csv_file = _data_file
    answer = send_email(csv_file)
    return (answer)

""" 
Sends email, returns status
"""
def send_email(csv_file, subject = ""):
    
    global _user_name
    sender = 'teamlightningbots@gmail.com'
    senderpasswd = 'projectAIY'
    receiver = 'atanub1@yahoo.com' #email_adress
    answer = "Successfully sent email"
    
    if ".csv" not in csv_file:
        answer = "incorrect csv file name "
        print(answer + csv_file)
        return(answer)
    
    if "@" not in receiver:
        answer = "incorrect email address"
        print(answer + receiver)
        return(answer)
    
    if subject == "":
        subject = 'Report for ' + _user_name
    
    header = 'To: ' + receiver + 'From: ' + sender + '\n' + 'Subject: ' + subject
    body = read_entire_file(csv_file)
    

    try:
       print("Trying to send email, timeout in 10 sec")
       smtpObj = smtplib.SMTP(host='smtp.gmail.com',port= 587,timeout = 10)
       smtpObj.ehlo()
       smtpObj.starttls()
       smtpObj.ehlo()
       smtpObj.login(sender,senderpasswd)
       smtpObj.sendmail(sender,receiver, header + '\n\n' + body)
       smtpObj.quit()
       answer = "Successfully sent email"
       print (answer)
    except:
       answer = "There was an error. Unable to send email"
       print (answer)
       
    return(answer)

"""
read the complete csv file to email
"""
def read_entire_file(filename):
    with open(filename, 'r') as my_file:
        content = my_file.read()
        #print(content)
    return(content)
    

#######################################
# process configuration category
######################################
"""
processes configuration.  "configure name to Piyali"
"""
def process_configure(text):
    
    global _user_name
    answer = "Error in processing configuraion.  The correct example is: configure name to John"
    print("processing configuration")

    # from "configure name to Piyali" get config item ("Piyali"). This is value in key value pair in dictionary
    value = get_config_value(text)
    #read existing configuration json file and convert to a dictionary
    config_dict = read_config_file()
    for key in _config_item_list:  #loop through all configuration values: "name" email"
        if key in text:
            config_dict[key] = value
            answer = "Configuration item  " + key +   " was changed to " + value
            print(answer)
    #write dictionary back to json file
    write_config_file(config_dict)

    return (answer)
"""
from text = "configure name to Piyali" gets "Piyali"
"""
def get_config_value(text):
    #split the text to list ["configure", "name", "to", "Piyali"]
    temp = text.split()
    item = temp[len(temp) -1] #last in list is "piyali" so, item = "piyali"
    return(item)
"""    
writes a dictionary to json config file  
"""
def write_config_file(my_dictionary):
    with open(_config_file, 'w') as f:
        json.dump(my_dictionary, f)
    f.close()
"""
reads the json configuration file and returns a dictionary
"""
def read_config_file():
    with open(_config_file) as f:
        my_dict = json.load(f)
    f.close()
    return(my_dict)

#######################################
# process Question category
######################################

"""
processes text like "what was my blood pressure on January 15,2017?"
and returns an answer
"""
def process_question(text):

    global _data_file
    csv_file = _data_file
    answer = "no data found for the specified day"
    match_list = []
    
    #if you pass "19 February 2019" it'll return 02-19-2019
    date_str = get_date(text)
    #reads csv file and returns all lines in file as a list of lists
    file_list = read_csv_list(csv_file)
    #loop on each line and match the date ("02-19-2019") and add all mathches to match_list
    for line_list in file_list:
        if(date_str == line_list[0]):
            match_list.append(line_list)
    
    print("Matched list from file: " )
    print(match_list)

    reading_name = get_reading_name(csv_file)
    
    #len of match_list is the number of matches
    answer = "you have " + str(len(match_list)) + " matches for that day. "
    
    for match in match_list:
        if len(match) == 4:  #pressure list 4 elements
            answer += reading_name + str(match[2]) + " and " + str(match[3]) + " at time " + str(match[1]) + "."
        elif len(match == 3): #sugar or weight list
            answer += reading_name + str(match[2])  + " at time " +  str(match[1]) + "."

    print(answer)
    return(answer)

"""
pass "January 19 2007" and get "01" (jan), "00" if no month
"""
def get_month(text):
    index = 0
    #minth is "01" or "12" two characters
    month = format(0, '02d')
    #go through all months in calender and convert "March" to "03"
    for mon in calendar.month_name:
        if mon != '' and mon.lower() in text.lower():
            break;
        index += 1

        month = format(index, '02d')

    return(month)

"""
From the text gets mm-dd-yy
if you pass "19 February 2019" it'll return 02-19-2019
"""
def get_date(text):

    date = format(0, '02d')
    month = format(0, '02d')
    year = format(0, '04d')
    mdy = month + "-" + date + "-" + year

    # using re extract date and month in form of a list [19,2019]
    date_year_list = list(re.findall(r'\d+', text))

    if len(date_year_list) >= 1 :  #"January 19 2007"

        if len(date_year_list) == 1:  # "January 19"  user did not specify year
            year = str(datetime.datetime.now().year)

        if(1 <int(date_year_list[0]) <=31): #if the number is less than 31 its date

            date = format(int(date_year_list[0]), '02d')
            month = get_month(text)
            if len(date_year_list) == 2:
                year = format(int(date_year_list[1]), '04d')
        else: #its yesr
            date = format(int(date_year_list[1]), '02d')
            month = get_month(text)
            if len(date_year_list) == 2:
                year = format(int(date_year_list[0]), '04d')

        #02-19-2019
        mdy = month + "-" + date + "-" + year
        print("Date was converted to " + mdy + " to serch in csv file")

    return(mdy)

"""
#from the csv file gets reading name. "blood_pressure.csv" will return "blood pressure"
"""
def get_reading_name(csv_file):
    
    if "pressure" in csv_file:
        return " blood pressure "
    elif "sugar" in csv_file:
        return " sugar level "
    elif "weight" in csv_file:
        return " weight "
    else:
        return " reading "
"""
#reads csv file and returns as list of lists for all lines, each line is a list
"""
def read_csv_list(csv_file):
    mylist = []
    csv_file = open(csv_file, 'r')
    csv_reader = csv.reader(csv_file, delimiter=',')
    for row in csv_reader:
        if row != []:
            mylist.append(row)
    csv_file.close()
    return(mylist)



##################################################
#  AIY functions - Process speech                #
##################################################

"""
Processes all events sent by cloud assistant
and takes appropriate actions
"""
def process_event(assiatant, event):
    status_ui = aiy.voicehat.get_status_ui()
    
    #assistant is Ready to hear "OK Google" keyword
    if event.type == EventType.ON_START_FINISHED:
        status_ui.status('ready for OK Google')
        if sys.stdout.isatty():
            print('Event:Say "OK, Google" then speak, or press Ctrl+C to quit...')
    
    #Listening to what the user is saying
    elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        status_ui.status('listening')
        print('Event:listening')
    
    # Processing in cloud
    elif event.type == EventType.ON_END_OF_UTTERANCE:
        status_ui.status('thinking')
        print('Event:processing data')
    
    #ready to listen to your next speech
    elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
          or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
          or event.type == EventType.ON_NO_RESPONSE):
        status_ui.status('ready')
        print('Event:ready')
    
    # Recognised your speech, converted to text and you can process text
    elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:

        global _user_name
        #Get the text of the speech
        print('Event:Recognised your speech, converted to text and you can process text')
        print('You said:', event.args['text'])
        text = event.args['text'].lower()

        #process the speech and find which categories it belongs to
        category = find_category(text)

        #Call each category function
        if category == "statement":
            assiatant.stop_conversation()
          
            answer = process_statement(text)
            sayit = "Hello " + _user_name + " " + answer
            aiy.audio.say(sayit)
                
        if category == "email":
            assiatant.stop_conversation()
            answer = process_email(text)
            sayit = "Hi " + _user_name + " " + answer
            aiy.audio.say(sayit)
        
        if category == "question":
            assiatant.stop_conversation()
            answer = process_question(text)
            aiy.audio.say(answer)
            
        
        if category == "configure":
            assiatant.stop_conversation()
            answer = process_configure(text)
            aiy.audio.say(answer)
            
        
        #some other stuff for debugging/fun
        if "ip" in text and "address" in text :
            assiatant.stop_conversation()
            ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
            aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'),lang='en-US', volume = 10)
        if 'lightning' in text or "cheer" in text:
            assiatant.stop_conversation()
            aiy.audio.say('Go Lightning Bots. Go')
        if 'my' in text and 'name':
            assiatant.stop_conversation()
            aiy.audio.say(_user_name)
    #assistant Error    
    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        print("Event:fatal error, stopping program")
        sys.exit(1)


"""
main function - Start of program
"""

def main():
        
    #Make sure its correct raspberry-py
    if platform.machine() == 'armv6l':
        print('This Raspberry-Pi does not run the AIY program!')
        exit(-1)
    
    #update the user name/email from json configuration file
    global _user_name
    global _email_address
    cfg = read_config_file()
    _user_name = cfg["name"]
    _email_address = cfg["email"]
    print("user name = " + _user_name)
    print("email = " + _email_address)
    
    #aiy.audio.say("Hi " + _user_name)
    
    #Get authentication for Google Assistant API
    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
    
    #set to english and volume max
    #aiy.assistant.grpc.AssistantServiceClient(language_code='en-US', volume_percentage=100)
    #https://www.youtube.com/watch?v=rKf6CNJsaPM - custom action
    
    #start assistant and process events
    assistant = Assistant(credentials)
    for event in assistant.start():
        process_event(assistant,event)
        
    return
    
#
#  __main__
#

if __name__ == '__main__':
    main()
