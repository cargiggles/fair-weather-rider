# Fair Weather Rider Lambda v3.0
# Andrew Cargill
# 2019-03-15 - Re-wrote To Use Dark Sky API And pytz

from botocore.vendored import requests
from darksky import forecast
from datetime import datetime, timedelta
from pytz import timezone
import boto3
import json
import os
import pytz

# API Keys
dark_sky_api_key = os.environ['dark_sky_api_key']

# Constants
lat = float(os.environ['lat'])
lng = float(os.environ['lng'])

# User Preferences
lowest_acceptable_precip = int(os.environ['lowest_acceptable_precip'])
lowest_acceptable_temp = int(os.environ['lowest_acceptable_temp'])
phone_number = os.environ['phone_number']

# Local Time Zone To Be Populated By Dark Sky API Call
local_time_zone = "" # America/Los_Angeles

bike_to_work = True

class BikeObject(object):
    """ An Hour Of The Day """
    def __init__(self, hour, precip, temp):
        self.hour = int(hour)
        self.precip = float(precip) # chance of precipitation
        self.temp = float(temp)

    def __str__(self):
        rep = str(self.hour) + ":00\n" + str(self.precip) + "% chance rain\n" + str(self.temp) + " F\n"
        return rep

    def bike_logic(self):
        global bike_to_work
        if self.precip > lowest_acceptable_precip or self.temp < lowest_acceptable_temp:
            bike_to_work = False

def dark_sky_hourly_forecast():
    """ Calls Dark Sky API Using 'darksky' Module And Returns Forecast Object """
    key = dark_sky_api_key
    exclude = "currently,minutely,daily,flags"
    dark_sky_hourly_forecast = forecast(key, lat, lng, exclude = exclude)
    return dark_sky_hourly_forecast

def get_local_date_time(hour):
    """ Accepts Unix Time Integer And Returns Date Time Object Converted To Local Time Zone """
    utc = pytz.utc
    utc_date_time = utc.localize(datetime.utcfromtimestamp(hour))
    local_time_zone_object = timezone(local_time_zone)
    local_date_time_object = utc_date_time.astimezone(local_time_zone_object)
    return local_date_time_object

def send_sns_sms(message):
    """ Accepts String And Sends SMS To Phone Number """
    sns = boto3.client('sns')
    print sns.publish(PhoneNumber = phone_number, Message = message)
    # print both executes and records status codes to CloudWatch

def lambda_handler(event, context):
    global local_time_zone # Allows Change Made To "local_time_zone" To Be Viewable In All Other Functions
    
    # Dark Sky Hourly API Call
    full_forecast = dark_sky_hourly_forecast()

    # Set local_time_zone String
    local_time_zone = full_forecast.timezone

    # Slice Out Array Of Forecasts For Next 24 Hours
    hourly_forecasts = full_forecast.hourly[:24]

    # Make List Of Commute Forecast Objects
    commute_times = [8, 9, 17, 18, 19] # Hours During Which I'd Conceivibly Be Biking
    commute_forecasts = []

    for hourly_forecast in hourly_forecasts:
        local_date_time = get_local_date_time(hourly_forecast.time)

        if local_date_time.hour in commute_times:
            commute_forecasts.append(hourly_forecast)

    # Make List of Bike Objects - Representing Each Potential Hour Of Commute With Bike Logic
    bikes = []
    for commute_forecast in commute_forecasts:
        bike = BikeObject(get_local_date_time(commute_forecast.time).hour, commute_forecast.precipProbability, commute_forecast.temperature)
        bikes.append(bike)

    # Invoke Each Bike Object's 'bike_logic()' Function To Test Whether To Toggle 'bike_to_work' False
    for bike in bikes:
        bike.bike_logic()
        print bike

    if bike_to_work == True:
        send_sns_sms("Ride Your Bike!" + " " + "(" + today_date_time.strftime("%A") + ")")
        print today_date_time.strftime("%a %b %d %Y") + "\nRide your bike!\nSMS Sent!"
    else:
        print "It's too cold and/or rainy, bus it."