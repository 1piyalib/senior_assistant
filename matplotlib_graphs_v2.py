import matplotlib
import matplotlib.pyplot as plt
import datetime
import random
import matplotlib.dates as mdates
import csv
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os



def plot_bar_chart():
    #https://pythonspot.com/matplotlib-bar-chart/
    #https://www.tutorialspoint.com/matplotlib/matplotlib_bar_plot.htm
    import numpy as np
    import matplotlib.pyplot as plt
    data = [[30, 25, 50, 20],
    [40, 23, 51, 17],
    [35, 22, 45, 19]]
    X = np.arange(4)
    fig = plt.figure()
    ax = fig.add_axes([0,0,1,1])
    ax.bar(X + 0.00, data[0], color = 'b', width = 0.25)
    ax.bar(X + 0.25, data[1], color = 'g', width = 0.25)
    ax.bar(X + 0.50, data[2], color = 'r', width = 0.25)
    plt.show()

"""
Open the csv file and converts lines to a list of lists
"""
def csv_to_list(csv_file):

    csv_file = open(csv_file, 'r')
    csv_data = csv.reader(csv_file,delimiter=',')
    data_list = list(csv_data)
    csv_file.close()

    return(data_list)

"""
Plots graph from a csv file and stores it as an image file
"""
def plot_graph(csv_file_name, show_plot = True, image_file = "plot_image.png"):

    #x and y axis values going to graph
    x_datetime_list = []      # x axis data is the date and time
    y_measurement1_list = []  # y axis - sugar data or blood pressure high data
    y_measurement2_list = []  # y axis - blood pressure low data
    y_average_list = []       # average value
    #axis labels
    plot_title  = ""
    y_label = ""
    x_label = ""
    legend1 = ""
    legent_palcement = "upper left"

    # Read csv file
    # csv_data_list is list of list of all lines
    # Read data from csv file. It'll return a list [date, time,data1,data2] - data1 for sugar data1,data2 for pressure
    csv_data_list = csv_to_list(csv_file_name)

    if "sugar" in csv_file_name:

        #get a and y axis
        for line_list in csv_data_list:
            datetime_str = line_list[0] + " " + line_list[1]  # add date and time column to make date/time
            x_datetime_list.append(datetime.datetime.strptime(datetime_str, '%m/%d/%Y %H:%M'))  # make it a datetime
            y_measurement1_list.append(float(line_list[2]))  # add measuremnt column as y axis

        plot_title = "Daily Sugar Variations"
        y_label = "sugar level (mg/dL)"
        x_label = "date-time"
        legend1 = "sugar"

        average = sum(y_measurement1_list)/len(y_measurement1_list)
        y_average_list = [average] * len(y_measurement1_list)

    elif "pressure" in csv_file_name:
            # get a and y axis
            for line_list in csv_data_list:
                datetime_str = line_list[0] + " " + line_list[1]  # add date and time column to make date/time
                x_datetime_list.append(datetime.datetime.strptime(datetime_str, '%m/%d/%Y %H:%M'))  # make it a datetime
                y_measurement1_list.append(float(line_list[2]))  # add low pressure column as y axis
                y_measurement2_list.append(float(line_list[3]))  # add high pressure column as y axis

            plot_title = "Daily Pressure Variations"
            y_label = "pressure (mm Hg)"
            x_label = "date-time"
            legend1 = "high"

            average = sum(y_measurement1_list) / len(y_measurement1_list)
            y_average_list = [average] * len(y_measurement1_list)
            legent_palcement = "upper right"

    #setup Plot
    plt.title(plot_title)
    plt.ylabel(y_label)
    plt.xlabel(x_label)
    plt.grid(True)

    #plot graph
    plt.plot(x_datetime_list, y_measurement1_list, color = 'b',  marker='o',label=legend1, linewidth=2.0)
    plt.plot(x_datetime_list,y_average_list, color = 'r', linestyle='--', label="average")

    if "pressure" in csv_file_name:
        plt.plot(x_datetime_list, y_measurement2_list, color='g', marker='o', label="low", linewidth=2.0)

    plt.legend(loc=legent_palcement)

    # beautify the x-labels
    myFmt = mdates.DateFormatter('%Y-%m-%d %H:%M')
    plt.gca().xaxis.set_major_formatter(myFmt)
    plt.gcf().autofmt_xdate()

    # save plot in png format
    plt.savefig(image_file)

    #show plot
    plt.show()
    plt.close()

"""
Opens the csv file and emails the data and attaches the plot image file
"""
def send_email_image(csv_file, subject="", image_file = "plot_image.png"):
    global _user_name
    sender = 'atbhatta@silabs.com'
    senderpasswd = 'projectAIY'
    receiver = 'atanub1@yahoo.com'  # email_adress
    answer = "Successfully sent email"

    print("plotting graph")
    plot_graph(csv_file,image_file)

    if ".csv" not in csv_file:
        answer = "incorrect csv file name "
        print(answer + csv_file)
        return (answer)

    if "@" not in receiver:
        answer = "incorrect email address"
        print(answer + receiver)
        return (answer)

    if "sugar" in csv_file:
        subject = "Daily blood sugar report"
    elif "pressure" in csv_file:
        subject = "Daily blood pressure report"

    img_data = open(image_file, 'rb').read()
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    body = read_entire_file(csv_file)
    text = MIMEText(body)
    msg.attach(text)
    image = MIMEImage(img_data, name=os.path.basename(image_file))
    msg.attach(image)

    try:
        print("Trying to send email, timeout in 10 sec")
        #smtpObj = smtplib.SMTP(host='smtp.gmail.com', port=587, timeout=10)
        smtpObj = smtplib.SMTP(host='postoffice.silabs.com', port=25, timeout=500)
        smtpObj.ehlo()
        smtpObj.starttls()
        smtpObj.ehlo()
        #smtpObj.login(sender, senderpasswd)
        smtpObj.sendmail(sender, receiver, msg.as_string())
        smtpObj.quit()
        answer = "Successfully sent email"
        print(answer)
    except:
        answer = "There was an error. Unable to send email"
        print(answer)

    return (answer)


"""
Read the complete csv file to email
"""
def read_entire_file(csv_file):
    with open(csv_file, 'r') as my_file:
        content = my_file.read()
        # print(content)

    header = ""
    #header for the data
    if "sugar" in csv_file:
        header = "Date\t\tTime\tSugar(ml/dl)\r\n" + "__________________________\r\n\r\n"
    elif "pressure" in csv_file:
        header = "Date\t\tTime\tlow\thigh\r\n" + "__________________________\r\n\r\n"

    final_content = header + content.replace(",", "\t")
    return (final_content)


#plot_graph("blood_sugar.csv")
#send_email_image("blood_sugar.csv")

#plot_graph("blood_pressure.csv")
send_email_image("blood_pressure.csv")